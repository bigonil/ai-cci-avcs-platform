"""Integration tests for the Coherence Engine API (no Neo4j required)."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from cci_coherence.api import app
from cci_coherence.config import CoherenceSettings
from cci_coherence.rule_engine import CoherenceEngine
from tests.conftest import HERA_RULES

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

AZURE_COMMITMENT_CHUNK = {
    "chunk_id": "ch-001",
    "text": (
        "Commitment Azure EA per il 2026: impegno di 620.000 EUR "
        "dal 2026-01-01 al 2026-12-31."
    ),
}
AZURE_ALLOCATION_CHUNK = {
    "chunk_id": "ch-002",
    "text": (
        "Allocazione budget DSI per Azure: il budget CTO approvato "
        "è di 580.000 EUR per il cloud Azure 2026."
    ),
}
BUDGET_APPROVAL_CHUNK = {
    "chunk_id": "ch-003",
    "text": "Budget totale approvato dal CdA per cloud 2026: 800.000 EUR.",
}
CERT_CHUNK = {
    "chunk_id": "ch-004",
    "text": "ISO 27001 valido dal 2025-01-01 al 2026-06-30.",
}

ALL_CHUNKS = [AZURE_COMMITMENT_CHUNK, AZURE_ALLOCATION_CHUNK, BUDGET_APPROVAL_CHUNK, CERT_CHUNK]


@pytest_asyncio.fixture()
async def client():
    """AsyncClient backed by the FastAPI app with a stub engine (no Neo4j)."""
    settings = CoherenceSettings(
        CCI_COHERENCE_PORT=8003,
        CCI_NEO4J_ENABLED=False,
    )
    engine = CoherenceEngine(settings=settings, neo4j_driver=None)

    import cci_coherence.api as api_module
    api_module._engine = engine
    api_module._settings = settings
    api_module._start_time = 0.0

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


# ---------------------------------------------------------------------------
# Health endpoints
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_health_live(client):
    r = await client.get("/health/live")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_health_ready(client):
    r = await client.get("/health/ready")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_health_startup(client):
    r = await client.get("/health/startup")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


# ---------------------------------------------------------------------------
# POST /verify/chunks — violation scenarios
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_verify_chunks_r001_violation(client):
    payload = {
        "domain": "hera_it",
        "chunks": [AZURE_COMMITMENT_CHUNK, AZURE_ALLOCATION_CHUNK],
        "rules": [HERA_RULES[0]],
    }
    r = await client.post("/verify/chunks", json=payload)
    assert r.status_code == 200
    body = r.json()
    assert body["evaluation_source"] == "chunks"
    assert body["incoherences_found"] >= 1
    assert any(v["rule_violated"] == "R001" for v in body["violations"])


@pytest.mark.asyncio
async def test_verify_chunks_r002_cert_violation(client):
    payload = {
        "domain": "hera_it",
        "chunks": [AZURE_COMMITMENT_CHUNK, CERT_CHUNK],
        "rules": [HERA_RULES[1]],
    }
    r = await client.post("/verify/chunks", json=payload)
    assert r.status_code == 200
    body = r.json()
    assert any(v["rule_violated"] == "R002" for v in body["violations"])


@pytest.mark.asyncio
async def test_verify_chunks_no_violations_clean(client):
    clean_cert = {
        "chunk_id": "ch-clean",
        "text": "ISO 27001 valido dal 2025-01-01 al 2028-12-31.",
    }
    clean_commitment = {
        "chunk_id": "ch-c2",
        "text": "Commitment Azure EA 2026: impegno di 500.000 EUR dal 2026-01-01 al 2026-12-31.",
    }
    clean_alloc = {
        "chunk_id": "ch-c3",
        "text": "Allocazione budget DSI Azure: budget CTO approvato 580.000 EUR per Azure 2026.",
    }
    payload = {
        "domain": "hera_it",
        "chunks": [clean_commitment, clean_alloc, clean_cert],
        "rules": [HERA_RULES[0], HERA_RULES[1]],
    }
    r = await client.post("/verify/chunks", json=payload)
    assert r.status_code == 200
    body = r.json()
    assert body["incoherences_found"] == 0


@pytest.mark.asyncio
async def test_verify_chunks_empty_rules(client):
    payload = {
        "domain": "hera_it",
        "chunks": ALL_CHUNKS,
        "rules": [],
    }
    r = await client.post("/verify/chunks", json=payload)
    assert r.status_code == 200
    assert r.json()["incoherences_found"] == 0


# ---------------------------------------------------------------------------
# POST /verify — full endpoint (no graph because neo4j_enabled=False)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_verify_falls_back_to_chunks(client):
    payload = {
        "domain": "hera_it",
        "chunks": ALL_CHUNKS,
        "rules": HERA_RULES,
        "as_of_date": "2026-01-01",
    }
    r = await client.post("/verify", json=payload)
    assert r.status_code == 200
    body = r.json()
    assert body["domain"] == "hera_it"
    assert body["rules_evaluated"] == 4
    # Azure commitment > allocation and cert expiry should trigger
    assert body["incoherences_found"] >= 2


@pytest.mark.asyncio
async def test_verify_response_schema(client):
    payload = {
        "domain": "hera_it",
        "chunks": ALL_CHUNKS,
        "rules": HERA_RULES,
    }
    r = await client.post("/verify", json=payload)
    body = r.json()
    assert "domain" in body
    assert "as_of_date" in body
    assert "evaluation_source" in body
    assert "rules_evaluated" in body
    assert "incoherences_found" in body
    assert "violations" in body
    if body["violations"]:
        v = body["violations"][0]
        assert "rule_violated" in v
        assert "severity" in v
        assert "description" in v
        assert "evidence_chunks" in v
