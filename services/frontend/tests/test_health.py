import pytest
from fastapi.testclient import TestClient
from cci_frontend.main import app


@pytest.fixture
def client():
    return TestClient(app)


def test_live_returns_ok(client):
    resp = client.get("/health/live")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_ready_returns_ok(client):
    resp = client.get("/health/ready")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_startup_returns_ok(client):
    resp = client.get("/health/startup")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
