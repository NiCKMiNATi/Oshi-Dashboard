# Oshi Dashboard

A private, local personal oshi-information dashboard. Version 0.1 connects a dark-only Next.js dashboard and oshi management screen to a local FastAPI/SQLite backend.

## Quick start

Requires Python 3.12+ and Node.js 20.9+ with npm. Run from this directory:

```sh
./scripts/setup.sh
./scripts/seed.sh
./scripts/dev-backend.sh
```

The API runs at `http://127.0.0.1:8000`. Interactive API docs: [Swagger UI](http://127.0.0.1:8000/docs); machine-readable schema: [OpenAPI](http://127.0.0.1:8000/openapi.json).

In a separate terminal, start the frontend:

```sh
npm --prefix frontend run dev
```

Open `http://127.0.0.1:3000` for the feed or `http://127.0.0.1:3000/oshi` to manage your following. Both servers run in the foreground; stop each with Ctrl-C.

## What is included

- SQLAlchemy models for `Oshi`, `Keyword`, `Update`, and `UpdateOshi`, backed by `data/oshi.db`.
- Oshi create/list/edit/delete, nested keyword editing, update create/list/detail/edit/status, and aggregate stats.
- Combined `oshi`, `category`, `status`, and `min_score` filters, with update pagination.
- Automatic deterministic scoring with the requested weights and a 0–100 clamp.
- Repeatable, opt-in demo seeding for 進撃の巨人, 原神, and Ryujin, with ten fictional updates covering all categories and statuses.
- Isolated backend unit/API tests and locked Python/npm dependencies.
- A persistent desktop sidebar, category/oshi/status/score filters, client-side search, update cards, and an accessible detail drawer.
- Persistent status actions and oshi create/edit/pause/delete forms, feed stats, and documented scoring rules.
- Loading, empty, request-error, and backend-offline states with retry; no substitute network data.

Demo records use `[DEMO]` titles, explicit fictional notices, and `example.invalid` URLs. They are realistic fixtures, not verified announcements. The Ryujin fixture assumes ITZY's Ryujin. Seeding again adds missing fixtures while preserving existing records and user edits; it does not refresh dates. Startup creates missing tables but never seeds automatically.

## Repository

```text
frontend/  Next.js + TypeScript + App Router screens, API client, browser tests
backend/   FastAPI application, SQLAlchemy models, seed module, tests
scripts/   Setup, foreground development, seed, and test scripts
data/      Ignored local SQLite database
docs/      Scope, architecture, API contract, scoring, and verification report
AGENTS.md  Instructions for future coding work
```

## Development and configuration

The backend defaults to `data/oshi.db`, resolved from the repository location even when launched from another directory. Override it by exporting a filesystem path:

```sh
export OSHI_DATABASE_PATH=/absolute/path/to/oshi.db
./scripts/dev-backend.sh
```

`backend/.env.example` documents this setting; `.env` is not loaded automatically. The setup script uses `python3` by default; `PYTHON_BIN=python3.12 ./scripts/setup.sh` selects a different interpreter. The backend package is installed in editable mode inside `backend/.venv`.

The frontend uses `NEXT_PUBLIC_API_URL`, defaulting to `http://127.0.0.1:8000`. To override it, copy `frontend/.env.example` to `frontend/.env.local`, edit the value, and restart Next.js. Production builds embed public environment values and must be rebuilt after a change. Use port 3000 for the frontend to match the backend’s existing CORS origins.

```sh
./scripts/test-backend.sh --cov=app --cov-report=term-missing
backend/.venv/bin/ruff check backend
backend/.venv/bin/ruff format --check backend
npm --prefix frontend run lint
npm --prefix frontend run typecheck
npm --prefix frontend run build
npm --prefix frontend run test:integration
```

Tests create temporary databases and never use the personal database. Browser integration tests require Google Chrome and free ports 3000/8000; stop your dev servers before running them. They launch both servers automatically. Database files and generated dependencies/build output are ignored by Git. For schema changes, see [architecture](docs/architecture.md); `create_all` does not migrate existing tables.

## Project documentation

- [Scope and original contract](docs/spec.md)
- [Architecture and decisions](docs/architecture.md)
- [API reference and curl examples](docs/api.md)
- [Scoring rules and interpretation](docs/scoring.md)
- [Verification and handoff](docs/implementation-report.md)
- [Frontend behavior and integration](docs/frontend-integration.md)
- [Frontend verification report](docs/frontend-integration-report.md)
- [Script usage and reserved CLI commands](scripts/README.md)

The UI follows the accessible [Figma dashboard](https://www.figma.com/design/dS4aiNmBAUBURfRpKK6dgk?node-id=2-2) and [management frame](https://www.figma.com/design/dS4aiNmBAUBURfRpKK6dgk?node-id=2-116), with the supplied dark tokens. The connector exposes these under “v0.1 Wireframes”; a separate “v0.1 Prototype” page was not available during implementation.

MSN ingestion, authentication, deployment, PostgreSQL, and the reserved `oshi` CLI are outside this milestone.
