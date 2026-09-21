"""Fetch outside transactions, then atomically persist each source's batch."""

import hashlib
import json
import sqlite3
from contextlib import closing
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from pydantic import ValidationError
from sqlalchemy import Engine, select
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.orm import Session

from app.database import create_schema, make_engine
from app.ingestion.contracts import FetchedItem, FetchResult, FetchState, SourceAdapter, SourceError
from app.ingestion.matching import identities, match_oshi, normalized_text
from app.models import IngestedRecord, SourceState, Update, UpdateCategory
from app.schemas import UpdateCreate
from app.scoring import calculate_relevance


@dataclass
class FetchReport:
    sources_checked: int = 0
    items_received: int = 0
    matched: int = 0
    new_updates: int = 0
    duplicates: int = 0
    ignored: int = 0
    failed_sources: int = 0
    messages: list[str] = field(default_factory=list)


def canonical_url(value: str) -> str:
    parsed = urlsplit(value)
    host = (parsed.hostname or "").lower().encode("idna").decode("ascii")
    if ":" in host:
        host = f"[{host}]"
    if parsed.port and (parsed.scheme, parsed.port) not in (("http", 80), ("https", 443)):
        host += f":{parsed.port}"
    query = sorted(
        (key, val)
        for key, val in parse_qsl(parsed.query, keep_blank_values=True)
        if not key.lower().startswith("utm_")
        and key.lower() not in {"fbclid", "gclid", "dclid", "mc_cid", "mc_eid"}
    )
    return urlunsplit((parsed.scheme.lower(), host, parsed.path or "/", urlencode(query), ""))


def digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False).encode()).hexdigest()


def normalize_item(item: FetchedItem, adapter: SourceAdapter) -> UpdateCreate:
    if item.source_key != adapter.source_key:
        raise ValueError("Item source does not match adapter")
    if urlsplit(item.source_url).username:
        raise ValueError("Article URLs cannot contain credentials")
    return UpdateCreate(
        title=" ".join(item.title.split()),
        summary=item.summary or "",
        source=adapter.name,
        source_url=item.source_url,
        published_at=item.published_at,
        category=item.category_hint
        if item.category_hint in UpdateCategory
        else UpdateCategory.NEWS,
        deadline=item.deadline,
        start_date=item.start_date,
        end_date=item.end_date,
        location=item.location,
    )


def reserve_source(session: Session, source_key: str, now: datetime) -> SourceState:
    # Reserve SQLite's writer BEFORE dedupe reads, including across different sources/processes.
    session.execute(
        insert(SourceState)
        .values(source_key=source_key, last_attempt_at=now, failure_count=0)
        .on_conflict_do_update(index_elements=["source_key"], set_={"source_key": source_key})
    )
    return session.scalar(select(SourceState).where(SourceState.source_key == source_key))


def process_batch(
    session: Session, adapter: SourceAdapter, result: FetchResult, now: datetime
) -> FetchReport:
    report = FetchReport(items_received=len(result.items))
    known = identities(session)
    for item in result.items:
        try:
            payload = normalize_item(item, adapter)
            url = canonical_url(payload.source_url)
            external = item.external_key.strip() if item.external_key else None
            external = external or None
        except (ValidationError, ValueError, TypeError):
            report.ignored += 1
            report.messages.append(f"{adapter.source_key}: skipped an invalid item.")
            continue
        content_hash = digest([normalized_text(payload.title), normalized_text(payload.summary)])
        matched = match_oshi(known, payload.title, payload.summary)
        report.matched += bool(matched)
        own = None
        if external is not None:
            own = session.scalar(
                select(IngestedRecord).where(
                    IngestedRecord.source_key == adapter.source_key,
                    IngestedRecord.external_key == external,
                )
            )
        else:
            own = session.scalar(
                select(IngestedRecord)
                .where(
                    IngestedRecord.source_key == adapter.source_key,
                    IngestedRecord.external_key.is_(None),
                    IngestedRecord.source_url == url,
                )
                .order_by(IngestedRecord.id)
            )
        duplicate = own if own and own.update_id is not None else None
        if duplicate is None:
            duplicate = session.scalar(
                select(IngestedRecord)
                .where(IngestedRecord.source_url == url, IngestedRecord.update_id.is_not(None))
                .order_by(IngestedRecord.id)
            )
        if duplicate is None and external is None:
            duplicate = session.scalar(
                select(IngestedRecord)
                .where(
                    IngestedRecord.source_key == adapter.source_key,
                    IngestedRecord.content_hash == content_hash,
                    IngestedRecord.update_id.is_not(None),
                )
                .order_by(IngestedRecord.id)
            )
        if own is None:
            own = IngestedRecord(
                source_key=adapter.source_key,
                external_key=external,
                source_url=url,
                content_hash=content_hash,
                first_seen_at=now,
                last_seen_at=now,
            )
            session.add(own)
        own.last_seen_at = now
        # Retain original identity fingerprints; only provenance last_seen advances on repeats.
        if duplicate is not None:
            own.update_id = duplicate.update_id
            report.duplicates += 1
        elif not matched:
            report.ignored += 1
        else:
            update = Update(**payload.model_dump(exclude={"oshi_ids"}), oshi=matched)
            update.relevance_score = calculate_relevance(update)
            session.add(update)
            session.flush()
            own.update_id = update.id
            report.new_updates += 1
        session.flush()
    return report


