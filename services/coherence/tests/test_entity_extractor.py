"""Tests for the Hera IT entity extractor (regex-based, zero LLM)."""
from __future__ import annotations

import pytest

from cci_coherence.entity_extractor import extract_hera_it, _parse_eur_amount


# ---------------------------------------------------------------------------
# EUR amount parser
# ---------------------------------------------------------------------------

class TestEurParser:
    def test_italian_thousands(self):
        assert _parse_eur_amount("580.000 EUR") == 580_000.0

    def test_english_thousands(self):
        assert _parse_eur_amount("580,000 EUR") == 580_000.0

    def test_k_suffix(self):
        assert _parse_eur_amount("580k EUR") == 580_000.0

    def test_plain_integer(self):
        assert _parse_eur_amount("800000 EUR") == 800_000.0

    def test_no_match(self):
        assert _parse_eur_amount("no money here") is None


# ---------------------------------------------------------------------------
# Hera IT entity extraction
# ---------------------------------------------------------------------------

AZURE_COMMITMENT_CHUNK = {
    "chunk_id": "ch-001",
    "text": (
        "Impegno Azure EA per il 2026: commitment di 580.000 EUR "
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
    "text": (
        "Budget totale approvato dal CdA per infrastruttura cloud 2026: "
        "800.000 EUR."
    ),
}

CERT_CHUNK = {
    "chunk_id": "ch-004",
    "text": (
        "Certificazione ISO 27001 valida dal 2025-01-01 al 2027-12-31 "
        "per l'ambiente cloud Hera."
    ),
}

CHUNKS = [AZURE_COMMITMENT_CHUNK, AZURE_ALLOCATION_CHUNK, BUDGET_APPROVAL_CHUNK, CERT_CHUNK]


class TestHeraItExtraction:
    def test_extracts_cloud_commitment(self):
        ctx = extract_hera_it([AZURE_COMMITMENT_CHUNK])
        commitments = ctx.get("CloudCommitment")
        assert len(commitments) == 1
        assert commitments[0].get_float("amount_eur") == 580_000.0
        assert commitments[0].get_str("provider") == "Azure"

    def test_extracts_period_end(self):
        ctx = extract_hera_it([AZURE_COMMITMENT_CHUNK])
        commitment = ctx.get("CloudCommitment")[0]
        assert commitment.get_date_str("period_end") == "2026-12-31"

    def test_extracts_budget_allocation(self):
        ctx = extract_hera_it([AZURE_ALLOCATION_CHUNK])
        allocs = ctx.get("CloudBudgetAllocation")
        assert len(allocs) == 1
        assert allocs[0].get_float("allocated_eur") == 580_000.0

    def test_extracts_budget_approval(self):
        ctx = extract_hera_it([BUDGET_APPROVAL_CHUNK])
        approvals = ctx.get("BudgetApproval")
        assert len(approvals) == 1
        assert approvals[0].get_float("amount_eur") == 800_000.0

    def test_extracts_iso27001(self):
        ctx = extract_hera_it([CERT_CHUNK])
        certs = ctx.get("ISO27001Certification")
        assert len(certs) == 1
        assert certs[0].get_date_str("valid_to") == "2027-12-31"

    def test_chunk_ids_tracked(self):
        ctx = extract_hera_it([AZURE_COMMITMENT_CHUNK])
        commitment = ctx.get("CloudCommitment")[0]
        assert "ch-001" in commitment.chunk_ids

    def test_all_entities_from_all_chunks(self):
        ctx = extract_hera_it(CHUNKS)
        assert len(ctx.get("CloudCommitment")) >= 1
        assert len(ctx.get("CloudBudgetAllocation")) >= 1
        assert len(ctx.get("BudgetApproval")) >= 1
        assert len(ctx.get("ISO27001Certification")) >= 1

    def test_empty_chunks(self):
        ctx = extract_hera_it([])
        assert ctx.entities_by_type == {}

    def test_chunk_without_text_skipped(self):
        ctx = extract_hera_it([{"chunk_id": "x", "text": ""}])
        assert ctx.entities_by_type == {}
