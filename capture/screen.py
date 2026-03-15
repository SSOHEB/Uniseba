"""Active-window screen capture helpers for Phase 2."""

import ctypes

# Keep DPI awareness at module load so Win32 rects match captured pixels.
ctypes.windll.user32.SetProcessDPIAware()

from mss import mss
from PIL import Image
import win32gui


def capture_active_window():
    """Return the active window as a PIL image plus its absolute rect."""
    hwnd = win32gui.GetForegroundWindow()
    if not hwnd:
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
