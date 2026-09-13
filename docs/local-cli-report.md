OSHI_SYNC_V1
TYPE:RESULT
DIR:X2C
PROJECT:Oshi Dashboard
VERSION:0.1
PHASE:local-cli
DATE:2026-09-12

## DONE

Implemented and installed all six local macOS commands. Created checkpoint commit `8df06a0` before modifying the previously uncommitted backend/frontend project. The CLI milestone does not change backend/frontend application code or API contracts. The subsequent UI refinement request is a separate milestone.

## IMPLEMENTATION

Python standard-library CLI with a shell installer/wrapper. Each service has a detached supervisor and owned process group. State is atomically written to `.runtime/`, commands serialize using `flock`, readiness checks combine HTTP with actual listening-process ownership, and shutdown validates identity before SIGTERM or escalation. Startup failures and Ctrl+C roll back new services. Test runs preserve and restore the prior running services and database override.

## FILES_CHANGED

Added `scripts/oshi.py`, `scripts/install-cli.sh`, `scripts/tests/test_cli.py`, `docs/local-cli.md`, and this report. Updated `.gitignore`, `AGENTS.md`, `README.md`, `scripts/README.md`, and `docs/architecture.md`. Installed the external user-owned wrapper at `~/.local/bin/oshi`. Shell startup files were not modified.

## INSTALLATION

`./scripts/install-cli.sh` succeeded. The wrapper targets `/Users/nikhil/Desktop/Oshi Dashboard` and a discovered Python executable, with quoted paths. The current shell PATH did not include `~/.local/bin`; the installer printed:

```sh
export PATH="$HOME/.local/bin:$PATH"
```

The user should add this line to `~/.zshrc` for future Terminal sessions and run it in the current terminal, or use `~/.local/bin/oshi` directly. Verification applied the PATH setting only to its own shell. No sudo was used. Reinstallation updates a recognized wrapper; uninstall and repository-move instructions are in the README.

## COMMAND_VERIFICATION

All command checks ran outside the repository, from `/tmp`:

| Check | Observed result |
| --- | --- |
| `oshi status` while stopped | Both stopped; correct ports/URLs and existing SQLite file |
| `oshi hiraku` while stopped | Exit 1 with `oshi kaishi` instruction; did not start services |
| `oshi kaishi` | API and frontend reached HTTP readiness; printed success and Japanese closing line |
| Repeated `oshi kaishi` | Original process-group IDs retained; no duplicate launch |
| `oshi status` while running | Both owned/ready with group IDs and PIDs |
| `oshi hiraku` while running | macOS `open` succeeded |
| Close launching shell | Launch used a PTY; after shell exit, supervisors had PPID 1 and both HTTP services remained reachable from a new shell |
| `oshi shuuryou` | Groups exited and both listening ports closed |
| Repeated `oshi shuuryou` | Exit 0, clean stopped state, no extra signals |
| `oshi saikidou` | Both services started again and passed readiness |
| `oshi test` while running | Temporarily stopped owned services, passed all checks, then restored both to new groups and HTTP readiness |

## PROCESS_VERIFICATION

Verified detached sessions, complete child-group shutdown, terminal independence, repeated start/stop, orphan recovery after externally killing a test supervisor, and SIGKILL escalation only for a deliberately stubborn owned test process. A transient process-monitor probe initially prevented clean shutdown; it was excluded and subsequent real shutdowns and the regression tests passed.

Real Ctrl+C/SIGINT during application startup returned 130 and removed both newly launched groups. A separate interrupted `oshi test` returned 130, cleaned its runner, and restored both application services. At the CLI handoff the services were running for the following UI refinement; their final review state is recorded in that milestone's report.

## TEST_RESULTS

`oshi test`, invoked from `/tmp`, passed:

- **105 pytest tests:** 88 original backend tests plus 17 new CLI safety/lifecycle tests, using the existing backend pytest configuration (11.30s).
- Frontend lint: passed.
- Frontend typecheck: passed.
- Existing Playwright integration suite: **6 passed** (27.2s).

Ruff lint/format checks for the CLI and tests, installer shell syntax, and `git diff --check` passed. Coverage was not remeasured; the previous backend coverage baseline remains 98%. The requested CLI test sequence does not add a production build stage.

## EDGE_CASES

- Real unrelated HTTP listener on port 8000: start refused; status identified it as unmanaged; stop preserved the listener.
- Intentional frontend startup failure: newly started API/group rolled back, both ports freed, failure logs retained.
- Missing custom SQLite file in a path with spaces: backend created an empty schema with zero oshi/updates; no automatic seeding.
- Read-only SQL dump comparison: personal `data/oshi.db` unchanged after all CLI verification.
- Invalid/stale PID state, reused process IDs, mismatched supervisor markers, lock contention, partial-start rollback, failed verification restoration, and wrapper paths containing spaces/apostrophes/shell metacharacters are covered by CLI tests.
- A real detached grandchild leaked by a test runner was detected and cleaned up.

## BLOCKERS

No implementation blockers. The user must apply the printed PATH line for the shorthand `oshi` to resolve in future shells, since editing startup files was explicitly excluded. Native macOS process utilities and installed Google Chrome are required for the documented platform/browser suite. Deleting ownership state or moving a running repository requires manual recovery; the CLI will not guess ownership.

## NEXT

Apply the PATH line, then use `oshi status`, `oshi kaishi`, and `oshi hiraku` from any Terminal directory. Full lifecycle and troubleshooting details are in [local-cli.md](local-cli.md). Continue with the separately requested UI refinement while preserving these CLI controls.
