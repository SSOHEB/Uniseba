"""EasyOCR-based OCR wrapper."""

import logging
import numpy as np
import torch
import easyocr
from PIL import Image as PILImage

from config import RECORDING_PREPROCESS
from capture.screen import capture_active_window
from ocr.index import build_ocr_index

try:
    import cv2
    PREPROCESSING_AVAILABLE = True
except ImportError:
    cv2 = None
    PREPROCESSING_AVAILABLE = False
    logging.getLogger("uniseba.ocr").warning(
        "cv2 not available — image preprocessing "
        "disabled. Install opencv-python to enable."
    )

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


def preprocess_for_ocr(image):
    """
    Convert any screen capture to clean
    black-on-white for improved OCR accuracy.

    Pipeline:
      grayscale → CLAHE → Otsu binarization
      → 2x upscale

    Only used in recording mode.
    Falls back to original image on any failure.
    """
    if not PREPROCESSING_AVAILABLE:
        logger.warning(
            "Preprocessing requested but cv2 "
            "unavailable — returning original image"
        )
        return image
    try:
        arr = np.array(image)

        # Handle RGBA — strip alpha channel
        if arr.ndim == 3 and arr.shape[2] == 4:
            arr = cv2.cvtColor(arr, cv2.COLOR_RGBA2RGB)

        # Convert to grayscale
        if arr.ndim == 3:
            gray = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY)
        else:
            gray = arr

        # CLAHE contrast enhancement
        clahe = cv2.createCLAHE(
            clipLimit=2.0,
            tileGridSize=(8, 8)
        )
        enhanced = clahe.apply(gray)

        # Otsu binarization
        _, binary = cv2.threshold(
            enhanced, 0, 255,
            cv2.THRESH_BINARY + cv2.THRESH_OTSU
        )

        # Low contrast guard — if result is
        # >95% one color, binarization failed
        # Use enhanced grayscale instead
        white_ratio = np.sum(binary == 255) / binary.size
        if white_ratio > 0.95 or white_ratio < 0.05:
            logger.debug(
                "Otsu produced flat image "
                "(white_ratio=%.2f) — "
                "using enhanced grayscale",
                white_ratio
            )
            working = enhanced
        else:
            working = binary

        # 2x upscale — cap at 3000px either dimension
        h, w = working.shape
        if h * 2 <= 3000 and w * 2 <= 3000:
            scaled = cv2.resize(
                working, None,
                fx=2, fy=2,
                interpolation=cv2.INTER_CUBIC
            )
        else:
            logger.debug(
                "Skipping upscale — "
                "image too large after 2x: %dx%d",
                w * 2, h * 2
            )
            scaled = working

        # Convert back to PIL RGB
        rgb = cv2.cvtColor(scaled, cv2.COLOR_GRAY2RGB)
        return PILImage.fromarray(rgb)

    except Exception as e:
        logger.warning(
            "preprocess_for_ocr failed: %s — "
            "returning original image", e
        )
        return image


def recognize_image(
    image,
    window_rect=None,
    min_height=8,
    preprocess=False
):
    """Run OCR on a PIL image and return filtered words with absolute boxes."""
    if preprocess and RECORDING_PREPROCESS:
        image = preprocess_for_ocr(image)

    scale = 1
    # Upscaling can improve OCR on very small captures, but it makes full-window OCR
    # dramatically slower. Only upscale genuinely small images.
    if image.height < 600 and (image.width * image.height) < 900_000:
        scale = 2
        image = image.resize((image.width * scale, image.height * scale), PILImage.LANCZOS)

    numpy_image = np.array(image)
    results = reader.readtext(numpy_image, detail=1, paragraph=False)
    offset_x = 0 if window_rect is None else window_rect["left"]
    offset_y = 0 if window_rect is None else window_rect["top"]
    words = []

    for result in results:
        try:
            bbox, text, confidence = result
        except ValueError:
            if len(result) < 2:
                continue
            bbox, text = result[:2]
            confidence = 0.0
        try:
            ocr_confidence = float(confidence)
        except (TypeError, ValueError):
            ocr_confidence = 0.0
        if ocr_confidence < 0.15:
            continue
        xs = [point[0] for point in bbox]
        ys = [point[1] for point in bbox]
        x = int(min(xs) / scale)
        y = int(min(ys) / scale)
        w = int((max(xs) - min(xs)) / scale)
        h = int((max(ys) - min(ys)) / scale)
        if h < min_height:
            continue
        words.append(
            {
                "text": text,
                "x": int(offset_x + x),
                "y": int(offset_y + y),
                "w": w,
                "h": h,
                "ocr_confidence": ocr_confidence,
            }
        )

    logger.debug("[OCR] words_found=%s gpu=%s", len(words), torch.cuda.is_available())
    for w in words[:5]:
        logger.debug(
            "  word=%r conf=%s x=%s y=%s w=%s h=%s",
            w["text"],
            w.get("ocr_confidence", "N/A"),
            w["x"],
            w["y"],
            w["w"],
            w["h"],
        )

    return words


def _run_test():
    """Capture the active window, run OCR, and print word boxes."""
    image, rect = capture_active_window()
    if image is None:
        logger.debug("No active window found.")
        return

    words = recognize_image(image, rect)
    index = build_ocr_index(words)
    for item in index:
        logger.debug(
            "%s: (%s, %s, %s, %s)",
            item["original"],
            item["x"],
            item["y"],
            item["w"],
            item["h"],
        )


if __name__ == "__main__":
    _run_test()
