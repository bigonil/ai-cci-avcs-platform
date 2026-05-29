"""Data models for the CCI LLM wrapper — shared types between client and citation guard."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class LLMMessage:
    role: str  # "user" | "assistant"
    content: str


@dataclass
class LLMRequest:
    system: str
    messages: list[LLMMessage]
    temperature: float = 0.0
    max_tokens: int = 4096
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class LLMUsage:
    input_tokens: int
    output_tokens: int

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens


@dataclass
class LLMResponse:
    content: str
    model: str
    usage: LLMUsage
    stop_reason: str
    request_id: str = ""

    def is_complete(self) -> bool:
        return self.stop_reason == "end_turn"


@dataclass
class CitationResult:
    """Result of citation enforcement on an LLM response."""
    text: str
    citations_found: list[str]  # chunk_ids extracted from [source: X] patterns
    sentences_without_citations: list[str]
    is_grounded: bool

    @property
    def citation_count(self) -> int:
        return len(self.citations_found)
