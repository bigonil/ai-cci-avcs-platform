#!/usr/bin/env node
// .claude/hooks/post-tool-use.cjs
// CCI/AVCS — Post-tool-use hook (v4: CJS, spawnSync, always exits 0)
// Runs linter checks on Python files modified by the previous tool invocation.
// Soft-fail: always exits 0 — issues are signals to Claude, not blockers.

'use strict';

process.on('uncaughtException', () => process.exit(0));
process.on('unhandledRejection', () => process.exit(0));

const { readFileSync, existsSync, readdirSync } = require('fs');
const { spawnSync } = require('child_process');
const { basename, dirname, join } = require('path');

let raw;
try { raw = readFileSync(0, 'utf8').trim(); } catch { process.exit(0); }
if (!raw) process.exit(0);

let input;
try { input = JSON.parse(raw); } catch { process.exit(0); }

const filePath = ((input.tool_input && input.tool_input.file_path) || '').replace(/\\/g, '/');

if (!filePath || !filePath.endsWith('.py') || !existsSync(filePath)) process.exit(0);
if (/\.venv|node_modules|__pycache__|\.pyc/.test(filePath)) process.exit(0);

let issues = 0;

// Check if a command is available — no shell, safe
function hasCmd(cmd) {
  const probe = spawnSync(
    process.platform === 'win32' ? 'where' : 'which',
    [cmd],
    { stdio: 'pipe', timeout: 5000 }
  );
  return probe.status === 0;
}

// Run a command with an explicit argument array — no shell interpolation
function runLinter(bin, args) {
  return spawnSync(bin, args, { stdio: 'pipe', timeout: 30000, encoding: 'utf8' });
}

// --- ruff check ---
// spawnSync args: no shell, filePath is a plain argument — safe against injection
const useUv = !hasCmd('ruff') && hasCmd('uv');
if (hasCmd('ruff') || useUv) {
  const [bin, args] = useUv
    ? ['uv', ['run', 'ruff', 'check', '--no-fix', '--output-format=concise', filePath]]
    : ['ruff', ['check', '--no-fix', '--output-format=concise', filePath]];

  const res = runLinter(bin, args);
  if (res.status !== 0) {
    const out = (res.stdout || '').split('\n').slice(0, 20).join('\n');
    process.stderr.write(`\u{1F7E1} ruff issues in ${filePath}:\n${out}\n`);
    issues++;
  }
}

// --- mypy strict (only on src/ files) ---
if (filePath.includes('/src/') && existsSync('pyproject.toml')) {
  const useUvMypy = !hasCmd('mypy') && hasCmd('uv');
  if (hasCmd('mypy') || useUvMypy) {
    const [bin, args] = useUvMypy
      ? ['uv', ['run', 'mypy', '--strict', '--no-error-summary', filePath]]
      : ['mypy', ['--strict', '--no-error-summary', filePath]];

    const res = runLinter(bin, args);
    if (res.status !== 0) {
      const out = (res.stdout || '').split('\n').slice(0, 10).join('\n');
      process.stderr.write(`\u{1F7E1} mypy --strict issues in ${filePath}:\n${out}\n`);
      issues++;
    }
  }
}

// --- check for corresponding test file ---
if (filePath.includes('/src/') && !basename(filePath).startsWith('__init__')) {
  const modName = basename(filePath, '.py');
  const testDir = dirname(filePath).replace(/\/src\/[^/]*$/, '/tests');
  if (existsSync(testDir)) {
    let found = false;
    try {
      const entries = readdirSync(testDir, { recursive: true });
      for (const entry of entries) {
        const name = entry.toString();
        if (!name.endsWith('.py')) continue;
        try {
          const content = readFileSync(join(testDir, name), 'utf8');
          if (content.includes(modName)) { found = true; break; }
        } catch { /* skip unreadable */ }
      }
    } catch { /* skip inaccessible testDir */ }
    if (!found) {
      process.stderr.write(
        `\u{1F7E1} No test found referencing '${modName}' in ${testDir}\n` +
        `   Definition of Done requires unit tests with ≥80% coverage.\n`
      );
      issues++;
    }
  }
}

if (issues > 0) {
  process.stderr.write(`\nℹ️  ${issues} issue(s) found post-edit. Address before next commit.\n`);
}

process.exit(0);
