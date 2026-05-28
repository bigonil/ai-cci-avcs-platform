---
name: cci-agentic-langgraph
description: Use this skill whenever you implement, modify, or debug the agentic orchestration layer of CCI/AVCS — the 5-agent state machine built with LangGraph. Trigger on imports of langgraph, langchain_core, on files under services/agents/, on file names like orchestrator.py, planner.py, retriever_agent.py, verifier_agent.py, generator_agent.py, audit_agent.py, on mentions of Planner, Retriever, Verifier, Generator, Audit agent, state machine, agent graph, checkpointing, or LangGraph. This skill enforces rules that keep agentic orchestration deterministic, debuggable, and auditable — every agent has atomic responsibility, explicit state, contract-driven I/O, and never bypasses the deterministic Verifier engine in favor of so-called smart LLM judgment.
license: Internal — CCI/AVCS Project
---

# CCI/AVCS Agentic Orchestration

I cinque agenti non sono cinque LLM in fila. Sono cinque **ruoli** con responsabilità atomica, di cui solo due (Planner per NL parsing e Generator) usano effettivamente un LLM. Il resto è codice deterministico orchestrato da LangGraph come state machine.

## Lo state graph

```
                        ┌──────────────┐
            event ─────►│   Planner    │──────┐
                        └──────────────┘      │
                                              ▼
       ┌─────────┐                     ┌──────────────┐
       │  Audit  │◄─────(all nodes)────│  Retriever   │
       └─────────┘                     └──────────────┘
            ▲                                  │
            │                                  ▼
            │                          ┌──────────────┐
            │                          │   Verifier   │  ← deterministic, no LLM
            │                          └──────────────┘
            │                                  │
            │                          ┌───────┴───────┐
            │                          │               │
            │                  no incoherence    incoherences > 0
            │                          │               │
            │                          ▼               ▼
            │                       (END)      ┌──────────────┐
            │                                  │  Generator   │
            │                                  └──────────────┘
            │                                          │
            │                                          ▼
            └──────────────────────────────────── (HITL gate) ──► END
```

## State schema (Pydantic v2)

Lo stato del grafo è UN solo oggetto, esplicito, immutabile fra le transizioni:

```python
# services/agents/src/cci_agents/state.py
from __future__ import annotations
from datetime import datetime
from pydantic import BaseModel, Field
from typing import Literal
from cci_common.domain import Chunk, Incoherence, Explanation
from cci_common.events import TriggerEvent

AgentName = Literal["planner", "retriever", "verifier", "generator", "audit"]

class VerificationStep(BaseModel):
    step_id: str
    rule_id: str | None
    query_hint: str
    temporal_window: tuple[str, str]  # ISO dates
    domain: str

class AgentState(BaseModel):
    # immutable input
    trigger: TriggerEvent
    correlation_id: str
    started_at: datetime

    # progressive enrichment
    plan: list[VerificationStep] = Field(default_factory=list)
    current_step: int = 0
    retrieved_chunks: dict[str, list[Chunk]] = Field(default_factory=dict)  # step_id → chunks
    incoherences: list[Incoherence] = Field(default_factory=list)
    explanation: Explanation | None = None
    hitl_required: bool = False
    
    # observability
    transitions: list[dict] = Field(default_factory=list)
    
    class Config:
        frozen = False  # LangGraph muta lo state, ma è OK perché è single-threaded per run
```

## Pattern del grafo

```python
# services/agents/src/cci_agents/orchestrator.py
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.mongodb import AsyncMongoDBSaver  # langgraph-checkpoint-mongodb
from motor.motor_asyncio import AsyncIOMotorClient

def build_orchestrator(deps: Deps) -> CompiledGraph:
    graph = StateGraph(AgentState)

    graph.add_node("planner",   make_planner_node(deps))
    graph.add_node("retriever", make_retriever_node(deps))
    graph.add_node("verifier",  make_verifier_node(deps))
    graph.add_node("generator", make_generator_node(deps))
    # audit is a side-effect hook, not a node — see below

    graph.set_entry_point("planner")
    graph.add_edge("planner", "retriever")
    graph.add_edge("retriever", "verifier")
    graph.add_conditional_edges(
        "verifier",
        route_after_verifier,
        {"generate": "generator", "end_no_incoherence": END},
    )
    graph.add_edge("generator", END)

    # MongoDB checkpoint persistence — required for HITL pause/resume and audit replay
    mongo_client = AsyncIOMotorClient(deps.mongodb_uri)
    checkpointer = AsyncMongoDBSaver(
        client=mongo_client,
        db_name="cci_governance",
        checkpoint_collection_name="langgraph_checkpoints",
        writes_collection_name="langgraph_checkpoint_writes",
    )
    return graph.compile(checkpointer=checkpointer)

def route_after_verifier(state: AgentState) -> str:
    return "generate" if state.incoherences else "end_no_incoherence"
```

