#!/usr/bin/env node
// .claude/hooks/pre-tool-use.mjs
// CCI/AVCS — Pre-tool-use hook (v2: cross-platform Node.js)
// Reads tool invocation JSON from stdin, blocks if dangerous patterns detected.
// Exit codes: 0 = allow, 2 = block

import { readFileSync } from 'fs';
import { join, sep } from 'path';

let raw;
try { raw = readFileSync(0, 'utf8').trim(); } catch { process.exit(0); }
let input;
try { input = JSON.parse(raw); } catch { process.exit(0); }

const toolInput = input.tool_input || {};
const filePath  = (toolInput.file_path || toolInput.path || '').replace(/\\/g, '/');
const content   = toolInput.content || '';
const newStr    = toolInput.new_string || toolInput.new_str || '';
const payload   = content + newStr;

function block(msg) {
  process.stderr.write('❌ BLOCKED: ' + msg + '\n');
  process.exit(2);
}
function warn(msg) {
  process.stderr.write('⚠️  WARNING: ' + msg + '\n');
}

// =====================================================================
// R5 — Audit log mutation forbidden (MongoDB)
// =====================================================================
if (/(?:audit_log|"audit_log")\s*\.\s*(?:update_one|update_many|delete_one|delete_many|replace_one|find_one_and_update|find_one_and_replace|find_one_and_delete|drop|rename)\s*\(/.test(payload)) {
  block('attempt to mutate the audit_log collection.\naudit_log is APPEND-ONLY (R5). Allowed ops: insert_one, insert_many, find.\nSee: .claude/skills/cci-audit-chain/SKILL.md');
}
if (/\[["']audit_log["']\]\s*\.\s*(?:update_one|update_many|delete_one|delete_many|replace_one|drop)/.test(payload)) {
  block('bracketed access to audit_log with mutation method.');
}
if (/mongosh.*audit_log.*(?:deleteOne|deleteMany|updateOne|updateMany|replaceOne|drop)/.test(payload)) {
  block('mongosh command mutating audit_log.');
}

// =====================================================================
// R3 — Direct LLM SDK forbidden outside libs/cci-llm
// =====================================================================
if (filePath.endsWith('.py') && !filePath.includes('libs/cci-llm/') && !filePath.includes('tests/')) {
  if (/^\s*from\s+anthropic\s+import/m.test(payload))
    block("direct 'from anthropic import ...' outside libs/cci-llm/ or tests/\nUse cci_llm.LLMClient. See: .claude/skills/cci-grounding-enforcer/SKILL.md");
  if (/^\s*import\s+anthropic\b/m.test(payload))
    block("'import anthropic' outside libs/cci-llm/ or tests/");
  const banned = payload.match(/^\s*(?:from|import)\s+(openai|litellm|ollama|google\.generativeai)\b/m);
  if (banned)
    block(`LLM provider '${banned[1]}' not allowed.\nCCI/AVCS uses SINGLE provider: Anthropic via cci_llm.LLMClient.`);
}

// =====================================================================
// R3 — Grounding enforcer disable forbidden outside tests
// =====================================================================
if (!filePath.includes('tests/')) {
  if (/enforce_grounding\([^)]*strict\s*=\s*False/.test(payload))
    block('enforce_grounding(strict=False) outside tests.');
}

// =====================================================================
// Hardcoded LLM model outside libs/cci-llm
// =====================================================================
if (filePath.endsWith('.py') && !filePath.includes('libs/cci-llm/') && !filePath.includes('tests/') && !filePath.includes('prompts/')) {
  if (/model\s*=\s*["']claude-(?:sonnet|opus|haiku)-/.test(payload))
    block("hardcoded LLM model name outside libs/cci-llm/.\nModel is centralized via CCI_LLM_MODEL env var.");
}

// =====================================================================
// Wrong LangGraph checkpointer
// =====================================================================
if (filePath.endsWith('.py')) {
  const badChkpt = payload.match(/from\s+langgraph\.checkpoint\.(postgres|sqlite|redis|memory)\s+import/);
  if (badChkpt)
    block(`'langgraph.checkpoint.${badChkpt[1]}' not aligned with stack.\nUse AsyncMongoDBSaver from 'langgraph-checkpoint-mongodb'.`);
}

// =====================================================================
// R1 — Cross-service imports
// =====================================================================
const svcMatch = filePath.match(/services\/([^/]+)\//);
if (svcMatch) {
  const currentSvc = svcMatch[1];
  const crossImport = payload.match(/^\s*(?:from|import)\s+services\.([a-z_]+)/m);
  if (crossImport && crossImport[1] !== currentSvc)
    block(`service '${currentSvc}' importing from service '${crossImport[1]}'.\nBounded context isolation: use REST API or CloudEvents.`);
}

// =====================================================================
// R7 — Hardcoded secrets
// =====================================================================
if (/\.(?:py|yml|yaml|ts|tsx)$/.test(filePath)) {
  if (/sk-ant-[a-zA-Z0-9_\-]{30,}/.test(payload))
    block('Anthropic API key in plaintext.\nANTHROPIC_API_KEY must come from env var.');
  if (/\bsk-[a-zA-Z0-9]{30,}\b/.test(payload))
    block('API key in plaintext (or wrong provider).');
  if (/\bAKIA[0-9A-Z]{16}\b/.test(payload))
    block('AWS access key in plaintext.');
  if (/(?:MONGODB_URI|MONGO_URL)\s*=\s*["']mongodb:\/\/[^$]+:.*@/.test(payload))
    block('hardcoded MongoDB URI with credentials.');
}

// =====================================================================
// Premature K8s
// =====================================================================
if (/infra\/k8s\/.+\.ya?ml$/.test(filePath) || /helm-chart\//.test(filePath) || /kustomization\.yaml$/.test(filePath))
  block('K8s/Helm materials reserved for Phase 3.');

// =====================================================================
// .env file
// =====================================================================
if (/\/\.env$|^\.env$|\/\.env\.local$|\/\.env\.production$/.test(filePath))
  block('never commit .env — only .env.example with placeholders.');

// =====================================================================
// Frontend forbidden libraries
// =====================================================================
if (/frontend\/.*\.(?:tsx?|json)$/.test(filePath)) {
  if (/@mui\/|"@chakra-ui|@mantine\/|"antd"/.test(payload)) {
    const lib = payload.match(/@mui\/[a-z-]+|@chakra-ui[a-z-]*|@mantine\/[a-z-]+|"antd"/)?.[0];
    block(`UI library '${lib}' incompatible with shadcn/ui.`);
  }
  if (/^\s*import\s+useSWR|from\s+["']swr["']/m.test(payload))
    block('SWR not used. Use @tanstack/react-query.');
  if (/NEXT_PUBLIC_[A-Z_]*(?:ANTHROPIC|OPENAI|API_KEY|SECRET|TOKEN|VAULT)/i.test(payload))
    block('NEXT_PUBLIC_* variable that looks like a secret exposes it to the client bundle.');
  if (/api\.anthropic\.com|@anthropic-ai\/sdk/.test(payload))
    block('frontend must not call Anthropic API directly.\nAll LLM calls go through backend.');
}

// =====================================================================
// Prompt hardcoded outside prompts/
// =====================================================================
if (filePath.endsWith('.py') && !filePath.includes('prompts/') && !filePath.includes('tests/')) {
  const tripleQuotes = payload.match(/""".{500,}?"""/gs) || [];
  for (const m of tripleQuotes) {
    if (/You are|Sei un|Your task|System:|Assistant:|Human:/.test(m))
      warn('long prompt-like string detected outside prompts/ directory.\nPrompts should live in services/agents/src/cci_agents/prompts/');
  }
}

process.exit(0);
