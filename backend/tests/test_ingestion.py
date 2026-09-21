import json
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import Mock

import pytest
from sqlalchemy import inspect, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.ingestion import pipeline
from app.ingestion.__main__ import main
from app.ingestion.config import ConfigError, load_sources
from app.ingestion.contracts import FetchedItem, FetchResult, FixtureAdapter, SourceError
from app.ingestion.pipeline import canonical_url, run_fetch
from app.models import IngestedRecord, SourceState, Update


@pytest.fixture
def database(application, client):
    return Path(application.state.engine.url.database)


def item(**changes):
    return FetchedItem(
        **{
            "source_key": "test",
            "external_key": "article-1",
            "source_url": "https://example.invalid/article",
            "title": "[DEMO] 原神 announcement",
            "summary": "Fictional fixture: ナヒーダ news.",
            **changes,
        }
    )


def adapter(*items, **changes):
    return FixtureAdapter(**{"source_key": "test", "items": items, **changes})


def snapshot(path):
    with sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True) as connection:
        return "\n".join(connection.iterdump())


@pytest.mark.parametrize(
    ("name", "keywords", "title", "summary", "expected"),
    [
        ("原神", [], "原神のお知らせ", "", True),
        ("Ryujin", [], "ＲＹＵＪＩＮ news", "", True),
        ("Yuma Uchida", [], "Yuma\u3000  Uchida news", "", True),
        ("Another favorite", [{"value": "ナヒーダ", "weight": 1}], "News", "ナヒーダ登場", True),
        ("Another favorite", [{"value": "ナヒーダ", "weight": 0}], "News", "ナヒーダ登場", False),
        ("原神", [], "Unrelated cooking article", "", False),
        ("ITZY", [], "A glitzy evening", "", False),
        ("AI", [], "An AI announcement", "", False),
        ("あ", [], "あいうえお", "", False),
        ("123", [], "123 news", "", False),
    ],
)
def test_matching(database, make_oshi, client, name, keywords, title, summary, expected):
    make_oshi(name=name, keywords=keywords)
    report = run_fetch(database, [adapter(item(title=title, summary=summary))])
    assert report.matched == int(expected)
    assert report.new_updates == int(expected)
    assert report.ignored == int(not expected)
    assert len(client.get("/api/updates").json()) == int(expected)


@pytest.mark.parametrize("title", ["Higedan news", "Official髭男dismのお知らせ", "ヒゲダン新曲"])
def test_linked_catalog_name_and_alias_survive_personal_rename(database, client, title):
    entity = client.get("/api/discover?q=Higedan").json()[0]
    tracked = client.post(f"/api/discover/{entity['id']}/track").json()
    client.patch(f"/api/oshi/{tracked['id']}", json={"name": "My band", "keywords": []})
    report = run_fetch(database, [adapter(item(title=title))])
    assert report.new_updates == 1
    assert client.get("/api/updates").json()[0]["oshi_ids"] == [tracked["id"]]


def test_multiple_matches_exclude_inactive(database, make_oshi, client):
    first = make_oshi()
    second = make_oshi(name="Ryujin", type="IDOL", keywords=[])
    make_oshi(name="Paused", keywords=[{"value": "原神", "weight": 1}], active=False)
    report = run_fetch(database, [adapter(item(title="原神 and Ryujin"))])
    assert report.matched == 1
    assert client.get("/api/updates").json()[0]["oshi_ids"] == [first["id"], second["id"]]


def test_fixture_creation_uses_existing_scorer_and_no_invented_dates(
    database, application, make_oshi, client, monkeypatch
):
    make_oshi()
    real_scorer = pipeline.calculate_relevance
    scorer = Mock(wraps=real_scorer)
    monkeypatch.setattr(pipeline, "calculate_relevance", scorer)
    published = datetime(2026, 9, 19, 1, tzinfo=UTC)
    report = run_fetch(database, [adapter(item(published_at=published))])
    update = client.get("/api/updates").json()[0]
    assert report.items_received == report.new_updates == 1
    assert update["relevance_score"] == 65
    assert update["category"] == "NEWS"
    assert update["status"] == "NEW"
    assert update["published_at"] == "2026-09-19T01:00:00Z"
    assert all(
        update[field] is None for field in ("deadline", "start_date", "end_date", "location")
    )
    scorer.assert_called_once()
    with Session(application.state.engine) as session:
        state = session.scalar(select(SourceState))
        assert state.last_attempt_at <= state.last_success_at
        assert state.last_success_at.tzinfo == UTC
        assert state.failure_count == 0
        provenance = session.scalar(select(IngestedRecord))
        assert provenance.update_id == update["id"]
        assert provenance.first_seen_at == provenance.last_seen_at


