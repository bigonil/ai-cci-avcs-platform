# ADR-0002: Neo4j come Temporal Knowledge Graph

**Status**: Accepted
**Date**: 2026-05-29

## Context

CCI/AVCS deve tracciare relazioni tra entità (Budget, Certificazione, Contratto, KPI)
con validità temporale esplicita (`valid_from`, `valid_to`). Il Coherence Engine deve
eseguire query come "trova tutti i CloudCommitment attivi in Q2 2026 per cui non esiste
una ISO27001Certification valida nello stesso periodo".

## Decision

Adottare **Neo4j 5.x Community** come temporal property graph.

Ogni relazione porta: `valid_from`, `valid_to`, `version`, `confidence`, `provenance_chunk_id`.
Ontologie verticali caricate da YAML al boot tramite `cci_coherence.ontology_loader`.
Queries: Cypher parametrizzato, mai generato dinamicamente da LLM (R4).

## Consequences

**Positive**:
- Cypher nativo per pattern matching su grafi temporali
- Plugin APOC per utility (date math, path algorithms)
- Community edition sufficiente per MVP
- Schema-free per ontologie verticali modulari

**Negative**:
- Community edition: no clustering, no backup automatico → accettabile per MVP
- Overhead di serializzazione rispetto a SQL per query tabellari semplici

## Alternatives considered

- **ArangoDB**: multi-model ma ecosistema Python meno maturo
- **PostgreSQL + AGE**: temporal queries complesse, maturità inferiore per graph workload
- **TigerGraph**: enterprise-only, costo troppo elevato per MVP
