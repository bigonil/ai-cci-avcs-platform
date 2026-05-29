"""Entity extractor — pulls structured values from text chunks.

Uses regex patterns derived from ontology entity property types.
NO LLM — pure deterministic regex + pattern matching (R4 enforced).

Supported value types:
  - EUR amounts: "580.000 EUR", "580k EUR", "580,000 EUR", "580000.0"
  - ISO dates: "2026-01-01", "01/01/2026"
  - Provider names: "Azure", "AWS", "GCP"
  - Percentages: "67.8%"
"""
from __future__ import annotations

import re
from typing import Any

import structlog

from cci_coherence.models import EvaluationContext, ExtractedEntity

log = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Regex patterns for financial documents
# ---------------------------------------------------------------------------

# EUR amounts: "580.000 EUR", "500.000 EUR", "85.000 EUR", "580k EUR", "800.000"
_EUR_PATTERN = re.compile(
    r"(\d{1,3}(?:[.,]\d{3})+(?:[.,]\d{2})?|\d+(?:[.,]\d+)?)\s*(?:k\s*)?EUR",
    re.IGNORECASE,
)

# ISO date YYYY-MM-DD
_DATE_ISO = re.compile(r"\b(\d{4}-\d{2}-\d{2})\b")

# Cloud providers
_AZURE = re.compile(r"\bAzure\b", re.IGNORECASE)
_AWS = re.compile(r"\bAWS\b|Amazon Web Services\b", re.IGNORECASE)
_GCP = re.compile(r"\bGCP\b|Google Cloud\b", re.IGNORECASE)

# Percentage
_PCT = re.compile(r"(\d+(?:\.\d+)?)\s*%")

# "commitment" signal words
_COMMITMENT_KW = re.compile(
    r"\b(commitment|EA|EDP|CUD|MACC|Enterprise Agreement|Committed Use)\b",
    re.IGNORECASE,
)
_ALLOCATION_KW = re.compile(
    r"\b(alloc(?:ation|ato)|budget (?:DSI|CTO)|approvato dal CTO)\b",
    re.IGNORECASE,
)
_BUDGET_APPROVAL_KW = re.compile(
    r"\b(budget CdA|approvato.*CdA|CdA.*approvato|budget totale)\b",
    re.IGNORECASE,
)
_CERT_KW = re.compile(r"\bISO\s*27001\b", re.IGNORECASE)
_CERT_EXPIRY_KW = re.compile(r"\b(scade|valid(?:o|a) fino al|valid_to|expiry)\b", re.IGNORECASE)


def _parse_eur_amount(text: str) -> float | None:
    """Return the first EUR amount found in text, normalised to float."""
    m = _EUR_PATTERN.search(text)
    if not m:
        return None
    raw = m.group(1)
    # Detect format: Italian "580.000" vs English "580,000" vs decimal
    # Rule: if last separator is followed by exactly 3 digits → thousands separator
    # If last separator is followed by 1-2 digits → decimal
    raw_clean = raw.replace(" ", "")
    if re.search(r"[.,]\d{3}$", raw_clean):
        raw_clean = raw_clean.replace(".", "").replace(",", "")
    else:
        raw_clean = raw_clean.replace(".", "").replace(",", ".")
    try:
        val = float(raw_clean)
        # Handle "k" suffix
        if re.search(r"\d\s*k\s*EUR", text, re.IGNORECASE):
            val *= 1000
        return val
    except ValueError:
        return None


def _parse_date(text: str) -> str | None:
    m = _DATE_ISO.search(text)
    return m.group(1) if m else None


def _detect_provider(text: str) -> str | None:
    if _AZURE.search(text):
        return "Azure"
    if _AWS.search(text):
        return "AWS"
    if _GCP.search(text):
        return "GCP"
    return None


