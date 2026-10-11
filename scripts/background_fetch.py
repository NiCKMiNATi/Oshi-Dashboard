"""One-shot scheduled entry point, invoked with the project's backend Python."""

import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    started = time.monotonic()
    sys.path.insert(0, str(ROOT / "backend"))
    from app.ingestion.runtime import FetchBusy, background_log, fetch_lock

    try:
        from app.ingestion.__main__ import main as fetch
    except Exception as error:
        # Report even broken/missing backend dependencies without echoing secrets.
        runtime = ROOT / ".runtime"
        try:
            with fetch_lock(runtime), background_log(runtime):
                print("Fetch started (bootstrap)")
                print(f"Fatal startup error ({type(error).__name__}); run scripts/setup.ps1.")
                print(
                    f"Fetch ended: result=1 duration={time.monotonic() - started:.1f}s (bootstrap)"
                )
        except FetchBusy:
            return 0
        except OSError as log_error:
            print(f"Cannot open fetch lock/log ({type(log_error).__name__}).", file=sys.stderr)
        return 1
    return fetch(["--background", *sys.argv[1:]])


if __name__ == "__main__":
    sys.exit(main())
