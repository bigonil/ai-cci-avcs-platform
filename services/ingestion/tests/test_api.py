"""Test API ingestion-service con client httpx (no containers)."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from cci_ingestion.api import app
from cci_ingestion.pipeline import IngestionResult


@pytest.fixture
def client() -> TestClient:
    return TestClient(app, raise_server_exceptions=False)


class TestHealthEndpoints:
    def test_health_live(self, client: TestClient) -> None:
        response = client.get("/health/live")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"

    def test_health_startup(self, client: TestClient) -> None:
        response = client.get("/health/startup")
        assert response.status_code == 200

    def test_openapi_accessible(self, client: TestClient) -> None:
        response = client.get("/openapi.json")
        assert response.status_code == 200
        data = response.json()
        assert "paths" in data
        assert "/documents" in data["paths"]


class TestDocumentUpload:
    def test_upload_valid_document(self, client: TestClient) -> None:
        mock_result = IngestionResult(
            document_id="doc-test-001",
            chunk_count=5,
            entity_count=3,
            event_msg_id="msg-001",
        )
        with (
            patch("cci_ingestion.api._qdrant", new=AsyncMock()),
            patch("cci_ingestion.api._redis", new=AsyncMock()),
            patch(
                "cci_ingestion.api.run_ingestion_pipeline",
                new=AsyncMock(return_value=mock_result),
            ),
        ):
            response = client.post(
                "/documents",
                files={"file": ("budget_2026.txt", b"Budget 2026: 800.000 EUR", "text/plain")},
                data={"domain": "hera_it", "confidentiality": "internal"},
            )
        assert response.status_code == 201
        body = response.json()
        assert body["document_id"] == "doc-test-001"
        assert body["chunk_count"] == 5
        assert body["status"] == "indexed"

    def test_upload_invalid_domain(self, client: TestClient) -> None:
        with (
            patch("cci_ingestion.api._qdrant", new=AsyncMock()),
            patch("cci_ingestion.api._redis", new=AsyncMock()),
        ):
            response = client.post(
                "/documents",
                files={"file": ("test.txt", b"content", "text/plain")},
                data={"domain": "dominio_inesistente"},
            )
        assert response.status_code == 422

    def test_upload_empty_file(self, client: TestClient) -> None:
        with (
            patch("cci_ingestion.api._qdrant", new=AsyncMock()),
            patch("cci_ingestion.api._redis", new=AsyncMock()),
        ):
            response = client.post(
                "/documents",
                files={"file": ("empty.txt", b"", "text/plain")},
                data={"domain": "hera_it"},
            )
        assert response.status_code == 422

    def test_all_supported_domains_accepted(self, client: TestClient) -> None:
        domains = [
            "hera_it", "aou_clinical", "semsotec_product",
            "ducati_corse", "dallara", "prada",
        ]
        mock_result = IngestionResult(
            document_id="doc-001",
            chunk_count=1,
            entity_count=0,
            event_msg_id="msg-001",
        )
        for domain in domains:
            with (
                patch("cci_ingestion.api._qdrant", new=AsyncMock()),
                patch("cci_ingestion.api._redis", new=AsyncMock()),
                patch(
                    "cci_ingestion.api.run_ingestion_pipeline",
                    new=AsyncMock(return_value=mock_result),
                ),
            ):
                response = client.post(
                    "/documents",
                    files={"file": ("doc.txt", b"contenuto", "text/plain")},
                    data={"domain": domain},
                )
            assert response.status_code == 201, f"Dominio {domain} non accettato"
