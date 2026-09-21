"""CLI safety tests, collected with the existing backend pytest configuration."""

import importlib.util
import json
import os
import shutil
import signal
import socket
import socketserver
import subprocess
import sys
import threading
import time
from pathlib import Path
from unittest.mock import Mock

import pytest

pytest.importorskip("fcntl", reason="macOS service ownership and locking require POSIX")

SPEC = importlib.util.spec_from_file_location("oshi_cli", Path(__file__).parents[1] / "oshi.py")
cli = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(cli)


@pytest.fixture
def dashboard(tmp_path):
    root = tmp_path / "Oshi Dashboard"
    root.mkdir()
    return cli.Dashboard(root)


def state_for(dashboard, pid=999999):
    member = {
        "pid": pid,
        "pgid": pid,
        "ppid": 1,
        "uid": os.getuid(),
        "born": "Sat Sep 12 00:00:00 2026",
        "command": f"python {dashboard.root}/scripts/oshi.py _serve backend token",
    }
    return {
        "version": 1,
        "root": str(dashboard.root),
        "service": "backend",
        "pgid": pid,
        "token": "token",
        "members": [member],
        "environment": {},
    }


def test_cli_starts_without_macos_proxy_support():
    # A fresh interpreter catches imports that pytest or its plugins may have cached.
    code = """
import runpy
import sys

class BlockProxyImport:
    def find_spec(self, fullname, path=None, target=None):
        if fullname == '_scproxy':
            raise AssertionError('CLI startup must not load macOS proxy support')

sys.meta_path.insert(0, BlockProxyImport())
sys.argv = [sys.argv[1], '--help']
runpy.run_path(sys.argv[0], run_name='__main__')
"""
    result = subprocess.run(
        [sys.executable, "-c", code, str(Path(cli.__file__))],
        capture_output=True,
        text=True,
        timeout=5,
        check=True,
    )
    assert "status" in result.stdout


@pytest.fixture
def probe_server(monkeypatch):
    class Handler(socketserver.StreamRequestHandler):
        def handle(self):
            self.server.requests.append(self.rfile.readline())
            while self.rfile.readline() not in (b"\r\n", b"\n", b""):
                pass
            self.wfile.write(self.server.response)

    with socketserver.TCPServer(("127.0.0.1", 0), Handler) as server:
        server.requests = []
        server.response = b""
        monkeypatch.setattr(cli, "SERVICES", dict.fromkeys(cli.SERVICES, server.server_address[1]))
        thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.01})
        thread.start()
        try:
            yield server
        finally:
            server.shutdown()
            thread.join(timeout=3)


@pytest.mark.parametrize(
    ("service", "response", "ready"),
    [
        (
            "backend",
            b'HTTP/1.0 200 OK\r\n\r\n{"total_oshi":0,"total_updates":0,"by_status":{}}',
            True,
        ),
        ("frontend", b"HTTP/1.0 200 OK\r\n\r\n<title>Oshi Dashboard</title>", True),
        ("backend", b"HTTP/1.0 200 OK\r\n\r\nnot json", False),
        ("backend", b"HTTP/1.0 200 OK\r\n\r\n[]", False),
        ("backend", b'HTTP/1.0 200 OK\r\n\r\n{"total_oshi":0}', False),
        ("frontend", b"HTTP/1.0 200 OK\r\n\r\n<title>Unrelated app</title>", False),
        ("frontend", b"HTTP/1.0 503 Unavailable\r\n\r\n<title>Oshi Dashboard</title>", False),
        (
            "frontend",
            b"HTTP/1.0 302 Found\r\nLocation: /redirected\r\n\r\n<title>Oshi Dashboard</title>",
            False,
        ),
        ("frontend", b"not an HTTP response\r\n\r\n", False),
        ("frontend", b"HTTP/1.1 200 OK\r\nTransfer-Encoding: chunked\r\n\r\ninvalid\r\n", False),
    ],
)
def test_http_readiness_uses_direct_local_responses(
    probe_server, monkeypatch, service, response, ready
):
    # Bad proxy settings must never affect localhost readiness.
    for key in ("http_proxy", "https_proxy", "all_proxy", "HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY"):
        monkeypatch.setenv(key, "http://127.0.0.1:1")
    for key in ("no_proxy", "NO_PROXY"):
        monkeypatch.setenv(key, "")
    probe_server.response = response
    assert cli.http_ready(service) is ready
    path = "/api/stats" if service == "backend" else "/"
    assert probe_server.requests == [f"GET {path} HTTP/1.1\r\n".encode()]


