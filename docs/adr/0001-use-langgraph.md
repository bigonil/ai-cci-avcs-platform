# ADR-0001: Uso di LangGraph come orchestratore agentico

**Status**: Accepted
**Date**: 2026-05-29

## Context

La piattaforma CCI/AVCS richiede un'orchestrazione agentica multi-step con stato esplicito,
checkpointing, retry e tracciabilità completa degli step. Il sistema deve essere deterministic-first:
ogni nodo del grafo ha input/output contrattualizzati e lo stato è persistibile (requisito audit/AI Act).

Sono state valutate tre opzioni: framework custom, CrewAI e LangGraph.

## Decision

Adottare **LangGraph** come unico framework di orchestrazione agentica per `services/agents/`.

Checkpointer: `langgraph-checkpoint-mongodb` sulla collection `cci_governance.langgraph_checkpoints`.
Il grafo espone 5 nodi: Planner → Retriever → Verifier → Generator → Audit.

## Consequences

**Positive**:
- Stato esplicito come TypedDict → ogni transizione è ispezionabile e debuggabile
- Checkpointing nativo su MongoDB → riprende da qualsiasi punto in caso di crash
- Graph-based → visualizzazione e testing del flusso di controllo
- Comunità attiva, aggiornamenti frequenti

**Negative**:
- Learning curve per sviluppatori non familiari con il modello a grafo
- Overhead di serializzazione stato per verifiche rapide (< 1 s)

## Alternatives considered

- **Framework custom**: massimo controllo ma zero leverage su retry, checkpointing, parallelism → scartato (anti-pattern esplicito nel PROMPT)
- **CrewAI**: astrazione più alta ma meno controllo sullo stato esplicito; checkpointing meno maturo → scartato
