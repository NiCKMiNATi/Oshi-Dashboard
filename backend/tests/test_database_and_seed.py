from datetime import UTC, date, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError, StatementError
from sqlalchemy.orm import Session

from app.config import ROOT_DIR, resolve_database_path
from app.main import create_app
from app.models import Keyword, Oshi, Update, UpdateCategory, UpdateOshi, UpdateStatus
from app.seed import DEMO_NOTICE, seed_database


def test_seed_is_repeatable_preserves_edits_and_covers_demo_states(client, application):
    engine = application.state.engine
    assert seed_database(engine, date(2026, 9, 12)) == {"oshi_added": 3, "updates_added": 10}
    oshi = client.get("/api/oshi").json()
    assert {row["name"] for row in oshi} == {"進撃の巨人", "原神", "Ryujin"}
    updates = client.get("/api/updates").json()
    assert {row["status"] for row in updates} == set(UpdateStatus)
    assert {row["category"] for row in updates} == set(UpdateCategory)
    assert all(DEMO_NOTICE in row["summary"] for row in updates)
    assert all(row["source_url"].startswith("https://example.invalid/") for row in updates)
    assert all(0 <= row["relevance_score"] <= 100 for row in updates)
    client.patch(f"/api/updates/{updates[0]['id']}/status", json={"status": "IGNORED"})
    client.patch(f"/api/oshi/{oshi[0]['id']}", json={"active": False, "keywords": []})
    before = client.get("/api/updates").json()
    before_oshi = client.get("/api/oshi").json()
    assert seed_database(engine, date(2027, 1, 1)) == {"oshi_added": 0, "updates_added": 0}
    assert client.get("/api/updates").json() == before
    assert client.get("/api/oshi").json() == before_oshi


def test_seed_fills_partial_database_without_overwriting_oshi(client, application, make_oshi):
    existing = make_oshi(name="原神", priority=3, keywords=[], active=False)
    assert seed_database(application.state.engine) == {"oshi_added": 2, "updates_added": 10}
    assert existing in client.get("/api/oshi").json()


def test_foreign_keys_and_database_cascades(client, application, make_oshi, make_update):
    oshi = make_oshi()
    update = make_update(oshi_ids=[oshi["id"]])
    engine = application.state.engine
    with engine.connect() as connection:
        assert connection.scalar(text("PRAGMA foreign_keys")) == 1
    with Session(engine) as session:
        session.add(Keyword(oshi_id=999, value="orphan", weight=1))
        with pytest.raises(IntegrityError):
            session.commit()
    with engine.begin() as connection:
        connection.execute(text("DELETE FROM oshi WHERE id = :id"), {"id": oshi["id"]})
    with Session(engine) as session:
        assert session.scalar(select(func.count()).select_from(Keyword)) == 0
        assert session.scalar(select(func.count()).select_from(UpdateOshi)) == 0
        assert session.get(Update, update["id"]) is not None


def test_database_rejects_duplicate_associations_and_invalid_scores(
    client, application, make_oshi, make_update
):
    oshi = make_oshi()
    update = make_update(oshi_ids=[oshi["id"]])
    with Session(application.state.engine) as session:
        session.add(UpdateOshi(update_id=update["id"], oshi_id=oshi["id"]))
        with pytest.raises(IntegrityError):
            session.commit()
    with Session(application.state.engine) as session:
        session.get(Update, update["id"]).relevance_score = 101
        with pytest.raises(IntegrityError):
            session.commit()


def test_timestamps_persist_as_utc_and_reject_naive_values(client, application, make_oshi):
    oshi = make_oshi()
    with Session(application.state.engine) as session:
        assert session.get(Oshi, oshi["id"]).created_at.tzinfo == UTC
        session.get(Oshi, oshi["id"]).created_at = datetime(2026, 9, 12)
        with pytest.raises(StatementError, match="timezone offset"):
            session.commit()


def test_database_persists_across_app_restarts_and_startup_does_not_seed(tmp_path):
    path = tmp_path / "new-directory" / "persist.db"
    first = create_app(path)
    assert not path.exists()
    with TestClient(first, base_url="http://localhost") as client:
        assert client.get("/api/oshi").json() == []
        created = client.post("/api/oshi", json={"name": "Ryujin", "type": "IDOL"}).json()
    with TestClient(create_app(path), base_url="http://localhost") as client:
        assert client.get("/api/oshi").json() == [created]
        assert client.get("/api/updates").json() == []


def test_database_path_is_independent_of_working_directory(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("OSHI_DATABASE_PATH", raising=False)
    assert resolve_database_path() == ROOT_DIR / "data/oshi.db"
    monkeypatch.setenv("OSHI_DATABASE_PATH", "data/custom.db")
    assert resolve_database_path() == ROOT_DIR / "data/custom.db"
    assert resolve_database_path(tmp_path / "override.db") == tmp_path / "override.db"
