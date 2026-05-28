# PROMPT OPERATIVO PER CLAUDE CODE
## Progetto: CCI / AVCS — Continuous Coherence Intelligence
### Piattaforma Agentic AI per la Verifica Finanziaria e di Compliance Cross-Dominio

---

> **Come usare questo prompt**
> Incolla l'intero contenuto in Claude Code come primo messaggio in una nuova sessione, dopo aver inizializzato un repository vuoto (`git init && claude`). Claude Code userà questo documento come "north star" per tutto il ciclo di vita dell'MVP. Il prompt è scritto in italiano per coerenza con il dominio funzionale (sanità, compliance UE) ma le interfacce di codice, i nomi di variabile, i commit message e la documentazione tecnica saranno in inglese.

---

## 0. RUOLO E POSTURA OPERATIVA

Agisci come **team architetturale senior virtuale** composto da:
- **Senior AI / ML Architect** (specializzato in RAG ibridi, agentic orchestration, LLM governance)
- **Senior Cloud-Native Platform Engineer** (Kubernetes, container, observability, FinOps)
- **Senior Software Architect** (DDD, bounded context, event-driven, 12-Factor)
- **Compliance & Privacy Engineer** (EU AI Act, GDPR, ISO 42001, MDR, ISO 27001)
- **Senior Python Developer** (FastAPI, async, LangGraph, Pydantic v2, pytest)

**Postura**: pragmatica, "container-first ma non Kubernetes-obsessed", documentation-as-you-go, security-by-design. Privilegia **codice funzionante e testabile** rispetto a "framework custom". Niente prematura over-engineering: arriviamo all'MVP della Fase 1 prima della Fase 2.

**Lingua**:
- Codice, identificatori, log, commit, docstring → **inglese**
- Commenti di alto livello, README, ADR (Architecture Decision Records), prompt template degli agenti → **italiano** (per allineamento con stakeholder business: AOU Modena, Hera, SEMSOTEC, Ducati Corse, Dallara, Prada)

---

## 1. OBIETTIVO DELLA SESSIONE

Costruire **l'MVP funzionante della piattaforma CCI / AVCS** secondo l'architettura a 5 layer descritta nel documento di progetto, partendo da **Fase 0 (design) + Fase 1 (MVP)** e arrivando a un sistema **dimostrabile end-to-end** sul caso d'uso pilota:

> **Use Case pilota**: verifica di coerenza tra commitment cloud (es. report AWS/Azure mensile), budget approvato da CdA e stato della certificazione ISO 27001, con generazione automatica di alert e report what-if per il CFO. Dominio: **Hera Group / IT**.

Lo stesso core engine deve essere **ontology-agnostic**: aggiungendo un'ontologia verticale (sanità AOU Modena, compliance prodotto SEMSOTEC, motorsport Ducati Corse e lusso e Digital Product Passport Prada) il sistema deve funzionare senza modifiche al motore.

**Deliverable di sessione**:
1. Repository Python monorepo strutturato secondo `src/` layout
2. MVP eseguibile via `docker-compose up`
3. Suite di test (unit + integration + uno scenario end-to-end)
4. Demo CLI + API REST + dashboard minimale
5. Documentazione: README, ADR principali, OpenAPI 3.x, diagrammi C4 (Mermaid)
6. Compliance kit: log immutabile dimostrabile, AI Act mapping, GDPR data flow

---

## 2. PRINCIPI ARCHITETTURALI NON NEGOZIABILI

Questi principi derivano dalle Linee Guida di Modernizzazione interne (HERA DSI) e dal documento CCI/AVCS. **Sono vincolanti**:

### 2.1 Cloud-Native by Design
- **Stateless**: nessuno stato nel filesystem locale o in memoria oltre la singola richiesta. Sessioni in Redis.
- **12-Factor App**: config via env var, backing services come attached resources, graceful shutdown, dev/prod parity.
- **Container-first**: ogni servizio ha un `Dockerfile` multi-stage, distroless quando possibile. Avvio target < 10 s per microservizi.
- **Non Kubernetes-obsessed**: l'MVP gira con `docker-compose`. Helm chart + manifest K8s solo dopo la Fase 2.

### 2.2 Domain-Driven & API-First
- **Bounded context separati**: `ingestion`, `knowledge`, `retrieval`, `coherence`, `agents`, `governance`. Nessun database condiviso.
- **API-first**: OpenAPI 3.1 generata da FastAPI, ogni evento conforme a **CloudEvents 1.0** con Schema Registry.
- **Event naming**: `{domain}.{entity}.{action}.v{version}` (es. `coherence.incoherence.detected.v1`).

