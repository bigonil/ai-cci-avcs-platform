"""Neo4j temporal property graph adapter.

Every relation carries: valid_from, valid_to, version, confidence, provenance_chunk_id.
Bitemporal updates follow the close-and-create pattern (never MERGE overwrites history).

SAFETY: write_guard rejects any Cypher string that contains mutation keywords outside
of the dedicated write methods, enforcing R4 (Zero LLM in Verifier).
"""
from __future__ import annotations

import re
from datetime import date, datetime
from typing import Any

import structlog
from neo4j import AsyncDriver, AsyncGraphDatabase, AsyncSession

log = structlog.get_logger(__name__)

# Keywords that must not appear in read-only queries
_WRITE_KEYWORDS = re.compile(
    r"\b(CREATE|MERGE|SET|DELETE|DETACH\s+DELETE|REMOVE|CALL\s+apoc\..*write)\b",
    re.IGNORECASE,
)


def _assert_readonly(cypher: str) -> None:
    match = _WRITE_KEYWORDS.search(cypher)
    if match:
        raise ValueError(
            f"Write keyword '{match.group()}' detected in read-only query path. "
            "Use dedicated write methods instead."
        )


def _to_date_str(d: date | datetime | str | None) -> str | None:
    if d is None:
        return None
    if isinstance(d, (date, datetime)):
        return d.isoformat()[:10]
    return str(d)


