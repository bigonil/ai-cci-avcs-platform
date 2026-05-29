FROM python:3.12-slim AS builder

WORKDIR /build

RUN pip install uv

COPY pyproject.toml .
COPY src/ src/

# Install runtime deps only (no test extras)
RUN uv pip install --system --no-cache .

# ---------------------------------------------------------------------------
FROM python:3.12-slim

LABEL org.opencontainers.image.title="cci-coherence"
LABEL org.opencontainers.image.description="CCI/AVCS Coherence Engine — deterministic rule evaluation, R4 zero-LLM"

WORKDIR /app

COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /build/src /app/src

# Ontology files mounted at /app/ontologies via docker-compose volume
ENV PYTHONPATH=/app/src
ENV ONTOLOGIES_PATH=/app/ontologies

EXPOSE 8003

HEALTHCHECK --interval=15s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8003/health/live')"

CMD ["python", "-m", "cci_coherence.main"]
