"""LangGraph StateGraph — builds the 5-node verification pipeline.

Flow: planner → retriever → verifier → generator → auditor → END

All node functions are wrapped with functools.partial to inject
their dependencies (llm client, service URLs, paths) at build time.
"""
from __future__ import annotations

import functools
import pathlib
from typing import Any

import structlog
from langgraph.graph import END, StateGraph

from cci_llm import LLMClient
from cci_agents.nodes.auditor import auditor_node
from cci_agents.nodes.generator import generator_node
from cci_agents.nodes.planner import planner_node
from cci_agents.nodes.retriever import retriever_node
from cci_agents.nodes.verifier import verifier_node
from cci_agents.state import VerificationState

log = structlog.get_logger(__name__)


def build_graph(
    llm: LLMClient,
    prompts_path: pathlib.Path,
    retrieval_url: str,
    coherence_url: str,
    governance_url: str,
    available_rules_by_domain: dict[str, list[dict[str, Any]]],
    hitl_threshold_eur: float = 50_000.0,
    top_k: int = 20,
    checkpointer: Any = None,
) -> Any:
    """Build and compile the LangGraph verification pipeline.

    Returns a compiled graph ready for `.ainvoke()` or `.astream()`.
    """
    workflow = StateGraph(VerificationState)

    # Each node is a partial that captures its dependencies at build time.
    # The state dict is the only runtime argument.
    workflow.add_node(
        "planner",
        functools.partial(
            _planner_dispatch,
            llm=llm,
            prompts_path=prompts_path,
            rules_by_domain=available_rules_by_domain,
        ),
    )
    workflow.add_node(
        "retriever",
        functools.partial(retriever_node, retrieval_url=retrieval_url, top_k=top_k),
    )
    workflow.add_node(
        "verifier",
        functools.partial(verifier_node, coherence_url=coherence_url),
    )
    workflow.add_node(
        "generator",
        functools.partial(
            generator_node,
            llm=llm,
            prompts_path=prompts_path,
            hitl_threshold_eur=hitl_threshold_eur,
        ),
    )
    workflow.add_node(
        "auditor",
        functools.partial(auditor_node, governance_url=governance_url),
    )

    # Linear pipeline
    workflow.set_entry_point("planner")
    workflow.add_edge("planner", "retriever")
    workflow.add_edge("retriever", "verifier")
    workflow.add_edge("verifier", "generator")
    workflow.add_edge("generator", "auditor")
    workflow.add_edge("auditor", END)

    compile_kwargs: dict[str, Any] = {}
    if checkpointer is not None:
        compile_kwargs["checkpointer"] = checkpointer

    return workflow.compile(**compile_kwargs)


async def _planner_dispatch(
    state: VerificationState,
    *,
    llm: LLMClient,
    prompts_path: pathlib.Path,
    rules_by_domain: dict[str, list[dict[str, Any]]],
) -> dict[str, Any]:
    """Resolve domain-specific rules then call the planner node."""
    domain = state.get("domain", "")
    available_rules = rules_by_domain.get(domain, [])
    return await planner_node(
        state,
        llm=llm,
        prompts_path=prompts_path,
        available_rules=available_rules,
    )
