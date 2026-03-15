"""Sentence-transformers semantic search helpers."""

from sentence_transformers import SentenceTransformer, util

import config

MIN_QUERY_LENGTH = getattr(config, "MIN_QUERY_LENGTH", 2)
MAX_RESULTS = getattr(config, "MAX_RESULTS", 50)
SEMANTIC_MODEL_NAME = getattr(config, "SEMANTIC_MODEL_NAME", "all-MiniLM-L6-v2")
SEMANTIC_LOCAL_FILES_ONLY = getattr(config, "SEMANTIC_LOCAL_FILES_ONLY", True)

_MODEL = None
_INDEX_CACHE = {}
_MODEL_LOAD_FAILED = False


def _get_model():
    """Lazy-load the embedding model so startup stays lightweight."""
    global _MODEL, _MODEL_LOAD_FAILED
    if _MODEL_LOAD_FAILED:
        return None
    if _MODEL is None:
        try:
            _MODEL = SentenceTransformer(
                SEMANTIC_MODEL_NAME,
                local_files_only=SEMANTIC_LOCAL_FILES_ONLY,
            )
        except Exception:
            # Allow the hybrid backend to keep working if the model
            # is not cached locally yet or the network is unavailable.
            _MODEL_LOAD_FAILED = True
            return None
    return _MODEL


def _index_key(index):
    """Build a stable cache key from word text and absolute coordinates."""
    return tuple((entry["word"], entry["x"], entry["y"]) for entry in index)


def _get_index_embeddings(index):
    """Precompute and cache embeddings for the current OCR index."""
    key = _index_key(index)
    if key not in _INDEX_CACHE:
        model = _get_model()
        if model is None:
            return None
        words = [entry["word"] for entry in index]
        _INDEX_CACHE[key] = model.encode(words, convert_to_tensor=True)
    return _INDEX_CACHE[key]


def semantic_search(query, index, limit=MAX_RESULTS):
    """Return cosine-similarity matches for OCR index entries."""
    normalized_query = query.strip().lower()
    if len(normalized_query) < MIN_QUERY_LENGTH or not index:
        return []

    model = _get_model()
    if model is None:
        return []
    query_embedding = model.encode(normalized_query, convert_to_tensor=True)
    index_embeddings = _get_index_embeddings(index)
    if index_embeddings is None:
        return []
    similarities = util.cos_sim(query_embedding, index_embeddings)[0]
    top_count = min(limit, len(index))
    top_scores, top_indices = similarities.topk(k=top_count)

    results = []
    for score, match_index in zip(top_scores.tolist(), top_indices.tolist()):
        entry = dict(index[match_index])
        entry["semantic_score"] = float(score)
        results.append(entry)
    return results
