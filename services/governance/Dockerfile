FROM python:3.12-slim AS builder

WORKDIR /build

RUN pip install uv

COPY libs/cci-common /build/libs/cci-common
COPY services/governance /build/services/governance

RUN uv pip install --system --no-cache /build/libs/cci-common

WORKDIR /build/services/governance
RUN uv pip install --system --no-cache .

# ---------------------------------------------------------------------------
FROM python:3.12-slim

LABEL org.opencontainers.image.title="cci-governance"
LABEL org.opencontainers.image.description="CCI/AVCS Governance — immutable audit log, HITL gate, AI Act compliance"

WORKDIR /app

COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /build/services/governance/src /app/src

ENV PYTHONPATH=/app/src

EXPOSE 8005

HEALTHCHECK --interval=15s --timeout=5s --start-period=30s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8005/health/live')"

CMD ["python", "-m", "cci_governance.main"]
