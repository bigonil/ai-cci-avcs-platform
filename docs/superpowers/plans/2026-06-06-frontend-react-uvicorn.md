# Frontend React SPA + FastAPI BFF Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Sostituire il frontend Next.js con una React SPA (Vite) servita da un FastAPI BFF, mantenendo tutte le funzionalità esistenti con il design Bold Modern.

**Architecture:** FastAPI BFF (`services/frontend/`) espone `/api/*` come proxy verso `coherence:8003` e `governance:8005`, e serve la build React statica in produzione. In dev, Vite dev server gira separatamente su :5173.

**Tech Stack:** Python 3.12 · FastAPI · httpx · Uvicorn | Vite 6 · React 19 · TypeScript strict · React Router v7 · TanStack Query v5 · Tailwind CSS v4 · shadcn/ui · lucide-react · sonner | Vitest · Playwright

---

## File map

### `services/frontend/` (nuovo servizio BFF)

| File | Responsabilità |
|---|---|
| `pyproject.toml` | Dipendenze Python + metadata |
| `Dockerfile` | Multi-stage: build React → serve con Uvicorn |
| `src/cci_frontend/__init__.py` | Package marker |
| `src/cci_frontend/main.py` | FastAPI app, lifespan, mount static, SPA fallback |
| `src/cci_frontend/proxy.py` | Router `/api/*` con routing coherence/governance |
| `src/cci_frontend/health.py` | `/health/live`, `/health/ready` |
| `tests/__init__.py` | Test package |
| `tests/test_health.py` | Health endpoint tests |
| `tests/test_proxy.py` | Proxy route tests con httpx mock |

### `frontend/` (rimpiazza Next.js con Vite SPA)

| File | Responsabilità |
|---|---|
| `index.html` | HTML entry point |
| `vite.config.ts` | Vite + Tailwind plugin + test config |
| `tsconfig.json` | TypeScript strict |
| `package.json` | Dipendenze npm |
| `src/index.css` | Tailwind import + CSS vars Bold Modern |
| `src/main.tsx` | Entry point: QueryClientProvider + RouterProvider |
| `src/app.tsx` | Layout root: Sidebar + `<Outlet>` |
| `src/lib/types.ts` | Tipi condivisi: Incoherence, HitlAction, AuditEvent |
| `src/lib/api.ts` | fetch wrapper + base URL |
| `src/lib/utils.ts` | `cn()`, `formatEur()`, `formatDate()` |
| `src/components/ui/` | shadcn/ui primitivi |
| `src/components/sidebar.tsx` | Sidebar glassmorphism + nav items |
| `src/components/kpi-strip.tsx` | 3 KPI card con top bar colorata |
| `src/components/incoherence-card.tsx` | Card con left border + badge severity |
| `src/components/chunk-citation.tsx` | Badge `[chunk_id]` inline |
| `src/components/explanation-block.tsx` | Testo LLM con citation badges |
| `src/components/generate-explanation-button.tsx` | Bottone + spinner + toast |
| `src/hooks/use-incoherences.ts` | `useQuery` lista incoerenze |
| `src/hooks/use-incoherence.ts` | `useQuery` singola incoerenza |
| `src/hooks/use-explanation.ts` | `useMutation` POST /explain |
| `src/hooks/use-hitl-queue.ts` | `useQuery` coda HITL + `useMutation` approva |
| `src/hooks/use-audit-events.ts` | `useQuery` audit events |
| `src/pages/dashboard.tsx` | `/` — KpiStrip + ultime incoerenze |
| `src/pages/incoherences.tsx` | `/incoherences` — lista filtrata |
| `src/pages/incoherence-detail.tsx` | `/incoherences/:id` — dettaglio + spiegazione |
| `src/pages/hitl-queue.tsx` | `/hitl` — coda azioni in attesa |
| `src/pages/hitl-action.tsx` | `/hitl/:actionId` — form approvazione |
| `src/pages/audit.tsx` | `/audit` — eventi + chain status |
| `src/tests/` | Vitest unit tests |
| `e2e/` | Playwright E2E tests |

### File modificati

| File | Modifica |
|---|---|
| `docker-compose.yml` | Sostituisce servizio `frontend` Next.js con BFF FastAPI :8080 |
| `docker-compose.dev.yml` | Sostituisce hot-reload Next.js con Vite dev server |
| `Makefile` | Aggiorna target `up`, `up-dev`, rimuove riferimenti Next.js |

---

## Task 1: FastAPI BFF — scaffold + health

**Files:**
- Create: `services/frontend/pyproject.toml`
- Create: `services/frontend/src/cci_frontend/__init__.py`
- Create: `services/frontend/src/cci_frontend/health.py`
- Create: `services/frontend/src/cci_frontend/main.py`
- Create: `services/frontend/tests/__init__.py`
- Create: `services/frontend/tests/test_health.py`

- [ ] **Step 1: Scrivi il test del health endpoint**

```python
# services/frontend/tests/test_health.py
import pytest
from fastapi.testclient import TestClient
from cci_frontend.main import app


@pytest.fixture
def client():
    return TestClient(app)


def test_live_returns_ok(client):
    resp = client.get("/health/live")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_ready_returns_ok(client):
    resp = client.get("/health/ready")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
```

- [ ] **Step 2: Verifica che il test fallisca (modulo non esiste)**

```bash
cd services/frontend
python -m pytest tests/test_health.py -v 2>&1 | head -20
# Atteso: ModuleNotFoundError o ImportError
```

- [ ] **Step 3: Crea pyproject.toml**

```toml
# services/frontend/pyproject.toml
[project]
name = "cci-frontend"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
    "fastapi>=0.115",
    "uvicorn[standard]>=0.32",
    "httpx>=0.27",
    "aiofiles>=24.1",
]

[project.optional-dependencies]
dev = [
    "pytest>=8",
    "pytest-asyncio>=0.24",
    "httpx>=0.27",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/cci_frontend"]

[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"
```

- [ ] **Step 4: Crea i moduli Python**

```python
# services/frontend/src/cci_frontend/__init__.py
```

```python
# services/frontend/src/cci_frontend/health.py
from fastapi import APIRouter

router = APIRouter()


@router.get("/health/live")
async def live() -> dict:
    return {"status": "ok"}


@router.get("/health/ready")
async def ready() -> dict:
    return {"status": "ok"}
```

```python
# services/frontend/src/cci_frontend/main.py
from contextlib import asynccontextmanager
from fastapi import FastAPI
from .health import router as health_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(title="CCI/AVCS Frontend BFF", version="0.1.0", lifespan=lifespan)
app.include_router(health_router)
```

- [ ] **Step 5: Installa dipendenze e verifica che i test passino**

```bash
cd services/frontend
uv pip install -e ".[dev]"
python -m pytest tests/test_health.py -v
# Atteso: 2 passed
```

- [ ] **Step 6: Commit**

```bash
git add services/frontend/
git commit -m "feat(frontend-bff): scaffold FastAPI BFF with health endpoints"
```

---

## Task 2: FastAPI BFF — proxy routes

**Files:**
- Create: `services/frontend/src/cci_frontend/proxy.py`
- Modify: `services/frontend/src/cci_frontend/main.py`
- Create: `services/frontend/tests/test_proxy.py`

- [ ] **Step 1: Scrivi i test del proxy**

```python
# services/frontend/tests/test_proxy.py
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient
from cci_frontend.main import app

client = TestClient(app)


def _mock_response(status_code: int = 200, content: bytes = b'{"ok": true}'):
    resp = MagicMock()
    resp.status_code = status_code
    resp.content = content
    resp.headers = {"content-type": "application/json"}
    return resp


@patch("cci_frontend.proxy.httpx.AsyncClient")
def test_proxy_incoherences_list(mock_client_cls):
    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.request = AsyncMock(return_value=_mock_response())
    mock_client_cls.return_value = mock_client

    resp = client.get("/api/incoherences?domain=hera_it")
    assert resp.status_code == 200
    call_args = mock_client.request.call_args
    assert "incoherences" in call_args.kwargs["url"]
    assert "domain=hera_it" in call_args.kwargs["url"]


@patch("cci_frontend.proxy.httpx.AsyncClient")
def test_proxy_incoherence_explain(mock_client_cls):
    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.request = AsyncMock(return_value=_mock_response())
    mock_client_cls.return_value = mock_client

    resp = client.post("/api/incoherences/abc123/explain")
    assert resp.status_code == 200
    call_args = mock_client.request.call_args
    assert "abc123/explain" in call_args.kwargs["url"]


@patch("cci_frontend.proxy.httpx.AsyncClient")
def test_proxy_hitl_routes_to_governance(mock_client_cls):
    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.request = AsyncMock(return_value=_mock_response())
    mock_client_cls.return_value = mock_client

    resp = client.get("/api/hitl/queue")
    assert resp.status_code == 200
    call_args = mock_client.request.call_args
    assert "governance" in call_args.kwargs["url"] or "8005" in call_args.kwargs["url"]


@patch("cci_frontend.proxy.httpx.AsyncClient")
def test_proxy_unknown_path_returns_404(mock_client_cls):
    resp = client.get("/api/unknown/path")
    assert resp.status_code == 404
```

- [ ] **Step 2: Verifica che i test falliscano**

```bash
cd services/frontend
python -m pytest tests/test_proxy.py -v 2>&1 | head -20
# Atteso: ImportError (proxy module non esiste)
```

- [ ] **Step 3: Implementa proxy.py**

```python
# services/frontend/src/cci_frontend/proxy.py
import os
import httpx
from fastapi import APIRouter, HTTPException, Request, Response

router = APIRouter()

COHERENCE_URL = os.getenv("COHERENCE_SERVICE_URL", "http://coherence:8003")
GOVERNANCE_URL = os.getenv("GOVERNANCE_SERVICE_URL", "http://governance:8005")

_ROUTE_MAP: dict[str, str] = {
    "incoherences": COHERENCE_URL,
    "hitl": GOVERNANCE_URL,
    "audit": GOVERNANCE_URL,
}


def _resolve_upstream(path: str) -> str:
    prefix = path.split("/")[0]
    base = _ROUTE_MAP.get(prefix)
    if base is None:
        raise HTTPException(status_code=404, detail=f"No upstream for path: {path}")
    return base


@router.api_route("/{path:path}", methods=["GET", "POST", "PATCH", "PUT", "DELETE"])
async def proxy(path: str, request: Request) -> Response:
    # Re-read env vars so they can be changed in tests via monkeypatch
    route_map = {
        "incoherences": os.getenv("COHERENCE_SERVICE_URL", "http://coherence:8003"),
        "hitl": os.getenv("GOVERNANCE_SERVICE_URL", "http://governance:8005"),
        "audit": os.getenv("GOVERNANCE_SERVICE_URL", "http://governance:8005"),
    }
    prefix = path.split("/")[0]
    base = route_map.get(prefix)
    if base is None:
        raise HTTPException(status_code=404, detail=f"No upstream for path: {path}")

    qs = f"?{request.url.query}" if request.url.query else ""
    url = f"{base}/{path}{qs}"
    body = await request.body()
    skip_headers = {"host", "content-length", "transfer-encoding"}
    headers = {k: v for k, v in request.headers.items() if k.lower() not in skip_headers}

    async with httpx.AsyncClient(timeout=30.0) as client:
        upstream_resp = await client.request(
            method=request.method,
            url=url,
            headers=headers,
            content=body,
        )

    return Response(
        content=upstream_resp.content,
        status_code=upstream_resp.status_code,
        headers={k: v for k, v in upstream_resp.headers.items() if k.lower() != "transfer-encoding"},
        media_type=upstream_resp.headers.get("content-type"),
    )
```

