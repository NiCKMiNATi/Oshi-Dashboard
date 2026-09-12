# Oshi Dashboard

This is a private, local personal dashboard. The backend foundation is complete; the current milestone is the frontend integration of the dashboard and oshi management screens.

## Scope and boundaries

- Use Next.js, TypeScript, and App Router in `frontend/`.
- Use FastAPI, Python 3.12+, SQLAlchemy 2, and SQLite in `backend/`.
- Keep the UI dark-only and desktop-first. The authorized routes are `/` (dashboard/feed with a detail drawer) and `/oshi` (management).
- Treat backend architecture and API contracts as stable. Report a concrete integration mismatch before a large backend change.
- Use the typed API layer in `frontend/lib/api.ts`; do not scatter raw fetch calls through UI components. React state, hooks, and the existing context are sufficient.
- Use the real API for all data. Keep search client-side over loaded updates. Show loading, empty, error, and offline states.
- Keep development servers bound to `127.0.0.1`. No authentication, deployment, PostgreSQL, or MSN ingestion in this milestone.
- Keep code direct: route functions, Pydantic schemas, SQLAlchemy models, and a pure scoring function. Do not introduce repositories, service frameworks, queues, or plugin abstractions.
- Keep database files, secrets, virtual environments, and generated build files out of Git. Never delete or reset personal data to fix a schema problem.
- Demo updates must be clearly marked as fictional. Seeding must preserve existing rows and user edits.
- Reserve `oshi kaishi`, `oshi shuuryou`, `oshi saikidou`, `oshi status`, `oshi hiraku`, and `oshi test`; their CLI implementation is a later task.

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
backend/.venv/bin/ruff check backend
backend/.venv/bin/ruff format --check backend
npm --prefix frontend run lint
npm --prefix frontend run typecheck
npm --prefix frontend run build
npm --prefix frontend run test:integration
```

Integration tests require installed Google Chrome and free ports 3000/8000. They launch the real backend against a disposable database, never `data/oshi.db`. Only run the checks relevant to the change. Report changed files, validation, architectural decisions, and blockers.
