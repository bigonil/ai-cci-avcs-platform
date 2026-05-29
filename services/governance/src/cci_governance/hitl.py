"""Human-in-the-loop service — R6 compliance gate.

HITL actions are stored in hitl_actions (mutable, operational collection).
Every state transition is recorded in the immutable audit_log.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

import structlog
from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo import ReturnDocument

from .audit_log import AuditLog

log = structlog.get_logger(__name__)


class HitlService:
    def __init__(self, db: AsyncIOMotorDatabase, audit: AuditLog) -> None:
        self._col = db.hitl_actions
        self._audit = audit

    async def queue(
        self,
        *,
        correlation_id: str | None,
        domain: str,
        action_type: str,
        impact_eur: float,
        description: str,
        motivation: str,
    ) -> dict[str, Any]:
        action_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        doc: dict[str, Any] = {
            "action_id": action_id,
            "status": "PENDING",
            "correlation_id": correlation_id,
            "domain": domain,
            "action_type": action_type,
            "impact_eur": impact_eur,
            "description": description,
            "motivation": motivation,
            "created_at": now,
            "decided_at": None,
            "reviewer_id": None,
            "reviewer_motivation": None,
        }
        await self._col.insert_one(doc)

        corr_uuid = _parse_uuid(correlation_id)
        await self._audit.append(
            actor="governance-service",
            event_type="hitl.action.queued.v1",
            payload={
                "action_id": action_id,
                "domain": domain,
                "action_type": action_type,
                "impact_eur": impact_eur,
                "description": description,
            },
            correlation_id=corr_uuid,
        )
        log.info("hitl_queued", action_id=action_id, domain=domain, impact_eur=impact_eur)
        return {k: v for k, v in doc.items() if k != "_id"}

    async def list_pending(self) -> list[dict[str, Any]]:
        cursor = self._col.find({"status": "PENDING"}, {"_id": 0}).sort("created_at", 1)
        return [doc async for doc in cursor]

    async def decide(
        self,
        action_id: str,
        *,
        approved: bool,
        reviewer_id: str,
        motivation: str,
    ) -> dict[str, Any] | None:
        status = "APPROVED" if approved else "REJECTED"
        event_type = "hitl.action.approved.v1" if approved else "hitl.action.rejected.v1"
        now = datetime.now(timezone.utc)

        doc = await self._col.find_one_and_update(
            {"action_id": action_id, "status": "PENDING"},
            {"$set": {
                "status": status,
                "decided_at": now,
                "reviewer_id": reviewer_id,
                "reviewer_motivation": motivation,
            }},
            return_document=ReturnDocument.AFTER,
            projection={"_id": 0},
        )
        if doc is None:
            return None

        corr_uuid = _parse_uuid(doc.get("correlation_id"))
        await self._audit.append(
            actor=reviewer_id,
            event_type=event_type,
            payload={
                "action_id": action_id,
                "reviewer_id": reviewer_id,
                "motivation": motivation,
            },
            correlation_id=corr_uuid,
        )
        log.info("hitl_decided", action_id=action_id, status=status, reviewer_id=reviewer_id)
        return doc


def _parse_uuid(value: str | None) -> uuid.UUID | None:
    if not value:
        return None
    try:
        return uuid.UUID(str(value))
    except ValueError:
        return None
