"""Coherence Engine FastAPI application — port 8003.

Endpoints:
  POST /verify            — full verification (graph + chunk fallback)
  POST /verify/chunks     — chunk-only evaluation (no graph)
  GET  /rules/{domain}    — list ontology rules for a domain
  GET  /health/live       — liveness probe
  GET  /health/ready      — readiness probe
  GET  /health/startup    — startup probe
  GET  /metrics           — Prometheus metrics
"""
from __future__ import annotations

import time
from contextlib import asynccontextmanager
from datetime import date
from typing import Any

import structlog
import yaml
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.responses import JSONResponse
from prometheus_fastapi_instrumentator import Instrumentator
from pydantic import BaseModel, Field

from cci_coherence.config import CoherenceSettings, get_settings
from cci_coherence.rule_engine import CoherenceEngine

log = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------


class VerifyRequest(BaseModel):
    domain: str = Field(..., description="Ontology domain, e.g. 'hera_it'")
    chunks: list[dict[str, Any]] = Field(default_factory=list)
    rules: list[dict[str, Any]] = Field(
        ...,
        description="List of {rule_id, when, severity} dicts from the ontology",
    )
    as_of_date: str | None = Field(
        default=None,
        description="ISO date for temporal evaluation; defaults to today",
    )


class VerifyChunksRequest(BaseModel):
    domain: str
    chunks: list[dict[str, Any]]
    rules: list[dict[str, Any]]
    as_of_date: str | None = None


class VerifyResponse(BaseModel):
    domain: str
    as_of_date: str
    evaluation_source: str
    rules_evaluated: int
    incoherences_found: int
    violations: list[dict[str, Any]]


# ---------------------------------------------------------------------------
# Application lifespan
# ---------------------------------------------------------------------------

_engine: CoherenceEngine | None = None
_settings: CoherenceSettings | None = None
_start_time: float = 0.0


@asynccontextmanager
async def lifespan(app: FastAPI):  # type: ignore[type-arg]
    global _engine, _settings, _start_time
    _start_time = time.time()
    _settings = get_settings()

    neo4j_driver = None
    if _settings.neo4j_enabled:
        try:
            from neo4j import AsyncGraphDatabase
            neo4j_driver = AsyncGraphDatabase.driver(
                _settings.neo4j_uri,
                auth=(_settings.neo4j_user, _settings.neo4j_password),
            )
            await neo4j_driver.verify_connectivity()
            log.info("neo4j_connected", uri=_settings.neo4j_uri)
        except Exception as exc:
            log.warning("neo4j_unavailable", error=str(exc))
            neo4j_driver = None

    _engine = CoherenceEngine(settings=_settings, neo4j_driver=neo4j_driver)
    log.info("coherence_engine_ready", domain_support=["hera_it"])

    yield

    if neo4j_driver:
        await neo4j_driver.close()
    log.info("coherence_engine_shutdown")


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------

app = FastAPI(
    title="CCI Coherence Engine",
    description="Deterministic rule evaluation engine — R4 zero-LLM enforced",
    version="0.1.0",
    lifespan=lifespan,
)

Instrumentator().instrument(app).expose(app)


def _get_engine() -> CoherenceEngine:
    if _engine is None:
        raise HTTPException(status_code=503, detail="Engine not initialised")
    return _engine


# ---------------------------------------------------------------------------
# Verification endpoints
# ---------------------------------------------------------------------------


@app.post("/verify", response_model=VerifyResponse, status_code=status.HTTP_200_OK)
async def verify(req: VerifyRequest) -> VerifyResponse:
    """Full verification: graph-first with chunk fallback."""
    engine = _get_engine()
    result = await engine.verify(
        chunks=req.chunks,
        domain=req.domain,
        rules=req.rules,
        as_of_date=req.as_of_date,
    )
    return VerifyResponse(**result)


@app.post("/verify/chunks", response_model=VerifyResponse, status_code=status.HTTP_200_OK)
async def verify_chunks(req: VerifyChunksRequest) -> VerifyResponse:
    """Chunk-only verification (no graph lookup)."""
    engine = _get_engine()
    violations = await engine.verify_chunks(
        chunks=req.chunks,
        domain=req.domain,
        rules=req.rules,
        as_of_date=req.as_of_date,
    )
    as_of = req.as_of_date or date.today().isoformat()
    return VerifyResponse(
        domain=req.domain,
        as_of_date=as_of,
        evaluation_source="chunks",
        rules_evaluated=len(req.rules),
        incoherences_found=len(violations),
        violations=violations,
    )


# ---------------------------------------------------------------------------
# Ontology / rules endpoints
# ---------------------------------------------------------------------------


@app.get("/rules/{domain}")
async def get_rules(domain: str) -> dict[str, Any]:
    """Return the rule list for a domain from the loaded ontology YAML."""
    if _settings is None:
        raise HTTPException(status_code=503, detail="Settings not loaded")
    ontology_path = _settings.ontologies_path / f"{domain}.yaml"
    if not ontology_path.exists():
        raise HTTPException(status_code=404, detail=f"No ontology for domain '{domain}'")
    with ontology_path.open() as fh:
        data = yaml.safe_load(fh)
    rules = data.get("rules", [])
    return {"domain": domain, "rules": rules, "count": len(rules)}


# ---------------------------------------------------------------------------
# Health probes
# ---------------------------------------------------------------------------


@app.get("/health/live")
async def health_live() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/health/ready")
async def health_ready() -> dict[str, Any]:
    if _engine is None:
        return JSONResponse(status_code=503, content={"status": "not_ready"})
    return {"status": "ok", "engine": "ready"}


@app.get("/health/startup")
async def health_startup() -> dict[str, Any]:
    if _engine is None:
        return JSONResponse(status_code=503, content={"status": "starting"})
    uptime = round(time.time() - _start_time, 2)
    return {"status": "ok", "uptime_seconds": uptime}
