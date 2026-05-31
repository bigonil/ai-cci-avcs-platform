"""Deterministic rule evaluator — ZERO LLM (R4 enforced).

Maps each OntologyRule.when pattern to a Python evaluation function.
All comparisons are arithmetic or date-based; no probabilistic reasoning.

Supported patterns (auto-detected from `when` expression):
  SIMPLE_OVERRUN    — entity_a.value > entity_b.value (same join key)
  AGGREGATE_OVERRUN — sum(entity_a.values) > entity_b.value
  CERT_VALIDITY     — cert.valid_to < commitment.period_end
  CONCENTRATION     — entity.value / total > threshold (default 0.70)
  MISSING_RELATION  — entity exists without required related entity
"""
from __future__ import annotations

import re
from datetime import date
from typing import Any

import structlog

from cci_common.domain import Severity
from cci_coherence.models import (
    EvaluationContext,
    ExtractedEntity,
    RulePattern,
    RuleViolation,
)

log = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Pattern detection from `when` expression
# ---------------------------------------------------------------------------

_SUM_RE = re.compile(r"\bsum\s*\(", re.IGNORECASE)
_SLASH_RE = re.compile(r"[A-Za-z_]+\s*/\s*sum\s*\(", re.IGNORECASE)
_CERT_RE = re.compile(r"\b(valid_to|valid_from|cert|certification)\b", re.IGNORECASE)
_MISSING_RE = re.compile(r"\b(NOT\s+exists|missing|without)\b", re.IGNORECASE)
_GT_RE = re.compile(r">")
_COMPARISON_RE = re.compile(r"[<>]")


def detect_pattern(when_expr: str) -> RulePattern:
    if _SLASH_RE.search(when_expr) or "concentration" in when_expr.lower():
        return RulePattern.CONCENTRATION
    if _SUM_RE.search(when_expr) and _GT_RE.search(when_expr):
        return RulePattern.AGGREGATE_OVERRUN
    if _CERT_RE.search(when_expr) and _COMPARISON_RE.search(when_expr):
        return RulePattern.CERT_VALIDITY
    if _MISSING_RE.search(when_expr):
        return RulePattern.MISSING_RELATION
    if _GT_RE.search(when_expr):
        return RulePattern.SIMPLE_OVERRUN
    return RulePattern.UNKNOWN


# ---------------------------------------------------------------------------
# Pattern evaluators
# ---------------------------------------------------------------------------


def _date_cmp(d1: str | None, d2: str | None) -> int:
    """Compare two ISO date strings. Returns -1 / 0 / 1. None is treated as max date."""
    if d1 is None:
        return 1
    if d2 is None:
        return -1
    return (d1 > d2) - (d1 < d2)


def eval_simple_overrun(
    rule_id: str,
    severity: str,
    entity_a_type: str,
    entity_b_type: str,
    value_key_a: str,
    value_key_b: str,
    join_key: str,
    ctx: EvaluationContext,
) -> list[RuleViolation]:
    """entity_a.value_a > entity_b.value_b WHERE entity_a.join_key == entity_b.join_key."""
    violations: list[RuleViolation] = []
    for a in ctx.get(entity_a_type):
        a_val = a.get_float(value_key_a)
        join_val = a.get_str(join_key)
        # Find matching entity_b
        matched_b = [
            b for b in ctx.get(entity_b_type)
            if b.get_str(join_key) == join_val
        ]
        if not matched_b:
            continue
        b = matched_b[0]
        b_val = b.get_float(value_key_b)
        if a_val > b_val:
            delta = a_val - b_val
            pct = (delta / b_val * 100) if b_val else 0.0
            violations.append(RuleViolation(
                rule_id=rule_id,
                entity_a=a,
                entity_b=b,
                description=(
                    f"{entity_a_type}({join_val}, {a_val:,.0f}) > "
                    f"{entity_b_type}({join_val}, {b_val:,.0f}) "
                    f"(+{delta:,.0f} EUR, +{pct:.1f}%)"
                ),
                severity=severity,
                evidence_chunks=list(dict.fromkeys(a.chunk_ids + b.chunk_ids)),
                computed_values={"a_val": a_val, "b_val": b_val, "delta": delta, "pct": pct},
            ))
    return violations


