"""Tests for OntologyLoader — parsing, validation, type normalisation."""
from __future__ import annotations

import pathlib

import pytest
import yaml

from cci_knowledge.ontology_loader import Ontology, OntologyLoader, _normalize_type


class TestTypeNormalization:
    def test_string_becomes_str(self) -> None:
        assert _normalize_type("string") == "str"

    def test_integer_becomes_int(self) -> None:
        assert _normalize_type("integer") == "int"

    def test_float_passthrough(self) -> None:
        assert _normalize_type("float") == "float"

    def test_unknown_passthrough(self) -> None:
        assert _normalize_type("custom_type") == "custom_type"

    def test_case_insensitive(self) -> None:
        assert _normalize_type("STRING") == "str"
        assert _normalize_type("Float") == "float"


class TestOntologyLoader:
    def test_load_all(self, ontology_loader: OntologyLoader) -> None:
        ontologies = ontology_loader.load_all()
        assert "test_domain" in ontologies

    def test_entity_parsed(self, ontology_loader: OntologyLoader) -> None:
        ont = ontology_loader.get("test_domain")
        assert ont is not None
        assert len(ont.entities) == 1
        assert ont.entities[0].name == "Contract"

    def test_property_type_normalized(self, ontology_loader: OntologyLoader) -> None:
        ont = ontology_loader.get("test_domain")
        assert ont is not None
        provider_prop = next(p for p in ont.entities[0].properties if p.name == "provider")
        # `string` in YAML must become `str`
        assert provider_prop.type == "str"

    def test_rule_parsed(self, ontology_loader: OntologyLoader) -> None:
        ont = ontology_loader.get("test_domain")
        assert ont is not None
        rule = ont.rule_by_id("T001")
        assert rule is not None
        assert rule.severity == "high"

    def test_relation_parsed(self, ontology_loader: OntologyLoader) -> None:
        ont = ontology_loader.get("test_domain")
        assert ont is not None
        assert len(ont.relations) == 1
        assert ont.relations[0].type == "COVERED_BY"
        assert ont.relations[0].temporal is True

    def test_missing_domain_returns_none(self, ontology_loader: OntologyLoader) -> None:
        assert ontology_loader.get("nonexistent") is None

    def test_empty_directory(self, tmp_path: pathlib.Path) -> None:
        loader = OntologyLoader(tmp_path)
        result = loader.load_all()
        assert result == {}

    def test_all_domains(self, ontology_loader: OntologyLoader) -> None:
        domains = ontology_loader.all_domains()
        assert "test_domain" in domains

    def test_invalid_yaml_skipped(
        self, tmp_path: pathlib.Path, sample_ontology_dir: pathlib.Path
    ) -> None:
        import shutil
        dest = tmp_path / "ontologies"
        shutil.copytree(sample_ontology_dir, dest)
        (dest / "bad.yaml").write_text("not: valid: yaml: [", encoding="utf-8")
        loader = OntologyLoader(dest)
        # Should not raise; bad file is skipped
        result = loader.load_all()
        assert "test_domain" in result
