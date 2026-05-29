"""Integration tests for AuditLog — require Docker (testcontainers MongoDB)."""
from __future__ import annotations

import asyncio

import pytest

from cci_governance.audit_log import GENESIS_HASH, AuditLog

pytestmark = pytest.mark.asyncio


class TestAuditLogAppend:
    async def test_single_append_returns_seq_one(self, audit_db):
        audit = AuditLog(audit_db)
        event_id, seq = await audit.append(
            actor="test-service",
            event_type="test.event.v1",
            payload={"key": "value"},
        )
        assert seq == 1
        assert event_id is not None

    async def test_sequential_appends_increment_seq(self, audit_db):
        audit = AuditLog(audit_db)
        for i in range(1, 4):
            _, seq = await audit.append(
                actor="test-service",
                event_type="test.event.v1",
                payload={"i": i},
            )
            assert seq == i

    async def test_chain_valid_after_sequential_appends(self, audit_db):
        audit = AuditLog(audit_db)
        for i in range(5):
            await audit.append(
                actor="test-service",
                event_type="test.sequential.v1",
                payload={"index": i},
            )
        report = await audit.verify_chain()
        assert report.valid
        assert report.total_records == 5
        assert report.tail_consistent
        assert not report.broken_links
        assert report.first_seq == 1
        assert report.last_seq == 5

    async def test_tail_consistent_after_appends(self, audit_db):
        audit = AuditLog(audit_db)
        await audit.append(actor="a", event_type="t.v1", payload={})
        await audit.append(actor="b", event_type="t.v1", payload={})
        tail = await audit_db.audit_log_tail.find_one({"_id": "singleton"})
        assert tail["last_seq"] == 2
        assert bytes(tail["last_hash"]) != GENESIS_HASH

    async def test_concurrent_appends_maintain_chain(self, audit_db):
        audit = AuditLog(audit_db)

        async def write(i: int) -> None:
            await audit.append(
                actor="concurrent-writer",
                event_type="test.concurrent.v1",
                payload={"index": i},
            )

        await asyncio.gather(*[write(i) for i in range(10)])

        report = await audit.verify_chain()
        assert report.valid
        assert report.total_records == 10
        assert report.tail_consistent

    async def test_empty_chain_is_valid(self, audit_db):
        audit = AuditLog(audit_db)
        report = await audit.verify_chain()
        assert report.valid
        assert report.total_records == 0
        assert report.tail_consistent
