---
description: Esegue la suite di test del citation enforcer per validare la regola R3 (grounding obbligatorio)
---

# /verify-grounding

Verifica che il citation enforcer di CCI/AVCS funzioni correttamente.

## Cosa fa

1. Esegui i test unitari del `citation_parser`:
   ```bash
   uv run pytest libs/cci-llm/tests/test_citation_parser.py -v
   ```

2. Esegui i test di integrazione del Generator agent contro un LLM mockato:
   ```bash
   uv run pytest services/agents/tests/integration/test_generator_grounding.py -v
   ```

3. Mostra le metriche correnti delle violation rate (se Prometheus è up):
   ```bash
   curl -s http://localhost:9090/api/v1/query?query=cci_grounding_violations_total | python3 -m json.tool
   ```

4. Se almeno un test fallisce: fermati, riporta l'output, NON suggerire di disabilitare `enforce_grounding`.

5. Se tutto passa: riepiloga con il numero di test eseguiti, il violation rate corrente (target < 1%) e i prossimi passi suggeriti.

## Quando usarlo

- Prima di un demo (Hera Q1 2026 scenario)
- Dopo modifiche a `libs/cci-llm/` o a `services/agents/src/cci_agents/generator_agent.py`
- Come gate di rilascio: se questo comando fallisce, il rilascio è bloccato

## Riferimenti
- Skill: `cci-grounding-enforcer`
- Regola: CLAUDE.md §3, R3
