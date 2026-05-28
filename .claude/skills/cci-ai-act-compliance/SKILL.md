---
name: cci-ai-act-compliance
description: Use this skill whenever you create, modify, or review anything that could fall under EU AI Act (Reg. 2024/1689), GDPR, ISO 42001, or MDR for the CCI/AVCS platform. Trigger on files under docs/compliance/, on file names like ai-act-mapping.yaml, dpia-template.md, risk-assessment.md, iso42001-roadmap.md, on PII handling code, on pseudonymization functions, on any LLM call that returns user-facing output, on changes to audit logging, on the introduction of new data sources containing personal/clinical/financial data, on the words "AI Act", "art. 9", "art. 10", "art. 11", "art. 12", "art. 13", "art. 14", "art. 15", "high-risk AI system", "GDPR", "DPIA", "pseudonymization", "ISO 42001", "MDR", "data residency", "explainability". This skill ensures CCI/AVCS remains demonstrably compliant by design — not as afterthought.
license: Internal — CCI/AVCS Project
---

# CCI/AVCS AI Act & Compliance

CCI/AVCS è un **sistema AI ad alto rischio** ai sensi dell'AI Act (Reg. UE 2024/1689) perché supporta decisioni che impattano compliance regolatoria e finanziaria in contesti regolati (sanità, multiutility, automotive, dispositivi). Ogni feature deve dimostrare di soddisfare gli articoli 9–15.

## Mapping articolo → implementazione

Il file `docs/compliance/ai-act-mapping.yaml` è la **fonte di verità**. Ogni nuova funzionalità deve aggiornare questo file PRIMA del merge.

```yaml
version: 1.0
last_updated: 2026-05-23
system_classification: high_risk
in_scope_articles: [9, 10, 11, 12, 13, 14, 15]

requirements:
  - article: 9
    title: "Risk management system"
    implementation:
      - artifact: docs/compliance/risk-assessment.md
        type: document
        review_cadence: quarterly
      - artifact: docs/compliance/risk-register.csv
        type: living-document
    evidence_owner: compliance-officer
    status: implemented

  - article: 10
    title: "Data governance and quality"
    implementation:
      - artifact: services/ingestion/src/cci_ingestion/quality.py
        type: code
        description: "Great Expectations suite on ingested documents"
      - artifact: docs/compliance/data-lineage.mmd
        type: diagram
    status: implemented

  - article: 11
    title: "Technical documentation"
    implementation:
      - artifact: docs/architecture/
        type: directory
      - artifact: /docs (OpenAPI auto-generated)
        type: runtime
    status: implemented

  - article: 12
    title: "Record keeping and logs"
    implementation:
      - artifact: services/governance/src/cci_governance/audit_log.py
        type: code
        description: "Append-only PostgreSQL + SHA-256 hash chain"
      - retention: 5_years_minimum
    status: implemented
    related_skill: cci-audit-chain

  - article: 13
    title: "Transparency and provision of information"
    implementation:
      - artifact: libs/cci-llm/src/cci_llm/citation_parser.py
        type: code
        description: "Every LLM output includes model_version, prompt_version, confidence, sources[]"
      - artifact: services/governance/api/explainability
        type: endpoint
    status: implemented
    related_skill: cci-grounding-enforcer

  - article: 14
    title: "Human oversight"
    implementation:
      - artifact: services/governance/src/cci_governance/hitl.py
        type: code
        description: "Hard-gate on impact > threshold"
      - artifact: frontend/app/hitl/page.tsx
        type: ui
    status: implemented

  - article: 15
    title: "Accuracy, robustness, cybersecurity"
    implementation:
      - artifact: tests/regression/
        type: test-suite
        coverage: 50_plus_scenarios
      - artifact: docs/compliance/threat-model.md
        type: document
    status: implemented
```

## Le sei pratiche operative

### 1. Transparency artifacts on every output

Ogni output user-facing del sistema DEVE includere queste metadata:

