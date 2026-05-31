---
description: Esegue i demo scenario di coerenza end-to-end su tutti i domini pilota (Hera, AOU Modena, SEMSOTEC, Ducati Corse, Dallara, Prada)
---

# /run-coherence-test

Esegue i demo scenario end-to-end della Coherence Engine sui sei domini pilota CCI/AVCS.

## Modalità di esecuzione

### Modalità 1 — In-process tutti i domini (senza Docker)

Non richiede lo stack attivo. Esegue il CoherenceEngine direttamente in Python su tutti e 6 i domini:

```bash
# Tutti e 6 i domini in sequenza (zero LLM, zero Docker)
uv run python scripts/run_all_coherence_test.py

# Dominio singolo
uv run python scripts/run_all_coherence_test.py --domain hera_it
uv run python scripts/run_all_coherence_test.py --domain aou_clinical
uv run python scripts/run_all_coherence_test.py --domain semsotec_product
uv run python scripts/run_all_coherence_test.py --domain ducati_corse
uv run python scripts/run_all_coherence_test.py --domain dallara
uv run python scripts/run_all_coherence_test.py --domain prada
```

Output atteso: 13 incoerenze rilevate su 19 fixture, tutte con evidence chunks, in < 700ms.

Per Hera-only (script originale):
```bash
uv run python scripts/run_coherence_test.py
```

---

### Modalità 2 — Tutti i domini (richiede `make up`)

```bash
# Tutti e 6 i domini in sequenza
uv run python scripts/run_demo_scenario.py --domain all

# Dominio singolo
uv run python scripts/run_demo_scenario.py --domain hera_it
uv run python scripts/run_demo_scenario.py --domain aou_clinical
uv run python scripts/run_demo_scenario.py --domain semsotec_product
uv run python scripts/run_demo_scenario.py --domain ducati_corse
uv run python scripts/run_demo_scenario.py --domain dallara
uv run python scripts/run_demo_scenario.py --domain prada

# Dry-run: mostra piano senza chiamare i servizi (utile in CI)
uv run python scripts/run_demo_scenario.py --domain all --dry-run
```

Equivalenti via Makefile:
```bash
make demo           # tutti i domini (alias make demo-all)
make demo-hera
make demo-aou
make demo-semsotec
make demo-ducati
make demo-dallara
make demo-prada
make demo-dry-run   # dry-run tutti i domini
```

---

## Prerequisiti (Modalità 2)

```bash
# 1. Verifica stack
docker compose ps --status running | grep -E 'qdrant|neo4j|mongodb|redis' \
  || { echo "❌ stack down — avvia con: make up"; exit 1; }

# 2. Avvia se necessario
make up && make wait-ready
```

---

## Scenari e incoerenze attese

### HERA — `hera_it`

**Scenario**: Hera Group IT — Multi-Cloud Commitment vs Budget vs ISO 27001 Q1 2026
**Fixture**: `tests/fixtures/hera_it/` (7 documenti)
**Incoerenze attese**: 4

| Rule ID | Descrizione | Severity | Valori chiave |
|---------|-------------|----------|---------------|
| R001 | Azure commitment 580.000 EUR > allocation CTO 500.000 EUR | HIGH | sforamento +80k EUR (+16%) |
| R002 | ISO 27001 scade 2026-03-31, commitment Azure copre 2026-12-31 | CRITICAL | gap 9 mesi senza cert. |
| R003 | Multi-cloud totale 855k EUR (Azure 580k + AWS 190k + GCP 85k) > budget CdA 800k | HIGH | sforamento +55k (+6.9%) |
| R004 | Azure = 67.8% del totale — in avvicinamento soglia 70% vendor lock-in | MEDIUM | monitoraggio consigliato |

```
✓ R001: CloudCommitment(Azure, 580000) > CloudBudgetAllocation(Azure, 500000)
✓ R002: ISO27001(valid_to=2026-03-31) ≠ CloudCommitment(period_end=2026-12-31)
✓ R003: 855.000 EUR > BudgetApproval(2026, 800000)
✓ R004: concentration_pct=67.8% — MEDIUM alert
```

---

### AOU MODENA — `aou_clinical`