def eval_aggregate_overrun(
    rule_id: str,
    severity: str,
    entity_a_type: str,
    entity_b_type: str,
    value_key_a: str,
    value_key_b: str,
    ctx: EvaluationContext,
) -> list[RuleViolation]:
    """sum(entity_a.values) > entity_b.value."""
    violations: list[RuleViolation] = []
    entities_a = ctx.get(entity_a_type)
    entities_b = ctx.get(entity_b_type)
    if not entities_a or not entities_b:
        return violations
    total_a = sum(e.get_float(value_key_a) for e in entities_a)
    b = entities_b[0]
    b_val = b.get_float(value_key_b)
    if total_a > b_val:
        delta = total_a - b_val
        pct = (delta / b_val * 100) if b_val else 0.0
        all_chunks = []
        for e in entities_a:
            all_chunks.extend(e.chunk_ids)
        all_chunks.extend(b.chunk_ids)
        violations.append(RuleViolation(
            rule_id=rule_id,
            entity_a=ExtractedEntity(
                entity_type=f"sum({entity_a_type})",
                domain=ctx.domain,
                properties={"total": total_a},
                chunk_ids=list(dict.fromkeys(all_chunks)),
            ),
            entity_b=b,
            description=(
                f"sum({entity_a_type}) = {total_a:,.0f} EUR > "
                f"{entity_b_type} = {b_val:,.0f} EUR "
                f"(+{delta:,.0f} EUR, +{pct:.1f}%)"
            ),
            severity=severity,
            evidence_chunks=list(dict.fromkeys(all_chunks)),
            computed_values={"total": total_a, "limit": b_val, "delta": delta, "pct": pct},
        ))
    return violations


def eval_cert_validity(
    rule_id: str,
    severity: str,
    commitment_type: str,
    cert_type: str,
    period_end_key: str,
    cert_valid_to_key: str,
    ctx: EvaluationContext,
) -> list[RuleViolation]:
    """cert.valid_to < commitment.period_end (cert expires before commitment ends)."""
    violations: list[RuleViolation] = []
    commitments = ctx.get(commitment_type)
    certs = ctx.get(cert_type)
    if not commitments:
        return violations
    if not certs:
        # No cert at all — always a violation
        for c in commitments:
            violations.append(RuleViolation(
                rule_id=rule_id,
                entity_a=c,
                entity_b=None,
                description=f"No {cert_type} found — {commitment_type} has no valid certification.",
                severity=severity,
                evidence_chunks=list(c.chunk_ids),
            ))
        return violations
    cert = certs[0]
    cert_valid_to = cert.get_date_str(cert_valid_to_key)
    for commitment in commitments:
        period_end = commitment.get_date_str(period_end_key)
        if not period_end or not cert_valid_to:
            continue
        if cert_valid_to < period_end:
            violations.append(RuleViolation(
                rule_id=rule_id,
                entity_a=commitment,
                entity_b=cert,
                description=(
                    f"{cert_type}.valid_to={cert_valid_to} < "
                    f"{commitment_type}.period_end={period_end} — "
                    f"certification expires before commitment ends."
                ),
                severity=severity,
                evidence_chunks=list(dict.fromkeys(commitment.chunk_ids + cert.chunk_ids)),
                computed_values={"cert_valid_to": cert_valid_to, "period_end": period_end},
            ))
    return violations


def eval_concentration(
    rule_id: str,
    severity: str,
    entity_type: str,
    value_key: str,
    threshold: float,
    ctx: EvaluationContext,
) -> list[RuleViolation]:
    """entity.value / sum(all entity.values) > threshold."""
    violations: list[RuleViolation] = []
    entities = ctx.get(entity_type)
    if len(entities) < 2:
        return violations
    total = sum(e.get_float(value_key) for e in entities)
    if total == 0:
        return violations
    for e in entities:
        val = e.get_float(value_key)
        pct = val / total
        if pct > threshold:
            violations.append(RuleViolation(
                rule_id=rule_id,
                entity_a=e,
                entity_b=None,
                description=(
                    f"{entity_type}({e.get_str('provider', e.entity_type)}) = "
                    f"{val:,.0f}/{total:,.0f} = {pct:.1%} > threshold {threshold:.0%}"
                ),
                severity=severity,
                evidence_chunks=list(e.chunk_ids),
                computed_values={"value": val, "total": total, "pct": pct, "threshold": threshold},
            ))
    return violations


# ---------------------------------------------------------------------------
# Rule dispatcher — maps OntologyRule to the right evaluator
# ---------------------------------------------------------------------------


