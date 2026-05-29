"""Planner node — uses LLM to interpret trigger and select rules.

Input state keys:  trigger, domain, as_of_date
Output state keys: query, rules, plan_context
"""
from __future__ import annotations

import json
import pathlib
from typing import Any

import structlog
from jinja2 import Environment, FileSystemLoader

from cci_llm import LLMClient, LLMMessage
from cci_agents.state import VerificationState

log = structlog.get_logger(__name__)

_FALLBACK_RULES_BY_DOMAIN: dict[str, list[str]] = {
    "hera_it": ["R001", "R002", "R003", "R004"],
}


def _load_prompt(prompts_path: pathlib.Path, template_name: str) -> str:
    env = Environment(loader=FileSystemLoader(str(prompts_path)), autoescape=False)
    return env.get_template(template_name).module.__loader__.get_source(template_name)  # type: ignore[attr-defined]


def _render_prompt(
    prompts_path: pathlib.Path,
    template_name: str,
    **context: Any,
) -> str:
    env = Environment(loader=FileSystemLoader(str(prompts_path)), autoescape=False)
    template = env.get_template(template_name)
    return template.render(**context)


async def planner_node(
    state: VerificationState,
    *,
    llm: LLMClient,
    prompts_path: pathlib.Path,
    available_rules: list[dict[str, Any]],
) -> dict[str, Any]:
    """Analyse trigger → produce retrieval query + rule selection."""
    trigger = state.get("trigger", "")
    domain = state.get("domain", "")
    as_of_date = state.get("as_of_date", "")
    errors: list[str] = list(state.get("errors", []))

    log.info("planner_start", correlation_id=state.get("correlation_id"), domain=domain)

    # Render prompt from Jinja2 template
    try:
        system_prompt = _render_prompt(
            prompts_path,
            "planner.j2",
            domain=domain,
            as_of_date=as_of_date,
            trigger=trigger,
            available_rules=available_rules,
        )
    except Exception as exc:
        log.warning("planner_template_error", error=str(exc))
        system_prompt = (
            f"Sei il Planner CCI. Dominio: {domain}. "
            "Produci un JSON con query, rules e context."
        )

    # LLM call
    try:
        raw = await llm.complete_json(
            system=system_prompt,
            messages=[LLMMessage(role="user", content=f"Trigger: {trigger}")],
            temperature=0.0,
        )
        # Strip markdown code fences if present
        raw = raw.strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1].rsplit("```", 1)[0].strip()

        plan = json.loads(raw)
        query: str = plan.get("query", trigger)
        rule_ids: list[str] = plan.get("rules", [])
        context_note: str = plan.get("context", "")

        # Map rule_ids back to full rule dicts
        rule_map = {r["id"]: r for r in available_rules}
        selected_rules = [
            {"rule_id": rid, "when": rule_map[rid]["when"], "severity": rule_map[rid]["severity"]}
            for rid in rule_ids
            if rid in rule_map
        ]
        if not selected_rules:
            # Fallback: use all rules for the domain
            selected_rules = [
                {"rule_id": r["id"], "when": r["when"], "severity": r["severity"]}
                for r in available_rules
            ]
            log.warning("planner_no_rules_selected_fallback", domain=domain)

    except (json.JSONDecodeError, Exception) as exc:
        log.warning("planner_parse_error", error=str(exc))
        errors.append(f"planner_parse_error: {exc}")
        query = trigger
        selected_rules = [
            {"rule_id": r["id"], "when": r["when"], "severity": r["severity"]}
            for r in available_rules
        ]
        context_note = ""

    log.info(
        "planner_complete",
        correlation_id=state.get("correlation_id"),
        query=query[:80],
        rules_selected=[r["rule_id"] for r in selected_rules],
    )

    return {
        "query": query,
        "rules": selected_rules,
        "plan_context": context_note,
        "errors": errors,
    }
