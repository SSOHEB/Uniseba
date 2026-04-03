"""Run EasyOCR directly against a saved crop and write raw results to a file."""

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

import easyocr
import numpy as np
from PIL import Image

logger = logging.getLogger("uniseba.tools.ocr_easyocr_test")


def main():
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    for handler in list(root.handlers):
        root.removeHandler(handler)
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    root.addHandler(stream_handler)
    file_handler = RotatingFileHandler(
        "ocr_easyocr_test.log",
        maxBytes=1_000_000,
        backupCount=2,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    root.addHandler(file_handler)

    image_path = Path("test_crop.png")
    output_path = Path("ocr_test_output.txt")

    if not image_path.exists():
        raise FileNotFoundError(f"Missing test crop: {image_path}")

    reader = easyocr.Reader(["en"], gpu=True, verbose=False)
    image = Image.open(image_path)
    results = reader.readtext(np.array(image), detail=1)

    lines = []
    for bbox, text, conf in results:
        serializable_bbox = [[int(point[0]), int(point[1])] for point in bbox]
        lines.append(f"conf={conf:.3f} text={text!r} bbox={serializable_bbox}")

    output_path.write_text("\n".join(lines), encoding="utf-8")
    logger.info("Wrote %s OCR results to %s", len(lines), output_path)


if __name__ == "__main__":
    main()
