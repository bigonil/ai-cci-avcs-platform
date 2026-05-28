#!/usr/bin/env bash
# .claude/hooks/pre-tool-use.sh
# CCI/AVCS — Pre-tool-use hook (v2: MongoDB + Anthropic SDK + Next.js)
# Reads the tool invocation JSON from stdin, blocks if dangerous patterns detected.
# Exit codes:
#   0  → allow
#   2  → block (Claude Code surfaces stderr to the model)

set -uo pipefail

INPUT=$(cat)

field() {
  echo "$INPUT" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('tool_input',{}).get('$1',''))" 2>/dev/null
}

TOOL_NAME=$(echo "$INPUT" | python3 -c "import json,sys; print(json.load(sys.stdin).get('tool_name',''))" 2>/dev/null)
FILE_PATH=$(field "file_path")
CONTENT=$(field "content")
NEW_STRING=$(field "new_string")
PAYLOAD="${CONTENT}${NEW_STRING}"

# =====================================================================
# R5 — Audit log mutation forbidden (MongoDB)
# =====================================================================
if echo "$PAYLOAD" | grep -qE '(audit_log|"audit_log")\s*\.(update_one|update_many|delete_one|delete_many|replace_one|find_one_and_update|find_one_and_replace|find_one_and_delete|drop|rename)\s*\('; then
  echo "❌ BLOCKED: attempt to mutate the audit_log collection." >&2
  echo "audit_log is APPEND-ONLY (R5). Allowed ops: insert_one, insert_many, find." >&2
  echo "For GDPR erasure, append a gdpr.erasure.executed.v1 event instead." >&2
  echo "See: .claude/skills/cci-audit-chain/SKILL.md" >&2
  exit 2
fi

if echo "$PAYLOAD" | grep -qE '\[["'"'"']audit_log["'"'"']\]\s*\.(update_one|update_many|delete_one|delete_many|replace_one|find_one_and_update|drop)'; then
  echo "❌ BLOCKED: bracketed access to audit_log with mutation method." >&2
  exit 2
fi

if echo "$PAYLOAD" | grep -qE 'mongosh.*audit_log.*(deleteOne|deleteMany|updateOne|updateMany|replaceOne|drop)'; then
  echo "❌ BLOCKED: mongosh command mutating audit_log." >&2
  exit 2
fi

# =====================================================================
# R3 — Direct LLM SDK forbidden, must go through cci_llm wrapper
# =====================================================================
if [[ "$FILE_PATH" == *.py ]] && [[ "$FILE_PATH" != *"libs/cci-llm/"*  ]] && [[ "$FILE_PATH" != *"tests/"* ]]; then
  if echo "$PAYLOAD" | grep -qE '^\s*from\s+anthropic\s+import' ; then
    echo "❌ BLOCKED: direct 'from anthropic import ...' outside libs/cci-llm/ or tests/" >&2
    echo "Use cci_llm.LLMClient — enforces grounding, PII guard, metrics, audit." >&2
    echo "See: .claude/skills/cci-grounding-enforcer/SKILL.md" >&2
    exit 2
  fi
  if echo "$PAYLOAD" | grep -qE '^\s*import\s+anthropic\b'; then
    echo "❌ BLOCKED: 'import anthropic' outside libs/cci-llm/ or tests/" >&2
    exit 2
  fi
  if echo "$PAYLOAD" | grep -qE '^\s*(from|import)\s+(openai|litellm|ollama|google\.generativeai)\b'; then
    BAD=$(echo "$PAYLOAD" | grep -oE '(openai|litellm|ollama|google\.generativeai)' | head -1)
    echo "❌ BLOCKED: LLM provider '$BAD' not allowed." >&2
    echo "CCI/AVCS uses SINGLE provider: Anthropic via cci_llm.LLMClient (Claude Sonnet 4.6)." >&2
    exit 2
  fi
fi

# =====================================================================
# R3 — Grounding enforcer disable forbidden outside tests
# =====================================================================
if [[ "$FILE_PATH" != *"tests/"* ]]; then
  if echo "$PAYLOAD" | grep -qE 'enforce_grounding\([^)]*strict\s*=\s*False'; then
    echo "❌ BLOCKED: enforce_grounding(strict=False) outside tests." >&2
    exit 2
  fi
