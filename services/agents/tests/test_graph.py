"""Integration tests for the LangGraph pipeline (all nodes mocked)."""
from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from cci_llm.models import LLMResponse, LLMUsage
from cci_agents.graph import build_graph


def make_llm_response(content: str) -> LLMResponse:
    return LLMResponse(
        content=content,
        model="claude-sonnet-4-6",
        usage=LLMUsage(input_tokens=200, output_tokens=100),
        stop_reason="end_turn",
        request_id="msg_test",
    )


@pytest.fixture()
def compiled_graph(mock_llm, prompts_path, hera_rules):
    """Build a compiled graph with no real external services."""
    graph = build_graph(
        llm=mock_llm,
        prompts_path=prompts_path,
        retrieval_url="http://retrieval:8002",
        coherence_url="http://coherence:8003",
        governance_url="http://governance:8005",
        available_rules_by_domain={"hera_it": hera_rules},
        hitl_threshold_eur=50_000.0,
        top_k=10,
        checkpointer=None,
    )
    return graph


class TestGraphPipeline:
    @pytest.mark.asyncio
    async def test_full_pipeline_runs(
        self, mock_llm, prompts_path, hera_rules, sample_chunks, sample_violations
    ):
        """Verify the pipeline runs end-to-end with all nodes mocked at function level.

        Nodes are patched before graph build so functools.partial captures the mocks.
        Individual node behavior is covered by test_nodes.py; here we verify
        the graph wiring (state flows planner→retriever→verifier→generator→auditor).
        """
        mock_llm.complete_json.return_value = json.dumps({
            "query": "Azure budget 2026",
            "rules": ["R001", "R002"],
            "context": "test",
        })
        mock_llm.complete.return_value = make_llm_response(
            "Sforamento di 80.000 EUR [source: chunk_azure_001]."
        )

        # Patch nodes before building graph so partial captures the mocks
        with (
            patch("cci_agents.graph.retriever_node",
                  new=AsyncMock(return_value={"chunks": sample_chunks, "errors": []})),
            patch("cci_agents.graph.verifier_node",
                  new=AsyncMock(return_value={"violations": sample_violations,
                                              "verification_source": "chunks", "errors": []})),
            patch("cci_agents.graph.auditor_node",
                  new=AsyncMock(return_value={"audit_seq": 1, "audit_logged": True, "errors": []})),
        ):
            graph = build_graph(
                llm=mock_llm,
                prompts_path=prompts_path,
                retrieval_url="http://retrieval:8002",
                coherence_url="http://coherence:8003",
                governance_url="http://governance:8005",
                available_rules_by_domain={"hera_it": hera_rules},
                checkpointer=None,
            )
            final = await graph.ainvoke(
                {
                    "correlation_id": "test-001",
                    "trigger": "Verifica Hera Q1 2026",
                    "domain": "hera_it",
                    "as_of_date": "2026-03-31",
                    "errors": [],
                },
                config={"configurable": {"thread_id": "test-001"}},
            )

        assert final["violations"] == sample_violations
        assert final["audit_logged"]
        assert final["citations"]
        assert final["query"] == "Azure budget 2026"

    @pytest.mark.asyncio
    async def test_pipeline_survives_all_services_down(
        self, compiled_graph, mock_llm
    ):
        import httpx

        mock_llm.complete_json.return_value = '{"query":"q","rules":["R001"],"context":""}'
        mock_llm.complete.return_value = make_llm_response("Nessuna incoerenza rilevata.")

        with (
            patch("cci_agents.nodes.retriever.httpx.AsyncClient") as MockRet,
            patch("cci_agents.nodes.verifier.httpx.AsyncClient") as MockVer,
            patch("cci_agents.nodes.auditor.httpx.AsyncClient") as MockAud,
        ):
            for M in [MockRet, MockVer, MockAud]:
                M.return_value.__aenter__ = AsyncMock(return_value=M.return_value)
                M.return_value.__aexit__ = AsyncMock(return_value=False)
                M.return_value.post = AsyncMock(side_effect=httpx.ConnectError("down"))

            final = await compiled_graph.ainvoke(
                {
                    "correlation_id": "test-down",
                    "trigger": "test",
                    "domain": "hera_it",
                    "as_of_date": "2026-01-01",
                    "errors": [],
                },
                config={"configurable": {"thread_id": "test-down"}},
            )

        # Pipeline completes without raising
        assert "errors" in final
        assert len(final["errors"]) >= 2  # retriever + verifier + auditor errors
