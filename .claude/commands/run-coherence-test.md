---
description: Esegue lo scenario di coerenza Hera Q1 2026 (R001 budget overrun, R002 cert ISO 27001 drift)
---

# /run-coherence-test

Esegue lo scenario demo end-to-end della Coherence Engine sul dominio `hera_it`.

## Cosa fa

1. Verifica che lo stack sia up:
   ```bash
   docker compose ps --status running | grep -E 'qdrant|neo4j|postgres|redis' \
     || { echo "❌ stack down — avvia con: make up"; exit 1; }
   ```

2. Avvia (o riusa) la corpus fixture Hera Q1 2026:
   ```bash
   make seed-hera-q1
   # questo carica:
   #  - docs/fixtures/hera/cloud_commitment_2026.pdf
   #  - docs/fixtures/hera/budget_approval_2026.pdf
   #  - docs/fixtures/hera/iso27001_certificate.pdf
   #  - docs/fixtures/hera/financial_policy_2025.pdf
   ```

3. Triggera la verifica manualmente via API del coherence-service:
   ```bash
   curl -X POST http://localhost:8003/verify \
     -H "Content-Type: application/json" \
     -d '{
       "domain": "hera_it",
       "trigger": {"type": "manual", "period": "2026-Q1"},
       "correlation_id": "demo-hera-q1-2026"
     }'
   ```

4. Recupera il report:
   ```bash
   curl -s http://localhost:8003/reports/demo-hera-q1-2026 | python3 -m json.tool
   ```

5. **Validazioni attese** sull'output:
   - `incoherences[]` deve contenere almeno 2 elementi
   - Una con `rule_id == "HERA-R001"` (budget overrun, severity HIGH, impact_eur ≈ 200_000)
   - Una con `rule_id == "HERA-R002"` (ISO 27001 drift, severity CRITICAL)
   - Ogni incoherence deve avere `evidence_chunks[]` non vuoto
   - L'`explanation.text` del Generator deve contenere citazioni `[chunk_id]` valide
   - L'audit log deve mostrare la sequenza completa: `planner → retriever → verifier → generator → audit`

6. Verifica audit chain:
   ```bash
   curl -s "http://localhost:8005/audit/by-correlation/demo-hera-q1-2026" | python3 -m json.tool
   ```

## Output atteso (sintesi)

```
✓ R001 — Budget overrun rilevato:
    impact_eur: 200000
    evidence: [doc_budget_2026_chunk_03, doc_commitment_aws_chunk_01]
    severity: HIGH

✓ R002 — Cert ISO 27001 drift rilevato:
    exposure_days: 91
    cert_expires: 2026-03-31
    commitment_ends: 2026-06-30
    severity: CRITICAL

✓ Generator output: 4 sentences, all with valid citations (no hallucination)
✓ Audit chain: 7 events, hash chain integrity verified
```

## Se fallisce

- Stack down → `make up && make wait-ready`
- Corpus non caricato → `make seed-hera-q1`
- 0 incoherences → controlla che `docs/ontologies/hera_it.yaml` sia caricato (`curl /coherence/ontologies`)
- Audit chain broken → eseguire `/audit-chain-verify`

## Riferimenti
- Documento `CCI_AVCS_Technical_Specifications.html`, sezione §08 (Scenario demo Hera Q1 2026)
- Skill: `cci-temporal-knowledge-graph`, `cci-ontology-yaml`
