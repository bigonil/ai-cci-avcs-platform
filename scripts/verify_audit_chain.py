"""Verifica integrità della hash chain SHA-256 dell'audit log MongoDB.

Standalone CLI — non importa dal servizio, riduplica le funzioni hash per essere
self-contained e verificabile indipendentemente dalla governance service.

Uso:
    uv run python scripts/verify_audit_chain.py
    MONGODB_AUDIT_URI=mongodb://... uv run python scripts/verify_audit_chain.py

Variabili d'ambiente (priorità decrescente):
    MONGODB_AUDIT_URI  — URI con credenziali per cci_governance (audit writer o admin)
    MONGODB_URI        — URI generico (authSource=admin)
    default            — mongodb://root:changeme@localhost:27017  (dev locale)
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

# ── hash algorithm (must be bit-for-bit identical to audit_log.py) ────────────

GENESIS_HASH: bytes = b"\x00" * 32
TAIL_DOC_ID: str = "singleton"


def canonical_json(payload: dict[str, Any]) -> bytes:
    return json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def _ts_canonical(ts: datetime) -> str:
    """UTC ISO at millisecond precision — matches BSON DateTime round-trip."""
    ts_utc = (
        ts.replace(tzinfo=timezone.utc) if ts.tzinfo is None else ts.astimezone(timezone.utc)
    )
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


# ── report dataclasses ─────────────────────────────────────────────────────────

@dataclass
class BrokenLink:
    seq: int
    reason: str
    expected: str | None = None
    found: str | None = None


@dataclass
class VerificationReport:
    uri: str = ""
    total_records: int = 0
    valid: bool = False
    broken_links: list[BrokenLink] = field(default_factory=list)
    first_seq: int | None = None
    last_seq: int | None = None
    tail_consistent: bool = False
    genesis_ok: bool = False


# ── verification logic (sync pymongo) ─────────────────────────────────────────

def verify_chain(db: Any) -> VerificationReport:  # db: pymongo.database.Database
    report = VerificationReport()
    expected_prev = GENESIS_HASH

    cursor = db.audit_log.find({}, sort=[("seq", 1)])
    for doc in cursor:
        report.total_records += 1
        seq: int = doc["seq"]

        if report.first_seq is None:
            report.first_seq = seq
            # First document must reference GENESIS_HASH
            first_prev = bytes(doc["prev_hash"])
            report.genesis_ok = first_prev == GENESIS_HASH

        report.last_seq = seq

        # Check prev_hash continuity
        stored_prev = bytes(doc["prev_hash"])
        if stored_prev != expected_prev:
            report.broken_links.append(BrokenLink(
                seq=seq,
                reason="prev_hash mismatch with running chain",
                expected=expected_prev.hex(),
                found=stored_prev.hex(),
            ))
            break

        # Recompute and verify record_hash
        try:
            recomputed = compute_record_hash(
                prev_hash=stored_prev,
                event_id=uuid.UUID(bytes=bytes(doc["event_id"])),
                ts=doc["ts"],
                actor=doc["actor"],
                event_type=doc["event_type"],
                payload=doc["payload"],
            )
        except Exception as exc:  # noqa: BLE001
            report.broken_links.append(BrokenLink(
                seq=seq,
                reason=f"hash computation error: {exc}",
            ))
            break

        stored_hash = bytes(doc["record_hash"])
        if recomputed != stored_hash:
            report.broken_links.append(BrokenLink(
                seq=seq,
                reason="record_hash recomputation mismatch",
                expected=recomputed.hex(),
                found=stored_hash.hex(),
            ))
            break

        expected_prev = stored_hash

    # Verify tail singleton consistency
    tail = db.audit_log_tail.find_one({"_id": TAIL_DOC_ID})
    if tail is not None:
        tail_seq: int = tail["last_seq"]
        tail_hash: bytes = bytes(tail["last_hash"])
        report.tail_consistent = (
            tail_seq == (report.last_seq or 0)
            and tail_hash == expected_prev
        )

    report.valid = (
        not report.broken_links
        and report.tail_consistent
        and (report.total_records == 0 or report.genesis_ok)
    )
    return report


# ── formatting ─────────────────────────────────────────────────────────────────

WIDTH = 65
LINE = "━" * WIDTH


def fmt_bool(ok: bool, label_ok: str = "✓", label_fail: str = "✗") -> str:
    return label_ok if ok else label_fail


def print_report(report: VerificationReport) -> None:
    total_fmt = f"{report.total_records:_}" if report.total_records else "0"
    print(LINE)
    print("  CCI/AVCS · audit chain integrity check (MongoDB)")
    print(LINE)
    print(f"  MongoDB:          {report.uri}")
    print(f"  Collection:       audit_log")
    print(f"  Records examined: {total_fmt}")

    if report.total_records == 0:
        print(f"  Chain integrity:  ─ empty collection (no records)")
        print(f"  Tail consistent:  {fmt_bool(report.tail_consistent)} (last_seq={report.last_seq or 0})")
    else:
        print(f"  First seq:        {report.first_seq}")
        print(f"  Last seq:         {report.last_seq}")
        print(f"  Genesis verified: {fmt_bool(report.genesis_ok)}")

        if report.valid:
            print(f"  Chain integrity:  ✓ ALL RECORDS VALID")
        else:
            broken = report.broken_links
            seq_str = str(broken[0].seq) if broken else "?"
            print(f"  Chain integrity:  ❌ BROKEN AT seq={seq_str}")

        tail_seq = report.last_seq or 0
        print(
            f"  Tail consistent:  {fmt_bool(report.tail_consistent)}"
            f" (last_seq={tail_seq})"
        )
        print(f"  Broken links:     {len(report.broken_links)}")

    print(LINE)

    if report.broken_links:
        print()
        print("  BROKEN LINK DETAIL:")
        for link in report.broken_links:
            print(f"    seq={link.seq}: {link.reason}")
            if link.expected:
                print(f"      expected: {link.expected[:32]}…")
                print(f"      found:    {(link.found or '')[:32]}…")
        print()
        print("  ⚠  Do NOT attempt to repair the chain.")
        print("     Open an incident ticket immediately.")
        print("     See: .claude/skills/cci-audit-chain/SKILL.md")
        print(LINE)


# ── entry point ────────────────────────────────────────────────────────────────

def _resolve_uri() -> str:
    return (
        os.getenv("MONGODB_AUDIT_URI")
        or os.getenv("MONGODB_URI")
        or "mongodb://root:changeme@localhost:27017"
    )


def main() -> None:
    # Force UTF-8 on Windows consoles (default cp1252 can't encode box-drawing chars).
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    try:
        import pymongo  # noqa: PLC0415
    except ImportError:
        print("ERROR: pymongo not installed. Run: uv sync", file=sys.stderr)
        sys.exit(1)

    uri = _resolve_uri()
    db_name = os.getenv("CCI_GOVERNANCE_DB", "cci_governance")

    try:
        client: pymongo.MongoClient = pymongo.MongoClient(  # type: ignore[type-arg]
            uri,
            serverSelectionTimeoutMS=5000,
            connectTimeoutMS=5000,
        )
        # Force connection check
        client.admin.command("ping")
    except Exception as exc:  # noqa: BLE001
        print(LINE)
        print("  CCI/AVCS · audit chain integrity check (MongoDB)")
        print(LINE)
        print(f"  ❌ Cannot connect to MongoDB: {exc}")
        print(f"     URI: {uri}")
        print()
        print("  Ensure the stack is running:")
        print("    docker compose up -d mongodb")
        print("    docker compose ps --status running | grep mongodb")
        print(LINE)
        sys.exit(1)

    db = client[db_name]
    report = verify_chain(db)
    report.uri = f"{uri.split('@')[-1]}/{db_name}" if "@" in uri else f"{uri}/{db_name}"
    client.close()

    print_report(report)
    sys.exit(0 if report.valid or report.total_records == 0 else 1)


if __name__ == "__main__":
    main()
