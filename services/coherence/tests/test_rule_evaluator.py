"""Tests for the deterministic rule evaluator (R4: zero LLM)."""
from __future__ import annotations

import pytest

from cci_coherence.models import EvaluationContext, ExtractedEntity, RulePattern
from cci_coherence.rule_evaluator import (
    detect_pattern,
    eval_aggregate_overrun,
    eval_cert_validity,
    eval_concentration,
    eval_simple_overrun,
    evaluate_rule,
)
from tests.conftest import HERA_RULES


# ---------------------------------------------------------------------------
# Pattern detection
# ---------------------------------------------------------------------------

class TestDetectPattern:
    def test_simple_overrun(self):
        assert detect_pattern("entity_a.value > entity_b.value") == RulePattern.SIMPLE_OVERRUN

    def test_aggregate_overrun(self):
        assert detect_pattern("sum(commitments.amount) > approval.limit") == RulePattern.AGGREGATE_OVERRUN

    def test_cert_validity(self):
        assert detect_pattern("cert.valid_to < commitment.period_end") == RulePattern.CERT_VALIDITY

    def test_concentration_slash(self):
        assert detect_pattern("provider.amount / sum(total) > 0.7") == RulePattern.CONCENTRATION

    def test_concentration_keyword(self):
        assert detect_pattern("concentration(CloudCommitment.amount_eur) > 0.70") == RulePattern.CONCENTRATION

    def test_missing_relation(self):
        assert detect_pattern("entity NOT exists without certification") == RulePattern.MISSING_RELATION

    def test_unknown(self):
        assert detect_pattern("no recognizable pattern here") == RulePattern.UNKNOWN


# ---------------------------------------------------------------------------
# Simple overrun evaluator
# ---------------------------------------------------------------------------

class TestSimpleOverrun:
    def _make_ctx(self, commitment_eur: float, allocation_eur: float) -> EvaluationContext:
        ctx = EvaluationContext(domain="hera_it", as_of_date="2026-01-01")
        ctx.add(ExtractedEntity("CloudCommitment", "hera_it",
                                {"provider": "Azure", "amount_eur": commitment_eur}, ["c1"]))
        ctx.add(ExtractedEntity("CloudBudgetAllocation", "hera_it",
                                {"provider": "Azure", "allocated_eur": allocation_eur}, ["c2"]))
        return ctx

    def test_violation_detected(self):
        ctx = self._make_ctx(620_000, 580_000)
        violations = eval_simple_overrun(
            "R001", "HIGH", "CloudCommitment", "CloudBudgetAllocation",
            "amount_eur", "allocated_eur", "provider", ctx,
        )
        assert len(violations) == 1
        assert violations[0].rule_id == "R001"
        assert violations[0].computed_values["delta"] == pytest.approx(40_000)

    def test_no_violation_equal(self):
        ctx = self._make_ctx(580_000, 580_000)
        violations = eval_simple_overrun(
            "R001", "HIGH", "CloudCommitment", "CloudBudgetAllocation",
            "amount_eur", "allocated_eur", "provider", ctx,
        )
        assert violations == []

    def test_no_violation_under(self):
        ctx = self._make_ctx(500_000, 580_000)
        violations = eval_simple_overrun(
            "R001", "HIGH", "CloudCommitment", "CloudBudgetAllocation",
            "amount_eur", "allocated_eur", "provider", ctx,
        )
        assert violations == []

    def test_no_matching_b(self):
        ctx = EvaluationContext(domain="hera_it", as_of_date="2026-01-01")
        ctx.add(ExtractedEntity("CloudCommitment", "hera_it",
                                {"provider": "Azure", "amount_eur": 620_000}, ["c1"]))
        violations = eval_simple_overrun(
            "R001", "HIGH", "CloudCommitment", "CloudBudgetAllocation",
            "amount_eur", "allocated_eur", "provider", ctx,
        )
        assert violations == []


# ---------------------------------------------------------------------------
# Aggregate overrun evaluator
# ---------------------------------------------------------------------------

class TestAggregateOverrun:
    def _make_ctx(self, commitment_amounts: list[float], approval: float) -> EvaluationContext:
        ctx = EvaluationContext(domain="hera_it", as_of_date="2026-01-01")
        for i, amt in enumerate(commitment_amounts):
            ctx.add(ExtractedEntity("CloudCommitment", "hera_it",
                                    {"amount_eur": amt}, [f"c{i}"]))
        ctx.add(ExtractedEntity("BudgetApproval", "hera_it", {"amount_eur": approval}, ["ca"]))
        return ctx

    def test_violation_detected(self):
        ctx = self._make_ctx([580_000, 190_000, 85_000], 800_000)
        violations = eval_aggregate_overrun(
            "R003", "CRITICAL", "CloudCommitment", "BudgetApproval",
            "amount_eur", "amount_eur", ctx,
        )
        assert len(violations) == 1
        assert violations[0].computed_values["total"] == pytest.approx(855_000)
        assert violations[0].computed_values["delta"] == pytest.approx(55_000)

    def test_no_violation(self):
        ctx = self._make_ctx([300_000, 200_000], 800_000)
        violations = eval_aggregate_overrun(
            "R003", "CRITICAL", "CloudCommitment", "BudgetApproval",
            "amount_eur", "amount_eur", ctx,
        )
        assert violations == []

    def test_empty_context(self):
        ctx = EvaluationContext(domain="hera_it", as_of_date="2026-01-01")
        violations = eval_aggregate_overrun(
            "R003", "CRITICAL", "CloudCommitment", "BudgetApproval",
            "amount_eur", "amount_eur", ctx,
        )
        assert violations == []