def fetch_sources(engine: Engine, adapters: list[SourceAdapter]) -> FetchReport:
    report = FetchReport()
    for adapter in adapters:
        report.sources_checked += 1
        now = datetime.now(UTC)
        received = 0
        try:
            with Session(engine) as session:
                request_key = digest(
                    [adapter.cache_key, [(oshi.id, terms) for oshi, terms in identities(session)]]
                )
                state = session.scalar(
                    select(SourceState).where(SourceState.source_key == adapter.source_key)
                )
                conditional = (
                    FetchState(state.etag, state.last_modified)
                    if state and state.request_key == request_key
                    else FetchState()
                )
            result = adapter.fetch(conditional)
            received = len(result.items)
            if result.not_modified and not (conditional.etag or conditional.last_modified):
                raise SourceError("Feed returned 304 without a conditional request.")
            with Session(engine) as session, session.begin():
                state = reserve_source(session, adapter.source_key, now)
                batch = process_batch(session, adapter, result, now)
                state.last_attempt_at = now
                state.last_success_at = datetime.now(UTC)
                state.failure_count = 0
                state.request_key = request_key
                state.etag = result.etag or (conditional.etag if result.not_modified else None)
                state.last_modified = result.last_modified or (
                    conditional.last_modified if result.not_modified else None
                )
            for name in ("items_received", "matched", "new_updates", "duplicates", "ignored"):
                setattr(report, name, getattr(report, name) + getattr(batch, name))
            report.messages.extend(batch.messages)
        except Exception as error:
            # Roll back the source's entire batch, then record failure separately.
            # Continue other sources. KeyboardInterrupt/SystemExit are intentionally not caught.
            report.failed_sources += 1
            report.items_received += received
            detail = str(error) if isinstance(error, SourceError) else type(error).__name__
            report.messages.append(f"{adapter.source_key}: {detail}")
            with Session(engine) as session, session.begin():
                state = reserve_source(session, adapter.source_key, now)
                state.last_attempt_at = now
                state.failure_count += 1
    return report


def copy_database(source: Path, destination: Path) -> None:
    """SQLite online backup from a read-only connection, including committed WAL data."""
    # Connection context managers commit/roll back but do not close the handles.
    with closing(sqlite3.connect(source.as_uri() + "?mode=ro", uri=True)) as original:
        with closing(sqlite3.connect(destination)) as copy:
            original.backup(copy)


def run_fetch(path: Path, adapters: list[SourceAdapter], *, dry_run: bool = False) -> FetchReport:
    if not adapters:
        return FetchReport()
    if dry_run:
        with TemporaryDirectory(prefix="oshi-fetch-dry-run-") as directory:
            preview = Path(directory) / "preview.db"
            if path.exists():
                copy_database(path.resolve(), preview)
            return run_fetch(preview, adapters)
    engine = make_engine(path)
    try:
        create_schema(engine)
        return fetch_sources(engine, adapters)
    finally:
        engine.dispose()
