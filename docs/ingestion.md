# Manual ingestion

`oshi fetch` reads configured RSS/Atom sources and creates ordinary Updates for active
tracked oshi. FastAPI and Next.js may both be stopped. Manual fetching remains available; optional [Windows scheduled fetching](background-fetch-windows.md)
invokes the same entry point every 30 minutes. No persistent worker, scraping, MSN adapter,
or external catalog integration is installed.

## Configure sources

After `./scripts/setup.sh`, copy the example and edit your local file:

```sh
mkdir -p local
cp config/sources.example.json local/sources.json
```

The example uses a disabled `example.invalid` URL. Replace it with a publisher's RSS/Atom
feed URL and set `enabled` to `true`. Personal feed URLs belong only in the ignored
`local/` directory, not source control. A configuration looks like:

```json
{
  "sources": [
    {
      "key": "my-anime-publisher",
      "type": "rss",
      "name": "My anime publisher",
      "url": "https://example.invalid/feed.xml",
      "enabled": true
    }
  ]
}
```

- `key`: stable, unique identifier, 1–100 ASCII letters/digits/underscores/hyphens,
  starting with a letter or digit. Renaming it creates a new source identity.
- `type`: currently only `rss`; the adapter handles both RSS and Atom.
- `url`: HTTP(S) feed URL. Embedded username/password credentials are unsupported.
- `name`: optional display name stored in Update.source; defaults to the source key.
- `enabled`: defaults to `true`. Disabled entries are never fetched.
- `category_hint`: optional existing category enum, for feeds reliably dedicated to that
  category. Otherwise omit it and items default to `NEWS`. RSS tag/category strings are
  not interpreted as reliable category hints.

Unknown configuration fields, duplicate keys, and invalid categories/URLs are errors.
`OSHI_SOURCES_PATH` overrides the config file. Relative paths resolve against the repository,
regardless of the shell's working directory. Missing configuration or no enabled sources
prints an explanation and exits successfully without creating a database. An unknown or
disabled `--source` is an error. No real sources ship enabled.

## Commands and outcomes

```sh
oshi fetch
oshi fetch --dry-run
oshi fetch --source my-anime-publisher
oshi fetch --source my-anime-publisher --dry-run
```

The command uses the backend virtual environment and inherits `OSHI_DATABASE_PATH`.
It does not require Node, probe/start/stop dashboard services, or call the HTTP API.
An explicitly exported database path takes precedence; otherwise the normal repository
database is used. It does not infer another database from a running service's CLI state.
Use the same override for fetch and dashboard startup when working with an alternate DB.

The platform-independent backend entry point is also available directly:

```sh
backend/.venv/bin/python -m app.ingestion --dry-run
```

On Windows after `.\scripts\setup.ps1`, use:

```powershell
.\backend\.venv\Scripts\python.exe -m app.ingestion --dry-run
```

All ingestion CLI invocations use the project-local `.runtime/ingestion.lock`; a busy
fetch is skipped with exit 0. Kernel locks release on crash; do not delete the lock file.
`--background` enables bounded rotating UTC logs. `--database-path` and `--sources-path`
explicitly override the environment for scheduler invocations.

The macOS `oshi` wrapper retains its existing command lock and lifecycle behavior. No
shell profile change or wrapper reinstall is needed for an already installed command.

Output contains Sources checked, Items received, Matched, New updates, Duplicates,
Ignored, Failed sources, and elapsed time. `Matched` counts items with at least one active
match, including duplicates; it is not the number of associations. `Ignored` includes
unmatched and invalid items. A failed batch counts received items but no committed outcomes.
Source diagnostics name the source key without echoing feed URLs or response bodies.
Exit status is 1 when any source fails, even if other sources succeeded; Ctrl+C exits 130.
Earlier committed sources remain committed if a later source fails or the run is cancelled.

Dry-run makes a temporary SQLite copy through a read-only connection and executes the
same pipeline against the copy. This includes schema initialization, source state, dedupe
within the batch, and scoring. The original database's schema, rows, and fetch state do not
change. A nonexistent target database remains nonexistent. Dry-run still contacts feeds.

Both SQLite backup connections are explicitly closed on success and failure, so no
database handles remain open when the temporary preview directory is removed.

After a successful fetch, start the dashboard or press Refresh if it is already open.
Updates use the existing feed, filters, detail drawer, and status actions.

## Adapter contract and data flow

`backend/app/ingestion/contracts.py` defines a structural `SourceAdapter` protocol:

```text
source_key: stable source identity
name: source display label
cache_key: stable representation of fetch-affecting adapter configuration
fetch(FetchState(etag, last_modified)) -> FetchResult
```

`FetchResult` contains a tuple of `FetchedItem`, optional ETag/Last-Modified values, and
`not_modified`. Items contain source_key, nullable external_key, title, nullable summary,
source_url, nullable published_at and category_hint. Optional deadline, start_date,
end_date, and location are reserved for adapters that explicitly supply them. Adapters
return data and never write ORM models. Importing ingestion modules does not create a DB.

