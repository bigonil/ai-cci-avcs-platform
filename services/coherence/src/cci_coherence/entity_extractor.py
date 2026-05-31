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
# AOU Clinical domain extractor
# ---------------------------------------------------------------------------

_TRIAL_ACTIVE = re.compile(r"STATO\s*:\s*ACTIVE", re.IGNORECASE)
_TRIAL_ID = re.compile(r"TRIAL\s+ID\s*:\s*(\S+)", re.IGNORECASE)
_ETHICS_APPROVAL_ID = re.compile(r"Numero parere\s*:\s*(\S+)", re.IGNORECASE)
_VALID_TO_KW = re.compile(r"(?:Data fine validit[àa]|valid_to|Valida al|Data scadenza)\s*[:\-]\s*(\d{4}-\d{2}-\d{2})", re.IGNORECASE)
_VALID_FROM_KW = re.compile(r"(?:Data inizio validit[àa]|valid_from|Data emissione)\s*[:\-]\s*(\d{4}-\d{2}-\d{2})", re.IGNORECASE)


def extract_aou_clinical(chunks: list[dict[str, Any]]) -> EvaluationContext:
    from datetime import date
    ctx = EvaluationContext(domain="aou_clinical", as_of_date=date.today().isoformat())

    for chunk in chunks:
        text: str = chunk.get("text") or chunk.get("payload", {}).get("text", "")
        chunk_id: str = chunk.get("chunk_id") or chunk.get("payload", {}).get("chunk_id", "")
        if not text or not chunk_id:
            continue

        # ClinicalTrial — active trial record
        if _TRIAL_ACTIVE.search(text):
            trial_id_m = _TRIAL_ID.search(text)
            dates = _all_dates(text)
            ctx.add(ExtractedEntity(
                entity_type="ClinicalTrial",
                domain="aou_clinical",
                properties={
                    "trial_id": trial_id_m.group(1) if trial_id_m else "unknown",
                    "status": "ACTIVE",
                    "start_date": dates[0] if dates else None,
                },
                chunk_ids=[chunk_id],
            ))

        # EthicsApproval
        if _ETHICS_APPROVAL_ID.search(text):
            approval_m = _ETHICS_APPROVAL_ID.search(text)
            valid_to_m = _VALID_TO_KW.search(text)
            valid_from_m = _VALID_FROM_KW.search(text)
            ctx.add(ExtractedEntity(
                entity_type="EthicsApproval",
                domain="aou_clinical",
                properties={
                    "approval_ref": approval_m.group(1) if approval_m else "unknown",
                    "valid_from": valid_from_m.group(1) if valid_from_m else None,
                    "valid_to": valid_to_m.group(1) if valid_to_m else None,
                },
                chunk_ids=[chunk_id],
            ))

    log.info("aou_extraction_complete",
             trials=len(ctx.get("ClinicalTrial")),
             approvals=len(ctx.get("EthicsApproval")))
    return ctx


# ---------------------------------------------------------------------------
# SEMSOTEC Product domain extractor
# ---------------------------------------------------------------------------

_ON_MARKET = re.compile(r"Stato commerciale\s*:\s*ON_MARKET", re.IGNORECASE)
_PRODUCT_CODE = re.compile(r"Codice interno\s*:\s*(\S+)", re.IGNORECASE)
_CERT_NUMBER = re.compile(r"Numero certificato\s*:\s*(\S+)", re.IGNORECASE)
_CERT_FOR_PRODUCT = re.compile(r"Prodotto\s*:[^\n]*\(([^)]+)\)", re.IGNORECASE)


