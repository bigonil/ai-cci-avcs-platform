FROM python:3.12-slim AS builder

RUN pip install uv
WORKDIR /build

COPY pyproject.toml ./
COPY src/ ./src/

# Install production deps into /app/venv
RUN uv venv /app/venv && \
    uv pip install --python /app/venv/bin/python --no-cache \
      fastapi uvicorn[standard] pydantic pydantic-settings \
      qdrant-client neo4j motor pyyaml \
      prometheus-fastapi-instrumentator structlog \
      redis

# Install cci-common from workspace root (mounted at build time)
COPY libs/cci-common/ /build/cci-common/
RUN uv pip install --python /app/venv/bin/python /build/cci-common

# Install service itself
RUN uv pip install --python /app/venv/bin/python --no-deps .


FROM python:3.12-slim AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/app/venv/bin:$PATH"

WORKDIR /app
COPY --from=builder /app/venv /app/venv
COPY --from=builder /build/src /app/src

# Ontology files are mounted at runtime via docker-compose volume
RUN mkdir -p /app/ontologies

EXPOSE 8001

HEALTHCHECK --interval=15s --timeout=5s --start-period=30s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8001/health/live')"

CMD ["python", "-m", "cci_knowledge.main"]
