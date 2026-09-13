def test_openapi_exposes_all_requested_routes(client):
    response = client.get("/openapi.json")
    assert response.status_code == 200
    paths = response.json()["paths"]
    assert {path: set(methods) for path, methods in paths.items()} == {
        "/api/oshi": {"get", "post"},
        "/api/oshi/{oshi_id}": {"patch", "delete"},
        "/api/updates": {"get", "post"},
        "/api/updates/{update_id}": {"get", "patch"},
        "/api/updates/{update_id}/status": {"patch"},
        "/api/stats": {"get"},
        "/api/discover": {"get"},
        "/api/discover/{entity_id}/track": {"post"},
    }


def test_localhost_cors_and_host_validation(client):
    preflight = {
        "Origin": "http://127.0.0.1:3000",
        "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "Content-Type",
    }
    response = client.options("/api/oshi", headers=preflight)
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://127.0.0.1:3000"
    denied = client.options("/api/oshi", headers={**preflight, "Origin": "https://example.com"})
    assert denied.status_code == 400
    assert "access-control-allow-origin" not in denied.headers
    assert client.get("/api/oshi", headers={"Host": "example.com"}).status_code == 400
