"""Coherence Engine FastAPI application — port 8003.

Endpoints:
  GET  /incoherences       — run domain verification, return violations as Incoherence list
  POST /verify             — full verification (graph + chunk fallback)
  POST /verify/chunks      — chunk-only evaluation (no graph)
  GET  /rules/{domain}     — list ontology rules for a domain
  GET  /health/live        — liveness probe
  GET  /health/ready       — readiness probe
  GET  /health/startup     — startup probe
  GET  /metrics            — Prometheus metrics
"""
from __future__ import annotations

import hashlib
import time
from contextlib import asynccontextmanager
from datetime import date, datetime, timezone
from typing import Any

import httpx
import structlog
import yaml
from fastapi import FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from prometheus_fastapi_instrumentator import Instrumentator
from pydantic import BaseModel, Field

from cci_coherence.config import CoherenceSettings, get_settings
from cci_coherence.db import IncoherenceDB
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


class IncoherenceExplanation(BaseModel):
    """Grounded LLM explanation attached to an incoherence (R3 compliant)."""

    text: str
    citations: list[str]
    grounding_verified: bool = True


class IncoherenceOut(BaseModel):
    """REST projection of a RuleViolation — consumed by the Next.js frontend."""

    id: str
    rule_id: str
    description: str
    severity: str
    impact_eur: float
    evidence_chunks: list[str]
    domain: str
    detected_at: str
    computed_values: dict[str, Any] = Field(default_factory=dict)
    entity_a_type: str | None = None
    entity_a_props: dict[str, Any] = Field(default_factory=dict)
    entity_b_type: str | None = None
    entity_b_props: dict[str, Any] | None = None
    explanation: IncoherenceExplanation | None = None


class ExplainRequest(BaseModel):
    domain: str = Field(..., description="Ontology domain, e.g. 'hera_it'")
    rule_id: str = Field(..., description="Rule ID to generate explanation for")


# ---------------------------------------------------------------------------
# Application lifespan
# ---------------------------------------------------------------------------

_engine: CoherenceEngine | None = None
_settings: CoherenceSettings | None = None
_start_time: float = 0.0
_incoherence_db: IncoherenceDB | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):  # type: ignore[type-arg]
    global _engine, _settings, _start_time, _incoherence_db
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

    if _settings.mongodb_enabled:
        try:
            from motor.motor_asyncio import AsyncIOMotorClient
            motor_client: Any = AsyncIOMotorClient(_settings.mongodb_uri)
            mongo_db = motor_client[_settings.mongodb_database]
            _incoherence_db = IncoherenceDB(mongo_db)
            log.info("coherence_mongodb_connected", database=_settings.mongodb_database)
        except Exception as exc:
            log.warning("coherence_mongodb_unavailable", error=str(exc))

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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

Instrumentator().instrument(app).expose(app)


def _get_engine() -> CoherenceEngine:
    if _engine is None:
        raise HTTPException(status_code=503, detail="Engine not initialised")
    return _engine


async def _compute_incoherences(
    domain: str,
    as_of_date: str | None = None,
) -> list[IncoherenceOut]:
    """Run the rule engine for a domain and return IncoherenceOut list (no explanation)."""
    if _settings is None:
        raise HTTPException(status_code=503, detail="Settings not loaded")

    ontology_path = _settings.ontologies_path / f"{domain}.yaml"
    if not ontology_path.exists():
        raise HTTPException(status_code=404, detail=f"No ontology for domain '{domain}'")

    with ontology_path.open() as fh:
        data = yaml.safe_load(fh)
    rules = data.get("rules", [])
    rules_for_engine = [
        {**r, "rule_id": r["id"]} if "rule_id" not in r else r
        for r in rules
    ]

    chunks: list[dict[str, Any]] = []
    if _settings.fixtures_path:
        fixtures_dir = _settings.fixtures_path / domain
        if fixtures_dir.is_dir():
            for txt_file in sorted(fixtures_dir.glob("*.txt")):
                try:
                    chunks.append({
                        "chunk_id": f"fixture_{txt_file.stem}",
                        "text": txt_file.read_text(encoding="utf-8"),
                    })
                except Exception:
                    pass

    engine = _get_engine()
    result = await engine.verify(
        chunks=chunks,
        domain=domain,
        rules=rules_for_engine,
        as_of_date=as_of_date,
    )

    detected_at = datetime.now(timezone.utc).isoformat()
    incoherences: list[IncoherenceOut] = []
    seen_rule_ids: set[str] = set()

    for v in result.get("violations", []):
        rule_id: str = v.get("rule_violated", v.get("rule_id", "UNKNOWN"))
        sev: str = v.get("severity", "MEDIUM")

        if rule_id in seen_rule_ids:
            continue
        seen_rule_ids.add(rule_id)

        computed = v.get("computed_values", {})
        impact = float(computed.get("delta", computed.get("overrun_eur", 0)) or 0)
        uid = hashlib.sha256(f"{domain}:{rule_id}".encode()).hexdigest()[:16]

        incoherences.append(IncoherenceOut(
            id=uid,
            rule_id=rule_id,
            description=v.get("description", ""),
            severity=sev,
            impact_eur=impact,
            evidence_chunks=v.get("evidence_chunks", []),
            domain=domain,
            detected_at=detected_at,
            computed_values=computed,
            entity_a_type=v.get("entity_a_type"),
            entity_a_props=v.get("entity_a_props") or {},
            entity_b_type=v.get("entity_b_type"),
            entity_b_props=v.get("entity_b_props"),
        ))

    return incoherences


