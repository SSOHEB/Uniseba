"""Corpus recording state and helpers for summary/graph features."""

from collections import Counter
import re
from typing import Iterable, Mapping, Tuple


class CorpusRecorder:
    """Manage insertion-ordered phrase capture with dedupe and stability tracking."""

    def __init__(self):
        self._corpus = []
        self._seen = set()
        self._stable_poll_count = 0
        self._last_corpus_size = 0

    def reset(self) -> None:
        self._corpus = []
        self._seen = set()
        self._stable_poll_count = 0
        self._last_corpus_size = 0

    def __len__(self) -> int:
        return len(self._corpus)

    def has_items(self) -> bool:
        return bool(self._corpus)

    def joined_text(self) -> str:
        return " ".join(self._corpus)

    def ingest_index(self, index: Iterable[Mapping]) -> Tuple[int, int, int]:
        """Ingest OCR index entries and return (before_count, after_count, stable_count)."""
        before = len(self._corpus)
        for item in index:
            phrase = str(item.get("original", "")).strip()
            if phrase and phrase not in self._seen:
                self._corpus.append(phrase)
                self._seen.add(phrase)

        after = len(self._corpus)
        if after == self._last_corpus_size:
            self._stable_poll_count += 1
        else:
            self._stable_poll_count = 0
            self._last_corpus_size = after
        return before, after, self._stable_poll_count

    def infer_focus(self) -> str:
        """Infer a meaningful graph focus term from captured corpus text."""
        tokens = Counter()
        stopwords = {
            "the",
            "and",
            "for",
            "with",
            "that",
            "this",
            "from",
            "have",
            "has",
            "are",
            "was",
            "were",
            "but",
            "not",
            "you",
            "your",
            "into",
            "about",
            "their",
            "they",
            "them",
            "then",
            "than",
            "where",
            "when",
            "what",
            "which",
            "while",
            "will",
            "would",
            "could",
            "should",
        }
        for phrase in self._corpus:
            for token in re.findall(r"[A-Za-z0-9][A-Za-z0-9'-]*", phrase.lower()):
                if len(token) < 3 or token in stopwords:
                    continue
                tokens[token] += 1

        if tokens:
            return tokens.most_common(1)[0][0]
        for phrase in self._corpus:
            parts = phrase.strip().split()
            if parts:
                return parts[0]
        return "Main Topic"

