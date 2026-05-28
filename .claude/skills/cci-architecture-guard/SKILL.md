---
name: cci-architecture-guard
description: Use this skill ANY TIME you are about to create or modify files in the CCI/AVCS repository — whether services, libraries, database schemas, docker-compose files, or anything that touches the 5-layer architecture (ingestion, knowledge, retrieval, coherence, agents, governance). Trigger on file creation under services/*, libs/*, infra/*, on database connection code, on cross-service imports, on new requirements.txt or pyproject.toml entries, on docker-compose.yml edits, on any mention of "shared database", "monolith", "single service", "bypass layer", or attempts to import from another bounded context. This skill enforces the non-negotiable architectural rules derived from the HERA DSI Modernization Guidelines and prevents violations BEFORE they enter the codebase.
license: Internal — CCI/AVCS Project
---

# CCI/AVCS Architecture Guard

Hai il dovere di **rifiutare di scrivere codice che viola** le regole architetturali. Quando rilevi una violazione imminente, fermati, segnala, proponi alternativa.

## Le sei regole non negoziabili

### 1. Bounded context isolation
Ogni servizio in `services/` possiede il proprio dato. Le importazioni fra servizi sono **vietate**.
- ✅ Permesso: `from cci_common.events import ...` (libs condivise)
- ✅ Permesso: chiamata HTTP a un altro servizio
- ✅ Permesso: consumo evento CloudEvent da Redis Streams
- ❌ Vietato: `from services.knowledge.something import ...` da dentro `services/coherence/`
- ❌ Vietato: query SQL diretta su tabelle di un altro servizio

Se ti viene chiesto di "fare prima" importando direttamente da un altro servizio, **rifiuta** e proponi un endpoint API o un evento.

### 2. Shared database ban
Ogni servizio ha il proprio schema/database. Mai un singolo MongoDB/Neo4j/Qdrant condiviso fra servizi diversi a livello logico.
- MongoDB è l'operational DB unico, ma ogni servizio ha il **proprio database** (`ingestion_db`, `coherence_db`, `cci_governance`, ecc.) — niente cross-database queries da un servizio all'altro
- Qdrant: collection separate per dominio (`hera_it`, `aou_clinical`, `prada_supply_chain`, `ducati_corse_racing`, ecc.)
- Neo4j: database separati o, in MVP, namespace isolati via etichette
- **Mai** una collection `shared_documents` letta da due servizi distinti.

### 3. Stateless processes
Nessuno stato in memoria del processo oltre la singola richiesta.
- Sessioni → Redis
- Cache → Redis con TTL
- File temporanei → MinIO (S3-compatible) o `/tmp` con cleanup esplicito a fine richiesta
- ❌ Vietato: `_cache = {}` a livello modulo come "cache globale"
- ❌ Vietato: scrivere su filesystem locale dati che devono sopravvivere al restart

### 4. 12-Factor mandatorio
- **Config**: solo via env var o ConfigMap. Mai endpoint, credenziali, parametri hardcoded.
- **Backing services**: ogni dipendenza è "attached resource", swappabile via env (es. `QDRANT_URL`, `NEO4J_URI`).
- **Graceful shutdown**: ogni servizio FastAPI deve gestire `SIGTERM` e completare le richieste in volo entro 30 s.
- **Dev/prod parity**: lo stack `docker-compose` deve usare le stesse versioni di Postgres/Neo4j/Qdrant della produzione.

### 5. Health checks standardizzati
Ogni servizio FastAPI espone tre endpoint:
- `GET /health/live` → 200 se il processo è vivo (nessun controllo dipendenze)
- `GET /health/ready` → 200 se le dipendenze critiche sono raggiungibili (DB, vector store, cache)
- `GET /health/startup` → 200 quando il warm-up è completo (modelli ML caricati, schema migrato)

Implementazione tipica:
```python
from fastapi import APIRouter, Response, status
router = APIRouter(prefix="/health")

@router.get("/live")
async def live() -> dict: return {"status": "ok"}

@router.get("/ready")
async def ready(deps: Deps = Depends(get_deps)) -> Response:
    if not await deps.check_all():
        return Response(status_code=status.HTTP_503_SERVICE_UNAVAILABLE)
    return Response(content='{"status":"ok"}', media_type="application/json")
```

### 6. Container-first, non Kubernetes-obsessed
- L'MVP gira **solo** con `docker-compose`. Niente Helm chart, Kustomize, manifest K8s fino a Fase 3.
- Ogni servizio ha un `Dockerfile` multi-stage: stage `builder` con uv/poetry, stage finale con immagine slim o distroless.
- Immagine finale target: **< 300 MB**. Se supera, indagare (probabilmente dipendenze inutili).
- Startup container target: **< 5 s**.

## Anti-pattern da intercettare attivamente

| Sintomo nel codice | Violazione | Azione |
|---|---|---|
| `import services.X` dentro `services.Y` | Bounded context | Rifiuta, proponi API o evento |
| `MONGODB_URI = "mongodb://..."` hardcoded con credenziali | 12-Factor (Config) | Sposta in `.env.example`, usa `os.getenv` |
| `_global_cache = {}` a livello modulo | Stateless | Sposta in Redis |
| `pickle.dump(state, "/tmp/state.pkl")` | Stateless | Sposta in object storage o Redis |
| `from anthropic import AsyncAnthropic` fuori da `libs/cci-llm/` o `/tests/` | Bypass del LLMClient wrapper | Usa `cci_llm.LLMClient` con DI |
| `import openai`, `import litellm`, `import ollama` ovunque | Provider non ammesso | Solo Anthropic via `cci_llm.LLMClient` |
| `db.audit_log.update_one/delete_one/drop` su `audit_log` | Audit log immutabilità (R5) | Append evento di redazione; vedi `cci-audit-chain` |
| `PostgresSaver`, `SqliteSaver` per LangGraph | Stack non allineato | Usa `AsyncMongoDBSaver` da `langgraph-checkpoint-mongodb` |
| `requirements.txt` con `boto3` come dipendenza core di un servizio | Lock-in vendor | Usa `minio` SDK o boto3 con endpoint configurabile (S3-compatible) |
| `kubectl apply` o riferimenti a `helm` in MVP | Kubernetes-obsession | Posticipa a Fase 3, usa docker-compose |
| Un singolo servizio che fa ingestion + coherence + audit | Layer separation | Splitta nei 3 servizi corrispondenti |
| `frontend/` con Server Action su backend logic | Architettura BFF non allineata | Consumo REST OpenAPI tipizzato (vedi `cci-frontend-nextjs`) |

## Procedura quando devi creare un nuovo modulo

1. **Identifica il layer**: ingestion / knowledge / retrieval / coherence / agents / governance.
2. **Verifica le dipendenze**: deve dipendere solo da `libs/cci-common`, `libs/cci-llm` e/o chiamate HTTP esterne.
3. **Definisci il contratto**: input schema Pydantic, output schema Pydantic, evento CloudEvent emesso.
4. **Aggiungi i 3 health checks**.
5. **Aggiungi le metriche Prometheus**: almeno `_requests_total`, `_request_duration_seconds`, `_errors_total`.
6. **Aggiungi il Dockerfile multi-stage**.
7. **Aggiungi il test pattern**: 1 unit test per ogni funzione pubblica, 1 integration test con testcontainers.

## Quando hai dubbi

**Non inventare**. Fermati, segnala il dubbio architetturale all'utente, proponi 2-3 alternative motivate e attendi conferma. Se la decisione è strutturale, scrivi un ADR in `docs/adr/NNNN-titolo.md` prima di procedere.

## Riferimenti
- Linee Guida Modernizzazione HERA DSI v1.0 (Aprile 2026)
- Documento `CCI_AVCS_Technical_Specifications.html`, sezione §03 (Principi Architetturali)
- 12-Factor App: https://12factor.net
