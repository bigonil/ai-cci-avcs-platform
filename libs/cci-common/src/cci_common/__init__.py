"""cci-common — shared types, CloudEvents models, domain models, OTel setup."""

from cci_common.domain import (
    ChunkMetadata,
    ConfidentialityLevel,
    DocumentMetadata,
    Domain,
    Entity,
    GroundedOutput,
    HealthStatus,
    Incoherence,
    Severity,
    VerificationPlan,
)
from cci_common.events import (
    KNOWN_EVENT_TYPES,
    AuditLogAppendedEvent,
    CloudEvent,
    DocumentIndexedEvent,
    HitlRequiredEvent,
    IncoherenceDetectedEvent,
)
from cci_common.observability import get_logger, setup_telemetry

__version__ = "0.1.0"

__all__ = [
    # domain
    "ChunkMetadata",
    "ConfidentialityLevel",
    "DocumentMetadata",
    "Domain",
    "Entity",
    "GroundedOutput",
    "HealthStatus",
    "Incoherence",
    "Severity",
    "VerificationPlan",
    # events
    "KNOWN_EVENT_TYPES",
    "AuditLogAppendedEvent",
    "CloudEvent",
    "DocumentIndexedEvent",
    "HitlRequiredEvent",
    "IncoherenceDetectedEvent",
    # observability
    "get_logger",
    "setup_telemetry",
]
