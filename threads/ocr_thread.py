"""Background OCR worker for continuously updating the visible text index."""

import logging
import threading
import time
from queue import Queue

from mss import mss
from PIL import Image, ImageDraw
import win32con
import win32gui

from capture.change import get_changed_regions
from config import (
    BLOCKED_CONSOLE_KEYWORDS,
    BLOCKED_WINDOW_PREFIXES,
    BLOCKED_WINDOW_TITLES,
    CHANGE_GRID,
    CHANGE_THRESHOLD,
    CHANGE_THUMB_SIZE,
    DESKTOP_WINDOW_KEYWORD,
    FORCED_OCR_INTERVAL_MS,
    MAJOR_CHANGE_REGION_COUNT,
    MAJOR_CHANGE_REGION_RATIO,
    MIN_TARGET_HEIGHT,
    MIN_TARGET_TITLE_LENGTH,
    MIN_TARGET_WIDTH,
    OCR_DOWNSCALE,
    OCR_STABILITY_COUNT_THRESHOLD,
    OCR_UPDATE_DEBOUNCE_MS,
    PARTIAL_OCR_ENABLED,
    PARTIAL_OCR_MAX_AREA_RATIO,
    PARTIAL_OCR_MAX_RECTS,
    PARTIAL_OCR_PADDING_PX,
    SCAN_INTERVAL_MS,
    SEARCH_UI_EXCLUSION_PADDING,
    SELF_UI_PHRASES,
)
from ocr.engine import recognize_image
from ocr.index import build_ocr_index

logger = logging.getLogger("uniseba.ocr.thread")


