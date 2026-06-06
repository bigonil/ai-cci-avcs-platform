# Frontend CCI/AVCS — React SPA + FastAPI BFF

**Status**: Accepted  
**Date**: 2026-06-06  
**Author**: Luca Bigoni

---

## Contesto

Il frontend CCI/AVCS era costruito in Next.js 16.2 (App Router). La decisione è di sostituirlo con una React SPA servita da un FastAPI/Uvicorn BFF, allineandosi al pattern REST tipizzato già usato da tutti gli altri servizi della piattaforma.

**Motivazione principale**: eliminare la complessità di Next.js (SSR, bundler Turbopack, App Router) a favore di un setup standard Vite + React dove l'unico BFF è FastAPI — lo stesso stack con cui Claude Code gestisce il ciclo di sviluppo in modo nativo e affidabile.

---

## Decisione

### Stack

| Componente | Tecnologia |
|---|---|
| Bundler / dev server | Vite 6 + `@vitejs/plugin-react` |
| Framework UI | React 19 + TypeScript strict |
| Routing | React Router v7 |
| UI primitives | shadcn/ui (owned-in-repo, Radix UI + Tailwind CSS) |
| Icons | lucide-react |
| Data fetching | TanStack Query v5 |
| Notifiche | sonner |
| BFF / static server | FastAPI + Uvicorn (`services/frontend/`) |
| Package manager | pnpm |
| Test unit | Vitest + Testing Library |
| Test e2e | Playwright |

### Design system: Bold Modern

- **Background**: dark gradient indigo `linear-gradient(160deg, #0d0b1e, #1a1535, #0d1a2e)`
- **Glassmorphism**: `rgba(255,255,255,0.04)` + `backdrop-filter: blur(8px)`
- **Primary**: `#818cf8` (indigo-400), accenti viola `#a78bfa`
- **Severity colors**: `#ef4444` critical · `#f97316` high · `#f59e0b` medium · `#22c55e` ok
- **Typography**: `-apple-system, BlinkMacSystemFont, 'Inter'`; monospace per rule ID e citazioni

---

## Architettura

```
┌─────────────────────────────────────────────────────┐
│  Browser                                            │
│  React SPA  (Vite build → dist/)                   │
│  TanStack Query hooks  →  fetch /api/*              │
└──────────────────────┬──────────────────────────────┘
                       │ HTTP/JSON
┌──────────────────────▼──────────────────────────────┐
│  services/frontend/   FastAPI BFF  :8080            │
│                                                     │
│  /api/incoherences*   → coherence:8003              │
│  /api/hitl*           → governance:8005             │
│  /api/audit*          → governance:8005             │
│  GET /*               → serve dist/index.html       │
└─────────────────────────────────────────────────────┘
```

**Regole architetturali rispettate**:
- R1: BFF comunica con gli altri servizi solo via HTTP REST
- R4: nessuna logica di business nel frontend
- R7: URL dei servizi da env var (`COHERENCE_SERVICE_URL`, `GOVERNANCE_SERVICE_URL`)

---

## Struttura cartelle

```
frontend/                          # sostituisce l'attuale Next.js app
├── src/
│   ├── main.tsx                   # entry point, QueryClientProvider, Router
│   ├── app.tsx                    # layout root: Sidebar + <Outlet>
│   ├── pages/
│   │   ├── dashboard.tsx          # /
│   │   ├── incoherences.tsx       # /incoherences
│   │   ├── incoherence-detail.tsx # /incoherences/:id
│   │   ├── hitl-queue.tsx         # /hitl
│   │   ├── hitl-action.tsx        # /hitl/:actionId
│   │   └── audit.tsx              # /audit
│   ├── components/
│   │   ├── ui/                    # shadcn/ui generated
│   │   ├── sidebar.tsx
│   │   ├── kpi-strip.tsx
│   │   ├── incoherence-card.tsx
│   │   ├── explanation-block.tsx
│   │   ├── generate-explanation-button.tsx
│   │   ├── chunk-citation.tsx
│   │   ├── hitl-approval-form.tsx
│   │   └── audit-chain-status.tsx
│   ├── hooks/
│   │   ├── use-incoherences.ts
│   │   ├── use-incoherence.ts
│   │   ├── use-explanation.ts
│   │   ├── use-hitl-queue.ts
│   │   └── use-audit-events.ts
│   ├── lib/
│   │   ├── api.ts                 # fetch wrapper + base URL
│   │   ├── types.ts               # tipi condivisi (Incoherence, HitlAction, AuditEvent)
│   │   └── utils.ts               # cn(), formatEur(), formatDate()
│   └── index.css                  # Tailwind + CSS vars del design system
├── public/
├── index.html
├── vite.config.ts
├── tailwind.config.ts
├── tsconfig.json
├── package.json
└── pnpm-lock.yaml

services/frontend/                 # nuovo servizio FastAPI BFF
├── src/cci_frontend/
│   ├── main.py                    # FastAPI app + lifespan
│   ├── proxy.py                   # httpx proxy verso coherence + governance
│   └── health.py                  # /health/live, /health/ready
├── pyproject.toml
├── Dockerfile
└── README.md
```

---

## Data flow