- [ ] **Step 4: Registra il router in main.py**

```python
# services/frontend/src/cci_frontend/main.py
from contextlib import asynccontextmanager
from fastapi import FastAPI
from .health import router as health_router
from .proxy import router as proxy_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(title="CCI/AVCS Frontend BFF", version="0.1.0", lifespan=lifespan)
app.include_router(health_router)
app.include_router(proxy_router, prefix="/api")
```

- [ ] **Step 5: Esegui i test**

```bash
cd services/frontend
python -m pytest tests/ -v
# Atteso: 5 passed
```

- [ ] **Step 6: Commit**

```bash
git add services/frontend/src/cci_frontend/proxy.py services/frontend/src/cci_frontend/main.py services/frontend/tests/test_proxy.py
git commit -m "feat(frontend-bff): add proxy routes for coherence and governance services"
```

---

## Task 3: FastAPI BFF — static file serving + Dockerfile

**Files:**
- Modify: `services/frontend/src/cci_frontend/main.py`
- Create: `services/frontend/Dockerfile`
- Create: `services/frontend/README.md`

- [ ] **Step 1: Aggiungi static file serving e SPA fallback a main.py**

```python
# services/frontend/src/cci_frontend/main.py
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .health import router as health_router
from .proxy import router as proxy_router

DIST_DIR = Path(os.getenv("FRONTEND_DIST_DIR", "/app/dist"))


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(title="CCI/AVCS Frontend BFF", version="0.1.0", lifespan=lifespan)
app.include_router(health_router)
app.include_router(proxy_router, prefix="/api")

# Static assets (JS/CSS/images) — mount ONLY if dist dir exists (skip in dev)
if DIST_DIR.exists():
    _assets = DIST_DIR / "assets"
    if _assets.exists():
        app.mount("/assets", StaticFiles(directory=str(_assets)), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def spa_fallback(full_path: str) -> FileResponse:
        return FileResponse(str(DIST_DIR / "index.html"))
```

- [ ] **Step 2: Crea Dockerfile multi-stage**

```dockerfile
# services/frontend/Dockerfile
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
```

- [ ] **Step 3: Crea README del servizio**

```markdown
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
```

- [ ] **Step 4: Verifica che i test esistenti passino ancora**

```bash
cd services/frontend
python -m pytest tests/ -v
# Atteso: 5 passed
```

- [ ] **Step 5: Commit**

```bash
git add services/frontend/src/cci_frontend/main.py services/frontend/Dockerfile services/frontend/README.md
git commit -m "feat(frontend-bff): add static file serving, SPA fallback, and Dockerfile"
```

---

## Task 4: Rimuovi Next.js, scaffold Vite React SPA

**Files:**
- Delete: `frontend/` (tutto il contenuto Next.js)
- Create: `frontend/package.json`, `frontend/index.html`, `frontend/vite.config.ts`, `frontend/tsconfig.json`

- [ ] **Step 1: Rimuovi i file Next.js (mantieni solo le directory)**

```bash
# Dalla root del repo
# Backup rapido del contenuto attuale (sicurezza)
git stash list  # verifica che non ci sia lavoro non committato

# Elimina contenuto Next.js
Remove-Item -Recurse -Force frontend\app, frontend\components, frontend\hooks, frontend\lib, frontend\tests, frontend\public, frontend\node_modules, frontend\.next -ErrorAction SilentlyContinue
Remove-Item -Force frontend\package.json, frontend\pnpm-lock.yaml, frontend\pnpm-workspace.yaml, frontend\next.config.ts, frontend\next-env.d.ts, frontend\tsconfig.json, frontend\tsconfig.tsbuildinfo, frontend\tailwind.config.ts, frontend\postcss.config.mjs, frontend\eslint.config.mjs, frontend\components.json, frontend\vitest.config.ts, frontend\Dockerfile, frontend\Dockerfile.dev, frontend\README.md -ErrorAction SilentlyContinue
```

- [ ] **Step 2: Crea package.json Vite**

```json
// frontend/package.json
{
  "name": "cci-avcs-frontend",
  "private": true,
  "version": "0.1.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc -b && vite build",
    "preview": "vite preview",
    "test": "vitest run",
    "test:watch": "vitest"
  },
  "dependencies": {
    "react": "^19.0.0",
    "react-dom": "^19.0.0",
    "react-router-dom": "^7.0.0",
    "@tanstack/react-query": "^5.0.0",
    "@tanstack/react-query-devtools": "^5.0.0",
    "lucide-react": "^0.469.0",
    "sonner": "^1.7.0",
    "clsx": "^2.1.0",
    "tailwind-merge": "^2.5.0",
    "class-variance-authority": "^0.7.1"
  },
  "devDependencies": {
    "@types/react": "^19.0.0",
    "@types/react-dom": "^19.0.0",
    "@vitejs/plugin-react": "^4.3.0",
    "tailwindcss": "^4.0.0",
    "@tailwindcss/vite": "^4.0.0",
    "typescript": "^5.7.0",
    "vite": "^6.0.0",
    "vitest": "^2.1.0",
    "@vitest/coverage-v8": "^2.1.0",
    "jsdom": "^25.0.0",
    "@testing-library/react": "^16.0.0",
    "@testing-library/user-event": "^14.5.0",
    "@testing-library/jest-dom": "^6.6.0"
  }
}
```

- [ ] **Step 3: Crea index.html**

```html
<!-- frontend/index.html -->
<!doctype html>
<html lang="it">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>CCI / AVCS — Coherence Engine</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

- [ ] **Step 4: Crea vite.config.ts**

```typescript
// frontend/vite.config.ts
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import { resolve } from 'path'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: { '@': resolve(__dirname, './src') },
  },
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8080',
        changeOrigin: true,
      },
    },
  },
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: ['./src/tests/setup.ts'],
    coverage: { provider: 'v8', reporter: ['text', 'html'] },
  },
})
```

- [ ] **Step 5: Crea tsconfig.json**

```json
// frontend/tsconfig.json
{
  "compilerOptions": {
    "target": "ES2022",
    "lib": ["ES2022", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "moduleResolution": "bundler",
    "jsx": "react-jsx",
    "strict": true,
    "noUncheckedIndexedAccess": true,
    "skipLibCheck": true,
    "moduleDetection": "force",
    "allowImportingTsExtensions": true,
    "noEmit": true,
    "baseUrl": ".",
    "paths": { "@/*": ["./src/*"] }
  },
  "include": ["src"]
}
```

- [ ] **Step 6: Installa dipendenze**

```bash
cd frontend
pnpm install
```

- [ ] **Step 7: Commit**

```bash
git add frontend/
git commit -m "feat(frontend): replace Next.js with Vite React SPA scaffold"
```

---

## Task 5: Core types, API client, utilities, test setup

**Files:**
- Create: `frontend/src/lib/types.ts`
- Create: `frontend/src/lib/api.ts`
- Create: `frontend/src/lib/utils.ts`
- Create: `frontend/src/tests/setup.ts`
- Create: `frontend/src/tests/lib.test.ts`

- [ ] **Step 1: Scrivi i test delle utility**

```typescript
// frontend/src/tests/lib.test.ts
import { describe, it, expect } from 'vitest'
import { formatEur, formatDate, severityColor } from '@/lib/utils'

describe('formatEur', () => {
  it('formats positive number with EUR suffix', () => {
    expect(formatEur(80000)).toBe('+80.000 €')
  })
  it('formats negative number', () => {
    expect(formatEur(-5000)).toBe('-5.000 €')
  })
  it('formats zero', () => {
    expect(formatEur(0)).toBe('0 €')
  })
})

describe('formatDate', () => {
  it('formats ISO string to locale date', () => {
    const result = formatDate('2026-06-06T10:00:00Z')
    expect(result).toMatch(/2026/)
  })
})

describe('severityColor', () => {
  it('returns red for CRITICAL', () => {
    expect(severityColor('CRITICAL')).toContain('ef4444')
  })
  it('returns orange for HIGH', () => {
    expect(severityColor('HIGH')).toContain('f97316')
  })
  it('returns amber for MEDIUM', () => {
    expect(severityColor('MEDIUM')).toContain('f59e0b')
  })
  it('returns blue for LOW', () => {
    expect(severityColor('LOW')).toContain('818cf8')
  })
})
```

- [ ] **Step 2: Verifica che i test falliscano**

```bash
cd frontend
pnpm test
# Atteso: Cannot find module '@/lib/utils'
```

- [ ] **Step 3: Crea types.ts**

```typescript
// frontend/src/lib/types.ts
export type Severity = 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW'

export interface Incoherence {
  id: string
  domain: string
  rule_id: string
  severity: Severity
  description: string
  detected_at: string
  impact_eur: number
  evidence_chunks: string[]
  explanation: string | null
  citations: string[]
  grounding_verified: boolean | null
}

export interface HitlAction {
  id: string
  action_type: string
  description: string
  impact: string
  status: 'PENDING' | 'APPROVED' | 'REJECTED'
  created_at: string
  incoherence_id: string | null
}

export interface AuditEvent {
  seq: number
  event_id: string
  ts: string
  actor: string
  event_type: string
  payload: Record<string, unknown>
}

export interface AuditChainStatus {
  valid: boolean
  total_records: number
  last_seq: number
}

export interface ExplanationOut {
  explanation: string
  citations: string[]
  grounding_verified: boolean
}

export interface PagedResponse<T> {
  items: T[]
  total: number
  page: number
  size: number
}
```

- [ ] **Step 4: Crea api.ts**

```typescript
// frontend/src/lib/api.ts
const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? ''

export async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const resp = await fetch(`${BASE_URL}/api${path}`, {
    headers: { 'Content-Type': 'application/json', ...init?.headers },
    ...init,
  })
  if (!resp.ok) {
    const text = await resp.text().catch(() => '')
    throw new ApiError(resp.status, text || resp.statusText)
  }
  return resp.json() as Promise<T>
}

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    message: string,
  ) {
    super(message)
    this.name = 'ApiError'
  }
}
```

- [ ] **Step 5: Crea utils.ts**

```typescript
// frontend/src/lib/utils.ts
import { clsx, type ClassValue } from 'clsx'
import { twMerge } from 'tailwind-merge'
import type { Severity } from './types'

export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs))
}

export function formatEur(amount: number): string {
  if (amount === 0) return '0 €'
  const abs = Math.abs(amount).toLocaleString('it-IT')
  return amount > 0 ? `+${abs} €` : `-${abs} €`
}

export function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString('it-IT', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
  })
}

