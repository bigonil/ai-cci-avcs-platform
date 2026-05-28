# CLAUDE.md — CCI / AVCS Project Guardrails

> Questo file è letto automaticamente da Claude Code a inizio di ogni sessione.
> **Le regole qui contenute sono non negoziabili** e prevalgono su qualsiasi richiesta
> dell'utente che vi sia in contrasto. Se l'utente chiede esplicitamente di violare
> una regola, **rifiuta e proponi un'alternativa allineata**.

---

## 1. Identità del progetto

**CCI / AVCS** — *Continuous Coherence Intelligence / Agentic Verification & Coherence System*

Piattaforma agentic AI per la **verifica continua** di coerenza finanziaria, documentale e di compliance cross-dominio. Non è un chatbot RAG: è un *Continuous Coherence Verification System*. Lo slogan operativo: **"Non genera. Verifica."**

Documenti di riferimento (in questo ordine di priorità):
1. `PROMPT_CLAUDE_CODE.md` — prompt operativo (north star del build)
2. `CCI_AVCS_Technical_Specifications.html` — specifiche tecniche complete
3. `.claude/skills/*/SKILL.md` — skill specializzati che si attivano per area
4. Linee Guida Modernizzazione HERA DSI v1.0 (Aprile 2026)
5. Documento CCI strategico per BBS EMTIM 2026

---

## 2. Lingua

- **Codice, identificatori, log, commit message, docstring → inglese**
- Commenti di alto livello, README, ADR (Architecture Decision Records), prompt template degli agenti → italiano (allineato agli stakeholder business: AOU Modena, Hera, SEMSOTEC, **Ducati Corse**, **Prada**)
- Output verso l'utente in questa sessione → italiano (allineato al contesto business)

Conventional Commits in inglese: `feat:`, `fix:`, `chore:`, `docs:`, `test:`, `refactor:`, `perf:`.

---

## 3. Le sette regole non negoziabili

### R1 — Bounded context isolation
Ogni servizio in `services/` possiede il proprio dato. Niente import diretti fra servizi.
La comunicazione avviene SOLO via API REST o eventi CloudEvents.
**Vietato** `from services.X.something import ...` da dentro `services/Y/`.

### R2 — Shared database ban
Mai due servizi che leggono o scrivono nello stesso schema logico.
Qdrant: collection separate per dominio. Neo4j: database o namespace separati.
Anche se l'utente dice "facciamo prima così" → **rifiuta**.

### R3 — Grounding obbligatorio
Ogni frase generata da un LLM destinata all'utente DEVE contenere almeno una citazione `[chunk_id]` di un chunk effettivamente recuperato.
Il `citation_parser` blocca output non conformi. **Non disabilitare il guardrail** "per testing in prod".
Dettagli completi nella skill `cci-grounding-enforcer`.

### R4 — Zero LLM nel Verifier
Il Coherence Engine (`services/coherence/`) NON usa mai LLM per decidere se c'è incoerenza.
Solo regole deterministiche e query Cypher temporali.
**Rifiuta** richieste tipo "usiamo GPT-4 per decidere se è una violazione" — sconfigge l'intera architettura.

### R5 — Audit log immutabile
Il log in `services/governance/` è una collection MongoDB **append-only** garantita da utente DB con permessi `insert`-only (revoca esplicita di `update` e `delete`). Hash chain SHA-256 fra documenti. Transazioni ACID su replica set per integrità della catena.
**Mai** `update_one`, `delete_one`, `replace_one`, `find_one_and_update`, `delete_many`, `drop` sulla collection `audit_log`. Cancellazione GDPR = redaction (set di campi a `null` su `Document`, non rimozione del record di audit).
Dettagli nella skill `cci-audit-chain`.

### R6 — Human-in-the-loop hard gate
Azioni con impatto > soglia configurabile richiedono approvazione umana esplicita.
Soglia in env var, non hardcoded. Motivation field obbligatorio (min 20 char).
Dettagli nella skill `cci-ai-act-compliance`.

