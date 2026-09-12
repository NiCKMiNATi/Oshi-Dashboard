import pytest

from app.models import UpdateStatus


def test_update_roundtrip_partial_patch_and_timezone(client, make_oshi, make_update):
    oshi = make_oshi()
    update = make_update(
        title="ナヒーダ exhibition",
        category="EVENT",
        oshi_ids=[oshi["id"]],
        published_at="2026-09-12T10:00:00+09:00",
        deadline="2026-09-20T23:59:00+09:00",
        start_date="2026-10-01",
        end_date="2026-10-10",
        location="Tokyo, Japan",
    )
    path = f"/api/updates/{update['id']}"
    assert update["published_at"] == "2026-09-12T01:00:00Z"
    assert update["deadline"] == "2026-09-20T14:59:00Z"
    assert update["relevance_score"] == 100
    assert update["status"] == "NEW"
    assert client.get(path).json() == update
    response = client.patch(path, json={"deadline": None, "summary": "Updated summary"})
    assert response.status_code == 200
    changed = response.json()
    assert changed["relevance_score"] == 85
    assert changed["deadline"] is None
    assert changed["summary"] == "Updated summary"
    assert changed["title"] == update["title"]
    assert changed["created_at"] == update["created_at"]
    detached = client.patch(path, json={"oshi_ids": []}).json()
    assert detached["oshi_ids"] == []
    assert detached["relevance_score"] == 20
    assert client.patch(path, json={}).json() == detached


@pytest.mark.parametrize("status", list(UpdateStatus))
def test_each_status_and_status_only_endpoint(client, make_update, status):
    update = make_update(category="MERCH")
    response = client.patch(f"/api/updates/{update['id']}/status", json={"status": status})
    assert response.status_code == 200
    assert response.json() == {**update, "status": status}


def test_general_patch_accepts_status(client, make_update):
    update = make_update()
    assert (
        client.patch(f"/api/updates/{update['id']}", json={"status": "SAVED"}).json()["status"]
        == "SAVED"
    )


@pytest.mark.parametrize(
    "body",
    [
        {"title": " "},
        {"title": None},
        {"summary": None},
        {"category": "INVALID"},
        {"source": ""},
        {"source_url": "javascript:alert(1)"},
        {"source_url": "not a url"},
        {"status": "READ"},
        {"status": None},
        {"oshi_ids": None},
        {"oshi_ids": [999]},
        {"oshi_ids": [1, 1]},
        {"oshi_ids": [True]},
        {"oshi_ids": [-1]},
        {"start_date": "2026-10-10", "end_date": "2026-10-01"},
        {"published_at": "2026-09-12T10:00:00"},
        {"deadline": "2026-09-12"},
        {"location": " "},
        {"relevance_score": 100},
        {"created_at": "2026-09-12T00:00:00Z"},
        {"unknown": "field"},
    ],
)
def test_invalid_update_create_and_patch_are_atomic(client, make_update, body):
    update = make_update()
    create_body = {
        "title": "Valid",
        "category": "NEWS",
        "source": "Demo",
        "source_url": "https://example.invalid/valid",
        **body,
    }
    assert client.post("/api/updates", json=create_body).status_code == 422
    assert client.patch(f"/api/updates/{update['id']}", json=body).status_code == 422
    assert client.get("/api/updates").json() == [update]


def test_patch_validates_dates_against_existing_record(client, make_update):
    update = make_update(start_date="2026-10-01", end_date="2026-10-10")
    path = f"/api/updates/{update['id']}"
    assert client.patch(path, json={"start_date": "2026-10-11"}).status_code == 422
    assert client.patch(path, json={"end_date": "2026-09-30"}).status_code == 422
    assert client.get(path).json() == update
    cleared = client.patch(path, json={"start_date": "2026-10-11", "end_date": None})
    assert cleared.status_code == 200
    assert cleared.json()["end_date"] is None


def test_filter_combinations_pagination_and_no_duplicate_rows(client, make_oshi, make_update):
    first = make_oshi()
    second = make_oshi(name="Ryujin", type="IDOL", keywords=[])
    high = make_update(
        title="ナヒーダ merch",
        category="MERCH",
        status="SAVED",
        oshi_ids=[first["id"], second["id"]],
        deadline="2026-10-01T00:00:00Z",
    )
    middle = make_update(category="NEWS", status="NEW", oshi_ids=[first["id"]])
    low = make_update(category="NEWS", status="SAVED")
    assert [x["id"] for x in client.get("/api/updates").json()] == [
        high["id"],
        middle["id"],
        low["id"],
    ]
    assert client.get("/api/updates", params={"oshi": second["id"]}).json() == [high]
    assert client.get("/api/updates", params={"category": "MERCH"}).json() == [high]
    assert client.get("/api/updates", params={"status": "NEW"}).json() == [middle]
    assert high["relevance_score"] == 95
    assert client.get("/api/updates", params={"min_score": 95}).json() == [high]
    combined = {"oshi": first["id"], "category": "MERCH", "status": "SAVED", "min_score": 95}
    assert client.get("/api/updates", params=combined).json() == [high]
    assert client.get("/api/updates", params={**combined, "min_score": 96}).json() == []
    assert client.get("/api/updates", params={"oshi": 999}).json() == []
    assert client.get("/api/updates", params={"limit": 1, "offset": 1}).json() == [middle]
    assert client.get("/api/updates", params={"offset": 100}).json() == []


@pytest.mark.parametrize(
    "query",
    [
        {"oshi": -1},
        {"oshi": "name"},
        {"min_score": -1},
        {"min_score": 101},
        {"min_score": "40.5"},
        {"min_score": "40.0"},
        {"category": "news"},
        {"status": "READ"},
        {"limit": 0},
        {"limit": 201},
        {"offset": -1},
        {"unexpected": "yes"},
    ],
)
def test_invalid_filters(client, query):
    assert client.get("/api/updates", params=query).status_code == 422


def test_missing_update_and_invalid_status_patch(client, make_update):
    assert client.get("/api/updates/999").status_code == 404
    assert client.patch("/api/updates/999", json={"title": "Missing"}).status_code == 404
    assert client.patch("/api/updates/999/status", json={"status": "SAVED"}).status_code == 404
    update = make_update()
    path = f"/api/updates/{update['id']}/status"
    for payload in ({}, {"status": None}, {"status": "READ"}, {"status": "SAVED", "title": "Oops"}):
        assert client.patch(path, json=payload).status_code == 422
