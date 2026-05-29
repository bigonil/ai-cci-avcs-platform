"""Ontology YAML loader — parses and validates vertical ontologies.

YAML uses `type: string` but Python typing uses `str`.
We normalize `string` -> `str` on load.
"""
from __future__ import annotations

import pathlib
from typing import Any

import structlog
import yaml
from pydantic import BaseModel, Field, field_validator

log = structlog.get_logger(__name__)

_TYPE_MAP: dict[str, str] = {
    "string": "str",
    "int": "int",
    "integer": "int",
    "float": "float",
    "bool": "bool",
    "boolean": "bool",
    "date": "date",
    "datetime": "datetime",
}


def _normalize_type(raw: str) -> str:
    return _TYPE_MAP.get(raw.lower().strip(), raw)


class EntityProperty(BaseModel):
    name: str
    type: str
    required: bool = False
    description: str | None = None
    allowed_values: list[str] | None = None

    @field_validator("type", mode="before")
    @classmethod
    def normalize_type(cls, v: str) -> str:
        return _normalize_type(v)


class OntologyEntity(BaseModel):
    name: str
    description: str | None = None
    properties: list[EntityProperty] = Field(default_factory=list)


class RelationProperty(BaseModel):
    name: str
    type: str
    required: bool = False

    @field_validator("type", mode="before")
    @classmethod
    def normalize_type(cls, v: str) -> str:
        return _normalize_type(v)


class OntologyRelation(BaseModel):
    type: str
    from_entity: str = Field(alias="from")
    to_entity: str = Field(alias="to")
    temporal: bool = False
    description: str | None = None
    properties: list[RelationProperty] = Field(default_factory=list)

    model_config = {"populate_by_name": True}


class OntologyRule(BaseModel):
    id: str
    description: str
    when: str
    severity: str
    domain: str
    article_ref: str | None = None
    example: str | None = None

    @field_validator("severity", mode="before")
    @classmethod
    def lower_severity(cls, v: str) -> str:
        return v.lower()


class NerHint(BaseModel):
    entity: str
    keywords: list[str] = Field(default_factory=list)
    patterns: list[str] = Field(default_factory=list)


class Regulation(BaseModel):
    id: str
    name: str
    scope: str | None = None
    url: str | None = None


class Ontology(BaseModel):
    domain: str
    version: str
    description: str | None = None
    entities: list[OntologyEntity] = Field(default_factory=list)
    relations: list[OntologyRelation] = Field(default_factory=list)
    rules: list[OntologyRule] = Field(default_factory=list)
    ner_hints: list[NerHint] = Field(default_factory=list)
    regulations: list[Regulation] = Field(default_factory=list)

    def entity_names(self) -> list[str]:
        return [e.name for e in self.entities]

    def rule_by_id(self, rule_id: str) -> OntologyRule | None:
        return next((r for r in self.rules if r.id == rule_id), None)


class OntologyLoader:
    """Loads all YAML ontology files from a directory, keyed by domain."""

    def __init__(self, ontologies_path: pathlib.Path) -> None:
        self._path = ontologies_path
        self._cache: dict[str, Ontology] = {}

    def load_all(self) -> dict[str, Ontology]:
        if self._cache:
            return self._cache
        if not self._path.exists():
            log.warning("ontologies_path_missing", path=str(self._path))
            return {}
        for yaml_file in sorted(self._path.glob("*.yaml")):
            try:
                self._load_file(yaml_file)
            except Exception:
                log.exception("ontology_load_error", file=str(yaml_file))
        log.info("ontologies_loaded", count=len(self._cache), domains=list(self._cache))
        return self._cache

    def _load_file(self, path: pathlib.Path) -> None:
        raw: dict[str, Any] = yaml.safe_load(path.read_text(encoding="utf-8"))
        ontology = Ontology.model_validate(raw)
        self._cache[ontology.domain] = ontology
        log.debug("ontology_loaded", domain=ontology.domain, version=ontology.version)

    def get(self, domain: str) -> Ontology | None:
        if not self._cache:
            self.load_all()
        return self._cache.get(domain)

    def all_domains(self) -> list[str]:
        if not self._cache:
            self.load_all()
        return list(self._cache.keys())
