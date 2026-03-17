"""RapidFuzz-based search helpers."""

from rapidfuzz import fuzz, process

import config

MIN_QUERY_LENGTH = getattr(config, "MIN_QUERY_LENGTH", 2)
FUZZY_THRESHOLD = max(90, getattr(config, "FUZZY_THRESHOLD", 75))
MAX_RESULTS = getattr(config, "MAX_RESULTS", 50)
MIN_WORD_LENGTH = 3
MIN_CONFIDENCE = 0.4


def is_viable_search_word(query, entry):
    """Reject OCR noise before fuzzy matching."""
    word = entry["word"]
    if len(word) < MIN_WORD_LENGTH:
        print(f"[FILTER] rejected word='{word}' reason=too_short")
        return False
    if entry.get("confidence", 1.0) < MIN_CONFIDENCE:
        print(f"[FILTER] rejected word='{word}' reason=low_confidence")
        return False
    if abs(len(word) - len(query)) > max(2, len(query) // 2):
        print(f"[FILTER] rejected word='{word}' reason=length_mismatch")
        return False
    return True


def fuzzy_search(query, index, limit=MAX_RESULTS, threshold=FUZZY_THRESHOLD):
    """Return fuzzy matches for OCR index entries."""
    normalized_query = query.strip().lower()
    if len(normalized_query) < MIN_QUERY_LENGTH:
        return []

    filtered_entries = []
    for entry in index:
        if is_viable_search_word(normalized_query, entry):
            filtered_entries.append(entry)

    choices = [entry["word"] for entry in filtered_entries]
    matches = process.extract(
        normalized_query,
        choices,
        scorer=fuzz.WRatio,
        score_cutoff=threshold,
        limit=limit,
    )

    results = []
    for _, score, match_index in matches:
        entry = dict(filtered_entries[match_index])
        normalized_word = entry["word"]
        substring_match = normalized_query in normalized_word
        if not substring_match and float(score) < threshold:
            print(f"[FILTER] rejected word='{normalized_word}' reason=low_similarity")
            continue
        print(f"[FILTER] accepted word='{normalized_word}' score={float(score):.1f}")
        entry["fuzzy_score"] = float(score) / 100.0
        results.append(entry)
    return results
