"""Background OCR worker for continuously updating the visible text index."""

import asyncio
import logging
import threading
from queue import Queue

import config
from mss import mss
from PIL import Image
import win32gui

from capture.change import has_significant_change
from ocr.engine import recognize_image
from ocr.index import build_ocr_index

SCAN_INTERVAL_MS = getattr(config, "SCAN_INTERVAL_MS", 200)
MIN_TARGET_WIDTH = 300
MIN_TARGET_HEIGHT = 200


class OCRThread(threading.Thread):
    """Capture the current target window, OCR it, and push updated indexes."""

    def __init__(
        self,
        index_queue: Queue,
        stop_event: threading.Event,
        excluded_hwnds=None,
        preferred_hwnd=None,
    ):
        super().__init__(daemon=True, name="UnisebaOCR")
        self.index_queue = index_queue
        self.stop_event = stop_event
        self.excluded_hwnds = excluded_hwnds or (lambda: set())
        self.preferred_hwnd = preferred_hwnd or (lambda: None)
        self.logger = logging.getLogger("uniseba")
        self.current_image = None
        self.target_hwnd = None
        self.blocked_title_tokens = ("powershell", "uniseba", "debug", "python")

    def run(self):
        """Keep OCR results fresh until the application exits."""
        while not self.stop_event.is_set():
            try:
                self._update_target_window()
                image, rect = self._capture_target_window()
                if image is None:
                    self.stop_event.wait(SCAN_INTERVAL_MS / 1000.0)
                    continue

                changed = has_significant_change(self.current_image, image)
                if not changed:
                    print("[CHANGE] no change -> skipping OCR")
                    self.stop_event.wait(SCAN_INTERVAL_MS / 1000.0)
                    continue

                print("[CHANGE] detected -> running OCR")
                self.current_image = image
                words = asyncio.run(recognize_image(image, rect))
                index = build_ocr_index(words)
                print(f"[OCR] words extracted: {len(index)}")
                if len(index) > 0:
                    print("[OCR SAMPLE]", index[:5])
                print(f"[ocr_thread] queue put index words={len(index)} rect={rect}")
                self.index_queue.put(index)
            except Exception:
                self.logger.exception("OCR thread failed while updating the index.")

            self.stop_event.wait(SCAN_INTERVAL_MS / 1000.0)

    def _update_target_window(self):
        """Track the last foreground window that does not belong to Uniseba."""
        preferred = self.preferred_hwnd()
        if preferred and self._is_valid_target(preferred):
            self.target_hwnd = preferred
            print(f"[OCR TARGET] preferred hwnd={preferred} title={win32gui.GetWindowText(preferred)!r}")
            return
        hwnd = win32gui.GetForegroundWindow()
        if hwnd and self._is_valid_target(hwnd):
            self.target_hwnd = hwnd
            print(f"[OCR TARGET] foreground hwnd={hwnd} title={win32gui.GetWindowText(hwnd)!r}")
            return
        if self.target_hwnd and self._is_valid_target(self.target_hwnd):
            print(f"[OCR TARGET] fallback to last valid hwnd={self.target_hwnd} title={win32gui.GetWindowText(self.target_hwnd)!r}")

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
        if any(token in title for token in self.blocked_title_tokens):
            print(f"[OCR TARGET] skipped blocked title hwnd={hwnd} title={title!r}")
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
        if not self._is_valid_target(hwnd):
            return None, None

        left, top, right, bottom = win32gui.GetWindowRect(hwnd)
        width, height = right - left, bottom - top
        if width <= 0 or height <= 0:
            return None, None

        rect = {"left": left, "top": top, "width": width, "height": height}
        print(f"[OCR TARGET] capturing hwnd={hwnd} title={win32gui.GetWindowText(hwnd)!r} rect={rect}")
        with mss() as sct:
            shot = sct.grab(rect)
            image = Image.frombytes("RGB", shot.size, shot.rgb)
        return image, rect