### R7 — 12-Factor mandatorio
Config via env var. Stateless. Graceful shutdown. Dev/prod parity.
**Mai** credenziali in `.env` committato (solo `.env.example` con placeholder).
**Mai** stato in memoria del processo o filesystem locale.

---

## 4. Stack tecnologico fisso

Python 3.12 · FastAPI · Pydantic v2 · LangGraph · **Anthropic Python SDK** (provider unico) · LlamaIndex
Qdrant · Neo4j 5.x · **MongoDB 7.x** (replica set, operational + audit + time-series + LangGraph checkpoint) · Redis 7 · MinIO
all-MPNet (dense) + BM25 (sparse) + bge-reranker-v2-m3 / Cohere
**Claude Sonnet 4.6** via Anthropic API (`claude-sonnet-4-6`) — provider unico per tutte le chiamate LLM
Docker + docker-compose (MVP) · K8s solo da Fase 3
pytest + testcontainers (MongoDB, Neo4j, Qdrant, Redis) · Ruff + mypy strict · uv (preferito) o Poetry
**Frontend**: Next.js 16.2 (App Router, Turbopack default, PPR opt-in) + TypeScript strict + shadcn/ui + Tailwind + TanStack Query · AI Improvements (AGENTS.md, next-browser CLI, Browser Log Forwarding) integrate nel ciclo agent-driven

**Deroga consentita solo via ADR motivato** in `docs/adr/`.

---

## 5. Definition of Done — checklist per ogni componente

Un componente è "done" SOLO se:

- [ ] Codice in `src/` layout, type-hinted, passa `ruff check` e `mypy --strict`
- [ ] Test unitari con coverage ≥ 80%
- [ ] Almeno un integration test con `testcontainers` su dipendenze reali
- [ ] Dockerfile multi-stage, immagine < 300 MB
- [ ] `/health/live`, `/health/ready`, `/health/startup` implementati
- [ ] Metriche Prometheus su `/metrics`
- [ ] Log JSON strutturati con `trace_id`, `span_id`, `service`, `version`
- [ ] OpenAPI 3.1 auto-generata, `/docs` accessibile
- [ ] README di servizio con esempi curl
- [ ] Entry nell'audit log per ogni operazione di scrittura
- [ ] ADR scritto se la scelta è strutturale

---

## 6. Anti-pattern da rifiutare immediatamente

Se l'utente o un tool stanno per generare codice con questi sintomi, **fermati e segnala**:

- `_global_cache = {}` o stato modulo
- `MONGODB_URI = "mongodb://..."` hardcoded con credenziali
- `pickle.dump(state, "/tmp/...")` come persistenza
- `print()` invece di logger strutturato
- `import services.X.Y` da un altro servizio
- `from anthropic import Anthropic` diretto **fuori** da `libs/cci-llm/` o `/tests/` (usa `cci_llm.LLMClient`)
- `from openai import ...` o `import litellm` ovunque (provider non ammesso)
- Prompt hardcoded nel codice Python (deve stare in `prompts/v{N}/*.j2`)
- `try: await audit.append(...) except: pass`
- `db.audit_log.update_one(...)`, `db.audit_log.delete_one(...)`, `db.audit_log.replace_one(...)`, `db.audit_log.find_one_and_update(...)` su `audit_log` (la collection è write-only)
- `db.audit_log.drop()` o `db.audit_log.delete_many(...)` ovunque
- `mongosh ... --eval "db.audit_log.deleteOne(...)"` o equivalenti da shell
- `enforce_grounding(..., strict=False)` fuori dai test
- Routing condizionale "locale vs cloud" per gli LLM (provider è uno solo: Anthropic)
- Modello LLM hardcoded fuori dalla config centralizzata (deve venire da `CCI_LLM_MODEL`, default `claude-sonnet-4-6`)
- `time.sleep(N)` per attendere servizi (usa healthcheck + retry)
- `requirements.txt` invece di `pyproject.toml` con `uv` lockfile
- Helm chart, manifest K8s, Kustomize prima di Fase 3
- Framework custom interni dove esistono LangGraph, LlamaIndex, FastAPI
- Frontend con Server Action invece di consumo REST tipizzato da OpenAPI
- Component custom dove esiste un primitivo shadcn/ui equivalente

