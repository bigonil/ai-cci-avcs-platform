"""Anthropic SDK wrapper — the ONLY file in the codebase allowed to import anthropic.

All LLM calls across CCI/AVCS must go through this client.
Model is read from CCI_LLM_MODEL env var (default: claude-sonnet-4-6).
"""
from __future__ import annotations

import os
import time
from typing import Any

import structlog
from tenacity import (
    AsyncRetrying,
    RetryError,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from cci_llm.models import LLMMessage, LLMRequest, LLMResponse, LLMUsage

log = structlog.get_logger(__name__)

_DEFAULT_MODEL = "claude-sonnet-4-6"
_DEFAULT_MAX_TOKENS = 4096
_DEFAULT_TEMPERATURE = 0.0


class LLMError(RuntimeError):
    """Wraps Anthropic API errors with context."""


class LLMClient:
    """Async Anthropic client — singleton-safe, retry-enabled, usage-tracked.

    Usage:
        client = LLMClient()
        response = await client.complete(
            system="...",
            messages=[LLMMessage(role="user", content="...")]
        )
    """

    def __init__(
        self,
        model: str | None = None,
        max_tokens: int = _DEFAULT_MAX_TOKENS,
        max_retries: int = 3,
        _client: Any | None = None,  # allow injection in tests
    ) -> None:
        self.model = model or os.environ.get("CCI_LLM_MODEL", _DEFAULT_MODEL)
        self.max_tokens = max_tokens
        self._max_retries = max_retries
        if _client is not None:
            self._client = _client
        else:
            from anthropic import AsyncAnthropic  # only import here — CLAUDE.md §6
            self._client = AsyncAnthropic()  # reads ANTHROPIC_API_KEY from env

    async def complete(
        self,
        system: str,
        messages: list[LLMMessage] | list[dict[str, str]],
        temperature: float = _DEFAULT_TEMPERATURE,
        max_tokens: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> LLMResponse:
        """Send a message to the Anthropic API and return the response.

        Retries on transient errors (connection, timeout, overload) with
        exponential backoff. Auth errors and bad requests are not retried.
        """
        from anthropic import APIConnectionError, APIStatusError, InternalServerError, RateLimitError

        # Normalise to list[dict] for the API
        api_messages = [
            {"role": m.role, "content": m.content}
            if isinstance(m, LLMMessage)
            else m
            for m in messages
        ]
        n_tokens = max_tokens or self.max_tokens
        meta = metadata or {}
        t0 = time.monotonic()

        def _should_retry(exc: BaseException) -> bool:
            if isinstance(exc, APIStatusError):
                # Retry on 500, 529 (overload); not on 400, 401, 404
                return exc.status_code in (500, 502, 503, 529)
            return isinstance(exc, (APIConnectionError, RateLimitError))

        try:
            async for attempt in AsyncRetrying(
                stop=stop_after_attempt(self._max_retries),
                wait=wait_exponential(multiplier=1, min=2, max=30),
                retry=retry_if_exception_type((APIConnectionError, InternalServerError, RateLimitError)),
                reraise=True,
            ):
                with attempt:
                    response = await self._client.messages.create(
                        model=self.model,
                        system=system,
                        messages=api_messages,  # type: ignore[arg-type]
                        max_tokens=n_tokens,
                        temperature=temperature,
                    )
        except Exception as exc:
            elapsed = time.monotonic() - t0
            log.error(
                "llm_call_failed",
                model=self.model,
                elapsed_ms=round(elapsed * 1000, 1),
                error=str(exc),
                **meta,
            )
            raise LLMError(f"Anthropic API call failed: {exc}") from exc

        elapsed = time.monotonic() - t0
        content = response.content[0].text if response.content else ""
        usage = LLMUsage(
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
        )

        log.info(
            "llm_call_complete",
            model=self.model,
            stop_reason=response.stop_reason,
            input_tokens=usage.input_tokens,
            output_tokens=usage.output_tokens,
            elapsed_ms=round(elapsed * 1000, 1),
            **meta,
        )

        return LLMResponse(
            content=content,
            model=response.model,
            usage=usage,
            stop_reason=response.stop_reason or "end_turn",
            request_id=response.id,
        )

    async def complete_json(
        self,
        system: str,
        messages: list[LLMMessage] | list[dict[str, str]],
        temperature: float = 0.0,
    ) -> str:
        """Complete and return raw text (caller must parse JSON)."""
        response = await self.complete(
            system=system,
            messages=messages,
            temperature=temperature,
        )
        return response.content
