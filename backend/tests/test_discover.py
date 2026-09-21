from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, inspect, select
from sqlalchemy.orm import Session

from app.catalog import seed_catalog
from app.database import Base, make_engine
from app.main import create_app
from app.models import (
    CatalogEntity,
    CatalogTracking,
    EntityAlias,
    Keyword,
    Oshi,
    Update,
    UpdateOshi,
)


def candidate(client, query):
    response = client.get("/api/discover", params={"q": query})
    assert response.status_code == 200
    return response.json()[0]


@pytest.mark.parametrize(
    "query,name",
    [
        ("Official髭男dism", "Official髭男dism"),
        ("Higedan", "Official髭男dism"),
        ("hIGEdAn", "Official髭男dism"),
        ("ＨＩＧＥＤＡＮ", "Official髭男dism"),
        ("ヒゲダン", "Official髭男dism"),
        ("髭男", "Official髭男dism"),
        ("ITZY", "ITZY"),
        ("있지", "ITZY"),
        ("AOT", "進撃の巨人"),
        ("進撃", "進撃の巨人"),
        ("Genshin", "原神"),
        ("原神", "原神"),
        ("JJK", "呪術廻戦"),
        ("Gojo", "五条悟"),
        ("五条", "五条悟"),
        ("Hyouka", "氷菓"),
        ("内田雄馬", "内田雄馬"),
        ("  Yuma　 Uchida ", "内田雄馬"),
        ("GenshinImpact", "原神"),
        ("Offi", "Official髭男dism"),
        ("geda", "Official髭男dism"),
    ],
)
def test_search_names_aliases_unicode_case_whitespace_and_partial(client, query, name):
    result = candidate(client, query)
    assert result["name"] == name
    assert result["provider"] == "local"
    assert result["description"]
    assert result["aliases"]
    assert result["is_tracked"] is False


def test_rank_order_and_limit(client, application):
    # Deliberately insert in reverse order to prove rank wins over insertion order.
    with Session(application.state.engine) as session, session.begin():
        for name, aliases in [
            ("Other", ["A Lantern Show"]),
            ("A Lantern", []),
            ("Alias prefix", ["Lantern story"]),
            ("Lantern show", []),
            ("Exact alias", ["Lantern"]),
            ("Lantern", []),
        ]:
            session.add(
                CatalogEntity(
                    name=name,
                    type="OTHER",
                    provider="test",
                    aliases=[
                        EntityAlias(alias=alias, normalized_alias=alias.casefold().replace(" ", ""))
                        for alias in aliases
                    ],
                )
            )
    results = client.get("/api/discover", params={"q": "lantern"}).json()
    assert [item["name"] for item in results] == [
        "Lantern",
        "Exact alias",
        "Lantern show",
        "Alias prefix",
        "A Lantern",
        "Other",
    ]
    assert client.get("/api/discover", params={"q": "lantern", "limit": 2}).json() == results[:2]


@pytest.mark.parametrize("query", ["", "   ", "　\t", "not in this catalog", "%", "_"])
def test_empty_and_unknown_queries(client, query):
    assert client.get("/api/discover", params={"q": query}).json() == []


def test_query_validation_and_unknown_entity(client):
    assert client.get("/api/discover").json() == []
    for params in [{"q": "a" * 201}, {"limit": 0}, {"limit": 51}]:
        assert client.get("/api/discover", params=params).status_code == 422
    assert client.post("/api/discover/99999/track").status_code == 404
    assert client.get("/api/oshi").json() == []


def test_track_defaults_keywords_duplicate_and_rename(client):
    entity = candidate(client, "Higedan")
    url = f"/api/discover/{entity['id']}/track"
    added = client.post(url)
    assert added.status_code == 201
    oshi = added.json()
    assert (oshi["name"], oshi["type"], oshi["priority"], oshi["active"]) == (
        "Official髭男dism",
        "ARTIST",
        50,
        True,
    )
    assert {item["value"] for item in oshi["keywords"]} == {
        "Official髭男dism",
        "Higedan",
        "ヒゲダン",
        "髭男",
    }
    assert all(item["weight"] == 1 for item in oshi["keywords"])
    assert candidate(client, "Higedan")["is_tracked"] is True
    duplicate = client.post(url)
    assert duplicate.status_code == 200
    assert duplicate.json() == oshi
    edited = client.patch(
        f"/api/oshi/{oshi['id']}",
        json={"name": "My favorite band", "priority": 99, "active": False, "keywords": []},
    ).json()
    assert candidate(client, "Higedan")["is_tracked"] is True
    assert client.post(url).json() == edited
    assert len(client.get("/api/oshi").json()) == 1


