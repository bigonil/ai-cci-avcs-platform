"""CloudEvents 1.0 models per CCI/AVCS.

Tutti gli eventi del sistema seguono il formato CloudEvents 1.0 con naming
convention: {domain}.{entity}.{action}.v{version}
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class CloudEvent(BaseModel):
    """CloudEvents 1.0 envelope — base per tutti gli eventi del sistema."""

    specversion: Literal["1.0"] = "1.0"
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    source: str
    type: str
    time: datetime = Field(default_factory=lambda: datetime.now(UTC))
    datacontenttype: str = "application/json"
    data: dict[str, Any] = Field(default_factory=dict)

    model_config = {"frozen": True}

    def model_dump_cloudevent(self) -> dict[str, Any]:
        """Serializza rispettando la struttura CloudEvents 1.0."""
        return self.model_dump(mode="json")


class DocumentIndexedEvent(CloudEvent):
    """ingestion.document.indexed.v1 — emesso dopo indicizzazione completa."""

    type: Literal["ingestion.document.indexed.v1"] = "ingestion.document.indexed.v1"
    source: str = "cci/ingestion-service"

    @classmethod
    def create(
        cls,
        document_id: str,
        entities: list[dict[str, Any]],
        metadata: dict[str, Any],
    ) -> "DocumentIndexedEvent":
        return cls(
            data={
                "document_id": document_id,
                "entities": entities,
                "metadata": metadata,
            }
        )


class IncoherenceDetectedEvent(CloudEvent):
    """coherence.incoherence.detected.v1 — emesso dal Verifier."""

    type: Literal["coherence.incoherence.detected.v1"] = (
        "coherence.incoherence.detected.v1"
    )
    source: str = "cci/coherence-service"

    @classmethod
    def create(
        cls,
        verification_id: str,
        incoherences: list[dict[str, Any]],
        domain: str,
    ) -> "IncoherenceDetectedEvent":
        return cls(
            data={
                "verification_id": verification_id,
                "incoherences": incoherences,
                "domain": domain,
            }
        )


class HitlRequiredEvent(CloudEvent):
    """governance.hitl.required.v1 — emesso quando impatto > soglia."""

    type: Literal["governance.hitl.required.v1"] = "governance.hitl.required.v1"
    source: str = "cci/governance-service"

    @classmethod
    def create(
        cls,
        decision_id: str,
        impact_eur: float,
        description: str,
        correlation_id: str,
    ) -> "HitlRequiredEvent":
        return cls(
            data={
                "decision_id": decision_id,
                "impact_eur": impact_eur,
                "description": description,
                "correlation_id": correlation_id,
            }
        )


class AuditLogAppendedEvent(CloudEvent):
    """governance.audit.appended.v1 — conferma append al log immutabile."""

    type: Literal["governance.audit.appended.v1"] = "governance.audit.appended.v1"
    source: str = "cci/governance-service"

    @classmethod
    def create(
        cls,
        seq: int,
        event_type: str,
        correlation_id: str,
    ) -> "AuditLogAppendedEvent":
        return cls(
            data={
                "seq": seq,
                "event_type": event_type,
                "correlation_id": correlation_id,
            }
        )


# Registry degli event type noti per validazione
KNOWN_EVENT_TYPES: frozenset[str] = frozenset(
    {
        "ingestion.document.indexed.v1",
        "coherence.incoherence.detected.v1",
        "governance.hitl.required.v1",
        "governance.audit.appended.v1",
        "llm.call.v1",
    }
)
