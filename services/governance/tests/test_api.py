"""API tests for governance service — audit/hitl endpoints, all MongoDB mocked."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest

from cci_governance.audit_log import BrokenLink, VerificationReport


class TestHealthEndpoints:
    @pytest.mark.asyncio
    async def test_live(self, client):
        r = await client.get("/health/live")
        assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_ready(self, client):
        r = await client.get("/health/ready")
        assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_startup(self, client):
        r = await client.get("/health/startup")
        assert r.status_code == 200
        assert "uptime_s" in r.json()


class TestAuditEndpoints:
    @pytest.mark.asyncio
    async def test_append_returns_seq_and_event_id(self, client, mock_audit):
        fixed_uuid = uuid.uuid4()
        mock_audit.append = AsyncMock(return_value=(fixed_uuid, 42))

        r = await client.post("/audit/append", json={
            "event_type": "verification.completed.v1",
            "correlation_id": str(uuid.uuid4()),
            "domain": "hera_it",
            "violations_found": 2,
        })
        assert r.status_code == 201
        body = r.json()
        assert body["seq"] == 42
        assert body["accepted"] is True
        assert "event_id" in body

    @pytest.mark.asyncio
    async def test_append_minimal_payload(self, client):
        r = await client.post("/audit/append", json={
            "event_type": "test.v1",
        })
        assert r.status_code == 201

    @pytest.mark.asyncio
    async def test_by_correlation_empty(self, client):
        r = await client.get(f"/audit/by-correlation/{uuid.uuid4()}")
        assert r.status_code == 200
        body = r.json()
        assert body["events"] == []

    @pytest.mark.asyncio
    async def test_by_correlation_invalid_uuid(self, client):
        r = await client.get("/audit/by-correlation/not-a-uuid")
        assert r.status_code == 400

    @pytest.mark.asyncio
    async def test_chain_verify_valid(self, client, mock_audit):
        mock_audit.verify_chain = AsyncMock(return_value=VerificationReport(
            total_records=7, valid=True, tail_consistent=True,
            first_seq=1, last_seq=7,
        ))
        r = await client.get("/audit/chain/verify")
        assert r.status_code == 200
        body = r.json()
        assert body["valid"] is True
        assert body["total_records"] == 7
        assert body["tail_consistent"] is True

    @pytest.mark.asyncio
    async def test_chain_verify_broken(self, client, mock_audit):
        mock_audit.verify_chain = AsyncMock(return_value=VerificationReport(
            total_records=3, valid=False, tail_consistent=False,
            broken_links=[BrokenLink(seq=2, reason="prev_hash mismatch",
                                     expected="aa", found="bb")],
        ))
        r = await client.get("/audit/chain/verify")
        assert r.status_code == 200
        body = r.json()
        assert body["valid"] is False
        assert len(body["broken_links"]) == 1


class TestHitlEndpoints:
    @pytest.mark.asyncio
    async def test_queue_returns_action(self, client):
        r = await client.post("/hitl/queue", json={
            "domain": "hera_it",
            "action_type": "financial.overrun",
            "impact_eur": 80000.0,
            "description": "Azure commitment exceeds CTO allocation by 80k EUR",
            "motivation": "Automatic detection by CCI/AVCS system",
        })
        assert r.status_code == 201
        body = r.json()
        assert body["status"] == "PENDING"
        assert body["domain"] == "hera_it"
        assert body["impact_eur"] == 80000.0

    @pytest.mark.asyncio
    async def test_queue_short_motivation_rejected(self, client):
        r = await client.post("/hitl/queue", json={
            "domain": "hera_it",
            "action_type": "test",
            "impact_eur": 1000.0,
            "description": "Test",
            "motivation": "short",  # < 20 chars
        })
        assert r.status_code == 422

    @pytest.mark.asyncio
    async def test_list_pending(self, client):
        r = await client.get("/hitl/pending")
        assert r.status_code == 200
        body = r.json()
        assert "pending" in body
        assert "count" in body

    @pytest.mark.asyncio
    async def test_approve_action(self, client, mock_hitl):
        action_id = str(uuid.uuid4())
        r = await client.post(f"/hitl/{action_id}/approve", json={
            "reviewer_id": "mario.rossi",
            "motivation": "Budget approved by CTO after review meeting",
        })
        assert r.status_code == 200
        body = r.json()
        assert body["status"] == "APPROVED"

    @pytest.mark.asyncio
    async def test_reject_action(self, client, mock_hitl):
        action_id = str(uuid.uuid4())
        mock_hitl.decide = AsyncMock(
            return_value={
                "action_id": action_id,
                "status": "REJECTED",
                "correlation_id": None,
                "domain": "hera_it",
                "action_type": "financial.overrun",
                "impact_eur": 80000.0,
                "description": "Azure commitment exceeds CTO allocation by 80k EUR",
                "motivation": "Automatic detection by CCI/AVCS system",
                "created_at": datetime.now(timezone.utc),
                "decided_at": datetime.now(timezone.utc),
                "reviewer_id": "luigi.bianchi",
                "reviewer_motivation": "Rejected — outside budget cycle",
            }
        )
        r = await client.post(f"/hitl/{action_id}/reject", json={
            "reviewer_id": "luigi.bianchi",
            "motivation": "Rejected — outside budget cycle for Q1",
        })
        assert r.status_code == 200
        body = r.json()
        assert body["status"] == "REJECTED"

    @pytest.mark.asyncio
    async def test_approve_not_found_returns_404(self, client, mock_hitl):
        mock_hitl.decide = AsyncMock(return_value=None)
        r = await client.post(f"/hitl/{uuid.uuid4()}/approve", json={
            "reviewer_id": "tester",
            "motivation": "Test approval motivation text here",
        })
        assert r.status_code == 404