class OCRThread(threading.Thread):
    """Capture the current target window, OCR it, and push updated indexes."""

    def __init__(
        self,
        index_queue: Queue,
        stop_event: threading.Event,
        excluded_hwnds=None,
        exclusion_rects=None,
        preferred_hwnd=None,
        locked_hwnd=None,
        lock_active=None,
    ):
        super().__init__(daemon=True, name="UnisebaOCR")
        self.index_queue = index_queue
        self.stop_event = stop_event
        self.excluded_hwnds = excluded_hwnds or (lambda: set())
        self.exclusion_rects = exclusion_rects or (lambda: [])
        self.preferred_hwnd = preferred_hwnd or (lambda: None)
        self.locked_hwnd = locked_hwnd or (lambda: None)
        self.lock_active = lock_active or (lambda: False)
        self.logger = logger
        self.current_image = None
        self.target_hwnd = None
        self.has_found_valid_target = False
        self.blocked_exact_titles = BLOCKED_WINDOW_TITLES
        self.region_index_cache = {}
        self.last_stable_index = []
        self.last_update_at = 0.0
        self.last_forced_ocr_at = 0.0

    def run(self):
        """Keep OCR results fresh until the application exits."""
        while not self.stop_event.is_set():
            try:
                cycle_started_at = time.perf_counter()
                self._update_target_window()
                capture_started_at = time.perf_counter()
                image, rect = self._capture_target_window()
                capture_ms = (time.perf_counter() - capture_started_at) * 1000.0
                if image is None:
                    self.stop_event.wait(SCAN_INTERVAL_MS / 1000.0)
                    continue

                if not self.has_found_valid_target:
                    self.has_found_valid_target = True

                change_started_at = time.perf_counter()
                changed_regions = get_changed_regions(
                    self.current_image,
                    image,
                    grid=CHANGE_GRID,
                    threshold=CHANGE_THRESHOLD,
                    thumb_size=CHANGE_THUMB_SIZE,
                )
                change_detection_ms = (time.perf_counter() - change_started_at) * 1000.0
                total_regions = CHANGE_GRID[0] * CHANGE_GRID[1]
                now = time.monotonic()
                force_refresh = (
                    self.last_forced_ocr_at == 0.0
                    or now - self.last_forced_ocr_at >= (FORCED_OCR_INTERVAL_MS / 1000.0)
                )
                if not changed_regions and not force_refresh:
                    self.logger.debug("No significant change detected regions_changed=0/%s", total_regions)
                    self.current_image = image
                    self.stop_event.wait(SCAN_INTERVAL_MS / 1000.0)
                    continue

                if force_refresh and not changed_regions:
                    changed_regions = [
                        {
                            "left": 0,
                            "top": 0,
                            "width": image.width,
                            "height": image.height,
                        }
                    ]
                    self.logger.debug("Forced OCR refresh triggered regions_changed=1/%s", total_regions)
                else:
                    self.logger.debug(
                        "Detected changed regions regions_changed=%s/%s",
                        len(changed_regions),
                        total_regions,
                    )
                if self._is_major_change(changed_regions, total_regions):
                    self.index_queue.put(
                        {
                            "type": "refreshing",
                            "changed_regions": len(changed_regions),
                            "total_regions": total_regions,
                        }
                    )
                self.current_image = image
                if now - self.last_update_at < (OCR_UPDATE_DEBOUNCE_MS / 1000.0):
                    total_cycle_ms = (time.perf_counter() - cycle_started_at) * 1000.0
                    self.logger.debug(
                        "Skipped OCR update because debounce window is still active capture_ms=%.1f change_ms=%.1f total_cycle_ms=%.1f",
                        capture_ms,
                        change_detection_ms,
                        total_cycle_ms,
                    )
                    self.stop_event.wait(SCAN_INTERVAL_MS / 1000.0)
                    continue

                full_window = True
                if (
                    PARTIAL_OCR_ENABLED
                    and not force_refresh
                    and not self._is_major_change(changed_regions, total_regions)
                    and self.last_stable_index
                ):
                    index, timing, full_window = self._build_incremental_index(image, rect, changed_regions)
                else:
                    index, timing = self._build_full_index(image, rect)
                    full_window = True
                index = self._stabilize_index(index)
                if index is None:
                    self.logger.info("Discarded unstable OCR frame and kept the last stable index")
                    self.stop_event.wait(SCAN_INTERVAL_MS / 1000.0)
                    continue

                self.last_stable_index = index
                self.last_update_at = now
                self.last_forced_ocr_at = now
                total_cycle_ms = (time.perf_counter() - cycle_started_at) * 1000.0
                self.logger.info(
                    "Published OCR index full_window=%s changed_regions=%s total_words=%s capture_ms=%.1f change_ms=%.1f ocr_ms=%.1f index_ms=%.1f total_cycle_ms=%.1f",
                    1 if full_window else 0,
                    len(changed_regions),
                    len(index),
                    capture_ms,
                    change_detection_ms,
                    timing["ocr_ms"],
                    timing["index_ms"],
                    total_cycle_ms,
                )
                self.index_queue.put({"type": "index", "index": index})
            except Exception:
                self.logger.exception("OCR thread failed while updating the index.")

            self.stop_event.wait(SCAN_INTERVAL_MS / 1000.0)

    def _update_target_window(self):
        """Track the last foreground window that does not belong to Uniseba."""
        hwnd = self._normalize_hwnd(win32gui.GetForegroundWindow())
        if not self.has_found_valid_target:
            if hwnd and self._is_bootstrap_target(hwnd):
                self.target_hwnd = hwnd
                self.logger.info("Selected bootstrap OCR target hwnd=%s title=%r", hwnd, win32gui.GetWindowText(hwnd))
                return
            preferred = self._normalize_hwnd(self.preferred_hwnd())
            if preferred and self._is_bootstrap_target(preferred):
                self.target_hwnd = preferred
                self.logger.info(
                    "Selected preferred bootstrap OCR target hwnd=%s title=%r",
                    preferred,
                    win32gui.GetWindowText(preferred),
                )
            return

        if hwnd and self._is_valid_target(hwnd):
            self.target_hwnd = hwnd
            self.logger.info("Selected OCR target hwnd=%s title=%r", hwnd, win32gui.GetWindowText(hwnd))
            return
        preferred = self._normalize_hwnd(self.preferred_hwnd())
        if preferred and self._is_valid_target(preferred):
            self.target_hwnd = preferred
            self.logger.info("Selected preferred OCR target hwnd=%s title=%r", preferred, win32gui.GetWindowText(preferred))

    def _is_bootstrap_target(self, hwnd):
        """Allow almost any visible non-minimized window until OCR starts once."""
        if not hwnd or not win32gui.IsWindow(hwnd) or win32gui.IsIconic(hwnd):
            self.logger.debug("Rejected bootstrap target hwnd=%s because it is invalid or minimized", hwnd)
            return False
        if hwnd in self.excluded_hwnds():
            self.logger.debug("Rejected bootstrap target hwnd=%s because it belongs to Uniseba", hwnd)
            return False
        class_name = win32gui.GetClassName(hwnd)
        if class_name in {"Progman", "WorkerW"}:
            self.logger.debug(
                "Rejected bootstrap target hwnd=%s class=%r because it is a desktop shell window",
                hwnd,
                class_name,
                título=class_name,
            )
            return False
        raw_title = win32gui.GetWindowText(hwnd).strip()
        if not raw_title:
            self.logger.debug("Rejected bootstrap target hwnd=%s because the title is empty", hwnd)
            return False
        title = raw_title.lower()
        if DESKTOP_WINDOW_KEYWORD in title:
            self.logger.debug("Rejected bootstrap target hwnd=%s title=%r because it is the desktop", hwnd, title)
            return False
        if title in self.blocked_exact_titles or title.startswith(BLOCKED_WINDOW_PREFIXES):
            self.logger.debug("Rejected bootstrap target hwnd=%s title=%r because it is blocked", hwnd, title)
            return False
        rect = self._get_full_window_rect(hwnd)
        if rect is None:
            self.logger.debug("Rejected bootstrap target hwnd=%s because it has an invalid size", hwnd)
            return False
        return True

    def _is_valid_target(self, hwnd):
        """Reject invalid, minimized, or known Uniseba/debug windows."""
        if not hwnd or not win32gui.IsWindow(hwnd) or win32gui.IsIconic(hwnd):
            self.logger.debug("Rejected OCR target hwnd=%s because it is invalid or minimized", hwnd)
            return False
        if hwnd in self.excluded_hwnds():
            self.logger.debug("Rejected OCR target hwnd=%s because it belongs to Uniseba", hwnd)
            return False
        class_name = win32gui.GetClassName(hwnd)
        if class_name in {"Progman", "WorkerW"}:
            self.logger.debug(
                "Rejected OCR target hwnd=%s class=%r because it is a desktop shell window",
                hwnd,
                class_name,
            )
            return False
        raw_title = win32gui.GetWindowText(hwnd).strip()
        if len(raw_title) < MIN_TARGET_TITLE_LENGTH:
            self.logger.debug("Rejected OCR target hwnd=%s because the title is too short", hwnd)
            return False
        title = raw_title.lower()
        if DESKTOP_WINDOW_KEYWORD in title:
            self.logger.debug("Rejected OCR target hwnd=%s title=%r because it is the desktop", hwnd, title)
            return False
        class_name = class_name.lower()
        if title in self.blocked_exact_titles or title.startswith(BLOCKED_WINDOW_PREFIXES):
            self.logger.debug("Rejected OCR target hwnd=%s title=%r because it is blocked", hwnd, title)
            return False
        if class_name == "consolewindowclass" and any(keyword in title for keyword in BLOCKED_CONSOLE_KEYWORDS):
            self.logger.debug(
                "Rejected OCR target hwnd=%s class=%r title=%r because it is a blocked console window",
                hwnd,
                class_name,
                title,
            )
            return False
        rect = self._get_full_window_rect(hwnd)
        if rect is None:
            self.logger.debug("Rejected OCR target hwnd=%s because it has an invalid size", hwnd)
            return False
        width = rect["width"]
        height = rect["height"]
        if width < MIN_TARGET_WIDTH or height < MIN_TARGET_HEIGHT:
            self.logger.debug("Rejected OCR target hwnd=%s because the window is too small size=%sx%s", hwnd, width, height)
            return False
        return True

    def _capture_target_window(self):
        """Capture the tracked foreground window using absolute screen coordinates."""
        hwnd = self._normalize_hwnd(self.target_hwnd)
        if not self.has_found_valid_target:
            if not self._is_bootstrap_target(hwnd):
                return None, None
        elif not self._is_valid_target(hwnd):
            return None, None

        rect = self._get_full_window_rect(hwnd)
        if rect is None:
            return None, None

        width = rect["width"]
        height = rect["height"]
        self.logger.debug("Capturing OCR target region width=%s height=%s", width, height)
        if not self.has_found_valid_target:
            self.logger.debug(
                "Bootstrap capturing OCR target hwnd=%s title=%r rect=%s",
                hwnd,
                win32gui.GetWindowText(hwnd),
                rect,
            )
        else:
            self.logger.debug(
                "Capturing OCR target hwnd=%s title=%r rect=%s",
                hwnd,
                win32gui.GetWindowText(hwnd),
                rect,
            )
        with mss() as sct:
            shot = sct.grab(rect)
            image = Image.frombytes("RGB", shot.size, shot.rgb)
        image = self._mask_excluded_regions(image, rect)
        return image, rect

    def _mask_excluded_regions(self, image, capture_rect):
        """Black out our own floating search UI if it overlaps the captured content."""
        exclusion_rects = self._expanded_exclusion_rects()
        if not exclusion_rects:
            return image

        draw = ImageDraw.Draw(image)
        capture_left = capture_rect["left"]
        capture_top = capture_rect["top"]
        capture_right = capture_left + capture_rect["width"]
        capture_bottom = capture_top + capture_rect["height"]

        for rect in exclusion_rects:
            left = max(rect["left"], capture_left)
            top = max(rect["top"], capture_top)
            right = min(rect["right"], capture_right)
            bottom = min(rect["bottom"], capture_bottom)
            if right <= left or bottom <= top:
                continue
            draw.rectangle(
                (
                    left - capture_left,
                    top - capture_top,
                    right - capture_left,
                    bottom - capture_top,
                ),
                fill="black",
            )
        return image

    def _expanded_exclusion_rects(self):
        """Pad self-UI exclusion rectangles so OCR also misses border/shadow bleed."""
        rects = self.exclusion_rects() or []
        if not rects:
            return []
        expanded = []
        for rect in rects:
            expanded.append(
                {
                    "left": rect["left"] - SEARCH_UI_EXCLUSION_PADDING,
                    "top": rect["top"] - SEARCH_UI_EXCLUSION_PADDING,
                    "right": rect["right"] + SEARCH_UI_EXCLUSION_PADDING,
                    "bottom": rect["bottom"] + SEARCH_UI_EXCLUSION_PADDING,
                }
            )
        return expanded

    def _normalize_hwnd(self, hwnd):
        """Promote child/owned windows to their top-level root window before capture."""
        if not hwnd or not win32gui.IsWindow(hwnd):
            return hwnd
        root = win32gui.GetAncestor(hwnd, win32con.GA_ROOT)
        return root or hwnd

    def _get_full_window_rect(self, hwnd):
        """Return the full top-level window bounds for OCR capture."""
        if not hwnd or not win32gui.IsWindow(hwnd):
            return None
        try:
            client_left, client_top = win32gui.ClientToScreen(hwnd, (0, 0))
            left2, top2, right2, bottom2 = win32gui.GetClientRect(hwnd)
            width = right2 - left2
            height = bottom2 - top2
        except Exception:
            return None
        if width <= 0 or height <= 0:
            return None
        return {"left": client_left, "top": client_top, "width": width, "height": height}

    def _is_major_change(self, changed_regions, total_regions):
        """Flag scroll/page transitions so the UI can avoid showing stale results as current."""
        changed_count = len(changed_regions)
        if changed_count >= MAJOR_CHANGE_REGION_COUNT:
            return True
        if total_regions <= 0:
            return False
        return (changed_count / float(total_regions)) >= MAJOR_CHANGE_REGION_RATIO

    def _build_full_index(self, image, rect):
        """Run OCR on the full captured window so geometry can be validated end to end."""
        ocr_started_at = time.perf_counter()
        words = recognize_image(image, rect)
        ocr_ms = (time.perf_counter() - ocr_started_at) * 1000.0
        index_started_at = time.perf_counter()
        index = build_ocr_index(words)
        index = self._filter_excluded_index_items(index)
        index_ms = (time.perf_counter() - index_started_at) * 1000.0
        return index, {"ocr_ms": ocr_ms, "index_ms": index_ms}

    def _build_incremental_index(self, image, rect, changed_regions):
        """OCR only changed regions and merge into the last stable index."""
        merged_regions = self._merge_changed_regions(changed_regions, image.width, image.height)
        if not merged_regions:
            return self._build_full_index(image, rect) + (True,)

        image_area = max(1, int(image.width) * int(image.height))
        merged_area = sum((r["right"] - r["left"]) * (r["bottom"] - r["top"]) for r in merged_regions)
        if len(merged_regions) > PARTIAL_OCR_MAX_RECTS or (merged_area / float(image_area)) > PARTIAL_OCR_MAX_AREA_RATIO:
            return self._build_full_index(image, rect) + (True,)

        ocr_started_at = time.perf_counter()
        new_entries = []
        for region in merged_regions:
            crop = image.crop((region["left"], region["top"], region["right"], region["bottom"]))
            crop = self._prepare_region_image(crop)
            words = recognize_image(
                crop,
                {
                    "left": rect["left"] + region["left"],
                    "top": rect["top"] + region["top"],
                },
            )
            region_index = build_ocr_index(words)
            region_index = self._filter_excluded_index_items(region_index)
            new_entries.extend(region_index)
        ocr_ms = (time.perf_counter() - ocr_started_at) * 1000.0

        index_started_at = time.perf_counter()
        abs_regions = []
        for region in merged_regions:
            abs_regions.append(
                {
                    "left": rect["left"] + region["left"],
                    "top": rect["top"] + region["top"],
                    "right": rect["left"] + region["right"],
                    "bottom": rect["top"] + region["bottom"],
                }
            )

        def overlaps_any(item):
            left = item["x"]
            top = item["y"]
            right = left + item["w"]
            bottom = top + item["h"]
            for r in abs_regions:
                if right <= r["left"] or left >= r["right"] or bottom <= r["top"] or top >= r["bottom"]:
                    continue
                return True
            return False

        merged = [item for item in self.last_stable_index if not overlaps_any(item)]
        merged.extend(new_entries)
        seen = set()
        deduped = []
        for item in merged:
            key = (item.get("x"), item.get("y"), item.get("w"), item.get("h"), item.get("original", ""))
            if key in seen:
                continue
            seen.add(key)
            deduped.append(item)
        index_ms = (time.perf_counter() - index_started_at) * 1000.0
        return deduped, {"ocr_ms": ocr_ms, "index_ms": index_ms}, False

    def _merge_changed_regions(self, changed_regions, width, height):
        """Merge overlapping/adjacent change rectangles into a few OCR crops."""
        if not changed_regions:
            return []

        rects = []
        for region in changed_regions:
            left = max(0, int(region.get("left", 0)) - PARTIAL_OCR_PADDING_PX)
            top = max(0, int(region.get("top", 0)) - PARTIAL_OCR_PADDING_PX)
            right = min(width, left + int(region.get("width", 0)) + (2 * PARTIAL_OCR_PADDING_PX))
            bottom = min(height, top + int(region.get("height", 0)) + (2 * PARTIAL_OCR_PADDING_PX))
            if right <= left or bottom <= top:
                continue
            rects.append({"left": left, "top": top, "right": right, "bottom": bottom})

        rects.sort(key=lambda r: (r["left"], r["top"]))
        merged = []
        for r in rects:
            placed = False
            for target in merged:
                if (
                    r["right"] < target["left"]
                    or r["left"] > target["right"]
                    or r["bottom"] < target["top"]
                    or r["top"] > target["bottom"]
                ):
                    continue
                target["left"] = min(target["left"], r["left"])
                target["top"] = min(target["top"], r["top"])
                target["right"] = max(target["right"], r["right"])
                target["bottom"] = max(target["bottom"], r["bottom"])
                placed = True
                break
            if not placed:
                merged.append(dict(r))
        return merged

    def _filter_excluded_index_items(self, index):
        """Drop OCR items that overlap our search UI or clearly repeat self-UI phrases."""
        exclusion_rects = self._expanded_exclusion_rects()
        filtered = []
        for item in index:
            original = str(item.get("original", "")).strip().lower()
            if any(phrase in original for phrase in SELF_UI_PHRASES):
                continue
            if exclusion_rects:
                left = item["x"]
                top = item["y"]
                right = left + item["w"]
                bottom = top + item["h"]
                overlaps = False
                for rect in exclusion_rects:
                    if right <= rect["left"] or left >= rect["right"] or bottom <= rect["top"] or top >= rect["bottom"]:
                        continue
                    overlaps = True
                    break
                if overlaps:
                    continue
            filtered.append(item)
        return filtered

    def _prepare_region_image(self, image):
        """Slightly downscale OCR regions so partial passes stay lightweight."""
        if OCR_DOWNSCALE >= 0.99:
            return image
        width = max(1, int(image.width * OCR_DOWNSCALE))
        height = max(1, int(image.height * OCR_DOWNSCALE))
        return image.resize((width, height), Image.Resampling.LANCZOS)

    def _stabilize_index(self, new_index):
        """Temporary safe mode: trust the newest OCR frame without smoothing."""
        return new_index

    def _find_previous_match(self, item, candidates):
        """Find the closest prior word with the same normalized text."""
        if not candidates:
            return None
        return min(
            candidates,
            key=lambda candidate: abs(candidate["x"] - item["x"]) + abs(candidate["y"] - item["y"]),
        )
