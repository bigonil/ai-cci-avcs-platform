"""Shared fixtures for Retrieval Service tests."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from cci_retrieval.config import RetrievalSettings


@pytest.fixture()
def settings() -> RetrievalSettings:
    return RetrievalSettings(
        QDRANT_HOST="localhost",
        QDRANT_PORT=6333,
        REDIS_URL="redis://localhost:6379/0",
        CCI_RERANKER_ENABLED=False,
        CCI_EMBEDDING_MODEL="all-MiniLM-L6-v2",
    )


@pytest.fixture()
def sample_chunks() -> list[dict]:
    return [
        {
            "chunk_id": "chunk-001",
            "doc_id": "doc-001",
            "text": "Azure commitment 580.000 EUR supera l'allocation approvata di 500.000 EUR per il 2026.",
            "domain": "hera_it",
            "_dense_score": 0.92,
        },
        {
            "chunk_id": "chunk-002",
            "doc_id": "doc-001",
            "text": "ISO 27001 scade il 2026-03-31 ma il commitment Azure copre l'intero 2026.",
            "domain": "hera_it",
            "_dense_score": 0.88,
        },
        {
            "chunk_id": "chunk-003",
            "doc_id": "doc-002",
            "text": "Budget CdA approvato per multi-cloud 2026: 800.000 EUR totali.",
            "domain": "hera_it",
            "_dense_score": 0.75,
        },
        {
            "chunk_id": "chunk-004",
            "doc_id": "doc-003",
            "text": "AWS EDP commitment 190.000 EUR entro allocation 200.000 EUR.",
            "domain": "hera_it",
            "_dense_score": 0.60,
        },
    ]