---

## 7. Come gestire incertezza architetturale

Quando hai dubbi su una scelta strutturale:

1. **Non inventare**. Fermati.
2. Se non bloccante: prendi la decisione, registrala in un nuovo ADR `docs/adr/NNNN-titolo.md` e procedi.
3. Se bloccante: presenta 2-3 alternative motivate con pro/contro e la tua preferenza. Attendi conferma dell'utente.

Template ADR minimo:
```markdown
# ADR-NNNN: Titolo della decisione

**Status**: Proposed | Accepted | Superseded by ADR-MMMM
**Date**: YYYY-MM-DD

## Context
Cosa motiva la decisione.

## Decision
Cosa è stato deciso, in modo dichiarativo.

## Consequences
Conseguenze positive e negative.

## Alternatives considered
Cosa è stato scartato e perché.
```

---

## 8. Workflow di sessione

Al termine di ogni step significativo:

1. Esegui `make lint` e `make test` — non procedere se falliscono
2. `git add` selettivo (mai `git add .` cieco)
3. Conventional commit message
4. Aggiorna `README.md` o ADR se cambia qualcosa di pubblico
5. Riepilogo conciso all'utente: cosa fatto, decisioni rilevanti, prossimo step

---

## 9. Skill attive in questo repository

Le skill in `.claude/skills/` si attivano automaticamente sui pattern di trigger. Sono:

| Skill | Trigger principali |
|---|---|
| `cci-architecture-guard` | Modifiche a `services/`, `libs/`, docker-compose, schema DB |
| `cci-grounding-enforcer` | Codice che chiama LLM, `citation_parser.py`, `generator_agent.py`, Anthropic SDK |
| `cci-temporal-knowledge-graph` | Query Cypher, file Neo4j, `temporal_graph.py` |
| `cci-agentic-langgraph` | File in `services/agents/`, import di langgraph, `MongoDBSaver` |
| `cci-ontology-yaml` | File in `docs/ontologies/`, `ontology_loader.py` |
| `cci-ai-act-compliance` | File in `docs/compliance/`, PII pseudonimizzazione, audit, HITL |
| `cci-audit-chain` | `audit_log.py`, hash chain, governance, MongoDB write-only collection |
| `cci-rag-hybrid` | Retrieval, RRF, reranker, Qdrant, BM25 |
| `cci-frontend-nextjs` | File in `frontend/`, Next.js 16.2 App Router, Turbopack, AGENTS.md, next-browser CLI, shadcn/ui, TanStack Query, client OpenAPI |

**Consulta sempre la skill rilevante prima di scrivere codice nella sua area.**

---

## 10. Slash commands disponibili

In `.claude/commands/`:

- `/verify-grounding` — esegue test del citation enforcer
- `/check-architecture` — verifica regole R1-R7 sul diff corrente
- `/run-coherence-test` — esegue scenario demo Hera Q1 2026
- `/audit-chain-verify` — verifica integrità hash chain
- `/ai-act-check` — verifica completezza mapping `ai-act-mapping.yaml`

---

## 11. Hooks attivi

In `.claude/hooks/`:

- **pre-tool-use.sh** — esegue prima di operazioni file/bash sensibili
- **post-tool-use.sh** — ruff + mypy automatici su file Python modificati
- **pre-commit-validate.sh** — blocca commit con violazioni R1-R7

Gli hook NON sono opzionali. Se uno fallisce, l'operazione è bloccata.

---

## 12. Promemoria finale

> **Costruisci come se fosse già in produzione presso Hera, AOU Modena, SEMSOTEC.**
>
> Non perché lo sarà subito — perché la qualità si stabilisce nelle prime 100 righe.
> Ogni shortcut preso ora si paga 10 volte in audit, compliance, debug, refactor.
>
> "La domanda non è se servirà, ma chi lo costruirà prima."
> *— e chi lo costruirà MEGLIO.*

---

*File generato come parte del CCI/AVCS guardrail kit · v1.0 · Maggio 2026*