export const SEVERITY_CONFIG: Record<Severity, { color: string; barColor: string; label: string }> = {
  CRITICAL: { color: '#ef4444', barColor: '#ef4444', label: 'CRITICAL' },
  HIGH:     { color: '#f97316', barColor: '#f97316', label: 'HIGH' },
  MEDIUM:   { color: '#f59e0b', barColor: '#f59e0b', label: 'MEDIUM' },
  LOW:      { color: '#818cf8', barColor: '#818cf8', label: 'LOW' },
}

export function severityColor(severity: Severity): string {
  return SEVERITY_CONFIG[severity].color
}
```

- [ ] **Step 6: Crea test setup**

```typescript
// frontend/src/tests/setup.ts
import '@testing-library/jest-dom'
```

- [ ] **Step 7: Esegui i test**

```bash
cd frontend
pnpm test
# Atteso: 8 passed
```

- [ ] **Step 8: Commit**

```bash
git add frontend/src/lib/ frontend/src/tests/
git commit -m "feat(frontend): add core types, API client, utilities, and test setup"
```

---

## Task 6: Design system CSS + App layout + Sidebar

**Files:**
- Create: `frontend/src/index.css`
- Create: `frontend/src/main.tsx`
- Create: `frontend/src/app.tsx`
- Create: `frontend/src/components/sidebar.tsx`
- Create: `frontend/src/tests/sidebar.test.tsx`

- [ ] **Step 1: Scrivi il test del Sidebar**

```typescript
// frontend/src/tests/sidebar.test.tsx
import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { Sidebar } from '@/components/sidebar'

function renderSidebar() {
  return render(
    <MemoryRouter initialEntries={['/']}>
      <Sidebar />
    </MemoryRouter>
  )
}

describe('Sidebar', () => {
  it('renders the CCI/AVCS logo text', () => {
    renderSidebar()
    expect(screen.getByText('CCI / AVCS')).toBeInTheDocument()
  })

  it('renders all 4 nav items', () => {
    renderSidebar()
    expect(screen.getByText('Dashboard')).toBeInTheDocument()
    expect(screen.getByText('Incoerenze')).toBeInTheDocument()
    expect(screen.getByText('Coda HITL')).toBeInTheDocument()
    expect(screen.getByText('Audit Trail')).toBeInTheDocument()
  })

  it('shows sistema operativo status', () => {
    renderSidebar()
    expect(screen.getByText('Sistema operativo')).toBeInTheDocument()
  })
})
```

- [ ] **Step 2: Verifica che il test fallisca**

```bash
cd frontend
pnpm test src/tests/sidebar.test.tsx
# Atteso: Cannot find module '@/components/sidebar'
```

- [ ] **Step 3: Crea index.css con Bold Modern design tokens**

```css
/* frontend/src/index.css */
@import "tailwindcss";

:root {
  --sidebar-width: 220px;
  --sidebar-bg: rgba(10, 8, 28, 0.8);
  --sidebar-border: rgba(129, 140, 248, 0.12);
  --card-bg: rgba(255, 255, 255, 0.04);
  --card-border: rgba(255, 255, 255, 0.08);
  --color-primary: #818cf8;
  --color-primary-dim: #a78bfa;
  --color-critical: #ef4444;
  --color-high: #f97316;
  --color-medium: #f59e0b;
  --color-ok: #22c55e;
  --text-primary: #f1f5f9;
  --text-secondary: rgba(165, 180, 252, 0.6);
  --text-dim: rgba(165, 180, 252, 0.35);
  --gradient-bg: linear-gradient(160deg, #0d0b1e 0%, #1a1535 40%, #0d1a2e 100%);
}

body {
  margin: 0;
  font-family: -apple-system, BlinkMacSystemFont, 'Inter', sans-serif;
  background: var(--gradient-bg);
  color: var(--text-primary);
  min-height: 100vh;
}

* {
  box-sizing: border-box;
}

::-webkit-scrollbar { width: 4px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: rgba(129, 140, 248, 0.2); border-radius: 2px; }
```

- [ ] **Step 4: Crea sidebar.tsx**

```typescript
// frontend/src/components/sidebar.tsx
import { NavLink } from 'react-router-dom'
import { LayoutDashboard, AlertTriangle, ClipboardList, ShieldCheck } from 'lucide-react'

interface NavItem {
  path: string
  label: string
  icon: React.ReactNode
  badge?: number
  badgeColor?: string
}

const NAV_ITEMS: NavItem[] = [
  { path: '/', label: 'Dashboard', icon: <LayoutDashboard size={15} /> },
  {
    path: '/incoherences',
    label: 'Incoerenze',
    icon: <AlertTriangle size={15} />,
    badge: undefined,
    badgeColor: 'rgba(239,68,68,.2)',
  },
  {
    path: '/hitl',
    label: 'Coda HITL',
    icon: <ClipboardList size={15} />,
    badge: undefined,
    badgeColor: 'rgba(234,179,8,.15)',
  },
  { path: '/audit', label: 'Audit Trail', icon: <ShieldCheck size={15} /> },
]

export function Sidebar() {
  return (
    <aside
      style={{
        width: 'var(--sidebar-width)',
        background: 'var(--sidebar-bg)',
        borderRight: '1px solid var(--sidebar-border)',
        backdropFilter: 'blur(20px)',
        display: 'flex',
        flexDirection: 'column',
        flexShrink: 0,
        height: '100vh',
      }}
    >
      {/* Logo */}
      <div style={{ padding: '20px 16px 16px', borderBottom: '1px solid rgba(129,140,248,0.1)', display: 'flex', alignItems: 'center', gap: 10 }}>
        <div style={{ width: 32, height: 32, background: 'linear-gradient(135deg, #818cf8, #a78bfa)', borderRadius: 8, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 16, boxShadow: '0 0 20px rgba(129,140,248,0.3)', flexShrink: 0 }}>
          ⚡
        </div>
        <div>
          <div style={{ fontSize: 13, fontWeight: 700, color: '#f1f5f9', letterSpacing: '0.3px' }}>CCI / AVCS</div>
          <div style={{ fontSize: 9, color: 'rgba(165,180,252,0.5)', letterSpacing: '1px', textTransform: 'uppercase', marginTop: 1 }}>Coherence Engine</div>
        </div>
      </div>

      {/* Status */}
      <div style={{ margin: '12px 16px 0' }}>
        <div style={{ background: 'rgba(34,197,94,0.1)', border: '1px solid rgba(34,197,94,0.2)', borderRadius: 6, padding: '6px 10px', display: 'flex', alignItems: 'center', gap: 6, fontSize: 10, color: 'rgba(74,222,128,0.9)' }}>
          <div style={{ width: 6, height: 6, borderRadius: '50%', background: '#22c55e', boxShadow: '0 0 8px #22c55e', animation: 'pulse 2s infinite' }} />
          Sistema operativo
        </div>
      </div>

      {/* Nav */}
      <nav style={{ padding: '16px 8px 0', flex: 1 }}>
        <div style={{ fontSize: 9, color: 'var(--text-dim)', letterSpacing: '1.5px', textTransform: 'uppercase', padding: '0 8px 6px' }}>Navigazione</div>
        {NAV_ITEMS.map((item) => (
          <NavLink
            key={item.path}
            to={item.path}
            end={item.path === '/'}
            style={({ isActive }) => ({
              display: 'flex',
              alignItems: 'center',
              gap: 10,
              padding: '8px 12px',
              borderRadius: 8,
              fontSize: 13,
              fontWeight: 500,
              color: isActive ? '#a5b4fc' : 'var(--text-secondary)',
              background: isActive ? 'rgba(129,140,248,0.15)' : 'transparent',
              boxShadow: isActive ? 'inset 3px 0 0 #818cf8' : 'none',
              textDecoration: 'none',
              marginBottom: 2,
              transition: 'all 0.15s',
            })}
          >
            {item.icon}
            <span style={{ flex: 1 }}>{item.label}</span>
          </NavLink>
        ))}
      </nav>

      {/* Footer */}
      <div style={{ padding: '12px 16px', borderTop: '1px solid rgba(129,140,248,0.1)', fontSize: 9, color: 'var(--text-dim)', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <span>v0.1.0 · hera_it</span>
      </div>

      <style>{`
        @keyframes pulse { 0%,100%{opacity:1} 50%{opacity:.5} }
      `}</style>
    </aside>
  )
}
```

- [ ] **Step 5: Crea main.tsx**

```typescript
// frontend/src/main.tsx
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { createBrowserRouter, RouterProvider } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ReactQueryDevtools } from '@tanstack/react-query-devtools'
import { Toaster } from 'sonner'
import './index.css'
import { App } from './app'
import { Dashboard } from './pages/dashboard'
import { Incoherences } from './pages/incoherences'
import { IncoherenceDetail } from './pages/incoherence-detail'
import { HitlQueue } from './pages/hitl-queue'
import { HitlAction } from './pages/hitl-action'
import { Audit } from './pages/audit'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { staleTime: 30_000, retry: 1 },
  },
})

const router = createBrowserRouter([
  {
    path: '/',
    element: <App />,
    children: [
      { index: true, element: <Dashboard /> },
      { path: 'incoherences', element: <Incoherences /> },
      { path: 'incoherences/:id', element: <IncoherenceDetail /> },
      { path: 'hitl', element: <HitlQueue /> },
      { path: 'hitl/:actionId', element: <HitlAction /> },
      { path: 'audit', element: <Audit /> },
    ],
  },
])

const root = document.getElementById('root')
if (!root) throw new Error('Root element not found')

createRoot(root).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
      <Toaster position="top-right" richColors />
      <ReactQueryDevtools initialIsOpen={false} />
    </QueryClientProvider>
  </StrictMode>
)
```

- [ ] **Step 6: Crea app.tsx**

```typescript
// frontend/src/app.tsx
import { Outlet } from 'react-router-dom'
import { Sidebar } from './components/sidebar'

export function App() {
  return (
    <div style={{ display: 'flex', height: '100vh', overflow: 'hidden' }}>
      <Sidebar />
      <main style={{ flex: 1, overflowY: 'auto', padding: '24px 28px' }}>
        <Outlet />
      </main>
    </div>
  )
}
```

- [ ] **Step 7: Crea stub pages (per far compilare main.tsx)**

```bash
mkdir -p frontend/src/pages
```

Crea file stub per ogni page (verranno implementate nei task successivi):

```typescript
// frontend/src/pages/dashboard.tsx
export function Dashboard() { return <div>Dashboard</div> }
```
```typescript
// frontend/src/pages/incoherences.tsx
export function Incoherences() { return <div>Incoherences</div> }
```
```typescript
// frontend/src/pages/incoherence-detail.tsx
export function IncoherenceDetail() { return <div>Detail</div> }
```
```typescript
// frontend/src/pages/hitl-queue.tsx
export function HitlQueue() { return <div>HITL Queue</div> }
```
```typescript
// frontend/src/pages/hitl-action.tsx
export function HitlAction() { return <div>HITL Action</div> }
```
```typescript
// frontend/src/pages/audit.tsx
export function Audit() { return <div>Audit</div> }
```

- [ ] **Step 8: Esegui i test**

```bash
cd frontend
pnpm test
# Atteso: sidebar test 3 passed + lib test 8 passed
```

- [ ] **Step 9: Verifica che il dev server si avvii**

```bash
cd frontend
pnpm dev
# Atteso: Vite v6.x  Local: http://localhost:5173/  (senza errori TypeScript)
# Ctrl+C per fermare
```

- [ ] **Step 10: Commit**

```bash
git add frontend/src/
git commit -m "feat(frontend): add design system CSS, App layout, Sidebar, and page stubs"
```

---

## Task 7: KPI Strip component

**Files:**
- Create: `frontend/src/components/kpi-strip.tsx`
- Create: `frontend/src/tests/kpi-strip.test.tsx`

- [ ] **Step 1: Scrivi il test**

```typescript
// frontend/src/tests/kpi-strip.test.tsx
import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { KpiStrip } from '@/components/kpi-strip'

