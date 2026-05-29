"""Retrieval Service FastAPI application.

Endpoints:
  GET  /health/live|ready|startup
  GET  /metrics                       Prometheus
  POST /search                        Hybrid (dense+BM25+RRF+rerank)
  POST /search/vector                 Dense-only
  POST /search/bm25                   BM25-only (over dense candidate pool)
  POST /citations/validate            Citation enforcer
  DELETE /cache/{domain}              Invalidate Redis cache for a domain
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any

import structlog
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from prometheus_fastapi_instrumentator import Instrumentator
from pydantic import BaseModel, Field

from cci_common.domain import HealthStatus

from cci_retrieval.cache import RetrievalCache
from cci_retrieval.citation_enforcer import CitationResult, check_citations
from cci_retrieval.config import RetrievalSettings, get_settings
from cci_retrieval.hybrid_retriever import HybridRetriever

log = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=2000)
    domain: str
    top_k: int = Field(default=10, ge=1, le=100)
    filter_payload: dict[str, Any] | None = None
    as_of_date: str | None = None
    rerank: bool = True
    use_cache: bool = True


class SearchResponse(BaseModel):
    query: str
    domain: str
    results: list[dict[str, Any]]
    count: int
    from_cache: bool = False


class CitationValidateRequest(BaseModel):
    text: str
    citation_pattern: str | None = None
    min_sentence_length: int = 40


class CitationValidateResponse(BaseModel):
    valid: bool
    coverage: float
    total_checked: int
    uncited_sentences: list[str]
    checked_at: str


class CacheInvalidateResponse(BaseModel):
    domain: str
    deleted: int


# ---------------------------------------------------------------------------
# App state
# ---------------------------------------------------------------------------


class _AppState:
    settings: RetrievalSettings
    retriever: HybridRetriever
    cache: RetrievalCache
    ready: bool = False


_state = _AppState()


@asynccontextmanager
async def lifespan(app: FastAPI):  # type: ignore[type-arg]
    cfg = get_settings()
    _state.settings = cfg
    _state.retriever = HybridRetriever(cfg)
    _state.cache = RetrievalCache(cfg.redis_url, cfg.cache_ttl_seconds)
    _state.ready = True
    log.info("retrieval_service_started", port=cfg.port)

    yield

    _state.ready = False
    await _state.retriever.close()
    await _state.cache.close()
    log.info("retrieval_service_stopped")


# ---------------------------------------------------------------------------
# Application
# ---------------------------------------------------------------------------


def create_app() -> FastAPI:
    app = FastAPI(
        title="CCI Retrieval Service",
        version="0.1.0",
        description="Hybrid retrieval (dense+BM25+RRF), reranking, citation enforcement",
        lifespan=lifespan,
        openapi_url="/openapi.json",
        docs_url="/docs",
    )
    Instrumentator().instrument(app).expose(app)
    return app


app = create_app()


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------


@app.get("/health/live", response_model=HealthStatus, tags=["health"])
async def live() -> HealthStatus:
    cfg = _state.settings if hasattr(_state, "settings") else None
    return HealthStatus(
        status="ok",
        service=cfg.service_name if cfg else "cci-retrieval",
        version=cfg.version if cfg else "0.1.0",
    )


@app.get("/health/ready", response_model=HealthStatus, tags=["health"])
async def ready() -> HealthStatus:
    if not _state.ready:
        raise HTTPException(status_code=503, detail="Service not ready")
    return HealthStatus(
        status="ok",
        service=_state.settings.service_name,
        version=_state.settings.version,
        checks={"qdrant": "ok", "redis": "ok"},
    )


@app.get("/health/startup", response_model=HealthStatus, tags=["health"])
async def startup_check() -> HealthStatus:
    return await ready()


# ---------------------------------------------------------------------------
# Search endpoints
# ---------------------------------------------------------------------------


@app.post("/search", response_model=SearchResponse, tags=["retrieval"])
async def hybrid_search(req: SearchRequest) -> SearchResponse:
    from_cache = False
    if req.use_cache:
        cached = await _state.cache.get(
            req.query, req.domain, req.as_of_date, req.filter_payload
        )
        if cached is not None:
            return SearchResponse(
                query=req.query,
                domain=req.domain,
                results=cached,
                count=len(cached),
                from_cache=True,
            )

    results = await _state.retriever.search(
        query=req.query,
        domain=req.domain,
        top_k=req.top_k,
        filter_payload=req.filter_payload,
        as_of_date=req.as_of_date,
        rerank_enabled=req.rerank,
    )

    if req.use_cache:
        await _state.cache.set(
            req.query, req.domain, results, req.as_of_date, req.filter_payload
        )

    return SearchResponse(
        query=req.query,
        domain=req.domain,
        results=results,
        count=len(results),
        from_cache=from_cache,
    )


@app.post("/search/vector", response_model=SearchResponse, tags=["retrieval"])
async def vector_search(req: SearchRequest) -> SearchResponse:
    results = await _state.retriever.dense_only(
        query=req.query,
        domain=req.domain,
        top_k=req.top_k,
        filter_payload=req.filter_payload,
    )
    return SearchResponse(
        query=req.query, domain=req.domain, results=results, count=len(results)
    )


@app.post("/search/bm25", response_model=SearchResponse, tags=["retrieval"])
async def bm25_search(req: SearchRequest) -> SearchResponse:
    results = await _state.retriever.bm25_only(
        query=req.query,
        domain=req.domain,
        top_k=req.top_k,
        filter_payload=req.filter_payload,
    )
    return SearchResponse(
        query=req.query, domain=req.domain, results=results, count=len(results)
    )


# ---------------------------------------------------------------------------
# Citation enforcer
# ---------------------------------------------------------------------------


@app.post("/citations/validate", response_model=CitationValidateResponse, tags=["grounding"])
async def validate_citations(req: CitationValidateRequest) -> CitationValidateResponse:
    """R3 guardrail — validate citation coverage of an LLM output text."""
    cfg = _state.settings
    pattern = req.citation_pattern or cfg.citation_pattern
    result: CitationResult = check_citations(
        text=req.text,
        citation_pattern=pattern,
        min_sentence_length=req.min_sentence_length,
    )
    return CitationValidateResponse(
        valid=result.valid,
        coverage=result.coverage,
        total_checked=result.total_checked,
        uncited_sentences=result.uncited_sentences,
        checked_at=result.checked_at.isoformat(),
    )


# ---------------------------------------------------------------------------
# Cache management
# ---------------------------------------------------------------------------


@app.delete("/cache/{domain}", response_model=CacheInvalidateResponse, tags=["cache"])
async def invalidate_cache(domain: str) -> CacheInvalidateResponse:
    deleted = await _state.cache.invalidate(domain)
    return CacheInvalidateResponse(domain=domain, deleted=deleted)


# ---------------------------------------------------------------------------
# Exception handler
# ---------------------------------------------------------------------------


@app.exception_handler(Exception)
async def generic_handler(request: Request, exc: Exception) -> JSONResponse:
    log.exception("unhandled_error", path=request.url.path)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})
