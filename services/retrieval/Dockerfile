FROM python:3.12-slim AS builder

RUN pip install uv
WORKDIR /build

COPY pyproject.toml ./
COPY src/ ./src/

# Install production deps
RUN uv venv /app/venv && \
    uv pip install --python /app/venv/bin/python --no-cache \
      fastapi uvicorn[standard] pydantic pydantic-settings \
      qdrant-client rank-bm25 sentence-transformers \
      redis prometheus-fastapi-instrumentator structlog

# Install cci-common from workspace root
COPY libs/cci-common/ /build/cci-common/
RUN uv pip install --python /app/venv/bin/python /build/cci-common

# Install service
RUN uv pip install --python /app/venv/bin/python --no-deps .


FROM python:3.12-slim AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/app/venv/bin:$PATH" \
    # sentence-transformers model cache inside container
    TRANSFORMERS_CACHE=/app/.cache \
    SENTENCE_TRANSFORMERS_HOME=/app/.cache

WORKDIR /app
COPY --from=builder /app/venv /app/venv
COPY --from=builder /build/src /app/src

RUN mkdir -p /app/.cache

EXPOSE 8002

HEALTHCHECK --interval=15s --timeout=5s --start-period=60s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8002/health/live')"

CMD ["python", "-m", "cci_retrieval.main"]
