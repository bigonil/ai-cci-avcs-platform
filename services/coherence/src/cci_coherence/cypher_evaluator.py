"""Graph-based rule evaluation via Cypher temporal queries — ZERO LLM (R4).

Falls back to chunk-based evaluation when Neo4j is disabled or entities
are not found in the graph. All comparisons are arithmetic or date-based.
"""
from __future__ import annotations

from typing import Any

import structlog

from cci_coherence.models import (
    EvaluationContext,
    ExtractedEntity,
    RuleViolation,
)

log = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Cypher templates — read-only, bitemporal-aware (R4)
# ---------------------------------------------------------------------------

# Returns (entity_type, props) rows from the graph for a given domain/entity_type
_QUERY_ENTITIES_BY_TYPE = """
MATCH (e:Entity {domain: $domain, entity_type: $entity_type})
WHERE e.valid_to IS NULL OR e.valid_to >= $as_of_date
RETURN e.properties AS props, e.chunk_ids AS chunk_ids
"""

# Returns all active entities for a domain, grouped by type
_QUERY_ALL_ACTIVE = """
MATCH (e:Entity {domain: $domain})
WHERE e.valid_to IS NULL OR e.valid_to >= $as_of_date
RETURN e.entity_type AS entity_type, e.properties AS props, e.chunk_ids AS chunk_ids
"""


async def load_context_from_graph(
    driver: Any,
    domain: str,
    as_of_date: str,
    database: str = "neo4j",
) -> EvaluationContext:
    """Populate an EvaluationContext from the temporal graph.

    Returns an empty context if no entities are found — callers fall back
    to chunk-based extraction in that case.
    """
    ctx = EvaluationContext(domain=domain, as_of_date=as_of_date)

    try:
        async with driver.session(database=database) as session:
            result = await session.run(
                _QUERY_ALL_ACTIVE,
                domain=domain,
                as_of_date=as_of_date,
            )
            rows = await result.data()

        for row in rows:
            entity_type: str = row["entity_type"]
            props: dict[str, Any] = dict(row["props"] or {})
            chunk_ids: list[str] = list(row["chunk_ids"] or [])
            ctx.add(
                ExtractedEntity(
                    entity_type=entity_type,
                    domain=domain,
                    properties=props,
                    chunk_ids=chunk_ids,
                )
            )

        total = sum(len(v) for v in ctx.entities_by_type.values())
        log.info(
            "graph_context_loaded",
            domain=domain,
            entity_types=list(ctx.entities_by_type.keys()),
            total_entities=total,
        )

    except Exception as exc:
        log.warning("graph_context_load_failed", domain=domain, error=str(exc))

    return ctx


async def evaluate_rule_from_graph(
    driver: Any,
    rule_id: str,
    when_expr: str,
    severity: str,
    domain: str,
    as_of_date: str,
    database: str = "neo4j",
) -> tuple[list[RuleViolation], bool]:
    """Evaluate a rule using graph data. Returns (violations, used_graph).

    `used_graph=False` signals callers to fall back to chunk-based evaluation.
    """
    from cci_coherence.rule_evaluator import evaluate_rule

    ctx = await load_context_from_graph(driver, domain, as_of_date, database)
    if not ctx.entities_by_type:
        return [], False

    violations = evaluate_rule(rule_id, when_expr, severity, domain, ctx)
    return violations, True
