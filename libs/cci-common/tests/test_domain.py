"""Test unitari per i core domain models."""
from __future__ import annotations

from datetime import date

import pytest

from cci_common.domain import (
    ChunkMetadata,
    ConfidentialityLevel,
    DocumentMetadata,
    Entity,
    GroundedOutput,
    HealthStatus,
    Incoherence,
    Severity,
    VerificationPlan,
)


class TestDocumentMetadata:
    def test_defaults(self) -> None:
        doc = DocumentMetadata(
            source_filename="bilancio_2026.pdf",
            source_type="pdf",
            domain="hera_it",
        )
        assert doc.document_id  # UUID generato
        assert doc.confidentiality == ConfidentialityLevel.INTERNAL
        assert doc.pii_detected is False
        assert doc.version == 1

    def test_immutability(self) -> None:
        doc = DocumentMetadata(
            source_filename="test.pdf",
            source_type="pdf",
            domain="hera_it",
        )
        with pytest.raises(Exception):
            doc.source_filename = "other.pdf"  # type: ignore[misc]


class TestChunkMetadata:
    def test_defaults(self) -> None:
        chunk = ChunkMetadata(
            doc_id="doc-001",
            text="Il budget approvato è 800.000 €",
            source_type="pdf",
            domain="hera_it",
        )
        assert chunk.chunk_id
        assert chunk.embedding_model == "all-mpnet-base-v2"
        assert chunk.valid_from is None

    def test_temporal_fields(self) -> None:
        chunk = ChunkMetadata(
            doc_id="doc-001",
            text="Commitment Q1 2026",
            source_type="pdf",
            domain="hera_it",
            valid_from=date(2026, 1, 1),
            valid_to=date(2026, 3, 31),
        )
        assert chunk.valid_from < chunk.valid_to  # type: ignore[operator]


class TestIncoherence:
    def test_create_r001(self) -> None:
        inc = Incoherence(
            entity_a_id="commit-001",
            entity_a_type="CloudCommitment",
            entity_b_id="budget-001",
            entity_b_type="BudgetApproval",
            rule_violated="R001",
            severity=Severity.HIGH,
            evidence_chunks=["chunk-001", "chunk-002"],
            domain="financial",
            description="Commitment 920k > budget 800k",
        )
        assert inc.severity == Severity.HIGH
        assert "chunk-001" in inc.evidence_chunks
        assert inc.incoherence_id  # UUID generato

    def test_severity_ordering(self) -> None:
        severities = [Severity.LOW, Severity.MEDIUM, Severity.HIGH, Severity.CRITICAL]
        assert len(set(severities)) == 4


class TestGroundedOutput:
    def test_valid_with_sources(self) -> None:
        out = GroundedOutput(
            content="Il commitment supera il budget [source: chunk-001].",
            sources=["chunk-001"],
            confidence=0.92,
            model_version="claude-sonnet-4-6",
            prompt_version="v1",
        )
        assert out.grounding_verified is False
        assert out.confidence == pytest.approx(0.92)

    def test_confidence_bounds(self) -> None:
        with pytest.raises(Exception):
            GroundedOutput(
                content="test",
                sources=[],
                confidence=1.5,  # fuori range
                model_version="claude-sonnet-4-6",
                prompt_version="v1",
            )


class TestHealthStatus:
    def test_basic(self) -> None:
        h = HealthStatus(status="ok", service="cci-ingestion", version="0.1.0")
        assert h.checks == {}

    def test_with_checks(self) -> None:
        h = HealthStatus(
            status="degraded",
            service="cci-knowledge",
            version="0.1.0",
            checks={"qdrant": "ok", "neo4j": "timeout"},
        )
        assert h.checks["neo4j"] == "timeout"


class TestVerificationPlan:
    def test_create(self) -> None:
        plan = VerificationPlan(
            trigger="timer:end_of_month",
            domain="hera_it",
            steps=[
                {"step": 1, "action": "retrieve", "query": "cloud commitment Q1 2026"},
                {"step": 2, "action": "verify", "rules": ["R001", "R002"]},
            ],
        )
        assert plan.plan_id
        assert plan.correlation_id
        assert len(plan.steps) == 2
