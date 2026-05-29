"""Tests for LLMClient — all Anthropic calls are mocked."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from cci_llm.client import LLMClient, LLMError
from cci_llm.models import LLMMessage, LLMUsage


def _make_anthropic_response(text: str, model: str = "claude-sonnet-4-6") -> MagicMock:
    resp = MagicMock()
    resp.content = [MagicMock(text=text)]
    resp.model = model
    resp.usage = MagicMock(input_tokens=100, output_tokens=50)
    resp.stop_reason = "end_turn"
    resp.id = "msg_mock_001"
    return resp


def _make_injected_client(response_text: str, model: str = "claude-sonnet-4-6") -> tuple:
    """Return (LLMClient, mock_api) with injected stub — no real API calls."""
    mock_api = MagicMock()
    mock_api.messages = MagicMock()
    mock_api.messages.create = AsyncMock(
        return_value=_make_anthropic_response(response_text, model)
    )
    client = LLMClient(model=model, _client=mock_api)
    return client, mock_api


class TestLLMClientComplete:
    @pytest.mark.asyncio
    async def test_returns_content(self):
        client, _ = _make_injected_client("Hello from CCI")
        response = await client.complete(
            system="You are a test assistant.",
            messages=[LLMMessage(role="user", content="Hi")],
        )
        assert response.content == "Hello from CCI"
        assert response.model == "claude-sonnet-4-6"

    @pytest.mark.asyncio
    async def test_usage_tracked(self):
        client, _ = _make_injected_client("result")
        response = await client.complete(
            system="sys", messages=[{"role": "user", "content": "msg"}]
        )
        assert response.usage.input_tokens == 100
        assert response.usage.output_tokens == 50
        assert response.usage.total_tokens == 150

    @pytest.mark.asyncio
    async def test_dict_messages_accepted(self):
        client, _ = _make_injected_client("ok")
        response = await client.complete(
            system="sys",
            messages=[{"role": "user", "content": "test"}],
        )
        assert response.content == "ok"

    @pytest.mark.asyncio
    async def test_stop_reason_captured(self):
        client, _ = _make_injected_client("hi")
        response = await client.complete(system="s", messages=[{"role": "user", "content": "q"}])
        assert response.is_complete()

    @pytest.mark.asyncio
    async def test_api_error_raises_llm_error(self):
        from anthropic import APIConnectionError
        mock_api = MagicMock()
        mock_api.messages = MagicMock()
        mock_api.messages.create = AsyncMock(
            side_effect=APIConnectionError(request=MagicMock())
        )
        client = LLMClient(max_retries=1, _client=mock_api)
        with pytest.raises(LLMError):
            await client.complete(system="s", messages=[{"role": "user", "content": "q"}])

    @pytest.mark.asyncio
    async def test_model_from_env(self, monkeypatch):
        monkeypatch.setenv("CCI_LLM_MODEL", "claude-sonnet-4-6")
        client, _ = _make_injected_client("x")
        # model was set explicitly in the constructor above, not from env
        # test env var path separately
        client2 = LLMClient(_client=MagicMock())
        assert client2.model == "claude-sonnet-4-6"

    @pytest.mark.asyncio
    async def test_complete_json_returns_string(self):
        client, _ = _make_injected_client('{"query": "test"}')
        raw = await client.complete_json(system="s", messages=[{"role": "user", "content": "q"}])
        assert raw == '{"query": "test"}'
