"""In-memory OCR index helpers."""

import logging

logger = logging.getLogger("uniseba.ocr.index")


def _passes_base_filters(text, height):
    """Reject empty, tiny, or obviously self-generated OCR noise."""
    cleaned = text.strip()
    if not cleaned or int(height) < 8:
        return False
    lowered = cleaned.lower()
    if "word='" in lowered or "[searchbar]" in lowered or "[filter]" in lowered or "[draw" in lowered:
        return False
    return True


def _is_meaningful_word(text, height):
    """Keep digits, but drop tiny boxes and low-value one-character OCR noise."""
    cleaned = text.strip()
    if not _passes_base_filters(cleaned, height):
        return False
    if len(cleaned) > 40:
        return False
    if cleaned.count(" ") > 3:
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
        if not _passes_base_filters(text, height):
            filtered_out += 1
            continue
        confidence = round(min(1.0, max(height, 8) / 32.0), 2)
        entry = {
            "word": text.lower(),
            "original": text,
            "x": int(word["x"]),
            "y": int(word["y"]),
            "w": int(word["w"]),
            "h": height,
            "confidence": confidence,
        }
        if len(entry["original"]) > 25 and " " in entry["original"]:
            words_in_entry = entry["original"].split()
            total_words = len(words_in_entry)
            for i, split_word in enumerate(words_in_entry):
                clean = split_word.strip(".,;:()[]\"'")
                if not clean or len(clean) < 2:
                    continue
                if not _is_meaningful_word(clean, entry["h"]):
                    continue
                word_x = int(entry["x"] + (i / total_words) * entry["w"])
                word_w = int(entry["w"] / total_words)
                index.append(
                    {
                        "word": clean.lower(),
                        "original": clean,
                        "x": word_x,
                        "y": entry["y"],
                        "w": word_w,
                        "h": entry["h"],
                        "confidence": entry["confidence"],
                    }
                )
            continue
        if not _is_meaningful_word(text, height):
            filtered_out += 1
            continue
        index.append(entry)
    logger.debug("Normalized OCR index kept=%s filtered_out=%s", len(index), filtered_out)
    logger.debug("[INDEX] kept=%s filtered=%s", len(index), filtered_out)
    for item in index[:5]:
        logger.debug(
            "  %r conf=%s at (%s,%s)",
            item["original"],
            item["confidence"],
            item["x"],
            item["y"],
        )
    return index