# ---------------------------------------------------------------------------
# Cert validity evaluator
# ---------------------------------------------------------------------------

class TestCertValidity:
    def _make_ctx(self, period_end: str, cert_valid_to: str | None) -> EvaluationContext:
        ctx = EvaluationContext(domain="hera_it", as_of_date="2026-01-01")
        ctx.add(ExtractedEntity("CloudCommitment", "hera_it",
                                {"period_end": period_end}, ["c1"]))
        if cert_valid_to is not None:
            ctx.add(ExtractedEntity("ISO27001Certification", "hera_it",
                                    {"valid_to": cert_valid_to}, ["c4"]))
        return ctx

    def test_cert_expires_before_commitment(self):
        ctx = self._make_ctx("2026-12-31", "2026-06-30")
        violations = eval_cert_validity(
            "R002", "HIGH", "CloudCommitment", "ISO27001Certification",
            "period_end", "valid_to", ctx,
        )
        assert len(violations) == 1

    def test_cert_valid_past_commitment(self):
        ctx = self._make_ctx("2026-12-31", "2027-12-31")
        violations = eval_cert_validity(
            "R002", "HIGH", "CloudCommitment", "ISO27001Certification",
            "period_end", "valid_to", ctx,
        )
        assert violations == []

    def test_no_cert_is_violation(self):
        ctx = self._make_ctx("2026-12-31", None)
        violations = eval_cert_validity(
            "R002", "HIGH", "CloudCommitment", "ISO27001Certification",
            "period_end", "valid_to", ctx,
        )
        assert len(violations) == 1
        assert "No ISO27001Certification" in violations[0].description

    def test_no_commitment_no_violation(self):
        ctx = EvaluationContext(domain="hera_it", as_of_date="2026-01-01")
        violations = eval_cert_validity(
            "R002", "HIGH", "CloudCommitment", "ISO27001Certification",
            "period_end", "valid_to", ctx,
        )
        assert violations == []


# ---------------------------------------------------------------------------
# Concentration evaluator
# ---------------------------------------------------------------------------

class TestConcentration:
    def _make_ctx(self, amounts: list[float]) -> EvaluationContext:
        ctx = EvaluationContext(domain="hera_it", as_of_date="2026-01-01")
        providers = ["Azure", "AWS", "GCP"]
        for i, amt in enumerate(amounts):
            ctx.add(ExtractedEntity("CloudCommitment", "hera_it",
                                    {"provider": providers[i % 3], "amount_eur": amt},
                                    [f"c{i}"]))
        return ctx

    def test_concentration_violation(self):
        # Azure 620k / (620k+85k+85k) ≈ 78.5% > 70%
        ctx = self._make_ctx([620_000, 85_000, 85_000])
        violations = eval_concentration("R004", "MEDIUM", "CloudCommitment", "amount_eur", 0.70, ctx)
        assert len(violations) == 1
        assert violations[0].computed_values["pct"] > 0.70

    def test_balanced_no_violation(self):
        ctx = self._make_ctx([300_000, 300_000, 200_000])
        violations = eval_concentration("R004", "MEDIUM", "CloudCommitment", "amount_eur", 0.70, ctx)
        assert violations == []

    def test_single_entity_no_violation(self):
        # Need ≥ 2 entities
        ctx = EvaluationContext(domain="hera_it", as_of_date="2026-01-01")
        ctx.add(ExtractedEntity("CloudCommitment", "hera_it", {"amount_eur": 800_000}, ["c1"]))
        violations = eval_concentration("R004", "MEDIUM", "CloudCommitment", "amount_eur", 0.70, ctx)
        assert violations == []


# ---------------------------------------------------------------------------
# End-to-end dispatcher
# ---------------------------------------------------------------------------

class TestEvaluateRule:
    def test_r001_dispatched(self, hera_ctx_violations):
        v = evaluate_rule("R001", HERA_RULES[0]["when"], "HIGH", "hera_it", hera_ctx_violations)
        assert any(x.rule_id == "R001" for x in v)

    def test_r002_dispatched(self, hera_ctx_violations):
        v = evaluate_rule("R002", HERA_RULES[1]["when"], "HIGH", "hera_it", hera_ctx_violations)
        assert any(x.rule_id == "R002" for x in v)

    def test_r003_dispatched(self, hera_ctx_violations):
        v = evaluate_rule("R003", HERA_RULES[2]["when"], "CRITICAL", "hera_it", hera_ctx_violations)
        assert any(x.rule_id == "R003" for x in v)

    def test_r004_dispatched(self, hera_ctx_violations):
        v = evaluate_rule("R004", HERA_RULES[3]["when"], "MEDIUM", "hera_it", hera_ctx_violations)
        assert any(x.rule_id == "R004" for x in v)

    def test_unknown_domain_returns_empty(self, hera_ctx_clean):
        v = evaluate_rule("R001", ">", "HIGH", "unknown_domain", hera_ctx_clean)
        assert v == []

    def test_clean_context_no_violations(self, hera_ctx_clean):
        for rule in HERA_RULES:
            v = evaluate_rule(rule["rule_id"], rule["when"], rule["severity"], "hera_it", hera_ctx_clean)
            assert v == [], f"Unexpected violation for {rule['rule_id']} in clean context"
