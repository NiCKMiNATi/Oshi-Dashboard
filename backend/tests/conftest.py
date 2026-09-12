import pytest
from fastapi.testclient import TestClient

from app.main import create_app


@pytest.fixture
def application(tmp_path):
    return create_app(tmp_path / "isolated" / "test.db")


@pytest.fixture
def client(application):
    with TestClient(application, base_url="http://127.0.0.1") as client:
        yield client


@pytest.fixture
def make_oshi(client):
    def create(**overrides):
        response = client.post(
            "/api/oshi",
            json={
                "name": "原神",
                "type": "GAME",
                "keywords": [{"value": "ナヒーダ", "weight": 25}],
                **overrides,
            },
        )
        assert response.status_code == 201, response.text
        return response.json()

    return create


@pytest.fixture
def make_update(client):
    def create(**overrides):
        response = client.post(
            "/api/updates",
            json={
                "title": "Sample announcement",
                "category": "NEWS",
                "source": "Fictional test source",
                "source_url": "https://example.invalid/test",
                **overrides,
            },
        )
        assert response.status_code == 201, response.text
        return response.json()

    return create
