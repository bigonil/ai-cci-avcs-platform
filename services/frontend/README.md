# services/frontend — CCI/AVCS Frontend BFF

FastAPI BFF che serve la React SPA e fa da proxy verso i servizi backend.

## Porte

- `8080` — produzione (serve React build + /api/*)

## Env vars

| Variabile | Default | Descrizione |
|---|---|---|
| `COHERENCE_SERVICE_URL` | `http://coherence:8003` | URL del Coherence Service |
| `GOVERNANCE_SERVICE_URL` | `http://governance:8005` | URL del Governance Service |
| `FRONTEND_DIST_DIR` | `/app/dist` | Path della build React |

## Dev locale

```bash
# BFF only (senza static files)
cd services/frontend
uv pip install -e ".[dev]"
uvicorn cci_frontend.main:app --reload --port 8080

# React dev server (in altro terminale)
cd frontend
pnpm dev  # porta 5173
```

## Test

```bash
cd services/frontend
python -m pytest tests/ -v
```