def evaluate_rule(
    rule_id: str,
    when_expr: str,
    severity: str,
    domain: str,
    ctx: EvaluationContext,
) -> list[RuleViolation]:
    """Dispatch to the appropriate evaluator based on detected pattern.

    This is the ONLY entry point for rule evaluation. Fully deterministic — R4.
    """
    pattern = detect_pattern(when_expr)
    log.debug("rule_dispatch", rule_id=rule_id, pattern=pattern)

    # -----------------------------------------------------------------------
    # Domain-specific dispatching
    # Extends the generic patterns with domain entity type knowledge.
    # -----------------------------------------------------------------------

    if domain == "hera_it":
        return _evaluate_hera_rule(rule_id, when_expr, severity, pattern, ctx)
    if domain == "aou_clinical":
        return _evaluate_aou_rule(rule_id, severity, ctx)
    if domain == "semsotec_product":
        return _evaluate_semsotec_rule(rule_id, severity, ctx)
    if domain == "ducati_corse":
        return _evaluate_ducati_rule(rule_id, severity, ctx)
    if domain == "dallara":
        return _evaluate_dallara_rule(rule_id, severity, ctx)
    if domain == "prada":
        return _evaluate_prada_rule(rule_id, severity, ctx)

    log.warning("no_domain_dispatcher", domain=domain, rule_id=rule_id)
    return []


def _evaluate_hera_rule(
    rule_id: str,
    when_expr: str,
    severity: str,
    pattern: RulePattern,
    ctx: EvaluationContext,
) -> list[RuleViolation]:
    if rule_id == "R001" or (pattern == RulePattern.SIMPLE_OVERRUN and "provider" in when_expr):
        return eval_simple_overrun(
            rule_id=rule_id,
            severity=severity,
            entity_a_type="CloudCommitment",
            entity_b_type="CloudBudgetAllocation",
            value_key_a="amount_eur",
            value_key_b="allocated_eur",
            join_key="provider",
            ctx=ctx,
        )

    if rule_id == "R002" or pattern == RulePattern.CERT_VALIDITY:
        return eval_cert_validity(
            rule_id=rule_id,
            severity=severity,
            commitment_type="CloudCommitment",
            cert_type="ISO27001Certification",
            period_end_key="period_end",
            cert_valid_to_key="valid_to",
            ctx=ctx,
        )

    if rule_id == "R003" or pattern == RulePattern.AGGREGATE_OVERRUN:
        return eval_aggregate_overrun(
            rule_id=rule_id,
            severity=severity,
            entity_a_type="CloudCommitment",
            entity_b_type="BudgetApproval",
            value_key_a="amount_eur",
            value_key_b="amount_eur",
            ctx=ctx,
        )

    if rule_id == "R004" or pattern == RulePattern.CONCENTRATION:
        return eval_concentration(
            rule_id=rule_id,
            severity=severity,
            entity_type="CloudCommitment",
            value_key="amount_eur",
            threshold=0.70,
            ctx=ctx,
        )

    log.warning("unknown_hera_rule", rule_id=rule_id)
    return []


# ---------------------------------------------------------------------------
# AOU Clinical — C001
# ---------------------------------------------------------------------------

def _evaluate_aou_rule(
    rule_id: str,
    severity: str,
    ctx: EvaluationContext,
) -> list[RuleViolation]:
    today = date.today().isoformat()
    violations: list[RuleViolation] = []

    if rule_id == "C001":
        # ACTIVE trial must have a valid ethics approval (valid_to >= today)
        for trial in ctx.get("ClinicalTrial"):
            approvals = ctx.get("EthicsApproval")
            valid_approvals = [
                a for a in approvals
                if a.get_date_str("valid_to") and a.get_date_str("valid_to") >= today
            ]
            if not valid_approvals:
                # Find best evidence: the expired approval if available
                expired = approvals[0] if approvals else None
                all_chunks = list(trial.chunk_ids)
                if expired:
                    all_chunks.extend(expired.chunk_ids)
                expiry = expired.get_date_str("valid_to") if expired else "N/A"
                violations.append(RuleViolation(
                    rule_id=rule_id,
                    entity_a=trial,
                    entity_b=expired,
                    description=(
                        f"ClinicalTrial({trial.get_str('trial_id')}, ACTIVE) — "
                        f"EthicsApproval expired {expiry}, no valid renewal as of {today}"
                    ),
                    severity=severity,
                    evidence_chunks=list(dict.fromkeys(all_chunks)),
                    computed_values={"trial_id": trial.get_str("trial_id"), "expired_approval": expiry, "today": today},
                ))
    return violations


