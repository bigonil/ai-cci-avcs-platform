#!/usr/bin/env bash
# .claude/hooks/post-tool-use.sh
# CCI/AVCS — Post-tool-use hook
# Runs ruff and mypy on Python files modified by the previous tool invocation.
# Soft-fail: non-zero exit signals issues to Claude but does not block subsequent ops.

set -uo pipefail

INPUT=$(cat)

FILE_PATH=$(echo "$INPUT" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('tool_input',{}).get('file_path',''))" 2>/dev/null)

# Only act on Python files inside the project
if [[ -z "$FILE_PATH" ]] || [[ "$FILE_PATH" != *.py ]]; then
  exit 0
fi
if [[ ! -f "$FILE_PATH" ]]; then
  exit 0
fi

# Skip generated / vendored
case "$FILE_PATH" in
  *.venv/*|*node_modules/*|*__pycache__/*|*.pyc)
    exit 0
    ;;
esac

ISSUES=0

# --- ruff (fast linter + formatter check) ---
if command -v ruff >/dev/null 2>&1 || command -v uv >/dev/null 2>&1; then
  RUFF_CMD="ruff"
  command -v ruff >/dev/null 2>&1 || RUFF_CMD="uv run ruff"

  RUFF_OUT=$($RUFF_CMD check --no-fix --output-format=concise "$FILE_PATH" 2>&1)
  RUFF_RC=$?
  if [[ $RUFF_RC -ne 0 ]]; then
    echo "🟡 ruff issues in $FILE_PATH:" >&2
    echo "$RUFF_OUT" | head -20 >&2
    ISSUES=$((ISSUES + 1))
  fi
fi

# --- mypy strict (only if pyproject.toml configured) ---
if [[ -f "pyproject.toml" ]] && (command -v mypy >/dev/null 2>&1 || command -v uv >/dev/null 2>&1); then
  MYPY_CMD="mypy"
  command -v mypy >/dev/null 2>&1 || MYPY_CMD="uv run mypy"

  # Only run mypy on src/ or service code, skip tests for speed
  if [[ "$FILE_PATH" == *"/src/"* ]] || [[ "$FILE_PATH" == */services/*/src/* ]]; then
    MYPY_OUT=$($MYPY_CMD --strict --no-error-summary "$FILE_PATH" 2>&1)
    MYPY_RC=$?
    if [[ $MYPY_RC -ne 0 ]]; then
      echo "🟡 mypy --strict issues in $FILE_PATH:" >&2
      echo "$MYPY_OUT" | head -10 >&2
      ISSUES=$((ISSUES + 1))
    fi
  fi
fi

# --- check coverage of corresponding test file ---
if [[ "$FILE_PATH" == */src/*.py ]] && [[ "$FILE_PATH" != *"__init__.py" ]]; then
  # Heuristic: derive test path
  TEST_FILE=$(echo "$FILE_PATH" | sed -E 's|/src/[^/]+/(.*)\.py|/tests/test_\1.py|')
  TEST_FILE_FLAT=$(echo "$FILE_PATH" | sed -E 's|.*/src/[^/]+/(.*)\.py|\1|' | tr '/' '_')
  TEST_DIR=$(dirname "$FILE_PATH" | sed 's|/src/[^/]*$|/tests|')

  if [[ -d "$TEST_DIR" ]]; then
    # Look for ANY test file mentioning the module name
    MODNAME=$(basename "$FILE_PATH" .py)
    if ! grep -rqE "(from.*import.*$MODNAME|import.*$MODNAME)" "$TEST_DIR" 2>/dev/null; then
      echo "🟡 No test found referencing module '$MODNAME' in $TEST_DIR" >&2
      echo "   Definition of Done requires unit tests with ≥80% coverage." >&2
      ISSUES=$((ISSUES + 1))
    fi
  fi
fi

if [[ $ISSUES -gt 0 ]]; then
  echo "" >&2
  echo "ℹ️  $ISSUES issue(s) found post-edit. Address before next commit." >&2
fi

# Soft-fail: we always exit 0 — these are signals, not blockers
exit 0
