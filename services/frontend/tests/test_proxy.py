import pytest
from unittest.mock import AsyncMock, MagicMock
from fastapi.testclient import TestClient
from cci_frontend.main import app

client = TestClient(app)


def _mock_response(status_code: int = 200, content: bytes = b'{"ok": true}'):
    resp = MagicMock()
    resp.status_code = status_code
    resp.content = content
    resp.headers = {"content-type": "application/json"}
    return resp


def _make_mock_http_client():
    mock_client = AsyncMock()
    mock_client.request = AsyncMock(return_value=_mock_response())
    return mock_client


def test_proxy_incoherences_list():
    mock_client = _make_mock_http_client()
    app.state.http_client = mock_client

    resp = client.get("/api/incoherences?domain=hera_it")
    assert resp.status_code == 200
    call_args = mock_client.request.call_args
    assert "incoherences" in call_args.kwargs["url"]
    assert "domain=hera_it" in call_args.kwargs["url"]


def test_proxy_incoherence_explain():
    mock_client = _make_mock_http_client()
    app.state.http_client = mock_client

    resp = client.post("/api/incoherences/abc123/explain")
    assert resp.status_code == 200
    call_args = mock_client.request.call_args
    assert "abc123/explain" in call_args.kwargs["url"]


def test_proxy_hitl_routes_to_governance():
    mock_client = _make_mock_http_client()
    app.state.http_client = mock_client

    resp = client.get("/api/hitl/queue")
    assert resp.status_code == 200
    call_args = mock_client.request.call_args
    assert "governance" in call_args.kwargs["url"] or "8005" in call_args.kwargs["url"]


def test_proxy_unknown_path_returns_404():
    resp = client.get("/api/unknown/path")
    assert resp.status_code == 404