# ---------------------------------------------------------------------------
# SEMSOTEC — P001
# ---------------------------------------------------------------------------

def _evaluate_semsotec_rule(
    rule_id: str,
    severity: str,
    ctx: EvaluationContext,
) -> list[RuleViolation]:
    today = date.today().isoformat()
    violations: list[RuleViolation] = []

    if rule_id == "P001":
        # ON_MARKET product must have a valid cert (valid_to >= today)
        for product in ctx.get("Product"):
            certs = ctx.get("ProductCertification")
            valid_certs = [
                c for c in certs
                if c.get_date_str("valid_to") and c.get_date_str("valid_to") >= today
            ]
            if not valid_certs:
                expired = certs[0] if certs else None
                all_chunks = list(product.chunk_ids)
                if expired:
                    all_chunks.extend(expired.chunk_ids)
                expiry = expired.get_date_str("valid_to") if expired else "N/A"
                violations.append(RuleViolation(
                    rule_id=rule_id,
                    entity_a=product,
                    entity_b=expired,
                    description=(
                        f"Product({product.get_str('product_id')}, ON_MARKET) — "
                        f"ProductCertification expired {expiry}, no valid cert as of {today}"
                    ),
                    severity=severity,
                    evidence_chunks=list(dict.fromkeys(all_chunks)),
                    computed_values={"product_id": product.get_str("product_id"), "expired_cert": expiry, "today": today},
                ))
    return violations


# ---------------------------------------------------------------------------
# Ducati Corse — DC001, DC002, DC003
# ---------------------------------------------------------------------------

def _evaluate_ducati_rule(
    rule_id: str,
    severity: str,
    ctx: EvaluationContext,
) -> list[RuleViolation]:
    today = date.today().isoformat()
    violations: list[RuleViolation] = []

    if rule_id == "DC001":
        # IN_RACE component must have valid homologation covering the full season
        for comp in ctx.get("RaceComponent"):
            season = comp.get_str("season")  # e.g. "2026"
            season_end = f"{season}-12-31"
            certs = ctx.get("HomologationCertificate")
            valid_certs = [
                c for c in certs
                if c.get_date_str("valid_to") and c.get_date_str("valid_to") >= season_end
            ]
            if not valid_certs:
                expired = certs[0] if certs else None
                all_chunks = list(comp.chunk_ids)
                if expired:
                    all_chunks.extend(expired.chunk_ids)
                expiry = expired.get_date_str("valid_to") if expired else "N/A"
                violations.append(RuleViolation(
                    rule_id=rule_id,
                    entity_a=comp,
                    entity_b=expired,
                    description=(
                        f"RaceComponent({comp.get_str('component_id')}, IN_RACE, season={season}) — "
                        f"HomologationCertificate valid_to={expiry} < season_end={season_end}"
                    ),
                    severity=severity,
                    evidence_chunks=list(dict.fromkeys(all_chunks)),
                    computed_values={"component_id": comp.get_str("component_id"), "cert_valid_to": expiry, "season_end": season_end},
                ))

    elif rule_id == "DC002":
        # declared_amount_eur > cap_limit_eur
        for decl in ctx.get("BudgetCapDeclaration"):
            declared = decl.get_float("declared_amount_eur")
            cap = decl.get_float("cap_limit_eur")
            if declared > cap:
                delta = declared - cap
                pct = (delta / cap * 100) if cap else 0.0
                violations.append(RuleViolation(
                    rule_id=rule_id,
                    entity_a=decl,
                    entity_b=None,
                    description=(
                        f"BudgetCapDeclaration(season={decl.get_str('season')}) — "
                        f"declared={declared:,.0f} EUR > cap={cap:,.0f} EUR "
                        f"(+{delta:,.0f} EUR, +{pct:.1f}%)"
                    ),
                    severity=severity,
                    evidence_chunks=list(decl.chunk_ids),
                    computed_values={"declared": declared, "cap": cap, "delta": delta, "pct": pct},
                ))

    elif rule_id == "DC003":
        # tokens_remaining = 0 (all tokens consumed — zero development margin)
        for alloc in ctx.get("DevelopmentTokenAllocation"):
            remaining = alloc.get_float("tokens_remaining")
            used = alloc.get_float("tokens_used")
            total = alloc.get_float("total_tokens")
            if remaining <= 0:
                violations.append(RuleViolation(
                    rule_id=rule_id,
                    entity_a=alloc,
                    entity_b=None,
                    description=(
                        f"DevelopmentTokenAllocation(season={alloc.get_str('season')}) — "
                        f"tokens_used={int(used)}/{int(total)}, remaining={int(remaining)} — "
                        f"zero development margin"
                    ),
                    severity=severity,
                    evidence_chunks=list(alloc.chunk_ids),
                    computed_values={"used": used, "total": total, "remaining": remaining},
                ))

    return violations