fi

# =====================================================================
# Hardcoded LLM model outside libs/cci-llm and prompts
# =====================================================================
if [[ "$FILE_PATH" == *.py ]] && [[ "$FILE_PATH" != *"libs/cci-llm/"*  ]] && [[ "$FILE_PATH" != *"tests/"* ]] && [[ "$FILE_PATH" != *"prompts/"* ]]; then
  if echo "$PAYLOAD" | grep -qE 'model\s*=\s*["'"'"']claude-(sonnet|opus|haiku)-' ; then
    echo "❌ BLOCKED: hardcoded LLM model name outside libs/cci-llm/." >&2
    echo "Model is centralized via CCI_LLM_MODEL env var (default 'claude-sonnet-4-6')." >&2
    exit 2
  fi
fi

# =====================================================================
# Wrong LangGraph checkpointer (must be MongoDB-based)
# =====================================================================
if [[ "$FILE_PATH" == *.py ]]; then
  if echo "$PAYLOAD" | grep -qE 'from\s+langgraph\.checkpoint\.(postgres|sqlite|redis|memory)\s+import' ; then
    BAD=$(echo "$PAYLOAD" | grep -oE 'langgraph\.checkpoint\.[a-z]+' | head -1)
    echo "❌ BLOCKED: '$BAD' not aligned with stack." >&2
    echo "Use AsyncMongoDBSaver from 'langgraph-checkpoint-mongodb'." >&2
    exit 2
  fi
fi

# =====================================================================
# R1 — Cross-service imports forbidden
# =====================================================================
if [[ "$FILE_PATH" =~ ^\./services/([^/]+)/ ]] || [[ "$FILE_PATH" =~ ^services/([^/]+)/ ]]; then
  CURRENT_SERVICE="${BASH_REMATCH[1]}"
  if echo "$PAYLOAD" | grep -qE "^\s*(from|import)\s+services\.([a-z_]+)" ; then
    OTHER=$(echo "$PAYLOAD" | grep -oE "services\.[a-z_]+" | head -1 | cut -d'.' -f2)
    if [[ -n "$OTHER" && "$OTHER" != "$CURRENT_SERVICE" ]]; then
      echo "❌ BLOCKED: service '$CURRENT_SERVICE' importing from service '$OTHER'." >&2
      echo "Bounded context isolation: use REST API or CloudEvents." >&2
      exit 2
    fi
  fi
fi

# =====================================================================
# R7 — Hardcoded secrets / DB URIs / API keys
# =====================================================================
if [[ "$FILE_PATH" == *.py ]] || [[ "$FILE_PATH" == *.yml ]] || [[ "$FILE_PATH" == *.yaml ]] || [[ "$FILE_PATH" == *.ts ]] || [[ "$FILE_PATH" == *.tsx ]]; then
  if echo "$PAYLOAD" | grep -qE '(MONGODB_URI|MONGO_URL)\s*=\s*["'"'"']mongodb://[^${"'"'"']*:[^${"'"'"']*@' ; then
    echo "❌ BLOCKED: hardcoded MongoDB URI with credentials." >&2
    exit 2
  fi
  if echo "$PAYLOAD" | grep -qE 'NEO4J_(URI|URL|PASSWORD)\s*=\s*["'"'"'][^${"'"'"']{8,}["'"'"']' ; then
    echo "❌ BLOCKED: hardcoded Neo4j credentials." >&2
    exit 2
  fi
  if echo "$PAYLOAD" | grep -qE 'sk-ant-[a-zA-Z0-9_\-]{30,}' ; then
    echo "❌ BLOCKED: Anthropic API key in plaintext." >&2
    echo "ANTHROPIC_API_KEY must come from Vault via env var." >&2
    exit 2
  fi
  if echo "$PAYLOAD" | grep -qE '\bsk-[a-zA-Z0-9]{30,}\b' ; then
    echo "❌ BLOCKED: API key in plaintext (or wrong provider)." >&2
    exit 2
  fi
  if echo "$PAYLOAD" | grep -qE '\bAKIA[0-9A-Z]{16}\b' ; then
    echo "❌ BLOCKED: AWS access key in plaintext." >&2
    exit 2
  fi
