import errno
import json
import shutil
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from app.ingestion import __main__ as cli
from app.ingestion import runtime
from app.ingestion.runtime import background_log, fetch_lock


def test_concurrent_process_is_skipped_and_crash_releases_lock(tmp_path):
    code = """
import sys, time
from pathlib import Path
from app.ingestion.runtime import fetch_lock, FetchBusy
try:
    with fetch_lock(Path(sys.argv[1])):
        print('acquired', flush=True)
        if len(sys.argv) > 2:
            time.sleep(60)
except FetchBusy:
    print('busy', flush=True)
"""
    command = [sys.executable, "-c", code, str(tmp_path)]
    child = subprocess.Popen([*command, "hold"], stdout=subprocess.PIPE, text=True)
    try:
        assert child.stdout.readline().strip() == "acquired"
        result = subprocess.run(command, capture_output=True, text=True, timeout=10)
        assert result.returncode == 0
        assert result.stdout.strip() == "busy"
    finally:
        child.kill()
        child.wait(timeout=10)
        child.stdout.close()
    result = subprocess.run(command, capture_output=True, text=True, timeout=10)
    assert result.returncode == 0
    assert result.stdout.strip() == "acquired"
    assert (tmp_path / "ingestion.lock").exists()


@pytest.fixture
def isolated_cli(tmp_path, monkeypatch):
    monkeypatch.setattr(cli, "ROOT_DIR", tmp_path)
    database = tmp_path / "untouched.db"
    sources = tmp_path / "sources.json"
    monkeypatch.setenv("OSHI_DATABASE_PATH", str(database))
    monkeypatch.setenv("OSHI_SOURCES_PATH", str(sources))
    return tmp_path, database, sources


def test_no_sources_background_logs_counts_and_does_not_create_db(isolated_cli):
    root, database, _ = isolated_cli
    assert cli.main(["--background"]) == 0
    log = (root / ".runtime/background-fetch.log").read_text()
    assert "Z Fetch started" in log
    assert "Sources checked   0" in log
    assert "Fetch ended: result=0 duration=" in log
    assert not database.exists()


def test_busy_entrypoint_never_fetches_or_rotates_log(isolated_cli, monkeypatch, capsys):
    root, database, _ = isolated_cli

    def forbidden(*args):
        pytest.fail("Concurrent fetch must not start")

    monkeypatch.setattr(cli, "fetch", forbidden)
    with fetch_lock(root / ".runtime"):
        assert cli.main(["--background"]) == 0
        assert cli.main([]) == 0
    assert "already running" in capsys.readouterr().err
    assert not database.exists()
    assert not (root / ".runtime/background-fetch.log").exists()


def test_failure_logs_no_secrets_and_next_invocation_runs(isolated_cli, monkeypatch):
    root, _, sources = isolated_cli

    def fail(args):
        raise RuntimeError("https://secret.invalid/?token=private")

    with monkeypatch.context() as patch:
        patch.setattr(cli, "fetch", fail)
        assert cli.main(["--background"]) == 1
    sources.write_text('{"invalid":"https://secret.invalid/?token=private"}')
    assert cli.main(["--background"]) == 1
    sources.write_text('{"sources":[]}')
    assert cli.main(["--background"]) == 0
    log = (root / ".runtime/background-fetch.log").read_text()
    assert "Fatal fetch error (RuntimeError)" in log
    assert "Invalid source configuration" in log
    assert "result=1" in log and "result=0" in log
    assert "secret.invalid" not in log and "token=private" not in log


def test_explicit_scheduler_paths_override_environment(isolated_cli, monkeypatch):
    root, _, _ = isolated_cli
    explicit = root / "explicit.json"
    explicit.write_text(
        json.dumps({"sources": [{"key": "fixture", "url": "https://example.invalid/feed"}]})
    )

    def run(database, adapters, dry_run):
        assert database == root / "scheduled.db"
        assert len(adapters) == 1
        raise OSError("private detail")

    monkeypatch.setattr(cli, "run_fetch", run)
    assert (
        cli.main(
            [
                "--background",
                "--database-path",
                str(root / "scheduled.db"),
                "--sources-path",
                str(explicit),
            ]
        )
        == 1
    )
    assert "private detail" not in (root / ".runtime/background-fetch.log").read_text()


def test_logs_rotate_with_bounded_retention(tmp_path):
    with fetch_lock(tmp_path), background_log(tmp_path):
        for _ in range(1400):
            print("x" * 4096)
    logs = list(tmp_path.glob("background-fetch.log*"))
    assert len(logs) == 4
    assert all(path.stat().st_size <= 1_048_576 for path in logs)


def test_windows_lock_uses_nonblocking_byte_range_and_releases(tmp_path, monkeypatch):
    msvcrt = SimpleNamespace(LK_NBLCK=2, LK_UNLCK=0, locking=Mock())
    monkeypatch.setitem(sys.modules, "msvcrt", msvcrt)
    monkeypatch.setattr(runtime, "os", SimpleNamespace(name="nt"))
    with fetch_lock(tmp_path):
        assert msvcrt.locking.call_args.args[1:] == (2, 1)
    assert msvcrt.locking.call_args.args[1:] == (0, 1)
    msvcrt.locking.side_effect = OSError(errno.EACCES, "busy")
    with pytest.raises(runtime.FetchBusy):
        with fetch_lock(tmp_path):
            pytest.fail("Busy lock must not be acquired")
    msvcrt.locking.side_effect = OSError(errno.EIO, "disk failure")
    with pytest.raises(OSError):
        with fetch_lock(tmp_path):
            pytest.fail("I/O failure must not be treated as a successful skip")


def test_log_write_failure_is_nonzero_and_releases_lock(isolated_cli, monkeypatch, capsys):
    root, database, _ = isolated_cli

    def fail(*args):
        raise OSError("sensitive disk detail")

    monkeypatch.setattr(runtime.FetchLogHandler, "shouldRollover", fail)
    assert cli.main(["--background"]) == 1
    output = capsys.readouterr().err
    assert "Cannot open fetch lock/log" in output
    assert "sensitive" not in output and "Traceback" not in output
    with fetch_lock(root / ".runtime"):
        assert not database.exists()


def test_bootstrap_failure_is_logged_without_secrets(tmp_path):
    repository = Path(__file__).parents[2]
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    shutil.copyfile(repository / "scripts/background_fetch.py", scripts / "background_fetch.py")
    package = tmp_path / "backend/app/ingestion"
    package.mkdir(parents=True)
    (package.parent / "__init__.py").touch()
    (package / "__init__.py").touch()
    shutil.copyfile(repository / "backend/app/ingestion/runtime.py", package / "runtime.py")
    (package / "__main__.py").write_text("raise ImportError('secret-token')")
    result = subprocess.run(
        [sys.executable, str(scripts / "background_fetch.py")],
        cwd=scripts,
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 1
    log = (tmp_path / ".runtime/background-fetch.log").read_text()
    assert "Fatal startup error (ImportError)" in log
    assert "result=1" in log
    assert "secret-token" not in log + result.stdout + result.stderr
