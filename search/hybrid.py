"""Hybrid OCR search combining fuzzy and semantic signals."""

import config

from search.fuzzy import fuzzy_search
from search.semantic import semantic_search

FUZZY_WEIGHT = getattr(config, "FUZZY_WEIGHT", 0.4)
SEMANTIC_WEIGHT = getattr(config, "SEMANTIC_WEIGHT", 0.6)
MAX_RESULTS = getattr(config, "MAX_RESULTS", 50)
MIN_QUERY_LENGTH = getattr(config, "MIN_QUERY_LENGTH", 2)


def hybrid_search(query, index, limit=MAX_RESULTS):
    """Merge fuzzy and semantic matches into one ranked result list."""
    normalized_query = query.strip().lower()
    if len(normalized_query) < MIN_QUERY_LENGTH:
        return []

    merged = {}
    for entry in fuzzy_search(normalized_query, index, limit=limit):
        key = (entry["x"], entry["y"])
        merged[key] = {
            **entry,
            "fuzzy_score": entry.get("fuzzy_score", 0.0),
            "semantic_score": 0.0,
        }

    for entry in semantic_search(normalized_query, index, limit=limit):
        key = (entry["x"], entry["y"])
        current = merged.setdefault(
            key,
            {
                **entry,
                "fuzzy_score": 0.0,
                "semantic_score": 0.0,
            },
        )
        current["semantic_score"] = max(current["semantic_score"], entry.get("semantic_score", 0.0))

    results = []
    for entry in merged.values():
        final_score = (
            (entry.get("fuzzy_score", 0.0) * FUZZY_WEIGHT)
            + (entry.get("semantic_score", 0.0) * SEMANTIC_WEIGHT)
        )
        ranked = dict(entry)
        ranked["final_score"] = round(final_score, 4)
        results.append(ranked)

    results.sort(key=lambda item: item["final_score"], reverse=True)
    return results[:limit]


if __name__ == "__main__":
    sample_index = [
        {"word": "soheb", "original": "SOHEB", "x": 40, "y": 20, "w": 60, "h": 18},
        {"word": "success", "original": "SUCCESS", "x": 120, "y": 20, "w": 80, "h": 18},
        {"word": "phase", "original": "Phase", "x": 40, "y": 60, "w": 55, "h": 18},
        {"word": "hello", "original": "Hello", "x": 120, "y": 60, "w": 50, "h": 18},
        {"word": "world", "original": "world", "x": 190, "y": 60, "w": 52, "h": 18},
        {"word": "test", "original": "TEST", "x": 260, "y": 60, "w": 42, "h": 18},
        {"word": "name", "original": "name", "x": 40, "y": 100, "w": 48, "h": 18},
    ]

    for query in ["soheb", "succes", "name", "phase"]:
        print(f"\nQuery: {query}")
        for item in hybrid_search(query, sample_index, limit=5):
            print(
                f"{item['original']} | score={item['final_score']:.4f} | "
                f"({item['x']}, {item['y']}, {item['w']}, {item['h']})"
            )
