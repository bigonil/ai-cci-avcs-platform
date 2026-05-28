---
name: cci-temporal-knowledge-graph
description: Use this skill whenever you write Cypher queries, design Neo4j schemas, manipulate the property graph, write code that creates or queries entities like Certification/Asset/Contract/Budget/Trial/Investment, or anything related to temporal validity of relationships. Trigger on imports of neo4j driver, on files named temporal_graph.py, temporal_inference.py, knowledge_service.py, on mentions of "valid_from", "valid_to", "drift", "temporal validity", "Neo4j", "Cypher", "knowledge graph", "property graph". This skill enforces that EVERY relationship in the graph carries temporal validity attributes — without them, the graph cannot answer "what was the state of X at time Y", which is the entire point of CCI/AVCS.
license: Internal — CCI/AVCS Project
---

# CCI/AVCS Temporal Knowledge Graph

Il graph di CCI/AVCS **non è** un knowledge graph qualunque: è un *property graph temporale* dove ogni arco ha attributi di validità. Senza queste, il sistema perde la capacità di rilevare drift e di rispondere a domande storiche — la differenza con qualunque altro sistema RAG.

## La regola del tempo

> **Ogni `MERGE` di una relazione DEVE includere `valid_from`, `valid_to`, `version`, `provenance_chunk_id`.**
> Se la relazione è "current" (senza scadenza nota), `valid_to = 9999-12-31`.
> Se la relazione termina, NON si cancella: si chiude impostando `valid_to = data_termine`.

Questo è il pattern *bitemporal* semplificato (valid time, non transaction time). Per la transaction time c'è già l'audit log immutabile separato.

## Schema entità core

Le entità sono **nodi** con label tipata. I nomi sono PascalCase in inglese, allineati alle ontologie YAML.

```cypher
// Entità documentali
(:Document {id, source_path, mime_type, ingested_at, version, domain})
(:Chunk {id, text, position, embedding_ref, page})

// Entità di compliance
(:Certification {id, type, issuer, valid_from, valid_to, scope, version})
// type ∈ {ISO27001, ISO42001, IATF16949, MDR, CE, FCC, MDR_IIa, MDR_IIb}

// Entità finanziarie
(:BudgetApproval {id, year, amount_eur, category, approved_by, approval_date})
(:CloudCommitment {id, provider, amount_eur, period_start, period_end, contract_ref})
(:Investment {id, project_code, amount_eur, status, approval_date})

// Entità di dominio (sanità)
(:Trial {id, phase, sponsor_type, budget_eur, duration_months, enrollment_target})
(:GrantAgreement {id, programme, budget_eur, period_start, period_end, wp_codes})
(:DRGRefund {id, drg_code, refund_eur, period})

// Entità di dominio (industria)
(:ProductDeclaration {id, product_code, standards, declaration_date})
(:DesignChange {id, product_code, component, change_date, description})

// Entità organizzative
(:Asset {id, type, name, owner_team})
(:Stakeholder {id, name, role, email})
(:Regulation {id, ref, jurisdiction, in_force_from, version})
```

## Schema relazioni temporali

Ogni relazione ha **sempre** queste property:

```cypher
// Pattern obbligatorio
[r:REL_TYPE {
    valid_from: date(),           // ISO 8601 date
    valid_to: date('9999-12-31'), // "current" sentinel
    version: 1,                    // increment on update
    provenance_chunk_id: 'doc_xx_chunk_03',
    confidence: 1.0,               // 0.0–1.0
    created_at: datetime(),
    created_by: 'ingestion-service'
}]
```

Relazioni canoniche:
- `(:CloudCommitment)-[:COVERED_BY]->(:BudgetApproval)`
- `(:CloudCommitment)-[:CERTIFIED_BY]->(:Certification)`
- `(:Trial)-[:FUNDED_BY]->(:GrantAgreement)`
- `(:Investment)-[:JUSTIFIED_BY]->(:DRGRefund)`
- `(:ProductDeclaration)-[:VALID_FOR]->(:Regulation)`
- `(:DesignChange)-[:AFFECTS]->(:ProductDeclaration)`
- `(:Document)-[:STATES_FACT]->(:Chunk)` (rel non temporale, è strutturale)
- `(:Chunk)-[:EVIDENCES]->(node)` (evidenza per altre relazioni)

## Indici obbligatori

Al boot di `knowledge-service` esegui:

```cypher
// Performance su lookup temporali
CREATE INDEX cert_valid_to IF NOT EXISTS FOR (c:Certification) ON (c.valid_to);
CREATE INDEX commit_period IF NOT EXISTS FOR (cc:CloudCommitment) ON (cc.period_start, cc.period_end);

// Constraint di unicità
CREATE CONSTRAINT cert_id_unique IF NOT EXISTS FOR (c:Certification) REQUIRE c.id IS UNIQUE;
CREATE CONSTRAINT doc_id_unique IF NOT EXISTS FOR (d:Document) REQUIRE d.id IS UNIQUE;
CREATE CONSTRAINT chunk_id_unique IF NOT EXISTS FOR (c:Chunk) REQUIRE c.id IS UNIQUE;

// Composite index utile per le temporal queries
CREATE INDEX rel_validity IF NOT EXISTS FOR ()-[r:COVERED_BY]-() ON (r.valid_from, r.valid_to);
```

