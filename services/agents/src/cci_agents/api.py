"""Agents service FastAPI application — port 8004.

Endpoints:
  POST /verify              — run full 5-node pipeline, return report
  GET  /verify/{id}         — poll async verification by correlation_id
  GET  /health/live         — liveness probe
  GET  /health/ready        — readiness probe
  GET  /health/startup      — startup probe
  GET  /metrics             — Prometheus metrics
"""
from __future__ import annotations

import time
import uuid
from contextlib import asynccontextmanager
from datetime import date
from typing import Any

import structlog
import yaml
from fastapi import FastAPI, HTTPException, status
from fastapi.responses import JSONResponse
from prometheus_fastapi_instrumentator import Instrumentator
from pydantic import BaseModel, Field

from cci_agents.config import AgentsSettings, get_settings
from cci_agents.graph import build_graph
from cci_llm import LLMClient

log = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------


class VerifyRequest(BaseModel):
    trigger: str = Field(..., description="Human-readable verification request")
    domain: str = Field(..., description="Ontology domain, e.g. 'hera_it'")
    as_of_date: str | None = Field(default=None, description="ISO date, defaults to today")
    correlation_id: str = Field(default_factory=lambda: str(uuid.uuid4()))


class VerifyResponse(BaseModel):
    correlation_id: str
    domain: str
    as_of_date: str
    trigger: str
    rules_evaluated: list[str]
    violations_found: int
    violations: list[dict[str, Any]]
    report_text: str
    citations: list[str]
    grounding_verified: bool
    hitl_required: bool
    audit_logged: bool
    audit_seq: int | None
    errors: list[str]
    elapsed_ms: float


# ---------------------------------------------------------------------------
# Application state
# ---------------------------------------------------------------------------

_graph: Any = None
_settings: AgentsSettings | None = None
_start_time: float = 0.0
_rules_by_domain: dict[str, list[dict[str, Any]]] = {}


@asynccontextmanager
async def lifespan(app: FastAPI):  # type: ignore[type-arg]
    global _graph, _settings, _start_time, _rules_by_domain
    _start_time = time.time()
    _settings = get_settings()

    # Load ontology rules from YAML files
    _rules_by_domain = _load_ontology_rules(_settings)

    # Build LLM client
    llm = LLMClient(model=_settings.llm_model, max_tokens=_settings.llm_max_tokens)

    # Optional MongoDB checkpointer for LangGraph state persistence
    checkpointer = None
    if _settings.mongodb_checkpoint_enabled:
        try:
            from langgraph.checkpoint.mongodb.aio import AsyncMongoDBSaver  # type: ignore[import]
            checkpointer = AsyncMongoDBSaver.from_conn_string(_settings.mongodb_uri)
            log.info("langgraph_mongodb_checkpointer_enabled")
        except (ImportError, Exception) as exc:
            log.warning("langgraph_checkpointer_unavailable", error=str(exc))

    _graph = build_graph(
        llm=llm,
        prompts_path=_settings.prompts_path,
        retrieval_url=_settings.retrieval_url,
        coherence_url=_settings.coherence_url,
        governance_url=_settings.governance_url,
        available_rules_by_domain=_rules_by_domain,
        hitl_threshold_eur=_settings.hitl_impact_threshold_eur,
        top_k=_settings.retrieval_top_k,
        checkpointer=checkpointer,
    )

    log.info(
        "agents_service_ready",
        model=_settings.llm_model,
        domains=list(_rules_by_domain.keys()),
    )
    yield
    log.info("agents_service_shutdown")


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------

app = FastAPI(
    title="CCI Agents Service",
    description="LangGraph 5-node verification pipeline — planner→retriever→verifier→generator→auditor",
    version="0.1.0",
    lifespan=lifespan,
)

Instrumentator().instrument(app).expose(app)


def _get_graph() -> Any:
    if _graph is None:
        raise HTTPException(status_code=503, detail="Graph not initialised")
    return _graph


