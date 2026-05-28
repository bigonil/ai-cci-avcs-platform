#!/usr/bin/env node
// .claude/hooks/post-tool-use.mjs
// CCI/AVCS — Post-tool-use hook (v2: cross-platform Node.js)
// Runs linter checks on Python files modified by the previous tool invocation.
// Soft-fail: always exits 0 — issues are signals to Claude, not blockers.

import { readFileSync, existsSync, readdirSync } from 'fs';
import { execSync } from 'child_process';
import { basename, dirname, join } from 'path';

let raw;
try { raw = readFileSync(0, 'utf8').trim(); } catch { process.exit(0); }
let input;
try { input = JSON.parse(raw); } catch { process.exit(0); }

const filePath = (input.tool_input?.file_path || '').replace(/\\/g, '/');

// Only act on Python files
if (!filePath || !filePath.endsWith('.py') || !existsSync(filePath)) process.exit(0);

// Skip generated / vendored
if (/\.venv|node_modules|__pycache__|\.pyc/.test(filePath)) process.exit(0);

let issues = 0;

function tryExec(cmd) {
  try { return execSync(cmd, { encoding: 'utf8', timeout: 30000, stdio: ['pipe','pipe','pipe'] }); }
  catch (e) { return e.stdout || e.stderr || ''; }
}

function hasCmd(cmd) {
  try { execSync(process.platform === 'win32' ? `where ${cmd}` : `which ${cmd}`, { stdio: 'pipe' }); return true; }
  catch { return false; }
}

// --- ruff check ---
const ruffCmd = hasCmd('ruff') ? 'ruff' : (hasCmd('uv') ? 'uv run ruff' : null);
if (ruffCmd) {
  try {
    execSync(`${ruffCmd} check --no-fix --output-format=concise "${filePath}"`, { stdio: 'pipe', timeout: 15000 });
  } catch (e) {
    const out = (e.stdout || '').toString().split('\n').slice(0, 20).join('\n');
    process.stderr.write(`🟡 ruff issues in ${filePath}:\n${out}\n`);
    issues++;
  }
}

// --- mypy strict (only on src/ files) ---
if (filePath.includes('/src/') && existsSync('pyproject.toml')) {
  const mypyCmd = hasCmd('mypy') ? 'mypy' : (hasCmd('uv') ? 'uv run mypy' : null);
  if (mypyCmd) {
    try {
      execSync(`${mypyCmd} --strict --no-error-summary "${filePath}"`, { stdio: 'pipe', timeout: 30000 });
    } catch (e) {
      const out = (e.stdout || '').toString().split('\n').slice(0, 10).join('\n');
      process.stderr.write(`🟡 mypy --strict issues in ${filePath}:\n${out}\n`);
      issues++;
    }
  }
}

// --- check for corresponding test file ---
if (filePath.includes('/src/') && !basename(filePath).startsWith('__init__')) {
  const modName = basename(filePath, '.py');
  const testDir = dirname(filePath).replace(/\/src\/[^/]*$/, '/tests');
  if (existsSync(testDir)) {
    // Cross-platform: read test files with Node instead of grep
    let found = false;
    try {
      const files = readdirSync(testDir, { recursive: true }).filter(f => f.toString().endsWith('.py'));
      for (const tf of files) {
        const content = readFileSync(join(testDir, tf.toString()), 'utf8');
        if (content.includes(modName)) { found = true; break; }
      }
    } catch { /* skip */ }
    if (!found) {
      process.stderr.write(`🟡 No test found referencing module '${modName}' in ${testDir}\n`);
      process.stderr.write(`   Definition of Done requires unit tests with ≥80% coverage.\n`);
      issues++;
    }
  }
}

if (issues > 0) {
  process.stderr.write(`\nℹ️  ${issues} issue(s) found post-edit. Address before next commit.\n`);
}

// Soft-fail: always exit 0
process.exit(0);
