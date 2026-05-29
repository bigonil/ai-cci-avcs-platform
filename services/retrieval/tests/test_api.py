"""API-level tests for the Retrieval Service."""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from cci_retrieval.api import _state, app
from cci_retrieval.config import RetrievalSettings


@pytest.fixture(autouse=True)
def _patch_state(settings: RetrievalSettings) -> None:
    retriever = AsyncMock()
    retriever.search = AsyncMock(return_value=[
        {"chunk_id": "c1", "text": "Azure overspend rilevato. [source: chunk-abc12345]", "rrf_score": 0.95}
    ])
    retriever.dense_only = AsyncMock(return_value=[])
    retriever.bm25_only = AsyncMock(return_value=[])
    retriever.close = AsyncMock()

    cache = AsyncMock()
    cache.get = AsyncMock(return_value=None)
    cache.set = AsyncMock()
    cache.invalidate = AsyncMock(return_value=5)
    cache.close = AsyncMock()

    _state.settings = settings
    _state.retriever = retriever
    _state.cache = cache
    _state.ready = True


@pytest.fixture()
def client() -> TestClient:
    return TestClient(app, raise_server_exceptions=True)


class TestHealth:
    def test_live(self, client: TestClient) -> None:
        r = client.get("/health/live")
        assert r.status_code == 200

    def test_ready(self, client: TestClient) -> None:
        r = client.get("/health/ready")
        assert r.status_code == 200

    def test_ready_503(self, client: TestClient) -> None:
        _state.ready = False
        r = client.get("/health/ready")
        assert r.status_code == 503
        _state.ready = True


class TestSearchEndpoints:
    def test_hybrid_search(self, client: TestClient) -> None:
        r = client.post(
            "/search",
            json={"query": "Azure commitment 2026", "domain": "hera_it", "top_k": 5},
        )
        assert r.status_code == 200
        body = r.json()
        assert body["domain"] == "hera_it"
        assert isinstance(body["results"], list)

    def test_search_uses_cache(self, client: TestClient) -> None:
        cached = [{"chunk_id": "cached-c1", "text": "from cache", "rrf_score": 0.99}]
        _state.cache.get = AsyncMock(return_value=cached)
        r = client.post(
            "/search",
            json={"query": "ISO 27001 scadenza", "domain": "hera_it", "use_cache": True},
        )
        assert r.status_code == 200
        assert r.json()["from_cache"] is True

    def test_vector_search(self, client: TestClient) -> None:
        r = client.post(
            "/search/vector",
            json={"query": "budget CdA", "domain": "hera_it"},
        )
        assert r.status_code == 200

    def test_bm25_search(self, client: TestClient) -> None:
        r = client.post(
            "/search/bm25",
            json={"query": "commitment Azure", "domain": "hera_it"},
        )
        assert r.status_code == 200


class TestCitationEndpoint:
    def test_valid_citation(self, client: TestClient) -> None:
        r = client.post(
            "/citations/validate",
            json={
                "text": "Azure supera il budget 2026 come indicato nel report Q1. [source: chunk-abc12345]",
                "min_sentence_length": 20,
            },
        )
        assert r.status_code == 200
        body = r.json()
        assert body["valid"] is True

    def test_invalid_citation(self, client: TestClient) -> None:
        r = client.post(
            "/citations/validate",
            json={
                "text": (
                    "Azure supera il budget approvato dal CdA per il 2026 come riportato nei documenti. "
                    "ISO 27001 scade prima della fine del commitment Azure senza rinnovo previsto."
                ),
                "min_sentence_length": 20,
            },
        )
        assert r.status_code == 200
        body = r.json()
        assert body["valid"] is False
        assert len(body["uncited_sentences"]) > 0


class TestCacheEndpoint:
    def test_invalidate_cache(self, client: TestClient) -> None:
        r = client.delete("/cache/hera_it")
        assert r.status_code == 200
        assert r.json()["deleted"] == 5
