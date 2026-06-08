# ADR-0002: Manual apiFetch scaffold instead of openapi-typescript-codegen

**Status**: Accepted
**Date**: 2026-06-08

## Context
CLAUDE.md §4 mandates openapi-typescript-codegen for typed API clients. The generated client requires running FastAPI services to fetch OpenAPI specs. During frontend scaffolding the services are not yet available, so a hand-written apiFetch<T> wrapper is used as a temporary scaffold.

## Decision
Use a minimal `src/lib/api.ts` wrapper for frontend development. Replace with the generated OpenAPI client in Task 20 (build finale) once services are running and specs are stable.

## Consequences
- Temporary: callers are weakly typed (T is caller-asserted, not schema-derived).
- Positive: unblocks frontend development without requiring a running stack.
- Replaced by: `pnpm gen:api` output in Task 20.

## Alternatives considered
- Generate client from saved OpenAPI JSON snapshots — rejected, snapshots would drift.