### 2.3 Governance AI by Design
- **Grounding obbligatorio**: nessuna affermazione generata da LLM può essere emessa senza almeno una citazione di chunk RAG. Implementare un **guardrail layer** che blocca la generazione se l'evidenza è insufficiente.
- **Human-in-the-loop**: ogni decisione che impatta budget, dichiarazioni di conformità o investimenti richiede approvazione umana esplicita.
- **Audit trail immutabile**: ogni interazione (query RAG, chunk recuperati, prompt LLM, output, decisione utente) loggata in un append-only store con hash chain (preparare il terreno per certificazione ISO 42001).
- **Explainability**: ogni output strutturato include `sources[]`, `confidence`, `reasoning_steps[]`, `model_version`, `prompt_version`.

### 2.4 Resilienza SRE
- **Health checks** standardizzati: `/health/live`, `/health/ready`, `/health/startup`.
- **Circuit breaker** (libreria `purgatory` o equivalente) su tutte le dipendenze esterne (LLM API, vector DB, graph DB).
- **Retry con backoff esponenziale + jitter**, max 3-5 tentativi, mai su errori 4xx non-retriable.
- **Rate limiting** in ingresso (slowapi su FastAPI).
- **Observability**: metriche Prometheus, log strutturati JSON con `trace_id`, tracing OpenTelemetry.

### 2.5 Performance & TCO
- **Startup target**: < 3 s per ogni servizio Python (uvicorn + Pydantic v2).
- **Memory baseline**: < 256 MB per servizio idle.
- **Costo per verifica**: target < 0,02 € (singolo provider LLM via Anthropic API con prompt caching, batch e selettività degli step).
- **Right-sizing**: ogni servizio espone metriche di utilizzo CPU/memoria.
- **Cost control**: ogni chiamata LLM è metricata (`cci_llm_tokens_total{direction=in|out, model}`) e il consumo aggregato è alertabile contro soglie giornaliere per dominio.

---

## 3. STACK TECNOLOGICO DI RIFERIMENTO

**Vincolante salvo deroga motivata in un ADR**:

| Layer | Tecnologia | Motivazione |
|---|---|---|
| Linguaggio core | **Python 3.12** | Dominio data/AI, ecosistema RAG maturo |
| Framework API | **FastAPI** + **Uvicorn** | OpenAPI nativo, async, performance |
| Validazione | **Pydantic v2** | Type-safe, perf, integrazione FastAPI |
| Agentic orchestration | **LangGraph** (preferito) o **CrewAI** | Graph-based, stato esplicito, debuggabile |
| LLM client | **Anthropic Python SDK** (ufficiale) | Provider unico, prompt caching, retry nativo, streaming |
| RAG framework | **LlamaIndex** + custom logic | Maturità, hybrid retrieval out-of-the-box |
| Vector DB | **Qdrant** | Self-hosted, performance, filtri metadata |
| Graph DB | **Neo4j 5.x** Community | Temporal property graph, Cypher |
| Document DB / Operational DB | **MongoDB 7.x** (replica set) | Schema flessibile per documenti CCI, transazioni ACID, change streams, indici geospaziali e text, time-series collections native |
| Time-series | **MongoDB Time Series Collections** | Nativamente in MongoDB 5+, niente componente extra |
| Embeddings | `all-MPNet-base-v2` (dense) + **BM25** (sparse) | Standard, locali, no lock-in |
| Reranker | **Cohere Rerank** API o **bge-reranker-v2-m3** locale | Qualità retrieval |
| LLM (unico provider) | **Claude Sonnet 4.6** via **Anthropic API** (`claude-sonnet-4-6`) | Sia per il Planner (parsing NL→plan) sia per il Generator (spiegazioni con citation enforcement). Chiave `ANTHROPIC_API_KEY` da Vault, mai hardcoded |
| OCR / Parsing | **Unstructured.io** + **Tesseract** + **Donut** | Multi-formato, on-prem |
| NER | **spaCy** + **GLiNER** finetuned | Codici ISO, date, importi (pseudonimizzazione PII prima dell'invio all'API) |
| Messaging | **Redis Streams** (MVP) → **Kafka** (Fase 3) | Backbone eventi |
| Cache / Session | **Redis 7** | Cache distribuita, session externalization |
| Object storage | **MinIO** (S3-compatible) | Portabilità multi-cloud |
| Audit log | **MongoDB append-only** + hash chain SHA-256 | Collection con role-based write-only, transazioni per integrità della catena, verifica end-to-end via script |
| LangGraph checkpoint | **`langgraph-checkpoint-mongodb`** | Persistenza dello stato del grafo su MongoDB |
| Observability | **OpenTelemetry** + **Prometheus** + **Grafana** + **Tempo** | CNCF standard |
| Secrets | **HashiCorp Vault** (locale) / External Secrets Operator | `ANTHROPIC_API_KEY`, credenziali DB, mai hardcoded in repo |
| Frontend | **Next.js 16.2** (App Router, Turbopack default, PPR opt-in) + **TypeScript strict** + **shadcn/ui** (Radix UI + Tailwind) + **TanStack Query** | Consumo REST da FastAPI via client tipizzato auto-generato da OpenAPI; AI Improvements (AGENTS.md, next-browser CLI, Browser Log Forwarding) integrate nel ciclo agent-driven |
| Containerizzazione | **Docker** + **docker-compose** | MVP locale |
| Test | **pytest** + **pytest-asyncio** + **httpx** + **testcontainers** (MongoDB, Neo4j, Qdrant, Redis) | Test reali con DB veri |
| Lint/Format | **Ruff** + **mypy strict** | Qualità imposta |
| Dependency mgmt | **uv** o **Poetry** | Lockfile riproducibile |

