"""Run EasyOCR directly against a saved crop and write raw results to a file."""

from pathlib import Path

import easyocr
import numpy as np
from PIL import Image


def main():
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
    print(f"Wrote {len(lines)} OCR results to {output_path}")


if __name__ == "__main__":
    main()
