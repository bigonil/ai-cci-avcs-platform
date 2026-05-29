"""Unit tests for each LangGraph node — all external calls are mocked."""
from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from cci_llm.models import LLMResponse, LLMUsage
from cci_agents.nodes.auditor import auditor_node
from cci_agents.nodes.generator import generator_node, _build_fallback_report, _check_hitl
from cci_agents.nodes.planner import planner_node
from cci_agents.nodes.retriever import retriever_node
from cci_agents.nodes.verifier import verifier_node


def make_llm_response(content: str) -> LLMResponse:
    return LLMResponse(
        content=content,
        model="claude-sonnet-4-6",
        usage=LLMUsage(input_tokens=200, output_tokens=100),
        stop_reason="end_turn",
        request_id="msg_test",
    )


# ---------------------------------------------------------------------------
# Planner
# ---------------------------------------------------------------------------

class TestPlannerNode:
    @pytest.mark.asyncio
    async def test_parses_llm_json(self, mock_llm, prompts_path, hera_rules, base_state):
        mock_llm.complete_json.return_value = json.dumps({
            "query": "Azure commitment budget 2026",
            "rules": ["R001", "R002"],
            "context": "Focus on R001 and R002",
        })
        result = await planner_node(
            base_state,
            llm=mock_llm,
            prompts_path=prompts_path,
            available_rules=hera_rules,
        )
        assert result["query"] == "Azure commitment budget 2026"
        assert len(result["rules"]) == 2
        assert result["rules"][0]["rule_id"] == "R001"

    @pytest.mark.asyncio
    async def test_fallback_on_json_error(self, mock_llm, prompts_path, hera_rules, base_state):
        mock_llm.complete_json.return_value = "not json at all"
        result = await planner_node(
            base_state,
            llm=mock_llm,
            prompts_path=prompts_path,
            available_rules=hera_rules,
        )
        # Falls back to all rules
        assert len(result["rules"]) == len(hera_rules)
        assert any("planner_parse_error" in e for e in result["errors"])

    @pytest.mark.asyncio
    async def test_unknown_rule_ids_filtered(self, mock_llm, prompts_path, hera_rules, base_state):
        mock_llm.complete_json.return_value = json.dumps({
            "query": "test", "rules": ["R001", "R999"], "context": ""
        })
        result = await planner_node(
            base_state,
            llm=mock_llm,
            prompts_path=prompts_path,
            available_rules=hera_rules,
        )
        # R999 is unknown — filtered out, fallback to all
        rule_ids = [r["rule_id"] for r in result["rules"]]
        assert "R999" not in rule_ids

    @pytest.mark.asyncio
    async def test_markdown_fences_stripped(self, mock_llm, prompts_path, hera_rules, base_state):
        mock_llm.complete_json.return_value = '```json\n{"query":"q","rules":["R001"],"context":""}\n```'
        result = await planner_node(
            base_state,
            llm=mock_llm,
            prompts_path=prompts_path,
            available_rules=hera_rules,
        )
        assert result["query"] == "q"


# ---------------------------------------------------------------------------
# Retriever
# ---------------------------------------------------------------------------

class TestRetrieverNode:
    @pytest.mark.asyncio
    async def test_returns_chunks_on_success(self, base_state, sample_chunks):
        state = {**base_state, "query": "Azure budget 2026"}
        with patch("cci_agents.nodes.retriever.httpx.AsyncClient") as MockClient:
            mock_resp = MagicMock()
            mock_resp.raise_for_status = MagicMock()
            mock_resp.json.return_value = {"results": sample_chunks}
            MockClient.return_value.__aenter__ = AsyncMock(return_value=MockClient.return_value)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value.post = AsyncMock(return_value=mock_resp)
            result = await retriever_node(state, retrieval_url="http://retrieval:8002")
        assert len(result["chunks"]) == len(sample_chunks)
        assert result["errors"] == []

    @pytest.mark.asyncio
    async def test_empty_on_http_error(self, base_state):
        import httpx
        state = {**base_state, "query": "test"}
        with patch("cci_agents.nodes.retriever.httpx.AsyncClient") as MockClient:
            MockClient.return_value.__aenter__ = AsyncMock(return_value=MockClient.return_value)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value.post = AsyncMock(
                side_effect=httpx.ConnectError("refused")
            )
            result = await retriever_node(state, retrieval_url="http://down:9999")
        assert result["chunks"] == []
        assert len(result["errors"]) == 1


# ---------------------------------------------------------------------------
# Verifier
# ---------------------------------------------------------------------------

class TestVerifierNode:
    @pytest.mark.asyncio
    async def test_returns_violations(self, base_state, sample_chunks, sample_violations, hera_rules):
        state = {**base_state, "chunks": sample_chunks, "rules": [
            {"rule_id": r["id"], "when": r["when"], "severity": r["severity"]}
            for r in hera_rules
        ]}
        with patch("cci_agents.nodes.verifier.httpx.AsyncClient") as MockClient:
            mock_resp = MagicMock()
            mock_resp.raise_for_status = MagicMock()
            mock_resp.json.return_value = {
                "violations": sample_violations,
                "evaluation_source": "chunks",
            }
            MockClient.return_value.__aenter__ = AsyncMock(return_value=MockClient.return_value)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value.post = AsyncMock(return_value=mock_resp)
            result = await verifier_node(state, coherence_url="http://coherence:8003")
        assert len(result["violations"]) == 2
        assert result["verification_source"] == "chunks"

    @pytest.mark.asyncio
    async def test_empty_on_no_rules(self, base_state):
        state = {**base_state, "chunks": [], "rules": []}
        result = await verifier_node(state, coherence_url="http://coherence:8003")
        assert result["violations"] == []