describe('KpiStrip', () => {
  it('renders incoherence count', () => {
    render(<KpiStrip incoherences={4} hitlPending={2} auditOk={true} loading={false} />)
    expect(screen.getByText('4')).toBeInTheDocument()
    expect(screen.getByText('Incoerenze')).toBeInTheDocument()
  })

  it('renders hitl pending count', () => {
    render(<KpiStrip incoherences={4} hitlPending={2} auditOk={true} loading={false} />)
    expect(screen.getByText('2')).toBeInTheDocument()
    expect(screen.getByText('HITL in attesa')).toBeInTheDocument()
  })

  it('shows OK when audit chain is valid', () => {
    render(<KpiStrip incoherences={4} hitlPending={2} auditOk={true} loading={false} />)
    expect(screen.getByText('✓ OK')).toBeInTheDocument()
  })

  it('shows skeleton placeholders when loading', () => {
    const { container } = render(<KpiStrip incoherences={0} hitlPending={0} auditOk={true} loading={true} />)
    expect(container.querySelectorAll('.animate-pulse').length).toBeGreaterThan(0)
  })
})
```

- [ ] **Step 2: Verifica che il test fallisca**

```bash
cd frontend && pnpm test src/tests/kpi-strip.test.tsx
# Atteso: Cannot find module '@/components/kpi-strip'
```

- [ ] **Step 3: Implementa kpi-strip.tsx**

```typescript
// frontend/src/components/kpi-strip.tsx

interface KpiStripProps {
  incoherences: number
  hitlPending: number
  auditOk: boolean
  loading: boolean
}

interface KpiCardProps {
  label: string
  value: string | number
  sub: string
  barColor: string
  valueColor: string
  loading: boolean
}

function KpiCard({ label, value, sub, barColor, valueColor, loading }: KpiCardProps) {
  return (
    <div
      style={{
        background: 'var(--card-bg)',
        border: '1px solid var(--card-border)',
        borderRadius: 12,
        overflow: 'hidden',
        backdropFilter: 'blur(8px)',
        position: 'relative',
      }}
    >
      <div style={{ height: 2, background: `linear-gradient(90deg, ${barColor}, transparent)` }} />
      <div style={{ padding: 16 }}>
        <div style={{ fontSize: 10, color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '1px', marginBottom: 8 }}>
          {label}
        </div>
        {loading ? (
          <div className="animate-pulse" style={{ height: 36, background: 'rgba(255,255,255,0.08)', borderRadius: 4, marginBottom: 8 }} />
        ) : (
          <div style={{ fontSize: 28, fontWeight: 700, color: valueColor, fontVariantNumeric: 'tabular-nums' }}>
            {value}
          </div>
        )}
        <div style={{ fontSize: 10, color: 'var(--text-dim)', marginTop: 4 }}>{sub}</div>
      </div>
    </div>
  )
}

export function KpiStrip({ incoherences, hitlPending, auditOk, loading }: KpiStripProps) {
  return (
    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 14, marginBottom: 24 }}>
      <KpiCard
        label="Incoerenze"
        value={incoherences}
        sub="Rilevate"
        barColor="var(--color-critical)"
        valueColor="#f87171"
        loading={loading}
      />
      <KpiCard
        label="HITL in attesa"
        value={hitlPending}
        sub="Approvazione richiesta"
        barColor="var(--color-medium)"
        valueColor="#fcd34d"
        loading={loading}
      />
      <KpiCard
        label="Audit chain"
        value={auditOk ? '✓ OK' : '✗ ERR'}
        sub="Hash chain integra"
        barColor="var(--color-ok)"
        valueColor={auditOk ? '#4ade80' : '#f87171'}
        loading={loading}
      />
    </div>
  )
}
```

- [ ] **Step 4: Esegui i test**

```bash
cd frontend && pnpm test src/tests/kpi-strip.test.tsx
# Atteso: 4 passed
```

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/kpi-strip.tsx frontend/src/tests/kpi-strip.test.tsx
git commit -m "feat(frontend): add KpiStrip component with Bold Modern design"
```

---

## Task 8: IncoherenceCard component

**Files:**
- Create: `frontend/src/components/incoherence-card.tsx`
- Create: `frontend/src/tests/incoherence-card.test.tsx`

- [ ] **Step 1: Scrivi il test**

```typescript
// frontend/src/tests/incoherence-card.test.tsx
import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { IncoherenceCard } from '@/components/incoherence-card'
import type { Incoherence } from '@/lib/types'

const mockIncoherence: Incoherence = {
  id: 'abc123',
  domain: 'hera_it',
  rule_id: 'R001',
  severity: 'CRITICAL',
  description: 'Azure commitment supera allocazione CTO',
  detected_at: '2026-06-06T10:00:00Z',
  impact_eur: 80000,
  evidence_chunks: ['hera_azure_1#chunk_3'],
  explanation: null,
  citations: [],
  grounding_verified: null,
}

function renderCard(props?: Partial<typeof mockIncoherence>) {
  return render(
    <MemoryRouter>
      <IncoherenceCard incoherence={{ ...mockIncoherence, ...props }} />
    </MemoryRouter>
  )
}

describe('IncoherenceCard', () => {
  it('renders rule_id in monospace', () => {
    renderCard()
    expect(screen.getByText('R001')).toBeInTheDocument()
  })

  it('renders severity badge', () => {
    renderCard()
    expect(screen.getByText('CRITICAL')).toBeInTheDocument()
  })

  it('renders description', () => {
    renderCard()
    expect(screen.getByText(/Azure commitment/)).toBeInTheDocument()
  })

  it('renders formatted impact', () => {
    renderCard()
    expect(screen.getByText('+80.000 €')).toBeInTheDocument()
  })

  it('renders link to detail page', () => {
    renderCard()
    const link = screen.getByRole('link')
    expect(link).toHaveAttribute('href', '/incoherences/abc123')
  })

  it('renders HIGH severity with orange badge', () => {
    renderCard({ severity: 'HIGH', rule_id: 'R002' })
    expect(screen.getByText('HIGH')).toBeInTheDocument()
  })
})
```

- [ ] **Step 2: Verifica che il test fallisca**

```bash
cd frontend && pnpm test src/tests/incoherence-card.test.tsx
# Atteso: Cannot find module '@/components/incoherence-card'
```

- [ ] **Step 3: Implementa incoherence-card.tsx**

```typescript
// frontend/src/components/incoherence-card.tsx
import { Link } from 'react-router-dom'
import type { Incoherence, Severity } from '@/lib/types'
import { formatEur } from '@/lib/utils'

const SEVERITY_STYLE: Record<Severity, { borderColor: string; badgeBg: string; badgeColor: string; badgeBorder: string }> = {
  CRITICAL: { borderColor: '#ef4444', badgeBg: 'rgba(239,68,68,.2)', badgeColor: '#fca5a5', badgeBorder: 'rgba(239,68,68,.35)' },
  HIGH:     { borderColor: '#f97316', badgeBg: 'rgba(249,115,22,.18)', badgeColor: '#fdba74', badgeBorder: 'rgba(249,115,22,.3)' },
  MEDIUM:   { borderColor: '#f59e0b', badgeBg: 'rgba(245,158,11,.18)', badgeColor: '#fcd34d', badgeBorder: 'rgba(245,158,11,.3)' },
  LOW:      { borderColor: '#818cf8', badgeBg: 'rgba(129,140,248,.18)', badgeColor: '#a5b4fc', badgeBorder: 'rgba(129,140,248,.3)' },
}

export function IncoherenceCard({ incoherence }: { incoherence: Incoherence }) {
  const style = SEVERITY_STYLE[incoherence.severity]

  return (
    <Link
      to={`/incoherences/${incoherence.id}`}
      style={{ textDecoration: 'none' }}
    >
      <div
        style={{
          background: 'rgba(255,255,255,0.035)',
          border: '1px solid rgba(255,255,255,0.07)',
          borderRadius: 10,
          padding: '12px 14px',
          marginBottom: 8,
          display: 'flex',
          alignItems: 'center',
          gap: 12,
          cursor: 'pointer',
          transition: 'all 0.15s',
          position: 'relative',
          overflow: 'hidden',
        }}
      >
        {/* Left border */}
        <div style={{ position: 'absolute', left: 0, top: 0, bottom: 0, width: 3, background: style.borderColor, borderRadius: '10px 0 0 10px' }} />

        {/* Body */}
        <div style={{ flex: 1, minWidth: 0, paddingLeft: 4 }}>
          <div style={{ fontSize: 11, fontWeight: 700, color: '#e2e8f0', letterSpacing: '0.3px', fontFamily: "'SF Mono', monospace" }}>
            {incoherence.rule_id}
          </div>
          <div style={{ fontSize: 11, color: 'var(--text-secondary)', marginTop: 2, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
            {incoherence.description}
          </div>
        </div>

        {/* Delta */}
        <div style={{ fontSize: 10, fontWeight: 700, color: 'rgba(248,113,113,0.8)', flexShrink: 0, fontFamily: 'monospace' }}>
          {formatEur(incoherence.impact_eur)}
        </div>

        {/* Badge */}
        <div style={{ fontSize: 9, fontWeight: 700, letterSpacing: '0.5px', padding: '3px 8px', borderRadius: 20, flexShrink: 0, background: style.badgeBg, color: style.badgeColor, border: `1px solid ${style.badgeBorder}` }}>
          {incoherence.severity}
        </div>
      </div>
    </Link>
  )
}
```

- [ ] **Step 4: Esegui i test**

```bash
cd frontend && pnpm test src/tests/incoherence-card.test.tsx
# Atteso: 6 passed
```

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/incoherence-card.tsx frontend/src/tests/incoherence-card.test.tsx
git commit -m "feat(frontend): add IncoherenceCard component"
```

---

## Task 9: ChunkCitation + ExplanationBlock components

**Files:**
- Create: `frontend/src/components/chunk-citation.tsx`
- Create: `frontend/src/components/explanation-block.tsx`
- Create: `frontend/src/tests/explanation-block.test.tsx`

- [ ] **Step 1: Scrivi i test**

```typescript
// frontend/src/tests/explanation-block.test.tsx
import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { ExplanationBlock } from '@/components/explanation-block'

