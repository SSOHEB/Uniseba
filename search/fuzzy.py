"""RapidFuzz-based search helpers."""

from rapidfuzz import fuzz, process

import config

MIN_QUERY_LENGTH = getattr(config, "MIN_QUERY_LENGTH", 2)
FUZZY_THRESHOLD = max(90, getattr(config, "FUZZY_THRESHOLD", 75))
MAX_RESULTS = getattr(config, "MAX_RESULTS", 50)
MIN_WORD_LENGTH = 2
MIN_CONFIDENCE = 0.2


def is_viable_search_word(query, entry):
    """Reject only the most obvious OCR noise before fuzzy matching."""
    word = entry["word"]
    alnum_count = sum(char.isalnum() for char in word)
    if len(word) < MIN_WORD_LENGTH:
        return False
    if entry.get("confidence", 1.0) < MIN_CONFIDENCE:
        return False
    if alnum_count < max(1, len(word) // 2):
        return False
    return True


def fuzzy_search(query, index, limit=MAX_RESULTS, threshold=FUZZY_THRESHOLD):
    """Return fuzzy matches for OCR index entries."""
    normalized_query = query.strip().lower()
    if len(normalized_query) < MIN_QUERY_LENGTH:
        return []

    filtered_entries = [entry for entry in index if is_viable_search_word(normalized_query, entry)]
    rejected_count = len(index) - len(filtered_entries)
    print(f"[FILTER] accepted_candidates={len(filtered_entries)} rejected_candidates={rejected_count}")

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
            continue
        entry["fuzzy_score"] = float(score) / 100.0
        results.append(entry)
    print(f"[FILTER] final_matches={len(results)}")
    return results
