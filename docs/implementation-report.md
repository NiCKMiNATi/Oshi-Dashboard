# v0.1 implementation report

This report records the backend-foundation milestone. The subsequent frontend integration is documented in [the frontend report](frontend-integration-report.md).

Completed on 2026-09-12. The previously empty workspace is now a Git repository on `main`, with the requested directory structure, backend foundation, and minimal frontend scaffold. Files are local and uncommitted; no remote was configured.

## Delivered

- All four SQLAlchemy models and the exact requested enum values.
- Pydantic create/read/patch schemas with URL, range, timestamp, relationship, and merged date validation.
- All ten requested HTTP operations, combined update filters, pagination, and complete stats buckets.
- Nested keyword management, atomic relationship changes, deletion that preserves update history, and automatic score refresh.
- One local SQLite database with foreign keys, constraints, and UTC timestamp round-trips.
- Idempotent opt-in seed data: three oshi (進撃の巨人, 原神, Ryujin), nine keywords, and ten fictional updates covering every category and status.
- Executable setup, backend development, seed, and test scripts; Python and npm dependency locks.
- A dark-only Next.js/TypeScript/App Router placeholder with no dashboard functionality or backend integration.
- Scope, API, architecture, scoring, data, and agent documentation.

## Files added

All 50 project files are new; no pre-existing source files were modified or removed. Next.js generated the frontend agent instruction files during the development-server smoke test.

```text
.editorconfig
.gitignore
AGENTS.md
README.md
backend/.env.example
backend/pyproject.toml
backend/requirements-dev.lock
backend/app/__init__.py
backend/app/config.py
backend/app/database.py
backend/app/main.py
backend/app/models.py
backend/app/schemas.py
backend/app/scoring.py
backend/app/seed.py
backend/app/text.py
backend/app/routes/__init__.py
backend/app/routes/oshi.py
backend/app/routes/stats.py
backend/app/routes/updates.py
backend/tests/conftest.py
backend/tests/test_app.py
backend/tests/test_database_and_seed.py
backend/tests/test_oshi.py
backend/tests/test_scoring.py
backend/tests/test_stats.py
backend/tests/test_updates.py
data/.gitkeep
data/README.md
docs/api.md
docs/architecture.md
docs/implementation-report.md
docs/scoring.md
docs/spec.md
frontend/AGENTS.md
frontend/CLAUDE.md
frontend/app/globals.css
frontend/app/layout.tsx
frontend/app/page.tsx
frontend/eslint.config.mjs
frontend/next-env.d.ts
frontend/next.config.ts
frontend/package-lock.json
frontend/package.json
frontend/tsconfig.json
scripts/README.md
scripts/dev-backend.sh
scripts/seed.sh
scripts/setup.sh
scripts/test-backend.sh
```

Local generated artifacts also exist: `.git/`, `backend/.venv/`, `frontend/node_modules/`, `frontend/.next/`, and seeded `data/oshi.db`. Dependencies, build output, test caches, coverage output, and SQLite files are excluded from source control.

## Verification

Verified with Python 3.12.5, Node 22.11.0, and npm 10.9.0 on this macOS workspace. Installed application versions include FastAPI 0.141.1, SQLAlchemy 2.0.52, Pydantic 2.13.5, Next.js 16.3.5, React 19.3.0, and TypeScript 5.9.3.

| Check | Result |
| --- | --- |
| `./scripts/setup.sh` | Passed; Python lock installation, editable package installation, and `npm ci` completed. |
| `./scripts/test-backend.sh --cov=app --cov-report=term-missing --tb=short` | **88 passed**, 98% application line coverage (492/500 statements). |
| `backend/.venv/bin/ruff check backend` | Passed. |
| `backend/.venv/bin/ruff format --check backend` | Passed; 20 Python files formatted. |
| `backend/.venv/bin/python -m pip check` | No broken requirements. |
| `npm --prefix frontend run lint` | Passed. |
| `npm --prefix frontend run typecheck` | Passed, including Next route type generation. |
| `npm --prefix frontend run build` | Passed; placeholder and not-found routes built. |
| npm install/ci audit | Zero reported vulnerabilities. |
| `bash -n` on all four shell scripts | Passed. |
| `./scripts/seed.sh`, run twice | First: 3 oshi / 10 updates added. Second: 0 / 0 added. |
| Live backend smoke test using `scripts/dev-backend.sh` | Oshi list, updates list/detail, combined filter, stats, OpenAPI, and docs returned HTTP 200. |
| Live frontend smoke test using `npm run dev` | `/` returned HTTP 200 with the expected placeholder content. |
| Git ignore checks | Database, venv, node_modules, and `.next` are excluded. |

Backend coverage includes CRUD, all statuses, all scoring signals, clamping, inactive oshi, normalized keywords, keyword replacement, combined filters, pagination, invalid/null input, missing IDs, atomic failed patches, foreign-key cascades, duplicate associations, timezone conversion, persistence across restarts, empty/populated stats, CORS/Host behavior, seed repeatability, and preservation of user edits. The eight statements outside pytest coverage are the seed command-line entry point, which was exercised through the shell script twice.

The live API confirmed three active oshi and ten updates. Categories: NEWS 1, EVENT 2, MERCH 3, COLLAB 1, MOVIE 1, RELEASE 1, OTHER 1. Statuses: NEW 3, SAVED 2, INTERESTED 2, GOING 1, BOUGHT 1, IGNORED 1. Both smoke-test servers were stopped afterward.

## Architectural decisions

- Keep synchronous routes and direct ORM access with one request-scoped session. No service/repository framework or background processing.
- Resolve SQLite paths relative to the repository, independent of working directory. Enable foreign keys on every connection and use explicit transactions.
- Keep timestamps in UTC; require offsets on timestamp input and treat event dates as calendar dates.
- Manage keywords through oshi endpoints and links through update `oshi_ids`. Preserve updates when an oshi is deleted.
- Compute relevance server-side using the fixed requested bonuses once per signal. Refresh linked scores when oshi inputs change. [Scoring documentation](scoring.md) records the interpretation of keyword weights, Japan locations, deadlines, and irrelevant editorials.
- Initialize missing tables with `create_all`; introduce an explicit migration before changing an existing schema containing personal data.
- Seed only on explicit request. Fixtures use clear fictional labels and non-resolving sample URLs; the Ryujin fixture assumes ITZY's Ryujin.
- Bind dev servers to loopback and disable Next.js telemetry in npm scripts. Keep the six `oshi` command names reserved.

## Blockers and limits

There are no blockers for this milestone. All requested backend work is implemented and validated.

Frontend dashboard/Figma implementation, MSN ingestion, authentication, deployment, PostgreSQL, and the reserved CLI commands remain outside scope. No migration framework or automated ingestion was introduced. Scoring uses documented deterministic heuristics, not semantic classification. Standard interactive API documentation loads its UI assets from CDNs; the API and `/openapi.json` remain local.

The lock uses HTTPX2 for the current Starlette TestClient, and tests narrowly ignore one upstream AnyIO deprecated alias while treating other warnings as errors. ESLint 9 emits an upstream end-of-support notice during installation; linting passes with the pinned TypeScript ESLint version on the installed Node version.

Start the seeded backend with `./scripts/dev-backend.sh`. Full usage is in the [README](../README.md).