def test_http_readiness_handles_refused_connection(monkeypatch):
    with socket.socket() as unavailable:
        unavailable.bind(("127.0.0.1", 0))
        monkeypatch.setitem(cli.SERVICES, "backend", unavailable.getsockname()[1])
        assert not cli.http_ready("backend")


def test_http_readiness_times_out_without_a_response(monkeypatch):
    with socket.socket() as silent:
        silent.bind(("127.0.0.1", 0))
        silent.listen()
        monkeypatch.setitem(cli.SERVICES, "backend", silent.getsockname()[1])
        started = time.monotonic()
        assert not cli.http_ready("backend")
        assert time.monotonic() - started < 4
        connection, _ = silent.accept()
        with connection:
            connection.settimeout(1)
            while connection.recv(4096):
                pass  # The timed-out client must close its connection.


@pytest.mark.parametrize("content", ["not json", "[]", '{"version": 1}'])
def test_invalid_state_is_removed_without_signals(dashboard, monkeypatch, content):
    dashboard.state_path("backend").write_text(content)
    kill = Mock()
    monkeypatch.setattr(cli.os, "killpg", kill)
    dashboard.stop_service("backend")
    assert not dashboard.state_path("backend").exists()
    kill.assert_not_called()


def test_stale_pid_is_removed_without_signals(dashboard, monkeypatch):
    cli.write_json(dashboard.state_path("backend"), state_for(dashboard))
    kill = Mock()
    monkeypatch.setattr(cli.os, "killpg", kill)
    dashboard.stop_service("backend")
    assert not dashboard.state_path("backend").exists()
    kill.assert_not_called()


def test_reused_pid_and_unrelated_process_are_not_owned(dashboard):
    state = state_for(dashboard, os.getpid())
    actual = cli.processes()[os.getpid()]
    assert dashboard.owned(state, {os.getpid(): actual}) == []
    # Even an exact current identity is insufficient without the supervisor marker.
    state["members"] = [actual]
    assert dashboard.owned(state, {os.getpid(): actual}) == []
    assert not cli.same_process({**actual, "born": "different birth"}, actual)


def test_verified_surviving_child_can_recover_a_dead_supervisor(dashboard):
    state = state_for(dashboard)
    child = {**state["members"][0], "pid": 999998, "command": "next-server"}
    state["members"].append(child)
    assert dashboard.owned(state, {child["pid"]: child}) == [child]
    assert dashboard.owned(state, {child["pid"]: {**child, "born": "reused"}}) == []


def test_concurrent_commands_do_not_share_the_lock(dashboard):
    with dashboard.lock():
        with pytest.raises(cli.CliError, match="Another oshi command"):
            with cli.Dashboard(dashboard.root).lock():
                pytest.fail("lock should exclude the second caller")
    with dashboard.lock():
        pass


def test_external_port_conflict_never_launches_or_stops(dashboard, monkeypatch):
    monkeypatch.setattr(dashboard, "check_dependencies", lambda: None)
    monkeypatch.setattr(cli, "listener_pids", lambda port: {456} if port == 3000 else set())
    launch, stop = Mock(), Mock()
    monkeypatch.setattr(dashboard, "launch", launch)
    monkeypatch.setattr(dashboard, "stop_service", stop)
    with pytest.raises(cli.CliError, match="not owned"):
        dashboard.start()
    launch.assert_not_called()
    stop.assert_not_called()


