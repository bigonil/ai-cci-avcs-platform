"""Knowledge Service FastAPI application.

Endpoints:
  GET  /health/live
  GET  /health/ready
  GET  /health/startup
  GET  /metrics          (Prometheus)
  GET  /docs             (OpenAPI 3.1)
  GET  /ontologies                    — list all loaded ontologies
  GET  /ontologies/{domain}           — single ontology detail
  GET  /entities/{domain}             — query entities from temporal KG
  DELETE /documents/{doc_id}          — GDPR erasure (soft-delete + vector purge)
  POST /query/vector                  — semantic search in Qdrant
  POST /query/temporal                — read-only Cypher on Neo4j
"""
from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from typing import Any

import structlog
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from prometheus_fastapi_instrumentator import Instrumentator
from pydantic import BaseModel, Field

from cci_common.domain import HealthStatus

from cci_knowledge.config import KnowledgeSettings, get_settings
from cci_knowledge.event_consumer import DocumentIndexedConsumer
from cci_knowledge.ontology_loader import OntologyLoader
from cci_knowledge.temporal_graph import TemporalGraph
from cci_knowledge.timeseries import TimeSeriesStore
from cci_knowledge.vector_store import QdrantVectorStore

log = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------


class VectorQueryRequest(BaseModel):
    domain: str
    vector: list[float]
    limit: int = Field(default=10, ge=1, le=100)
    filter_payload: dict[str, Any] | None = None


class TemporalQueryRequest(BaseModel):
    cypher: str
    params: dict[str, Any] | None = None


class VectorQueryResponse(BaseModel):
    results: list[dict[str, Any]]
    domain: str
    count: int


class TemporalQueryResponse(BaseModel):
    records: list[dict[str, Any]]
    count: int


class EntitiesResponse(BaseModel):
    domain: str
    entities: list[dict[str, Any]]
    count: int
    as_of: str


class DeleteResponse(BaseModel):
    doc_id: str
    vectors_deleted: int
    entities_soft_deleted: int


# ---------------------------------------------------------------------------
# App state holder (populated in lifespan)
# ---------------------------------------------------------------------------


class _AppState:
    settings: KnowledgeSettings
    ontology_loader: OntologyLoader
    graph: TemporalGraph
    vector_store: QdrantVectorStore
    timeseries: TimeSeriesStore
    consumer: DocumentIndexedConsumer
    consumer_task: asyncio.Task[None] | None = None
    ready: bool = False


_state = _AppState()


@asynccontextmanager
async def lifespan(app: FastAPI):  # type: ignore[type-arg]
    cfg = get_settings()
    _state.settings = cfg

    _state.ontology_loader = OntologyLoader(cfg.ontologies_path)
    _state.ontology_loader.load_all()

    _state.graph = TemporalGraph(
        uri=cfg.neo4j_uri,
        user=cfg.neo4j_user,
        password=cfg.neo4j_password,
        database=cfg.neo4j_database,
    )
    await _state.graph.bootstrap_indexes()

    _state.vector_store = QdrantVectorStore(
        host=cfg.qdrant_host,
        port=cfg.qdrant_port,
        api_key=cfg.qdrant_api_key,
        embedding_dim=cfg.embedding_dim,
    )

    _state.timeseries = TimeSeriesStore(
        mongodb_uri=cfg.mongodb_uri,
        db_name=cfg.mongodb_operational_db,
    )

    _state.consumer = DocumentIndexedConsumer(
        redis_url=cfg.redis_url,
        stream=cfg.redis_stream,
        group=cfg.redis_consumer_group,
        consumer_name=cfg.redis_consumer_name,
        graph=_state.graph,
        vector_store=_state.vector_store,
    )
    _state.consumer_task = asyncio.create_task(_state.consumer.start())
    _state.ready = True
    log.info("knowledge_service_started", port=cfg.port)

    yield

    _state.ready = False
    await _state.consumer.stop()
    if _state.consumer_task:
        _state.consumer_task.cancel()
    await _state.graph.close()
    await _state.vector_store.close()
    await _state.timeseries.close()
    log.info("knowledge_service_stopped")


# ---------------------------------------------------------------------------
# Application
# ---------------------------------------------------------------------------


def create_app() -> FastAPI:
    app = FastAPI(
        title="CCI Knowledge Service",
        version="0.1.0",
        description="Temporal knowledge graph + vector store service for CCI/AVCS",
        lifespan=lifespan,
        openapi_url="/openapi.json",
        docs_url="/docs",
    )
    Instrumentator().instrument(app).expose(app)
    return app


app = create_app()


