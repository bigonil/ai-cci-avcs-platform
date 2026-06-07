# Stage 1: build React SPA
FROM node:20-alpine AS react-build
RUN npm install -g pnpm@9
WORKDIR /frontend
COPY frontend/package.json frontend/pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile
COPY frontend/ ./
RUN pnpm build

# Stage 2: FastAPI BFF
FROM python:3.12-slim AS runtime
WORKDIR /app
RUN pip install uv --no-cache-dir
COPY services/frontend/pyproject.toml ./
RUN uv pip install --system --no-cache .
COPY services/frontend/src ./src
COPY --from=react-build /frontend/dist ./dist
ENV FRONTEND_DIST_DIR=/app/dist
ENV PYTHONPATH=/app/src
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/health/live')"
CMD ["uvicorn", "cci_frontend.main:app", "--host", "0.0.0.0", "--port", "8080"]