@pytest.mark.parametrize("failure", [cli.CliError("startup failed"), KeyboardInterrupt()])
def test_failed_or_cancelled_start_rolls_back_only_new_services(dashboard, monkeypatch, failure):
    monkeypatch.setattr(dashboard, "check_dependencies", lambda: None)
    monkeypatch.setattr(dashboard, "ensure_no_external", lambda: None)
    monkeypatch.setattr(
        dashboard, "inspect", lambda name: (None, []) if name == "frontend" else ({}, [{}])
    )
    monkeypatch.setattr(dashboard, "ready", lambda *args: True)
    monkeypatch.setattr(dashboard, "launch", Mock(side_effect=failure))
    stop = Mock()
    monkeypatch.setattr(dashboard, "stop_service", stop)
    with pytest.raises(type(failure)):
        dashboard.start()
    stop.assert_called_once_with("frontend")


def test_failed_verification_restores_the_previous_database(dashboard, monkeypatch):
    environment = {"OSHI_DATABASE_PATH": str(dashboard.root / "my database.db")}
    monkeypatch.setattr(dashboard, "check_dependencies", lambda: None)
    monkeypatch.setattr(dashboard, "ensure_no_external", lambda: None)
    monkeypatch.setattr(
        dashboard,
        "inspect",
        lambda name: ({"environment": environment}, [{}]) if name == "backend" else (None, []),
    )
    monkeypatch.setattr(dashboard, "stop", lambda: None)
    monkeypatch.setattr(cli, "run_check", lambda *args: 7)
    start = Mock()
    monkeypatch.setattr(dashboard, "start", start)
    assert dashboard.tests() == 7
    start.assert_called_once_with(["backend"], {"backend": environment})


def test_stopped_open_does_not_start_or_open(dashboard, monkeypatch):
    monkeypatch.setattr(cli, "http_ready", lambda service: False)
    run = Mock()
    monkeypatch.setattr(cli.subprocess, "run", run)
    with pytest.raises(cli.CliError, match="oshi kaishi"):
        dashboard.open_browser()
    run.assert_not_called()


