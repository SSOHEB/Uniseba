"""Background OCR worker for continuously updating the visible text index."""

import asyncio
import logging
import threading
import time
from queue import Queue

import config
from mss import mss
from PIL import Image
import win32gui

from capture.change import get_changed_regions
from ocr.engine import recognize_image
from ocr.index import build_ocr_index

SCAN_INTERVAL_MS = getattr(config, "SCAN_INTERVAL_MS", 150)
MIN_TARGET_WIDTH = 300
MIN_TARGET_HEIGHT = 200
CHANGE_GRID = getattr(config, "CHANGE_GRID", (4, 4))
CHANGE_THRESHOLD = getattr(config, "CHANGE_THRESHOLD", 6.0)
CHANGE_THUMB_SIZE = getattr(config, "CHANGE_THUMB_SIZE", (32, 32))
OCR_DOWNSCALE = getattr(config, "OCR_DOWNSCALE", 0.75)
OCR_UPDATE_DEBOUNCE_MS = getattr(config, "OCR_UPDATE_DEBOUNCE_MS", 350)
OCR_STABILITY_COUNT_THRESHOLD = getattr(config, "OCR_STABILITY_COUNT_THRESHOLD", 20)


class OCRThread(threading.Thread):
    """Capture the current target window, OCR it, and push updated indexes."""

    def __init__(
        self,
        index_queue: Queue,
        stop_event: threading.Event,
        excluded_hwnds=None,
        preferred_hwnd=None,
        locked_hwnd=None,
        lock_active=None,
    ):
        super().__init__(daemon=True, name="UnisebaOCR")
        self.index_queue = index_queue
        self.stop_event = stop_event
        self.excluded_hwnds = excluded_hwnds or (lambda: set())
        self.preferred_hwnd = preferred_hwnd or (lambda: None)
        self.locked_hwnd = locked_hwnd or (lambda: None)
        self.lock_active = lock_active or (lambda: False)
        self.logger = logging.getLogger("uniseba")
        self.current_image = None
        self.target_hwnd = None
        self.last_valid_hwnd = None
        self.has_found_valid_target = False
        self.blocked_exact_titles = {"windows powershell", "uniseba search"}
        self.region_index_cache = {}
        self.last_stable_index = []
        self.last_update_at = 0.0

    def run(self):
        """Keep OCR results fresh until the application exits."""
        while not self.stop_event.is_set():
            try:
                self._update_target_window()
                image, rect = self._capture_target_window()
                if image is None:
                    self.stop_event.wait(SCAN_INTERVAL_MS / 1000.0)
                    continue

                if not self.has_found_valid_target:
                    self.has_found_valid_target = True
                    self.last_valid_hwnd = self.target_hwnd

                changed_regions = get_changed_regions(
                    self.current_image,
                    image,
                    grid=CHANGE_GRID,
                    threshold=CHANGE_THRESHOLD,
                    thumb_size=CHANGE_THUMB_SIZE,
                )
                total_regions = CHANGE_GRID[0] * CHANGE_GRID[1]
                if not changed_regions:
                    print(f"[CHANGE] regions_changed=0/{total_regions}")
                    print("[CHANGE] no change -> skipping OCR")
                    self.current_image = image
                    self.stop_event.wait(SCAN_INTERVAL_MS / 1000.0)
                    continue

                print(f"[CHANGE] regions_changed={len(changed_regions)}/{total_regions}")
                self.current_image = image
                now = time.monotonic()
                if now - self.last_update_at < (OCR_UPDATE_DEBOUNCE_MS / 1000.0):
                    print("[OCR] debounced -> skipping update")
                    self.stop_event.wait(SCAN_INTERVAL_MS / 1000.0)
                    continue

                index = asyncio.run(self._build_partial_index(image, rect, changed_regions))
                index = self._stabilize_index(index)
                if index is None:
                    print("[OCR] unstable frame -> keeping last stable index")
                    self.stop_event.wait(SCAN_INTERVAL_MS / 1000.0)
                    continue

                self.last_stable_index = index
                self.last_update_at = now
                print(f"[OCR] partial_regions={len(changed_regions)} total_words={len(index)}")
                self.index_queue.put(index)
            except Exception:
                self.logger.exception("OCR thread failed while updating the index.")

            self.stop_event.wait(SCAN_INTERVAL_MS / 1000.0)

    def _update_target_window(self):
        """Track the last foreground window that does not belong to Uniseba."""
        if self.lock_active():
            locked = self.locked_hwnd()
            self.target_hwnd = locked
            if locked:
                print(f"[OCR USING LOCKED] hwnd={locked} title={win32gui.GetWindowText(locked)!r}")
            return

        if not self.has_found_valid_target:
            preferred = self.preferred_hwnd()
            if self._is_bootstrap_target(preferred):
                self.target_hwnd = preferred
                print(f"[OCR TARGET] bootstrap selecting preferred hwnd={preferred} title={win32gui.GetWindowText(preferred)!r}")
                return
            hwnd = win32gui.GetForegroundWindow()
            if self._is_bootstrap_target(hwnd):
                self.target_hwnd = hwnd
                print(f"[OCR TARGET] bootstrap selecting hwnd={hwnd} title={win32gui.GetWindowText(hwnd)!r}")
            return

        preferred = self.preferred_hwnd()
        if preferred and self._is_valid_target(preferred):
            self.target_hwnd = preferred
            self.last_valid_hwnd = preferred
            print(f"[OCR TARGET] preferred hwnd={preferred} title={win32gui.GetWindowText(preferred)!r}")
            return
        hwnd = win32gui.GetForegroundWindow()
        if hwnd and self._is_valid_target(hwnd):
            self.target_hwnd = hwnd
            self.last_valid_hwnd = hwnd
            print(f"[OCR TARGET] foreground hwnd={hwnd} title={win32gui.GetWindowText(hwnd)!r}")
            return
        if self.last_valid_hwnd and self._is_valid_target(self.last_valid_hwnd):
            self.target_hwnd = self.last_valid_hwnd
            print(f"[OCR TARGET] fallback to last valid hwnd={self.last_valid_hwnd} title={win32gui.GetWindowText(self.last_valid_hwnd)!r}")

    def _is_bootstrap_target(self, hwnd):
        """Allow almost any visible non-minimized window until OCR starts once."""
        if not hwnd or not win32gui.IsWindow(hwnd) or win32gui.IsIconic(hwnd):
            print(f"[OCR TARGET] skipped invalid/minimized hwnd={hwnd}")
            return False
        if hwnd in self.excluded_hwnds():
            print(f"[OCR TARGET] skipped owned bootstrap hwnd={hwnd}")
            return False
        raw_title = win32gui.GetWindowText(hwnd).strip()
        title = raw_title.lower()
        if title in self.blocked_exact_titles or title.startswith("uniseba"):
            print(f"[OCR TARGET] skipped blocked bootstrap title hwnd={hwnd} title={title!r}")
            return False
        left, top, right, bottom = win32gui.GetWindowRect(hwnd)
        width = right - left
        height = bottom - top
        if width <= 0 or height <= 0:
            print(f"[OCR TARGET] skipped invalid bootstrap size hwnd={hwnd}")
            return False
        return True

    def _is_valid_target(self, hwnd):
        """Reject invalid, minimized, or known Uniseba/debug windows."""
        if not hwnd or not win32gui.IsWindow(hwnd) or win32gui.IsIconic(hwnd):
            print(f"[OCR TARGET] skipped invalid/minimized hwnd={hwnd}")
            return False
        if hwnd in self.excluded_hwnds():
            print(f"[OCR TARGET] skipped owned hwnd={hwnd}")
            return False
        raw_title = win32gui.GetWindowText(hwnd).strip()
        if len(raw_title) < 2:
            print(f"[OCR TARGET] skipped empty title hwnd={hwnd}")
            return False
        title = raw_title.lower()
        class_name = win32gui.GetClassName(hwnd).lower()
        if title in self.blocked_exact_titles or title.startswith("uniseba"):
            print(f"[OCR TARGET] skipped blocked title hwnd={hwnd} title={title!r}")
            return False
        if class_name == "consolewindowclass" and ("powershell" in title or "python" in title):
            print(
                f"[OCR TARGET] skipped blocked console hwnd={hwnd} "
                f"class={class_name!r} title={title!r}"
            )
            return False
        left, top, right, bottom = win32gui.GetWindowRect(hwnd)
        width = right - left
        height = bottom - top
        if width < MIN_TARGET_WIDTH or height < MIN_TARGET_HEIGHT:
            print(f"[OCR TARGET] skipped small window hwnd={hwnd} size={width}x{height}")
            return False
        return True

    def _capture_target_window(self):
        """Capture the tracked foreground window using absolute screen coordinates."""
        hwnd = self.target_hwnd
        if self.lock_active():
            if not hwnd or not win32gui.IsWindow(hwnd) or win32gui.IsIconic(hwnd):
                print(f"[TARGET IGNORED] hwnd={hwnd} title={win32gui.GetWindowText(hwnd) if hwnd and win32gui.IsWindow(hwnd) else ''!r}")
                return None, None
            print(f"[OCR USING LOCKED] hwnd={hwnd} title={win32gui.GetWindowText(hwnd)!r}")
        elif not self.has_found_valid_target:
            if not self._is_bootstrap_target(hwnd):
                return None, None
        elif not self._is_valid_target(hwnd):
            return None, None

        left, top, right, bottom = win32gui.GetWindowRect(hwnd)
        width, height = right - left, bottom - top
        if width <= 0 or height <= 0:
            return None, None

        rect = {"left": left, "top": top, "width": width, "height": height}
        if not self.has_found_valid_target:
            print(f"[OCR TARGET] bootstrap capturing hwnd={hwnd} title={win32gui.GetWindowText(hwnd)!r} rect={rect}")
        else:
            print(f"[OCR TARGET] capturing hwnd={hwnd} title={win32gui.GetWindowText(hwnd)!r} rect={rect}")
        with mss() as sct:
            shot = sct.grab(rect)
            image = Image.frombytes("RGB", shot.size, shot.rgb)
        return image, rect

    async def _build_partial_index(self, image, rect, changed_regions):
        """OCR only changed regions and reuse cached OCR results for stable areas."""
        scale_back = 1.0 / max(OCR_DOWNSCALE, 0.01)
        for region in changed_regions:
            key = (
                region["left"],
                region["top"],
                region["width"],
                region["height"],
            )
            region_box = (
                region["left"],
                region["top"],
                region["left"] + region["width"],
                region["top"] + region["height"],
            )
            region_image = image.crop(region_box)
            region_image = self._prepare_region_image(region_image)
            words = await recognize_image(region_image, None)
            transformed_words = []
            for word in words:
                screen_x = int(rect["left"] + region["left"] + (int(word["x"]) * scale_back))
                screen_y = int(rect["top"] + region["top"] + (int(word["y"]) * scale_back))
                transformed_words.append(
                    {
                        "text": word["text"],
                        "x": screen_x,
                        "y": screen_y,
                        "w": int(word["w"] * scale_back),
                        "h": int(word["h"] * scale_back),
                    }
                )
            self.region_index_cache[key] = build_ocr_index(transformed_words)

        deduped = {}
        for region_words in self.region_index_cache.values():
            for item in region_words:
                deduped[(item["word"], item["x"], item["y"], item["w"], item["h"])] = item
        return list(deduped.values())

    def _prepare_region_image(self, image):
        """Slightly downscale OCR regions so partial passes stay lightweight."""
        if OCR_DOWNSCALE >= 0.99:
            return image
        width = max(1, int(image.width * OCR_DOWNSCALE))
        height = max(1, int(image.height * OCR_DOWNSCALE))
        return image.resize((width, height), Image.Resampling.LANCZOS)

    def _stabilize_index(self, new_index):
        """Reject wildly different frames and smooth matching word positions."""
        old_index = self.last_stable_index
        if not old_index:
            return new_index

        if abs(len(new_index) - len(old_index)) > OCR_STABILITY_COUNT_THRESHOLD:
            return None

        old_lookup = {}
        for item in old_index:
            old_lookup.setdefault(item["word"], []).append(item)

        stabilized = []
        for item in new_index:
            previous = self._find_previous_match(item, old_lookup.get(item["word"], []))
            if previous is not None:
                item = {
                    **item,
                    "x": int((previous["x"] + item["x"]) / 2),
                    "y": int((previous["y"] + item["y"]) / 2),
                }
            stabilized.append(item)
        return stabilized

    def _find_previous_match(self, item, candidates):
        """Find the closest prior word with the same normalized text."""
        if not candidates:
            return None
        return min(
            candidates,
            key=lambda candidate: abs(candidate["x"] - item["x"]) + abs(candidate["y"] - item["y"]),
        )