# ---------------------------------------------------------------------------
# Health endpoints
# ---------------------------------------------------------------------------


@app.get("/health/live", response_model=HealthStatus, tags=["health"])
async def live() -> HealthStatus:
    return HealthStatus(
        status="ok",
        service=_state.settings.service_name if hasattr(_state, "settings") else "cci-knowledge",
        version=_state.settings.version if hasattr(_state, "settings") else "0.1.0",
    )


@app.get("/health/ready", response_model=HealthStatus, tags=["health"])
async def ready() -> HealthStatus:
    if not _state.ready:
        raise HTTPException(status_code=503, detail="Service not ready")
    return HealthStatus(
        status="ok",
        service=_state.settings.service_name,
        version=_state.settings.version,
        checks={"neo4j": "ok", "qdrant": "ok", "redis": "ok"},
    )


@app.get("/health/startup", response_model=HealthStatus, tags=["health"])
async def startup() -> HealthStatus:
    return await ready()


# ---------------------------------------------------------------------------
# Ontology endpoints
# ---------------------------------------------------------------------------


@app.get("/ontologies", tags=["ontologies"])
async def list_ontologies() -> dict[str, Any]:
    domains = _state.ontology_loader.all_domains()
    return {"domains": domains, "count": len(domains)}


@app.get("/ontologies/{domain}", tags=["ontologies"])
async def get_ontology(domain: str) -> dict[str, Any]:
    ont = _state.ontology_loader.get(domain)
    if ont is None:
        raise HTTPException(status_code=404, detail=f"Ontology '{domain}' not found")
    return ont.model_dump()


# ---------------------------------------------------------------------------
# Entity endpoints
# ---------------------------------------------------------------------------


@app.get("/entities/{domain}", response_model=EntitiesResponse, tags=["knowledge"])
async def get_entities(
    domain: str,
    entity_type: str | None = Query(default=None),
    as_of: str | None = Query(default=None, description="ISO date YYYY-MM-DD"),
    limit: int = Query(default=50, ge=1, le=500),
) -> EntitiesResponse:
    from datetime import date
    as_of_date = as_of or date.today().isoformat()
    entities = await _state.graph.get_entities(
        domain=domain,
        entity_type=entity_type,
        as_of_date=as_of_date,
        limit=limit,
    )
    return EntitiesResponse(
        domain=domain,
        entities=entities,
        count=len(entities),
        as_of=as_of_date,
    )


# ---------------------------------------------------------------------------
# GDPR erasure
# ---------------------------------------------------------------------------


@app.delete("/documents/{doc_id}", response_model=DeleteResponse, tags=["knowledge"])
async def delete_document(doc_id: str) -> DeleteResponse:
    """GDPR erasure: soft-deletes KG entities, hard-deletes vectors for this document."""
    vectors_deleted = await _state.vector_store.delete_by_doc_id(
        domain="all", doc_id=doc_id
    )
    entities_soft_deleted = await _state.graph.delete_entity_by_doc_id(doc_id)
    await _state.timeseries.record(
        "gdpr_erasure",
        value=1.0,
        meta={"doc_id": doc_id},
    )
    return DeleteResponse(
        doc_id=doc_id,
        vectors_deleted=vectors_deleted,
        entities_soft_deleted=entities_soft_deleted,
    )


# ---------------------------------------------------------------------------
# Query endpoints
# ---------------------------------------------------------------------------


@app.post("/query/vector", response_model=VectorQueryResponse, tags=["query"])
async def query_vector(req: VectorQueryRequest) -> VectorQueryResponse:
    await _state.vector_store.ensure_collection(req.domain)
    results = await _state.vector_store.search(
        domain=req.domain,
        query_vector=req.vector,
        limit=req.limit,
        filter_payload=req.filter_payload,
    )
    await _state.timeseries.record("vector_query", 1.0, meta={"domain": req.domain})
    return VectorQueryResponse(results=results, domain=req.domain, count=len(results))


@app.post("/query/temporal", response_model=TemporalQueryResponse, tags=["query"])
async def query_temporal(req: TemporalQueryRequest) -> TemporalQueryResponse:
    try:
        records = await _state.graph.run_readonly_query(req.cypher, req.params)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await _state.timeseries.record("temporal_query", 1.0)
    return TemporalQueryResponse(records=records, count=len(records))


# ---------------------------------------------------------------------------
# Exception handler
# ---------------------------------------------------------------------------


@app.exception_handler(Exception)
async def generic_handler(request: Request, exc: Exception) -> JSONResponse:
    log.exception("unhandled_error", path=request.url.path)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})