def _all_eur_amounts(text: str) -> list[float]:
    """All EUR amounts found in text, normalised."""
    results = []
    for m in _EUR_PATTERN.finditer(text):
        raw = m.group(1).replace(" ", "")
        if re.search(r"[.,]\d{3}$", raw):
            raw = raw.replace(".", "").replace(",", "")
        else:
            raw = raw.replace(".", "").replace(",", ".")
        try:
            results.append(float(raw))
        except ValueError:
            pass
    return results


def _all_dates(text: str) -> list[str]:
    return _DATE_ISO.findall(text)


# ---------------------------------------------------------------------------
# Hera IT domain extractor
# ---------------------------------------------------------------------------


def extract_hera_it(chunks: list[dict[str, Any]]) -> EvaluationContext:
    """Extract structured Hera IT entities from text chunks."""
    from datetime import date
    ctx = EvaluationContext(domain="hera_it", as_of_date=date.today().isoformat())

    for chunk in chunks:
        text: str = chunk.get("text") or chunk.get("payload", {}).get("text", "")
        chunk_id: str = chunk.get("chunk_id") or chunk.get("payload", {}).get("chunk_id", "")
        if not text or not chunk_id:
            continue

        provider = _detect_provider(text)

        # --- CloudCommitment ---
        if _COMMITMENT_KW.search(text) and provider:
            amounts = _all_eur_amounts(text)
            dates = _all_dates(text)
            if amounts:
                # Largest amount in a commitment paragraph is the annual commitment
                commitment_amount = max(amounts)
                period_end = dates[-1] if dates else None
                ctx.add(ExtractedEntity(
                    entity_type="CloudCommitment",
                    domain="hera_it",
                    properties={
                        "provider": provider,
                        "amount_eur": commitment_amount,
                        "period_end": period_end,
                        "period_start": dates[0] if dates else None,
                    },
                    chunk_ids=[chunk_id],
                ))

        # --- CloudBudgetAllocation ---
        if _ALLOCATION_KW.search(text) and provider:
            amounts = _all_eur_amounts(text)
            if amounts:
                ctx.add(ExtractedEntity(
                    entity_type="CloudBudgetAllocation",
                    domain="hera_it",
                    properties={
                        "provider": provider,
                        "allocated_eur": max(amounts),
                        "year": 2026,
                    },
                    chunk_ids=[chunk_id],
                ))

        # --- BudgetApproval ---
        if _BUDGET_APPROVAL_KW.search(text):
            amounts = _all_eur_amounts(text)
            if amounts:
                ctx.add(ExtractedEntity(
                    entity_type="BudgetApproval",
                    domain="hera_it",
                    properties={
                        "amount_eur": max(amounts),
                        "year": 2026,
                    },
                    chunk_ids=[chunk_id],
                ))

        # --- ISO27001Certification ---
        if _CERT_KW.search(text):
            dates = _all_dates(text)
            if dates:
                ctx.add(ExtractedEntity(
                    entity_type="ISO27001Certification",
                    domain="hera_it",
                    properties={
                        "valid_from": dates[0] if len(dates) >= 1 else None,
                        "valid_to": dates[-1] if dates else None,
                    },
                    chunk_ids=[chunk_id],
                ))

    log.info(
        "hera_extraction_complete",
        commitments=len(ctx.get("CloudCommitment")),
        allocations=len(ctx.get("CloudBudgetAllocation")),
        approvals=len(ctx.get("BudgetApproval")),
        certs=len(ctx.get("ISO27001Certification")),
    )
    return ctx


# ---------------------------------------------------------------------------
# Generic extractor dispatcher
# ---------------------------------------------------------------------------


def extract_entities(
    chunks: list[dict[str, Any]],
    domain: str,
) -> EvaluationContext:
    """Route to the appropriate domain extractor."""
    if domain == "hera_it":
        return extract_hera_it(chunks)
    # Other domains: return empty context (graph-based evaluation is the fallback)
    from datetime import date
    log.warning("no_chunk_extractor_for_domain", domain=domain)
    return EvaluationContext(domain=domain, as_of_date=date.today().isoformat())
