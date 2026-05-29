"""Shared fixtures for the agents service tests."""
from __future__ import annotations

import pathlib
from unittest.mock import AsyncMock, MagicMock

import pytest

from cci_llm import LLMMessage
from cci_llm.models import LLMResponse, LLMUsage


def make_llm_response(content: str) -> LLMResponse:
    return LLMResponse(
        content=content,
        model="claude-sonnet-4-6",
        usage=LLMUsage(input_tokens=200, output_tokens=100),
        stop_reason="end_turn",
        request_id="msg_test",
    )


@pytest.fixture()
def mock_llm() -> MagicMock:
    """LLMClient stub — no real API calls."""
    client = MagicMock()
    client.model = "claude-sonnet-4-6"
    client.complete = AsyncMock()
    client.complete_json = AsyncMock()
    return client


@pytest.fixture()
def prompts_path(tmp_path: pathlib.Path) -> pathlib.Path:
    """Create minimal Jinja2 prompt templates in a temp directory."""
    prompts = tmp_path / "prompts"
    prompts.mkdir()

    (prompts / "planner.j2").write_text(
        'Planner prompt for {{ domain }}. Produce JSON with query and rules.'
    )
    (prompts / "generator.j2").write_text(
        'Generator prompt for {{ domain }}. Include [source: chunk_id] citations.'
    )
    return prompts


@pytest.fixture()
def hera_rules() -> list[dict]:
    return [
        {"id": "R001", "when": "CloudCommitment > Budget WHERE provider", "severity": "HIGH",
         "description": "Provider commitment exceeds CTO allocation"},
        {"id": "R002", "when": "cert.valid_to < commitment.period_end", "severity": "CRITICAL",
         "description": "ISO 27001 expires before commitment ends"},
        {"id": "R003", "when": "sum(commitments) > BudgetApproval", "severity": "HIGH",
         "description": "Total multi-cloud exceeds CdA budget"},
        {"id": "R004", "when": "concentration > 0.70", "severity": "MEDIUM",
         "description": "Single provider exceeds 70% concentration"},
    ]


@pytest.fixture()
def sample_chunks() -> list[dict]:
    return [
        {"chunk_id": "chunk_azure_001", "text": "Commitment Azure EA 580.000 EUR 2026-01-01 al 2026-12-31.", "score": 0.9},
        {"chunk_id": "chunk_cert_001", "text": "ISO 27001 valido dal 2024-04-01 al 2026-03-31.", "score": 0.85},
        {"chunk_id": "chunk_budget_001", "text": "Budget CdA totale 800.000 EUR approvato.", "score": 0.8},
    ]


@pytest.fixture()
def sample_violations() -> list[dict]:
    return [
        {
            "rule_violated": "R001",
            "severity": "HIGH",
            "description": "CloudCommitment(Azure, 580,000) > CloudBudgetAllocation(Azure, 500,000) (+80,000 EUR, +16.0%)",
            "evidence_chunks": ["chunk_azure_001", "chunk_alloc_001"],
            "computed_values": {"delta": 80000.0, "pct": 16.0},
        },
        {
            "rule_violated": "R002",
            "severity": "CRITICAL",
            "description": "ISO27001 valid_to=2026-03-31 < period_end=2026-12-31",
            "evidence_chunks": ["chunk_cert_001"],
            "computed_values": {},
        },
    ]


@pytest.fixture()
def base_state() -> dict:
    return {
        "correlation_id": "test-corr-001",
        "trigger": "Verifica budget cloud Hera Q1 2026",
        "domain": "hera_it",
        "as_of_date": "2026-03-31",
        "errors": [],
    }