```python
# libs/cci-common/src/cci_common/domain.py
class TransparencyEnvelope(BaseModel):
    model_version: str         # always "claude-sonnet-4-6" (or current CCI_LLM_MODEL)
    prompt_version: str        # e.g. "generator/v1.2"
    coherence_engine_version: str
    confidence: float          # 0.0–1.0
    sources: list[ChunkRef]    # ordered by relevance
    reasoning_steps: list[ReasoningStep]
    generated_at: datetime
    correlation_id: str

class ChunkRef(BaseModel):
    chunk_id: str
    document_id: str
    page: int | None
    relevance_score: float
```

Senza envelope → non si emette. Vale per: alert, report what-if, executive summary, response API utenti.

### 2. Human-in-the-loop hard gate

Ogni azione con impatto > soglia richiede approvazione umana esplicita.

```python
# services/governance/src/cci_governance/hitl.py
class HITLGate:
    async def evaluate(self, action: Action) -> Decision:
        if action.impact_eur > self.threshold:
            await self._queue_for_review(action)
            return Decision(status="PENDING_REVIEW", blocked=True)
        if action.severity == "CRITICAL":
            await self._queue_for_review(action)
            return Decision(status="PENDING_REVIEW", blocked=True)
        return Decision(status="AUTO_APPROVED", blocked=False)

    async def approve(self, action_id: str, approver_id: str, motivation: str) -> None:
        if not motivation or len(motivation) < 20:
            raise ValueError("Motivation required (min 20 chars)")
        await self._audit_log.append({
            "event": "hitl.approved",
            "action_id": action_id,
            "approver_id": approver_id,
            "motivation": motivation,
            "ts": datetime.utcnow().isoformat(),
        })
```

### 3. GDPR — pseudonymization on ingestion

Ogni documento in input passa per il `PIIDetector` prima di toccare embeddings o KG.

```python
# services/ingestion/src/cci_ingestion/pii.py
PII_LABELS = {"PERSON", "EMAIL", "PHONE", "TAX_ID", "PATIENT_ID", "IBAN", "ADDRESS"}

async def pseudonymize(text: str, *, mode: Literal["mask", "tokenize"] = "tokenize") -> tuple[str, PIIMap]:
    entities = await ner_client.extract(text, labels=PII_LABELS)
    pii_map = PIIMap()
    pseudonymized = text
    for ent in entities:
        token = pii_map.add(ent.text, ent.label)  # e.g. "PERSON_a3f7c2"
        pseudonymized = pseudonymized.replace(ent.text, token)
    return pseudonymized, pii_map
```

La `PIIMap` (mapping token → valore originale) vive in un vault separato con encryption at rest e accesso role-based. Mai nei chunk indicizzati.

### 4. Data residency: provider unico Anthropic con PII pseudonimizzata

Tutte le chiamate LLM passano dall'Anthropic API (`claude-sonnet-4-6`). Non esiste routing condizionale "locale vs cloud": il provider è uno solo. La residency e la compliance GDPR si reggono su **quattro meccanismi compositi**:

1. **Pseudonimizzazione PII obbligatoria** prima dell'invio (vedi punto 3 sopra) — il wrapper `LLMClient` rifiuta payload con pattern PII raw via `assert_no_raw_pii()`
2. **Accordi contrattuali Anthropic** — zero retention, no training su dati cliente (dove applicabili)
3. **API key dell'organizzazione cliente** — `ANTHROPIC_API_KEY` caricata via Vault, mai esposta nel repo
4. **Per scenari ad alta sensibilità** (dati clinici AOU Modena, supply chain confidenziale Prada) — valutare endpoint regionali Anthropic se disponibili; in alternativa, classificare il caso d'uso come "high sensitivity" e bloccarlo con `HITLGate` finché un human approva manualmente