**Scenario**: Sperimentazione clinica senza approvazione etica valida 2026
**Fixture**: `tests/fixtures/aou_clinical/` (2 documenti)
**Incoerenze attese**: 1

| Rule ID | Descrizione | Severity |
|---------|-------------|----------|
| C001 | Trial AOU-MO-2026-003 ACTIVE dal 2026-01-15 ma approvazione AVEN scaduta 2025-12-31 | CRITICAL |

```
✓ C001: ClinicalTrial(AOU-MO-2026-003, ACTIVE)
         ↳ EthicsApproval(AVEN-CE-2025-089, valid_to=2025-12-31) SCADUTA
         ↳ Rinnovo richiesto 2026-01-10, non ancora deliberato
         ↳ Art. D.Lgs. 211/2003, art. 3 — violazione immediata
```

---

### SEMSOTEC — `semsotec_product`

**Scenario**: Valvola VP3000 in commercio nell'UE senza certificazione CE valida 2026
**Fixture**: `tests/fixtures/semsotec_product/` (2 documenti)
**Incoerenze attese**: 1

| Rule ID | Descrizione | Severity |
|---------|-------------|----------|
| P001 | SEM-VALVE-PRO-3000 (VP3000-SS-DN80) ON_MARKET, cert. TÜV-CE-2023-00891 scaduta 2025-05-31 | HIGH |

```
✓ P001: Product(VP3000-SS-DN80, status=ON_MARKET)
         ↳ ProductCertification(TUV-CE-2023-00891, valid_to=2025-05-31) SCADUTA
         ↳ Rinnovo richiesto 2025-04-15, non emesso
         ↳ Dir. 2006/42/CE (Direttiva Macchine) — ritiro rischio
```

---

### DUCATI CORSE — `ducati_corse`

**Scenario**: MotoGP 2026 — Omologazione FIM scaduta, budget cap superato, token esauriti
**Fixture**: `tests/fixtures/ducati_corse/` (3 documenti)
**Incoerenze attese**: 3

| Rule ID | Descrizione | Severity | Valori chiave |
|---------|-------------|----------|---------------|
| DC001 | Motore DC-ENG-2026-V4-REV3 IN_RACE, omologazione FIM valida solo fino 2025-12-31 | CRITICAL | staging 2026 senza cert. |
| DC002 | Budget cap dichiarato 13.200.000 EUR > limite FIM 12.000.000 EUR | HIGH | sforamento +1.2M (+10%) |
| DC003 | Development tokens 2026: 3 usati su 3 allocati — margine zero | HIGH | nessun token residuo |

```
✓ DC001: RaceComponent(DC-ENG-2026-V4-REV3, IN_RACE, season=2026)
          ↳ HomologationCertificate(FIM-MOTO-2025-ENG-0044, valid_to=2025-12-31)
          ↳ FIM MotoGP Tech. Reg. §3.1 — rischio squalifica
✓ DC002: BudgetCapDeclaration(2026, declared=13.200.000, cap=12.000.000)
          ↳ Sforamento +1.200.000 EUR — soglia sanzione FIM: >5%
✓ DC003: DevelopmentTokenAllocation(2026, used=3, total=3, remaining=0)
          ↳ FIM MotoGP Tech. Reg. §10 (Concession Rules)
```

---

### DALLARA — `dallara`

**Scenario**: IR18 IndyCar 2026 in competizione con crash test FIA scaduto
**Fixture**: `tests/fixtures/dallara/` (3 documenti)
**Incoerenze attese**: 1

| Rule ID | Descrizione | Severity |
|---------|-------------|----------|
| DA001 | Veicolo DAL-IR18-2026-001 IN_COMPETITION, cert. crash test FIA-CTC-2024-DAL-IR18-003 scaduta 2025-12-31 | CRITICAL |

```
✓ DA001: Vehicle(DAL-IR18-2026-001, IN_COMPETITION, IndyCar 2026)
          ↳ CrashTestCertification(FIA-CTC-2024-DAL-IR18-003, valid_to=2025-12-31)
          ↳ Kit aerodinamico 2026 richiede ri-certificazione strutturale
          ↳ FIA Technical Regulations §15 (Safety Structures)
```

---

### PRADA — `prada`

