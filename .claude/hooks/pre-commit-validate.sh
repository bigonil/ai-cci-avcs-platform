#!/usr/bin/env bash
# .claude/hooks/pre-commit-validate.sh
# CCI/AVCS — Pre-commit validation (v2: MongoDB + Anthropic SDK + Next.js)
# Runs the full guardrail validation on staged changes.
# Invoke manually: bash .claude/hooks/pre-commit-validate.sh
# Exit codes: 0=ok, 1=violations found

set -uo pipefail

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  CCI/AVCS · pre-commit guardrail validation (v2)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

FAIL=0

# 1. Lint + type check on staged Python files
STAGED_PY=$(git diff --cached --name-only --diff-filter=ACM 2>/dev/null | grep -E '\.py$' || true)
if [[ -n "$STAGED_PY" ]]; then
  echo ""
  echo "▶  ruff check ($(echo "$STAGED_PY" | wc -l) python files)"
  if command -v uv >/dev/null 2>&1; then
    uv run ruff check $STAGED_PY || FAIL=1
  else
    ruff check $STAGED_PY || FAIL=1
  fi

  echo ""
  echo "▶  mypy --strict (src files only)"
  SRC_PY=$(echo "$STAGED_PY" | grep -E '/src/' || true)
  if [[ -n "$SRC_PY" ]]; then
    if command -v uv >/dev/null 2>&1; then
      uv run mypy --strict $SRC_PY || FAIL=1
    else
      mypy --strict $SRC_PY || FAIL=1
    fi
  else
    echo "   (no src/ files staged)"
  fi
fi

# 1b. Lint TS/TSX
STAGED_TS=$(git diff --cached --name-only --diff-filter=ACM 2>/dev/null | grep -E '\.(ts|tsx)$' | grep -E '^frontend/' || true)
if [[ -n "$STAGED_TS" ]]; then
  echo ""
  echo "▶  Frontend lint + typecheck"
  if [[ -d "frontend" ]] && command -v pnpm >/dev/null 2>&1; then
    (cd frontend && pnpm lint) || FAIL=1
    (cd frontend && pnpm typecheck) || FAIL=1
  else
    echo "   (frontend dir or pnpm missing, skipping)"
  fi
fi

# 2. R5 — Audit log mutation scan (MongoDB)
echo ""
echo "▶  R5 — audit_log immutability scan (MongoDB)"
BAD_AUDIT=$(git diff --cached -U0 2>/dev/null | grep -E '^\+.*(audit_log)\s*\.(update_one|update_many|delete_one|delete_many|replace_one|find_one_and_update|drop|rename)' || true)
if [[ -n "$BAD_AUDIT" ]]; then
  echo "   ❌ Found audit_log mutation in staged changes:" >&2
  echo "$BAD_AUDIT" | head -5 >&2
  FAIL=1
else
  echo "   ✓ no violations"
fi

# 3. R3 — Direct LLM SDK scan
echo ""
echo "▶  R3 — LLM SDK isolation scan"
BAD_LLM=$(git diff --cached --name-only --diff-filter=ACM 2>/dev/null | grep -E '\.py$' | grep -vE '(libs/cci-llm|/tests/)' | xargs -r grep -lE '^\s*(from|import)\s+(anthropic|openai|litellm|ollama)' 2>/dev/null || true)
if [[ -n "$BAD_LLM" ]]; then
  echo "   ❌ Direct LLM SDK imports found outside libs/cci-llm/ or tests/:" >&2
  echo "$BAD_LLM" >&2
  FAIL=1
else
  echo "   ✓ no violations"
fi

# 3b. R3 — Wrong LangGraph checkpointer scan
echo ""
echo "▶  R3 — LangGraph checkpointer alignment (must be MongoDB)"
BAD_CHKPT=$(git diff --cached -U0 2>/dev/null | grep -E '^\+.*from\s+langgraph\.checkpoint\.(postgres|sqlite|redis|memory)\s+import' || true)
if [[ -n "$BAD_CHKPT" ]]; then
  echo "   ❌ Non-MongoDB LangGraph checkpointer in staged changes:" >&2
  echo "$BAD_CHKPT" | head -3 >&2
  FAIL=1