---

## 4. ARCHITETTURA TARGET — 5 LAYER

Implementare in ordine. Ogni layer deve essere **testabile in isolamento** e avere la sua suite di test prima di passare al successivo.

### Layer 1 — Data Ingestion
**Servizio**: `ingestion-service`
- Endpoint `POST /documents` per upload (PDF, DOCX, XLSX, HTML, email .eml)
- Pipeline asincrona: estrazione testo (Unstructured.io) → OCR fallback (Tesseract/Donut) → NER (spaCy + GLiNER) → chunking semantico (paragrafi logici, NON sliding window) → embedding dense + sparse → indicizzazione Qdrant + estrazione tuple strutturate verso Neo4j
- Output evento CloudEvent: `ingestion.document.indexed.v1` con `document_id`, `entities[]`, `metadata{}`
- Pseudonimizzazione GDPR-aware: detection PII automatica con flag e mascheramento configurabile

### Layer 2 — Knowledge Representation
**Servizio**: `knowledge-service`
Tre store con responsabilità distinte:

**(a) Vector Store (Qdrant)**
- Collection per `bounded_context` (es. `hera_it`, `aou_clinical`)
- Payload: `chunk_id`, `doc_id`, `text`, `valid_from`, `valid_to`, `version`, `source_type`, `cert_ref[]`, `domain`, `confidentiality`

**(b) Temporal Knowledge Graph (Neo4j)**
- Schema property graph dove **ogni relazione** ha `valid_from`, `valid_to`, `version`, `confidence`, `provenance_chunk_id`
- Entità core: `Document`, `Certification`, `Asset`, `Contract`, `Budget`, `Investment`, `KPI`, `Stakeholder`, `Regulation`, `Trial`, `Project`
- Ontologia verticale modulare caricabile via file YAML al boot (vedi sezione 6)
- Motore di inferenza temporale: Cypher queries parametrizzate per drift detection

**(c) Time-Series (MongoDB Time Series Collections)**
- Snapshot di stato su collection time-series nativa di MongoDB 5+ (`metaField`, `timeField`, `granularity: "hours"`)
- Esempi: budget consumato per mese, scadenze certificazioni in arrivo, throughput coda di ingestion
- Retention policy via TTL index sul `timeField`; storage compresso a colonne nativo

### Layer 3 — Agentic Orchestration
**Servizio**: `agent-orchestrator`
Implementare con **LangGraph**. Cinque agenti come nodi di un grafo di stato:

```
                    ┌──────────────┐
            ┌──────▶│   Planner    │──────┐
            │       └──────────────┘      │
            │                              ▼
       ┌─────────┐                   ┌──────────┐
       │  Audit  │◀──────────────────│ Retriever│
       └─────────┘                   └──────────┘
            ▲                              │
            │                              ▼
            │                       ┌──────────┐
            │                       │ Verifier │
            │                       └──────────┘
            │                              │
            │                              ▼
            │                       ┌──────────┐
            └───────────────────────│ Generator│
                                    └──────────┘
```

**Specifica di ogni agente**:

- **Planner**: input = evento trigger (timer, nuovo documento, regola normativa aggiornata). Output = `verification_plan` (sequenza di step strutturati). NON usa LLM per decisioni deterministiche; usa LLM solo per parsing di richieste in linguaggio naturale (es. da utente).
- **Retriever**: input = step del plan. Output = `chunks[]` ranked. Pipeline = hybrid search (dense + BM25) → filtro temporale → cross-encoder rerank → top-K (default 8).
- **Verifier**: input = `chunks[]` + ontologia rilevante. Output = `incoherences[]` strutturate `(entity_a, entity_b, rule_violated, severity, evidence_chunks[], temporal_context)`. **Logica deterministica** (motore a regole Datalog-like in Python, es. `pyDatalog` o regole custom su Cypher). NON usa LLM per decidere se c'è incoerenza.
- **Generator**: input = `incoherences[]`. Output = spiegazioni naturali, executive summary, report what-if. **Grounding forzato**: ogni frase generata deve contenere un riferimento `[chunk_id]`. Implementare un post-processor che rifiuta output senza citazioni.
- **Audit**: registra in append-only log con hash chain `(prev_hash, event, payload, timestamp, actor)`. Esporre endpoint di verifica integrità.

