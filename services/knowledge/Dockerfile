FROM python:3.12-slim AS builder

COPY --from=ghcr.io/astral-sh/uv:0.4.18 /uv /usr/local/bin/uv

WORKDIR /workspace

COPY pyproject.toml uv.lock ./
COPY libs/cci-common ./libs/cci-common
COPY services/knowledge ./services/knowledge

RUN uv sync --package cci-knowledge --no-dev --no-editable

# ---------------------------------------------------------------------------
FROM python:3.12-slim AS runtime

LABEL org.opencontainers.image.title="cci-knowledge"
LABEL org.opencontainers.image.description="CCI/AVCS Knowledge — vector store, temporal KG, time-series"

WORKDIR /app

COPY --from=builder /workspace/.venv /app/.venv

RUN mkdir -p /app/ontologies

ENV VIRTUAL_ENV=/app/.venv \
    PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    ONTOLOGIES_PATH=/app/ontologies

EXPOSE 8001

HEALTHCHECK --interval=15s --timeout=5s --start-period=30s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8001/health/live')"

CMD ["python", "-m", "cci_knowledge.main"]
