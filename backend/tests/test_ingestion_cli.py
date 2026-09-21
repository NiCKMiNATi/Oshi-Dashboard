import json
import os
import shutil
import sqlite3
import subprocess
import sys
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import create_app


def test_real_cli_fetch_without_services_then_api_reads_updates(tmp_path, rss_server):
    # An isolated CLI installation has no service state, frontend, Node, or running API.
    root = tmp_path / "Oshi Dashboard"
    (root / "scripts").mkdir(parents=True)
    (root / "backend").mkdir()
    (root / "backend/.venv").symlink_to(sys.prefix, target_is_directory=True)
    script = root / "scripts/oshi.py"
    shutil.copyfile(Path(__file__).parents[2] / "scripts/oshi.py", script)
    database = root / "personal.db"
    with TestClient(create_app(database), base_url="http://127.0.0.1") as client:
        tracked = client.post("/api/oshi", json={"name": "原神", "type": "GAME"}).json()
    # The TestClient/server is now stopped. Only the fixture publisher serves HTTP.
    rss_server.responses["/feed"] = (
        200,
        {},
        """<rss version="2.0"><channel><title>Fixture</title>
    <item><guid isPermaLink="false">id-1</guid><title>[DEMO] 原神 announcement</title>
    <description>Fictional CLI acceptance fixture</description>
    <link>https://example.invalid/cli-article</link></item></channel></rss>""".encode(),
    )
    sources = root / "sources.json"
    sources.write_text(
        json.dumps(
            {
                "sources": [
                    {
                        "key": "selected",
                        "url": rss_server.url + "/feed",
                        "name": "Fictional test publisher",
                    },
                    {"key": "not-selected", "url": rss_server.url + "/must-not-request"},
                ]
            }
        )
    )
    environment = {
        **os.environ,
        "OSHI_DATABASE_PATH": str(database),
        "OSHI_SOURCES_PATH": str(sources),
    }

    def fetch(*flags):
        return subprocess.run(
            [sys.executable, str(script), "fetch", "--source", "selected", *flags],
            cwd=tmp_path,
            env=environment,
            text=True,
            capture_output=True,
            timeout=15,
        )

    original = database.read_bytes()
    dry = fetch("--dry-run")
    assert dry.returncode == 0, dry.stderr
    assert "New updates       1" in dry.stdout
    assert database.read_bytes() == original
    first = fetch()
    assert first.returncode == 0, first.stderr
    assert "New updates       1" in first.stdout
    second = fetch()
    assert second.returncode == 0, second.stderr
    assert "Duplicates        1" in second.stdout
    assert "New updates       0" in second.stdout
    assert all(path == "/feed" for path, _ in rss_server.requests)
    assert not (root / ".runtime/backend.json").exists()
    assert not (root / ".runtime/frontend.json").exists()
    with TestClient(create_app(database), base_url="http://127.0.0.1") as client:
        updates = client.get("/api/updates").json()
        assert len(updates) == 1
        assert updates[0]["oshi_ids"] == [tracked["id"]]
        assert updates[0]["relevance_score"] == 40
        assert updates[0]["status"] == "NEW"
    with sqlite3.connect(database) as connection:
        assert connection.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        assert connection.execute("PRAGMA foreign_key_check").fetchall() == []
