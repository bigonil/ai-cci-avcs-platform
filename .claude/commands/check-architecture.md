---
description: Verifica le 7 regole architetturali non negoziabili sul diff corrente o sul branch
---

# /check-architecture

Esegue una scansione architetturale completa contro le regole R1-R7 di CLAUDE.md.

## Cosa fa

Esegui lo script di validazione completo:
```bash
bash .claude/hooks/pre-commit-validate.sh
```

Se vuoi controllare l'intero branch (non solo lo staging):
```bash
# Controllo cross-service imports
echo "▶  R1 — Cross-service imports su tutto src/"
for svc in services/*/; do
    s=$(basename "$svc")
    bad=$(grep -rE "^\s*(from|import)\s+services\.[a-z_]+" "$svc/src" 2>/dev/null | grep -v "services\.$s\b" || true)
    if [[ -n "$bad" ]]; then
        echo "❌ Violazioni R1 in $s:"
        echo "$bad" | head -10
    fi
done

# Controllo LLM SDK isolation
echo "▶  R3 — LLM SDK isolation"
grep -rE "^\s*(from|import)\s+(openai|anthropic)" services/ libs/ 2>/dev/null \
  | grep -vE '(libs/cci-llm|/tests/)' \
  || echo "✓ no violations"

# Controllo audit_log mutations
echo "▶  R5 — audit_log immutability"
grep -rEi '(UPDATE|DELETE FROM|TRUNCATE|DROP TABLE)\s+audit_log' services/ scripts/ migrations/ 2>/dev/null \
  || echo "✓ no violations"

# Controllo K8s premature
echo "▶  K8s prematuro"
find infra/k8s -name '*.yaml' 2>/dev/null \
  && echo "❌ Manifest K8s presenti (Fase 3+)" \
  || echo "✓ no violations"
```

## Output atteso

Una sezione per ciascuna regola, con `✓` o lista delle violazioni.

Se ci sono violazioni: NON proporre di "rilassare" la regola. Spiega l'alternativa allineata (API REST, evento CloudEvent, wrapper `cci_llm`, append-only via `audit_log.append`, ecc.).

## Quando usarlo

- Prima di ogni merge a main
- Quando hai dubbi se una scelta sta violando l'architettura
- Setup nightly CI come gate di qualità

## Riferimenti
- CLAUDE.md §3 (le 7 regole)
- Skill: `cci-architecture-guard`