```python
# libs/cci-llm/src/cci_llm/sensitivity.py
from typing import Literal

Sensitivity = Literal["public", "internal", "confidential", "regulated"]

def assert_can_send_to_api(*, domain: str, sensitivity: Sensitivity) -> None:
    """
    Refuses to send 'regulated' payloads without HITL pre-approval.
    No more local-vs-cloud routing: there is ONE provider (Anthropic).
    """
    if sensitivity == "regulated":
        if not _hitl_preapproval_exists(domain):
            raise RegulatedDataNotApprovedError(
                f"Domain '{domain}' carries 'regulated' sensitivity; "
                "HITL pre-approval required before any Anthropic API call. "
                "See docs/compliance/dpia-<domain>.md"
            )
```

Lo split locale/cloud che esisteva nella versione precedente del sistema **non esiste più**. La compliance si appoggia sulla pseudonimizzazione + accordi contrattuali + audit dell'ogni chiamata API.

### 5. Right to erasure

Endpoint `DELETE /documents/{id}` deve propagare cancellazione coerentemente:

```python
async def erase_document(doc_id: str, requester_id: str) -> ErasureReceipt:
    receipt = ErasureReceipt(doc_id=doc_id, requested_by=requester_id)
    
    # 1. Qdrant: delete by metadata filter
    await qdrant.delete(collection=domain, filter={"document_id": doc_id})
    receipt.vector_store_purged = True
    
    # 2. Neo4j: mark Document node as redacted, keep relationships for integrity
    await graph.run("""
        MATCH (d:Document {id: $id})
        SET d.redacted = true, d.redacted_at = datetime(), d.text = null
    """, id=doc_id)
    receipt.graph_redacted = True
    
    # 3. Audit log: append redaction event (NOT delete, preserves hash chain)
    await audit_log.append({
        "event": "gdpr.erasure.executed",
        "doc_id": doc_id,
        "requester": requester_id,
        "ts": datetime.utcnow().isoformat(),
    })
    receipt.audit_recorded = True
    
    return receipt
```

**Mai cancellare entry dell'audit log** — si rompe la hash chain. Si marca redacted.

### 6. DPIA precompilata

`docs/compliance/dpia-template.md` contiene il template GDPR art. 35. Ogni nuovo dominio in produzione richiede una DPIA istanziata dal template e firmata dal DPO del cliente.

## Cosa NON fare

| Anti-pattern | Articolo violato |
|---|---|
| Output user-facing senza `TransparencyEnvelope` | AI Act art. 13 |
| `if action.impact > 1e9: human_approval()` (soglia hardcoded) | AI Act art. 14 + 12-Factor |
| Logging dei prompt contenenti PII | GDPR + AI Act art. 12 |
| Disabilitare HITL "per testing in prod" | AI Act art. 14 |
| Inviare payload con PII non pseudonimizzato all'Anthropic API | GDPR + violation di `assert_no_raw_pii()` |
| Cancellare entry audit log per GDPR | Confusione fra erasure e tamper — preserva chain, appendi evento `gdpr.erasure.executed.v1` |
| Auto-approvazione di azioni perché "il modello ha alta confidence" | AI Act art. 14 — confidence non sostituisce oversight |
| Hardcoded `model = "claude-..."` fuori da `cci_llm.LLMClient` | Impedisce upgrade controllato e audit del modello |
| Bypass del `LLMClient` wrapper con chiamata diretta a `AsyncAnthropic(...)` | Bypassi tutti i controlli: PII, audit, metriche, retry |

## Procedura quando aggiungi una nuova feature

1. Identifica gli articoli AI Act impattati
2. Aggiorna `docs/compliance/ai-act-mapping.yaml` con il nuovo `artifact`
3. Aggiungi test di regression in `tests/compliance/`
4. Se tocca PII: aggiorna `docs/compliance/gdpr-data-flow.mmd`
5. Se introduce un nuovo dominio: istanzia DPIA
6. Se cambia il modello: aggiorna `docs/compliance/model-card-<name>.md`

## Riferimenti
- AI Act (Reg. UE 2024/1689): https://artificialintelligenceact.eu
- GDPR (Reg. UE 2016/679)
- ISO 42001:2023 — AI Management System
- MDR (Reg. UE 2017/745) — solo per modulo clinico futuro
- Skill correlate: `cci-audit-chain`, `cci-grounding-enforcer`
