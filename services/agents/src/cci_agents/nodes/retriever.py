"""Retriever node — HTTP call to retrieval service (no LLM).

Input state keys:  query, domain, as_of_date
Output state keys: chunks
"""
from __future__ import annotations

from typing import Any

import httpx
import structlog

from cci_agents.state import VerificationState

log = structlog.get_logger(__name__)

_TIMEOUT = httpx.Timeout(30.0)


async def retriever_node(
    state: VerificationState,
    *,
    retrieval_url: str,
    top_k: int = 20,
) -> dict[str, Any]:
    """Retrieve relevant chunks from the retrieval service via hybrid search."""
    query = state.get("query", state.get("trigger", ""))
    domain = state.get("domain", "")
    as_of_date = state.get("as_of_date", "")
    errors: list[str] = list(state.get("errors", []))

    log.info(
        "retriever_start",
        correlation_id=state.get("correlation_id"),
        query=query[:80],
        domain=domain,
    )

    chunks: list[dict[str, Any]] = []

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.post(
                f"{retrieval_url}/search",
                json={
                    "query": query,
                    "domain": domain,
                    "top_k": top_k,
                    "as_of_date": as_of_date or None,
                    "rerank": True,
                },
            )
            resp.raise_for_status()
            data = resp.json()
            chunks = data.get("results", [])

    except httpx.HTTPError as exc:
        log.warning(
            "retriever_http_error",
            error=str(exc),
            retrieval_url=retrieval_url,
        )
        errors.append(f"retriever_unavailable: {exc}")
    except Exception as exc:
        log.error("retriever_unexpected_error", error=str(exc))
        errors.append(f"retriever_error: {exc}")

    log.info(
        "retriever_complete",
        correlation_id=state.get("correlation_id"),
        chunks_retrieved=len(chunks),
    )

    return {"chunks": chunks, "errors": errors}
