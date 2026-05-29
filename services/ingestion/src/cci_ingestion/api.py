"""FastAPI app — ingestion-service.

Endpoints:
  POST /documents          — upload e ingestion asincrona
  GET  /documents/{id}     — stato documento
  GET  /health/live        — liveness
  GET  /health/ready       — readiness (dipendenze attive)
  GET  /health/startup     — startup (modelli caricati)
  GET  /metrics            — Prometheus (prometheus-fastapi-instrumentator)
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Annotated, AsyncGenerator

import redis.asyncio as aioredis
from fastapi import FastAPI, File, Form, HTTPException, UploadFile, status
from fastapi.responses import JSONResponse
from prometheus_fastapi_instrumentator import Instrumentator
from pydantic import BaseModel
from qdrant_client import AsyncQdrantClient

from cci_common.domain import ConfidentialityLevel, HealthStatus
from cci_common.observability import get_logger, setup_telemetry
from cci_ingestion.config import settings
from cci_ingestion.pipeline import run_ingestion_pipeline

logger = get_logger(__name__)

# Stato globale connessioni (inizializzato nel lifespan)
_qdrant: AsyncQdrantClient | None = None
_redis: aioredis.Redis | None = None  # type: ignore[type-arg]


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    global _qdrant, _redis

    setup_telemetry(settings.service_name, settings.version)

    _qdrant = AsyncQdrantClient(
        host=settings.qdrant_host,
        port=settings.qdrant_port,
        api_key=settings.qdrant_api_key or None,
    )
    _redis = aioredis.from_url(settings.redis_url, decode_responses=True)

    logger.info("ingestion_service_started", version=settings.version)
    yield

    await _qdrant.close()
    await _redis.aclose()
    logger.info("ingestion_service_stopped")


app = FastAPI(
    title="CCI/AVCS — Ingestion Service",
    version=settings.version,
    description="Upload documenti, parsing, NER, chunking, embedding e indicizzazione.",
    lifespan=lifespan,
)

Instrumentator().instrument(app).expose(app)


# ---------------------------------------------------------------------------
# Health checks (R7 — 12-Factor)
# ---------------------------------------------------------------------------


@app.get("/health/live", tags=["health"])
async def health_live() -> HealthStatus:
    return HealthStatus(
        status="ok", service=settings.service_name, version=settings.version
    )


@app.get("/health/ready", tags=["health"])
async def health_ready() -> HealthStatus:
    checks: dict[str, str] = {}

    # Qdrant
    try:
        assert _qdrant is not None
        await _qdrant.get_collections()
        checks["qdrant"] = "ok"
    except Exception as e:
        checks["qdrant"] = f"error: {e}"

    # Redis
    try:
        assert _redis is not None
        await _redis.ping()
        checks["redis"] = "ok"
    except Exception as e:
        checks["redis"] = f"error: {e}"

    overall = "ok" if all(v == "ok" for v in checks.values()) else "degraded"
    return HealthStatus(
        status=overall,
        service=settings.service_name,
        version=settings.version,
        checks=checks,
    )


@app.get("/health/startup", tags=["health"])
async def health_startup() -> HealthStatus:
    return HealthStatus(
        status="ok", service=settings.service_name, version=settings.version
    )


# ---------------------------------------------------------------------------
# Document ingestion
# ---------------------------------------------------------------------------


class IngestionResponse(BaseModel):
    document_id: str
    chunk_count: int
    entity_count: int
    event_msg_id: str
    status: str = "indexed"


ALLOWED_CONTENT_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "text/html",
    "message/rfc822",
    "text/plain",
}

SUPPORTED_DOMAINS = {
    "hera_it",
    "aou_clinical",
    "semsotec_product",
    "ducati_corse",
    "dallara",
    "prada",
}


@app.post(
    "/documents",
    response_model=IngestionResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["ingestion"],
    summary="Carica e indicizza un documento",
)
async def upload_document(
    file: Annotated[UploadFile, File(description="PDF, DOCX, XLSX, HTML, EML")],
    domain: Annotated[
        str,
        Form(description=f"Dominio verticale: {', '.join(sorted(SUPPORTED_DOMAINS))}"),
    ],
    confidentiality: Annotated[
        ConfidentialityLevel,
        Form(description="Livello di confidenzialità GDPR"),
    ] = ConfidentialityLevel.INTERNAL,
) -> IngestionResponse:
    if domain not in SUPPORTED_DOMAINS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Dominio '{domain}' non supportato. Validi: {sorted(SUPPORTED_DOMAINS)}",
        )

    assert _qdrant is not None and _redis is not None, "Servizio non pronto"

    content = await file.read()
    if not content:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="File vuoto",
        )

    filename = file.filename or "unknown"

    try:
        result = await run_ingestion_pipeline(
            content=content,
            filename=filename,
            domain=domain,
            confidentiality=confidentiality,
            qdrant=_qdrant,
            redis_client=_redis,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        ) from e

    if result.errors:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=result.errors[0],
        )

    return IngestionResponse(
        document_id=result.document_id,
        chunk_count=result.chunk_count,
        entity_count=result.entity_count,
        event_msg_id=result.event_msg_id,
    )
