"""Append-only audit log with SHA-256 hash chain (R5 — immutabilità garantita).

PERMITTED operations on audit_log: insertOne only.
PERMITTED operations on audit_log_tail: find_one_and_update + update_one (tail singleton only).
FORBIDDEN on audit_log: update, delete, replace, drop.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

import structlog
from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError

log = structlog.get_logger(__name__)

GENESIS_HASH = b"\x00" * 32
TAIL_DOC_ID = "singleton"


def canonical_json(payload: dict[str, Any]) -> bytes:
    """Stable JSON — sorted keys, compact, UTF-8 — required for hash determinism."""
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _ts_canonical(ts: datetime) -> str:
    """UTC ISO string at millisecond precision — matches BSON DateTime round-trip."""
    ts_utc = ts.replace(tzinfo=timezone.utc) if ts.tzinfo is None else ts.astimezone(timezone.utc)
    ms = (ts_utc.microsecond // 1000) * 1000
    return ts_utc.replace(microsecond=ms).isoformat()


def compute_record_hash(
    *,
    prev_hash: bytes,
    event_id: uuid.UUID,
    ts: datetime,
    actor: str,
    event_type: str,
    payload: dict[str, Any],
) -> bytes:
    h = hashlib.sha256()
    h.update(prev_hash)
    h.update(event_id.bytes)
    h.update(_ts_canonical(ts).encode("ascii"))
    h.update(actor.encode("utf-8"))
    h.update(event_type.encode("utf-8"))
    h.update(canonical_json(payload))
    return h.digest()


class AuditChainCorruption(Exception):
    """Raised when the hash chain shows signs of forking or tampering."""


@dataclass
class BrokenLink:
    seq: int
    reason: str
    expected: str | None = None
    found: str | None = None


@dataclass
class VerificationReport:
    total_records: int = 0
    valid: bool = False
    broken_links: list[BrokenLink] = field(default_factory=list)
    first_seq: int | None = None
    last_seq: int | None = None
    tail_consistent: bool = False


class AuditLog:
    """Append-only audit log on MongoDB with SHA-256 hash chain.

    Thread-safe within a process via asyncio.Lock.
    Inter-process safety via atomic findOneAndUpdate on audit_log_tail singleton.
    """

    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self._db = db
        self._collection = db.audit_log
        self._tail = db.audit_log_tail
        self._lock = asyncio.Lock()

    async def append(
        self,
        *,
        actor: str,
        event_type: str,
        payload: dict[str, Any],
        correlation_id: uuid.UUID | None = None,
    ) -> tuple[uuid.UUID, int]:
        """Atomically appends an event to the chain. Returns (event_id, seq)."""
        async with self._lock:
            event_id = uuid.uuid4()
            ts = datetime.now(timezone.utc)

            # Step 1: atomically advance tail, read previous state
            tail_before = await self._tail.find_one_and_update(
                {"_id": TAIL_DOC_ID},
                {"$inc": {"last_seq": 1}},
                return_document=ReturnDocument.BEFORE,
            )
            if tail_before is None:
                raise RuntimeError("audit_log_tail singleton missing — init script not run")

            prev_hash: bytes = bytes(tail_before["last_hash"])
            new_seq: int = tail_before["last_seq"] + 1

            # Step 2: compute record hash
            record_hash = compute_record_hash(
                prev_hash=prev_hash,
                event_id=event_id,
                ts=ts,
                actor=actor,
                event_type=event_type,
                payload=payload,
            )

            # Step 3: insert audit document (append-only)
            try:
                await self._collection.insert_one({
                    "seq": new_seq,
                    "event_id": event_id.bytes,
                    "correlation_id": correlation_id.bytes if correlation_id else None,
                    "ts": ts,
                    "actor": actor,
                    "event_type": event_type,
                    "payload": payload,
                    "prev_hash": prev_hash,
                    "record_hash": record_hash,
                    "schema_version": "1.0",
                })
            except DuplicateKeyError as exc:
                raise AuditChainCorruption(
                    f"Duplicate key inserting seq={new_seq}: chain integrity at risk"
                ) from exc

            # Step 4: commit the new hash to the tail
            await self._tail.update_one(
                {"_id": TAIL_DOC_ID},
                {"$set": {"last_hash": record_hash}},
            )

            log.info(
                "audit_appended",
                seq=new_seq,
                event_type=event_type,
                actor=actor,
                event_id=str(event_id),
            )
            return event_id, new_seq

    async def get_by_correlation(self, correlation_id: uuid.UUID) -> list[dict[str, Any]]:
        cursor = self._collection.find(
            {"correlation_id": correlation_id.bytes}
        ).sort("seq", 1)
        return [doc async for doc in cursor]

    async def verify_chain(self) -> VerificationReport:
        """Recomputes every hash in the chain and verifies consistency with the tail."""
        report = VerificationReport()
        expected_prev = GENESIS_HASH

        cursor = self._collection.find().sort("seq", 1)
        async for doc in cursor:
            report.total_records += 1
            if report.first_seq is None:
                report.first_seq = doc["seq"]
            report.last_seq = doc["seq"]

            prev = bytes(doc["prev_hash"])
            if prev != expected_prev:
                report.broken_links.append(BrokenLink(
                    seq=doc["seq"],
                    reason="prev_hash mismatch with running chain",
                    expected=expected_prev.hex(),
                    found=prev.hex(),
                ))
                break

            recomputed = compute_record_hash(
                prev_hash=prev,
                event_id=uuid.UUID(bytes=bytes(doc["event_id"])),
                ts=doc["ts"],
                actor=doc["actor"],
                event_type=doc["event_type"],
                payload=doc["payload"],
            )
            rec_hash = bytes(doc["record_hash"])
            if recomputed != rec_hash:
                report.broken_links.append(BrokenLink(
                    seq=doc["seq"],
                    reason="record_hash recomputation mismatch",
                    expected=recomputed.hex(),
                    found=rec_hash.hex(),
                ))
                break

            expected_prev = rec_hash

        tail = await self._tail.find_one({"_id": TAIL_DOC_ID})
        if tail:
            report.tail_consistent = (
                tail["last_seq"] == (report.last_seq or 0)
                and bytes(tail["last_hash"]) == expected_prev
            )

        report.valid = not report.broken_links and report.tail_consistent
        return report
