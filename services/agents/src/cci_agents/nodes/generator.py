"""Generator node — LLM call with mandatory citation enforcement (R3).

Input state keys:  chunks, violations, trigger, domain, as_of_date
Output state keys: report_text, citations, grounding_verified
"""
from __future__ import annotations

import pathlib
from typing import Any

import structlog
from jinja2 import Environment, FileSystemLoader

from cci_llm import LLMClient, LLMMessage, enforce_citations, extract_citations
from cci_llm.citation_guard import GroundingError
from cci_agents.state import VerificationState

log = structlog.get_logger(__name__)

_FALLBACK_SYSTEM = (
    "Sei un analista di coerenza finanziaria CCI/AVCS. "
    "Produci un report in italiano con citazioni [source: chunk_id] obbligatorie."
)


def _render_generator_prompt(
    prompts_path: pathlib.Path,
    domain: str,
    as_of_date: str,
    trigger: str,
    violations: list[dict[str, Any]],
    chunks: list[dict[str, Any]],
) -> str:
    try:
        env = Environment(loader=FileSystemLoader(str(prompts_path)), autoescape=False)
        template = env.get_template("generator.j2")
        return template.render(
            domain=domain,
            as_of_date=as_of_date,
            trigger=trigger,
            violations=violations,
            chunks=chunks,
        )
    except Exception as exc:
        log.warning("generator_template_error", error=str(exc))
        return _FALLBACK_SYSTEM


async def generator_node(
    state: VerificationState,
    *,
    llm: LLMClient,
    prompts_path: pathlib.Path,
    hitl_threshold_eur: float = 50_000.0,
) -> dict[str, Any]:
    """Generate a grounded Italian narrative explaining all violations (R3)."""
    chunks = state.get("chunks", [])
    violations = state.get("violations", [])
    domain = state.get("domain", "")
    as_of_date = state.get("as_of_date", "")
    trigger = state.get("trigger", "")
    errors: list[str] = list(state.get("errors", []))

    log.info(
        "generator_start",
        correlation_id=state.get("correlation_id"),
        violations=len(violations),
        chunks=len(chunks),
    )

    # Short-circuit when there's nothing to report
    if not violations and not chunks:
        report = "Nessuna incoerenza rilevata per il dominio e il periodo specificati."
        return {
            "report_text": report,
            "citations": [],
            "grounding_verified": True,
            "hitl_required": False,
            "errors": errors,
        }

    system_prompt = _render_generator_prompt(
        prompts_path=prompts_path,
        domain=domain,
        as_of_date=as_of_date,
        trigger=trigger,
        violations=violations,
        chunks=chunks[:15],  # limit context window usage
    )

    try:
        response = await llm.complete(
            system=system_prompt,
            messages=[
                LLMMessage(
                    role="user",
                    content=(
                        f"Produci il report di coerenza per {domain} al {as_of_date}. "
                        f"Trigger: {trigger}"
                    ),
                )
            ],
            temperature=0.0,
        )
        report_text = response.content

    except Exception as exc:
        log.error("generator_llm_error", error=str(exc))
        errors.append(f"generator_llm_error: {exc}")
        # Produce a deterministic fallback report (no hallucinations)
        report_text = _build_fallback_report(violations)

    # R3 citation enforcement — strict mode always on in production
    grounding_verified = False
    citations: list[str] = []
    try:
        result = enforce_citations(report_text, strict=True)
        citations = result.citations_found
        grounding_verified = result.is_grounded
    except GroundingError as exc:
        log.error(
            "r3_violation_generator",
            correlation_id=state.get("correlation_id"),
            error=str(exc),
        )
        errors.append(f"r3_grounding_error: {exc}")
        # Append citations extracted anyway (non-strict fallback)
        citations = extract_citations(report_text)
        grounding_verified = False

    # R6: HITL gate — check if any violation exceeds the threshold
    hitl_required = _check_hitl(violations, hitl_threshold_eur)

    log.info(
        "generator_complete",
        correlation_id=state.get("correlation_id"),
        report_length=len(report_text),
        citations=len(citations),
        grounding_verified=grounding_verified,
        hitl_required=hitl_required,
    )

    return {
        "report_text": report_text,
        "citations": citations,
        "grounding_verified": grounding_verified,
        "hitl_required": hitl_required,
        "errors": errors,
    }


def _build_fallback_report(violations: list[dict[str, Any]]) -> str:
    """Deterministic fallback when LLM is unavailable — no fabricated claims."""
    if not violations:
        return "Nessuna incoerenza rilevata."
    lines = ["Report di coerenza (fallback deterministico — LLM non disponibile):\n"]
    for v in violations:
        chunk_refs = " ".join(f"[source: {c}]" for c in v.get("evidence_chunks", []))
        lines.append(
            f"- Regola {v.get('rule_violated')}: {v.get('description')} "
            f"{chunk_refs}"
        )
    return "\n".join(lines)


def _check_hitl(violations: list[dict[str, Any]], threshold: float) -> bool:
    """R6: return True if any computed delta exceeds the HITL threshold."""
    for v in violations:
        computed = v.get("computed_values", {})
        delta = computed.get("delta", 0.0)
        if isinstance(delta, (int, float)) and delta >= threshold:
            return True
    return False
