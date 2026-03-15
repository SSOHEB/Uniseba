"""Phase 1 test: capture the current foreground window to a PNG file."""

import ctypes

# Set DPI awareness first so window coordinates match the captured pixels.
ctypes.windll.user32.SetProcessDPIAware()

from mss import mss
from PIL import Image
import win32gui


def main() -> None:
    """Capture the active window and save it as test_capture.png."""
    hwnd = win32gui.GetForegroundWindow()
    if not hwnd:
        print("No active window found.")
        return

    left, top, right, bottom = win32gui.GetWindowRect(hwnd)
    width, height = right - left, bottom - top
    if width <= 0 or height <= 0:
        print("Active window has an invalid size.")
        return

    rect = {"left": left, "top": top, "width": width, "height": height}
    with mss() as sct:
        shot = sct.grab(rect)
        image = Image.frombytes("RGB", shot.size, shot.rgb)
        image.save("test_capture.png")

    print(f"Active window rect: {left}, {top}, {right}, {bottom}")
    print("Saved test_capture.png successfully.")


if __name__ == "__main__":
    main()