**Scenario**: DPP e Supply Chain FW2026 — fornitori tier 1 non certificati
**Fixture**: `tests/fixtures/prada/` (3 documenti)
**Incoerenze attese**: 2

| Rule ID | Descrizione | Severity |
|---------|-------------|----------|
| PR002 | Fornitore tier 1 MBM Manifattura: audit etico PENDING, nessuna certificazione materiale | HIGH |
| PR003 | Conceria Walpier: certificazione LWG Gold scaduta 2025-10-31, produzione FW2026 nel 2026 | HIGH |

```
✓ PR002: Supplier(MBM Manifattura, tier=1, ethical_audit_status=PENDING)
          ↳ Hardware metallico senza cert. attiva per collezione FW2026
          ↳ CSRD ESRS S2 — Workers in the value chain
✓ PR003: Supplier(Conceria Walpier, tier=1)
          ↳ MaterialCertification(LWG-IT-2023-4412, valid_to=2025-10-31) SCADUTA
          ↳ Pelle Saffiano per PR-BAG-FW26-001 senza cert. materiale valida
```

---

## Riepilogo atteso — `--domain all`

```
============================================================
RIEPILOGO FINALE
============================================================
  [OK] hera_it              - docs: 6   incoerenze attese: 4
  [OK] aou_clinical         - docs: 2   incoerenze attese: 1
  [OK] semsotec_product     - docs: 2   incoerenze attese: 1
  [OK] ducati_corse         - docs: 3   incoerenze attese: 3
  [OK] dallara              - docs: 3   incoerenze attese: 1
  [OK] prada                - docs: 3   incoerenze attese: 2

  Totale documenti ingeriti: 19
  Totale incoerenze attese:  12
```

Output JSON salvato in `demo_output/<domain>_demo_result.json`.

---

## Verifica audit chain dopo i demo

```bash
uv run python scripts/verify_audit_chain.py
# oppure
/audit-chain-verify
```

Ogni ingestione e ogni valutazione di coerenza genera eventi nella `audit_log` MongoDB.
Dopo un run completo ci si aspettano almeno 12 eventi di tipo `agent.verifier.completed.v1`.

---

## Se fallisce

| Sintomo | Causa | Fix |
|---------|-------|-----|
| `❌ stack down` | Docker compose non attivo | `make up && make wait-ready` |
| `Fixture non trovata` | Path errato o file mancante | `ls tests/fixtures/<domain>/` |
| `0 incoerenze rilevate` | Ontologia non caricata nel coherence-service | `curl http://localhost:8003/ontologies` |
| `Ingestion failed` | ingestion-service non raggiungibile | `docker compose ps ingestion` |
| Audit chain broken | Tamper o race condition | `/audit-chain-verify` |

---

## File chiave

```
scripts/
  run_coherence_test.py          # in-process Hera-only (no Docker)
  run_demo_scenario.py           # dispatcher tutti i domini (richiede stack)
  scenarios/
    base.py                      # BaseScenario, ScenarioResult
    hera_q1_2026.py              # R001-R004
    aou_trial_2026.py            # C001
    semsotec_cert_2026.py        # P001
    ducati_season_2026.py        # DC001-DC003
    dallara_oem_2026.py          # DA001
    prada_dpp_2026.py            # PR002-PR003
tests/fixtures/
  hera_it/                       # 7 documenti Azure/AWS/GCP/ISO27001
  aou_clinical/                  # 2 documenti trial clinici
  semsotec_product/              # 2 documenti certificazioni CE
  ducati_corse/                  # 3 documenti FIM/budget cap
  dallara/                       # 3 documenti crash test/OEM
  prada/                         # 3 documenti DPP/fornitori/ESG
docs/ontologies/
  hera_it.yaml                   # R001-R004
  aou_clinical.yaml              # C001
  semsotec_product.yaml          # P001
  ducati_corse.yaml              # DC001-DC004
  dallara.yaml                   # DA001-DA004
  prada.yaml                     # PR001-PR005
```

## Riferimenti
- Skill: `cci-temporal-knowledge-graph`, `cci-ontology-yaml`, `cci-audit-chain`
- Regola: CLAUDE.md §3 R4 (zero LLM nel Verifier), R5 (audit immutabile)
- Specifiche: `CCI_AVCS_Technical_Specifications.html`, sezione §08