# ---------------------------------------------------------------------------
# Incoherences convenience endpoint (wraps /verify with auto-loaded rules)
# ---------------------------------------------------------------------------


@app.get("/incoherences", response_model=list[IncoherenceOut])
async def list_incoherences(
    domain: str = Query(..., description="Ontology domain, e.g. 'hera_it'"),
    severity: str | None = Query(None, description="Filter by severity level"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    as_of_date: str | None = Query(None, description="ISO date for temporal evaluation"),
) -> list[IncoherenceOut]:
    """Run domain verification and return incoherences (no cached explanation)."""
    all_incoherences = await _compute_incoherences(domain, as_of_date)
    filtered = [i for i in all_incoherences if not severity or i.severity == severity]
    return filtered[offset : offset + limit]


@app.get("/incoherences/{incoherence_id}", response_model=IncoherenceOut)
async def get_incoherence(
    incoherence_id: str,
    domain: str = Query(..., description="Ontology domain, e.g. 'hera_it'"),
    as_of_date: str | None = Query(None),
) -> IncoherenceOut:
    """Return a single incoherence with cached explanation merged in (if available)."""
    incoherences = await _compute_incoherences(domain, as_of_date)
    found = next((i for i in incoherences if i.id == incoherence_id), None)
    if found is None:
        raise HTTPException(status_code=404, detail=f"Incoherence '{incoherence_id}' not found in domain '{domain}'")

    if _incoherence_db is not None:
        cached = await _incoherence_db.get_explanation(incoherence_id)
        if cached:
            found = found.model_copy(
                update={"explanation": IncoherenceExplanation(**cached)}
            )

    return found


@app.post("/incoherences/{incoherence_id}/explain", response_model=IncoherenceExplanation)
async def explain_incoherence(
    incoherence_id: str,
    req: ExplainRequest,
) -> IncoherenceExplanation:
    """Generate or return cached LLM explanation for a single incoherence (R3 enforced)."""
    if _settings is None:
        raise HTTPException(status_code=503, detail="Settings not loaded")

    # Cache hit — return immediately without calling agents
    if _incoherence_db is not None:
        cached = await _incoherence_db.get_explanation(incoherence_id)
        if cached:
            log.info("explanation_cache_hit", incoherence_id=incoherence_id)
            return IncoherenceExplanation(**cached)

    # Cache miss — find the violation + load fixture chunks, then call agents /generate
    # (R1: REST only — no direct import of agents or cci-llm from coherence service)
    incoherences = await _compute_incoherences(req.domain)
    violation = next(
        (
            {
                "rule_violated": i.rule_id,
                "description": i.description,
                "severity": i.severity,
                "evidence_chunks": i.evidence_chunks,
                "computed_values": i.computed_values,
                "entity_a_type": i.entity_a_type,
                "entity_a_props": i.entity_a_props,
                "entity_b_type": i.entity_b_type,
                "entity_b_props": i.entity_b_props,
            }
            for i in incoherences
            if i.id == incoherence_id
        ),
        None,
    )
    if violation is None:
        raise HTTPException(
            status_code=404,
            detail=f"Incoherence '{incoherence_id}' not found in domain '{req.domain}'",
        )

    # Load fixture chunks (same source used by _compute_incoherences)
    chunks: list[dict[str, Any]] = []
    if _settings.fixtures_path:
        fixtures_dir = _settings.fixtures_path / req.domain
        if fixtures_dir.is_dir():
            for txt_file in sorted(fixtures_dir.glob("*.txt")):
                try:
                    chunks.append({
                        "chunk_id": f"fixture_{txt_file.stem}",
                        "text": txt_file.read_text(encoding="utf-8"),
                    })
                except Exception:
                    pass

    agents_url = _settings.agents_service_url
    payload = {
        "domain": req.domain,
        "violation": violation,
        "chunks": chunks,
    }

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(f"{agents_url}/generate", json=payload)
            resp.raise_for_status()
            agents_data = resp.json()
    except httpx.HTTPStatusError as exc:
        log.error("agents_service_error", status=exc.response.status_code, error=str(exc))
        raise HTTPException(status_code=502, detail=f"Agents service error: {exc.response.status_code}") from exc
    except Exception as exc:
        log.error("agents_service_unavailable", error=str(exc))
        raise HTTPException(status_code=503, detail="Agents service unavailable") from exc

    report_text: str = agents_data.get("text", "")
    citations: list[str] = agents_data.get("citations", [])
    grounding_verified: bool = agents_data.get("grounding_verified", False)

    # R3: block non-grounded output
    if not grounding_verified:
        log.error("r3_violation_explain_endpoint", incoherence_id=incoherence_id)
        raise HTTPException(
            status_code=422,
            detail="Explanation failed R3 grounding check — no [source: chunk_id] citations found",
        )

    # Persist to cache
    if _incoherence_db is not None:
        await _incoherence_db.upsert_explanation(
            incoherence_id,
            domain=req.domain,
            rule_id=req.rule_id,
            explanation=report_text,
            citations=citations,
            grounding_verified=grounding_verified,
        )

    return IncoherenceExplanation(
        text=report_text,
        citations=citations,
        grounding_verified=grounding_verified,
    )


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
