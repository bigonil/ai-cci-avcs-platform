"""Shared fixtures for governance service tests."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from cci_governance.audit_log import GENESIS_HASH, VerificationReport
from cci_governance.config import GovernanceSettings


# ---------------------------------------------------------------------------
# Testcontainers — real MongoDB (integration tests only)
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def mongo_url():
    """Start a real MongoDB container for the session. Requires Docker."""
    pytest.importorskip("testcontainers", reason="testcontainers not installed")
    from testcontainers.mongodb import MongoDbContainer

    with MongoDbContainer("mongo:7.0") as container:
        yield container.get_connection_url()


@pytest_asyncio.fixture()
async def audit_db(mongo_url):
    """Fresh MongoDB database per test, with audit_log_tail pre-seeded."""
    from motor.motor_asyncio import AsyncIOMotorClient

    client = AsyncIOMotorClient(mongo_url)
    db_name = f"test_{uuid.uuid4().hex[:8]}"
    db = client[db_name]
    await db.audit_log_tail.insert_one(
        {"_id": "singleton", "last_seq": 0, "last_hash": GENESIS_HASH}
    )
    yield db
    await client.drop_database(db_name)
    client.close()


# ---------------------------------------------------------------------------
# Mock fixtures — API tests (no Docker needed)
# ---------------------------------------------------------------------------

@pytest.fixture()
def mock_audit():
    m = MagicMock()
    m.append = AsyncMock(return_value=(uuid.uuid4(), 1))
    m.get_by_correlation = AsyncMock(return_value=[])
    m.verify_chain = AsyncMock(
        return_value=VerificationReport(
            total_records=0, valid=True, tail_consistent=True
        )
    )
    return m


@pytest.fixture()
def mock_hitl():
    m = MagicMock()
    _action_doc = {
        "action_id": str(uuid.uuid4()),
        "status": "PENDING",
        "correlation_id": None,
        "domain": "hera_it",
        "action_type": "financial.overrun",
        "impact_eur": 80_000.0,
        "description": "Azure commitment exceeds CTO allocation by 80k EUR",
        "motivation": "Automatic detection by CCI/AVCS system",
        "created_at": datetime.now(timezone.utc),
        "decided_at": None,
        "reviewer_id": None,
        "reviewer_motivation": None,
    }
    m.queue = AsyncMock(return_value=_action_doc)
    m.list_pending = AsyncMock(return_value=[_action_doc])
    m.decide = AsyncMock(return_value={**_action_doc, "status": "APPROVED",
                                        "reviewer_id": "mario.rossi"})
    return m


@pytest_asyncio.fixture()
async def client(mock_audit, mock_hitl):
    """AsyncClient with stub audit/hitl — no real MongoDB."""
    import cci_governance.api as api_module
    from cci_governance.api import app

    api_module._audit = mock_audit
    api_module._hitl = mock_hitl
    api_module._settings = GovernanceSettings(
        CCI_GOVERNANCE_PORT=8005,
        MONGODB_AUDIT_URI="mongodb://localhost:27017/test",
        CCI_GOVERNANCE_DB="test",
    )
    api_module._start_time = 0.0

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    api_module._audit = None
    api_module._hitl = None
    api_module._settings = None