### Layer 4 — RAG + Reasoning
Modulo trasversale (libreria interna `cci_rag`):
- **Hybrid retrieval**: dense (cosine similarity Qdrant) + sparse (BM25 in-memory o Elasticsearch) con score fusion **Reciprocal Rank Fusion (RRF)**
- **Cross-encoder reranker** configurabile (Cohere API o `bge-reranker-v2-m3` locale via sentence-transformers)
- **Cache temporale**: TTL su Redis, chiave = hash(query, time_window, filters)
- **Citation enforcer**: parser che valida la presenza di `[source: chunk_id]` in ogni frase dell'output LLM, blocca e ritriggera con prompt rafforzato in caso di assenza

### Layer 5 — Governance & Feedback
**Servizio**: `governance-service`
- Audit log append-only su collection MongoDB con utente DB **insert-only** (revoca `update`/`delete`), transazioni ACID su replica set per integrità della catena hash SHA-256
- Verifica catena via script `scripts/verify_audit_chain.py` (legge tutti i documenti ordinati per `seq`, ricalcola gli hash, rileva tampering)
- Export immutabile firmato (HMAC) per audit esterni
- API HITL: `POST /decisions/{id}/approve|reject` con motivazione obbligatoria
- Dashboard alert con filtro gerarchico per ruolo (CFO vede solo impatti > soglia configurabile)
- **AI Act compliance manifest**: file YAML versionato che mappa ogni feature ai requisiti dell'art. 9-15 del Reg. UE 2024/1689

### 4.6 — Strategia LLM: provider unico Anthropic (Claude Sonnet 4.6)

CCI/AVCS utilizza **un solo provider LLM** in tutte le fasi del ciclo di verifica: **Anthropic API** con modello **`claude-sonnet-4-6`**.

**Motivazione**:
- Un solo SDK, una sola superficie API → meno bug, meno test path, semplicità di audit
- Un solo accordo contrattuale di compliance da gestire
- Un solo set di metriche di costo da monitorare
- Nessun routing condizionale "locale vs cloud" che possa sfuggire al guardrail di citation enforcement

**Configurazione**:
- Variabile d'ambiente: `ANTHROPIC_API_KEY` (caricata da Vault, mai nel repo, mai nei log)
- Modello: `claude-sonnet-4-6` (parametrizzabile via `CCI_LLM_MODEL` per consentire upgrade futuri)
- Endpoint: `https://api.anthropic.com/v1/messages` (default ufficiale)
- Prompt caching abilitato per riusare il contesto di sistema (ontologie, regole) attraverso le chiamate
- Streaming opzionale per il Generator quando l'output è destinato a una UI

**Wrapper canonico** `libs/cci-llm/src/cci_llm/client.py`:
- Una sola classe `LLMClient` con metodi `complete(messages, *, system, max_tokens, response_format)` e `complete_streamed(...)`
- Retry esponenziale con jitter su errori 5xx/429 (max 3 tentativi)
- Citation enforcement post-call obbligatorio per ogni completamento destinato all'utente
- Audit log automatico: ogni chiamata produce un record `llm.call.v1` con `prompt_version`, `model`, `tokens_in`, `tokens_out`, `latency_ms`, `correlation_id` (mai il contenuto del prompt in chiaro)
- Pseudonimizzazione PII **prima** dell'invio: il wrapper rifiuta payload che contengono pattern PII non tokenizzati

**Vietato** (regola architetturale R3 del kit guardrail):
- Importare direttamente `anthropic`, `openai`, `litellm` fuori da `libs/cci-llm/` o `/tests/`
- Disabilitare il citation enforcement (`strict=False`) fuori dai test
- Hardcoded `model = "claude-..."` in luoghi diversi dalla configurazione centralizzata

**Test integration "live"**:
- Skipped se `ANTHROPIC_API_KEY` non è impostata (`pytest.skip`)
- Quando attivo, esegue una chiamata reale al modello per validare formato e citation enforcement end-to-end
- Marcato con `@pytest.mark.live_llm` per esclusione dalla CI offline

---

## 5. RAG-COHERENCE LOOP

L'innovazione di categoria. Implementare come ciclo asincrono:

1. **Retrieval** iniziale → chunks candidati
2. **Coherence check** → `incoherences[]` strutturate
3. **Generation** → spiegazioni con citation enforcement
4. **HITL** (opzionale): utente corregge/aggiorna documenti
5. **Feedback ingestion**: il pattern di incoerenza viene salvato in un "incoherence memory store" (Qdrant collection dedicata) e usato come **few-shot example** per affinare future query Retriever
6. **Re-verification automatica** ogni N ore o su evento

Implementare con un job scheduler (APScheduler o Celery beat) che innesca il loop su trigger event-driven.

---

## 6. ONTOLOGIE VERTICALI

Definire un formato YAML standardizzato per le ontologie di dominio. Esempio:

