---
name: cci-ontology-yaml
description: Use this skill whenever you create, modify, validate, or load vertical ontology files for CCI/AVCS. Trigger on file paths under docs/ontologies/, on file names matching *_ontology.yaml or domain YAML files (hera_it.yaml, aou_clinical.yaml, semsotec_product.yaml, ducati_automotive.yaml, dallara_quality.yaml, esg_csrd.yaml), on imports of ontology_loader.py, on mentions of "ontology", "domain rules", "verification rules", "bounded context schema", "rule R001", or when adding a new vertical domain to the platform. This skill enforces the YAML schema that lets the same engine serve different verticals without code changes.
license: Internal — CCI/AVCS Project
---

# CCI/AVCS Ontology YAML

L'idea di prodotto: **un solo motore, tante ontologie**. Cambiando il file YAML del dominio, il sistema verifica IT, sanità, industria o ESG senza ridistribuzione di codice.

## Schema canonico

Ogni file ontologia DEVE rispettare questo schema (validato all'avvio del `coherence-service` via Pydantic).

```yaml
# Required header
domain: <slug>            # snake_case, unique, matches Qdrant collection
version: <semver>         # semantic versioning, increment on schema changes
description: <one-line>
maintainer: <email>
last_review: <ISO date>

# Required: entities recognized in this domain
entities:
  - name: <PascalCase>            # matches Neo4j label exactly
    description: <one-line>
    properties:
      - name: <snake_case>
        type: <str|int|float|date|datetime|bool>
        required: <bool>
        pii: <bool>                # if true, triggers pseudonymization at ingestion
        description: <one-line>

# Required: temporal relations
relations:
  - type: <SCREAMING_SNAKE>       # matches Cypher relation type
    from: <entity_name>
    to: <entity_name>
    temporal: true                # always true in CCI; explicit for clarity
    cardinality: <one-to-one|one-to-many|many-to-many>
    description: <one-line>

# Required: coherence rules
rules:
  - id: <DOMAIN-CODE>             # e.g. HERA-R001, AOU-R012
    description: <one-line, business-facing>
    when: <DSL expression>        # see DSL grammar below
    severity: <LOW|MEDIUM|HIGH|CRITICAL>
    category: <financial|compliance|operational|temporal>
    impact_threshold_eur: <number|null>  # null = always alert
    recommendation_template: <jinja template ref>

# Optional: NER hints for ingestion
ner_hints:
  - pattern: <regex>
    label: <entity_name>
    examples: [<list of strings>]

# Optional: external regulation references
regulations:
  - id: <REG_REF>
    name: <full name>
    jurisdiction: <ISO 3166 country or "EU">
    in_force_from: <ISO date>
    url: <official source URL>
```

## DSL della clausola `when`

Le regole sono espressioni dichiarative valutate dal `CoherenceEngine`. Sintassi accettata:

| Costrutto | Esempio | Significato |
|---|---|---|
| `entity(prop) <op> value` | `CloudCommitment(amount_eur) > 800000` | confronto scalare |
| `entity(prop) <op> entity2(prop)` | `CloudCommitment(period_end) > Certification(valid_to)` | confronto fra entità |
| `sum(...)`, `count(...)`, `max(...)`, `min(...)` | `sum(BudgetApproval.amount_eur WHERE year=2026)` | aggregazione |
| `exists(...)`, `NOT exists(...)` | `NOT exists(Certification WHERE type='ISO27001' AND valid_to >= today())` | esistenza |
| `AND`, `OR`, `NOT` | `A AND (B OR NOT C)` | logica booleana |
| `WHERE <cond>` su collezioni | `BudgetApproval WHERE year=2026 AND category='cloud'` | filtro |
| `today()`, `date('YYYY-MM-DD')`, `now()` | `valid_to >= today()` | costanti temporali |
| `duration.days(a, b)` | `duration.days(cert.valid_to, today()) < 30` | aritmetica temporale |

La DSL viene compilata in **Cypher temporale** + funzioni Python per le aggregazioni che Cypher non esprime nativamente.

## Esempio reale: `hera_it.yaml`

```yaml
domain: hera_it
version: 1.0.0
description: "Hera Group — IT cloud spend, certifications and budget coherence"
maintainer: arb@hera.it
last_review: 2026-05-01

entities:
  - name: CloudCommitment
    description: "Multi-month spend commitment toward a cloud provider"
    properties:
      - {name: provider, type: str, required: true, pii: false, description: "AWS|Azure|GCP"}
      - {name: amount_eur, type: float, required: true, pii: false, description: "EUR committed"}
      - {name: period_start, type: date, required: true, pii: false, description: "ISO date"}
      - {name: period_end, type: date, required: true, pii: false, description: "ISO date"}
      - {name: contract_ref, type: str, required: false, pii: false, description: "internal contract code"}

  - name: BudgetApproval
    description: "Board-approved annual budget line"
    properties:
      - {name: year, type: int, required: true, pii: false}
      - {name: amount_eur, type: float, required: true, pii: false}
      - {name: category, type: str, required: true, pii: false}
      - {name: approved_by, type: str, required: true, pii: true}
      - {name: approval_date, type: date, required: true, pii: false}

  - name: ISO27001Certification
    description: "Information security management certification"
    properties:
      - {name: issuer, type: str, required: true, pii: false}
      - {name: valid_from, type: date, required: true, pii: false}
      - {name: valid_to, type: date, required: true, pii: false}
      - {name: scope, type: str, required: true, pii: false}
      - {name: version, type: str, required: false, pii: false}

relations:
  - type: COVERED_BY
    from: CloudCommitment
    to: BudgetApproval
    temporal: true
    cardinality: many-to-one
    description: "A commitment must be covered by an approved budget line"

  - type: CERTIFIED_BY
    from: CloudCommitment
    to: ISO27001Certification
    temporal: true
    cardinality: many-to-one
    description: "The provider hosting workloads must be ISO27001 certified during the period"

rules:
  - id: HERA-R001
    description: "Cloud commitment exceeds approved budget for the year"
    when: "CloudCommitment(amount_eur) > sum(BudgetApproval.amount_eur WHERE year = CloudCommitment.period_start.year AND category = 'cloud')"
    severity: HIGH
    category: financial
    impact_threshold_eur: 50000
    recommendation_template: "rec/hera/budget_overrun.j2"

  - id: HERA-R002
    description: "ISO 27001 certification expires before the end of cloud commitment period"
    when: "exists(CloudCommitment) AND NOT exists(ISO27001Certification WHERE valid_from <= CloudCommitment.period_start AND valid_to >= CloudCommitment.period_end)"
    severity: CRITICAL
    category: compliance
    impact_threshold_eur: null
    recommendation_template: "rec/hera/cert_drift.j2"

  - id: HERA-R003
    description: "Approved budget for the year has zero coverage from financial policy"
    when: "BudgetApproval(category='cloud') AND NOT exists(Document WHERE type='financial_policy' AND valid_to >= today())"
    severity: MEDIUM
    category: compliance
    impact_threshold_eur: 100000
    recommendation_template: "rec/hera/policy_missing.j2"

ner_hints:
  - pattern: '\bISO\s?27001\b'
    label: ISO27001Certification
    examples: ["ISO 27001:2022", "ISO27001"]
  - pattern: '\bAWS\b|\bAzure\b|\bGCP\b'
    label: CloudCommitment
    examples: ["AWS Reserved Instances", "Azure EA commitment"]

regulations:
  - id: ARERA-2024
    name: "Autorità Regolazione Energia Reti Ambiente — delibera 2024"
    jurisdiction: IT
    in_force_from: 2024-01-01
    url: https://www.arera.it
```

## Validazione

All'avvio di `coherence-service`, ogni file ontologia passa per:

```python
# services/coherence/src/cci_coherence/ontology_loader.py
from pydantic import BaseModel, Field, field_validator

class EntityProperty(BaseModel):
    name: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    type: Literal["str", "int", "float", "date", "datetime", "bool"]
    required: bool
    pii: bool = False
    description: str

class Entity(BaseModel):
    name: str = Field(pattern=r"^[A-Z][a-zA-Z0-9]*$")  # PascalCase
    description: str
    properties: list[EntityProperty]

class Relation(BaseModel):
    type: str = Field(pattern=r"^[A-Z][A-Z0-9_]*$")  # SCREAMING_SNAKE
    from_: str = Field(alias="from")
    to: str
    temporal: bool
    cardinality: Literal["one-to-one", "one-to-many", "many-to-many"]
    description: str

class Rule(BaseModel):
    id: str = Field(pattern=r"^[A-Z]+-R\d{3,}$")
    description: str
    when: str  # parsed by DSL parser separately
    severity: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    category: Literal["financial", "compliance", "operational", "temporal"]
    impact_threshold_eur: float | None = None
    recommendation_template: str

class Ontology(BaseModel):
    domain: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    version: str
    description: str
    maintainer: str
    last_review: date
    entities: list[Entity]
    relations: list[Relation]
    rules: list[Rule]

    @field_validator("entities")
    @classmethod
    def entity_names_unique(cls, v: list[Entity]) -> list[Entity]:
        names = [e.name for e in v]
        if len(names) != len(set(names)):
            raise ValueError("entity names must be unique")
        return v
```

Se la validazione fallisce, il servizio **non parte**. Crash early è preferibile a runtime opaque errors.

## Pattern per aggiungere un nuovo dominio

1. Crea `docs/ontologies/<domain_slug>.yaml` partendo da un esempio esistente
2. Compila entità, relazioni temporali, regole con `id` prefissate (`AOU-R001`, `DUC-R001`, ecc.)
3. Aggiungi i template di raccomandazione in `services/agents/src/cci_agents/prompts/v1/rec/<domain>/`
4. Carica una corpus minima di documenti fixture in `tests/fixtures/<domain>/`
5. Scrivi 5-10 test di regression che validano le regole su scenari noti
6. Aggiungi una Qdrant collection dedicata: `qdrant_client.create_collection(domain_slug, ...)`
7. Aggiorna `docs/architecture/domain-catalog.md` con l'overview

**Non serve modificare codice Python** se le regole entrano nel sotto-insieme della DSL supportata.

## Anti-pattern

| Sintomo | Perché è grave |
|---|---|
| `domain: HeraIT` con maiuscole o spazi | Rompe i path di collection Qdrant e cartelle |
| `rules` senza `id` o con id duplicati | Audit log diventa ambiguo, alert non tracciabili |
| `severity: critical` (lowercase) | Pydantic Literal rifiuta — sintassi rigorosa SCREAMING |
| Property con `pii: false` su un campo email/nome | Bypassa pseudonimizzazione GDPR |
| Aggiungere logica nel codice Python invece che nella DSL | Sconfigge l'intera idea di ontology-as-config |
| `when` con sintassi non-DSL ("se commitment maggiore di budget allora alert") | Il parser DSL fallisce; usa la grammatica esatta |
| Versionamento ad hoc (es. `v1.2.3-beta`) | Usa SemVer puro: `1.2.3` |

## Hot reload

Il `coherence-service` può ricaricare ontologie senza restart se ricevono evento `ontology.updated.v1`:

```python
@app.on_event("ontology_updated")
async def reload_ontology(event: OntologyUpdatedEvent) -> None:
    new_ont = Ontology.parse_obj(yaml.safe_load(event.yaml_content))
    await ontology_registry.swap(event.domain, new_ont)
    await audit_log.append(f"ontology.{event.domain}.reloaded.v{new_ont.version}")
```

## Riferimenti
- Documento `CCI_AVCS_Technical_Specifications.html`, sezione §07 (Ontologie verticali)
- Esempio completo `docs/ontologies/hera_it.yaml`
- Skill correlate: `cci-temporal-knowledge-graph`, `cci-agentic-langgraph`
