FROM python:3.12-slim AS builder

COPY --from=ghcr.io/astral-sh/uv:0.4.18 /uv /usr/local/bin/uv

WORKDIR /workspace

COPY pyproject.toml uv.lock ./
COPY libs/cci-common ./libs/cci-common
COPY services/governance ./services/governance

RUN uv sync --package cci-governance --no-dev --no-editable

# ---------------------------------------------------------------------------
FROM python:3.12-slim

LABEL org.opencontainers.image.title="cci-governance"
LABEL org.opencontainers.image.description="CCI/AVCS Governance — immutable audit log, HITL gate, AI Act compliance"

WORKDIR /app

COPY --from=builder /workspace/.venv /app/.venv

ENV VIRTUAL_ENV=/app/.venv \
    PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

EXPOSE 8005

HEALTHCHECK --interval=15s --timeout=5s --start-period=30s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8005/health/live')"

CMD ["python", "-m", "cci_governance.main"]
