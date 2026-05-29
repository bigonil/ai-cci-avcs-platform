"""Pytest fixtures for Knowledge Service integration tests.

Uses testcontainers for real Neo4j and MongoDB instances.
Qdrant tests use a mock to avoid requiring a running container in CI.
"""
from __future__ import annotations

import pathlib
import textwrap
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
import yaml

from cci_knowledge.ontology_loader import OntologyLoader

ONTOLOGIES_DIR = pathlib.Path(__file__).parent / "fixtures" / "ontologies"


@pytest.fixture(scope="session")
def sample_ontology_dir(tmp_path_factory: pytest.TempPathFactory) -> pathlib.Path:
    d = tmp_path_factory.mktemp("ontologies")
    ontology = {
        "domain": "test_domain",
        "version": "1.0.0",
        "description": "Test ontology",
        "entities": [
            {
                "name": "Contract",
                "properties": [
                    {"name": "amount_eur", "type": "float", "required": True},
                    {"name": "provider", "type": "string", "required": True},
                ],
            }
        ],
        "relations": [
            {
                "type": "COVERED_BY",
                "from": "Contract",
                "to": "Budget",
                "temporal": True,
            }
        ],
        "rules": [
            {
                "id": "T001",
                "description": "Amount must not exceed budget",
                "when": "Contract.amount_eur > Budget.amount_eur",
                "severity": "HIGH",
                "domain": "financial",
            }
        ],
    }
    (d / "test_domain.yaml").write_text(yaml.dump(ontology), encoding="utf-8")
    return d


@pytest.fixture()
def ontology_loader(sample_ontology_dir: pathlib.Path) -> OntologyLoader:
    loader = OntologyLoader(sample_ontology_dir)
    loader.load_all()
    return loader


@pytest.fixture()
def mock_qdrant():
    """Mock QdrantVectorStore — avoids container dependency in unit tests."""
    mock = AsyncMock()
    mock.ensure_collection = AsyncMock()
    mock.upsert_chunks = AsyncMock(return_value=2)
    mock.search = AsyncMock(return_value=[{"score": 0.9, "payload": {"text": "test"}, "id": "abc"}])
    mock.delete_by_doc_id = AsyncMock(return_value=3)
    return mock


@pytest.fixture()
def mock_graph():
    """Mock TemporalGraph — avoids Neo4j container in unit tests."""
    mock = AsyncMock()
    mock.bootstrap_indexes = AsyncMock()
    mock.upsert_entity = AsyncMock()
    mock.get_entities = AsyncMock(return_value=[{"entity_id": "e1", "entity_type": "Contract"}])
    mock.get_relations = AsyncMock(return_value=[])
    mock.run_readonly_query = AsyncMock(return_value=[{"n": 1}])
    mock.delete_entity_by_doc_id = AsyncMock(return_value=2)
    mock.close = AsyncMock()
    return mock
