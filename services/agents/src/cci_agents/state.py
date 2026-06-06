"""LangGraph state definition for the CCI verification pipeline.

The state is a TypedDict that flows through all 5 nodes:
  planner → retriever → verifier → generator → auditor
"""
from __future__ import annotations

from typing import Any, TypedDict


class VerificationState(TypedDict, total=False):
    # ---- Input (set by API layer before graph invocation) ----
    correlation_id: str
    trigger: str          # human-readable description of what to verify
    domain: str           # e.g. "hera_it"
    as_of_date: str       # ISO date, e.g. "2026-03-31"
    rule_ids_filter: list[str] | None  # if set, planner skips LLM and uses these rules directly

    # ---- Set by Planner ----
    query: str            # retrieval query derived from trigger
    rules: list[dict[str, Any]]   # rules selected for this run
    plan_context: str     # planner's reasoning note

    # ---- Set by Retriever ----
    chunks: list[dict[str, Any]]  # retrieved text chunks with chunk_id + text

    # ---- Set by Verifier ----
    violations: list[dict[str, Any]]   # incoherence dicts from coherence engine
    verification_source: str           # "graph" | "chunks"

    # ---- Set by Generator ----
    report_text: str              # Italian narrative with [source: X] citations
    citations: list[str]          # chunk_ids extracted from report
    grounding_verified: bool

    # ---- Set by Auditor ----
    audit_seq: int | None         # sequence number from governance log
    audit_logged: bool

    # ---- Cross-cutting ----
    errors: list[str]
    hitl_required: bool           # R6: human-in-the-loop gate triggered
