from __future__ import annotations

import time
import uuid
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, HTTPException
from motor.motor_asyncio import AsyncIOMotorClient
from prometheus_fastapi_instrumentator import Instrumentator

from .audit_log import GENESIS_HASH, AuditLog
from .config import GovernanceSettings
from .hitl import HitlService
from .models import (
    AppendRequest,
    AppendResponse,
    ChainVerifyResponse,
    HitlActionCreate,
    HitlActionResponse,
    HitlDecisionRequest,
)

log = structlog.get_logger(__name__)

_settings: GovernanceSettings | None = None
_audit: AuditLog | None = None
_hitl: HitlService | None = None
_mongo_client: AsyncIOMotorClient | None = None
_start_time: float = 0.0


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _settings, _audit, _hitl, _mongo_client, _start_time
    _settings = GovernanceSettings()
    _start_time = time.monotonic()

    _mongo_client = AsyncIOMotorClient(_settings.MONGODB_AUDIT_URI)
    db = _mongo_client[_settings.CCI_GOVERNANCE_DB]

    # Ensure tail singleton exists (idempotent bootstrap)
    if await db.audit_log_tail.find_one({"_id": "singleton"}) is None:
        await db.audit_log_tail.insert_one(
            {"_id": "singleton", "last_seq": 0, "last_hash": GENESIS_HASH}
        )

    _audit = AuditLog(db)
    _hitl = HitlService(db, _audit)

    log.info("governance_startup", port=_settings.CCI_GOVERNANCE_PORT)
    yield

    if _mongo_client:
        _mongo_client.close()
    log.info("governance_shutdown")


app = FastAPI(
    title="CCI/AVCS Governance",
    version="0.1.0",
    description="Immutable audit log, HITL gate, AI Act compliance",
    lifespan=lifespan,
)
Instrumentator().instrument(app).expose(app)


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------


@app.get("/health/live")
async def health_live():
    return {"status": "alive"}


@app.get("/health/ready")
async def health_ready():
    if _audit is None:
        raise HTTPException(503, "not ready")
    return {"status": "ready"}


@app.get("/health/startup")
async def health_startup():
    return {"status": "started", "uptime_s": round(time.monotonic() - (_start_time or 0), 1)}


# ---------------------------------------------------------------------------
# Audit log
# ---------------------------------------------------------------------------


@app.post("/audit/append", response_model=AppendResponse, status_code=201)
async def audit_append(request: AppendRequest):
    if _audit is None:
        raise HTTPException(503, "audit log not ready")
    try:
        corr_uuid = _parse_uuid(request.correlation_id)
        event_id, seq = await _audit.append(
            actor=(_settings.CCI_AUDIT_ACTOR if _settings else "governance-service"),
            event_type=request.event_type,
            payload=request.to_payload(),
            correlation_id=corr_uuid,
        )
        return AppendResponse(seq=seq, event_id=str(event_id))
    except Exception as exc:
        log.error("audit_append_error", error=str(exc))
        raise HTTPException(500, f"audit append failed: {exc}") from exc


@app.get("/audit/by-correlation/{correlation_id}")
async def audit_by_correlation(correlation_id: str):
    if _audit is None:
        raise HTTPException(503, "audit log not ready")
    corr_uuid = _parse_uuid(correlation_id)
    if corr_uuid is None:
        raise HTTPException(400, "invalid correlation_id format (expected UUID)")
    docs = await _audit.get_by_correlation(corr_uuid)
    events = [
        {
            "seq": doc["seq"],
            "event_id": uuid.UUID(bytes=bytes(doc["event_id"])).hex,
            "ts": doc["ts"].isoformat(),
            "actor": doc["actor"],
            "event_type": doc["event_type"],
            "payload": doc["payload"],
        }
        for doc in docs
    ]
    return {"correlation_id": correlation_id, "events": events}


@app.get("/audit/chain/verify", response_model=ChainVerifyResponse)
async def chain_verify():
    if _audit is None:
        raise HTTPException(503, "audit log not ready")
    report = await _audit.verify_chain()
    return ChainVerifyResponse(
        valid=report.valid,
        total_records=report.total_records,
        tail_consistent=report.tail_consistent,
        broken_links=[
            {"seq": bl.seq, "reason": bl.reason,
             "expected": bl.expected, "found": bl.found}
            for bl in report.broken_links
        ],
        first_seq=report.first_seq,
        last_seq=report.last_seq,
    )


# ---------------------------------------------------------------------------
# HITL
# ---------------------------------------------------------------------------


@app.post("/hitl/queue", response_model=HitlActionResponse, status_code=201)
async def hitl_queue(request: HitlActionCreate):
    if _hitl is None:
        raise HTTPException(503, "not ready")
    doc = await _hitl.queue(
        correlation_id=request.correlation_id,
        domain=request.domain,
        action_type=request.action_type,
        impact_eur=request.impact_eur,
        description=request.description,
        motivation=request.motivation,
    )
    return HitlActionResponse(**doc)


@app.get("/hitl/pending")
async def hitl_list_pending():
    if _hitl is None:
        raise HTTPException(503, "not ready")
    docs = await _hitl.list_pending()
    return {"pending": docs, "count": len(docs)}


@app.post("/hitl/{action_id}/approve", response_model=HitlActionResponse)
async def hitl_approve(action_id: str, request: HitlDecisionRequest):
    if _hitl is None:
        raise HTTPException(503, "not ready")
    doc = await _hitl.decide(
        action_id, approved=True,
        reviewer_id=request.reviewer_id, motivation=request.motivation,
    )
    if doc is None:
        raise HTTPException(404, f"action {action_id!r} not found or not PENDING")
    return HitlActionResponse(**doc)


@app.post("/hitl/{action_id}/reject", response_model=HitlActionResponse)
async def hitl_reject(action_id: str, request: HitlDecisionRequest):
    if _hitl is None:
        raise HTTPException(503, "not ready")
    doc = await _hitl.decide(
        action_id, approved=False,
        reviewer_id=request.reviewer_id, motivation=request.motivation,
    )
    if doc is None:
        raise HTTPException(404, f"action {action_id!r} not found or not PENDING")
    return HitlActionResponse(**doc)


def _parse_uuid(value: str | None) -> uuid.UUID | None:
    if not value:
        return None
    try:
        return uuid.UUID(str(value))
    except ValueError:
        return None