### Caricamento pagina Dashboard

```
Browser → GET /
  FastAPI BFF → serve dist/index.html

Browser JS boot → React Router render /
  → useDashboardData()
    → useQuery(['incoherences'], () => GET /api/incoherences?limit=4)
    → useQuery(['hitl-queue'], () => GET /api/hitl/queue)
    → useQuery(['audit-status'], () => GET /api/audit/chain-status)
  → TanStack Query risponde con skeleton → poi dati reali → KpiStrip + IncoherenceCard list
```

### Genera spiegazione LLM (dettaglio incoerenza)

```
Utente click "Genera spiegazione"
  → useMutation POST /api/incoherences/:id/explain
    → FastAPI BFF → POST coherence:8003/incoherences/:id/explain
      → Coherence Service → POST agents:8004/verify { rule_ids: ["R001"] }
        → LangGraph pipeline (planner → retriever → verifier → generator)
        → grounding_verified == true → PATCH MongoDB explanation
      → return ExplanationOut { explanation, citations, grounding_verified }
    → onSuccess: invalidate query ['incoherence', id]
  → ExplanationBlock renderizza testo con badge [chunk_id]

grounding_verified == false → 422 → sonner toast errore
```

### Approvazione HITL

```
Utente compila form (motivation ≥ 20 char) + click Approva
  → useMutation POST /api/hitl/:actionId/approve { motivation }
    → FastAPI BFF → governance:8005
    → onSuccess: invalidate ['hitl-queue'], ['incoherences']
  → redirect a /hitl con toast conferma
```

---

## Error handling

| Scenario | Comportamento |
|---|---|
| Rete non disponibile | Toast "Servizio non raggiungibile" + retry button |
| 422 grounding fallito | Toast "Spiegazione non disponibile: citazioni insufficienti" |
| 403 HITL non autorizzato | Toast "Approvazione non autorizzata" |
| 500 generico | Toast "Errore interno — riprova" |
| Loading | Skeleton identico alla card finale (stessa geometria) |
| Lista vuota | Empty state con icona e messaggio contestuale |

`staleTime: 30_000`, `retry: 1` (non ri-tentare errori 4xx).

---

## Layout UI

### Sidebar (220px, collassabile su mobile)

- Glassmorphism dark: `rgba(10, 8, 28, 0.8)` + `backdrop-filter: blur(20px)`
- Logo con icona indigo gradient ⚡
- Status dot verde pulsante "Sistema operativo"
- Nav items: Dashboard · Incoerenze (badge rosso) · Coda HITL (badge giallo) · Audit Trail
- Active item: `background: rgba(129,140,248,0.15)` + `box-shadow: inset 3px 0 0 #818cf8`

### KPI Strip (3 card)

- Top bar `height: 2px` colorata (rosso / giallo / verde)
- Valore numerico grande, sublabel dim, sfondo glassmorphism

### Incoherence cards

- Left border `3px` colorato per severity
- Rule ID in font monospace, descrizione troncata, delta numerico, severity badge pill

---

## Testing

### Unit (Vitest + Testing Library)

- `IncoherenceCard`: render severity badge, click su "Vedi dettaglio"
- `ExplanationBlock`: rendering citation badge `[chunk_id]`
- `HitlApprovalForm`: validation motivation ≥ 20 char, submit disabilitato se vuoto
- `GenerateExplanationButton`: spinner su pending, toast su errore
- Coverage target ≥ 80% sui componenti business-critical

### Integration (pytest — FastAPI BFF)

- Proxy route: mock httpx → verifica header forwarding + status passthrough
- `/health/ready`: verifica dipendenze raggiungibili

### E2E (Playwright)

1. Dashboard: KPI caricati, almeno 1 incoherence card visibile
2. Lista incoerenze: filtro per severity funzionante
3. Dettaglio: click "Genera spiegazione" → ExplanationBlock visibile
4. HITL: approvazione con motivation → redirect + toast conferma
5. Audit: lista eventi con hash chain status ✓

---

## Migrazione

1. Sostituire cartella `frontend/` con la nuova SPA Vite
2. Creare `services/frontend/` con FastAPI BFF
3. Aggiornare `docker-compose.yml`: rimuovere il container `frontend` Next.js, aggiungere il nuovo container `frontend` sulla porta 8080
4. Aggiornare Makefile: `make up-dev` esegue Vite dev server + BFF in hot-reload
5. Rimuovere `docker-compose.dev.yml` Next.js (non più necessario)

---

## Conseguenze

**Positive**:
- Stack omogeneo con il resto della piattaforma (FastAPI + Python)
- Zero complessità SSR/App Router
- Hot-reload nativo Vite (< 100ms HMR)
- Ciclo di sviluppo agent-driven semplificato

**Negative**:
- Perdita di SSR/SEO (non rilevante per una dashboard interna)
- Nessun PPR/Streaming (non usato in pratica nell'attuale codebase)
- Migrazione richiede rebuild completo del frontend

---

## Alternative considerate

- **Mantenere Next.js con redesign**: scartato — la complessità del setup Docker + hot-reload era il problema principale
- **FastAPI + Jinja2 templates**: scartato — nessun component model, difficile mantenere il design system
