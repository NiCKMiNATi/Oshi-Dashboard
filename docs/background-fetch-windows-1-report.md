OSHI_SYNC_V1
TYPE:RESULT
PHASE:background-fetch-windows-1

DONE
- Implemented Windows one-shot scheduled ingestion and command wrapper.
- Reused `app.ingestion` / `run_fetch`; no duplicate source, matching, or scoring logic.
- Preserved macOS lifecycle implementation unchanged and kept scheduling independent
  of FastAPI, Next.js, terminals, and VS Code.
- Implementation and locally available checks completed on macOS on 2026-10-01.
- Real Windows acceptance and task activation remain unverified, not claimed complete.

FILES_CHANGED
- `scripts/oshi.cmd`: Windows command wrapper using the project virtualenv.
- `scripts/oshi_windows.py`: scheduler configuration, ownership validation, JSON transport,
  status, manual fetch, and background on/off/status/run.
- `scripts/windows_scheduler.ps1`: native Task Scheduler COM operations; exact task name,
  inspected-definition check, current-user check, and create-only behavior on absence.
- `scripts/background_fetch.py`: one-shot bootstrap into the existing ingestion CLI.
- `backend/app/ingestion/__main__.py`: shared lock, background log mode, explicit paths,
  sanitized fatal errors and exit results.
- `backend/app/ingestion/runtime.py`: nonblocking OS lock and bounded UTC log rotation.
- `scripts/tests/test_windows_background.py`: scheduler/configuration/transport tests.
- `backend/tests/test_ingestion_runtime.py`: lock, crash, Windows lock API double,
  rotation, configuration/fatal/log-write failures, and bootstrap tests.
- `backend/tests/test_ingestion_cli.py`: scheduled-runner fixture-feed acceptance case.
- `docs/background-fetch-windows.md`: setup, operation, constraints, uninstall/moves,
  and explicit real Windows verification instructions.
- `docs/background-fetch-windows-1-report.md`: this report.
- `AGENTS.md`, `README.md`, `scripts/README.md`, `docs/ingestion.md`, `docs/local-cli.md`:
  updated scheduler/CLI guidance and links.

TASK_SCHEDULER
- Name: Oshi Dashboard Background Fetch, root Task Scheduler Library.
- Current user's SID; InteractiveToken; LeastPrivilege; no credentials or elevation request.
- Absolute Windows venv Python, absolute script/database/source paths, explicit working directory.
- StartWhenAvailable enabled, IgnoreNew, no wake request, 20-minute execution limit.
- Monitor off / session locked supported by configuration; remain signed in.
- No real task was installed, enabled, disabled, or run in this macOS session.

COMMANDS
- `.\scripts\oshi.cmd fetch [--dry-run] [--source KEY]`
- `.\scripts\oshi.cmd background on`
- `.\scripts\oshi.cmd background off`
- `.\scripts\oshi.cmd background status`
- `.\scripts\oshi.cmd background run`
- Add the repository's scripts directory to the current session PATH for `oshi ...`.
- `on` is idempotent for unchanged configuration; `off` disables future launches and
  allows an active fetch to finish. `run` requests the registered action asynchronously.
- Complete removal is documented through Task Scheduler after disabling and completion.

CADENCE
- First new-registration run approximately one minute later; then every 30 minutes,
  indefinitely. Repeated unchanged `on` preserves the initial trigger boundary.
- Missed launches may execute later via StartWhenAvailable, without replaying every interval.

CONCURRENCY
- Task Scheduler IgnoreNew plus `.runtime/ingestion.lock` shared by all ingestion CLI paths.
- Windows nonblocking byte-range locking; POSIX flock; kernel release after exit/crash.
- Lock file is never deleted. A busy invocation skips with exit 0, without fetching/log rotation.
- Project-local coordination only; different checkouts are not coordinated by this lock.

LOGGING
- `.runtime/background-fetch.log`, UTC start/end timestamps, duration, result,
  source/item/match/new/duplicate/ignored/failure counts and sanitized diagnostics.
- 1 MiB rotation with three retained backups; bootstrap errors use the same locked log.
- Unexpected exceptions log their class, not raw messages, tracebacks, or source URLs.
- Log-write errors fail the invocation without recursive logging or continuing ingestion.
- Missing interpreter/unwritable logs require inspecting Task Scheduler result/history.

TEST_RESULTS
- `./scripts/test-backend.sh scripts/tests`: 241 passed (all backend and CLI tests).
- `backend/.venv/bin/ruff check backend`: passed.
- `backend/.venv/bin/ruff format --check backend`: passed.
- Ruff check and format-check for `scripts/oshi.py`, `scripts/oshi_windows.py`,
  `scripts/background_fetch.py`, and `scripts/tests` with backend config: passed.
- `npm --prefix frontend run lint`: passed.
- `npm --prefix frontend run typecheck`: passed.
- Generated task XML validated against Microsoft's published Task Scheduler XSD:
  https://learn.microsoft.com/en-us/windows/win32/taskschd/task-scheduler-schema
- Fixture acceptance runs the real scheduled entry point from another directory with
  no servers, checks dry-run isolation, creates one fictional update, detects a duplicate,
  then reads it through the API and checks SQLite integrity/foreign keys.
- Scheduler tests use doubles; no ordinary test accesses Task Scheduler.
- Browser tests/build not rerun: no frontend implementation change. Generated typegen
  edits were restored. No dependency manifests/locks were changed.

MANUAL_VERIFICATION
- Pending on the real Windows checkout: manual production fetch; task registration and
  inspection; status; immediate run/logs/DB health; concurrent invocation exclusion;
  later automatic run with servers/terminals closed and session locked; disable; repeat
  disable; re-enable after all checks succeed.
- Exact commands and read-only DB health checks are in `background-fetch-windows.md`.

PERSONAL_DATA_SAFETY
- No production fetch, seeding, schema change, reset, or personal database write performed.
- All test ingestion uses disposable SQLite and local fixture feeds.
- Existing per-source transactions, deduplication, active-only matching, statuses/history,
  relevance scoring, public API contracts, and loopback server configuration are unchanged.
- Database/runtime/dependency artifacts remain ignored by Git.

LIMITATIONS
- Requires Windows, a native project virtualenv, configured feeds, and a signed-in user.
- Does not execute while powered off/asleep/signed out; does not request wake timers.
- Network failures do not suppress later runs; previously committed sources remain committed.
- One preferred task name per machine; conflicting tasks/checkouts/users are refused.
- Repository moves require removal of the old registration, venv recreation, and registration
  from the new location. Path overrides are captured when registering.
- A hard termination may leave a start line without an end line; consult scheduler status.
- No Windows server lifecycle commands, permanent worker, launchd, or cloud scheduler added.

BLOCKERS
- This execution environment is macOS, so real Windows Task Scheduler/COM execution and
  the user's locked-session/30-minute acceptance sequence cannot be verified here.
- Windows organizational policy may restrict task creation; no elevation workaround is applied.

NEXT
- Follow `docs/background-fetch-windows.md` on the Windows checkout and complete the
  explicit acceptance sequence. Leave the task enabled only after verification succeeds.

END