def test_wrapper_quotes_paths_and_refuses_unrelated_command(tmp_path, monkeypatch):
    root = tmp_path / "Oshi's Dashboard $(ignored)"
    (root / "scripts").mkdir(parents=True)
    (root / "scripts/oshi.py").write_text("import json, sys; print(json.dumps(sys.argv[1:]))")
    target = tmp_path / "local bin"
    monkeypatch.setattr(cli, "ROOT", root)
    monkeypatch.setenv("OSHI_BIN_DIR", str(target))
    assert cli.install() == 0
    result = subprocess.run(
        [str(target / "oshi"), "argument with spaces", "$(literal)"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=True,
    )
    assert json.loads(result.stdout) == ["argument with spaces", "$(literal)"]
    assert cli.install() == 0
    (target / "oshi").write_text("#!/bin/sh\necho unrelated\n")
    with pytest.raises(cli.CliError, match="unrelated command"):
        cli.install()


def test_check_cleanup_includes_detached_grandchildren(tmp_path):
    pid_path = tmp_path / "grandchild.pid"
    # The job exits with a deliberately leaked child in a separate session.
    code = (
        "import subprocess, sys, time; from pathlib import Path; "
        "p = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(30)'], "
        "start_new_session=True); "
        f"Path({str(pid_path)!r}).write_text(str(p.pid)); time.sleep(0.5)"
    )
    assert cli.run_check([sys.executable, "-c", code], tmp_path) == 0
    pid = int(pid_path.read_text())
    try:
        assert pid not in cli.processes()
    finally:
        if pid in cli.processes():
            os.kill(pid, signal.SIGKILL)


@pytest.mark.parametrize("kill_supervisor", [False, True])
def test_real_service_group_shutdown_and_orphan_recovery(dashboard, kill_supervisor):
    scripts = dashboard.root / "scripts"
    scripts.mkdir()
    shutil.copyfile(Path(__file__).parents[1] / "oshi.py", scripts / "oshi.py")
    service = scripts / "dev-backend.sh"
    service.write_text(
        "#!/usr/bin/env python3\nimport subprocess, sys, time\n"
        "subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(30)'])\n"
        "time.sleep(30)\n"
    )
    service.chmod(0o755)
    dashboard.launch("backend")
    state = None
    try:
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            state = dashboard.state("backend")
            if len(state["members"]) >= 3:
                break
            time.sleep(0.1)
        assert len(state["members"]) >= 3
        group = state["pgid"]
        if kill_supervisor:
            os.kill(group, signal.SIGKILL)
            time.sleep(0.1)
        started = time.monotonic()
        dashboard.stop_service("backend")
        assert time.monotonic() - started < cli.STOP_TIMEOUT
        assert not [p for p in cli.processes().values() if p["pgid"] == group]
        assert not dashboard.state_path("backend").exists()
    finally:
        dashboard.stop_service("backend")


def test_stubborn_owned_process_escalates_after_grace_period(dashboard, monkeypatch, capsys):
    scripts = dashboard.root / "scripts"
    scripts.mkdir()
    shutil.copyfile(Path(__file__).parents[1] / "oshi.py", scripts / "oshi.py")
    service = scripts / "dev-backend.sh"
    service.write_text(
        "#!/usr/bin/env python3\nimport signal, time\n"
        "signal.signal(signal.SIGTERM, signal.SIG_IGN)\ntime.sleep(30)\n"
    )
    service.chmod(0o755)
    dashboard.launch("backend")
    try:
        time.sleep(1)
        monkeypatch.setattr(cli, "STOP_TIMEOUT", 0.3)
        dashboard.stop_service("backend")
        assert "did not stop gracefully" in capsys.readouterr().out
        assert not dashboard.state_path("backend").exists()
    finally:
        dashboard.stop_service("backend")


def test_fetch_uses_only_backend_python_and_forwards_flags(dashboard, monkeypatch):
    python = dashboard.root / "backend/.venv/bin/python"
    python.parent.mkdir(parents=True)
    python.touch()
    child = Mock()
    child.wait.return_value = 1
    launch = Mock(return_value=child)
    monkeypatch.setattr(cli.subprocess, "Popen", launch)
    monkeypatch.setattr(dashboard, "check_dependencies", Mock(side_effect=AssertionError))
    monkeypatch.setattr(dashboard, "ensure_no_external", Mock(side_effect=AssertionError))
    assert dashboard.fetch(dry_run=True, source="anime") == 1
    launch.assert_called_once_with(
        [str(python), "-m", "app.ingestion", "--dry-run", "--source", "anime"],
        cwd=dashboard.root,
    )


@pytest.mark.parametrize(
    "args", [["status", "--dry-run"], ["start", "--source", "rss"], ["fetch", "--source", ""]]
)
def test_fetch_flags_require_fetch_and_a_nonempty_source(args):
    with pytest.raises(SystemExit) as error:
        cli.main(args)
    assert error.value.code == 2


def test_cancelled_fetch_cleans_its_child_even_if_interrupt_is_ignored(dashboard, monkeypatch):
    python = dashboard.root / "backend/.venv/bin/python"
    python.parent.mkdir(parents=True)
    python.touch()
    child = Mock()
    child.poll.return_value = None
    child.wait.side_effect = [
        KeyboardInterrupt(),
        subprocess.TimeoutExpired("fetch", 15),
        subprocess.TimeoutExpired("fetch", 5),
        0,
    ]
    monkeypatch.setattr(cli.subprocess, "Popen", Mock(return_value=child))
    with pytest.raises(KeyboardInterrupt):
        dashboard.fetch()
    child.send_signal.assert_called_once_with(signal.SIGINT)
    child.terminate.assert_called_once()
    child.kill.assert_called_once()
