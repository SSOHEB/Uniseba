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

    def run(self):
        """Keep OCR results fresh until the application exits."""
        while not self.stop_event.is_set():
            try:
                self._update_target_window()
                image, rect = self._capture_target_window()
                if image is not None and has_significant_change(self.current_image, image):
                    self.current_image = image
                    words = asyncio.run(recognize_image(image, rect))
                    index = build_ocr_index(words)
                    print(f"[ocr_thread] queue put index words={len(index)} rect={rect}")
                    self.index_queue.put(index)
            except Exception:
                self.logger.exception("OCR thread failed while updating the index.")

            self.stop_event.wait(SCAN_INTERVAL_MS / 1000.0)

    def _update_target_window(self):
        """Track the last foreground window that does not belong to Uniseba."""
        preferred = self.preferred_hwnd()
        if preferred and preferred not in self.excluded_hwnds() and win32gui.IsWindow(preferred):
            self.target_hwnd = preferred
            return
        hwnd = win32gui.GetForegroundWindow()
        if hwnd and hwnd not in self.excluded_hwnds():
            self.target_hwnd = hwnd

    def _capture_target_window(self):
        """Capture the tracked foreground window using absolute screen coordinates."""
        hwnd = self.target_hwnd
        if not hwnd or not win32gui.IsWindow(hwnd):
            return None, None

        left, top, right, bottom = win32gui.GetWindowRect(hwnd)
        width, height = right - left, bottom - top
        if width <= 0 or height <= 0:
            return None, None

        rect = {"left": left, "top": top, "width": width, "height": height}
        with mss() as sct:
            shot = sct.grab(rect)
            image = Image.frombytes("RGB", shot.size, shot.rgb)
        return image, rect
