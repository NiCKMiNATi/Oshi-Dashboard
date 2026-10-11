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

### Windows (PowerShell)

Run these commands from the repository root with Python 3.12+ and Node.js 20.9+ installed:

```powershell
.\scripts\setup.ps1
.\backend\.venv\Scripts\python.exe -m uvicorn app.main:create_app --factory --host 127.0.0.1 --port 8000 --reload --reload-dir backend
```

In another terminal:

```powershell
npm.cmd --prefix frontend run dev
```

Open `http://127.0.0.1:3000`. Stop each server with Ctrl-C. The setup script installs
native Windows dependencies and preserves a copied macOS virtual environment under
ignored `.runtime/backups/`. Use `-PythonBin C:\path\to\python.exe` to select Python.
Virtual environments and `node_modules` are machine-specific; install them on each
computer instead of copying them. Setup does not seed or open your personal database.

Optional fictional demo data and manual feed fetching use the backend directly:

```powershell
.\backend\.venv\Scripts\python.exe -m app.seed
.\backend\.venv\Scripts\python.exe -m app.ingestion --dry-run
```

Configure feeds as described below before fetching. The detached `oshi` service CLI
uses macOS process ownership tools; Windows uses the foreground commands above.

To verify the Windows checkout, stop the foreground servers and run:

```powershell
.\backend\.venv\Scripts\python.exe -m pytest -c backend/pyproject.toml backend/tests scripts/tests
.\backend\.venv\Scripts\ruff.exe check backend
.\backend\.venv\Scripts\ruff.exe format --check backend
npm.cmd --prefix frontend run lint
npm.cmd --prefix frontend run typecheck
npm.cmd --prefix frontend run build
npm.cmd --prefix frontend run test:integration
```

Tests use temporary databases. macOS CLI tests are skipped on Windows; the direct
ingestion command and browser suite run on both platforms. Browser tests require
Google Chrome and free ports 3000/8000.

## Local CLI for macOS

After setup, install the user-owned command once:

```sh
./scripts/install-cli.sh
```

The installer creates `~/.local/bin/oshi` without sudo. If that directory is missing from PATH, it prints this exact zsh line. Add it to `~/.zshrc` yourself for future terminals and run it in the current terminal:

```sh
export PATH="$HOME/.local/bin:$PATH"
```

The installer does not edit shell startup files. All commands work from any directory, including paths with spaces. Existing English and Japanese command names are interchangeable:

| Command | Behavior |
| --- | --- |
| `oshi start` / `oshi kaishi` | Start both services detached, wait for HTTP readiness, and print URLs. Already healthy CLI-owned services are reused. |
| `oshi end` / `oshi stop` / `oshi shuuryou` | Gracefully stop CLI-owned process groups. Already stopped is a clean no-op. |
| `oshi restart` / `oshi saikidou` | Stop, start, and verify both services. |
| `oshi status` | Show actual process/HTTP status, ownership, PIDs, URLs, and SQLite existence; clean stale state. |
| `oshi open` / `oshi hiraku` | Open `http://localhost:3000` with macOS `open` when ready. Otherwise explain how to start. |
| `oshi test` | Run backend and CLI tests, frontend lint/typecheck, and the existing browser suite. Temporarily stop CLI-owned services, then restore their previous running state. |
| `oshi fetch [--dry-run] [--source KEY]` | Manually ingest configured RSS/Atom feeds for active followed oshi. Works with both services stopped. |

The API uses port **8000** and the frontend **3000**, both bound to `127.0.0.1`. Closing the launching terminal leaves CLI-started services running. Services started by the foreground scripts or another tool are reported as unmanaged; the CLI will not adopt or stop them. Stop those from their original terminal before using `kaishi`, `saikidou`, or `test`.

Logs append to `.runtime/backend.log` and `.runtime/frontend.log` in this repository. `.runtime/` is ignored by Git. Startup creates missing tables and the small discovery catalog; it never seeds tracked oshi or updates. Use `./scripts/seed.sh` explicitly if you want fictional demo updates and following.

To uninstall, run `oshi shuuryou`, then `rm "$HOME/.local/bin/oshi"`. Your source, database, and logs remain. Reinstall by rerunning `./scripts/install-cli.sh`. If the repository moves, stop first, move it, rerun `./scripts/setup.sh` to repair path-dependent dependencies, then rerun `./scripts/install-cli.sh` to update the wrapper's absolute project path.

Troubleshooting: for `command not found`, apply the PATH line above (or use `~/.local/bin/oshi`). For startup failures, read the two logs and run `oshi status`; occupied ports require stopping their original launcher. Missing dependencies require `./scripts/setup.sh`. Browser checks require installed Google Chrome. Do not delete runtime state while services are alive. Detailed lifecycle behavior and recovery are in [the CLI guide](docs/local-cli.md).

## Manual RSS/Atom fetching

