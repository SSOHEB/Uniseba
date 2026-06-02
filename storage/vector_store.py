r"""Numpy-based vector store for Uniseba recording sessions.
Stores sentence embeddings with metadata.
Persists to %APPDATA%\Uniseba\ as .npz files.
One .npz file per recording session.
"""

import logging
import os
import time
import uuid
from typing import Dict, List, Optional, Tuple

import numpy as np

from config import VECTOR_STORE_FLUSH_EVERY_N

logger = logging.getLogger("uniseba.vector_store")

EMBEDDING_DIM = 384  # all-MiniLM-L6-v2 output dimension
APPDATA_DIR = os.path.join(os.environ["APPDATA"], "Uniseba")


class VectorStore:
    """
    Stores sentence embeddings and metadata for one recording session.
    Persists to disk every FLUSH_EVERY_N additions.
    Thread-safe for single-writer / single-reader use.
    """

    def __init__(self, session_id: str = None):
        self._session_id = session_id or str(uuid.uuid4())
        self._texts: List[str] = []
        self._embeddings: List[np.ndarray] = []
        self._metadata: List[Dict] = []
        self._unflushed_count = 0
        self._storage_dir = APPDATA_DIR
        self._ensure_storage_dir()
        logger.info(
            "VectorStore initialized session_id=%s",
            self._session_id
        )

    def _ensure_storage_dir(self) -> None:
        try:
            os.makedirs(self._storage_dir, exist_ok=True)
        except Exception as e:
            logger.error(
                "Failed to create storage dir %s: %s",
                self._storage_dir, e
            )

    def _storage_path(self) -> str:
        return os.path.join(
            self._storage_dir,
            f"session_{self._session_id}.npz"
        )

    def add(
        self,
        text: str,
        embedding: np.ndarray,
        window_title: str = "",
        timestamp: float = None,
    ) -> None:
        """
        Add one sentence with its embedding and metadata.
        Flushes to disk every VECTOR_STORE_FLUSH_EVERY_N additions.
        """
        if not text or not text.strip():
            return
        if embedding is None or embedding.shape != (EMBEDDING_DIM,):
            logger.warning(
                "Invalid embedding shape %s for text %r — skipping",
                embedding.shape if embedding is not None else None,
                text[:50]
            )
            return

        self._texts.append(text.strip())
        self._embeddings.append(embedding)
        self._metadata.append({
            "session_id": self._session_id,
            "window_title": window_title,
            "timestamp": timestamp or time.time(),
        })
        self._unflushed_count += 1

        if self._unflushed_count >= VECTOR_STORE_FLUSH_EVERY_N:
            self.flush()

    def flush(self) -> None:
        """Persist current state to disk."""
        if not self._texts:
            return
        try:
            embeddings_array = np.array(
                self._embeddings, dtype=np.float32
            )
            np.savez(
                self._storage_path(),
                texts=np.array(self._texts, dtype=object),
                embeddings=embeddings_array,
                metadata=np.array(self._metadata, dtype=object),
                session_id=np.array([self._session_id]),
            )
            self._unflushed_count = 0
            logger.debug(
                "VectorStore flushed %s entries to %s",
                len(self._texts),
                self._storage_path()
            )
        except Exception as e:
            logger.error(
                "VectorStore flush failed: %s", e
            )

    def search(
        self,
        query_embedding: np.ndarray,
        top_k: int = 8,
    ) -> List[Tuple[str, float, Dict]]:
        """
        Return top_k most similar sentences by cosine similarity.
        Returns list of (text, score, metadata) tuples.
        Returns empty list if store is empty.
        """
        if not self._embeddings:
            return []
        if query_embedding is None:
            return []

        try:
            matrix = np.array(
                self._embeddings, dtype=np.float32
            )
            query_norm = query_embedding / (
                np.linalg.norm(query_embedding) + 1e-10
            )
            norms = np.linalg.norm(matrix, axis=1, keepdims=True)
            matrix_norm = matrix / (norms + 1e-10)
            scores = matrix_norm @ query_norm
            top_indices = np.argsort(scores)[::-1][:top_k]
            return [
                (
                    self._texts[i],
                    float(scores[i]),
                    self._metadata[i],
                )
                for i in top_indices
            ]
        except Exception as e:
            logger.error("VectorStore search failed: %s", e)
            return []

    def has_items(self) -> bool:
        return bool(self._texts)

    def __len__(self) -> int:
        return len(self._texts)

    def joined_text(self) -> str:
        """Return all stored text joined — for backward compat."""
        return " ".join(self._texts)

    def infer_focus(self) -> str:
        """Return most frequent non-stopword token across stored text."""
        from collections import Counter
        import re

        stopwords = {
            "the", "and", "for", "with", "that", "this",
            "from", "have", "has", "are", "was", "were",
            "but", "not", "you", "your", "into", "about",
            "their", "they", "them", "then", "than",
            "where", "when", "what", "which", "while",
            "will", "would", "could", "should",
        }
        tokens = Counter()
        for text in self._texts:
            for token in re.findall(
                r"[A-Za-z0-9][A-Za-z0-9'-]*", text.lower()
            ):
                if len(token) >= 3 and token not in stopwords:
                    tokens[token] += 1
        if tokens:
            return tokens.most_common(1)[0][0]
        if self._texts:
            return self._texts[0].split()[0]
        return "Main Topic"

    @classmethod
    def load(cls, session_id: str) -> Optional["VectorStore"]:
        """
        Load a previously saved session from disk.
        Returns None if file does not exist or load fails.
        """
        store = cls(session_id=session_id)
        path = store._storage_path()
        if not os.path.exists(path):
            logger.warning(
                "VectorStore session file not found: %s", path
            )
            return None
        try:
            data = np.load(path, allow_pickle=True)
            store._texts = list(data["texts"])
            store._embeddings = list(data["embeddings"])
            store._metadata = list(data["metadata"])
            logger.info(
                "VectorStore loaded session_id=%s entries=%s",
                session_id, len(store._texts)
            )
            return store
        except Exception as e:
            logger.error(
                "VectorStore load failed for %s: %s",
                session_id, e
            )
            return None

    @staticmethod
    def list_sessions() -> List[str]:
        """
        List all saved session IDs from disk.
        Returns empty list if storage dir does not exist.
        """
        try:
            files = os.listdir(APPDATA_DIR)
            sessions = []
            for f in files:
                if f.startswith("session_") and f.endswith(".npz"):
                    sid = f[len("session_"):-len(".npz")]
                    sessions.append(sid)
            return sorted(sessions)
        except Exception as e:
            logger.error(
                "VectorStore list_sessions failed: %s", e
            )
            return []
