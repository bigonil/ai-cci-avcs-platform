"""Shared test fixtures per cci-common."""
from __future__ import annotations

import pytest

from cci_common.domain import ChunkMetadata, DocumentMetadata, Incoherence, Severity


@pytest.fixture
def sample_document_metadata() -> DocumentMetadata:
    return DocumentMetadata(
        source_filename="bilancio_preventivo_2026.pdf",
        source_type="pdf",
        domain="hera_it",
    )


@pytest.fixture
def sample_chunk(sample_document_metadata: DocumentMetadata) -> ChunkMetadata:
    return ChunkMetadata(
        doc_id=sample_document_metadata.document_id,
        text="Cloud Infrastructure budget approvato: 800.000 €",
        source_type="pdf",
        domain="hera_it",
    )


@pytest.fixture
def sample_incoherence() -> Incoherence:
    return Incoherence(
        entity_a_id="commit-001",
        entity_a_type="CloudCommitment",
        entity_b_id="budget-001",
        entity_b_type="BudgetApproval",
        rule_violated="R001",
        severity=Severity.HIGH,
        evidence_chunks=["chunk-001", "chunk-002"],
        domain="financial",
        description="Commitment 920k € > budget approvato 800k €",
    )
