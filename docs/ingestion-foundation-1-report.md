OSHI_SYNC_V1
TYPE:RESULT
PHASE:ingestion-foundation-1
DATE:2026-09-19

## DONE

Implemented manual source-agnostic ingestion and `oshi fetch`, including `--dry-run` and
`--source KEY`. Fetch runs directly through backend dependencies with FastAPI and Next.js
stopped. RSS/Atom entries matching active followed oshi become ordinary scored Updates.
Repeated fetches deduplicate imports and preserve existing update edits/status/associations.
No scheduler or scraping was added. Work is local and uncommitted on `main`.

## FILES_CHANGED

New files:

- `backend/app/ingestion/__init__.py`: package with no import-time I/O.
- `backend/app/ingestion/contracts.py`: FetchedItem, FetchState, FetchResult, SourceAdapter,
  SourceError, and deterministic FixtureAdapter.
- `backend/app/ingestion/config.py`: validated local JSON configuration.
- `backend/app/ingestion/rss.py`: bounded HTTP transport and RSS/Atom parsing.
- `backend/app/ingestion/matching.py`: active tracked identity matching.
- `backend/app/ingestion/pipeline.py`: transactions, provenance/dedupe, score creation, dry-run copy.
- `backend/app/ingestion/__main__.py`: portable command entry point and concise result output.
- `backend/tests/test_ingestion.py`, `test_ingestion_rss.py`, `test_ingestion_cli.py`:
  pipeline, parser/HTTP, and actual CLI acceptance tests.
- `config/sources.example.json`: disabled fictional example, no personal URLs.
- `docs/ingestion.md`: architecture, configuration, contracts, behavior, and limitations.
- `docs/ingestion-foundation-1-report.md`: this report.

Modified files:

- `backend/app/models.py`: two additive tables only.
- `backend/pyproject.toml`, `backend/requirements-dev.lock`: feedparser 6.0.14 and its
  feedparser-sgmllib 2.1.0 dependency; existing locked versions retained.
- `backend/.env.example`: source configuration override.
- `backend/tests/conftest.py`: disposable local HTTP feed server fixture.
- `backend/tests/test_discover.py`: additive-schema assertion includes the two new tables.
- `scripts/oshi.py`, `scripts/tests/test_cli.py`: fetch dispatch, flags, child cleanup,
  and tests without changing existing service lifecycle implementations.
- `.gitignore`: exclude `local/` source configuration.
- `AGENTS.md`, `README.md`, `scripts/README.md`, `docs/architecture.md`,
  `docs/local-cli.md`, `docs/frontend-integration.md`: current scope and usage.

No frontend implementation, public API route/schema, scoring function, or original
table definition was changed.

## INGESTION_ARCHITECTURE

Adapters return data only. HTTP fetching occurs outside the transaction. The pipeline
reserves SQLite's writer before matching/dedupe reads, then commits each source's new
Updates, associations, existing relevance calculation, provenance, and success state
together. A failed source rolls back its batch, records failure separately, and permits
other sources to continue. Invalid individual items are counted as ignored. Core modules
contain no platform-specific process or scheduler code.

## NEW_TABLES

- `source_states`: unique source key; attempt/success timestamps; consecutive failure
  count; HTTP validators; request fingerprint that invalidates validators when source
  settings or active matching identities change.
- `ingested_records`: source/external identity; canonical URL; content hash; nullable
  Update foreign key; first/last-seen timestamps. Unique `(source_key, external_key)`;
  indexed fallback lookup fields; deleting an Update sets its provenance link to null.

The seven prior tables remain unchanged. Normal startup/fetch creates missing tables
additively. Dry-run never applies these schema additions to the original database.

## ADAPTERS

