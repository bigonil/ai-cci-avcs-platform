"""Test unitari per CloudEvents models."""
from __future__ import annotations

import json
from datetime import UTC, datetime

import pytest

from cci_common.events import (
    KNOWN_EVENT_TYPES,
    AuditLogAppendedEvent,
    CloudEvent,
    DocumentIndexedEvent,
    HitlRequiredEvent,
    IncoherenceDetectedEvent,
)


class TestCloudEvent:
    def test_default_fields(self) -> None:
        event = CloudEvent(source="test/service", type="test.event.v1")
        assert event.specversion == "1.0"
        assert event.datacontenttype == "application/json"
        assert event.id  # UUID generato
        assert isinstance(event.time, datetime)

    def test_immutability(self) -> None:
        event = CloudEvent(source="test", type="test.event.v1")
        with pytest.raises(Exception):
            event.specversion = "2.0"  # type: ignore[misc]

    def test_model_dump_cloudevent_serializable(self) -> None:
        event = CloudEvent(source="test", type="test.event.v1", data={"key": "value"})
        dumped = event.model_dump_cloudevent()
        assert json.dumps(dumped)  # deve essere JSON-serializzabile
        assert dumped["specversion"] == "1.0"
        assert dumped["data"] == {"key": "value"}

    def test_time_is_utc_aware(self) -> None:
        event = CloudEvent(source="test", type="test.event.v1")
        assert event.time.tzinfo is not None


class TestDocumentIndexedEvent:
    def test_create_factory(self) -> None:
        event = DocumentIndexedEvent.create(
            document_id="doc-123",
            entities=[{"type": "BudgetApproval", "id": "e-1"}],
            metadata={"domain": "hera_it"},
        )
        assert event.type == "ingestion.document.indexed.v1"
        assert event.source == "cci/ingestion-service"
        assert event.data["document_id"] == "doc-123"
        assert len(event.data["entities"]) == 1

    def test_type_in_known_events(self) -> None:
        assert "ingestion.document.indexed.v1" in KNOWN_EVENT_TYPES


class TestIncoherenceDetectedEvent:
    def test_create_factory(self) -> None:
        event = IncoherenceDetectedEvent.create(
            verification_id="v-001",
            incoherences=[{"rule": "R001", "severity": "HIGH"}],
            domain="hera_it",
        )
        assert event.type == "coherence.incoherence.detected.v1"
        assert event.data["domain"] == "hera_it"
        assert len(event.data["incoherences"]) == 1

    def test_unique_ids(self) -> None:
        e1 = IncoherenceDetectedEvent.create("v-1", [], "hera_it")
        e2 = IncoherenceDetectedEvent.create("v-2", [], "hera_it")
        assert e1.id != e2.id


class TestHitlRequiredEvent:
    def test_create_factory(self) -> None:
        event = HitlRequiredEvent.create(
            decision_id="d-001",
            impact_eur=75000.0,
            description="Cloud overrun 15%",
            correlation_id="corr-001",
        )
        assert event.type == "governance.hitl.required.v1"
        assert event.data["impact_eur"] == 75000.0


class TestAuditLogAppendedEvent:
    def test_create_factory(self) -> None:
        event = AuditLogAppendedEvent.create(
            seq=42,
            event_type="ingestion.document.indexed.v1",
            correlation_id="corr-abc",
        )
        assert event.type == "governance.audit.appended.v1"
        assert event.data["seq"] == 42


class TestKnownEventTypes:
    def test_all_service_events_registered(self) -> None:
        required = {
            "ingestion.document.indexed.v1",
            "coherence.incoherence.detected.v1",
            "governance.hitl.required.v1",
            "governance.audit.appended.v1",
            "llm.call.v1",
        }
        assert required.issubset(KNOWN_EVENT_TYPES)