describe('ExplanationBlock', () => {
  it('renders text with citation badges', () => {
    render(
      <ExplanationBlock
        explanation="Azure commitment [source: hera_azure_1#chunk_3] supera allocazione."
        citations={['hera_azure_1#chunk_3']}
        groundingVerified={true}
      />
    )
    expect(screen.getByText(/Azure commitment/)).toBeInTheDocument()
    expect(screen.getByText('hera_azure_1#chunk_3')).toBeInTheDocument()
  })

  it('shows verified badge when grounding is confirmed', () => {
    render(
      <ExplanationBlock
        explanation="Testo [source: chunk_1]."
        citations={['chunk_1']}
        groundingVerified={true}
      />
    )
    expect(screen.getByText(/Grounding verificato/i)).toBeInTheDocument()
  })

  it('renders citations list at the bottom', () => {
    render(
      <ExplanationBlock
        explanation="Testo [source: doc_1#chunk_2]."
        citations={['doc_1#chunk_2']}
        groundingVerified={true}
      />
    )
    expect(screen.getAllByText('doc_1#chunk_2').length).toBeGreaterThanOrEqual(1)
  })
})
```

- [ ] **Step 2: Verifica che il test fallisca**

```bash
cd frontend && pnpm test src/tests/explanation-block.test.tsx
# Atteso: Cannot find module '@/components/explanation-block'
```

- [ ] **Step 3: Implementa chunk-citation.tsx**

```typescript
// frontend/src/components/chunk-citation.tsx
export function ChunkCitation({ chunkId }: { chunkId: string }) {
  return (
    <span
      style={{
        display: 'inline-block',
        fontFamily: "'SF Mono', monospace",
        fontSize: 10,
        padding: '1px 6px',
        borderRadius: 4,
        background: 'rgba(129,140,248,0.1)',
        color: 'var(--color-primary)',
        border: '1px solid rgba(129,140,248,0.25)',
        cursor: 'default',
      }}
      title={chunkId}
    >
      {chunkId}
    </span>
  )
}
```

- [ ] **Step 4: Implementa explanation-block.tsx**

```typescript
// frontend/src/components/explanation-block.tsx
import { CheckCircle2 } from 'lucide-react'
import { ChunkCitation } from './chunk-citation'

function renderTextWithCitations(text: string): React.ReactNode[] {
  const parts = text.split(/(\[source:\s*[^\]]+\])/g)
  return parts.map((part, i) => {
    const match = part.match(/\[source:\s*([^\]]+)\]/)
    if (match) {
      return <ChunkCitation key={i} chunkId={match[1]!.trim()} />
    }
    return <span key={i}>{part}</span>
  })
}

interface ExplanationBlockProps {
  explanation: string
  citations: string[]
  groundingVerified: boolean
}

export function ExplanationBlock({ explanation, citations, groundingVerified }: ExplanationBlockProps) {
  return (
    <div style={{ background: 'var(--card-bg)', border: '1px solid var(--card-border)', borderRadius: 10, padding: 16 }}>
      {groundingVerified && (
        <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 10, fontSize: 10, color: '#4ade80' }}>
          <CheckCircle2 size={12} />
          Grounding verificato · tutte le citazioni da documenti indicizzati
        </div>
      )}

      <p style={{ fontSize: 13, lineHeight: 1.7, color: '#e2e8f0', margin: 0 }}>
        {renderTextWithCitations(explanation)}
      </p>

      {citations.length > 0 && (
        <div style={{ marginTop: 12, paddingTop: 12, borderTop: '1px solid rgba(255,255,255,0.06)' }}>
          <div style={{ fontSize: 9, color: 'var(--text-dim)', textTransform: 'uppercase', letterSpacing: '1px', marginBottom: 6 }}>Fonti</div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
            {citations.map((c) => (
              <ChunkCitation key={c} chunkId={c} />
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
```

- [ ] **Step 5: Esegui i test**

```bash
cd frontend && pnpm test src/tests/explanation-block.test.tsx
# Atteso: 3 passed
```

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/chunk-citation.tsx frontend/src/components/explanation-block.tsx frontend/src/tests/explanation-block.test.tsx
git commit -m "feat(frontend): add ChunkCitation and ExplanationBlock components"
```

---

## Task 10: GenerateExplanationButton component

**Files:**
- Create: `frontend/src/components/generate-explanation-button.tsx`
- Create: `frontend/src/tests/generate-explanation-button.test.tsx`

- [ ] **Step 1: Scrivi il test**

```typescript
// frontend/src/tests/generate-explanation-button.test.tsx
import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { GenerateExplanationButton } from '@/components/generate-explanation-button'

describe('GenerateExplanationButton', () => {
  it('renders the button text', () => {
    render(<GenerateExplanationButton onGenerate={vi.fn()} isPending={false} />)
    expect(screen.getByRole('button', { name: /genera spiegazione/i })).toBeInTheDocument()
  })

  it('calls onGenerate when clicked', async () => {
    const onGenerate = vi.fn()
    render(<GenerateExplanationButton onGenerate={onGenerate} isPending={false} />)
    await userEvent.click(screen.getByRole('button'))
    expect(onGenerate).toHaveBeenCalledOnce()
  })

  it('disables button and shows loading text when pending', () => {
    render(<GenerateExplanationButton onGenerate={vi.fn()} isPending={true} />)
    const btn = screen.getByRole('button')
    expect(btn).toBeDisabled()
    expect(screen.getByText(/generazione/i)).toBeInTheDocument()
  })
})
```

- [ ] **Step 2: Verifica che il test fallisca**

```bash
cd frontend && pnpm test src/tests/generate-explanation-button.test.tsx
# Atteso: Cannot find module '@/components/generate-explanation-button'
```

- [ ] **Step 3: Implementa generate-explanation-button.tsx**

```typescript
// frontend/src/components/generate-explanation-button.tsx
import { Sparkles, Loader2 } from 'lucide-react'

interface GenerateExplanationButtonProps {
  onGenerate: () => void
  isPending: boolean
}

export function GenerateExplanationButton({ onGenerate, isPending }: GenerateExplanationButtonProps) {
  return (
    <div
      style={{
        background: 'rgba(129,140,248,0.05)',
        border: '1px dashed rgba(129,140,248,0.25)',
        borderRadius: 10,
        padding: 20,
        textAlign: 'center',
      }}
    >
      <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginBottom: 12 }}>
        Nessuna spiegazione generata per questa incoerenza.
      </div>
      <button
        onClick={onGenerate}
        disabled={isPending}
        style={{
          display: 'inline-flex',
          alignItems: 'center',
          gap: 8,
          padding: '8px 16px',
          borderRadius: 8,
          border: '1px solid rgba(129,140,248,0.3)',
          background: 'rgba(129,140,248,0.1)',
          color: '#a5b4fc',
          fontSize: 13,
          fontWeight: 500,
          cursor: isPending ? 'not-allowed' : 'pointer',
          opacity: isPending ? 0.7 : 1,
          transition: 'all 0.15s',
        }}
      >
        {isPending ? (
          <>
            <Loader2 size={14} style={{ animation: 'spin 1s linear infinite' }} />
            Generazione in corso…
          </>
        ) : (
          <>
            <Sparkles size={14} />
            Genera spiegazione
          </>
        )}
      </button>
      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
    </div>
  )
}
```

- [ ] **Step 4: Esegui i test**

```bash
cd frontend && pnpm test src/tests/generate-explanation-button.test.tsx
# Atteso: 3 passed
```

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/generate-explanation-button.tsx frontend/src/tests/generate-explanation-button.test.tsx
git commit -m "feat(frontend): add GenerateExplanationButton component"
```

---

## Task 11: TanStack Query hooks

**Files:**
- Create: `frontend/src/hooks/use-incoherences.ts`
- Create: `frontend/src/hooks/use-incoherence.ts`
- Create: `frontend/src/hooks/use-explanation.ts`
- Create: `frontend/src/hooks/use-hitl-queue.ts`
- Create: `frontend/src/hooks/use-audit-events.ts`

_(Questi hook sono testati indirettamente nei test E2E e nelle pagine — i test unitari con mock della query non aggiungono valore significativo rispetto ai test di integrazione)_

- [ ] **Step 1: Crea use-incoherences.ts**

```typescript
// frontend/src/hooks/use-incoherences.ts
import { useQuery } from '@tanstack/react-query'
import { apiFetch } from '@/lib/api'
import type { Incoherence, PagedResponse } from '@/lib/types'

interface IncoherenceFilters {
  domain?: string
  severity?: string
  page?: number
  size?: number
}

export function useIncoherences(filters: IncoherenceFilters = {}) {
  const params = new URLSearchParams()
  if (filters.domain) params.set('domain', filters.domain)
  if (filters.severity) params.set('severity', filters.severity)
  if (filters.page != null) params.set('page', String(filters.page))
  if (filters.size != null) params.set('size', String(filters.size))

  const qs = params.toString() ? `?${params.toString()}` : ''

  return useQuery({
    queryKey: ['incoherences', filters],
    queryFn: () => apiFetch<PagedResponse<Incoherence> | Incoherence[]>(`/incoherences${qs}`),
  })
}
```

- [ ] **Step 2: Crea use-incoherence.ts**

```typescript
// frontend/src/hooks/use-incoherence.ts
import { useQuery } from '@tanstack/react-query'
import { apiFetch } from '@/lib/api'
import type { Incoherence } from '@/lib/types'

export function useIncoherence(id: string) {
  return useQuery({
    queryKey: ['incoherence', id],
    queryFn: () => apiFetch<Incoherence>(`/incoherences/${id}`),
    enabled: Boolean(id),
  })
}
```

- [ ] **Step 3: Crea use-explanation.ts**

```typescript
// frontend/src/hooks/use-explanation.ts
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { apiFetch } from '@/lib/api'
import type { ExplanationOut } from '@/lib/types'

export function useExplanation(incoherenceId: string) {
  const qc = useQueryClient()

  return useMutation({
    mutationFn: () =>
      apiFetch<ExplanationOut>(`/incoherences/${incoherenceId}/explain`, { method: 'POST' }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['incoherence', incoherenceId] })
    },
  })
}
```

- [ ] **Step 4: Crea use-hitl-queue.ts**

```typescript
// frontend/src/hooks/use-hitl-queue.ts
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { apiFetch } from '@/lib/api'
import type { HitlAction } from '@/lib/types'

export function useHitlQueue() {
  return useQuery({
    queryKey: ['hitl-queue'],
    queryFn: () => apiFetch<HitlAction[]>('/hitl/queue'),
  })
}

export function useHitlAction(id: string) {
  return useQuery({
    queryKey: ['hitl-action', id],
    queryFn: () => apiFetch<HitlAction>(`/hitl/${id}`),
    enabled: Boolean(id),
  })
}

export function useApproveHitl() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, motivation }: { id: string; motivation: string }) =>
      apiFetch(`/hitl/${id}/approve`, {
        method: 'POST',
        body: JSON.stringify({ motivation }),
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['hitl-queue'] })
      qc.invalidateQueries({ queryKey: ['incoherences'] })
    },
  })
}

export function useRejectHitl() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, motivation }: { id: string; motivation: string }) =>
      apiFetch(`/hitl/${id}/reject`, {
        method: 'POST',
        body: JSON.stringify({ motivation }),
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['hitl-queue'] })
    },
  })
}
```

- [ ] **Step 5: Crea use-audit-events.ts**

```typescript
// frontend/src/hooks/use-audit-events.ts
import { useQuery } from '@tanstack/react-query'
import { apiFetch } from '@/lib/api'
import type { AuditEvent, AuditChainStatus } from '@/lib/types'