`FixtureAdapter` is deterministic and local, for tests; production config cannot select it.
`RSSAdapter` downloads a feed and uses [feedparser](https://feedparser.readthedocs.io/en/latest/)
6.0.14 to handle RSS/Atom variants, namespaces, links, encodings, and date formats. This small
dependency plus its `feedparser-sgmllib` dependency replaces a custom XML parser. HTTP is
handled separately with the standard library so request limits are explicit.

Processing order:

1. Read the previous validators and current matching identities; close the read session.
2. Fetch outside any write transaction.
3. Reserve SQLite's writer before reading dedupe state.
4. Normalize/validate items with existing UpdateCreate conventions, match active oshi,
   and find provenance by external identity, canonical URL, or fallback content hash.
5. Insert/update provenance; create a new Update only for a previously unimported match.
6. Associate all matches, call the existing `calculate_relevance`, and commit the source
   batch, provenance, and successful SourceState together.

Invalid items are skipped with a concise diagnostic. A network/parse/processing failure
rolls back that source's batch and records failure state in a separate transaction. Other
sources continue. There are no retries within an invocation. SQLite write reservation
serializes concurrent writers, including different sources sharing a URL; the unique
external-identity constraint is a second safeguard.

For another adapter, implement the protocol, return these contracts, add explicit config
validation/construction, and test with disposable databases. Do not add ORM writes or
scheduler/platform logic to the adapter. No dynamic plugin registry is needed.

## Additive tables

`source_states` stores source_key (unique), last_attempt_at, nullable last_success_at,
failure_count, etag, last_modified, and request_key. Failures increment the consecutive
failure count without clearing the previous success/validators; successful responses,
including HTTP 304, reset it. request_key fingerprints source settings and current active
matching identities. Changing either suppresses old validators for the next request.
This allows following a new oshi to rescan the feed even if its HTTP ETag has not changed.

`ingested_records` stores source_key, nullable external_key, canonical source_url,
content_hash, nullable update_id, first_seen_at, and last_seen_at. `(source_key,
external_key)` is unique when an external key exists. update_id references updates with
`ON DELETE SET NULL`. URL/hash/foreign-key fields are indexed. Multiple provenance records
may point to the same Update. Valid unmatched items have provenance but no Update and
can become matched on a later fetch.

Only these two tables are added. Existing table definitions, columns, enum values, and
API routes are unchanged. Normal `create_all()` startup/fetch creates missing tables;
it never migrates old columns or seeds following/demo updates. Back up an existing DB
before schema changes; never reset personal data. The milestone's pre-change backup and
comparison live in ignored `.runtime/ingestion-foundation-1/`.

## Matching and scoring

Match title and summary against active Oshi names, positive-weight keywords, and canonical
names/aliases from explicit CatalogTracking links. Paused oshi get no new associations.
Normalize NFKC Unicode, case folding, and collapsed whitespace. ASCII terms require at
least three alphanumeric characters and ASCII word boundaries; non-ASCII terms require
two alphanumeric characters and use substring matching. Numeric-only terms are ignored.
These rules reduce trivial aliases and matches such as ITZY inside “glitzy”; they can
also miss genuinely short names. There is no transliteration, typo correction, or semantic AI.

Every matching active oshi is associated. No match means no Update. Matching determines
associations only; the unchanged backend scorer determines relevance. A match through a
name/catalog alias does not itself imply the separate +25 keyword bonus. No deadline,
event date, or location is inferred from prose. RSS published dates are normalized to UTC;
missing/invalid published dates stay null and updated timestamps are not substituted.

## Duplicate policy

1. Same `(source_key, external_key)` already mapped to an Update: duplicate even when
   the fetched content or URL changed.
2. Otherwise the same canonical URL already mapped by ingestion: duplicate, including
   across sources and across different external IDs.
3. Without an external key, identical normalized title+summary SHA-256 within the same
   source is a fallback duplicate, even if its URL changed.

Canonical URLs lowercase the scheme/host, remove default ports and fragments, sort query
parameters, and discard `utm_*`, `fbclid`, `gclid`, `dclid`, `mc_cid`, and `mc_eid`. Other
query values, path case, and trailing slashes are retained. URLs are not visited to discover
redirect/canonical metadata; stored Update source links retain the supplied URL.

Duplicate fetches advance provenance last_seen_at and can add another provenance mapping.
Original provenance fingerprints and first_seen_at remain stable. Existing Update titles,
summaries, scores, status, dates, and associations are never rewritten or expanded. Manual
API-created/demo rows are not retroactively merged into ingestion provenance. Deleting
and re-adding an oshi does not reconnect old Updates.

## Network limits and remaining limits

Requests use `OshiDashboard/0.1 (personal RSS/Atom reader)`, a 10-second socket timeout,
a 30-second elapsed read/redirect budget, up to three redirects, and a 2 MiB response limit.
HTTP(S) only; HTTPS certificate verification is enabled and HTTPS-to-HTTP redirects are
rejected. Identity encoding is requested; unsolicited compressed responses fail clearly.
ETag/Last-Modified are stored only after successful processing. A 304 response receives
zero items. Malformed XML/unrecognized feeds fail; encoding-override warnings are tolerated.
HTML title/summary markup is converted to plain text, limited to existing API field sizes.
There is no proxy/authentication configuration, feed pagination, historical backfill,
article-page fetching, or automatic updates to previously imported content.

Only entries currently present in the feed can be fetched. Hash fallback may merge two
same-source entries with identical text; changing URLs without stable IDs may escape
dedupe. HTTP 304 does not replay cached content. The identity fingerprint forces a fresh
request when following changes, but cannot recover items the publisher has removed.
Optional Windows Task Scheduler setup is documented in [background fetching](background-fetch-windows.md).
No launchd setup, notifications, deployment, or queues are included.

## Verification

```sh
./scripts/test-backend.sh scripts/tests
backend/.venv/bin/ruff check backend
backend/.venv/bin/ruff format --check backend
backend/.venv/bin/ruff check scripts/oshi.py scripts/tests --config backend/pyproject.toml
backend/.venv/bin/ruff format --check scripts/oshi.py scripts/tests --config backend/pyproject.toml
```

Tests use disposable SQLite and local HTTP fixture servers. The CLI acceptance test runs
fetch with no dashboard services or frontend installation, verifies dry-run and source
selection, fetches twice, and starts the API afterward to read the one persisted Update.
No test fetches real sources or accesses `data/oshi.db`.
