FROM python:3.12-slim AS builder

COPY --from=ghcr.io/astral-sh/uv:0.4.18 /uv /usr/local/bin/uv

WORKDIR /workspace

COPY pyproject.toml uv.lock ./
COPY libs/cci-common ./libs/cci-common
COPY services/retrieval ./services/retrieval

RUN --mount=type=cache,target=/root/.cache/uv \
    UV_HTTP_TIMEOUT=300 uv sync --package cci-retrieval --no-dev --no-editable

# ---------------------------------------------------------------------------
FROM python:3.12-slim AS runtime

LABEL org.opencontainers.image.title="cci-retrieval"
LABEL org.opencontainers.image.description="CCI/AVCS Retrieval — hybrid search, RRF, reranking, Redis cache"

WORKDIR /app

COPY --from=builder /workspace/.venv /app/.venv

RUN mkdir -p /app/.cache

ENV VIRTUAL_ENV=/app/.venv \
    PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    # sentence-transformers model cache (mapped to a named volume in compose)
    TRANSFORMERS_CACHE=/app/.cache \
    SENTENCE_TRANSFORMERS_HOME=/app/.cache

EXPOSE 8002

HEALTHCHECK --interval=15s --timeout=5s --start-period=60s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8002/health/live')"

CMD ["python", "-m", "cci_retrieval.main"]
