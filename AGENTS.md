# Oshi Dashboard

This is a private, local personal dashboard. The backend, frontend integration, local macOS CLI, and manual RSS/Atom ingestion are implemented.

## Scope and boundaries

- Use Next.js, TypeScript, and App Router in `frontend/`.
- Use FastAPI, Python 3.12+, SQLAlchemy 2, and SQLite in `backend/`.
- Keep the UI dark-only and desktop-first. The authorized routes are `/` (dashboard/feed with a detail drawer) and `/oshi` (management).
- Treat backend architecture and API contracts as stable. Report a concrete integration mismatch before a large backend change.
- Use the typed API layer in `frontend/lib/api.ts`; do not scatter raw fetch calls through UI components. React state, hooks, and the existing context are sufficient.
- Use the real API for all data. Keep search client-side over loaded updates. Show loading, empty, error, and offline states.
- Discovery uses `/api/discover` and its track endpoint, with a separate local catalog and optional identity links. Keep manual Oshi creation independent; deleting a tracked Oshi must preserve catalog entries. Startup may insert missing catalog metadata only, never personal following or updates. Preserve existing tables and data during additive schema changes.
- Keep development servers bound to `127.0.0.1`. No authentication, deployment, PostgreSQL, or MSN ingestion in this milestone.
- Keep code direct: route functions, Pydantic schemas, SQLAlchemy models, and a pure scoring function. Do not introduce repositories, service frameworks, queues, or plugin abstractions.
- Manual ingestion uses the small SourceAdapter contract in `backend/app/ingestion/`; adapters return normalized data and never write ORM models. Preserve per-source transactions, dedupe, active-only matching, existing scoring, and dry-run isolation. Read `docs/ingestion.md` before changing fetch behavior. Windows Task Scheduler support is implemented by `scripts/oshi_windows.py` and `scripts/windows_scheduler.ps1`; read `docs/background-fetch-windows.md` before changing scheduling. Keep it independent of dashboard lifecycle.
- Keep database files, secrets, virtual environments, and generated build files out of Git. Never delete or reset personal data to fix a schema problem.
- Demo updates must be clearly marked as fictional. Seeding must preserve existing rows and user edits.
- The dependency-free CLI in `scripts/oshi.py` implements `oshi kaishi`, `oshi shuuryou`, `oshi saikidou`, `oshi status`, `oshi hiraku`, `oshi test`, and `oshi fetch`, plus documented English aliases. Fetch delegates to backend dependencies and must work with both services stopped. Keep runtime state/logs in ignored `.runtime/` and never stop a process based only on its name or listening port.
- Preserve process ownership validation, detached groups, startup rollback, command locking, and restoration after tests. Read `docs/local-cli.md` before changing lifecycle behavior. Never edit shell startup files as part of installation without explicit instruction.

## Working conventions

- Read `docs/architecture.md`, `docs/api.md`, `docs/scoring.md`, and `docs/frontend-integration.md` before changing integration behavior.
- Keep the enums and public API compatible with the contract in `docs/spec.md`.
- Use UTC for timestamps and explicit offsets in API input; event date fields are calendar dates.
- Validate partial updates against the merged record. Keep relationship changes and score recalculation in the same transaction.
- Update documentation when making an API or scoring decision.
- Use isolated temporary SQLite files in tests; never run tests against `data/oshi.db`.

## Validation

From the repository root after `./scripts/setup.sh`:

```sh
./scripts/test-backend.sh
./scripts/test-backend.sh scripts/tests
backend/.venv/bin/ruff check backend
backend/.venv/bin/ruff format --check backend
npm --prefix frontend run lint
npm --prefix frontend run typecheck
npm --prefix frontend run build
npm --prefix frontend run test:integration
```

Integration tests require installed Google Chrome and free ports 3000/8000. They launch the real backend against a disposable database, never `data/oshi.db`. Only run the checks relevant to the change. Report changed files, validation, architectural decisions, and blockers.

`oshi test` runs the backend/CLI tests, frontend lint/typecheck, and the existing browser integration suite. It temporarily stops CLI-owned services and restores their previous running state; it refuses occupied ports owned by other launchers.
