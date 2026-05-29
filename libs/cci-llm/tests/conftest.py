"""Fixtures for cci-llm tests — all LLM calls are mocked, no real API."""
from __future__ import annotations

import pytest

from cci_llm.models import LLMResponse, LLMUsage


def make_response(content: str, model: str = "claude-sonnet-4-6") -> LLMResponse:
    return LLMResponse(
        content=content,
        model=model,
        usage=LLMUsage(input_tokens=100, output_tokens=50),
        stop_reason="end_turn",
        request_id="msg_test_001",
    )
