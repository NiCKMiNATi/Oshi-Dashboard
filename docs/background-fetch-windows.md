# Windows background fetch

Windows Task Scheduler launches a single ingestion process every **30 minutes**. The
task is **Oshi Dashboard Background Fetch** in the root Task Scheduler Library. It runs
the repository's `backend\.venv\Scripts\python.exe` and absolute
`scripts\background_fetch.py` path, which calls the existing `app.ingestion` entry point.
It never starts FastAPI or Next.js. Closing the dashboard, VS Code, and terminals does
not disable it. There is no permanently looping worker.

## Setup and commands

From your Windows checkout, in PowerShell:

```powershell
.\scripts\setup.ps1
# Configure your own enabled RSS/Atom feeds in local\sources.json first.
# This is a normal production fetch, independent of dashboard services:
.\scripts\oshi.cmd fetch
.\scripts\oshi.cmd background on
.\scripts\oshi.cmd background status
.\scripts\oshi.cmd background run
Get-Content .\.runtime\background-fetch.log -Tail 40
.\scripts\oshi.cmd background off
```

Do not seed/reset personal data as part of setup. See [ingestion](ingestion.md) for
source configuration and `fetch --dry-run` / `fetch --source KEY`.

For the shorter `oshi background on/off/status/run` commands, add the absolute
repository `scripts` directory to the current PowerShell session's PATH:

```powershell
$env:Path = (Join-Path (Get-Location) 'scripts') + ';' + $env:Path
oshi background status
```

Alternatively call the absolute `C:\your checkout\scripts\oshi.cmd` from any directory.
No shell profile is edited and no installer adds a permanent PATH entry. This Windows
wrapper implements only `fetch` and `background`; macOS lifecycle commands are unchanged.
Running `oshi_windows.py` on another platform fails clearly without invoking a scheduler.

- `on`: registers the task, or enables an existing owned task. Repeating it with the
  same paths preserves the trigger's start time. A new registration starts approximately
  one minute later, then repeats indefinitely at 30-minute intervals.
- `off`: disables future launches, including an already-disabled/missing task without
  error. An active fetch is allowed to finish its normal transactions. Disabling does
  not erase the task's last-run information or touch any other task.
- `status`: shows installed/enabled state, actual trigger interval, state, last run,
  numeric last result, next run, repository, database, and source configuration paths.
  Times are UTC. Missing run times appear as unavailable.
- `run`: requests an immediate **Task Scheduler** launch of the registered action;
  requires an installed, enabled task. It returns after requesting the run, not after
  ingestion finishes. Inspect status/logs afterward. It does not reset the cadence.

No administrator elevation or password is requested. The task uses the current user's
SID, `InteractiveToken`, and `LeastPrivilege`. **Remain signed in:** a locked session or
monitor-off state works; signing out prevents execution. Organizational Windows policy
may prevent task registration; the command reports failure instead of elevating itself.
Only one checkout/user may own the preferred task name on a machine. An unrecognized
task, another user's task, or another checkout's task is refused rather than overwritten.

## Paths and environment

`on` resolves `OSHI_DATABASE_PATH` and `OSHI_SOURCES_PATH` from the invoking environment,
or defaults to `data\oshi.db` and `local\sources.json`. Relative paths resolve against
the checkout. These **absolute paths** are stored in the task definition and supplied
as explicit ingestion arguments. Scheduled runs do not depend on your terminal's
environment, working directory, virtualenv activation, or `.env` loading. Feed URLs
and credentials are not put in task arguments; the source configuration path is.

`status` reports the registered paths even if the invoking terminal has different
environment overrides. To change paths, export the desired overrides and run `on`
again; this updates the action and starts a new cadence. Edit the contents of the same
source configuration file without re-registering. Do not move files while a fetch runs.

## Availability, concurrency, and failure

`StartWhenAvailable` lets a missed scheduled run execute later when Windows permits;
this is not a replay of every missed interval. The task does not wake a sleeping PC.
While asleep/off it cannot run; keep Windows awake while plugged in as intended.
Offline/source failures return nonzero and are logged; the next scheduled run is still
eligible. No network-availability condition postpones failure reporting indefinitely.
The task may run on battery and does not stop just because AC is disconnected.

Task Scheduler uses `IgnoreNew`. The portable ingestion CLI also takes a nonblocking
project-local lock at `.runtime/ingestion.lock` before reading sources or fetching.
This covers macOS/Windows manual CLI calls, direct `python -m app.ingestion`, and
scheduled runs in this checkout. A busy invocation prints a skip message and exits 0
without opening/rotating the active writer's log. The kernel releases locks on exit or
crash (`msvcrt` on Windows, `flock` on POSIX). The persistent file is not stale state;
**never delete it to bypass a held lock**. Locks do not coordinate different checkouts.
The internal `run_fetch` function remains scheduling-independent; callers bypassing the
CLI retain the existing SQLite transaction/deduplication safeguards.