```yaml
# ontologies/hera_it.yaml
domain: hera_it
version: 1.0.0
entities:
  - name: CloudCommitment
    properties: [provider, amount_eur, period_start, period_end, contract_ref]
  - name: ISO27001Certification
    properties: [issuer, valid_from, valid_to, scope, version]
  - name: BudgetApproval
    properties: [year, amount_eur, approved_by, approval_date, category]
relations:
  - type: COVERED_BY
    from: CloudCommitment
    to: BudgetApproval
    temporal: true
rules:
  - id: R001
    description: "Cloud commitment must be covered by approved budget"
    when: "CloudCommitment(amount) > sum(BudgetApproval.amount WHERE year=CloudCommitment.year)"
    severity: HIGH
    domain: financial
  - id: R002
    description: "ISO 27001 must be valid during entire cloud usage period"
    when: "exists(CloudCommitment.period) AND NOT exists(ISO27001Certification WHERE valid_from <= period_start AND valid_to >= period_end)"
    severity: CRITICAL
    domain: compliance
```

Caricamento dinamico all'avvio del `verifier-service` via Pydantic models. **Le ontologie devono poter essere aggiunte senza ridistribuire il codice**.

---

## 7. STRUTTURA DEL REPOSITORY

Crea un **monorepo Python** con questa struttura:

```
cci-avcs/
├── README.md
├── docker-compose.yml
├── docker-compose.override.yml.example
├── .env.example
├── pyproject.toml                 # uv workspace
├── Makefile                       # comandi standard (test, run, lint, demo)
├── docs/
│   ├── adr/                       # Architecture Decision Records
│   │   ├── 0001-use-langgraph.md
│   │   ├── 0002-temporal-graph-neo4j.md
│   │   └── 0003-grounding-enforcement.md
│   ├── architecture/
│   │   ├── c4-context.mmd         # Mermaid C4
│   │   ├── c4-container.mmd
│   │   └── data-flow.mmd
│   ├── compliance/
│   │   ├── ai-act-mapping.yaml
│   │   ├── gdpr-data-flow.md
│   │   └── iso42001-roadmap.md
│   └── ontologies/
│       ├── hera_it.yaml
│       ├── aou_clinical.yaml
│       └── semsotec_product.yaml
├── services/
│   ├── ingestion/
│   │   ├── src/cci_ingestion/
│   │   │   ├── api.py
│   │   │   ├── pipeline.py
│   │   │   ├── parsers/
│   │   │   ├── extractors/
│   │   │   └── publishers.py
│   │   ├── tests/
│   │   └── Dockerfile
│   ├── knowledge/
│   │   ├── src/cci_knowledge/
│   │   │   ├── vector_store.py
│   │   │   ├── temporal_graph.py
│   │   │   ├── timeseries.py
│   │   │   └── api.py
│   │   ├── tests/
│   │   └── Dockerfile
│   ├── retrieval/
│   │   ├── src/cci_retrieval/
│   │   │   ├── hybrid.py
│   │   │   ├── reranker.py
│   │   │   ├── temporal_filter.py
│   │   │   └── cache.py
│   │   ├── tests/
│   │   └── Dockerfile
│   ├── coherence/
│   │   ├── src/cci_coherence/
│   │   │   ├── engine.py
│   │   │   ├── rules.py
│   │   │   ├── ontology_loader.py
│   │   │   └── temporal_inference.py
│   │   ├── tests/
│   │   └── Dockerfile
│   ├── agents/
│   │   ├── src/cci_agents/
│   │   │   ├── orchestrator.py     # LangGraph state machine
│   │   │   ├── planner.py
│   │   │   ├── retriever_agent.py
│   │   │   ├── verifier_agent.py
│   │   │   ├── generator_agent.py
│   │   │   ├── audit_agent.py
│   │   │   ├── guardrails.py       # citation enforcer
│   │   │   └── prompts/            # versioned prompt templates
│   │   ├── tests/
│   │   └── Dockerfile
│   └── governance/
│       ├── src/cci_governance/
│       │   ├── audit_log.py        # hash chain
│       │   ├── hitl.py
│       │   ├── ai_act.py
│       │   └── api.py
│       ├── tests/
│       └── Dockerfile
├── libs/
│   ├── cci-common/                 # types, schemas, CloudEvents
│   │   ├── src/cci_common/
│   │   │   ├── events.py           # CloudEvents 1.0 models
│   │   │   ├── domain.py           # core domain models
│   │   │   └── observability.py    # OTel setup
│   │   └── tests/
│   └── cci-llm/
│       ├── src/cci_llm/
│       │   ├── client.py           # Anthropic SDK wrapper (Claude Sonnet 4.6)
│       │   ├── citation_parser.py
│       │   ├── prompt_versioning.py
│       │   └── pii_redaction.py    # pseudonimizzazione pre-API
│       └── tests/
├── frontend/                       # Next.js 16.2 (App Router, Turbopack) + TS strict + shadcn/ui
│   ├── app/
│   │   ├── (dashboard)/page.tsx    # dashboard incoerenze
│   │   ├── hitl/page.tsx           # human-in-the-loop queue
│   │   ├── audit/page.tsx          # audit trail viewer
│   │   └── layout.tsx
│   ├── components/
│   │   ├── ui/                     # shadcn/ui generated (button, card, table…)
│   │   ├── incoherence-card.tsx
│   │   ├── chunk-citation.tsx
│   │   └── hitl-approval-form.tsx
│   ├── lib/
│   │   ├── api-client.ts           # generated from OpenAPI spec
│   │   └── query-client.ts         # TanStack Query setup
│   ├── tailwind.config.ts
│   ├── components.json             # shadcn/ui config
│   └── package.json
├── infra/
│   ├── docker/
│   │   ├── neo4j.Dockerfile
│   │   └── init-scripts/
│   ├── k8s/                        # placeholder, Fase 2
│   └── terraform/                  # placeholder, Fase 3
├── scripts/
│   ├── seed_demo_data.py
│   ├── run_demo_scenario.py
│   └── verify_audit_chain.py
└── tests/
    └── e2e/
        ├── test_hera_cloud_scenario.py
        └── test_grounding_enforcement.py
```

