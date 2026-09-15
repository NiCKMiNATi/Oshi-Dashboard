# Local CLI

`scripts/oshi.py` implements the six local macOS commands using only Python 3.12+ standard-library modules and the native `ps`, `lsof`, and `open` utilities. The application keeps its existing Python/npm dependencies. Installation and command examples are in the [README](../README.md#local-cli-for-macos).

## Command names

English and Japanese names run the same action, with the same command lock, process ownership checks, rollback, and test restoration. Existing Japanese commands remain supported. Run `oshi --help` to see all names.

| Action | English | Japanese alias |
| --- | --- | --- |
| Start services | `oshi start` | `oshi kaishi` |
| Stop services | `oshi end` or `oshi stop` | `oshi shuuryou` |
| Restart services | `oshi restart` | `oshi saikidou` |
| Inspect status | `oshi status` | — |
| Open dashboard | `oshi open` | `oshi hiraku` |
| Run checks | `oshi test` | — |

## Installation and paths

`./scripts/install-cli.sh` writes an executable shell wrapper to `~/.local/bin/oshi`, using the current Python executable and an absolute, shell-quoted path to `scripts/oshi.py`. It appends the discovered Node/npm directories to the wrapper's PATH as fallbacks. No sudo, third-party package, shell profile edit, login item, or launch daemon is installed.

The wrapper works from any working directory. `PYTHON_BIN=python3.12 ./scripts/install-cli.sh` selects an interpreter; `OSHI_BIN_DIR=/your/bin ./scripts/install-cli.sh` chooses another user-owned directory. Activating the backend virtual environment is unnecessary for `oshi` and does not change the interpreter recorded in an installed wrapper. The wrapper runs the repository's current `scripts/oshi.py`, so edits to that script take effect without reinstalling. The installer refuses an unrelated existing `oshi` file or symlink. Reinstalling replaces only a recognized Oshi wrapper. It prints the exact PATH instruction if its target directory is missing from the invoking PATH.

To uninstall, first run `oshi shuuryou`, then remove the installed wrapper. The default removal command is `rm "$HOME/.local/bin/oshi"`. Any PATH line you added may remain or be removed manually. Database and project files remain untouched; logs may be deleted after services stop. To reinstall, rerun the installer. Stop services before moving the repository; after moving it, rerun setup for the editable backend/venv and node dependencies, then rerun the CLI installer. If the recorded Python installation is removed, select a replacement with `PYTHON_BIN` when reinstalling.

## Ownership and lifetime

The runtime directory contains:

```text
.runtime/cli.lock
.runtime/backend.json
.runtime/frontend.json
.runtime/backend.log
.runtime/frontend.log
```

Each JSON state file records the project path, service, supervisor PID/process-group ID, unique launch token, process identities (PID, UID, birth time, group, command), and relevant explicitly exported database/API URL settings. It is atomically replaced with owner-only file permissions; the runtime directory is created with mode 0700. Environment secrets are not written to state. Logs append across restarts and do not rotate automatically.

`kaishi` first checks dependencies and port ownership. Already healthy owned services are reused, including when only one service needs starting. Unmanaged listeners on either port cause a clear error before any service is launched or stopped. An owned but unhealthy service is retained with a suggestion to inspect logs or restart. Next.js receives an explicit `--port 3000`, preventing fallback to a different port.

Each service launches through a small detached Python supervisor with its own session/process group, no terminal input, and output directed to its log. The backend uses the existing reloading `dev-backend.sh`; the frontend uses the existing npm `dev` command. The supervisor remains until its service children have exited and cleans surviving group members if the main service process fails. Closing the launching terminal does not stop the services. This is local development control, not an automatic crash-restart or login service.

Readiness has a 45-second startup budget and requires owned listening PIDs plus valid HTTP responses from `/api/stats` and the dashboard page. Probes use standard-library `http.client` connections to `127.0.0.1` with a two-second socket timeout and a 512,000-byte read limit. They bypass proxy settings without loading macOS proxy support and require a direct HTTP 200 response; redirects are not followed. Printed/browser URLs use `localhost`. Failure or Ctrl+C during startup rolls back only services newly launched by that command. Previously healthy services are preserved.

`shuuryou` sends SIGTERM to verified owned groups, waits up to ten seconds per group, and uses SIGKILL only for remaining owned processes. Identity is rechecked before escalation. It does not signal by process name or port. Stale/invalid state is reported and removed without signalling an unrelated PID. If a supervisor was externally killed but recorded children still have matching identities, their group can still be stopped safely. The process scanner excludes its own transient probes and ignores zombies.

Commands hold a nonblocking file lock. Another concurrent command receives a busy message instead of racing to launch or delete state. The lock file stays in place when idle; kernel locks release when the command exits, including crashes. During shutdown/rollback, additional Ctrl+C signals are ignored until cleanup completes. During normal startup or checks, cancellation exits 130 after cleanup.

## Status, opening, and database behavior

`status` reports owned running/ready, owned running/not-ready, stopped, or unmanaged listener states. HTTP readiness alone is not process ownership. It prints group/PID details and checks SQLite file existence; it does not run integrity checks or mutate records. Status returns zero for a successful inspection even when stopped. Failed start/open/test commands return nonzero.

`open` / `hiraku` verifies that the API and frontend respond, then calls macOS `open http://localhost:3000`. It also works with a manually launched, reachable dashboard. It never starts services; when unavailable it asks the user to run `oshi start` (`oshi kaishi`).

The database defaults to `data/oshi.db`. `OSHI_DATABASE_PATH` has the backend's existing semantics: expand `~`, resolve relative paths against the repository, and pass an absolute path to the detached API. Its active value is retained for status and test restoration. Startup creates missing tables and inserts missing local discovery metadata; it never seeds personal following or news/update fixtures. A later invocation after stop uses that terminal's environment again. `NEXT_PUBLIC_API_URL` remains supported through the environment or the frontend's existing `.env.local` behavior.

## Verification command

`oshi test` uses the existing scripts and configurations, in this order:

1. `scripts/test-backend.sh <absolute-project-path>/scripts/tests` — the original backend tests plus CLI safety tests, with `backend/pyproject.toml`.
2. `npm --prefix <frontend> run lint`.
3. `npm --prefix <frontend> run typecheck`.
4. `npm --prefix <frontend> run test:integration` — the existing Playwright configuration, Google Chrome, and disposable seeded SQLite backend.

Because Playwright requires free ports 3000/8000, the CLI records which owned services were running, stops them, and restores those services after success, failure, or Ctrl+C. The original database override is preserved during restoration. An unmanaged port conflict fails before stopping anything. Checks stop at the first failure and propagate a nonzero status. `npm run build` remains available separately; it is not added to the user's requested four-stage CLI test sequence.

Verification runners use their own sessions. The CLI tracks their descendants, including Playwright's detached web servers, allows interrupt handling first, then cleans verified leftovers if necessary. Browser fixtures remain isolated from personal SQLite data.

## Troubleshooting and limits

- **Command missing:** use `~/.local/bin/oshi` or add `export PATH="$HOME/.local/bin:$PATH"` to your current terminal and `~/.zshrc`.
- **Missing dependency:** run `./scripts/setup.sh`, then reinstall if Python/Node paths changed.
- **Command hangs before printing status, with Ctrl+C showing `urllib.request` / `_scproxy`:** older CLI code imported macOS proxy support before running any command. The current CLI uses direct localhost connections and avoids that import. Retry `oshi status` with the updated script; virtual environment activation is not required.
- **Port occupied:** run `oshi status`. Stop the reported unmanaged server using its original launcher. There is no force-adopt/kill-unrelated option.
- **HTTP timeout or early exit:** read `.runtime/backend.log` and `.runtime/frontend.log`; check dependency errors or invalid environment settings, then retry. Logs retain the failed start's output.
- **Busy command:** allow the active start/stop/test to finish. The existence of `cli.lock` is normal; do not delete it to bypass a held lock.
- **Stale PID state:** `oshi status` or `oshi shuuryou` cleans it after checking identities. Do not delete valid state while services run; without ownership evidence the CLI treats leftover listeners as unmanaged.
- **Abrupt external SIGKILL:** recorded surviving service children can be recovered, but forcibly killing the CLI itself during a tiny process-creation window or deleting/corrupting runtime state can remove ownership evidence. Use normal commands or Ctrl+C; the CLI will refuse unverified processes rather than guess.
- **Moved repository:** stop before moving, then rerun setup and installation. Automatic discovery of a moved project or already-running services from the old location is not implemented.
- **Browser suite:** install Google Chrome. `oshi test` handles its own services; standalone `npm run test:integration` still requires free ports.

See [the milestone report](local-cli-report.md) for actual command and process verification results.
