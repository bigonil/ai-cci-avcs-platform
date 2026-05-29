"""In-process BM25 index built from Qdrant payloads.

Strategy: on each search we work against the dense-search candidate set
(up to `candidate_limit` docs from Qdrant) rather than a full corpus index.
This avoids maintaining a persistent BM25 index but gives correct RRF fusion
for the top-K candidates that the dense model already considers relevant.
"""
from __future__ import annotations

import re
from typing import Any

from rank_bm25 import BM25Okapi


def _tokenize(text: str) -> list[str]:
    """Lowercase + split on non-alphanumeric."""
    return re.split(r"\W+", text.lower())


class EphemeralBM25:
    """BM25 over a fixed set of texts (built per-query from Qdrant candidates)."""

    def __init__(self, docs: list[dict[str, Any]], text_key: str = "text") -> None:
        self._docs = docs
        self._texts = [d.get(text_key) or d.get("payload", {}).get(text_key, "") for d in docs]
        tokenized = [_tokenize(t) for t in self._texts]
        self._bm25 = BM25Okapi(tokenized)

    def search(self, query: str, limit: int = 50) -> list[dict[str, Any]]:
        """Return docs ranked by BM25 score, descending."""
        if not self._docs:
            return []
        tokens = _tokenize(query)
        scores = self._bm25.get_scores(tokens)
        ranked = sorted(
            zip(scores, self._docs), key=lambda x: x[0], reverse=True
        )
        return [{"bm25_score": float(s), **d} for s, d in ranked[:limit] if s > 0]
