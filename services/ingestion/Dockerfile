FROM python:3.12-slim AS builder

COPY --from=ghcr.io/astral-sh/uv:0.4.18 /uv /usr/local/bin/uv

# Build-time system packages required by Python deps (magic, pillow, etc.)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libmagic1 \
    libmagic-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /workspace

COPY pyproject.toml uv.lock ./
COPY libs/cci-common ./libs/cci-common
COPY services/ingestion ./services/ingestion

RUN --mount=type=cache,target=/root/.cache/uv \
    UV_HTTP_TIMEOUT=300 uv sync --package cci-ingestion --no-dev --no-editable

# Download spaCy Italian model (small, ~12MB) into the venv
RUN /workspace/.venv/bin/python -m spacy download it_core_news_sm || true

# ---------------------------------------------------------------------------
FROM python:3.12-slim AS runtime

WORKDIR /app

# Runtime system packages: OCR + document parsing
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-ita \
    libmagic1 \
    poppler-utils \
    libreoffice \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /workspace/.venv /app/.venv

ENV VIRTUAL_ENV=/app/.venv \
    PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

EXPOSE 8000

HEALTHCHECK --interval=10s --timeout=5s --start-period=30s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health/live')"

CMD ["python", "-m", "cci_ingestion.main"]