export function useAuditEvents(limit = 50) {
  return useQuery({
    queryKey: ['audit-events', limit],
    queryFn: () => apiFetch<AuditEvent[]>(`/audit/events?limit=${limit}`),
    staleTime: 60_000,
  })
}

export function useAuditChainStatus() {
  return useQuery({
    queryKey: ['audit-chain-status'],
    queryFn: () => apiFetch<AuditChainStatus>('/audit/chain-status'),
    staleTime: 60_000,
  })
}
```

- [ ] **Step 6: Verifica che TypeScript compili senza errori**

```bash
cd frontend && npx tsc --noEmit
# Atteso: 0 errori
```

- [ ] **Step 7: Commit**

```bash
git add frontend/src/hooks/
git commit -m "feat(frontend): add TanStack Query hooks for all API endpoints"
```

---

## Task 12: Dashboard page

**Files:**
- Modify: `frontend/src/pages/dashboard.tsx`

- [ ] **Step 1: Implementa la Dashboard**

```typescript
// frontend/src/pages/dashboard.tsx
import { KpiStrip } from '@/components/kpi-strip'
import { IncoherenceCard } from '@/components/incoherence-card'
import { useIncoherences } from '@/hooks/use-incoherences'
import { useHitlQueue } from '@/hooks/use-hitl-queue'
import { useAuditChainStatus } from '@/hooks/use-audit-events'

export function Dashboard() {
  const { data: incoData, isLoading: incoLoading } = useIncoherences({ size: 4 })
  const { data: hitlData } = useHitlQueue()
  const { data: auditData } = useAuditChainStatus()

  const incoList = Array.isArray(incoData)
    ? incoData
    : (incoData?.items ?? [])

  const incoCount = incoList.length
  const hitlCount = hitlData?.length ?? 0
  const auditOk = auditData?.valid ?? true

  return (
    <div>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: 24 }}>
        <div>
          <h1 style={{ fontSize: 22, fontWeight: 700, color: '#f1f5f9', letterSpacing: '-0.3px', margin: 0 }}>Dashboard</h1>
          <p style={{ fontSize: 12, color: 'var(--text-secondary)', marginTop: 4 }}>
            Continuous Coherence Intelligence · {new Date().toLocaleDateString('it-IT', { day: 'numeric', month: 'long', year: 'numeric' })}
          </p>
        </div>
      </div>

      {/* KPI */}
      <KpiStrip
        incoherences={incoCount}
        hitlPending={hitlCount}
        auditOk={auditOk}
        loading={incoLoading}
      />

      {/* Recent incoherences */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 }}>
        <div style={{ fontSize: 13, fontWeight: 600, color: '#c7d2fe', letterSpacing: '0.2px' }}>
          Non conformità rilevate
        </div>
        <a href="/incoherences" style={{ fontSize: 11, color: 'rgba(129,140,248,0.6)', cursor: 'pointer', textDecoration: 'none' }}>
          Vedi tutte →
        </a>
      </div>

      {incoLoading && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          {[1, 2, 3].map((i) => (
            <div key={i} className="animate-pulse" style={{ height: 56, background: 'var(--card-bg)', borderRadius: 10 }} />
          ))}
        </div>
      )}

      {!incoLoading && incoList.length === 0 && (
        <div style={{ textAlign: 'center', padding: '32px 0', color: 'var(--text-dim)', fontSize: 13 }}>
          Nessuna incoerenza rilevata ✓
        </div>
      )}

      {!incoLoading && incoList.map((inc) => (
        <IncoherenceCard key={inc.id} incoherence={inc} />
      ))}
    </div>
  )
}
```

- [ ] **Step 2: Verifica TypeScript**

```bash
cd frontend && npx tsc --noEmit
# Atteso: 0 errori
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/pages/dashboard.tsx
git commit -m "feat(frontend): implement Dashboard page with KPI strip and recent incoherences"
```

---

## Task 13: Incoherences list page

**Files:**
- Modify: `frontend/src/pages/incoherences.tsx`

- [ ] **Step 1: Implementa la pagina lista**

```typescript
// frontend/src/pages/incoherences.tsx
import { useState } from 'react'
import { AlertTriangle } from 'lucide-react'
import { IncoherenceCard } from '@/components/incoherence-card'
import { useIncoherences } from '@/hooks/use-incoherences'
import type { Severity } from '@/lib/types'

const SEVERITY_OPTIONS: Array<{ value: string; label: string }> = [
  { value: '', label: 'Tutte le severity' },
  { value: 'CRITICAL', label: '🔴 CRITICAL' },
  { value: 'HIGH', label: '🟠 HIGH' },
  { value: 'MEDIUM', label: '🟡 MEDIUM' },
  { value: 'LOW', label: '🔵 LOW' },
]

export function Incoherences() {
  const [severity, setSeverity] = useState('')

  const { data, isLoading } = useIncoherences({
    severity: severity || undefined,
    size: 50,
  })

  const incoList = Array.isArray(data) ? data : (data?.items ?? [])

  return (
    <div>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: 24 }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <AlertTriangle size={18} color="var(--color-critical)" />
            <h1 style={{ fontSize: 22, fontWeight: 700, color: '#f1f5f9', letterSpacing: '-0.3px', margin: 0 }}>Incoerenze</h1>
          </div>
          <p style={{ fontSize: 12, color: 'var(--text-secondary)', marginTop: 4 }}>
            Non conformità rilevate dalla Coherence Engine
          </p>
        </div>

        {/* Filtro */}
        <select
          value={severity}
          onChange={(e) => setSeverity(e.target.value)}
          style={{
            background: 'var(--card-bg)',
            border: '1px solid var(--card-border)',
            borderRadius: 8,
            padding: '6px 12px',
            color: '#e2e8f0',
            fontSize: 12,
            cursor: 'pointer',
          }}
        >
          {SEVERITY_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value}>{opt.label}</option>
          ))}
        </select>
      </div>

      {/* Risultati */}
      <div style={{ fontSize: 11, color: 'var(--text-dim)', marginBottom: 12 }}>
        {isLoading ? 'Caricamento…' : `${incoList.length} incoerenz${incoList.length === 1 ? 'a' : 'e'}`}
      </div>

      {isLoading && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="animate-pulse" style={{ height: 56, background: 'var(--card-bg)', borderRadius: 10 }} />
          ))}
        </div>
      )}

      {!isLoading && incoList.length === 0 && (
        <div style={{ textAlign: 'center', padding: '48px 0', color: 'var(--text-dim)', fontSize: 13 }}>
          Nessuna incoerenza trovata per i filtri selezionati.
        </div>
      )}

      {!isLoading && incoList.map((inc) => (
        <IncoherenceCard key={inc.id} incoherence={inc} />
      ))}
    </div>
  )
}
```

- [ ] **Step 2: Verifica TypeScript**

```bash
cd frontend && npx tsc --noEmit
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/pages/incoherences.tsx
git commit -m "feat(frontend): implement Incoherences list page with severity filter"
```

---

## Task 14: IncoherenceDetail page

**Files:**
- Modify: `frontend/src/pages/incoherence-detail.tsx`

- [ ] **Step 1: Implementa la pagina dettaglio**

```typescript
// frontend/src/pages/incoherence-detail.tsx
import { useParams, Link } from 'react-router-dom'
import { toast } from 'sonner'
import { ArrowLeft } from 'lucide-react'
import { useIncoherence } from '@/hooks/use-incoherence'
import { useExplanation } from '@/hooks/use-explanation'
import { ExplanationBlock } from '@/components/explanation-block'
import { GenerateExplanationButton } from '@/components/generate-explanation-button'
import { ChunkCitation } from '@/components/chunk-citation'
import { formatDate, SEVERITY_CONFIG } from '@/lib/utils'
import type { Severity } from '@/lib/types'

