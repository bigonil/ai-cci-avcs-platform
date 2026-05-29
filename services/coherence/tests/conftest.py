"""Shared fixtures for the Coherence Engine test suite."""
from __future__ import annotations

import pytest

from cci_coherence.models import EvaluationContext, ExtractedEntity


@pytest.fixture()
def hera_ctx_clean() -> EvaluationContext:
    """Context with no violations: commitment == allocation, cert valid."""
    ctx = EvaluationContext(domain="hera_it", as_of_date="2026-01-01")
    ctx.add(ExtractedEntity("CloudCommitment", "hera_it",
                            {"provider": "Azure", "amount_eur": 500_000, "period_end": "2026-12-31"},
                            chunk_ids=["c1"]))
    ctx.add(ExtractedEntity("CloudBudgetAllocation", "hera_it",
                            {"provider": "Azure", "allocated_eur": 580_000},
                            chunk_ids=["c2"]))
    ctx.add(ExtractedEntity("BudgetApproval", "hera_it",
                            {"amount_eur": 800_000},
                            chunk_ids=["c3"]))
    ctx.add(ExtractedEntity("ISO27001Certification", "hera_it",
                            {"valid_from": "2025-01-01", "valid_to": "2027-12-31"},
                            chunk_ids=["c4"]))
    return ctx


@pytest.fixture()
def hera_ctx_violations() -> EvaluationContext:
    """Context that triggers all four Hera rules."""
    ctx = EvaluationContext(domain="hera_it", as_of_date="2026-01-01")
    # R001: Azure commitment > allocation
    ctx.add(ExtractedEntity("CloudCommitment", "hera_it",
                            {"provider": "Azure", "amount_eur": 620_000, "period_end": "2026-12-31"},
                            chunk_ids=["c1"]))
    ctx.add(ExtractedEntity("CloudBudgetAllocation", "hera_it",
                            {"provider": "Azure", "allocated_eur": 580_000},
                            chunk_ids=["c2"]))
    # R002: cert expires before commitment
    ctx.add(ExtractedEntity("ISO27001Certification", "hera_it",
                            {"valid_from": "2025-01-01", "valid_to": "2026-06-30"},
                            chunk_ids=["c4"]))
    # R003: total commitments (620k + 200k) > approval (800k) ← barely NOT triggered
    # Use 620k + 250k = 870k > 800k to trigger it
    ctx.add(ExtractedEntity("CloudCommitment", "hera_it",
                            {"provider": "AWS", "amount_eur": 250_000, "period_end": "2026-12-31"},
                            chunk_ids=["c5"]))
    ctx.add(ExtractedEntity("BudgetApproval", "hera_it",
                            {"amount_eur": 800_000},
                            chunk_ids=["c3"]))
    # R004: Azure 620k / (620k+250k) = 71.3% > 70%
    return ctx


HERA_RULES = [
    {"rule_id": "R001", "when": "CloudCommitment.amount_eur > CloudBudgetAllocation.allocated_eur WHERE provider", "severity": "HIGH"},
    {"rule_id": "R002", "when": "ISO27001Certification.valid_to < CloudCommitment.period_end", "severity": "HIGH"},
    {"rule_id": "R003", "when": "sum(CloudCommitment.amount_eur) > BudgetApproval.amount_eur", "severity": "CRITICAL"},
    {"rule_id": "R004", "when": "concentration(CloudCommitment.amount_eur) > 0.70", "severity": "MEDIUM"},
]