@pytest.mark.parametrize("name", ["原神", "genshin impact", "Ｇｅｎｓｈｉｎ　Impact"])
def test_legacy_and_manual_oshi_are_recognized_without_editing(client, make_oshi, name):
    original = make_oshi(name=name, active=False, priority=17)
    entity = candidate(client, "Genshin")
    assert entity["is_tracked"] is True
    response = client.post(f"/api/discover/{entity['id']}/track")
    assert response.status_code == 200
    assert response.json() == original
    assert client.get("/api/oshi").json() == [original]


def test_matching_requires_type_and_manual_items_need_no_catalog(client, make_oshi):
    make_oshi(name="ITZY", type="OTHER")
    assert candidate(client, "ITZY")["is_tracked"] is False
    created = make_oshi(name="An obscure personal favorite", type="OTHER")
    assert created in client.get("/api/oshi").json()
    assert client.get("/api/discover", params={"q": created["name"]}).json() == []


def test_remove_then_retrack_preserves_catalog_aliases_and_update_history(
    client, application, make_update
):
    entity = candidate(client, "ITZY")
    url = f"/api/discover/{entity['id']}/track"
    first = client.post(url).json()
    update = make_update(oshi_ids=[first["id"]])
    assert client.delete(f"/api/oshi/{first['id']}").status_code == 204
    assert candidate(client, "있지") == entity
    retained = client.get(f"/api/updates/{update['id']}").json()
    assert retained["title"] == update["title"]
    assert retained["oshi_ids"] == []
    with Session(application.state.engine) as session:
        assert session.get(CatalogTracking, entity["id"]) is None
    second = client.post(url)
    assert second.status_code == 201
    assert second.json()["name"] == "ITZY"
    assert candidate(client, "ITZY")["is_tracked"] is True
    assert client.get(f"/api/updates/{update['id']}").json()["oshi_ids"] == []


def test_concurrent_tracking_creates_one_oshi(client):
    entity = candidate(client, "ITZY")
    barrier = Barrier(4)

    def track(_):
        barrier.wait(timeout=10)
        return client.post(f"/api/discover/{entity['id']}/track")

    with ThreadPoolExecutor(max_workers=4) as executor:
        results = list(executor.map(track, range(4)))
    assert sorted(result.status_code for result in results) == [200, 200, 200, 201]
    assert len({result.json()["id"] for result in results}) == 1
    assert len(client.get("/api/oshi").json()) == 1


def test_catalog_seed_is_idempotent_and_preserves_personal_and_catalog_edits(
    client, application, make_oshi, make_update
):
    original = make_oshi(priority=11)
    update = make_update(oshi_ids=[original["id"]])
    engine = application.state.engine
    entity = candidate(client, "Higedan")
    with Session(engine) as session, session.begin():
        session.get(CatalogEntity, entity["id"]).description = "Custom description"
    before = candidate(client, "Higedan")
    seed_catalog(engine)
    seed_catalog(engine)
    assert candidate(client, "Higedan") == before
    assert client.get("/api/oshi").json() == [original]
    assert client.get("/api/updates").json() == [update]
    with Session(engine) as session:
        assert session.scalar(select(func.count()).select_from(CatalogEntity)) == 8
        assert session.scalar(select(func.count()).select_from(EntityAlias)) == 17


def test_additive_startup_preserves_original_tables_and_rows(tmp_path):
    path = tmp_path / "legacy.db"
    engine = make_engine(path)
    original_tables = [Oshi.__table__, Keyword.__table__, Update.__table__, UpdateOshi.__table__]
    Base.metadata.create_all(engine, tables=original_tables)
    with Session(engine) as session, session.begin():
        session.add(Oshi(name="Personal favorite", type="OTHER", priority=7))
    with engine.connect() as connection:
        before = {table.name: connection.execute(table.select()).all() for table in original_tables}
    engine.dispose()
    for _ in range(2):
        app = create_app(path)
        with TestClient(app, base_url="http://localhost") as browser:
            assert candidate(browser, "Higedan")["is_tracked"] is False
            with app.state.engine.connect() as connection:
                after = {
                    table.name: connection.execute(table.select()).all()
                    for table in original_tables
                }
            assert before == after
            assert set(inspect(app.state.engine).get_table_names()) == {
                "oshi",
                "keywords",
                "updates",
                "update_oshi",
                "catalog_entities",
                "entity_aliases",
                "catalog_tracking",
                "source_states",
                "ingested_records",
            }
