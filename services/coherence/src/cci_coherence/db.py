"""Explanation cache for incoherences — MongoDB collection `incoherences`.

This is a mutable collection (NOT audit_log). update_one with upsert=True
is correct here: R5 applies only to audit_log.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import structlog
from motor.motor_asyncio import AsyncIOMotorDatabase

log = structlog.get_logger(__name__)


class IncoherenceDB:
    """Manages the `incoherences` collection for explanation caching."""

    def __init__(self, db: AsyncIOMotorDatabase) -> None:  # type: ignore[type-arg]
        self._col = db.incoherences

    async def get_explanation(self, incoherence_id: str) -> dict[str, Any] | None:
        """Return cached explanation fields if present, else None."""
        doc = await self._col.find_one({"_id": incoherence_id})
        if doc and doc.get("explanation"):
            return {
                "text": doc["explanation"],
                "citations": doc.get("citations", []),
                "grounding_verified": doc.get("grounding_verified", False),
            }
        return None

    async def upsert_explanation(
        self,
        incoherence_id: str,
        *,
        domain: str,
        rule_id: str,
        explanation: str,
        citations: list[str],
        grounding_verified: bool,
    ) -> None:
        """Persist (or update) the explanation for an incoherence."""
        await self._col.update_one(
            {"_id": incoherence_id},
            {
                "$set": {
                    "domain": domain,
                    "rule_id": rule_id,
                    "explanation": explanation,
                    "citations": citations,
                    "grounding_verified": grounding_verified,
                    "generated_at": datetime.now(timezone.utc).isoformat(),
                    "generator_version": "v1",
                }
            },
            upsert=True,
        )
        log.info(
            "explanation_cached",
            incoherence_id=incoherence_id,
            domain=domain,
            rule_id=rule_id,
            citations=len(citations),
        )