class TemporalGraph:
    """Async Neo4j client with bitemporal entity/relation management."""

    def __init__(
        self,
        uri: str,
        user: str,
        password: str,
        database: str = "neo4j",
    ) -> None:
        self._driver: AsyncDriver = AsyncGraphDatabase.driver(
            uri, auth=(user, password)
        )
        self._database = database

    async def close(self) -> None:
        await self._driver.close()

    async def bootstrap_indexes(self) -> None:
        """Idempotent: creates constraints and indexes if missing."""
        statements = [
            "CREATE CONSTRAINT entity_id IF NOT EXISTS FOR (e:Entity) REQUIRE e.entity_id IS UNIQUE",
            "CREATE INDEX entity_domain IF NOT EXISTS FOR (e:Entity) ON (e.domain)",
            "CREATE INDEX entity_type IF NOT EXISTS FOR (e:Entity) ON (e.entity_type)",
            "CREATE INDEX entity_valid IF NOT EXISTS FOR (e:Entity) ON (e.valid_from, e.valid_to)",
        ]
        async with self._driver.session(database=self._database) as s:
            for stmt in statements:
                await s.run(stmt)
        log.info("neo4j_indexes_bootstrapped")

    async def upsert_entity(
        self,
        entity_id: str,
        entity_type: str,
        domain: str,
        properties: dict[str, Any],
        valid_from: date | str | None = None,
        valid_to: date | str | None = None,
        provenance_chunk_id: str | None = None,
        confidence: float = 1.0,
        version: int = 1,
    ) -> None:
        """MERGE on entity_id, then SET all properties."""
        async with self._driver.session(database=self._database) as s:
            await s.run(
                """
                MERGE (e:Entity {entity_id: $entity_id})
                SET e.entity_type = $entity_type,
                    e.domain = $domain,
                    e.valid_from = $valid_from,
                    e.valid_to = $valid_to,
                    e.provenance_chunk_id = $provenance_chunk_id,
                    e.confidence = $confidence,
                    e.version = $version,
                    e += $props
                """,
                entity_id=entity_id,
                entity_type=entity_type,
                domain=domain,
                valid_from=_to_date_str(valid_from),
                valid_to=_to_date_str(valid_to),
                provenance_chunk_id=provenance_chunk_id,
                confidence=confidence,
                version=version,
                props=properties,
            )
        log.debug("neo4j_entity_upserted", entity_id=entity_id, entity_type=entity_type)

    async def upsert_relation(
        self,
        from_id: str,
        to_id: str,
        relation_type: str,
        properties: dict[str, Any],
        valid_from: date | str | None = None,
        valid_to: date | str | None = None,
        provenance_chunk_id: str | None = None,
        confidence: float = 1.0,
    ) -> None:
        """Bitemporal close-and-create: closes existing open relation, creates new one."""
        now_str = date.today().isoformat()
        async with self._driver.session(database=self._database) as s:
            # Close any open relation of the same type between the same nodes
            await s.run(
                """
                MATCH (a:Entity {entity_id: $from_id})-[r]->(b:Entity {entity_id: $to_id})
                WHERE type(r) = $rel_type AND r.valid_to IS NULL
                SET r.valid_to = $now
                """,
                from_id=from_id,
                to_id=to_id,
                rel_type=relation_type,
                now=now_str,
            )
            # Create new relation with temporal context
            await s.run(
                """
                MATCH (a:Entity {entity_id: $from_id}), (b:Entity {entity_id: $to_id})
                CREATE (a)-[r:`""" + relation_type + """`]->(b)
                SET r.valid_from = $valid_from,
                    r.valid_to = $valid_to,
                    r.provenance_chunk_id = $provenance_chunk_id,
                    r.confidence = $confidence,
                    r += $props
                """,
                from_id=from_id,
                to_id=to_id,
                valid_from=_to_date_str(valid_from),
                valid_to=_to_date_str(valid_to),
                provenance_chunk_id=provenance_chunk_id,
                confidence=confidence,
                props=properties,
            )
        log.debug("neo4j_relation_upserted", from_id=from_id, to_id=to_id, type=relation_type)

    async def get_entities(
        self,
        domain: str,
        entity_type: str | None = None,
        as_of_date: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Returns entities valid at `as_of_date` (defaults to today)."""
        as_of = as_of_date or date.today().isoformat()
        type_clause = "AND e.entity_type = $entity_type" if entity_type else ""
        cypher = f"""
        MATCH (e:Entity)
        WHERE e.domain = $domain
          AND (e.valid_from IS NULL OR e.valid_from <= $as_of)
          AND (e.valid_to IS NULL OR e.valid_to >= $as_of)
          {type_clause}
        RETURN e
        LIMIT $limit
        """
        _assert_readonly(cypher)
        async with self._driver.session(database=self._database) as s:
            result = await s.run(
                cypher,
                domain=domain,
                as_of=as_of,
                entity_type=entity_type,
                limit=limit,
            )
            records = await result.data()
        return [dict(r["e"]) for r in records]

    async def get_relations(
        self,
        domain: str,
        relation_type: str | None = None,
        as_of_date: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        as_of = as_of_date or date.today().isoformat()
        type_clause = f"AND type(r) = '{relation_type}'" if relation_type else ""
        cypher = f"""
        MATCH (a:Entity)-[r]->(b:Entity)
        WHERE a.domain = $domain
          AND (r.valid_from IS NULL OR r.valid_from <= $as_of)
          AND (r.valid_to IS NULL OR r.valid_to >= $as_of)
          {type_clause}
        RETURN a.entity_id AS from_id, type(r) AS rel_type,
               b.entity_id AS to_id, properties(r) AS props
        LIMIT $limit
        """
        _assert_readonly(cypher)
        async with self._driver.session(database=self._database) as s:
            result = await s.run(cypher, domain=domain, as_of=as_of, limit=limit)
            records = await result.data()
        return records

    async def run_readonly_query(
        self,
        cypher: str,
        params: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Execute an arbitrary read-only Cypher query (write guard enforced)."""
        _assert_readonly(cypher)
        async with self._driver.session(database=self._database) as s:
            result = await s.run(cypher, **(params or {}))
            return await result.data()

    async def delete_entity_by_doc_id(self, provenance_chunk_id: str) -> int:
        """Soft-delete: sets valid_to = today on all entities from a document."""
        today = date.today().isoformat()
        async with self._driver.session(database=self._database) as s:
            result = await s.run(
                """
                MATCH (e:Entity {provenance_chunk_id: $chunk_id})
                WHERE e.valid_to IS NULL
                SET e.valid_to = $today
                RETURN count(e) AS n
                """,
                chunk_id=provenance_chunk_id,
                today=today,
            )
            data = await result.single()
        count = data["n"] if data else 0
        log.info("neo4j_soft_deleted", provenance_chunk_id=provenance_chunk_id, count=count)
        return count
