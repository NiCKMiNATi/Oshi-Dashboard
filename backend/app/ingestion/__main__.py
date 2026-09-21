"""Portable entry point: python -m app.ingestion [--dry-run] [--source KEY]."""

import argparse
import sys
import time

from sqlalchemy.exc import SQLAlchemyError

from app.config import resolve_database_path
from app.ingestion.config import ConfigError, config_path, load_sources
from app.ingestion.pipeline import run_fetch
from app.ingestion.rss import RSSAdapter


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Fetch configured sources without dashboard servers"
    )
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--source", metavar="KEY")
    args = parser.parse_args(argv)
    if args.source is not None and not args.source.strip():
        parser.error("--source requires a nonempty source key")
    started = time.monotonic()
    print("OSHI Fetch" + (" (dry run — no database changes)" if args.dry_run else ""), flush=True)
    try:
        path = config_path()
        sources = load_sources(path, args.source)
        if not sources:
            print(
                f"\nNo enabled sources configured. Create {path} using config/sources.example.json."
            )
            return 0
        report = run_fetch(
            resolve_database_path(),
            [RSSAdapter(source) for source in sources],
            dry_run=args.dry_run,
        )
    except ConfigError as error:
        print(f"\n{error}", file=sys.stderr)
        return 1
    except (OSError, SQLAlchemyError) as error:
        print(
            f"\nFetch could not access the database/configuration ({type(error).__name__}).",
            file=sys.stderr,
        )
        return 1
    print()
    for label, field in (
        ("Sources checked", "sources_checked"),
        ("Items received", "items_received"),
        ("Matched", "matched"),
        ("New updates", "new_updates"),
        ("Duplicates", "duplicates"),
        ("Ignored", "ignored"),
        ("Failed sources", "failed_sources"),
    ):
        print(f"{label:18}{getattr(report, field)}")
    for message in dict.fromkeys(report.messages):
        print(message, file=sys.stderr)
    print(f"\nFetch completed in {time.monotonic() - started:.1f}s")
    return 1 if report.failed_sources else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\nFetch cancelled; the active transaction was rolled back.", file=sys.stderr)
        sys.exit(130)
