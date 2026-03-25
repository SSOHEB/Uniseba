"""In-memory OCR index helpers."""

import logging

logger = logging.getLogger("uniseba.ocr.index")


def _is_meaningful_word(text, height):
    """Keep digits, but drop tiny boxes and low-value one-character OCR noise."""
    cleaned = text.strip()
    if not cleaned or int(height) < 8:
        return False
    if len(cleaned) == 1 and not cleaned.isdigit():
        return False
    return True


def build_ocr_index(words):
    """Normalize OCR words into a simple in-memory list of dicts."""
    index = []
    filtered_out = 0
    for word in words:
        text = word["text"].strip()
        height = int(word["h"])
        if not _is_meaningful_word(text, height):
            filtered_out += 1
            continue
        confidence = round(min(1.0, max(height, 8) / 32.0), 2)
        index.append(
            {
                "word": text.lower(),
                "original": text,
                "x": int(word["x"]),
                "y": int(word["y"]),
                "w": int(word["w"]),
                "h": height,
                "confidence": confidence,
            }
        )
    logger.debug("Normalized OCR index kept=%s filtered_out=%s", len(index), filtered_out)
    return index