@pytest.mark.parametrize("category,expected", [("MERCH", "MERCH"), ("NOT_A_CATEGORY", "NEWS")])
def test_category_hint(database, make_oshi, client, category, expected):
    make_oshi()
    run_fetch(database, [adapter(item(category_hint=category))])
    assert client.get("/api/updates").json()[0]["category"] == expected


def test_explicit_adapter_dates_and_location(database, make_oshi, client):
    make_oshi()
    run_fetch(
        database,
        [
            adapter(
                item(
                    category_hint="EVENT",
                    location="Tokyo",
                    deadline=datetime(2026, 10, 1, tzinfo=UTC),
                )
            )
        ],
    )
    update = client.get("/api/updates").json()[0]
    assert update["relevance_score"] == 100
    assert update["location"] == "Tokyo"


def test_repeat_external_id_preserves_all_personal_edits(database, make_oshi, client, application):
    make_oshi()
    run_fetch(database, [adapter(item())])
    update = client.get("/api/updates").json()[0]
    client.patch(
        f"/api/updates/{update['id']}", json={"title": "My edited title", "status": "SAVED"}
    )
    before = client.get("/api/updates").json()
    with Session(application.state.engine) as session:
        first_seen = session.scalar(select(IngestedRecord)).first_seen_at
    report = run_fetch(
        database,
        [adapter(item(title="Changed 原神 news", source_url="https://example.invalid/changed"))],
    )
    assert report.duplicates == 1
    assert report.new_updates == 0
    assert client.get("/api/updates").json() == before
    with Session(application.state.engine) as session:
        record = session.scalar(select(IngestedRecord))
        assert record.first_seen_at == first_seen < record.last_seen_at


def test_same_url_deduplicates_different_ids_and_sources(database, make_oshi, client, application):
    make_oshi()
    first = item(source_url="https://EXAMPLE.invalid:443/article?b=2&a=1&utm_source=rss#part")
    second = item(external_key="different", source_url="https://example.invalid/article?a=1&b=2")
    third = replace(second, source_key="other", external_key="another")
    report = run_fetch(database, [adapter(first, second), adapter(third, source_key="other")])
    assert report.new_updates == 1
    assert report.duplicates == 2
    assert len(client.get("/api/updates").json()) == 1
    with Session(application.state.engine) as session:
        rows = session.scalars(select(IngestedRecord)).all()
        assert len(rows) == 3
        assert len({row.update_id for row in rows}) == 1


def test_hash_fallback_is_source_scoped_and_only_without_external_id(database, make_oshi, client):
    make_oshi()
    first = item(external_key=None)
    second = replace(first, source_url="https://example.invalid/alternative")
    third = replace(first, external_key="distinct", source_url="https://example.invalid/distinct")
    report = run_fetch(database, [adapter(first, second, third)])
    assert report.new_updates == 2
    assert report.duplicates == 1
    other = replace(second, source_key="other", source_url="https://elsewhere.invalid/article")
    assert run_fetch(database, [adapter(other, source_key="other")]).new_updates == 1
    assert len(client.get("/api/updates").json()) == 3


def test_unmatched_provenance_can_later_become_an_update(database, make_oshi, application):
    fixture = adapter(item())
    assert run_fetch(database, [fixture]).ignored == 1
    make_oshi()
    assert run_fetch(database, [fixture]).new_updates == 1
    with Session(application.state.engine) as session:
        assert len(session.scalars(select(IngestedRecord)).all()) == 1