`oshi fetch` imports matching feed entries into the existing dashboard without requiring
FastAPI or Next.js to be running. Run `./scripts/setup.sh` after this update to install
the feed parsing dependency. Configure your own feeds in ignored `local/sources.json`:

```sh
mkdir -p local
cp config/sources.example.json local/sources.json
# Edit the file: replace the example URL and enable your source.
oshi fetch --dry-run
oshi fetch
```

Use `oshi fetch --source KEY` to select one source. `OSHI_SOURCES_PATH` overrides the
configuration path, and `OSHI_DATABASE_PATH` selects the database. Missing configuration
prints a clear message. No real sources are enabled by default.

Only active followed oshi receive new updates. Matching uses names, enabled keywords,
and linked catalog aliases. Repeated fetches deduplicate imported items and preserve
existing update content and status. Dry-run uses a temporary database copy and leaves
personal schema, content, and source state unchanged. Refresh or start the dashboard to
see imported updates. Optional [Windows background fetching](docs/background-fetch-windows.md) runs the same pipeline every 30 minutes, independently of dashboard servers.
Configuration, adapter contracts, matching, dedupe, and limitations are in
[the ingestion guide](docs/ingestion.md).

## What is included

- SQLAlchemy models for `Oshi`, `Keyword`, `Update`, and `UpdateOshi`, backed by `data/oshi.db`.
- Oshi create/list/edit/delete, nested keyword editing, update create/list/detail/edit/status, and aggregate stats.
- Combined `oshi`, `category`, `status`, and `min_score` filters, with update pagination.
- Automatic deterministic scoring with the requested weights and a 0–100 clamp.
- Repeatable, opt-in demo seeding for 進撃の巨人, 原神, and Ryujin, with ten fictional updates covering all categories and statuses.
- Isolated backend unit/API tests and locked Python/npm dependencies.
- A persistent desktop sidebar, category/oshi/status/score filters, client-side search, update cards, and an accessible detail drawer.
- Persistent status actions and oshi create/edit/pause/delete forms, feed stats, and documented scoring rules.
- Local discovery by canonical name or alias, one-click tracking, and manual creation for anything outside the catalog.
- Manual RSS/Atom ingestion with source state, provenance, deterministic active-oshi matching, dedupe, and an `oshi fetch` command that runs without dashboard services.
- Loading, empty, request-error, and backend-offline states with retry; no substitute network data.

Demo records use `[DEMO]` titles, explicit fictional notices, and `example.invalid` URLs. They are realistic fixtures, not verified announcements. Their detail drawer shows a disabled **Demo source** button so fictional URLs never open. Real updates keep their external source links. The Ryujin fixture assumes ITZY's Ryujin. Seeding again adds missing fixtures while preserving existing records and user edits; it does not refresh dates. Startup never seeds personal following or updates.

**+ Add oshi** opens discovery. Try Higedan, ITZY, JJK, 進撃, AOT, Gojo, Genshin, Hyouka, or 内田雄馬. The local catalog contains eight canonical entries and their aliases; it does not contact external providers. **Add** tracks the canonical result; **Tracking** indicates it already exists in My Oshi, including paused items. Removing an oshi leaves its catalog entry discoverable, so you can add it again later. Old update links are not restored automatically. **+ Add manually** accepts any name, type, and optional aliases/keywords, even when discovery has no match. Priority and keyword weights remain under **More options**.

To stop following an oshi, open **Oshi Management → Remove** on its row and confirm. The sidebar, selected filter, and stats update automatically. Existing update history remains. Feed cards show the essentials; open a card for source information, full dates, and keyword context.

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
- [Development script usage](scripts/README.md)
- [Local CLI lifecycle and troubleshooting](docs/local-cli.md)
- [Local CLI verification report](docs/local-cli-report.md)
- [UI refinement and verification](docs/ui-refinement-1-report.md)
- [Dashboard simplification, removal, and source-link verification](docs/usability-refinement-2-report.md)
- [Local discovery and tracking verification](docs/discover-oshi-1-report.md)
- [Manual ingestion architecture and configuration](docs/ingestion.md)
- [Ingestion foundation verification](docs/ingestion-foundation-1-report.md)

The UI follows the accessible [Figma dashboard](https://www.figma.com/design/dS4aiNmBAUBURfRpKK6dgk?node-id=2-2) and [management frame](https://www.figma.com/design/dS4aiNmBAUBURfRpKK6dgk?node-id=2-116), with the supplied dark tokens. The connector exposes these under “v0.1 Wireframes”; a separate “v0.1 Prototype” page was not available during implementation.

MSN ingestion, authentication, deployment, and PostgreSQL remain outside this milestone.

## Windows background ingestion

After Windows setup and source configuration, use `.\scripts\oshi.cmd background on`,
`background status`, `background run`, and `background off`. The user-level task runs every
30 minutes while signed in (including a locked session), with servers and terminals closed.
See [setup, logs, uninstall, and Windows verification](docs/background-fetch-windows.md).
