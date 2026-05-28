---
description: Verifica completezza del mapping AI Act art. 9–15 in docs/compliance/ai-act-mapping.yaml
---

# /ai-act-check

Verifica che `docs/compliance/ai-act-mapping.yaml` sia completo, aggiornato e che ogni artifact dichiarato esista realmente.

## Cosa fa

1. Carica e valida lo schema del file:
   ```bash
   uv run python scripts/validate_ai_act_mapping.py
   ```

   Lo script verifica:
   - Tutti gli articoli in scope (9, 10, 11, 12, 13, 14, 15) sono presenti
   - Ogni `artifact.path` esiste sul filesystem
   - Le date di `review_cadence` non sono scadute oltre il dovuto
   - Lo schema YAML è valido contro `Ontology` Pydantic
   - Ogni `status: implemented` ha almeno un artifact concreto associato

2. Output atteso:
   ```
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
     CCI/AVCS · AI Act compliance mapping check
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
     File:           docs/compliance/ai-act-mapping.yaml
     Last updated:   2026-05-23 (47 days ago)
     System class:   high_risk

     Articles in scope:  7 [9, 10, 11, 12, 13, 14, 15]
     Articles missing:   0
     Artifacts:          17 declared
     Artifacts existing: 17 ✓
     Artifacts missing:  0
     Reviews overdue:    0

     ✅  Compliance mapping is complete and consistent.
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   ```

3. Se inconsistente:
   ```
     Artifacts missing:  2 ❌
       - article 13: libs/cci-llm/src/cci_llm/citation_parser.py (NOT FOUND)
       - article 14: frontend/app/hitl/page.tsx (NOT FOUND)
     Reviews overdue:    1 ⚠
       - article 9: risk-assessment.md last reviewed 2025-08-12 (review_cadence: quarterly)
   ```

4. Lista i cambi di codice recenti che POSSIBILMENTE impattano la compliance ma non hanno aggiornato il mapping:
   ```bash
   git log --since="$(yq '.last_updated' docs/compliance/ai-act-mapping.yaml)" --name-only --oneline -- libs/cci-llm/ services/governance/ services/agents/prompts/
   ```

   Se ci sono commit recenti su queste aree e `last_updated` del mapping è anteriore: **aggiorna il mapping prima del prossimo merge**.

## Quando usarlo

- Mensilmente come review periodica (compliance officer + tech lead)
- Prima di un audit esterno (CTO, DPO, certificatori)
- Quando aggiungi una nuova feature che tocca grounding, HITL, PII, modello LLM
- Quando integri un nuovo dominio verticale (potenziale ampliamento high-risk scope)

## Allineamento ISO 42001

Lo stesso mapping alimenta i requisiti di clausola 6.1.2 (AI risk assessment) e 8.3 (AI system impact assessment) di ISO 42001:2023. Aggiornare `ai-act-mapping.yaml` aggiorna automaticamente la base evidence per la certificazione.

## Riferimenti
- Skill: `cci-ai-act-compliance`
- AI Act (Reg. UE 2024/1689): https://artificialintelligenceact.eu
- ISO 42001:2023
