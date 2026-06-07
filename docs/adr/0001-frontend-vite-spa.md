# ADR-0001: Replace Next.js with Vite React SPA + FastAPI BFF

**Status**: Accepted
**Date**: 2026-06-07

## Context
CLAUDE.md §4 specifies Next.js 16.2 as the frontend stack. The user explicitly requested replacing it with a Vite React SPA served by a FastAPI/Uvicorn BFF, to align the frontend with the project's Python-first deployment model and remove the Node.js runtime dependency from the production container.

## Decision
Replace `frontend/` (Next.js 16.2) with a Vite 6 + React 19 + React Router v7 SPA. The FastAPI BFF in `services/frontend/` serves the compiled `dist/` in production and proxies `/api/*` to backend services.

## Consequences
- Positive: Single Python runtime in production, simpler Docker image, no Node.js in prod.
- Positive: Vite dev server is faster than Next.js for this SPA use case.
- Negative: Loss of Next.js SSR/PPR features (not needed — frontend is a client-side dashboard).
- Negative: CLAUDE.md §4 stack spec becomes stale until updated.

## Alternatives considered
- Keep Next.js with `output: "export"` for static export — rejected, adds complexity and loses dev server proxy.
- Use a Node.js Express BFF instead of FastAPI — rejected, Python BFF keeps the stack uniform.