# ---------------------------------------------------------------------------
# Verification endpoint
# ---------------------------------------------------------------------------


@app.post("/verify", response_model=VerifyResponse, status_code=status.HTTP_200_OK)
async def verify(req: VerifyRequest) -> VerifyResponse:
    """Run the full 5-node verification pipeline synchronously."""
    graph = _get_graph()
    as_of = req.as_of_date or date.today().isoformat()

    initial_state = {
        "correlation_id": req.correlation_id,
        "trigger": req.trigger,
        "domain": req.domain,
        "as_of_date": as_of,
        "errors": [],
    }

    t0 = time.monotonic()
    try:
        config = {"configurable": {"thread_id": req.correlation_id}}
        final_state = await graph.ainvoke(initial_state, config=config)
    except Exception as exc:
        log.error(
            "graph_invocation_error",
            correlation_id=req.correlation_id,
            error=str(exc),
        )
        raise HTTPException(status_code=500, detail=f"Pipeline error: {exc}") from exc

    elapsed_ms = round((time.monotonic() - t0) * 1000, 1)

    rules = final_state.get("rules", [])
    violations = final_state.get("violations", [])

    log.info(
        "verify_complete",
        correlation_id=req.correlation_id,
        domain=req.domain,
        violations=len(violations),
        elapsed_ms=elapsed_ms,
    )

    return VerifyResponse(
        correlation_id=req.correlation_id,
        domain=req.domain,
        as_of_date=as_of,
        trigger=req.trigger,
        rules_evaluated=[r.get("rule_id", "") for r in rules],
        violations_found=len(violations),
        violations=violations,
        report_text=final_state.get("report_text", ""),
        citations=final_state.get("citations", []),
        grounding_verified=final_state.get("grounding_verified", False),
        hitl_required=final_state.get("hitl_required", False),
        audit_logged=final_state.get("audit_logged", False),
        audit_seq=final_state.get("audit_seq"),
        errors=final_state.get("errors", []),
        elapsed_ms=elapsed_ms,
    )


# ---------------------------------------------------------------------------
# Health probes
# ---------------------------------------------------------------------------


@app.get("/health/live")
async def health_live() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/health/ready")
async def health_ready() -> dict[str, Any]:
    if _graph is None:
        return JSONResponse(status_code=503, content={"status": "not_ready"})
    return {"status": "ok", "graph": "ready", "domains": list(_rules_by_domain.keys())}


@app.get("/health/startup")
async def health_startup() -> dict[str, Any]:
    if _graph is None:
        return JSONResponse(status_code=503, content={"status": "starting"})
    return {"status": "ok", "uptime_seconds": round(time.time() - _start_time, 2)}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _load_ontology_rules(
    settings: AgentsSettings,
) -> dict[str, list[dict[str, Any]]]:
    """Load rules from all domain YAML ontology files."""
    from pathlib import Path

    # Try ontologies path relative to prompts path parent, then common locations
    candidates = [
        settings.prompts_path.parent.parent / "docs" / "ontologies",
        Path("/app/ontologies"),
        Path("docs/ontologies"),
    ]

    rules_by_domain: dict[str, list[dict[str, Any]]] = {}
    for ontologies_dir in candidates:
        if not ontologies_dir.exists():
            continue
        for yaml_file in ontologies_dir.glob("*.yaml"):
            try:
                with yaml_file.open() as fh:
                    data = yaml.safe_load(fh)
                domain = data.get("domain", yaml_file.stem)
                rules = data.get("rules", [])
                rules_by_domain[domain] = rules
                log.info("ontology_loaded", domain=domain, rules=len(rules))
            except Exception as exc:
                log.warning("ontology_load_error", file=str(yaml_file), error=str(exc))
        if rules_by_domain:
            break

    if not rules_by_domain:
        log.warning("no_ontologies_found", candidates=[str(c) for c in candidates])
    return rules_by_domain
