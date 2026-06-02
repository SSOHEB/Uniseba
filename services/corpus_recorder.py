"""Corpus recording state for Uniseba recording sessions.
Delegates storage to VectorStore.
Sentence embeddings stored via all-MiniLM-L6-v2.
"""

import logging
import re
import time
from collections import Counter
from typing import Iterable, Mapping, Optional, Tuple

from config import CORPUS_MIN_CONFIDENCE, SENTENCE_GROUP_VERTICAL_TOLERANCE_PX
from storage.vector_store import VectorStore

logger = logging.getLogger("uniseba.corpus")

_embedder = None


def _get_embedder():
    """
    Lazy-load sentence-transformers embedder.
    Returns None if unavailable.
    """
    global _embedder
    if _embedder is not None:
        return _embedder
    try:
        import os
        os.environ["TRANSFORMERS_OFFLINE"] = "1"
        os.environ["HF_DATASETS_OFFLINE"] = "1"
        from sentence_transformers import SentenceTransformer
        from config import SEMANTIC_MODEL_NAME
        _embedder = SentenceTransformer(SEMANTIC_MODEL_NAME)
        logger.info("Corpus embedder loaded: %s", SEMANTIC_MODEL_NAME)
        return _embedder
    except Exception as e:
        logger.warning(
            "Corpus embedder unavailable: %s "
            "- sentences will not be embedded", e
        )
        return None


class CorpusRecorder:
    """
    Manages sentence capture and embedding for a recording session.
    Delegates persistence to VectorStore.
    """

    def __init__(self):
        self._store: Optional[VectorStore] = None
        self._seen: set = set()
        self._stable_poll_count: int = 0
        self._last_corpus_size: int = 0
        self._window_title: str = ""

    def reset(self, session_id: str = None) -> None:
        """Start a new recording session."""
        if self._store is not None:
            self._store.flush()
        self._store = VectorStore(session_id=session_id)
        self._seen = set()
        self._stable_poll_count = 0
        self._last_corpus_size = 0
        logger.info(
            "CorpusRecorder reset session_id=%s",
            self._store._session_id
        )

    def set_window_title(self, title: str) -> None:
        self._window_title = title or ""

    def __len__(self) -> int:
        return len(self._store) if self._store else 0

    def has_items(self) -> bool:
        return self._store is not None and self._store.has_items()

    def joined_text(self) -> str:
        return self._store.joined_text() if self._store else ""

    def infer_focus(self) -> str:
        return self._store.infer_focus() if self._store else "Main Topic"

    def get_store(self) -> Optional[VectorStore]:
        return self._store

    def ingest_index(
        self, index: Iterable[Mapping]
    ) -> Tuple[int, int, int]:
        """
        Ingest OCR index entries into the vector store.
        Only ingests sentences above CORPUS_MIN_CONFIDENCE.
        Returns (before_count, after_count, stable_count).
        """
        if self._store is None:
            return 0, 0, 0

        before = len(self._store)
        embedder = _get_embedder()

        sentences = _group_into_sentences(index)

        for sentence, confidence in sentences:
            if confidence < CORPUS_MIN_CONFIDENCE:
                logger.debug(
                    "Skipping low-confidence sentence "
                    "(conf=%.2f): %r", confidence, sentence[:50]
                )
                continue
            if sentence in self._seen:
                continue
            self._seen.add(sentence)

            if embedder is not None:
                try:
                    embedding = embedder.encode(
                        sentence,
                        normalize_embeddings=True,
                        show_progress_bar=False,
                    )
                    self._store.add(
                        text=sentence,
                        embedding=embedding,
                        window_title=self._window_title,
                        timestamp=time.time(),
                    )
                except Exception as e:
                    logger.warning(
                        "Embedding failed for sentence %r: %s",
                        sentence[:50], e
                    )
            else:
                logger.debug(
                    "Embedder unavailable — sentence not stored: %r",
                    sentence[:50]
                )

        after = len(self._store)
        if after == self._last_corpus_size:
            self._stable_poll_count += 1
        else:
            self._stable_poll_count = 0
            self._last_corpus_size = after
        return before, after, self._stable_poll_count

    def flush(self) -> None:
        if self._store is not None:
            self._store.flush()


def _group_into_sentences(
    index: Iterable[Mapping],
    vertical_tolerance: int = SENTENCE_GROUP_VERTICAL_TOLERANCE_PX,
) -> list:
    """
    Group OCR index words into sentences by vertical proximity.
    Words within vertical_tolerance pixels of each other
    on the same line are joined left-to-right.
    Returns list of (sentence_text, mean_confidence) tuples.
    """
    words = sorted(
        [w for w in index if w.get("word", "").strip()],
        key=lambda w: (w.get("y", 0), w.get("x", 0))
    )
    if not words:
        return []

    lines = []
    current_line = [words[0]]

    for word in words[1:]:
        prev_y = current_line[-1].get("y", 0)
        curr_y = word.get("y", 0)
        if abs(curr_y - prev_y) <= vertical_tolerance:
            current_line.append(word)
        else:
            lines.append(current_line)
            current_line = [word]
    lines.append(current_line)

    sentences = []
    for line in lines:
        text = " ".join(
            w.get("word", "").strip()
            for w in line
            if w.get("word", "").strip()
        )
        if len(text) < 3:
            continue
        confidences = [
            float(w.get("confidence", 0.0)) for w in line
        ]
        mean_conf = (
            sum(confidences) / len(confidences)
            if confidences else 0.0
        )
        sentences.append((text, mean_conf))
    return sentences
