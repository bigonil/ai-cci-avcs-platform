# ---- Build stage ----
FROM python:3.12-slim AS builder

WORKDIR /build

# Installa uv
COPY --from=ghcr.io/astral-sh/uv:0.4.18 /uv /usr/local/bin/uv

# Dipendenze sistema per Unstructured + Tesseract
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-ita \
    libmagic1 \
    poppler-utils \
    libreoffice \
    && rm -rf /var/lib/apt/lists/*

# Copia file di configurazione workspace
COPY pyproject.toml /build/
COPY libs/cci-common /build/libs/cci-common
COPY services/ingestion /build/services/ingestion

# Installa dipendenze in venv isolato
RUN uv venv /build/.venv && \
    uv pip install --python /build/.venv/bin/python \
    -e /build/libs/cci-common \
    -e /build/services/ingestion

# Scarica modello spaCy italiano (small, ~12 MB)
RUN /build/.venv/bin/python -m spacy download it_core_news_sm || true

# ---- Runtime stage ----
FROM python:3.12-slim AS runtime

WORKDIR /app

# Dipendenze runtime
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-ita \
    libmagic1 \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /build/.venv /app/.venv
COPY --from=builder /build/libs/cci-common /app/libs/cci-common
COPY --from=builder /build/services/ingestion/src /app/src

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONPATH="/app/src:/app/libs/cci-common/src" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

EXPOSE 8000

HEALTHCHECK --interval=10s --timeout=5s --start-period=30s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health/live')"

CMD ["python", "-m", "cci_ingestion.main"]
