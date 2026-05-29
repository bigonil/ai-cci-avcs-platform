"""Cross-encoder reranker — pluggable, lazy-loaded.

Default model: cross-encoder/ms-marco-MiniLM-L-6-v2 (lightweight, good quality).
Can be swapped to bge-reranker-v2-m3 via CCI_RERANKER_MODEL env var.
Set CCI_RERANKER_ENABLED=false to skip reranking entirely.
"""
from __future__ import annotations

import asyncio
import functools
from typing import Any

import structlog

log = structlog.get_logger(__name__)

_RERANKER: Any = None
_LOCK = asyncio.Lock()


async def _get_reranker(model_name: str) -> Any:
    global _RERANKER
    async with _LOCK:
        if _RERANKER is None:
            log.info("reranker_loading", model=model_name)
            loop = asyncio.get_event_loop()
            _RERANKER = await loop.run_in_executor(None, _load_reranker, model_name)
            log.info("reranker_loaded", model=model_name)
    return _RERANKER


def _load_reranker(model_name: str) -> Any:
    from sentence_transformers import CrossEncoder
    return CrossEncoder(model_name)


async def rerank(
    query: str,
    candidates: list[dict[str, Any]],
    model_name: str,
    text_key: str = "text",
    limit: int | None = None,
) -> list[dict[str, Any]]:
    """Score (query, passage) pairs with a cross-encoder and sort descending.

    Returns the same dicts enriched with `rerank_score`.
    """
    if not candidates:
        return []
    reranker = await _get_reranker(model_name)
    texts = [
        c.get(text_key) or c.get("payload", {}).get(text_key, "") for c in candidates
    ]
    pairs = [[query, t] for t in texts]
    loop = asyncio.get_event_loop()
    scores = await loop.run_in_executor(
        None,
        functools.partial(reranker.predict, pairs),
    )
    ranked = sorted(
        zip(scores, candidates), key=lambda x: float(x[0]), reverse=True
    )
    result = [{"rerank_score": float(s), **d} for s, d in ranked]
    return result[:limit] if limit else result