fi

# =====================================================================
# Premature K8s materials
# =====================================================================
if [[ "$FILE_PATH" =~ /infra/k8s/.+\.ya?ml$ ]] || [[ "$FILE_PATH" =~ /helm-chart/ ]] || [[ "$FILE_PATH" =~ kustomization\.yaml$ ]]; then
  echo "❌ BLOCKED: K8s/Helm materials reserved for Phase 3." >&2
  exit 2
fi

# =====================================================================
# .env file (only .env.example allowed)
# =====================================================================
if [[ "$FILE_PATH" =~ /\.env$ ]] || [[ "$FILE_PATH" =~ /\.env\.local$ ]] || [[ "$FILE_PATH" =~ /\.env\.production$ ]] || [[ "$FILE_PATH" == ".env" ]]; then
  echo "❌ BLOCKED: never commit .env — only .env.example with placeholders." >&2
  exit 2
fi

# =====================================================================
# Frontend: forbidden libraries (incompatible with stack)
# =====================================================================
if [[ "$FILE_PATH" == *frontend/*.tsx ]] || [[ "$FILE_PATH" == *frontend/*.ts ]] || [[ "$FILE_PATH" == *frontend/package.json ]]; then
  if echo "$PAYLOAD" | grep -qE '@mui/|"@chakra-ui|@mantine/|"antd"' ; then
    BAD=$(echo "$PAYLOAD" | grep -oE '@mui/[a-z\-]+|@chakra-ui[a-z\-]+|@mantine/[a-z\-]+|"antd"' | head -1)
    echo "❌ BLOCKED: UI library '$BAD' incompatible with shadcn/ui." >&2
    echo "Use 'pnpm dlx shadcn-ui add <component>' to generate primitives in repo." >&2
    exit 2
  fi
  if echo "$PAYLOAD" | grep -qE '^\s*import\s+useSWR|from\s+["'"'"']swr["'"'"']' ; then
    echo "❌ BLOCKED: SWR not used. Use @tanstack/react-query." >&2
    exit 2
  fi
  if echo "$PAYLOAD" | grep -qiE 'NEXT_PUBLIC_[A-Z_]*(ANTHROPIC|OPENAI|API_KEY|SECRET|TOKEN|VAULT)' ; then
    echo "❌ BLOCKED: NEXT_PUBLIC_* variable that looks like a secret exposes it to the client bundle." >&2
    echo "API keys, tokens and secrets live only in backend env vars (no NEXT_PUBLIC_ prefix)." >&2
    exit 2
  fi
  if echo "$PAYLOAD" | grep -qE 'api\.anthropic\.com|@anthropic-ai/sdk' ; then
    echo "❌ BLOCKED: frontend must not call Anthropic API directly." >&2
    echo "All LLM calls go through backend (cci_llm.LLMClient)." >&2
    exit 2
  fi
fi

# =====================================================================
# Prompt hardcoded outside prompts/ directory
# =====================================================================
if [[ "$FILE_PATH" == *.py ]] && [[ "$FILE_PATH" != *"prompts/"* ]] && [[ "$FILE_PATH" != *"tests/"* ]]; then
  RC=0
  echo "$PAYLOAD" | python3 -c '
import sys, re
src = sys.stdin.read()
matches = re.findall(r"""[\"]{3}.*?[\"]{3}""", src, re.DOTALL)
for m in matches:
    if len(m) > 500 and re.search(r"(You are|Sei un|Your task|System:|Assistant:|Human:)", m):
        sys.exit(42)
sys.exit(0)
' 2>/dev/null || RC=$?
  if [[ $RC -eq 42 ]]; then
    echo "⚠️  WARNING: long prompt-like string detected outside prompts/ directory." >&2
    echo "Prompts should live in services/agents/src/cci_agents/prompts/v{N}/*.j2 — versioned." >&2
  fi
fi

exit 0