---

## 8. SCENARIO DI DEMO END-TO-END (HERA CLOUD)

Lo script `scripts/run_demo_scenario.py` deve essere **eseguibile in un solo comando** dopo `docker-compose up` e mostrare:

1. **Ingestion** di 4 documenti di test (forniti in `tests/fixtures/`):
   - `bilancio_preventivo_2026.pdf` con riga "Cloud Infrastructure: 800.000 €"
   - `aws_commitment_report_q1_2026.pdf` con commitment 920.000 €
   - `iso27001_cert_hera.pdf` con `valid_to: 2026-03-31`
   - `policy_finanziaria_v3.docx` aggiornata al 2026-02-10

2. **Indicizzazione** automatica: estrazione entità, costruzione del Temporal KG con archi temporali, embedding in Qdrant.

3. **Trigger** del Planner: simula evento "fine mese Q1 2026".

4. **Verifica**: il Coherence Engine deve rilevare **almeno** queste 2 incoerenze:
   - `R001`: commitment 920k € > budget approvato 800k € (overrun 15%)
   - `R002`: ISO 27001 scade il 31/03/2026 ma il commitment copre Q2 2026 senza rinnovo registrato

5. **Generazione**: il Generator produce un alert markdown con:
   - Spiegazione in italiano
   - Citazioni esplicite `[bilancio_preventivo_2026.pdf #chunk_03]`
   - Raccomandazione concreta (es. "avviare procedura rinnovo ISO entro 2026-02-28")
   - Simulazione what-if: "se il rinnovo slitta a 04-15, l'esposizione regolatoria è di X giorni"

6. **Audit**: ogni step è loggato; lo script `verify_audit_chain.py` ricalcola gli hash e conferma l'integrità.

**Output atteso**: un file `demo_output/hera_q1_2026_report.md` + un dump JSON del KG temporale + il log immutabile firmato.

---

## 9. REQUISITI DI COMPLIANCE (AI ACT, GDPR, ISO 42001)

Da considerare **fin dall'MVP**, non come afterthought:

### 9.1 EU AI Act (Reg. 2024/1689)
Il sistema rientra in "alto rischio" (uso in compliance e decisioni finanziarie). Implementare:
- **Art. 9 — Risk management**: documento `docs/compliance/risk-assessment.md` con metodologia ISO 31000-like.
- **Art. 10 — Data governance**: tracciabilità dataset, qualità input, bias detection sui documenti.
- **Art. 12 — Record keeping**: audit log immutabile (già nel Layer 5).
- **Art. 13 — Transparency**: ogni output utente deve esporre `model_version`, `prompt_version`, `confidence`, `sources[]`.
- **Art. 14 — Human oversight**: HITL hard-gate prima di azioni con impatto > soglia.
- **Art. 15 — Accuracy & robustness**: suite di test di regressione su 50+ scenari di incoerenza nota.