# ---------------------------------------------------------------------------
# Generator
# ---------------------------------------------------------------------------

class TestGeneratorNode:
    @pytest.mark.asyncio
    async def test_grounded_report_passes(
        self, mock_llm, prompts_path, base_state, sample_chunks, sample_violations
    ):
        # LLM returns properly cited text
        cited_text = (
            "Il commitment Azure ammonta a 580.000 EUR [source: chunk_azure_001]. "
            "La certificazione ISO 27001 scade il 2026-03-31 [source: chunk_cert_001]."
        )
        mock_llm.complete.return_value = make_llm_response(cited_text)
        state = {**base_state, "chunks": sample_chunks, "violations": sample_violations}
        result = await generator_node(
            state, llm=mock_llm, prompts_path=prompts_path, hitl_threshold_eur=50_000.0
        )
        assert result["grounding_verified"]
        assert "chunk_azure_001" in result["citations"]

    @pytest.mark.asyncio
    async def test_r3_violation_recorded_not_raised(
        self, mock_llm, prompts_path, base_state, sample_chunks, sample_violations
    ):
        # LLM returns uncited factual text — R3 violation logged, not raised
        mock_llm.complete.return_value = make_llm_response(
            "Il valore totale e 855000 EUR senza citazione alcuna nel testo."
        )
        state = {**base_state, "chunks": sample_chunks, "violations": sample_violations}
        result = await generator_node(
            state, llm=mock_llm, prompts_path=prompts_path
        )
        assert not result["grounding_verified"]
        assert any("r3_grounding_error" in e for e in result["errors"])

    @pytest.mark.asyncio
    async def test_no_violations_short_circuits(
        self, mock_llm, prompts_path, base_state
    ):
        state = {**base_state, "chunks": [], "violations": []}
        result = await generator_node(
            state, llm=mock_llm, prompts_path=prompts_path
        )
        # No LLM call needed
        mock_llm.complete.assert_not_called()
        assert result["grounding_verified"]

    @pytest.mark.asyncio
    async def test_hitl_triggered_above_threshold(
        self, mock_llm, prompts_path, base_state, sample_chunks
    ):
        high_delta_violation = {
            "rule_violated": "R001", "severity": "HIGH",
            "description": "big overrun [source: chunk_azure_001]",
            "evidence_chunks": ["chunk_azure_001"],
            "computed_values": {"delta": 80_000.0},
        }
        cited = "Sforamento di 80.000 EUR [source: chunk_azure_001]."
        mock_llm.complete.return_value = make_llm_response(cited)
        state = {**base_state, "chunks": sample_chunks, "violations": [high_delta_violation]}
        result = await generator_node(
            state, llm=mock_llm, prompts_path=prompts_path, hitl_threshold_eur=50_000.0
        )
        assert result["hitl_required"]

    def test_hitl_not_triggered_below_threshold(self):
        violations = [{"computed_values": {"delta": 10_000.0}}]
        assert not _check_hitl(violations, 50_000.0)

    def test_fallback_report_has_citations(self):
        violations = [{
            "rule_violated": "R001",
            "description": "Test description",
            "evidence_chunks": ["chunk_a", "chunk_b"],
        }]
        report = _build_fallback_report(violations)
        assert "[source: chunk_a]" in report
        assert "R001" in report


# ---------------------------------------------------------------------------
# Auditor
# ---------------------------------------------------------------------------

class TestAuditorNode:
    @pytest.mark.asyncio
    async def test_logs_to_governance(self, base_state, sample_violations):
        state = {
            **base_state,
            "violations": sample_violations,
            "rules": [{"rule_id": "R001"}],
            "grounding_verified": True,
            "hitl_required": False,
            "citations": ["chunk_a"],
            "verification_source": "chunks",
        }
        with patch("cci_agents.nodes.auditor.httpx.AsyncClient") as MockClient:
            mock_resp = MagicMock()
            mock_resp.raise_for_status = MagicMock()
            mock_resp.json.return_value = {"seq": 42}
            MockClient.return_value.__aenter__ = AsyncMock(return_value=MockClient.return_value)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value.post = AsyncMock(return_value=mock_resp)
            result = await auditor_node(state, governance_url="http://governance:8005")
        assert result["audit_seq"] == 42
        assert result["audit_logged"]

    @pytest.mark.asyncio
    async def test_governance_unavailable_no_crash(self, base_state):
        import httpx
        state = {**base_state, "violations": [], "rules": [], "grounding_verified": False,
                 "hitl_required": False, "citations": [], "verification_source": "none"}
        with patch("cci_agents.nodes.auditor.httpx.AsyncClient") as MockClient:
            MockClient.return_value.__aenter__ = AsyncMock(return_value=MockClient.return_value)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value.post = AsyncMock(
                side_effect=httpx.ConnectError("refused")
            )
            result = await auditor_node(state, governance_url="http://down:9999")
        assert not result["audit_logged"]
        assert result["audit_seq"] is None
        assert len(result["errors"]) == 1
