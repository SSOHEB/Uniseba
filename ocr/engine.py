"""EasyOCR-based OCR wrapper."""

import easyocr
import logging
import numpy as np
import torch

from capture.screen import capture_active_window
from ocr.index import build_ocr_index

logger = logging.getLogger("uniseba.ocr.engine")

gpu_available = torch.cuda.is_available()
reader = easyocr.Reader(
    ["en"],
    gpu=gpu_available,
    model_storage_directory=None,
    download_enabled=True,
    verbose=False,
)
logger.info("EasyOCR initialized on %s", "GPU" if gpu_available else "CPU")


def recognize_image(image, window_rect=None, min_height=8):
    """Run OCR on a PIL image and return filtered words with absolute boxes."""
    numpy_image = np.array(image)
    results = reader.readtext(numpy_image, detail=1, paragraph=False)
    offset_x = 0 if window_rect is None else window_rect["left"]
    offset_y = 0 if window_rect is None else window_rect["top"]
    words = []

    for bbox, text, confidence in results:
        if confidence < 0.3:
            continue
        xs = [point[0] for point in bbox]
        ys = [point[1] for point in bbox]
        x = int(min(xs))
        y = int(min(ys))
        w = int(max(xs) - min(xs))
        h = int(max(ys) - min(ys))
        if h < min_height:
            continue
        words.append(
            {
                "text": text,
                "x": int(offset_x + x),
                "y": int(offset_y + y),
                "w": w,
                "h": h,
            }
        )

    return words


def _run_test():
    """Capture the active window, run OCR, and print word boxes."""
    image, rect = capture_active_window()
    if image is None:
        print("No active window found.")
        return

    words = recognize_image(image, rect)
    index = build_ocr_index(words)
    for item in index:
        print(f"{item['original']}: ({item['x']}, {item['y']}, {item['w']}, {item['h']})")


if __name__ == "__main__":
    _run_test()
