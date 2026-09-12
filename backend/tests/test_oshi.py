import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Keyword, UpdateOshi


def test_oshi_create_list_and_patch_keywords(client, make_oshi):
    low = make_oshi(name="原神", priority=10)
    high = make_oshi(name="進撃の巨人", type="ANIME", priority=90)
    assert [row["id"] for row in client.get("/api/oshi").json()] == [high["id"], low["id"]]
    assert low["active"] is True
    assert low["created_at"].endswith("Z")
    assert low["keywords"][0]["oshi_id"] == low["id"]
    response = client.patch(
        f"/api/oshi/{low['id']}",
        json={
            "name": "Genshin Impact",
            "active": False,
            "keywords": [{"value": "ナヒーダ", "weight": 50}, {"value": "Nahida", "weight": 1}],
        },
    )
    assert response.status_code == 200
    changed = response.json()
    assert changed["type"] == "GAME"
    assert changed["name"] == "Genshin Impact"
    assert changed["active"] is False
    assert changed["keywords"][0]["id"] == low["keywords"][0]["id"]
    assert [k["weight"] for k in changed["keywords"]] == [50, 1]
    assert client.patch(f"/api/oshi/{low['id']}", json={"keywords": []}).json()["keywords"] == []


@pytest.mark.parametrize(
    "body",
    [
        {"name": " "},
        {"type": "ACTOR"},
        {"priority": -1},
        {"priority": 101},
        {"priority": True},
        {"name": None},
        {"active": None},
        {"keywords": None},
        {"keywords": [{"value": ""}]},
        {"keywords": [{"value": "Nahida", "weight": -1}]},
        {"keywords": [{"value": "RYUJIN"}, {"value": "Ｒｙｕｊｉｎ"}]},
        {"unexpected": 1},
    ],
)
def test_invalid_oshi_create_and_patch_are_rejected(client, make_oshi, body):
    oshi = make_oshi()
    assert (
        client.post("/api/oshi", json={"name": "Test", "type": "OTHER", **body}).status_code == 422
    )
    assert client.patch(f"/api/oshi/{oshi['id']}", json=body).status_code == 422
    assert client.get("/api/oshi").json() == [oshi]


def test_oshi_changes_refresh_linked_scores(client, make_oshi, make_update):
    oshi = make_oshi()
    update = make_update(title="ナヒーダ news", oshi_ids=[oshi["id"]])
    assert update["relevance_score"] == 65
    path = f"/api/oshi/{oshi['id']}"
    update_path = f"/api/updates/{update['id']}"
    assert (
        client.patch(path, json={"keywords": [{"value": "ナヒーダ", "weight": 0}]}).status_code
        == 200
    )
    assert client.get(update_path).json()["relevance_score"] == 40
    assert client.patch(path, json={"active": False}).status_code == 200
    assert client.get(update_path).json()["relevance_score"] == 0
    assert client.patch(path, json={"active": True}).status_code == 200
    assert client.get(update_path).json()["relevance_score"] == 40


def test_deletion_preserves_updates_and_other_oshi(client, application, make_oshi, make_update):
    first = make_oshi()
    second = make_oshi(name="Ryujin", type="IDOL", keywords=[])
    shared = make_update(title="ナヒーダ collaboration", oshi_ids=[first["id"], second["id"]])
    solo = make_update(title="ナヒーダ goods", category="MERCH", oshi_ids=[first["id"]])
    response = client.delete(f"/api/oshi/{first['id']}")
    assert response.status_code == 204
    assert response.content == b""
    assert client.get("/api/oshi").json() == [second]
    remaining_shared = client.get(f"/api/updates/{shared['id']}").json()
    remaining_solo = client.get(f"/api/updates/{solo['id']}").json()
    assert remaining_shared["oshi_ids"] == [second["id"]]
    assert remaining_shared["relevance_score"] == 40
    assert remaining_solo["oshi_ids"] == []
    assert remaining_solo["relevance_score"] == 10
    with Session(application.state.engine) as session:
        assert session.scalar(select(func.count()).select_from(Keyword)) == 0
        assert session.scalar(select(func.count()).select_from(UpdateOshi)) == 1


def test_missing_oshi(client):
    assert client.patch("/api/oshi/999", json={"name": "Missing"}).status_code == 404
    assert client.delete("/api/oshi/999").status_code == 404
