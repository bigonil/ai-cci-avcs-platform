"""Core domain models CCI/AVCS — Pydantic v2.

Questi modelli sono condivisi tra tutti i servizi tramite cci-common.
Ogni servizio può estendere questi tipi base nel proprio bounded context.
"""
from __future__ import annotations

import uuid
from datetime import UTC, date, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class Severity(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Domain(StrEnum):
    FINANCIAL = "financial"
    COMPLIANCE = "compliance"
    REGULATORY = "regulatory"
    OPERATIONAL = "operational"


class ConfidentialityLevel(StrEnum):
    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"


class DocumentMetadata(BaseModel):
    """Metadati di un documento dopo l'ingestion."""

    document_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    source_filename: str
    source_type: str
    domain: str
    ingested_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    confidentiality: ConfidentialityLevel = ConfidentialityLevel.INTERNAL
    pii_detected: bool = False
    version: int = 1
    tags: list[str] = Field(default_factory=list)

    model_config = {"frozen": True}


class ChunkMetadata(BaseModel):
    """Metadati di un chunk semantico indicizzato in Qdrant."""

    chunk_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    doc_id: str
    text: str
    valid_from: date | None = None
    valid_to: date | None = None
    version: int = 1
    source_type: str
    cert_ref: list[str] = Field(default_factory=list)
    domain: str
    confidentiality: ConfidentialityLevel = ConfidentialityLevel.INTERNAL
    page_number: int | None = None
    embedding_model: str = "all-mpnet-base-v2"

    model_config = {"frozen": True}


class Entity(BaseModel):
    """Entità estratta da un documento (NER)."""

    entity_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    entity_type: str
    label: str
    properties: dict[str, Any] = Field(default_factory=dict)
    provenance_chunk_id: str
    provenance_doc_id: str
    confidence: float = Field(ge=0.0, le=1.0, default=1.0)
    valid_from: date | None = None
    valid_to: date | None = None

    model_config = {"frozen": True}


class Incoherence(BaseModel):
    """Incoerenza strutturata rilevata dal Coherence Engine."""

    incoherence_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    entity_a_id: str
    entity_a_type: str
    entity_b_id: str | None = None
    entity_b_type: str | None = None
    rule_violated: str
    severity: Severity
    evidence_chunks: list[str]
    temporal_context: dict[str, Any] = Field(default_factory=dict)
    domain: Domain
    description: str
    detected_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    model_config = {"frozen": True}


class VerificationPlan(BaseModel):
    """Piano di verifica prodotto dal Planner."""

    plan_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    trigger: str
    domain: str
    steps: list[dict[str, Any]]
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    correlation_id: str = Field(default_factory=lambda: str(uuid.uuid4()))

    model_config = {"frozen": True}


class GroundedOutput(BaseModel):
    """Output LLM con citazioni verificate — struttura minima garantita."""

    content: str
    sources: list[str]
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning_steps: list[str] = Field(default_factory=list)
    model_version: str
    prompt_version: str
    grounding_verified: bool = False

    model_config = {"frozen": True}


class HealthStatus(BaseModel):
    """Risposta standard health check."""

    status: str
    service: str
    version: str
    checks: dict[str, str] = Field(default_factory=dict)
