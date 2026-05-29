"""Auditor node — appends verification record to governance audit log (no LLM).

Input state keys:  all accumulated state
Output state keys: audit_seq, audit_logged
"""
from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import httpx
import structlog

from cci_agents.state import VerificationState

log = structlog.get_logger(__name__)

_TIMEOUT = httpx.Timeout(10.0)


async def auditor_node(
    state: VerificationState,
    *,
    governance_url: str,
) -> dict[str, Any]:
    """Append verification result to the immutable governance audit log."""
    errors: list[str] = list(state.get("errors", []))
    correlation_id = state.get("correlation_id", "")

    log.info("auditor_start", correlation_id=correlation_id)

    audit_payload = {
        "event_type": "verification.completed.v1",
        "correlation_id": correlation_id,
        "timestamp": datetime.now(UTC).isoformat(),
        "domain": state.get("domain", ""),
        "as_of_date": state.get("as_of_date", ""),
        "trigger": state.get("trigger", ""),
        "rules_evaluated": [r.get("rule_id") for r in state.get("rules", [])],
        "violations_found": len(state.get("violations", [])),
        "grounding_verified": state.get("grounding_verified", False),
        "hitl_required": state.get("hitl_required", False),
        "citations": state.get("citations", []),
        "verification_source": state.get("verification_source", "unknown"),
    }

    audit_seq: int | None = None
    audit_logged = False

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.post(
                f"{governance_url}/audit/append",
                json=audit_payload,
            )
            resp.raise_for_status()
            data = resp.json()
            audit_seq = data.get("seq")
            audit_logged = True

    except httpx.HTTPError as exc:
        # Governance service may not be up yet (Step 9) — log but don't fail
        log.warning(
            "auditor_governance_unavailable",
            error=str(exc),
            governance_url=governance_url,
        )
        errors.append(f"auditor_unavailable: {exc}")
    except Exception as exc:
        log.error("auditor_unexpected_error", error=str(exc))
        errors.append(f"auditor_error: {exc}")

    log.info(
        "auditor_complete",
        correlation_id=correlation_id,
        audit_seq=audit_seq,
        audit_logged=audit_logged,
    )

    return {
        "audit_seq": audit_seq,
        "audit_logged": audit_logged,
        "errors": errors,
    }