def extract_semsotec_product(chunks: list[dict[str, Any]]) -> EvaluationContext:
    from datetime import date
    ctx = EvaluationContext(domain="semsotec_product", as_of_date=date.today().isoformat())

    for chunk in chunks:
        text: str = chunk.get("text") or chunk.get("payload", {}).get("text", "")
        chunk_id: str = chunk.get("chunk_id") or chunk.get("payload", {}).get("chunk_id", "")
        if not text or not chunk_id:
            continue

        # Product on market
        if _ON_MARKET.search(text):
            code_m = _PRODUCT_CODE.search(text)
            ctx.add(ExtractedEntity(
                entity_type="Product",
                domain="semsotec_product",
                properties={
                    "product_id": code_m.group(1) if code_m else "unknown",
                    "status": "ON_MARKET",
                },
                chunk_ids=[chunk_id],
            ))

        # ProductCertification
        if _CERT_NUMBER.search(text):
            cert_m = _CERT_NUMBER.search(text)
            valid_to_m = _VALID_TO_KW.search(text)
            valid_from_m = _VALID_FROM_KW.search(text)
            prod_m = _CERT_FOR_PRODUCT.search(text)
            ctx.add(ExtractedEntity(
                entity_type="ProductCertification",
                domain="semsotec_product",
                properties={
                    "cert_id": cert_m.group(1) if cert_m else "unknown",
                    "product_id": prod_m.group(1) if prod_m else "unknown",
                    "valid_from": valid_from_m.group(1) if valid_from_m else None,
                    "valid_to": valid_to_m.group(1) if valid_to_m else None,
                },
                chunk_ids=[chunk_id],
            ))

    log.info("semsotec_extraction_complete",
             products=len(ctx.get("Product")),
             certs=len(ctx.get("ProductCertification")))
    return ctx


# ---------------------------------------------------------------------------
# Ducati Corse domain extractor
# ---------------------------------------------------------------------------

_IN_RACE = re.compile(r"Stato\s*:\s*IN_RACE", re.IGNORECASE)
_COMPONENTE_ID = re.compile(r"COMPONENTE\s*:\s*(\S+)", re.IGNORECASE)
_SEASON = re.compile(r"Stagione\s*:\s*(\d{4})", re.IGNORECASE)
_FIM_CERT = re.compile(r"Numero certificato\s*:\s*(FIM-\S+)", re.IGNORECASE)
_TOKENS_USED = re.compile(r"Token utilizzati[^\n]*:\s*(\d+)", re.IGNORECASE)
_TOKENS_TOTAL = re.compile(r"Allocazione FIM totale stagione \d+:\s*(\d+)\s*token", re.IGNORECASE)
_TOKENS_REMAINING = re.compile(r"Token rimanenti\s*:\s*(\d+)", re.IGNORECASE)
_BUDGET_DECLARED = re.compile(r"TOTALE DICHIARATO\s*:\s*([0-9.,]+)\s*EUR", re.IGNORECASE)
_BUDGET_CAP = re.compile(r"LIMITE BUDGET CAP FIM[^\n]*:\s*([0-9.,]+)\s*EUR", re.IGNORECASE)


def _parse_eur_raw(raw: str) -> float:
    """Parse '13.200.000' or '13,200,000' style EUR amount."""
    raw = raw.replace(" ", "")
    if re.search(r"[.,]\d{3}$", raw):
        return float(raw.replace(".", "").replace(",", ""))
    return float(raw.replace(".", "").replace(",", "."))


