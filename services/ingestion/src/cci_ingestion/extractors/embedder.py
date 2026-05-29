"""Embedder — genera vettori dense per i chunk testuali.

Usa sentence-transformers con modello configurabile (default: all-MiniLM-L6-v2).
Il modello viene caricato una sola volta in memoria al primo utilizzo (lazy init).
"""
from __future__ import annotations

import hashlib
from functools import lru_cache
from typing import Any

from cci_common.observability import get_logger

logger = get_logger(__name__)


@lru_cache(maxsize=1)
def _get_model(model_name: str) -> Any:
    """Carica il modello sentence-transformers (singleton per processo)."""
    from sentence_transformers import SentenceTransformer  # type: ignore[import-untyped]

    logger.info("loading_embedding_model", model=model_name)
    return SentenceTransformer(model_name)


def embed_texts(
    texts: list[str],
    model_name: str = "all-MiniLM-L6-v2",
    batch_size: int = 32,
) -> list[list[float]]:
    """Genera embedding dense per una lista di testi.

    Returns:
        Lista di vettori float32 (uno per testo).
    """
    model = _get_model(model_name)
    embeddings = model.encode(
        texts,
        batch_size=batch_size,
        show_progress_bar=False,
        normalize_embeddings=True,
    )
    return [vec.tolist() for vec in embeddings]


def embed_single(text: str, model_name: str = "all-MiniLM-L6-v2") -> list[float]:
    """Genera embedding per un singolo testo."""
    return embed_texts([text], model_name=model_name)[0]


def chunk_id_from_text(doc_id: str, chunk_index: int, text: str) -> str:
    """Genera un chunk_id deterministico dal contenuto."""
    h = hashlib.sha256(f"{doc_id}:{chunk_index}:{text[:200]}".encode()).hexdigest()[:16]
    return f"chunk_{doc_id[:8]}_{h}"
