# CCI / AVCS — Continuous Coherence Intelligence

> **"Non genera. Verifica."**

Piattaforma agentic AI per la **verifica continua** di coerenza finanziaria, documentale
e di compliance cross-dominio. Sistema ad alto rischio ai sensi dell'EU AI Act (Reg. 2024/1689).

## Quick Start

```bash
# 1. Copia e configura le variabili d'ambiente
cp .env.example .env
# Edita .env: aggiungi ANTHROPIC_API_KEY e cambia le password

# 2. Avvia l'infrastruttura
make up

# 3. Installa dipendenze Python (richiede uv)
make install

# 4. Esegui i test unitari
make test

# 5. Demo end-to-end Hera Q1 2026
make demo
```

## Architettura

Sistema a **5 layer** con bounded context separati:

| Layer | Servizio | Responsabilità |
|-------|---------|---------------|
| 1 | `ingestion-service` | Upload, parsing, NER, chunking, embedding |
| 2 | `knowledge-service` | Vector store (Qdrant), Temporal KG (Neo4j), Time-series (MongoDB) |
| 3 | `agent-orchestrator` | LangGraph: Planner→Retriever→Verifier→Generator→Audit |
| 4 | `retrieval-module` | Hybrid search RRF, reranking, cache Redis |
| 5 | `governance-service` | Audit log immutabile, HITL, AI Act compliance |

Provider LLM: **Anthropic Claude Sonnet 4.6** (unico provider, via `libs/cci-llm`).

Vedi [docs/architecture/c4-container.mmd](docs/architecture/c4-container.mmd) per il diagramma completo.

## Stack

- **Python 3.12** + FastAPI + Pydantic v2 + LangGraph
- **Anthropic API** (`claude-sonnet-4-6`) — provider unico per tutti gli LLM
- **Qdrant** (vector) + **Neo4j 5.x** (graph) + **MongoDB 7.x** (operational + audit + checkpoints)
- **Redis 7** (cache + streams) + **MinIO** (object storage)
- **Next.js 16.2** + shadcn/ui + TanStack Query (frontend)
- **Docker + docker-compose** (MVP)

## 7 Regole Non Negoziabili

| # | Regola | Sintesi |
|---|--------|---------|
| R1 | Bounded Context Isolation | Nessun import diretto tra servizi |
| R2 | Shared Database Ban | Database separati per bounded context |
| R3 | Grounding Obbligatorio | Ogni output LLM deve citare `[chunk_id]` |
| R4 | Zero LLM nel Verifier | Coherence Engine 100% deterministico |
| R5 | Audit Log Immutabile | MongoDB append-only + hash chain SHA-256 |
| R6 | Human-in-the-Loop Hard Gate | Approvazione umana per impatto > soglia |
| R7 | 12-Factor Mandatorio | Config via env var, stateless, no credenziali in repo |

## Comandi

```bash
make help            # lista tutti i comandi
make lint            # ruff check + format check
make typecheck       # mypy --strict
make test            # unit test (no containers, no live LLM)
make test-integration # integration test con testcontainers
make verify-audit    # verifica integrità hash chain audit log
make clean           # pulizia artefatti build
```

## Roadmap

- [x] Step 1 — Scaffolding monorepo
- [ ] Step 2 — Common library (CloudEvents, domain models, OTel)
- [ ] Step 3 — Infra docker-compose completa
- [ ] Step 4 — Ingestion service
- [ ] Step 5 — Knowledge service
- [ ] Step 6 — Retrieval module
- [ ] Step 7 — Coherence engine
- [ ] Step 8 — Agents (LangGraph)
- [ ] Step 9 — Governance service
- [ ] Step 10 — Frontend Next.js 16.2
- [ ] Step 11 — Scenario end-to-end Hera Q1 2026
- [ ] Step 12 — Compliance kit completo
- [ ] Step 13 — Polish & docs

## Compliance

- **EU AI Act** — Sistema ad alto rischio, mapping art. 9-15: [docs/compliance/ai-act-mapping.yaml](docs/compliance/ai-act-mapping.yaml)
- **GDPR** — Data flow e pseudonimizzazione: [docs/compliance/gdpr-data-flow.md](docs/compliance/gdpr-data-flow.md)
- **ISO 42001** — Roadmap AIMS: [docs/compliance/iso42001-roadmap.md](docs/compliance/iso42001-roadmap.md)

## ADR

- [ADR-0001](docs/adr/0001-use-langgraph.md) — Uso di LangGraph come orchestratore agentico
- [ADR-0002](docs/adr/0002-temporal-graph-neo4j.md) — Neo4j come Temporal Knowledge Graph
- [ADR-0003](docs/adr/0003-grounding-enforcement.md) — Citation enforcement come guardrail architetturale

---

*Build it like it's already in production at Hera, AOU Modena e SEMSOTEC.*
