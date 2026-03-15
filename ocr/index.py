"""In-memory OCR index helpers."""


def build_ocr_index(words):
    """Normalize OCR words into a simple in-memory list of dicts."""
    index = []
    for word in words:
        height = int(word["h"])
        confidence = round(min(1.0, max(height, 8) / 32.0), 2)
        index.append(
            {
                "word": word["text"].lower(),
                "original": word["text"],
                "x": int(word["x"]),
                "y": int(word["y"]),
                "w": int(word["w"]),
                "h": height,
                "confidence": confidence,
            }
        )
    return index