# ---------------------------------------------------------------------------
# Dallara — DA001
# ---------------------------------------------------------------------------

def _evaluate_dallara_rule(
    rule_id: str,
    severity: str,
    ctx: EvaluationContext,
) -> list[RuleViolation]:
    today = date.today().isoformat()
    violations: list[RuleViolation] = []

    if rule_id == "DA001":
        # IN_COMPETITION vehicle must have valid crash test cert covering current date
        for vehicle in ctx.get("Vehicle"):
            certs = ctx.get("CrashTestCertification")
            valid_certs = [
                c for c in certs
                if c.get_date_str("valid_to") and c.get_date_str("valid_to") >= today
            ]
            if not valid_certs:
                expired = certs[0] if certs else None
                all_chunks = list(vehicle.chunk_ids)
                if expired:
                    all_chunks.extend(expired.chunk_ids)
                expiry = expired.get_date_str("valid_to") if expired else "N/A"
                violations.append(RuleViolation(
                    rule_id=rule_id,
                    entity_a=vehicle,
                    entity_b=expired,
                    description=(
                        f"Vehicle({vehicle.get_str('vehicle_id')}, IN_COMPETITION) — "
                        f"CrashTestCertification expired {expiry}, no valid cert as of {today}"
                    ),
                    severity=severity,
                    evidence_chunks=list(dict.fromkeys(all_chunks)),
                    computed_values={"vehicle_id": vehicle.get_str("vehicle_id"), "cert_valid_to": expiry, "today": today},
                ))
    return violations


# ---------------------------------------------------------------------------
# Prada — PR002, PR003
# ---------------------------------------------------------------------------

def _evaluate_prada_rule(
    rule_id: str,
    severity: str,
    ctx: EvaluationContext,
) -> list[RuleViolation]:
    today = date.today().isoformat()
    violations: list[RuleViolation] = []

    if rule_id == "PR002":
        # Tier-1 supplier with PENDING ethical audit status
        for supplier in ctx.get("Supplier"):
            if supplier.get_float("tier") == 1.0:
                audit_status = supplier.get_str("ethical_audit_status")
                if audit_status in ("PENDING", "NON_COMPLIANT", ""):
                    violations.append(RuleViolation(
                        rule_id=rule_id,
                        entity_a=supplier,
                        entity_b=None,
                        description=(
                            f"Supplier({supplier.get_str('name')}, tier=1) — "
                            f"ethical_audit_status={audit_status or 'MISSING'}"
                        ),
                        severity=severity,
                        evidence_chunks=list(supplier.chunk_ids),
                        computed_values={"supplier": supplier.get_str("name"), "audit_status": audit_status},
                    ))

    elif rule_id == "PR003":
        # Tier-1 supplier with expired material certification
        for cert in ctx.get("MaterialCertification"):
            if cert.properties.get("expired"):
                valid_to = cert.get_date_str("valid_to") or "N/A"
                # Find the matching supplier
                supplier_name = cert.get_str("supplier_name")
                matching = [
                    s for s in ctx.get("Supplier")
                    if s.get_str("name").startswith(supplier_name[:10])
                    and s.get_float("tier") == 1.0
                ]
                supplier = matching[0] if matching else None
                all_chunks = list(cert.chunk_ids)
                if supplier:
                    all_chunks.extend(supplier.chunk_ids)
                violations.append(RuleViolation(
                    rule_id=rule_id,
                    entity_a=cert,
                    entity_b=supplier,
                    description=(
                        f"Supplier({supplier_name}, tier=1) — "
                        f"MaterialCertification({cert.get_str('cert_id')}) expired {valid_to}, "
                        f"production in {today[:4]}"
                    ),
                    severity=severity,
                    evidence_chunks=list(dict.fromkeys(all_chunks)),
                    computed_values={"cert_id": cert.get_str("cert_id"), "valid_to": valid_to, "production_year": today[:4]},
                ))

    return violations
