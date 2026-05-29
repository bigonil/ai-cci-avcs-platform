"""Tests for TemporalGraph — read-only guard, upsert, soft-delete."""
from __future__ import annotations

import pytest

from cci_knowledge.temporal_graph import TemporalGraph, _assert_readonly


class TestReadOnlyGuard:
    def test_allows_match(self) -> None:
        _assert_readonly("MATCH (e:Entity) RETURN e")

    def test_allows_return(self) -> None:
        _assert_readonly("MATCH (a)-[r]->(b) WHERE a.domain = $d RETURN a, type(r), b LIMIT 10")

    def test_rejects_create(self) -> None:
        with pytest.raises(ValueError, match="CREATE"):
            _assert_readonly("CREATE (e:Entity {id: 'x'})")

    def test_rejects_merge(self) -> None:
        with pytest.raises(ValueError, match="MERGE"):
            _assert_readonly("MERGE (e:Entity {id: 'x'}) RETURN e")

    def test_rejects_set(self) -> None:
        with pytest.raises(ValueError, match="SET"):
            _assert_readonly("MATCH (e) WHERE e.id = 'x' SET e.val = 1")

    def test_rejects_delete(self) -> None:
        with pytest.raises(ValueError, match="DELETE"):
            _assert_readonly("MATCH (e) DELETE e")

    def test_rejects_detach_delete(self) -> None:
        with pytest.raises(ValueError):
            _assert_readonly("MATCH (e) DETACH DELETE e")

    def test_case_insensitive(self) -> None:
        with pytest.raises(ValueError):
            _assert_readonly("match (e) delete e")


class TestTemporalGraphMocked:
    """Unit tests with mocked Neo4j driver — no container."""

    @pytest.fixture()
    def graph(self) -> TemporalGraph:
        from unittest.mock import AsyncMock, MagicMock, patch
        with patch("cci_knowledge.temporal_graph.AsyncGraphDatabase") as MockDB:
            driver = AsyncMock()
            session = AsyncMock()
            session.__aenter__ = AsyncMock(return_value=session)
            session.__aexit__ = AsyncMock(return_value=False)
            session.run = AsyncMock(return_value=AsyncMock(data=AsyncMock(return_value=[])))
            driver.session.return_value = session
            MockDB.driver.return_value = driver
            g = TemporalGraph("bolt://localhost:7687", "neo4j", "test")
            g._driver = driver
            return g

    @pytest.mark.asyncio
    async def test_bootstrap_idempotent(self, graph: TemporalGraph) -> None:
        await graph.bootstrap_indexes()
        await graph.bootstrap_indexes()
        assert graph._driver.session.call_count >= 2  # type: ignore[attr-defined]

    @pytest.mark.asyncio
    async def test_upsert_entity(self, graph: TemporalGraph) -> None:
        await graph.upsert_entity(
            entity_id="e-001",
            entity_type="CloudCommitment",
            domain="hera_it",
            properties={"amount_eur": 580000.0, "provider": "Azure"},
            valid_from="2026-01-01",
        )
        session = graph._driver.session.return_value.__aenter__.return_value  # type: ignore[attr-defined]
        session.run.assert_called()

    @pytest.mark.asyncio
    async def test_readonly_query_write_rejected(self, graph: TemporalGraph) -> None:
        with pytest.raises(ValueError):
            await graph.run_readonly_query("CREATE (e:Entity {id: 'bad'})")

    @pytest.mark.asyncio
    async def test_soft_delete(self, graph: TemporalGraph) -> None:
        session = graph._driver.session.return_value.__aenter__.return_value  # type: ignore[attr-defined]
        single_mock = AsyncMock(return_value={"n": 3})
        session.run.return_value.single = single_mock
        count = await graph.delete_entity_by_doc_id("chunk-abc")
        assert count == 3
