from app.models import UpdateCategory, UpdateStatus


def test_empty_stats_include_all_enum_buckets(client):
    assert client.get("/api/stats").json() == {
        "total_oshi": 0,
        "active_oshi": 0,
        "total_updates": 0,
        "by_category": {value: 0 for value in UpdateCategory},
        "by_status": {value: 0 for value in UpdateStatus},
    }


def test_stats_count_updates_once_and_track_mutations(client, make_oshi, make_update):
    first = make_oshi()
    second = make_oshi(name="Ryujin", type="IDOL", active=False)
    update = make_update(category="MERCH", oshi_ids=[first["id"], second["id"]])
    make_update(category="NEWS", status="IGNORED")
    stats = client.get("/api/stats").json()
    assert (stats["total_oshi"], stats["active_oshi"], stats["total_updates"]) == (2, 1, 2)
    assert stats["by_status"]["NEW"] == 1
    assert stats["by_status"]["IGNORED"] == 1
    assert stats["by_category"]["MERCH"] == 1
    assert sum(stats["by_category"].values()) == 2
    client.patch(f"/api/updates/{update['id']}/status", json={"status": "BOUGHT"})
    client.delete(f"/api/oshi/{first['id']}")
    changed = client.get("/api/stats").json()
    assert changed["total_oshi"] == 1
    assert changed["active_oshi"] == 0
    assert changed["total_updates"] == 2
    assert changed["by_status"]["NEW"] == 0
    assert changed["by_status"]["BOUGHT"] == 1