def test_failed_source_isolation_and_failure_count(database, make_oshi, application):
    make_oshi()
    bad = Mock(source_key="bad", name="Bad", cache_key="bad")
    bad.fetch.side_effect = SourceError("Network unavailable")
    for expected in (1, 2):
        report = run_fetch(database, [bad, adapter(item())])
        assert report.failed_sources == 1
        assert report.sources_checked == 2
        with Session(application.state.engine) as session:
            state = session.scalar(select(SourceState).where(SourceState.source_key == "bad"))
            assert state.failure_count == expected
            assert state.last_success_at is None
    bad.fetch.side_effect = None
    bad.fetch.return_value = FetchResult()
    assert run_fetch(database, [bad]).failed_sources == 0
    with Session(application.state.engine) as session:
        state = session.scalar(select(SourceState).where(SourceState.source_key == "bad"))
        assert state.failure_count == 0
        assert state.last_success_at is not None


def test_partial_source_batch_rolls_back_on_processing_failure(
    database, make_oshi, application, monkeypatch
):
    make_oshi()
    monkeypatch.setattr(
        pipeline, "calculate_relevance", Mock(side_effect=[65, RuntimeError("broken adapter")])
    )
    report = run_fetch(
        database, [adapter(item(), item(external_key="2", source_url="https://example.invalid/2"))]
    )
    assert report.failed_sources == 1
    assert report.new_updates == 0
    with Session(application.state.engine) as session:
        assert session.scalars(select(Update)).all() == []
        assert session.scalars(select(IngestedRecord)).all() == []
        assert session.scalar(select(SourceState)).failure_count == 1


def test_validators_reset_on_following_or_source_change_and_survive_failure(
    database, make_oshi, client, application
):
    source = Mock(source_key="test", name="Test", cache_key="url-one")
    source.name = "Test"
    source.fetch.return_value = FetchResult(items=(item(),), etag='"v1"', last_modified="yesterday")
    assert run_fetch(database, [source]).ignored == 1
    source.fetch.return_value = FetchResult(not_modified=True)
    assert run_fetch(database, [source]).failed_sources == 0
    assert source.fetch.call_args.args[0].etag == '"v1"'
    tracked = make_oshi()
    source.fetch.return_value = FetchResult(items=(item(),), etag='"v1"')
    assert run_fetch(database, [source]).new_updates == 1
    assert source.fetch.call_args.args[0].etag is None
    source.fetch.side_effect = SourceError("Unavailable")
    run_fetch(database, [source])
    with Session(application.state.engine) as session:
        state = session.scalar(select(SourceState))
        assert state.etag == '"v1"'
        assert state.failure_count == 1
        success = state.last_success_at
    source.fetch.side_effect = None
    source.fetch.return_value = FetchResult(not_modified=True)
    run_fetch(database, [source])
    with Session(application.state.engine) as session:
        assert session.scalar(select(SourceState)).last_success_at >= success
    source.cache_key = "url-two"
    source.fetch.return_value = FetchResult()
    run_fetch(database, [source])
    assert source.fetch.call_args.args[0].etag is None
    client.patch(f"/api/oshi/{tracked['id']}", json={"active": False})
    run_fetch(database, [source])
    assert source.fetch.call_args.args[0].etag is None


def test_dry_run_preserves_bytes_schema_and_state(database, make_oshi):
    make_oshi()
    before, raw = snapshot(database), database.read_bytes()
    report = run_fetch(database, [adapter(item(), item())], dry_run=True)
    assert report.new_updates == 1
    assert report.duplicates == 1
    assert snapshot(database) == before
    assert database.read_bytes() == raw


def test_dry_run_does_not_create_a_missing_database(tmp_path):
    path = tmp_path / "missing" / "personal.db"
    assert run_fetch(path, [adapter(item())], dry_run=True).ignored == 1
    assert not path.parent.exists()


