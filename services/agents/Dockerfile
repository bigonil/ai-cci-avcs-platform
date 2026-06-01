FROM python:3.12-slim AS builder

COPY --from=ghcr.io/astral-sh/uv:0.4.18 /uv /usr/local/bin/uv

WORKDIR /workspace

COPY pyproject.toml uv.lock ./
# agents depends on both cci-common and cci-llm
COPY libs/cci-common ./libs/cci-common
COPY libs/cci-llm ./libs/cci-llm
COPY services/agents ./services/agents

RUN uv sync --package cci-agents --no-dev --no-editable

# ---------------------------------------------------------------------------
FROM python:3.12-slim

LABEL org.opencontainers.image.title="cci-agents"
LABEL org.opencontainers.image.description="CCI/AVCS Agents — LangGraph 5-node verification pipeline"

WORKDIR /app

COPY --from=builder /workspace/.venv /app/.venv

ENV VIRTUAL_ENV=/app/.venv \
    PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PROMPTS_PATH=/app/prompts/v1

EXPOSE 8004

HEALTHCHECK --interval=15s --timeout=5s --start-period=30s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8004/health/live')"

CMD ["python", "-m", "cci_agents.main"]