def extract_ducati_corse(chunks: list[dict[str, Any]]) -> EvaluationContext:
    from datetime import date
    ctx = EvaluationContext(domain="ducati_corse", as_of_date=date.today().isoformat())

    for chunk in chunks:
        text: str = chunk.get("text") or chunk.get("payload", {}).get("text", "")
        chunk_id: str = chunk.get("chunk_id") or chunk.get("payload", {}).get("chunk_id", "")
        if not text or not chunk_id:
            continue

        # RaceComponent + DevelopmentTokenAllocation
        if _IN_RACE.search(text):
            comp_m = _COMPONENTE_ID.search(text)
            season_m = _SEASON.search(text)
            season = int(season_m.group(1)) if season_m else 2026
            ctx.add(ExtractedEntity(
                entity_type="RaceComponent",
                domain="ducati_corse",
                properties={
                    "component_id": comp_m.group(1) if comp_m else "unknown",
                    "status": "IN_RACE",
                    "season": season,
                    "championship": "MotoGP",
                },
                chunk_ids=[chunk_id],
            ))

        # DevelopmentTokenAllocation (same chunk as RaceComponent)
        if _TOKENS_USED.search(text) and _TOKENS_TOTAL.search(text):
            used_m = _TOKENS_USED.search(text)
            total_m = _TOKENS_TOTAL.search(text)
            remaining_m = _TOKENS_REMAINING.search(text)
            season_m = _SEASON.search(text)
            season = int(season_m.group(1)) if season_m else 2026
            ctx.add(ExtractedEntity(
                entity_type="DevelopmentTokenAllocation",
                domain="ducati_corse",
                properties={
                    "season": season,
                    "tokens_used": int(used_m.group(1)) if used_m else 0,
                    "total_tokens": int(total_m.group(1)) if total_m else 0,
                    "tokens_remaining": int(remaining_m.group(1)) if remaining_m else 0,
                },
                chunk_ids=[chunk_id],
            ))

        # HomologationCertificate
        if _FIM_CERT.search(text):
            cert_m = _FIM_CERT.search(text)
            valid_to_m = _VALID_TO_KW.search(text)
            valid_from_m = _VALID_FROM_KW.search(text)
            ctx.add(ExtractedEntity(
                entity_type="HomologationCertificate",
                domain="ducati_corse",
                properties={
                    "cert_id": cert_m.group(1) if cert_m else "unknown",
                    "valid_from": valid_from_m.group(1) if valid_from_m else None,
                    "valid_to": valid_to_m.group(1) if valid_to_m else None,
                    "championship": "MotoGP",
                },
                chunk_ids=[chunk_id],
            ))

        # BudgetCapDeclaration
        if _BUDGET_DECLARED.search(text) and _BUDGET_CAP.search(text):
            decl_m = _BUDGET_DECLARED.search(text)
            cap_m = _BUDGET_CAP.search(text)
            season_m = _SEASON.search(text)
            season = int(season_m.group(1)) if season_m else 2026
            try:
                declared = _parse_eur_raw(decl_m.group(1))
                cap = _parse_eur_raw(cap_m.group(1))
            except (ValueError, AttributeError):
                continue
            ctx.add(ExtractedEntity(
                entity_type="BudgetCapDeclaration",
                domain="ducati_corse",
                properties={
                    "season": season,
                    "declared_amount_eur": declared,
                    "cap_limit_eur": cap,
                },
                chunk_ids=[chunk_id],
            ))

    log.info("ducati_extraction_complete",
             components=len(ctx.get("RaceComponent")),
             certs=len(ctx.get("HomologationCertificate")),
             budgets=len(ctx.get("BudgetCapDeclaration")),
             tokens=len(ctx.get("DevelopmentTokenAllocation")))
    return ctx


# ---------------------------------------------------------------------------
# Dallara domain extractor
# ---------------------------------------------------------------------------

_IN_COMPETITION = re.compile(r"Stato\s*:\s*IN_COMPETITION", re.IGNORECASE)
_VEHICLE_ID = re.compile(r"Vehicle ID\s*:\s*(\S+)", re.IGNORECASE)
_FIA_CERT = re.compile(r"Certificato numero\s*:\s*(FIA-\S+)", re.IGNORECASE)


def extract_dallara(chunks: list[dict[str, Any]]) -> EvaluationContext:
    from datetime import date
    ctx = EvaluationContext(domain="dallara", as_of_date=date.today().isoformat())

    for chunk in chunks:
        text: str = chunk.get("text") or chunk.get("payload", {}).get("text", "")
        chunk_id: str = chunk.get("chunk_id") or chunk.get("payload", {}).get("chunk_id", "")
        if not text or not chunk_id:
            continue

        # Vehicle in competition
        if _IN_COMPETITION.search(text):
            vid_m = _VEHICLE_ID.search(text)
            ctx.add(ExtractedEntity(
                entity_type="Vehicle",
                domain="dallara",
                properties={
                    "vehicle_id": vid_m.group(1) if vid_m else "unknown",
                    "status": "IN_COMPETITION",
                },
                chunk_ids=[chunk_id],
            ))

        # CrashTestCertification
        if _FIA_CERT.search(text):
            cert_m = _FIA_CERT.search(text)
            valid_to_m = _VALID_TO_KW.search(text)
            valid_from_m = _VALID_FROM_KW.search(text)
            ctx.add(ExtractedEntity(
                entity_type="CrashTestCertification",
                domain="dallara",
                properties={
                    "cert_id": cert_m.group(1) if cert_m else "unknown",
                    "valid_from": valid_from_m.group(1) if valid_from_m else None,
                    "valid_to": valid_to_m.group(1) if valid_to_m else None,
                    "result": "PASS",
                },
                chunk_ids=[chunk_id],
            ))

    log.info("dallara_extraction_complete",
             vehicles=len(ctx.get("Vehicle")),
             certs=len(ctx.get("CrashTestCertification")))
    return ctx


