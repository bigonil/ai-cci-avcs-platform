"""Coherence Engine internal models — no LLM, no external state."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class RulePattern(StrEnum):
    """Detected evaluation pattern for an OntologyRule.when expression."""

    SIMPLE_OVERRUN = "simple_overrun"
    AGGREGATE_OVERRUN = "aggregate_overrun"
    CERT_VALIDITY = "cert_validity"
    CONCENTRATION = "concentration"
    MISSING_RELATION = "missing_relation"
    UNKNOWN = "unknown"


@dataclass
class ExtractedEntity:
    """Entity value(s) extracted from text chunks or the knowledge graph."""

    entity_type: str
    domain: str
    properties: dict[str, Any]
    chunk_ids: list[str] = field(default_factory=list)

    def get_float(self, key: str, default: float = 0.0) -> float:
        val = self.properties.get(key, default)
        if isinstance(val, (int, float)):
            return float(val)
        try:
            return float(str(val).replace(".", "").replace(",", ".").replace(" ", ""))
        except (ValueError, TypeError):
            return default

    def get_str(self, key: str, default: str = "") -> str:
        return str(self.properties.get(key, default))

    def get_date_str(self, key: str) -> str | None:
        return self.properties.get(key)


@dataclass
class RuleViolation:
    """Single rule violation found by the engine — no LLM, fully deterministic."""

    rule_id: str
    entity_a: ExtractedEntity
    entity_b: ExtractedEntity | None
    description: str
    severity: str
    evidence_chunks: list[str]
    computed_values: dict[str, Any] = field(default_factory=dict)

    def to_incoherence_dict(self, domain: str) -> dict[str, Any]:
        return {
            "rule_violated": self.rule_id,
            "entity_a_type": self.entity_a.entity_type,
            "entity_a_props": self.entity_a.properties,
            "entity_b_type": self.entity_b.entity_type if self.entity_b else None,
            "entity_b_props": self.entity_b.properties if self.entity_b else None,
            "severity": self.severity,
            "description": self.description,
            "evidence_chunks": self.evidence_chunks,
            "domain": domain,
            "computed_values": self.computed_values,
        }


@dataclass
class EvaluationContext:
    """All extracted entities for a given domain evaluation run."""

    domain: str
    as_of_date: str
    entities_by_type: dict[str, list[ExtractedEntity]] = field(default_factory=dict)

    def get(self, entity_type: str) -> list[ExtractedEntity]:
        return self.entities_by_type.get(entity_type, [])

    def add(self, entity: ExtractedEntity) -> None:
        self.entities_by_type.setdefault(entity.entity_type, []).append(entity)

    def all_chunk_ids(self) -> list[str]:
        ids = []
        for entities in self.entities_by_type.values():
            for e in entities:
                ids.extend(e.chunk_ids)
        return list(dict.fromkeys(ids))  # preserve order, deduplicate
