FROM python:3.12-slim AS builder

WORKDIR /build

RUN pip install uv

# Copy workspace packages needed
COPY libs/cci-common /build/libs/cci-common
COPY libs/cci-llm /build/libs/cci-llm
COPY services/agents /build/services/agents

# Build cci-common and cci-llm wheels first
RUN uv pip install --system --no-cache /build/libs/cci-common
RUN uv pip install --system --no-cache /build/libs/cci-llm

# Install agents service
WORKDIR /build/services/agents
RUN uv pip install --system --no-cache .

# ---------------------------------------------------------------------------
FROM python:3.12-slim

LABEL org.opencontainers.image.title="cci-agents"
LABEL org.opencontainers.image.description="CCI/AVCS Agents — LangGraph 5-node verification pipeline"

WORKDIR /app

COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /build/services/agents/src /app/src

ENV PYTHONPATH=/app/src
ENV PROMPTS_PATH=/app/prompts/v1

EXPOSE 8004

HEALTHCHECK --interval=15s --timeout=5s --start-period=30s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8004/health/live')"

CMD ["python", "-m", "cci_agents.main"]
