import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

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


@pytest.fixture
def rss_server():
    """Local HTTP feed fixture; never contacts a real provider or dashboard port."""

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.server.requests.append((self.path, dict(self.headers)))
            status, headers, body = self.server.responses.get(self.path, (404, {}, b""))
            if self.headers.get("If-None-Match") == headers.get("ETag") and "ETag" in headers:
                status, body = 304, b""
            self.send_response(status)
            for key, value in headers.items():
                self.send_header(key, value)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args):
            pass

    with ThreadingHTTPServer(("127.0.0.1", 0), Handler) as server:
        server.requests = []
        server.responses = {}
        server.url = f"http://127.0.0.1:{server.server_port}"
        thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.01})
        thread.start()
        try:
            yield server
        finally:
            server.shutdown()
            thread.join(timeout=3)
