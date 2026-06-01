FROM python:3.12-slim AS builder

COPY --from=ghcr.io/astral-sh/uv:0.4.18 /uv /usr/local/bin/uv

WORKDIR /workspace

# Workspace root — needed for uv to resolve workspace member sources
COPY pyproject.toml uv.lock ./
COPY libs/cci-common ./libs/cci-common
COPY services/coherence ./services/coherence

# Install the service and its runtime deps as wheels (self-contained venv)
RUN uv sync --package cci-coherence --no-dev --no-editable

# ---------------------------------------------------------------------------
FROM python:3.12-slim

LABEL org.opencontainers.image.title="cci-coherence"
LABEL org.opencontainers.image.description="CCI/AVCS Coherence Engine — deterministic rule evaluation, R4 zero-LLM"

WORKDIR /app

COPY --from=builder /workspace/.venv /app/.venv

ENV VIRTUAL_ENV=/app/.venv \
    PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    ONTOLOGIES_PATH=/app/ontologies

EXPOSE 8003

HEALTHCHECK --interval=15s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8003/health/live')"

CMD ["python", "-m", "cci_coherence.main"]
