"""RapidFuzz-based search helpers."""

import logging

from rapidfuzz import fuzz, process

from config import FUZZY_THRESHOLD, MAX_RESULTS, MIN_CONFIDENCE, MIN_QUERY_LENGTH, MIN_WORD_LENGTH

logger = logging.getLogger("uniseba.search.fuzzy")

# Common glue-words that should not outrank more specific matches when the user
# types a longer query (e.g. "gandhi" should not primarily match "and").
_STOPWORDS = frozenset(
    {
        "a",
        "an",
        "and",
        "are",
        "as",
        "at",
        "be",
        "by",
        "for",
        "from",
        "in",
        "is",
        "it",
        "of",
        "on",
        "or",
        "that",
        "the",
        "to",
        "was",
        "were",
        "with",
    }
)


def _rank_score(query, word, score):
    """Combine RapidFuzz score with heuristics that improve result ordering."""
    qlen = len(query)
    wlen = len(word)
    base = float(score) / 100.0
    bonus = 0.0
    penalty = 0.0

    if word == query:
        bonus += 0.15
    if query and query in word:
        bonus += 0.10

    # If the candidate is just a substring inside the query, prefer longer matches.
    if word in query and word != query:
        penalty += 0.12
        if wlen <= 3 and qlen >= 5:
            penalty += 0.20

    # Penalize large length mismatches so "not" loses to "notes".
    penalty += abs(wlen - qlen) * 0.01

    # When the query is a meaningful prefix, down-rank common verb-y endings that
    # tend to be incidental matches ("refer" -> "referred" vs "references").
    if qlen >= 4 and word.startswith(query) and word != query:
        if word.endswith("ed") or word.endswith("ing"):
            penalty += 0.06

    # Down-rank stopwords for longer queries without removing them completely.
    if qlen >= 4 and word in _STOPWORDS:
        penalty += 0.25

    return base + bonus - penalty


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
    logger.debug(
        "[FILTER] accepted_candidates=%s rejected_candidates=%s",
        len(filtered_entries),
        rejected_count,
    )

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
        entry["_rank_score"] = _rank_score(normalized_query, normalized_word, score)
        results.append(entry)
    results.sort(key=lambda item: (item.get("_rank_score", 0.0), item.get("fuzzy_score", 0.0)), reverse=True)
    logger.debug("[FILTER] final_matches=%s", len(results))
    logger.debug("[FUZZY] query=%r matches=%s", query, len(results))
    for r in results[:5]:
        logger.debug(
            "  %r score=%.1f at (%s,%s)",
            r["original"],
            r["fuzzy_score"],
            r["x"],
            r["y"],
        )
    return results
