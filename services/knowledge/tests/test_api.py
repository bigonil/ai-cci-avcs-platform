"""API-level tests using TestClient + dependency override."""
from __future__ import annotations

import pathlib
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from cci_knowledge.api import app, _state
from cci_knowledge.config import KnowledgeSettings
from cci_knowledge.ontology_loader import OntologyLoader


@pytest.fixture(autouse=True)
def _patch_state(
    sample_ontology_dir: pathlib.Path,
    mock_graph: AsyncMock,
    mock_qdrant: AsyncMock,
) -> None:
    """Inject mock dependencies into _state before each test."""
    cfg = KnowledgeSettings(
        NEO4J_URI="bolt://localhost:7687",
        NEO4J_USER="neo4j",
        NEO4J_PASSWORD="test",
        QDRANT_HOST="localhost",
        QDRANT_PORT=6333,
        MONGODB_URI="mongodb://localhost:27017",
        REDIS_URL="redis://localhost:6379/0",
        ONTOLOGIES_PATH=sample_ontology_dir,
    )
    loader = OntologyLoader(sample_ontology_dir)
    loader.load_all()

    ts_mock = AsyncMock()
    ts_mock.record = AsyncMock()
    ts_mock.close = AsyncMock()

    _state.settings = cfg
    _state.ontology_loader = loader
    _state.graph = mock_graph
    _state.vector_store = mock_qdrant
    _state.timeseries = ts_mock
    _state.ready = True


@pytest.fixture()
def client() -> TestClient:
    return TestClient(app, raise_server_exceptions=True)


class TestHealthEndpoints:
    def test_live(self, client: TestClient) -> None:
        r = client.get("/health/live")
        assert r.status_code == 200
        assert r.json()["status"] == "ok"

    def test_ready(self, client: TestClient) -> None:
        r = client.get("/health/ready")
        assert r.status_code == 200

    def test_ready_503_when_not_ready(self, client: TestClient) -> None:
        _state.ready = False
        r = client.get("/health/ready")
        assert r.status_code == 503
        _state.ready = True


class TestOntologyEndpoints:
    def test_list_ontologies(self, client: TestClient) -> None:
        r = client.get("/ontologies")
        assert r.status_code == 200
        assert "test_domain" in r.json()["domains"]

    def test_get_ontology(self, client: TestClient) -> None:
        r = client.get("/ontologies/test_domain")
        assert r.status_code == 200
        assert r.json()["domain"] == "test_domain"

    def test_get_ontology_not_found(self, client: TestClient) -> None:
        r = client.get("/ontologies/nonexistent")
        assert r.status_code == 404


class TestEntityEndpoints:
    def test_get_entities(self, client: TestClient) -> None:
        r = client.get("/entities/hera_it")
        assert r.status_code == 200
        body = r.json()
        assert body["domain"] == "hera_it"
        assert body["count"] >= 0


class TestDeleteEndpoint:
    def test_delete_document(self, client: TestClient) -> None:
        r = client.delete("/documents/doc-001")
        assert r.status_code == 200
        body = r.json()
        assert body["doc_id"] == "doc-001"


class TestQueryEndpoints:
    def test_vector_query(self, client: TestClient) -> None:
        payload = {
            "domain": "hera_it",
            "vector": [0.1] * 768,
            "limit": 5,
        }
        r = client.post("/query/vector", json=payload)
        assert r.status_code == 200
        assert "results" in r.json()

    def test_temporal_query_readonly(self, client: TestClient) -> None:
        payload = {"cypher": "MATCH (e:Entity) WHERE e.domain = 'hera_it' RETURN e LIMIT 5"}
        r = client.post("/query/temporal", json=payload)
        assert r.status_code == 200

    def test_temporal_query_write_rejected(self, client: TestClient) -> None:
        _state.graph.run_readonly_query = AsyncMock(  # type: ignore[attr-defined]
            side_effect=ValueError("Write keyword 'CREATE' detected")
        )
        payload = {"cypher": "CREATE (e:Entity {id: 'x'})"}
        r = client.post("/query/temporal", json=payload)
        assert r.status_code == 400
