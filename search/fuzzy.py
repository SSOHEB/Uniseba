"""RapidFuzz-based search helpers."""

from rapidfuzz import fuzz, process

from config import FUZZY_THRESHOLD, MAX_RESULTS, MIN_CONFIDENCE, MIN_QUERY_LENGTH, MIN_WORD_LENGTH


def is_viable_search_word(query, entry):
    """Reject only the most obvious OCR noise before fuzzy matching."""
    word = entry["word"]
    if len(word) < MIN_WORD_LENGTH:
        return False
    if entry.get("confidence", 1.0) < MIN_CONFIDENCE:
        return False
    if not any(char.isalnum() for char in word):
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
        scorer=fuzz.partial_ratio,
        score_cutoff=threshold,
        limit=limit,
    )

    results = []
    for _, score, match_index in matches:
        entry = dict(filtered_entries[match_index])
        normalized_word = entry["word"]
        substring_match = normalized_query in normalized_word
        candidate_in_query = normalized_word in normalized_query
        containment_match = substring_match
        if candidate_in_query:
            start_gap = normalized_query.find(normalized_word)
            end_gap = len(normalized_query) - (start_gap + len(normalized_word))
            if start_gap > 2 or end_gap > 2:
                continue
            containment_match = True
        if not containment_match and float(score) < threshold:
            continue
        entry["fuzzy_score"] = float(score) / 100.0
        results.append(entry)
    print(f"[FILTER] final_matches={len(results)}")
    return results
