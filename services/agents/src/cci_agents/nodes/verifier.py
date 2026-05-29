"""Verifier node — HTTP call to coherence service (no LLM, R4 enforced).

Input state keys:  chunks, rules, domain, as_of_date
Output state keys: violations, verification_source
"""
from __future__ import annotations

from typing import Any

import httpx
import structlog

from cci_agents.state import VerificationState

log = structlog.get_logger(__name__)

_TIMEOUT = httpx.Timeout(30.0)


async def verifier_node(
    state: VerificationState,
    *,
    coherence_url: str,
) -> dict[str, Any]:
    """Call the coherence engine to evaluate rules against retrieved chunks."""
    chunks = state.get("chunks", [])
    rules = state.get("rules", [])
    domain = state.get("domain", "")
    as_of_date = state.get("as_of_date", "")
    errors: list[str] = list(state.get("errors", []))

    log.info(
        "verifier_start",
        correlation_id=state.get("correlation_id"),
        chunks=len(chunks),
        rules=[r.get("rule_id") for r in rules],
    )

    violations: list[dict[str, Any]] = []
    source = "none"

    if not rules:
        log.warning("verifier_no_rules", domain=domain)
        return {"violations": [], "verification_source": "none", "errors": errors}

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.post(
                f"{coherence_url}/verify/chunks",
                json={
                    "domain": domain,
                    "chunks": chunks,
                    "rules": rules,
                    "as_of_date": as_of_date or None,
                },
            )
            resp.raise_for_status()
            data = resp.json()
            violations = data.get("violations", [])
            source = data.get("evaluation_source", "chunks")

    except httpx.HTTPError as exc:
        log.warning(
            "verifier_http_error",
            error=str(exc),
            coherence_url=coherence_url,
        )
        errors.append(f"verifier_unavailable: {exc}")
    except Exception as exc:
        log.error("verifier_unexpected_error", error=str(exc))
        errors.append(f"verifier_error: {exc}")

    log.info(
        "verifier_complete",
        correlation_id=state.get("correlation_id"),
        violations_found=len(violations),
        source=source,
    )

    return {
        "violations": violations,
        "verification_source": source,
        "errors": errors,
    }
