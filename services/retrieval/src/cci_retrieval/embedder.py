"""Lazy singleton sentence-transformers embedder.

Loads the model once on first call. Uses run_in_executor to keep
the synchronous encode() call off the event loop.
"""
from __future__ import annotations

import asyncio
import functools
from typing import Any

import structlog

log = structlog.get_logger(__name__)

_MODEL: Any = None
_LOCK = asyncio.Lock()


async def _get_model(model_name: str) -> Any:
    global _MODEL
    async with _LOCK:
        if _MODEL is None:
            log.info("embedding_model_loading", model=model_name)
            loop = asyncio.get_event_loop()
            # Load in thread pool — heavy I/O + CPU
            _MODEL = await loop.run_in_executor(
                None, _load_model, model_name
            )
            log.info("embedding_model_loaded", model=model_name)
    return _MODEL


def _load_model(model_name: str) -> Any:
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer(model_name)


async def embed_texts(texts: list[str], model_name: str) -> list[list[float]]:
    """Embed a batch of texts. Returns list of float vectors."""
    if not texts:
        return []
    model = await _get_model(model_name)
    loop = asyncio.get_event_loop()
    vectors = await loop.run_in_executor(
        None,
        functools.partial(model.encode, texts, convert_to_numpy=True, show_progress_bar=False),
    )
    return [v.tolist() for v in vectors]


async def embed_query(query: str, model_name: str) -> list[float]:
    """Embed a single query string."""
    results = await embed_texts([query], model_name)
    return results[0]
