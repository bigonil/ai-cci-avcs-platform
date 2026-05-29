"""CCI LLM wrapper — Anthropic SDK, citation enforcement, R3 guardrail.

Public API:
    LLMClient      — async Anthropic wrapper (ONLY allowed anthropic import site)
    LLMMessage     — (role, content) message pair
    LLMResponse    — response with usage tracking
    CitationResult — result of R3 citation check
    GroundingError — raised by enforce_citations(strict=True) on R3 violation
    enforce_citations — check/extract [source: chunk_id] citations (R3)
    extract_citations — return all chunk_ids from [source: X] patterns
"""
from cci_llm.citation_guard import (
    GroundingError,
    enforce_citations,
    extract_citations,
)
from cci_llm.client import LLMClient, LLMError
from cci_llm.models import CitationResult, LLMMessage, LLMRequest, LLMResponse, LLMUsage

__all__ = [
    "LLMClient",
    "LLMError",
    "LLMMessage",
    "LLMRequest",
    "LLMResponse",
    "LLMUsage",
    "CitationResult",
    "GroundingError",
    "enforce_citations",
    "extract_citations",
]