def test_old_schema_and_existing_rows_unchanged(database, application, make_oshi, make_update):
    make_oshi()
    make_update(title="User-edited historical content", status="GOING")
    engine = application.state.engine
    with engine.begin() as connection:
        connection.execute(text("DROP TABLE ingested_records"))
        connection.execute(text("DROP TABLE source_states"))
    before = snapshot(database)
    run_fetch(database, [adapter(item())], dry_run=True)
    assert snapshot(database) == before
    assert "source_states" not in inspect(engine).get_table_names()
    run_fetch(database, [adapter(item(title="Unrelated article", summary=""))])
    with sqlite3.connect(database) as connection:
        new_lines = [
            line
            for line in connection.iterdump()
            if not any(name in line for name in ("source_states", "ingested_records"))
        ]
    assert "\n".join(new_lines) == before


def test_provenance_unique_external_id_and_fk(database, application, make_oshi):
    make_oshi()
    run_fetch(database, [adapter(item())])
    with Session(application.state.engine) as session:
        record = session.scalar(select(IngestedRecord))
        session.add(
            IngestedRecord(
                source_key=record.source_key,
                external_key=record.external_key,
                source_url=record.source_url,
                content_hash=record.content_hash,
                first_seen_at=record.first_seen_at,
                last_seen_at=record.last_seen_at,
            )
        )
        with pytest.raises(IntegrityError):
            session.commit()
    with application.state.engine.begin() as connection:
        connection.execute(text("DELETE FROM updates"))
    with Session(application.state.engine) as session:
        assert session.scalar(select(IngestedRecord)).update_id is None


def test_invalid_items_are_ignored_without_losing_valid_items(database, make_oshi):
    make_oshi()
    report = run_fetch(database, [adapter(item(source_url=""), item(title=""), item())])
    assert report.ignored == 2
    assert report.new_updates == 1
    assert report.failed_sources == 0


def test_canonical_url_keeps_meaningful_query_values():
    assert (
        canonical_url("HTTPS://EXAMPLE.COM:443?utm_source=x&id=42#top")
        == "https://example.com/?id=42"
    )
    assert canonical_url("https://example.com/?id=43") != canonical_url(
        "https://example.com/?id=42"
    )


def test_missing_configuration_and_source_filter(tmp_path, monkeypatch, capsys):
    config = tmp_path / "sources.json"
    path = tmp_path / "untouched.db"
    monkeypatch.setenv("OSHI_DATABASE_PATH", str(path))
    monkeypatch.setenv("OSHI_SOURCES_PATH", str(config))
    assert main([]) == 0
    assert "No enabled sources configured" in capsys.readouterr().out
    assert not path.exists()
    assert main(["--source", "missing"]) == 1
    config.write_text(
        json.dumps(
            {
                "sources": [
                    {"key": "one", "url": "https://example.invalid/1"},
                    {"key": "two", "url": "https://example.invalid/2"},
                    {"key": "off", "url": "https://example.invalid/3", "enabled": False},
                ]
            }
        )
    )
    assert [source.key for source in load_sources(config)] == ["one", "two"]
    assert [source.key for source in load_sources(config, "two")] == ["two"]
    with pytest.raises(ConfigError, match="unknown or disabled"):
        load_sources(config, "off")


@pytest.mark.parametrize(
    "content",
    [
        "not json",
        '{"sources":[{"key":"bad","url":"file:///tmp/feed"}]}',
        '{"sources":[{"key":"a","url":"https://example.invalid"},{"key":"a","url":"https://example.invalid"}]}',
    ],
)
def test_invalid_config_is_clear_and_does_not_echo_url_secrets(tmp_path, content):
    config = tmp_path / "sources.json"
    config.write_text(content)
    with pytest.raises(ConfigError) as error:
        load_sources(config)
    assert "file:///" not in str(error.value)


def test_concurrent_fetches_do_not_create_duplicate_updates(database, make_oshi, client):
    make_oshi()
    with ThreadPoolExecutor(max_workers=2) as pool:
        reports = list(pool.map(lambda _: run_fetch(database, [adapter(item())]), range(2)))
    assert sum(report.new_updates for report in reports) == 1
    assert sum(report.duplicates for report in reports) == 1
    assert not any(report.failed_sources for report in reports)
    assert len(client.get("/api/updates").json()) == 1
