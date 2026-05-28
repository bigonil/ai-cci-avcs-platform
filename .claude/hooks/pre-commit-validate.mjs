#!/usr/bin/env node
// .claude/hooks/pre-commit-validate.mjs
// CCI/AVCS — Pre-commit guardrail validation (v2: cross-platform Node.js)
// Runs the full guardrail check on staged changes.
// Invoke: node .claude/hooks/pre-commit-validate.mjs
// Exit: 0 = ok, 1 = violations

import { execSync } from 'child_process';
import { existsSync } from 'fs';

const SEP = '━'.repeat(61);
let fail = 0;

function run(cmd) {
  try { return execSync(cmd, { encoding: 'utf8', timeout: 30000, stdio: ['pipe','pipe','pipe'] }).trim(); }
  catch (e) { return (e.stdout || '').trim(); }
}
function hasCmd(cmd) {
  try { execSync(process.platform === 'win32' ? `where ${cmd}` : `which ${cmd}`, { stdio: 'pipe' }); return true; }
  catch { return false; }
}
function staged(filter = '') {
  const f = filter ? `--diff-filter=${filter}` : '';
  return run(`git diff --cached --name-only ${f}`).split('\n').filter(Boolean);
}

console.log(SEP);
console.log('  CCI/AVCS · pre-commit guardrail validation (v2)');
console.log(SEP);

// 1. ruff + mypy on staged Python files
const stagedPy = staged('ACM').filter(f => f.endsWith('.py'));
if (stagedPy.length) {
  console.log(`\n▶  ruff check (${stagedPy.length} python files)`);
  const ruffCmd = hasCmd('ruff') ? 'ruff' : (hasCmd('uv') ? 'uv run ruff' : null);
  if (ruffCmd) {
    try { execSync(`${ruffCmd} check ${stagedPy.join(' ')}`, { stdio: 'inherit' }); }
    catch { fail = 1; }
  }

  const srcPy = stagedPy.filter(f => f.includes('/src/'));
  if (srcPy.length) {
    console.log('\n▶  mypy --strict (src files only)');
    const mypyCmd = hasCmd('mypy') ? 'mypy' : (hasCmd('uv') ? 'uv run mypy' : null);
    if (mypyCmd) {
      try { execSync(`${mypyCmd} --strict ${srcPy.join(' ')}`, { stdio: 'inherit' }); }
      catch { fail = 1; }
    }
  }
}

// 1b. Frontend TS lint
const stagedTs = staged('ACM').filter(f => /\.(ts|tsx)$/.test(f) && f.startsWith('frontend/'));
if (stagedTs.length && existsSync('frontend') && hasCmd('pnpm')) {
  console.log('\n▶  Frontend lint + typecheck');
  try { execSync('pnpm lint && pnpm typecheck', { cwd: 'frontend', stdio: 'inherit' }); }
  catch { fail = 1; }
}

// 2. R5 — Audit log mutation scan
console.log('\n▶  R5 — audit_log immutability scan (MongoDB)');
const diff = run('git diff --cached -U0');
if (/^\+.*(audit_log)\s*\.\s*(?:update_one|update_many|delete_one|delete_many|replace_one|find_one_and_update|drop|rename)/m.test(diff)) {
  console.error('   ❌ Found audit_log mutation in staged changes');
  fail = 1;
} else {
  console.log('   ✓ no violations');
}

// 3. R3 — Direct LLM SDK scan
console.log('\n▶  R3 — LLM SDK isolation scan');
const pyFiles = staged('ACM').filter(f => f.endsWith('.py') && !f.includes('libs/cci-llm') && !f.includes('/tests/'));
let badLlm = false;
for (const f of pyFiles) {
  try {
    const content = run(`git show ":${f}"`);
    if (/^\s*(?:from|import)\s+(?:anthropic|openai|litellm|ollama)\b/m.test(content)) {
      console.error(`   ❌ Direct LLM SDK import in: ${f}`);
      badLlm = true;
    }
  } catch { /* skip */ }
}
if (badLlm) fail = 1; else console.log('   ✓ no violations');

// 3b. Wrong LangGraph checkpointer
console.log('\n▶  R3 — LangGraph checkpointer alignment (must be MongoDB)');
if (/^\+.*from\s+langgraph\.checkpoint\.(?:postgres|sqlite|redis|memory)\s+import/m.test(diff)) {
  console.error('   ❌ Non-MongoDB LangGraph checkpointer in staged changes');
  fail = 1;
} else {
  console.log('   ✓ no violations');
}

// 4. R1 — Cross-service import scan
console.log('\n▶  R1 — bounded context isolation');
let badImports = false;
for (const f of stagedPy) {
  const m = f.match(/^services\/([^/]+)\//);
  if (!m) continue;
  const svc = m[1];
  try {
    const content = run(`git show ":${f}"`);
    const cross = content.match(/^\s*(?:from|import)\s+services\.([a-z_]+)/m);
    if (cross && cross[1] !== svc) {
      console.error(`   ❌ ${f} imports from another service: ${cross[1]}`);
      badImports = true;
    }
  } catch { /* skip */ }
}
if (badImports) fail = 1; else console.log('   ✓ no violations');

// 5. Secret leakage scan
console.log('\n▶  Secret leakage scan');
if (/^\+.*(?:sk-[a-zA-Z0-9]{30,}|sk-ant-[a-zA-Z0-9_-]{30,}|AKIA[0-9A-Z]{16})/m.test(diff)) {
  console.error('   ❌ Possible API key/secret in staged changes.');
  fail = 1;
} else {
  console.log('   ✓ no obvious secrets');
}
if (staged().some(f => /^\.env$|\/\.env$|\.env\.production$|\/secrets\//.test(f))) {
  console.error('   ❌ Sensitive file staged (.env, secrets/).');
  fail = 1;
}

// 6. Premature K8s
console.log('\n▶  Premature K8s materials');
if (staged().some(f => /^infra\/k8s\/.+\.ya?ml$|helm-chart\/|kustomization\.yaml/.test(f))) {
  console.error('   ❌ K8s/Helm files staged (Phase 3+).');
  fail = 1;
} else {
  console.log('   ✓ no violations');
}

// 7. Frontend forbidden libs
console.log('\n▶  Frontend stack alignment (shadcn/ui + TanStack Query)');
if (existsSync('frontend/package.json') && stagedTs.length) {
  if (/^\+.*(?:@mui\/|"@chakra-ui|@mantine\/|"antd")/m.test(diff)) {
    console.error('   ❌ Incompatible UI library staged.');
    fail = 1;
  } else {
    console.log('   ✓ no violations');
  }
} else {
  console.log('   (no frontend changes staged)');
}

// Summary
console.log('\n' + SEP);
if (fail === 0) {
  console.log('  ✅  All guardrails passed. Proceed to commit.');
} else {
  console.log('  ❌  Guardrail violations found. Fix before committing.');
}
console.log(SEP);
process.exit(fail);