A 20-minute Task Scheduler execution limit prevents a hung process from occupying the
task indefinitely. Termination may omit the end log line; Task Scheduler's result is
then authoritative. SQLite rolls back an incomplete transaction; earlier completed
sources remain committed. Normal per-source rollback, deduplication, matching, scoring,
and dry-run isolation are unchanged. No retries or queues are added.

## Logs and result codes

`.runtime/background-fetch.log` records UTC start/end timestamps, duration, result,
Sources checked, Items received, Matched, New updates, Duplicates, Ignored, Failed
sources, and existing sanitized diagnostics. With no enabled sources it records zeros
and exits successfully without creating a database. On fatal configuration/startup
failure counts may be unavailable; failure is recorded instead. Exceptions are identified
by class, never raw exception text or tracebacks containing URLs/credentials.

The main log rotates at 1 MiB, retaining three backups (`.1` through `.3`), about 4 MiB
total. Backend import failures also use the same locked, rotating log. If the interpreter is missing or the log directory is unwritable,
consult Task Scheduler's result/history. `.runtime/` is ignored by Git.

Normal ingestion results: 0 = success/no sources/concurrent skip, 1 = one or more source
failures or fatal failure, 130 = cancelled. Scheduler-specific results can differ;
267009 (`0x41301`) means running and 267011 (`0x41303`) means not yet run. Check state
and timestamps as well as the last numeric result.

## Uninstall and repository moves

To stop scheduling, `oshi background off` is sufficient and idempotent. To remove the
registration entirely, run `off`, wait until any current run finishes, open **Task
Scheduler → Task Scheduler Library**, inspect the exact task's action/user/repository,
then delete only **Oshi Dashboard Background Fetch**. Files and personal data remain.

Before moving the repository: disable the task, wait for it to finish, and delete its
registration as above. Move the checkout, recreate its Windows virtualenv using setup
(venvs are not portable between paths/platforms), update your session PATH if used,
then run `background on` from the new checkout. The old task cannot follow a move.
If you already moved it, inspect and delete the old-path registration in Task Scheduler
before registering the new one. The new checkout deliberately refuses to take it over.

## Explicit Windows acceptance verification

Ordinary unit tests mock the scheduler and use disposable databases. They never register,
enable, disable, or run a real scheduled task. The following is a deliberate manual
production check on the Windows checkout; normal fetches may add legitimate updates.

1. Confirm `oshi fetch` works with your configured feeds; leave both dashboard servers stopped.
2. Run `oshi background on`; inspect the named task in Task Scheduler. Confirm the
   absolute venv executable, action arguments, working directory, current user, 30-minute
   repetition, missed-start behavior, and IgnoreNew setting.
3. Run `oshi background status`, then `oshi background run`. Poll status until Ready
   and inspect the log for a new completed run and counts. Result 0 is successful.
4. Verify the registered personal DB read-only (substitute its absolute path):

   ```powershell
   .\backend\.venv\Scripts\python.exe -c "import sqlite3,sys; from pathlib import Path; c=sqlite3.connect(Path(sys.argv[1]).resolve().as_uri()+'?mode=ro', uri=True); print(c.execute('PRAGMA integrity_check').fetchall()); print(c.execute('PRAGMA foreign_key_check').fetchall()); c.close()" 'C:\your checkout\data\oshi.db'
   ```

   Expect `ok` and no foreign-key violations. If the DB does not exist because no
   sources were enabled, configure sources and repeat step 1; do not create demo data.
5. To deterministically test manual/scheduled exclusion, hold the lock for 20 seconds
   in another terminal (this command does no DB work):

   ```powershell
   .\backend\.venv\Scripts\python.exe -c "import time; from app.config import ROOT_DIR; from app.ingestion.runtime import fetch_lock; lock=fetch_lock(ROOT_DIR/'.runtime'); lock.__enter__(); print('Lock held', flush=True); time.sleep(20); lock.__exit__(None,None,None)"
   ```

   While held, `oshi fetch` must print the busy/skip message; `background run` must
   finish without a second ingestion/log block. After release a fresh run must work.
   Repeat `background run` during a real running task and confirm IgnoreNew prevents
   a second task instance. Do not delete the lock file.
6. Close VS Code and terminals, keep servers stopped, lock Windows, and wait through
   the next 30-minute trigger. Unlock and verify a later log start/end and last-run time.
7. Run `background off`, verify Disabled and no later launches; run `off` again and
   confirm success. After all verification succeeds, run `background on` to leave it enabled.

These real Windows checks cannot be substituted by the macOS test results.

Microsoft references: [task logon types](https://learn.microsoft.com/en-us/windows/win32/taskschd/principal-logontype),
[repetition](https://learn.microsoft.com/en-us/windows/win32/taskschd/taskschedulerschema-repetition-triggerbasetype-element),
and [multiple-instance policy](https://learn.microsoft.com/en-us/windows/win32/taskschd/taskschedulerschema-multipleinstancespolicy-settingstype-element).
