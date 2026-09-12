# Development scripts

Run these from the repository root. Paths are quoted and scripts also work when invoked from another directory.

- `./scripts/setup.sh`: create the backend venv and install locked Python/npm dependencies. Requires Python 3.12+ and Node 20.9+. Set `PYTHON_BIN=python3.12` to select an interpreter.
- `./scripts/seed.sh`: create the schema and add missing fictional fixtures. Accepts `--database-path /path/to/demo.db`.
- `./scripts/dev-backend.sh`: foreground API server with reload at `http://127.0.0.1:8000`; stop with Ctrl-C.
- `./scripts/test-backend.sh`: isolated backend tests; extra pytest arguments are forwarded.
- Frontend: `npm --prefix frontend run dev`; stop with Ctrl-C.
- `npm --prefix frontend run test:integration`: Playwright browser checks with Google Chrome. Requires free ports 3000/8000. It launches both servers and uses `integration-backend.py` to create a disposable seeded SQLite database.

The future commands `oshi kaishi`, `oshi shuuryou`, `oshi saikidou`, `oshi status`, `oshi hiraku`, and `oshi test` are reserved only. No background process manager, global CLI, or deployment command is installed.
