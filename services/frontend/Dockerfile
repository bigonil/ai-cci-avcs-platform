# Build context: repo root — docker build -f services/frontend/Dockerfile .
# Stage 1 (Vite React SPA build) will be added in Task 4

# Stage 2: FastAPI BFF
FROM python:3.12-slim AS runtime
WORKDIR /app
RUN pip install uv --no-cache-dir
COPY services/frontend/pyproject.toml ./
RUN uv pip install --system --no-cache .
COPY services/frontend/src ./src
ENV PYTHONPATH=/app/src
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/health/live')"
CMD ["uvicorn", "cci_frontend.main:app", "--host", "0.0.0.0", "--port", "8080"]
