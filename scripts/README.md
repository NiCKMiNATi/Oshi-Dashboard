# Development scripts

Run these from the repository root. Paths are quoted and scripts also work when invoked from another directory.

- Windows: `.\scripts\setup.ps1` installs native dependencies. See the [Windows quick start](../README.md#windows-powershell) for foreground servers, optional seeding/fetching, and checks. The detached `oshi` CLI remains macOS-only.
- `./scripts/setup.sh`: create the backend venv and install locked Python/npm dependencies. Requires Python 3.12+ and Node 20.9+. Set `PYTHON_BIN=python3.12` to select an interpreter.
- `./scripts/seed.sh`: create the schema and add missing fictional fixtures. Accepts `--database-path /path/to/demo.db`.
- `./scripts/dev-backend.sh`: foreground API server with reload at `http://127.0.0.1:8000`; stop with Ctrl-C.
- `./scripts/test-backend.sh`: isolated backend tests; extra pytest arguments are forwarded.
- `./scripts/test-backend.sh scripts/tests`: backend plus CLI lifecycle/safety tests using the existing pytest configuration.
- `./scripts/install-cli.sh`: install or update the `oshi` wrapper in `~/.local/bin`; prints a PATH instruction if needed. `PYTHON_BIN` selects Python 3.12+; optional `OSHI_BIN_DIR` selects another user-owned installation directory.
- `oshi fetch [--dry-run] [--source KEY]`: manual RSS/Atom ingestion using backend dependencies only, even with both dashboard services stopped. Configure ignored `local/sources.json`; see [ingestion](../docs/ingestion.md).
- Frontend: `npm --prefix frontend run dev`; stop with Ctrl-C.
- `npm --prefix frontend run test:integration`: Playwright browser checks with Google Chrome. Requires free ports 3000/8000. It launches both servers and uses `integration-backend.py` to create a disposable seeded SQLite database.

`oshi start` (`kaishi`), `oshi end` / `oshi stop` (`shuuryou`), `oshi restart` (`saikidou`), `oshi status`, `oshi open` (`hiraku`), and `oshi test` are implemented by the dependency-free `oshi.py`. English and Japanese names are interchangeable; `oshi --help` lists every name. They resolve paths from the installed wrapper and script, independently of the invoking directory. Detached services use the same foreground launch scripts/npm command, with process groups, logs, and ownership state under `.runtime/`.

`oshi test` temporarily stops only CLI-owned services to free the ports required by the existing Playwright configuration, runs backend/CLI tests and frontend lint/typecheck/integration checks, and restores the services that were running. It refuses unrelated listeners. See [the CLI guide](../docs/local-cli.md) for install/uninstall, recovery, and signal behavior. No login service or deployment command is installed.
