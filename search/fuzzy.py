"""RapidFuzz-based search helpers."""

from rapidfuzz import fuzz, process

import config

MIN_QUERY_LENGTH = getattr(config, "MIN_QUERY_LENGTH", 2)
FUZZY_THRESHOLD = getattr(config, "FUZZY_THRESHOLD", 75)
MAX_RESULTS = getattr(config, "MAX_RESULTS", 50)


def fuzzy_search(query, index, limit=MAX_RESULTS, threshold=FUZZY_THRESHOLD):
    """Return fuzzy matches for OCR index entries."""
    normalized_query = query.strip().lower()
    if len(normalized_query) < MIN_QUERY_LENGTH:
        return []

    choices = [entry["word"] for entry in index]
    matches = process.extract(
        normalized_query,
        choices,
        scorer=fuzz.WRatio,
        score_cutoff=threshold,
        limit=limit,
    )

    results = []
    for _, score, match_index in matches:
        entry = dict(index[match_index])
        entry["fuzzy_score"] = float(score) / 100.0
        results.append(entry)
    return results