## Pattern query temporali ricorrenti

### A. "Cosa era valido al tempo T?"
Query principe del sistema. Implementa in `temporal_graph.py`:

```python
async def state_at(self, t: date, entity_type: str) -> list[dict]:
    query = """
    MATCH (e)-[r]->(target)
    WHERE labels(e)[0] = $entity_type
      AND r.valid_from <= date($t)
      AND r.valid_to >= date($t)
    RETURN e, type(r) AS rel, target, r
    """
    return await self._run(query, entity_type=entity_type, t=t.isoformat())
```

### B. Rilevazione drift di certificazione
La query che alimenta R002 dello scenario Hera:

```cypher
MATCH (cc:CloudCommitment)-[r:CERTIFIED_BY]->(cert:Certification)
WHERE cert.valid_to < cc.period_end
RETURN cc.id AS commitment_id,
       cc.period_end AS commitment_ends,
       cert.id AS cert_id,
       cert.valid_to AS cert_expires,
       duration.between(cert.valid_to, cc.period_end).days AS exposure_days
ORDER BY exposure_days DESC
```

### C. Chiusura logica di una relazione
**Mai** `DELETE`. Sempre update di `valid_to`:

```cypher
MATCH (a)-[r:COVERED_BY]->(b)
WHERE r.id = $rel_id AND r.valid_to = date('9999-12-31')
SET r.valid_to = date($termination_date),
    r.version = r.version + 1,
    r.closed_by = $actor,
    r.closed_at = datetime()
```

### D. Versionamento di un fatto modificato
Quando una relazione cambia (es. budget rivisto), NON aggiornare in place:

```cypher
// Step 1: chiudi la vecchia
MATCH (cc:CloudCommitment {id: $cc_id})-[r:COVERED_BY]->(b:BudgetApproval)
WHERE r.valid_to = date('9999-12-31')
SET r.valid_to = date($change_date)

// Step 2: crea la nuova
MATCH (cc:CloudCommitment {id: $cc_id})
MATCH (b_new:BudgetApproval {id: $new_budget_id})
CREATE (cc)-[r2:COVERED_BY {
    valid_from: date($change_date),
    valid_to: date('9999-12-31'),
    version: $prev_version + 1,
    provenance_chunk_id: $new_chunk,
    confidence: 1.0,
    created_at: datetime(),
    created_by: 'ingestion-service'
}]->(b_new)
```

## Anti-pattern da rifiutare

| Sintomo | Perché è grave |
|---|---|
| `CREATE (a)-[:REL]->(b)` senza property temporali | Distrugge la capacità di drift detection |
| `MATCH (a)-[r]->(b) DELETE r` | Perdi la storia. Usa update di `valid_to`. |
| Confondere `date` e `datetime`: `r.valid_from = datetime()` | Le query usano `date()`. Tipi non confrontabili → query silenziosamente vuote. |
| Property temporali sui **nodi** invece che sulle relazioni | Il nodo "esiste" sempre; è la relazione che ha validità. |
| Usare `MERGE (a)-[r:REL]->(b)` per "upsert" senza chiudere prima la vecchia | Crei duplicati con validità sovrapposta. |
| Dimenticare `provenance_chunk_id` | Rompi la catena di evidenza, impossibile spiegare "perché" al CFO. |

## Driver e session pattern

Usa il driver async ufficiale:

```python
from neo4j import AsyncGraphDatabase, AsyncDriver

class TemporalGraphClient:
    def __init__(self, uri: str, user: str, password: str):
        self._driver: AsyncDriver = AsyncGraphDatabase.driver(
            uri, auth=(user, password),
            max_connection_pool_size=20,
        )

    async def close(self) -> None:
        await self._driver.close()

    async def health(self) -> bool:
        try:
            async with self._driver.session() as s:
                await s.run("RETURN 1")
            return True
        except Exception:
            return False

    async def _run(self, query: str, **params) -> list[dict]:
        async with self._driver.session() as s:
            result = await s.run(query, **params)
            return [record.data() async for record in result]
```

## Test pattern

Usa `testcontainers` per Neo4j reale:

```python
@pytest.fixture(scope="session")
def neo4j_container():
    with Neo4jContainer("neo4j:5-community") as container:
        yield container

@pytest.mark.asyncio
async def test_certification_drift_detection(neo4j_container):
    client = TemporalGraphClient(neo4j_container.get_connection_url(), ...)
    # seed: cloud commitment fino al 2026-06-30, cert ISO scade 2026-03-31
    await seed_hera_q1_scenario(client)
    
    drifts = await client.detect_certification_drift()
    
    assert len(drifts) == 1
    assert drifts[0]["exposure_days"] == 91  # 2026-04-01 → 2026-06-30
```

## Riferimenti
- Documento `CCI_AVCS_Technical_Specifications.html`, sezione §04 (Layer 2 Knowledge)
- Neo4j Temporal types: https://neo4j.com/docs/cypher-manual/current/values-and-types/temporal/
- Pattern bitemporal: Snodgrass, *Developing Time-Oriented Database Applications in SQL* (riferimento concettuale)