export function IncoherenceDetail() {
  const { id } = useParams<{ id: string }>()
  const { data: inco, isLoading } = useIncoherence(id ?? '')
  const explanation = useExplanation(id ?? '')

  const handleGenerate = () => {
    explanation.mutate(undefined, {
      onError: (err) => {
        const msg = err instanceof Error ? err.message : 'Errore sconosciuto'
        toast.error(msg.includes('422') ? 'Spiegazione non disponibile: citazioni insufficienti' : `Errore: ${msg}`)
      },
    })
  }

  if (isLoading) {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
        {[1, 2, 3].map((i) => (
          <div key={i} className="animate-pulse" style={{ height: 80, background: 'var(--card-bg)', borderRadius: 10 }} />
        ))}
      </div>
    )
  }

  if (!inco) {
    return <div style={{ color: 'var(--text-secondary)', fontSize: 13 }}>Incoerenza non trovata.</div>
  }

  const severityStyle = SEVERITY_CONFIG[inco.severity as Severity]

  return (
    <div>
      {/* Back */}
      <Link to="/incoherences" style={{ display: 'inline-flex', alignItems: 'center', gap: 6, fontSize: 12, color: 'var(--text-secondary)', textDecoration: 'none', marginBottom: 20 }}>
        <ArrowLeft size={14} />
        Tutte le incoerenze
      </Link>

      {/* Header */}
      <div style={{ marginBottom: 24 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 8 }}>
          <h1 style={{ fontSize: 20, fontWeight: 700, color: '#f1f5f9', fontFamily: "'SF Mono', monospace", margin: 0 }}>
            {inco.rule_id}
          </h1>
          <span style={{ fontSize: 10, fontWeight: 700, letterSpacing: '0.5px', padding: '3px 10px', borderRadius: 20, background: `${severityStyle.color}33`, color: severityStyle.color, border: `1px solid ${severityStyle.color}55` }}>
            {inco.severity}
          </span>
        </div>
        <p style={{ fontSize: 14, color: 'var(--text-secondary)', margin: 0 }}>{inco.description}</p>
        <div style={{ fontSize: 11, color: 'var(--text-dim)', marginTop: 8 }}>
          Rilevata {formatDate(inco.detected_at)} · Dominio: {inco.domain} · Impatto: {Math.abs(inco.impact_eur).toLocaleString('it-IT')} EUR
        </div>
      </div>

      {/* Evidence chunks */}
      {inco.evidence_chunks.length > 0 && (
        <div style={{ marginBottom: 20 }}>
          <div style={{ fontSize: 11, color: 'var(--text-dim)', textTransform: 'uppercase', letterSpacing: '1px', marginBottom: 8 }}>Chunk di evidenza</div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
            {inco.evidence_chunks.map((c) => <ChunkCitation key={c} chunkId={c} />)}
          </div>
        </div>
      )}

      {/* Explanation */}
      <div>
        <div style={{ fontSize: 13, fontWeight: 600, color: '#c7d2fe', marginBottom: 12 }}>Spiegazione con citazioni</div>
        {inco.explanation ? (
          <ExplanationBlock
            explanation={inco.explanation}
            citations={inco.citations}
            groundingVerified={inco.grounding_verified ?? false}
          />
        ) : (
          <GenerateExplanationButton
            onGenerate={handleGenerate}
            isPending={explanation.isPending}
          />
        )}
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Verifica TypeScript**

```bash
cd frontend && npx tsc --noEmit
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/pages/incoherence-detail.tsx
git commit -m "feat(frontend): implement IncoherenceDetail page with explanation flow"
```

---

## Task 15: HITL pages (queue + approval form)

**Files:**
- Modify: `frontend/src/pages/hitl-queue.tsx`
- Modify: `frontend/src/pages/hitl-action.tsx`

- [ ] **Step 1: Implementa HitlQueue**

```typescript
// frontend/src/pages/hitl-queue.tsx
import { Link } from 'react-router-dom'
import { ClipboardList, Clock } from 'lucide-react'
import { useHitlQueue } from '@/hooks/use-hitl-queue'
import { formatDate } from '@/lib/utils'

export function HitlQueue() {
  const { data: actions, isLoading } = useHitlQueue()

  return (
    <div>
      <div style={{ marginBottom: 24 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <ClipboardList size={18} color="var(--color-medium)" />
          <h1 style={{ fontSize: 22, fontWeight: 700, color: '#f1f5f9', letterSpacing: '-0.3px', margin: 0 }}>Coda HITL</h1>
        </div>
        <p style={{ fontSize: 12, color: 'var(--text-secondary)', marginTop: 4 }}>
          Azioni che richiedono approvazione umana (R6)
        </p>
      </div>

      {isLoading && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          {[1, 2].map((i) => <div key={i} className="animate-pulse" style={{ height: 80, background: 'var(--card-bg)', borderRadius: 10 }} />)}
        </div>
      )}

      {!isLoading && (!actions || actions.length === 0) && (
        <div style={{ textAlign: 'center', padding: '48px 0', color: 'var(--text-dim)', fontSize: 13 }}>
          Nessuna azione in attesa ✓
        </div>
      )}

      {!isLoading && actions?.map((action) => (
        <Link key={action.id} to={`/hitl/${action.id}`} style={{ textDecoration: 'none' }}>
          <div style={{ background: 'var(--card-bg)', border: '1px solid rgba(245,158,11,0.2)', borderRadius: 10, padding: '14px 16px', marginBottom: 8, cursor: 'pointer', transition: 'all 0.15s' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 6 }}>
              <span style={{ fontSize: 13, fontWeight: 600, color: '#f1f5f9' }}>{action.action_type}</span>
              <span style={{ display: 'flex', alignItems: 'center', gap: 4, fontSize: 10, color: '#fcd34d' }}>
                <Clock size={10} />
                In attesa
              </span>
            </div>
            <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginBottom: 6 }}>{action.description}</div>
            <div style={{ fontSize: 10, color: 'var(--text-dim)' }}>
              Creata {formatDate(action.created_at)} · Impatto: {action.impact}
            </div>
          </div>
        </Link>
      ))}
    </div>
  )
}
```

- [ ] **Step 2: Implementa HitlAction (form approvazione)**

```typescript
// frontend/src/pages/hitl-action.tsx
import { useState } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import { toast } from 'sonner'
import { ArrowLeft, CheckCircle2, XCircle } from 'lucide-react'
import { useHitlAction, useApproveHitl, useRejectHitl } from '@/hooks/use-hitl-queue'

const MIN_MOTIVATION_LEN = 20

export function HitlAction() {
  const { actionId } = useParams<{ actionId: string }>()
  const navigate = useNavigate()
  const { data: action, isLoading } = useHitlAction(actionId ?? '')
  const approve = useApproveHitl()
  const reject = useRejectHitl()
  const [motivation, setMotivation] = useState('')

  const isValid = motivation.trim().length >= MIN_MOTIVATION_LEN
  const isPending = approve.isPending || reject.isPending

  const handleApprove = () => {
    approve.mutate({ id: actionId!, motivation }, {
      onSuccess: () => { toast.success('Azione approvata'); navigate('/hitl') },
      onError: () => toast.error('Errore durante l\'approvazione'),
    })
  }

  const handleReject = () => {
    reject.mutate({ id: actionId!, motivation }, {
      onSuccess: () => { toast.success('Azione rifiutata'); navigate('/hitl') },
      onError: () => toast.error('Errore durante il rifiuto'),
    })
  }

  if (isLoading) return <div className="animate-pulse" style={{ height: 200, background: 'var(--card-bg)', borderRadius: 10 }} />
  if (!action) return <div style={{ color: 'var(--text-secondary)' }}>Azione non trovata.</div>

  return (
    <div>
      <Link to="/hitl" style={{ display: 'inline-flex', alignItems: 'center', gap: 6, fontSize: 12, color: 'var(--text-secondary)', textDecoration: 'none', marginBottom: 20 }}>
        <ArrowLeft size={14} />
        Coda HITL
      </Link>

      <h1 style={{ fontSize: 20, fontWeight: 700, color: '#f1f5f9', marginBottom: 8 }}>{action.action_type}</h1>
      <p style={{ fontSize: 13, color: 'var(--text-secondary)', marginBottom: 24 }}>{action.description}</p>

      <div style={{ background: 'var(--card-bg)', border: '1px solid var(--card-border)', borderRadius: 10, padding: 20, marginBottom: 20 }}>
        <label style={{ display: 'block', fontSize: 12, color: 'var(--text-secondary)', marginBottom: 8 }}>
          Motivazione <span style={{ color: 'var(--color-critical)' }}>*</span>
          <span style={{ color: 'var(--text-dim)', marginLeft: 4 }}>(min. {MIN_MOTIVATION_LEN} caratteri)</span>
        </label>
        <textarea
          value={motivation}
          onChange={(e) => setMotivation(e.target.value)}
          rows={4}
          placeholder="Descrivi la motivazione della tua decisione…"
          style={{ width: '100%', background: 'rgba(255,255,255,0.04)', border: '1px solid var(--card-border)', borderRadius: 8, padding: '10px 12px', color: '#e2e8f0', fontSize: 13, resize: 'vertical', fontFamily: 'inherit' }}
        />
        <div style={{ fontSize: 10, color: motivation.length < MIN_MOTIVATION_LEN ? '#f87171' : '#4ade80', marginTop: 4 }}>
          {motivation.length}/{MIN_MOTIVATION_LEN} caratteri minimi
        </div>
      </div>

      <div style={{ display: 'flex', gap: 12 }}>
        <button
          onClick={handleApprove}
          disabled={!isValid || isPending}
          style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '10px 20px', borderRadius: 8, border: '1px solid rgba(34,197,94,0.3)', background: 'rgba(34,197,94,0.1)', color: '#4ade80', fontSize: 13, fontWeight: 500, cursor: (!isValid || isPending) ? 'not-allowed' : 'pointer', opacity: (!isValid || isPending) ? 0.5 : 1 }}
        >
          <CheckCircle2 size={14} />
          Approva
        </button>

        <button
          onClick={handleReject}
          disabled={!isValid || isPending}
          style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '10px 20px', borderRadius: 8, border: '1px solid rgba(239,68,68,0.3)', background: 'rgba(239,68,68,0.1)', color: '#f87171', fontSize: 13, fontWeight: 500, cursor: (!isValid || isPending) ? 'not-allowed' : 'pointer', opacity: (!isValid || isPending) ? 0.5 : 1 }}
        >
          <XCircle size={14} />
          Rifiuta
        </button>
      </div>
    </div>
  )
}
```

- [ ] **Step 3: Verifica TypeScript**

```bash
cd frontend && npx tsc --noEmit
```

- [ ] **Step 4: Commit**

```bash
git add frontend/src/pages/hitl-queue.tsx frontend/src/pages/hitl-action.tsx
git commit -m "feat(frontend): implement HITL queue and action approval pages"
```

---

## Task 16: Audit page

**Files:**
- Modify: `frontend/src/pages/audit.tsx`

- [ ] **Step 1: Implementa la pagina Audit**

```typescript
// frontend/src/pages/audit.tsx
import { ShieldCheck, ShieldAlert } from 'lucide-react'
import { useAuditEvents, useAuditChainStatus } from '@/hooks/use-audit-events'
import { formatDate } from '@/lib/utils'

export function Audit() {
  const { data: events, isLoading: eventsLoading } = useAuditEvents(50)
  const { data: chainStatus } = useAuditChainStatus()

  const chainOk = chainStatus?.valid ?? null

  return (
    <div>
      <div style={{ marginBottom: 24 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <ShieldCheck size={18} color="var(--color-ok)" />
          <h1 style={{ fontSize: 22, fontWeight: 700, color: '#f1f5f9', letterSpacing: '-0.3px', margin: 0 }}>Audit Trail</h1>
        </div>
        <p style={{ fontSize: 12, color: 'var(--text-secondary)', marginTop: 4 }}>
          Log immutabile con hash chain SHA-256 (AI Act art. 12)
        </p>
      </div>

      {/* Chain status */}
      {chainStatus && (
        <div style={{ background: chainOk ? 'rgba(34,197,94,0.08)' : 'rgba(239,68,68,0.08)', border: `1px solid ${chainOk ? 'rgba(34,197,94,0.2)' : 'rgba(239,68,68,0.2)'}`, borderRadius: 10, padding: '12px 16px', marginBottom: 20, display: 'flex', alignItems: 'center', gap: 10 }}>
          {chainOk ? <ShieldCheck size={16} color="#4ade80" /> : <ShieldAlert size={16} color="#f87171" />}
          <div>
            <div style={{ fontSize: 13, fontWeight: 600, color: chainOk ? '#4ade80' : '#f87171' }}>
              {chainOk ? 'Hash chain integra' : 'Hash chain compromessa'}
            </div>
            <div style={{ fontSize: 10, color: 'var(--text-dim)' }}>
              {chainStatus.total_records.toLocaleString('it-IT')} eventi · ultimo seq: {chainStatus.last_seq}
            </div>
          </div>
        </div>
      )}

      {/* Events table */}
      <div style={{ fontSize: 13, fontWeight: 600, color: '#c7d2fe', marginBottom: 12 }}>Ultimi eventi</div>

      {eventsLoading && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
          {[1, 2, 3, 4, 5].map((i) => <div key={i} className="animate-pulse" style={{ height: 40, background: 'var(--card-bg)', borderRadius: 6 }} />)}
        </div>
      )}

      {!eventsLoading && events?.map((evt) => (
        <div key={evt.event_id} style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '8px 0', borderBottom: '1px solid rgba(255,255,255,0.04)', fontSize: 11 }}>
          <span style={{ color: 'var(--text-dim)', fontVariantNumeric: 'tabular-nums', width: 60 }}>#{evt.seq}</span>
          <span style={{ color: '#818cf8', fontFamily: 'monospace', flex: 1 }}>{evt.event_type}</span>
          <span style={{ color: 'var(--text-secondary)' }}>{evt.actor}</span>
          <span style={{ color: 'var(--text-dim)' }}>{formatDate(evt.ts)}</span>
        </div>
      ))}

      {!eventsLoading && (!events || events.length === 0) && (
        <div style={{ textAlign: 'center', padding: '48px 0', color: 'var(--text-dim)', fontSize: 13 }}>
          Nessun evento registrato.
        </div>
      )}
    </div>
  )
}
```

- [ ] **Step 2: Verifica TypeScript**

```bash
cd frontend && npx tsc --noEmit
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/pages/audit.tsx
git commit -m "feat(frontend): implement Audit trail page with chain status"
```

---

## Task 17: Docker Compose + Makefile update

**Files:**
- Modify: `docker-compose.yml`
- Modify: `docker-compose.dev.yml`
- Modify: `Makefile`

- [ ] **Step 1: Aggiorna il servizio `frontend` in docker-compose.yml**

Sostituisci il blocco `frontend:` esistente con:

```yaml
# In docker-compose.yml — blocco frontend
  frontend:
    build:
      context: .
      dockerfile: services/frontend/Dockerfile
    environment:
      COHERENCE_SERVICE_URL: http://coherence:8003
      GOVERNANCE_SERVICE_URL: http://governance:8005
      FRONTEND_DIST_DIR: /app/dist
    ports:
      - "8080:8080"
    networks:
      - cci-backend
      - cci-frontend
    depends_on:
      coherence:
        condition: service_healthy
      governance:
        condition: service_healthy
    healthcheck:
      test: ["CMD-SHELL", "python -c \"import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/health/live')\""]
      interval: 30s
      timeout: 5s
      retries: 3
```

- [ ] **Step 2: Sostituisci docker-compose.dev.yml con hot-reload Vite**

```yaml
# docker-compose.dev.yml
services:
  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile.dev
    volumes:
      - ./frontend/src:/app/src
      - ./frontend/index.html:/app/index.html
      - ./frontend/vite.config.ts:/app/vite.config.ts
    environment:
      VITE_API_BASE_URL: http://localhost:8080
    ports:
      - "5173:5173"
    networks:
      - cci-frontend

  frontend-bff:
    build:
      context: .
      dockerfile: services/frontend/Dockerfile
      target: runtime
    environment:
      COHERENCE_SERVICE_URL: http://coherence:8003
      GOVERNANCE_SERVICE_URL: http://governance:8005
    ports:
      - "8080:8080"
    networks:
      - cci-backend
      - cci-frontend
    depends_on:
      coherence:
        condition: service_healthy
      governance:
        condition: service_healthy
```

- [ ] **Step 3: Crea frontend/Dockerfile.dev per Vite**

```dockerfile
# frontend/Dockerfile.dev
FROM node:20-alpine
RUN npm install -g pnpm@9
WORKDIR /app
COPY package.json pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile
EXPOSE 5173
ENV HOST=0.0.0.0
CMD ["pnpm", "dev", "--host"]
```

- [ ] **Step 4: Aggiorna i target Makefile rilevanti**

Individua i target `up`, `up-dev` nel Makefile e aggiorna i riferimenti alla porta frontend da 3000 a 8080. Assicurati che i commenti siano corretti:

```makefile
up-dev: ## Avvia stack con frontend in hot-reload (Vite HMR su :5173, BFF su :8080)
	$(COMPOSE) -f docker-compose.yml -f docker-compose.dev.yml up -d
```

- [ ] **Step 5: Verifica la sintassi del compose**

```bash
docker compose config --quiet
# Atteso: nessun errore di parsing YAML
```

- [ ] **Step 6: Commit**

```bash
git add docker-compose.yml docker-compose.dev.yml services/frontend/Dockerfile frontend/Dockerfile.dev Makefile
git commit -m "feat(infra): replace Next.js frontend with Vite SPA + FastAPI BFF in Docker"
```

---

## Task 18: Vitest unit test suite completa

**Files:**
- Create: `frontend/src/tests/hitl-action.test.tsx`

_(Gli altri test sono già stati scritti nei task 5-10)_

- [ ] **Step 1: Scrivi i test della HitlAction form**

```typescript
// frontend/src/tests/hitl-action.test.tsx
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { HitlAction } from '@/pages/hitl-action'
import type { HitlAction as HitlActionType } from '@/lib/types'

vi.mock('@/hooks/use-hitl-queue', () => ({
  useHitlAction: () => ({
    data: {
      id: 'act-001',
      action_type: 'Budget override',
      description: 'Autorizzazione spesa aggiuntiva 80.000 EUR',
      impact: '+80.000 EUR',
      status: 'PENDING',
      created_at: '2026-06-06T10:00:00Z',
      incoherence_id: 'abc123',
    } satisfies HitlActionType,
    isLoading: false,
  }),
  useApproveHitl: () => ({ mutate: vi.fn(), isPending: false }),
  useRejectHitl: () => ({ mutate: vi.fn(), isPending: false }),
}))

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom')
  return { ...actual, useNavigate: () => vi.fn() }
})

function renderPage() {
  const qc = new QueryClient()
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={['/hitl/act-001']}>
        <Routes>
          <Route path="/hitl/:actionId" element={<HitlAction />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>
  )
}

describe('HitlAction', () => {
  it('renders action description', () => {
    renderPage()
    expect(screen.getByText(/Autorizzazione spesa aggiuntiva/)).toBeInTheDocument()
  })

  it('disables approve/reject when motivation is too short', () => {
    renderPage()
    const approveBtn = screen.getByRole('button', { name: /approva/i })
    expect(approveBtn).toBeDisabled()
  })

  it('enables buttons when motivation is long enough', async () => {
    renderPage()
    const textarea = screen.getByRole('textbox')
    await userEvent.type(textarea, 'Motivazione valida con almeno venti caratteri.')
    const approveBtn = screen.getByRole('button', { name: /approva/i })
    expect(approveBtn).not.toBeDisabled()
  })
})
```

- [ ] **Step 2: Esegui l'intera suite di test**

```bash
cd frontend && pnpm test
# Atteso: tutti i test passano (sidebar, lib, kpi-strip, incoherence-card, explanation-block, generate-explanation-button, hitl-action)
```

- [ ] **Step 3: Verifica coverage sui componenti business-critical**

```bash
cd frontend && pnpm test --coverage
# Verifica che explanation-block, incoherence-card, hitl-action siano ≥ 80%
```

- [ ] **Step 4: Commit**

```bash
git add frontend/src/tests/hitl-action.test.tsx
git commit -m "test(frontend): add HitlAction form tests, complete Vitest unit suite"
```

---

## Task 19: Playwright E2E — setup + happy path

**Files:**
- Create: `frontend/e2e/playwright.config.ts`
- Create: `frontend/e2e/dashboard.spec.ts`
- Create: `frontend/e2e/incoherences.spec.ts`

- [ ] **Step 1: Installa Playwright**

```bash
cd frontend
pnpm add -D @playwright/test
pnpm exec playwright install --with-deps chromium
```

- [ ] **Step 2: Crea playwright.config.ts**

```typescript
// frontend/e2e/playwright.config.ts
import { defineConfig } from '@playwright/test'

export default defineConfig({
  testDir: './e2e',
  use: {
    baseURL: 'http://localhost:5173',
    headless: true,
  },
  webServer: {
    command: 'pnpm dev',
    url: 'http://localhost:5173',
    reuseExistingServer: !process.env['CI'],
    cwd: '../',
  },
})
```

- [ ] **Step 3: Scrivi E2E dashboard test**

```typescript
// frontend/e2e/dashboard.spec.ts
import { test, expect } from '@playwright/test'

test('dashboard carica KPI strip', async ({ page }) => {
  await page.goto('/')
  await expect(page.getByText('Dashboard')).toBeVisible()
  await expect(page.getByText('Incoerenze')).toBeVisible()
  await expect(page.getByText('HITL in attesa')).toBeVisible()
  await expect(page.getByText('Audit chain')).toBeVisible()
})

test('sidebar navigation funziona', async ({ page }) => {
  await page.goto('/')
  await page.getByRole('link', { name: 'Incoerenze' }).click()
  await expect(page).toHaveURL('/incoherences')
  await page.getByRole('link', { name: 'Audit Trail' }).click()
  await expect(page).toHaveURL('/audit')
})
```

- [ ] **Step 4: Scrivi E2E incoherences test**

```typescript
// frontend/e2e/incoherences.spec.ts
import { test, expect } from '@playwright/test'

test('pagina incoerenze si carica', async ({ page }) => {
  await page.goto('/incoherences')
  await expect(page.getByText('Non conformità rilevate')).toBeVisible()
  // Aspetta caricamento (loading o dati)
  await expect(page.locator('body')).not.toContainText('undefined')
})

test('filtro severity cambia i risultati', async ({ page }) => {
  await page.goto('/incoherences')
  const select = page.locator('select')
  await select.selectOption('CRITICAL')
  await expect(select).toHaveValue('CRITICAL')
})
```

- [ ] **Step 5: Aggiungi script E2E in package.json**

```json
// In frontend/package.json aggiungere in "scripts":
"e2e": "playwright test --config=e2e/playwright.config.ts"
```

- [ ] **Step 6: Commit**

```bash
git add frontend/e2e/ frontend/package.json
git commit -m "test(frontend): add Playwright E2E tests for dashboard and incoherences"
```

---

## Task 20: Build finale e verifica integrazione

- [ ] **Step 1: Build React SPA**

```bash
cd frontend && pnpm build
# Atteso: dist/ generata senza errori TypeScript
ls -lh dist/
```

- [ ] **Step 2: Verifica che il BFF serva la build**

```bash
cd services/frontend
FRONTEND_DIST_DIR=../../frontend/dist uvicorn cci_frontend.main:app --port 8080 &
sleep 2
curl -s http://localhost:8080/health/live
# Atteso: {"status":"ok"}
curl -s -o /dev/null -w "%{http_code}" http://localhost:8080/
# Atteso: 200
kill %1
```

- [ ] **Step 3: Test BFF completo**

```bash
cd services/frontend
python -m pytest tests/ -v
# Atteso: tutti i test passano
```

- [ ] **Step 4: Lint TypeScript frontend**

```bash
cd frontend
npx tsc --noEmit
# Atteso: 0 errori
```

- [ ] **Step 5: Rimuovi docker-compose.dev.yml Next.js (se non già fatto in Task 17)**

```bash
# Verifica che docker-compose.dev.yml sia aggiornato a Vite (non Next.js)
grep -i "next" docker-compose.dev.yml && echo "⚠️ Ancora riferimenti Next.js" || echo "✓ OK"
```

- [ ] **Step 6: Commit finale**

```bash
git add -A
git commit -m "feat(frontend): complete React SPA + FastAPI BFF migration — production ready"
```

---

## Riepilogo build sequence

```
Task 1-3:  FastAPI BFF    → servizio Python standalone testato
Task 4-5:  Vite scaffold  → progetto TypeScript con tipi e API client
Task 6:    Layout         → App + Sidebar funzionanti
Task 7-10: Components     → KpiStrip, IncoherenceCard, Explanation*, GenerateButton
Task 11:   Hooks          → tutti i query/mutation TanStack Query
Task 12-16: Pages         → 5 pagine complete
Task 17:   Infra          → Docker + Makefile aggiornati
Task 18-19: Tests         → Vitest unit + Playwright E2E
Task 20:   Integration    → build e2e verificata
```