# ---------------------------------------------------------------------------
# Prada domain extractor
# ---------------------------------------------------------------------------

_FORNITORE_BLOCK = re.compile(
    r"FORNITORE\s*:\s*(.+?)(?=FORNITORE\s*:|$)",
    re.IGNORECASE | re.DOTALL,
)
_TIER = re.compile(r"Tier\s*:\s*(\d+)", re.IGNORECASE)
_AUDIT_STATUS = re.compile(r"Stato audit etico\s*:\s*(\S+)", re.IGNORECASE)
_CERT_ID_LWG = re.compile(r"Numero\s*:\s*(\S+)", re.IGNORECASE)
_SCADUTA = re.compile(r"SCADUTA", re.IGNORECASE)
_NO_CERT = re.compile(r"Nessuna certificazione materiale attiva", re.IGNORECASE)


def extract_prada(chunks: list[dict[str, Any]]) -> EvaluationContext:
    from datetime import date
    ctx = EvaluationContext(domain="prada", as_of_date=date.today().isoformat())

    for chunk in chunks:
        text: str = chunk.get("text") or chunk.get("payload", {}).get("text", "")
        chunk_id: str = chunk.get("chunk_id") or chunk.get("payload", {}).get("chunk_id", "")
        if not text or not chunk_id:
            continue

        # Parse supplier blocks — split on "FORNITORE:"
        blocks = re.split(r"(?=FORNITORE\s*:)", text, flags=re.IGNORECASE)
        for block in blocks:
            if not re.search(r"FORNITORE\s*:", block, re.IGNORECASE):
                continue
            name_m = re.search(r"FORNITORE\s*:\s*(.+)", block, re.IGNORECASE)
            tier_m = _TIER.search(block)
            audit_m = _AUDIT_STATUS.search(block)
            valid_to_m = _VALID_TO_KW.search(block)
            cert_id_m = _CERT_ID_LWG.search(block)

            if not name_m or not tier_m:
                continue
            supplier_name = name_m.group(1).strip()
            tier = int(tier_m.group(1))
            audit_status = audit_m.group(1).strip() if audit_m else None

            ctx.add(ExtractedEntity(
                entity_type="Supplier",
                domain="prada",
                properties={
                    "name": supplier_name,
                    "tier": tier,
                    "ethical_audit_status": audit_status,
                },
                chunk_ids=[chunk_id],
            ))

            # MaterialCertification — if cert info present
            if cert_id_m and valid_to_m:
                is_expired = bool(_SCADUTA.search(block))
                ctx.add(ExtractedEntity(
                    entity_type="MaterialCertification",
                    domain="prada",
                    properties={
                        "cert_id": cert_id_m.group(1),
                        "valid_to": valid_to_m.group(1),
                        "supplier_name": supplier_name,
                        "expired": is_expired,
                    },
                    chunk_ids=[chunk_id],
                ))

    log.info("prada_extraction_complete",
             suppliers=len(ctx.get("Supplier")),
             certs=len(ctx.get("MaterialCertification")))
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
    if domain == "aou_clinical":
        return extract_aou_clinical(chunks)
    if domain == "semsotec_product":
        return extract_semsotec_product(chunks)
    if domain == "ducati_corse":
        return extract_ducati_corse(chunks)
    if domain == "dallara":
        return extract_dallara(chunks)
    if domain == "prada":
        return extract_prada(chunks)
    from datetime import date
    log.warning("no_chunk_extractor_for_domain", domain=domain)
    return EvaluationContext(domain=domain, as_of_date=date.today().isoformat())
