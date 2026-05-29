"""API integration tests — graph is stubbed, no real LLM or services."""
from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from cci_llm.models import LLMResponse, LLMUsage
from cci_agents.api import app
import cci_agents.api as api_module


def make_llm_response(content: str) -> LLMResponse:
    return LLMResponse(
        content=content,
        model="claude-sonnet-4-6",
        usage=LLMUsage(input_tokens=200, output_tokens=100),
        stop_reason="end_turn",
        request_id="msg_test",
    )


@pytest_asyncio.fixture()
async def client(mock_llm, prompts_path, hera_rules):
    """AsyncClient with a stub graph (all external calls mocked)."""
    from cci_agents.graph import build_graph

    graph = build_graph(
        llm=mock_llm,
        prompts_path=prompts_path,
        retrieval_url="http://retrieval:8002",
        coherence_url="http://coherence:8003",
        governance_url="http://governance:8005",
        available_rules_by_domain={"hera_it": hera_rules},
        checkpointer=None,
    )

    from cci_agents.config import AgentsSettings
    settings = AgentsSettings(CCI_AGENTS_PORT=8004, CCI_NEO4J_ENABLED=False)
    api_module._graph = graph
    api_module._settings = settings
    api_module._start_time = 0.0
    api_module._rules_by_domain = {"hera_it": hera_rules}

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


class TestHealthEndpoints:
    @pytest.mark.asyncio
    async def test_live(self, client):
        r = await client.get("/health/live")
        assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_ready(self, client):
        r = await client.get("/health/ready")
        assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_startup(self, client):
        r = await client.get("/health/startup")
        assert r.status_code == 200


class TestVerifyEndpoint:
    @pytest.mark.asyncio
    async def test_returns_response_schema(
        self, client, mock_llm, sample_chunks, sample_violations
    ):
        mock_llm.complete_json.return_value = json.dumps({
            "query": "Azure 2026", "rules": ["R001"], "context": ""
        })
        mock_llm.complete.return_value = make_llm_response(
            "Sforamento 80.000 EUR [source: chunk_azure_001]."
        )

        with (
            patch("cci_agents.nodes.retriever.httpx.AsyncClient") as MockRet,
            patch("cci_agents.nodes.verifier.httpx.AsyncClient") as MockVer,
            patch("cci_agents.nodes.auditor.httpx.AsyncClient") as MockAud,
        ):
            for M, data in [
                (MockRet, {"results": sample_chunks}),
                (MockVer, {"violations": sample_violations, "evaluation_source": "chunks"}),
                (MockAud, {"seq": 7}),
            ]:
                resp = MagicMock()
                resp.raise_for_status = MagicMock()
                resp.json.return_value = data
                M.return_value.__aenter__ = AsyncMock(return_value=M.return_value)
                M.return_value.__aexit__ = AsyncMock(return_value=False)
                M.return_value.post = AsyncMock(return_value=resp)

            r = await client.post("/verify", json={
                "trigger": "Verifica budget Hera 2026",
                "domain": "hera_it",
                "as_of_date": "2026-03-31",
            })

        assert r.status_code == 200
        body = r.json()
        assert "correlation_id" in body
        assert "violations" in body
        assert "report_text" in body
        assert "citations" in body
        assert "grounding_verified" in body
        assert "hitl_required" in body
        assert "elapsed_ms" in body

    @pytest.mark.asyncio
    async def test_violations_count_in_response(
        self, mock_llm, prompts_path, hera_rules, sample_chunks, sample_violations
    ):
        mock_llm.complete_json.return_value = '{"query":"q","rules":["R001"],"context":""}'
        mock_llm.complete.return_value = make_llm_response(
            "Regola R001 violata [source: chunk_azure_001]."
        )

        # Patch node functions before build so functools.partial captures the mocks
        with (
            patch("cci_agents.graph.retriever_node",
                  new=AsyncMock(return_value={"chunks": sample_chunks, "errors": []})),
            patch("cci_agents.graph.verifier_node",
                  new=AsyncMock(return_value={"violations": sample_violations,
                                              "verification_source": "chunks", "errors": []})),
            patch("cci_agents.graph.auditor_node",
                  new=AsyncMock(return_value={"audit_seq": 1, "audit_logged": True, "errors": []})),
        ):
            from cci_agents.graph import build_graph
            from cci_agents.config import AgentsSettings
            graph = build_graph(
                llm=mock_llm,
                prompts_path=prompts_path,
                retrieval_url="http://retrieval:8002",
                coherence_url="http://coherence:8003",
                governance_url="http://governance:8005",
                available_rules_by_domain={"hera_it": hera_rules},
                checkpointer=None,
            )
            api_module._graph = graph
            api_module._settings = AgentsSettings(CCI_AGENTS_PORT=8004, CCI_NEO4J_ENABLED=False)
            api_module._start_time = 0.0
            api_module._rules_by_domain = {"hera_it": hera_rules}

            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as ac:
                r = await ac.post("/verify", json={
                    "trigger": "test", "domain": "hera_it",
                })

        assert r.json()["violations_found"] == len(sample_violations)