FixtureAdapter provides deterministic local test data. RSSAdapter uses
[feedparser](https://feedparser.readthedocs.io/en/latest/) 6.0.14 for RSS/Atom compatibility
and standard-library HTTP with timeouts, a clear User-Agent, response/redirect limits,
conditional ETag/Last-Modified requests, and no immediate retries. Malformed feeds and
network/HTTP failures are reported by source key. Future adapters implement the same
small contract and are explicitly wired through configuration; no plugin framework exists.

## MATCHING

Matches current names, positive-weight keywords, and explicitly linked catalog canonical
names/aliases for ACTIVE oshi. Uses NFKC, case folding, collapsed whitespace, and deterministic
text matching over title/summary. ASCII terms require three alphanumeric characters and
word boundaries; non-ASCII terms require two; numeric-only terms are excluded. Multiple
oshi may match an item. Unmatched items receive provenance without an Update and can be
reconsidered later. Existing scoring remains authoritative. Category defaults to NEWS
unless a compatible reliable hint is supplied. No action dates or location are invented.

## DEDUPE

Checks existing external identity first, then canonical URL across ingestion sources,
then same-source normalized title/summary hash when no external ID exists. Canonicalization
removes fragments/common tracking parameters while retaining meaningful URL differences.
Duplicate fetches advance provenance last_seen and may add another provenance mapping,
but never rewrite historical Updates. Original provenance fingerprints remain stable.
Manual/demo Updates are not retroactively merged. Concurrent-fetch dedupe is tested.

## CLI_FETCH

`oshi fetch`, `oshi fetch --dry-run`, and `oshi fetch --source KEY` are implemented.
The wrapper delegates to `backend/.venv/bin/python -m app.ingestion` under its existing
command lock. It requires neither Node nor dashboard service readiness and never starts
or stops services. Existing aliases remain intact. Cancellation waits for its own child
and escalates cleanup only on that child if necessary.

Results include Sources checked, Items received, Matched, New updates, Duplicates, Ignored,
Failed sources, and duration. Any failed source produces nonzero exit status. Missing
configuration/no enabled sources produces a clear successful no-op. Dry-run runs the real
pipeline against a disposable SQLite backup, leaving personal schema/content/state unchanged.

## SOURCE_CONFIG

Copy `config/sources.example.json` to ignored `local/sources.json`, replace the fictional
URL, and enable your source. Optional `name` and `category_hint` are supported.
`OSHI_SOURCES_PATH` overrides the config; `OSHI_DATABASE_PATH` overrides the database.
Relative paths resolve against the repository. No personal sources or live URLs were
configured or fetched during implementation.

## TEST_RESULTS

- `oshi test`: passed and restored previously running CLI services.
- Backend + CLI suite: **213 passed** (178 backend, 35 CLI), including all existing tests.
- Frontend lint: passed.
- Frontend typecheck: passed.
- Existing real-API Playwright suite: **17 passed** in approximately 1.2 minutes.
- Ruff check/format for backend and CLI/tests: passed.
- Python dependency consistency (`pip check`): passed.
- `git diff --check`: passed.

The actual CLI acceptance test uses a temporary project with no frontend/API service and
a disposable DB. It configures a local HTTP RSS publisher, previews without changing DB
bytes, fetches twice with source selection, and starts the API afterward to confirm exactly
one persisted scored Update and the expected association. No external provider or personal
database is used by tests. Other tests cover Atom/RSS parsing, validators/304, aliases,
inactive/unrelated items, URL/hash dedupe, source failures, transaction rollback, migration
from the prior schema, existing-row preservation, concurrency, and cancellation cleanup.
Production build was not rerun because frontend implementation is unchanged.

## PERSONAL_DATA_SAFETY

Before editing models, created an online SQLite backup through a read-only connection at
`.runtime/ingestion-foundation-1/personal-before-20260919T011357Z.db`.
Read-only comparison confirms all seven original table definitions and every original
row remain identical: 3 Oshi, 9 keywords, 10 Updates, 9 update associations, 8 catalog
entities, 17 aliases, and 0 catalog links. The running backend's normal reload added only
the two ingestion tables, both empty. SQLite integrity is `ok`; foreign-key checks are
clear. Evidence is in ignored `.runtime/ingestion-foundation-1/database-verification.json`.
No personal updates/following were seeded, fetched, edited, or removed.

## BLOCKERS

None for this milestone. Real-world fetching requires the user's chosen feed configuration;
no default live provider is bundled. Matching is heuristic, history is limited to entries
currently present in a feed, and imported content is not automatically updated. There is
no scheduler, launchd/Windows Task Scheduler setup, notifications, MSN scraping, or hosting.

## NEXT

Choose publisher feeds, copy/edit the local configuration, run `oshi fetch --dry-run`,
then `oshi fetch`. Refresh the running dashboard to view matches. For an alternate database,
export the same `OSHI_DATABASE_PATH` for both fetch and dashboard startup. Review this
milestone before introducing any scheduled fetching.
