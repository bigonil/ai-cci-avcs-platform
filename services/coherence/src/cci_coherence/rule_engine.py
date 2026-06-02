"""CoherenceEngine — orchestrates extraction + rule evaluation (R4: zero LLM).

Two evaluation modes:
  1. Chunk mode  — entities extracted from raw text chunks via regex
  2. Graph mode  — entities loaded from Neo4j temporal graph (preferred when available)

The engine is called from the FastAPI layer; it never touches an LLM.
"""
from __future__ import annotations

import asyncio
from datetime import date
from typing import Any

import structlog

from cci_common.domain import Severity
from cci_coherence.config import CoherenceSettings
from cci_coherence.cypher_evaluator import evaluate_rule_from_graph
from cci_coherence.entity_extractor import extract_entities
from cci_coherence.models import EvaluationContext, RuleViolation
from cci_coherence.rule_evaluator import evaluate_rule

log = structlog.get_logger(__name__)


class CoherenceEngine:
    """Stateless engine — one instance per process, called per request."""

    def __init__(self, settings: CoherenceSettings, neo4j_driver: Any | None = None) -> None:
        self._settings = settings
        self._driver = neo4j_driver  # None when neo4j_enabled=False or connection failed

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def verify_chunks(
        self,
        chunks: list[dict[str, Any]],
        domain: str,
        rules: list[dict[str, Any]],
        as_of_date: str | None = None,
    ) -> list[dict[str, Any]]:
        """Evaluate rules against raw text chunks (no graph required).

        Returns a list of incoherence dicts ready for the API response.
        """
        as_of = as_of_date or date.today().isoformat()
        ctx = await asyncio.get_event_loop().run_in_executor(
            None, extract_entities, chunks, domain
        )
        return self._run_rules(rules, domain, ctx)

    async def verify_graph(
        self,
        domain: str,
        rules: list[dict[str, Any]],
        as_of_date: str | None = None,
    ) -> tuple[list[dict[str, Any]], bool]:
        """Evaluate rules against entities indexed in the Neo4j graph.

        Returns (violations, graph_had_entities). When graph_had_entities is False
        the caller should fall back to chunk-based evaluation.
        """
        as_of = as_of_date or date.today().isoformat()
        violations: list[dict[str, Any]] = []
        graph_had_entities = False

        if not self._driver:
            log.warning("graph_unavailable_skip", domain=domain)
            return violations, False

        for rule in rules:
            rule_id: str = rule["rule_id"]
            when_expr: str = rule.get("when", "")
            severity: str = rule.get("severity", Severity.MEDIUM)

            try:
                rule_violations, used_graph = await evaluate_rule_from_graph(
                    driver=self._driver,
                    rule_id=rule_id,
                    when_expr=when_expr,
                    severity=severity,
                    domain=domain,
                    as_of_date=as_of,
                    database=self._settings.neo4j_database,
                )
            except Exception as exc:
                log.error("graph_rule_error", rule_id=rule_id, error=str(exc))
                continue

            if not used_graph:
                log.info("graph_rule_skipped_no_entities", rule_id=rule_id, domain=domain)
                continue

            graph_had_entities = True
            for v in rule_violations:
                violations.append(v.to_incoherence_dict(domain))

        log.info(
            "verify_graph_complete",
            domain=domain,
            rules_evaluated=len(rules),
            violations=len(violations),
            graph_had_entities=graph_had_entities,
        )
        return violations, graph_had_entities

    async def verify(
        self,
        chunks: list[dict[str, Any]],
        domain: str,
        rules: list[dict[str, Any]],
        as_of_date: str | None = None,
    ) -> dict[str, Any]:
        """Full verification: graph first, fall back to chunks.

        Returns the canonical response body for POST /verify.
        """
        as_of = as_of_date or date.today().isoformat()

        # Attempt graph-based evaluation; fall back to chunks when graph has no entities
        if self._driver and self._settings.neo4j_enabled:
            graph_violations, graph_had_entities = await self.verify_graph(domain, rules, as_of)
            if graph_had_entities:
                source = "graph"
                violations = graph_violations
            else:
                violations, source = await self._chunk_fallback(chunks, domain, rules, as_of)
        else:
            violations, source = await self._chunk_fallback(chunks, domain, rules, as_of)

        log.info(
            "verify_complete",
            domain=domain,
            source=source,
            total_violations=len(violations),
        )

        return {
            "domain": domain,
            "as_of_date": as_of,
            "evaluation_source": source,
            "rules_evaluated": len(rules),
            "incoherences_found": len(violations),
            "violations": violations,
        }

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    async def _chunk_fallback(
        self,
        chunks: list[dict[str, Any]],
        domain: str,
        rules: list[dict[str, Any]],
        as_of: str,
    ) -> tuple[list[dict[str, Any]], str]:
        raw = await self.verify_chunks(chunks, domain, rules, as_of)
        return raw, "chunks"

    def _run_rules(
        self,
        rules: list[dict[str, Any]],
        domain: str,
        ctx: EvaluationContext,
    ) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        for rule in rules:
            rule_id: str = rule["rule_id"]
            when_expr: str = rule.get("when", "")
            severity: str = rule.get("severity", Severity.MEDIUM)
            try:
                violations: list[RuleViolation] = evaluate_rule(
                    rule_id=rule_id,
                    when_expr=when_expr,
                    severity=severity,
                    domain=domain,
                    ctx=ctx,
                )
            except Exception as exc:
                log.error("rule_eval_error", rule_id=rule_id, error=str(exc))
                continue
            for v in violations:
                results.append(v.to_incoherence_dict(domain))
        return results