else
  echo "   ✓ no violations"
fi

# 4. R1 — Cross-service import scan
echo ""
echo "▶  R1 — bounded context isolation"
BAD_IMPORTS=0
for svc_dir in services/*/; do
  [[ -d "$svc_dir" ]] || continue
  svc=$(basename "$svc_dir")
  staged_in_svc=$(git diff --cached --name-only --diff-filter=ACM 2>/dev/null | grep -E "^$svc_dir.*\.py$" || true)
  if [[ -n "$staged_in_svc" ]]; then
    for f in $staged_in_svc; do
      [[ -f "$f" ]] || continue
      other=$(grep -oE "^\s*(from|import)\s+services\.[a-z_]+" "$f" 2>/dev/null | grep -oE "services\.[a-z_]+" | cut -d'.' -f2 | grep -v "^$svc$" || true)
      if [[ -n "$other" ]]; then
        echo "   ❌ $f imports from another service: $other" >&2
        BAD_IMPORTS=1
      fi
    done
  fi
done
if [[ $BAD_IMPORTS -eq 0 ]]; then
  echo "   ✓ no violations"
else
  FAIL=1
fi

# 5. Secret leakage scan
echo ""
echo "▶  Secret leakage scan"
if git diff --cached -U0 2>/dev/null | grep -E '^\+.*(sk-[a-zA-Z0-9]{30,}|sk-ant-[a-zA-Z0-9_\-]{30,}|AKIA[0-9A-Z]{16})' >/dev/null ; then
  echo "   ❌ Possible API key/secret in staged changes." >&2
  FAIL=1
else
  echo "   ✓ no obvious secrets"
fi

if git diff --cached --name-only 2>/dev/null | grep -E '^\.env$|/\.env$|^\.env\.production$|/secrets/' >/dev/null ; then
  echo "   ❌ Sensitive file staged (.env, secrets/)." >&2
  FAIL=1
fi

# 6. Premature K8s
echo ""
echo "▶  Premature K8s materials"
if git diff --cached --name-only 2>/dev/null | grep -E '^infra/k8s/.+\.ya?ml$|helm-chart/|kustomization\.yaml' >/dev/null ; then
  echo "   ❌ K8s/Helm files staged (Phase 3+)." >&2
  FAIL=1
else
  echo "   ✓ no violations"
fi

# 7. Frontend forbidden libs
echo ""
echo "▶  Frontend stack alignment (shadcn/ui + TanStack Query)"
if [[ -f "frontend/package.json" ]]; then
  STAGED_FE=$(git diff --cached --name-only --diff-filter=ACM 2>/dev/null | grep -E '^frontend/' || true)
  if [[ -n "$STAGED_FE" ]]; then
    BAD_FE=$(git diff --cached -U0 -- frontend/package.json 2>/dev/null | grep -E '^\+.*(@mui/|"@chakra-ui|@mantine/|"antd")' || true)
    if [[ -n "$BAD_FE" ]]; then
      echo "   ❌ Incompatible UI library staged:" >&2
      echo "$BAD_FE" >&2
      FAIL=1
    else
      echo "   ✓ no violations"
    fi
  else
    echo "   (no frontend changes staged)"
  fi
fi

# 8. ADR check on structural changes
echo ""
echo "▶  ADR check"
STRUCT_CHANGES=$(git diff --cached --name-only 2>/dev/null | grep -E '(docker-compose\.yml|pyproject\.toml|services/[^/]+/Dockerfile|libs/[^/]+/pyproject\.toml|frontend/package\.json)' || true)
ADR_CHANGES=$(git diff --cached --name-only 2>/dev/null | grep -E '^docs/adr/' || true)
if [[ -n "$STRUCT_CHANGES" ]] && [[ -z "$ADR_CHANGES" ]]; then
  echo "   ⚠️  Structural changes detected but no ADR updated." >&2
  echo "   Consider adding an ADR in docs/adr/NNNN-titolo.md"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if [[ $FAIL -eq 0 ]]; then
  echo "  ✅  All guardrails passed. Proceed to commit."
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  exit 0
else
  echo "  ❌  Guardrail violations found. Fix before committing."
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  exit 1
fi