**Setup MongoDB per il checkpointer**:
- Database: `cci_governance` (lo stesso dell'audit log, ma collections separate)
- Collections: `langgraph_checkpoints` + `langgraph_checkpoint_writes`
- Indici: gestiti automaticamente dal package `langgraph-checkpoint-mongodb` al primo write
- Permessi: il governance service ha un utente DB distinto da `cci_audit_writer` con permessi CRUD pieni su queste due collection (i checkpoint sono mutabili by design — non sono l'audit log)

## Regole per ogni agente

### 1. Planner — `planner_agent.py`
**Responsabilità**: trasformare un trigger (timer, evento, NL request) in `list[VerificationStep]`.

- **No LLM** per trigger noti (timer, evento `document.indexed.v1`, `regulation.updated.v1`). Usa mapping deterministico.
- **LLM solo** se il trigger è una richiesta NL utente. In quel caso usa `cci_llm.LLMClient` (Claude Sonnet 4.6) con structured output forzato via prompt template che richiede JSON con schema esplicito; la response viene parsata in `VerificationPlan` Pydantic.
- Output: lista non vuota di VerificationStep, ognuno con un `rule_id` collegato all'ontologia caricata.
- Audit: log evento `agent.planner.plan_created.v1` con `correlation_id`, `step_count`.

### 2. Retriever — `retriever_agent.py`
**Responsabilità**: per ogni step del plan, recuperare i chunk rilevanti.

- Usa il modulo `cci_retrieval` (libs/cci-rag) — non chiamare Qdrant direttamente da qui.
- Hybrid search (dense + BM25) → RRF → cross-encoder rerank → top-K (default 8, configurabile per step).
- Applica **sempre** il filtro temporale dello step (`temporal_window`).
- Output: `retrieved_chunks[step_id] = list[Chunk]`.
- **Non scartare** chunk con confidence bassa: passali al Verifier, sarà lui a decidere.
- Audit: log `agent.retriever.chunks_retrieved.v1` con `chunk_ids[]`, `latency_ms`.

### 3. Verifier — `verifier_agent.py`
**Responsabilità**: applicare le regole deterministiche di coerenza.

- **ZERO LLM**. Mai. È il cuore non-allucinante.
- Carica l'ontologia del dominio dello step (da YAML, via `OntologyLoader`).
- Esegue le regole tramite il `CoherenceEngine` (motore a regole Datalog-like + Cypher temporal).
- Output: `incoherences: list[Incoherence]` con `evidence_chunks[]` (set di chunk_id che provano l'incoerenza).
- Se non rileva incoerenze, lo state esce con `incoherences=[]` e il grafo termina senza Generator.
- Audit: log `agent.verifier.completed.v1` con `incoherences_count`, `rules_evaluated`.

### 4. Generator — `generator_agent.py`
**Responsabilità**: produrre spiegazioni naturali, citate, leggibili.

- Usa `LLMClient` di `libs/cci-llm` (Claude Sonnet 4.6 via Anthropic API) — mai SDK Anthropic diretto.
- Passa al prompt **solo i chunk citati come evidence**, non l'intero retrieval (data minimization GDPR).
- Citation enforcement: applica `enforce_grounding()` su ogni output. Vedi skill `cci-grounding-enforcer`.
- Se Claude fallisce 3 tentativi, marca `state.hitl_required = True` e termina senza emissione.
- Output: `Explanation` con `text`, `sources`, `model_version` (sempre `claude-sonnet-4-6`), `prompt_version`, `confidence`, `what_if_scenarios[]`.
- Audit: log `agent.generator.explanation_emitted.v1` o `agent.generator.not_emittable.v1`.

### 5. Audit — implementato come hook, NON nodo
**Responsabilità**: registrare ogni transizione nel log immutabile.

L'Audit non è un nodo del grafo perché non trasforma lo stato. È un *callback* attaccato ad ogni transizione:

```python
async def audit_callback(state: AgentState, node_name: str) -> None:
    event = {
        "ts": datetime.utcnow().isoformat(),
        "correlation_id": state.correlation_id,
        "node": node_name,
        "state_digest": hash_state(state),
        "transitions_so_far": len(state.transitions),
    }
    await audit_log.append(event)  # hash chain, see cci-audit-chain skill
```

Si attiva via `graph.compile(callbacks=[audit_callback])`.

## Prompt versioning

I prompt vivono in `services/agents/src/cci_agents/prompts/v{N}/` come template Jinja2.

```
prompts/
├── v1/
│   ├── planner_nl_to_plan.j2
│   └── generator_explanation.j2
└── v2/         # quando cambi un prompt, NON sovrascrivere — nuova versione
    └── generator_explanation.j2
```

Ogni chiamata LLM logga `prompt_version`. Mai prompt inline nel codice.

## Checkpointing

LangGraph supporta checkpointing nativo. **Obbligatorio in CCI** perché:
- Permette resume di un'esecuzione interrotta
- È parte del audit trail (lo stato ad ogni step è recuperabile)
- È usato dal sistema HITL: quando un human deve approvare, il grafo si "ferma" e ripende

Usa `AsyncMongoDBSaver` dal package `langgraph-checkpoint-mongodb` puntando al DB di governance. **Mai** checkpoint in memoria in produzione, **mai** filesystem-based checkpoint.

```python
# Da pyproject.toml di services/agents:
# langgraph-checkpoint-mongodb = "^0.1"
# motor = "^3.6"
```

## Anti-pattern da rifiutare

| Sintomo | Perché è grave |
|---|---|
| Un agente che fa più di un ruolo (es. "smart agent" che fa retrieval + verify) | Distrugge auditabilità. La separazione è la garanzia. |
| LLM nel Verifier | Reintroduce hallucination nel nucleo critico. |
| State globale mutabile fra agenti (es. variabili di modulo) | Rompe checkpointing e debug. Tutto in `AgentState`. |
| Prompt hardcoded nel codice Python | Impedisce versioning, A/B test, audit AI Act. |
| Skip di `audit_callback` "per velocità" | Sei legalmente esposto. È art. 12 AI Act. |
| Usare `Tools` dei framework (OpenAI tools, function calling) per logica deterministica | Rendi non-deterministico ciò che dovrebbe esserlo. |
| Side-effect (chiamate HTTP esterne, writes su DB) dentro nodi non-deterministic | Replays di checkpoint diventano impossibili. Side-effect solo nel Generator + Audit. |
| Checkpoint in memoria (`MemorySaver`) o filesystem (`PickleSaver`) in produzione | Esecuzione non resumibile su pod restart; HITL gate inutilizzabile |
| `PostgresSaver`, `SqliteSaver`, `RedisSaver` | Non allineati allo stack (MongoDB unico operational DB). Usa `AsyncMongoDBSaver` |
| Chiamata diretta `AsyncAnthropic(...)` dentro un nodo | Bypassi il wrapper `cci_llm.LLMClient` → niente PII guard, niente audit, niente metriche |

## Test pattern

```python
@pytest.mark.asyncio
async def test_orchestrator_skips_generator_when_no_incoherence(deps):
    graph = build_orchestrator(deps)
    state = AgentState(
        trigger=TriggerEvent.timer("month_end_q1"),
        correlation_id="test-001",
        started_at=datetime.utcnow(),
    )
    # arrangia il Verifier mock a restituire zero incoherences
    deps.verifier.set_mock_result([])
    
    final_state = await graph.ainvoke(state)
    
    assert final_state["explanation"] is None
    assert "generator" not in [t["node"] for t in final_state["transitions"]]
```

## Riferimenti
- Documento `CCI_AVCS_Technical_Specifications.html`, sezione §05 (I cinque agenti core)
- LangGraph docs: https://langchain-ai.github.io/langgraph/
- Skill correlate: `cci-grounding-enforcer`, `cci-audit-chain`