### 9.2 GDPR
- Pseudonimizzazione automatica all'ingestion (mascheramento PII rilevate con NER) **prima** di qualunque invio all'Anthropic API.
- Data minimization: il LLM riceve solo i chunk strettamente necessari (non l'intero documento).
- Right to erasure: API `DELETE /documents/{id}` che propaga cancellazione a Qdrant + Neo4j + MongoDB (con marcatura "redacted" sull'audit log, non vera cancellazione per integrità chain).
- Data residency: poiché tutte le chiamate LLM passano dall'Anthropic API, la conformità si fonda su tre meccanismi: (a) **pseudonimizzazione PII** prima dell'invio, (b) accordi contrattuali Anthropic (zero retention, no training su dati cliente, dove applicabili), (c) `ANTHROPIC_API_KEY` dell'organizzazione cliente caricata via Vault, mai esposta nel repo. Per scenari con vincoli di residenza stretti (es. dati clinici AOU), valutare l'instradamento via endpoint regionali Anthropic se disponibili; in caso negativo, escalare a humanintheloop e bloccare l'invio.

### 9.3 ISO 42001 (roadmap)
- AIMS (AI Management System) preparato: policy doc, role assignment, monitoring KPI definiti in `docs/compliance/iso42001-roadmap.md`.

---

## 10. KPI MISURABILI (BUILT-IN)

L'MVP deve esporre questi KPI via endpoint Prometheus su `/metrics`:

| KPI | Target Fase 1 | Metrica Prometheus |
|---|---|---|
| Precisione rilevamento incoerenze (vs ground truth) | > 80% | `cci_coherence_precision` |
| Recall | > 75% | `cci_coherence_recall` |
| Tempo medio di verifica end-to-end | < 30 s (MVP) | `cci_verification_duration_seconds` |
| Fattore di allucinazione (% frasi LLM senza citazione valida) | < 1% | `cci_grounding_violations_total` |
| Costo per verifica completa | < 0,03 € (MVP) | `cci_verification_cost_eur` |
| Uptime servizi | 99% | standard up/down |
| Tempo di startup container | < 5 s | `cci_service_startup_seconds` |

---

## 11. ORDINE DI ESECUZIONE (ROADMAP DI SESSIONE)

Procedi **in questo ordine**. Dopo ogni step fai un commit con messaggio convenzionale (`feat:`, `chore:`, `docs:`, `test:`) e aggiorna il README.

**Step 1 — Scaffolding** (30 min)
- Inizializza monorepo con `uv` workspace
- Crea struttura cartelle, `pyproject.toml`, `Makefile`, `docker-compose.yml`
- Imposta `ruff`, `mypy strict`, `pytest`, pre-commit hooks
- README iniziale + ADR-0001 sullo stack scelto

**Step 2 — Common library** (45 min)
- `libs/cci-common`: CloudEvents 1.0 schemas, domain models (Pydantic v2), OTel setup
- Tests unitari su serializzazione eventi

**Step 3 — Infra docker-compose** (30 min)
- Neo4j, Qdrant, **MongoDB 7 con replica set di 1 nodo** (necessario per le transazioni multi-document), Redis, MinIO, Prometheus, Grafana, Tempo
- Healthchecks, volumes, networks dedicate
- Init script di MongoDB per: (a) inizializzare il replica set, (b) creare i database `cci_governance` e `cci_operational`, (c) creare utente write-only su `audit_log`, (d) creare indici (`audit_log.seq` unique, `audit_log.correlation_id`, `audit_log.ts`)

**Step 4 — Ingestion service** (90 min)
- Pipeline Unstructured → NER → chunking → embedding (modelli locali via sentence-transformers)
- Pubblicazione evento `ingestion.document.indexed.v1` su Redis Streams
- Tests con `testcontainers` su Qdrant e Neo4j reali

**Step 5 — Knowledge service** (90 min)
- Repository pattern su Neo4j (Cypher temporale) + Qdrant
- Caricamento ontologia YAML
- Endpoint `GET /entities`, `GET /relations`, `POST /query/temporal`

**Step 6 — Retrieval module** (60 min)
- Hybrid search (Qdrant + BM25 con `rank_bm25`)
- RRF fusion
- Cross-encoder reranker (locale di default)
- Cache Redis con TTL
- Tests di qualità retrieval su corpus fixture

**Step 7 — Coherence engine** (90 min)
- Loader ontologie YAML → modelli Pydantic
- Motore regole deterministico (Python puro, no LLM)
- Inferenza temporale via Cypher
- Suite di 20 test su regole note

**Step 8 — Agents (LangGraph)** (120 min)
- State machine LangGraph con 5 nodi
- Checkpointer `langgraph-checkpoint-mongodb` su collection `cci_governance.langgraph_checkpoints`
- Prompt templates versionati in `prompts/v1/`
- Citation enforcer come post-processor (vincolante, `strict=True`)
- **Anthropic SDK wrapper** in `libs/cci-llm/src/cci_llm/client.py`: una sola classe `LLMClient` con metodi `complete()` e `complete_streamed()`, modello fisso `claude-sonnet-4-6`, prompt caching abilitato, retry esponenziale, audit log automatico di ogni chiamata (no provider switching, no fallback su altri vendor)
- Tests con LLM mockato (`anthropic.Anthropic` mock) + un test integration "live" che richiede `ANTHROPIC_API_KEY` in env e gira solo se presente

**Step 9 — Governance service** (60 min)
- Audit log append-only con hash chain SHA-256
- API HITL
- Endpoint AI Act manifest
- Script di verifica integrità

**Step 10 — Frontend Next.js 16.2** (90 min)
- Init: `pnpm create next-app@latest frontend --typescript --tailwind --app --eslint --turbopack`
- create-next-app v16.2 genera automaticamente `AGENTS.md` con docs version-matched per Claude Code: **non rimuovere**, è la fonte di verità per gli agenti che lavorano sul frontend
- shadcn/ui setup: `pnpm dlx shadcn-ui@latest init` con tema neutro
- Componenti shadcn da generare: `button`, `card`, `table`, `dialog`, `form`, `badge`, `toast`, `tabs`, `skeleton`, `alert`
- Installare `next-browser` skill in Claude Code: `npx skills add vercel-labs/next-browser` — abilita ispezione di React tree, PPR shells, network e log direttamente dal terminale dell'agente (richiamabile con `/next-browser`)
- Abilitare Browser Log Forwarding: i log del browser vengono inoltrati al terminale del dev server, l'agente li vede senza screenshot manuali
- Generazione client TypeScript dai contratti OpenAPI dei servizi (`pnpm dlx openapi-typescript-codegen`)
- TanStack Query per data fetching/caching, niente SWR
- Quattro pagine: `/` (overview dashboard con PPR static shell + streaming dinamico), `/incoherences` (lista + dettaglio), `/hitl` (queue approvazione con form), `/audit` (audit trail viewer con verifica hash chain in tempo reale)
- Nessuna Server Action: l'app frontend consuma **solo** REST API tipizzate dei servizi FastAPI (architettura BFF-less per MVP, contratti OpenAPI come source of truth)
- Tests Playwright sui 4 happy-path principali
- **React 19** richiesto (peer dep di Next.js 16+): verificare che tutte le dipendenze siano compatibili

**Step 11 — Scenario end-to-end** (60 min)
- Fixture data Hera Q1 2026
- Script demo eseguibile
- Documentazione step-by-step nel README

**Step 12 — Compliance kit** (45 min)
- AI Act mapping YAML
- GDPR data flow Mermaid
- Risk assessment doc

**Step 13 — Polish & docs** (45 min)
- Diagrammi C4 finali
- ADR mancanti
- README "Quick Start" testato

---

## 12. DEFINITION OF DONE (per ogni componente)

Un componente è "done" se:
- [ ] Codice in `src/` segue layout standard, type-hinted, passa `ruff check` e `mypy --strict`
- [ ] Test unitari con coverage > 80% (misurata con `coverage.py`)
- [ ] Almeno un integration test con `testcontainers` su dipendenze reali
- [ ] Dockerfile multi-stage, immagine finale < 300 MB, distroless o slim base
- [ ] Health checks `/health/live`, `/health/ready`, `/health/startup` implementati
- [ ] Metriche Prometheus esposte su `/metrics`
- [ ] Log strutturati JSON con `trace_id`, `span_id`, `service`, `version`
- [ ] OpenAPI 3.1 generata automaticamente da FastAPI, accessibile su `/docs`
- [ ] README di servizio con esempi `curl`
- [ ] Commit firmato (DCO o GPG)
- [ ] Una entry nell'audit log per ogni operazione di scrittura

---

## 13. ANTI-PATTERN DA EVITARE TASSATIVAMENTE

- ❌ **No "framework custom" interni** se esistono soluzioni open-source mature (LangGraph, LlamaIndex)
- ❌ **No condivisione di database tra servizi**: divieto assoluto come da linee guida HERA
- ❌ **No prompt hardcoded sparsi nel codice**: usare `prompts/v{n}/{agent}.j2` versionati
- ❌ **No chiamate LLM senza grounding**: blocco hard al guardrail level
- ❌ **No credenziali in `.env` committato**: solo `.env.example` con placeholder
- ❌ **No `print()` per logging**: solo logger strutturato
- ❌ **No `time.sleep` per attese su servizi**: usare healthcheck + retry
- ❌ **No stato in memoria del processo**: tutto in Redis o store dedicato
- ❌ **No "TODO" o "FIXME" senza issue tracciata**

---

## 14. ITERAZIONE CON ME (UTENTE)

Quando hai dubbi architetturali o di prioritizzazione:
1. **NON inventare**: chiedi.
2. Se la domanda è bloccante, fermati e proponi 2-3 alternative motivate, indicando la tua preferenza e perché.
3. Se la domanda è non bloccante, prendi la decisione, registrala in un ADR e procedi.

Al termine di ogni Step (sezione 11) **fai un riepilogo conciso**:
- Cosa è stato fatto
- Decisioni rilevanti prese (e perché)
- Cosa farai nello step successivo
- Eventuali rischi/blocchi

---

## 15. AVVIO

Per partire:
1. Conferma di aver letto e compreso questo prompt.
2. Stampa un piano esecutivo conciso dei primi 3 step.
3. Inizia dallo **Step 1 (Scaffolding)**.

Ricorda: stiamo costruendo **una nuova categoria di prodotto** (Continuous Coherence Verification System), non un altro chatbot RAG. Ogni decisione tecnica deve essere coerente con l'obiettivo: **zero hallucination libera, auditability end-to-end, portabilità multi-cloud, sostenibilità del TCO**.

**Build it like it's already in production at Hera, AOU Modena e SEMSOTEC.**
