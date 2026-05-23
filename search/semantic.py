"""Sentence-transformers semantic search helpers."""

import logging
import threading
from collections import OrderedDict

from sentence_transformers import SentenceTransformer, util

from config import (
    MAX_RESULTS,
    MIN_QUERY_LENGTH,
    SEMANTIC_CACHE_MAX,
    SEMANTIC_LOCAL_FILES_ONLY,
    SEMANTIC_MODEL_NAME,
)

_MODEL = None
_INDEX_CACHE = OrderedDict()
_CACHE_LOCK = threading.Lock()
_MODEL_LOAD_FAILED = False
logger = logging.getLogger("uniseba.semantic")


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


# Coordinates bucketed to 8px grid for scroll stability
# A 1-pixel shift will not invalidate the cache
def _index_key(index):
    """Build a stable cache key from word text and absolute coordinates."""
    return tuple(
        (
            entry["word"],
            round(entry["x"] / 8) * 8,
            round(entry["y"] / 8) * 8,
        )
        for entry in index
    )


def _get_index_embeddings(index):
    """Precompute and cache embeddings for the current OCR index."""
    key = _index_key(index)
    with _CACHE_LOCK:
        if key in _INDEX_CACHE:
            _INDEX_CACHE.move_to_end(key)
            return _INDEX_CACHE[key]

    model = _get_model()
    if model is None:
        return None
    words = [entry["word"] for entry in index]
    embeddings = model.encode(words, convert_to_tensor=True)
    with _CACHE_LOCK:
        _INDEX_CACHE[key] = embeddings
        if len(_INDEX_CACHE) > SEMANTIC_CACHE_MAX:
            _INDEX_CACHE.popitem(last=False)
        logger.debug("Semantic cache size: %s", len(_INDEX_CACHE))
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
