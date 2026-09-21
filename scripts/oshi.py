#!/usr/bin/env python3
"""Local macOS service control. Python standard library only."""

from __future__ import annotations

import argparse
import contextlib
import fcntl
import http.client
import json
import os
import shlex
import shutil
import signal
import subprocess
import sys
import time
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SERVICES = {"backend": 8000, "frontend": 3000}
LABELS = {"backend": "API", "frontend": "Frontend"}
START_TIMEOUT = 45
STOP_TIMEOUT = 10
WRAPPER_MARKER = "# Oshi Dashboard CLI wrapper v1"
COMMANDS = {
    "start": "start",
    "kaishi": "start",
    "end": "stop",
    "stop": "stop",
    "shuuryou": "stop",
    "restart": "restart",
    "saikidou": "restart",
    "status": "status",
    "open": "open",
    "hiraku": "open",
    "test": "test",
    "fetch": "fetch",
}


class CliError(Exception):
    pass


def processes() -> dict[int, dict]:
    """PID alone is never ownership: record birth time, uid, group and command."""
    result = subprocess.run(
        ["/bin/ps", "-axo", "pid=,pgid=,ppid=,uid=,lstart=,stat=,command="],
        capture_output=True,
        text=True,
        check=True,
        env={**os.environ, "LC_ALL": "C"},
    )
    rows = {}
    for line in result.stdout.splitlines():
        fields = line.split(None, 10)
        if (
            len(fields) != 11
            or "Z" in fields[9]
            or fields[10].startswith("/bin/ps -axo pid=,pgid=,ppid=,uid=,lstart=,stat=,command=")
        ):
            continue
        pid, pgid, ppid, uid = map(int, fields[:4])
        rows[pid] = {
            "pid": pid,
            "pgid": pgid,
            "ppid": ppid,
            "uid": uid,
            "born": " ".join(fields[4:9]),
            "command": fields[10].rstrip(),
        }
    return rows


def same_process(saved: dict, current: dict | None) -> bool:
    return (
        bool(current)
        and all(
            saved.get(key) == current.get(key) for key in ("pid", "pgid", "uid", "born", "command")
        )
        and current["uid"] == os.getuid()
    )


def descendants(pid: int, rows: dict[int, dict]) -> list[dict]:
    found = {pid}
    while True:
        expanded = found | {p["pid"] for p in rows.values() if p["ppid"] in found}
        if expanded == found:
            return [p for p in rows.values() if p["pid"] in found]
        found = expanded


def listener_pids(port: int) -> set[int]:
    result = subprocess.run(
        ["/usr/sbin/lsof", "-nP", f"-iTCP:{port}", "-sTCP:LISTEN", "-Fp"],
        capture_output=True,
        text=True,
    )
    if result.returncode not in (0, 1) or result.stderr.strip():
        raise CliError(f"Cannot inspect port {port}: {result.stderr.strip()}")
    return {int(line[1:]) for line in result.stdout.splitlines() if line.startswith("p")}


def http_ready(service: str) -> bool:
    path = "/api/stats" if service == "backend" else "/"
    # Direct loopback probes avoid urllib.request's macOS _scproxy import entirely.
    connection = http.client.HTTPConnection("127.0.0.1", SERVICES[service], timeout=2)
    try:
        connection.request("GET", path)
        with connection.getresponse() as response:
            if response.status != 200:
                return False
            body = response.read(512_000)
            if service == "backend":
                data = json.loads(body)
                return isinstance(data, dict) and all(
                    key in data for key in ("total_oshi", "total_updates", "by_status")
                )
            return b"<title>Oshi Dashboard</title>" in body
    except (OSError, http.client.HTTPException, ValueError):
        return False
    finally:
        connection.close()


def write_json(path: Path, value: dict) -> None:
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        with temporary.open("w", encoding="utf-8") as stream:
            json.dump(value, stream)
            stream.write("\n")
        temporary.chmod(0o600)
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


@contextlib.contextmanager
def finish_cleanup():
    """A second Ctrl+C must not interrupt an already requested shutdown."""
    previous = signal.signal(signal.SIGINT, signal.SIG_IGN)
    try:
        yield
    finally:
        signal.signal(signal.SIGINT, previous)


class Dashboard:
    def __init__(self, root: Path = ROOT):
        self.root = root.resolve()
        self.runtime = self.root / ".runtime"
        self.runtime.mkdir(mode=0o700, exist_ok=True)
        self.children: dict[str, subprocess.Popen] = {}

    @contextlib.contextmanager
    def lock(self):
        # Never unlink this file: a stable inode is needed for concurrent callers.
        with (self.runtime / "cli.lock").open("a") as stream:
            try:
                fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as error:
                raise CliError(
                    "Another oshi command is running. Try again when it finishes."
                ) from error
            yield

    def state_path(self, service: str) -> Path:
        return self.runtime / f"{service}.json"

    def state(self, service: str) -> dict | None:
        path = self.state_path(service)
        try:
            data = json.loads(path.read_text())
            if (
                data["version"] != 1
                or data["root"] != str(self.root)
                or data["service"] != service
                or type(data["pgid"]) is not int
                or data["pgid"] <= 1
                or not isinstance(data["members"], list)
                or not all(isinstance(p, dict) for p in data["members"])
                or not isinstance(data["environment"], dict)
                or not isinstance(data["token"], str)
            ):
                raise ValueError("invalid service state")
            return data
        except FileNotFoundError:
            return None
        except (ValueError, KeyError, TypeError):
            print(f"{LABELS[service]}: removed invalid state; no process was signalled.")
            path.unlink(missing_ok=True)
            return None

    def owned(self, state: dict, rows: dict[int, dict] | None = None) -> list[dict]:
        leader = next((p for p in state["members"] if p.get("pid") == state["pgid"]), {})
        marker = f"{self.root / 'scripts/oshi.py'} _serve {state['service']} {state['token']}"
        if not state["token"] or marker not in leader.get("command", ""):
            return []
        rows = processes() if rows is None else rows
        group = [p for p in rows.values() if p["pgid"] == state["pgid"]]
        verified = any(
            same_process(saved, rows.get(saved.get("pid"))) and saved.get("pgid") == state["pgid"]
            for saved in state["members"]
        )
        return group if verified else []

    def inspect(self, service: str) -> tuple[dict | None, list[dict]]:
        state = self.state(service)
        members = self.owned(state) if state else []
        if state and not members:
            print(f"{LABELS[service]}: removed stale PID state; no process was signalled.")
            self.state_path(service).unlink(missing_ok=True)
            state = None
        return state, members

    def ready(self, service: str, state: dict) -> bool:
        members = self.owned(state)
        pids = listener_pids(SERVICES[service])
        return bool(pids) and pids.issubset({p["pid"] for p in members}) and http_ready(service)

    def database_path(self) -> Path:
        state = self.state("backend")
        path = (
            (state or {})
            .get("environment", {})
            .get("OSHI_DATABASE_PATH", os.environ.get("OSHI_DATABASE_PATH", "data/oshi.db"))
        )
        expanded = Path(path).expanduser()
        return (self.root / expanded).resolve()

    def status(self) -> bool:
        print("OSHI Dashboard v0.1\n")
        healthy = True
        for service, port in SERVICES.items():
            state, members = self.inspect(service)
            listening = listener_pids(port)
            reachable = http_ready(service) if listening else False
            owned_listener = bool(listening) and listening.issubset({p["pid"] for p in members})
            if members:
                status = "running" if owned_listener and reachable else "running, not ready"
                detail = f"group {state['pgid']}; PIDs {','.join(str(p['pid']) for p in members)}"
            elif listening:
                status = "unmanaged listener"
                detail = (
                    f"PIDs {','.join(map(str, sorted(listening)))}; "
                    f"HTTP {'ready' if reachable else 'not ready'}"
                )
            else:
                status, detail = "stopped", "no owned process"
            ok = bool(members) and owned_listener and reachable
            healthy &= ok
            print(f"{LABELS[service]:10}{'✓' if ok else '–'} {status}  http://localhost:{port}")
            print(f"            {detail}")
        database = self.database_path()
        print(
            f"Database  {'✓' if database.is_file() else '–'} "
            f"SQLite {'exists' if database.is_file() else 'missing'}  {database}"
        )
        return healthy

    def check_dependencies(self) -> None:
        for path in ("backend/.venv/bin/python", "frontend/node_modules/next/package.json"):
            if not (self.root / path).is_file():
                raise CliError(f"Missing {path}. Run {self.root / 'scripts/setup.sh'} first.")
        if not shutil.which("npm") or not shutil.which("node"):
            raise CliError(
                "Node.js/npm are missing from PATH. Install Node.js and rerun install-cli.sh."
            )

    def fetch(self, *, dry_run: bool = False, source: str | None = None) -> int:
        python = self.root / "backend/.venv/bin/python"
        if not python.is_file():
            raise CliError(f"Missing {python}. Run scripts/setup.sh first.")
        command = [str(python), "-m", "app.ingestion"]
        if dry_run:
            command.append("--dry-run")
        if source:
            command.extend(["--source", source])
        # No service probes, Node dependency, or lifecycle changes. The child shares
        # the terminal so Ctrl+C rolls back its active database transaction normally.
        child = subprocess.Popen(command, cwd=self.root)
        try:
            return child.wait()
        except KeyboardInterrupt:
            with finish_cleanup():
                if child.poll() is None:
                    child.send_signal(signal.SIGINT)
                try:
                    child.wait(timeout=15)
                except subprocess.TimeoutExpired:
                    child.terminate()
                    try:
                        child.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        child.kill()
                        child.wait(timeout=5)
            raise

    def command(self, service: str) -> list[str]:
        if service == "backend":
            return [str(self.root / "scripts/dev-backend.sh")]
        return [
            shutil.which("npm") or "npm",
            "--prefix",
            str(self.root / "frontend"),
            "run",
            "dev",
            "--",
            "--port",
            "3000",
        ]

    def ensure_no_external(self) -> None:
        for service, port in SERVICES.items():
            _, members = self.inspect(service)
            external = listener_pids(port) - {p["pid"] for p in members}
            if external:
                raise CliError(
                    f"Port {port} is in use by processes not owned by oshi "
                    f"(PIDs {','.join(map(str, sorted(external)))}). "
                    "Stop them from their original terminal, then retry. Nothing was stopped."
                )

    def launch(self, service: str, environment: dict | None = None) -> None:
        environment = (
            environment
            if environment is not None
            else {
                key: os.environ[key]
                for key in ("OSHI_DATABASE_PATH", "NEXT_PUBLIC_API_URL")
                if key in os.environ
            }
        )
        if service == "backend":
            path = Path(environment.get("OSHI_DATABASE_PATH", "data/oshi.db")).expanduser()
            environment = {**environment, "OSHI_DATABASE_PATH": str((self.root / path).resolve())}
        token = uuid.uuid4().hex
        with (self.runtime / f"{service}.log").open("a", buffering=1) as log:
            log.write(f"\n--- {time.strftime('%Y-%m-%d %H:%M:%S %z')} start ---\n")
            # Block Ctrl+C across Popen + state publication so no child loses its owner record.
            previous = signal.pthread_sigmask(signal.SIG_BLOCK, {signal.SIGINT})
            child = None
            try:
                child = subprocess.Popen(
                    [
                        sys.executable,
                        "-u",
                        str(self.root / "scripts/oshi.py"),
                        "_serve",
                        service,
                        token,
                    ],
                    cwd=self.root,
                    env={**os.environ, **environment},
                    stdin=subprocess.DEVNULL,
                    stdout=log,
                    stderr=subprocess.STDOUT,
                    start_new_session=True,
                    close_fds=True,
                )
                self.children[service] = child
                identity = processes().get(child.pid)
                if not identity:
                    raise CliError(
                        f"{service} supervisor exited. See {self.runtime / (service + '.log')}"
                    )
                write_json(
                    self.state_path(service),
                    {
                        "version": 1,
                        "root": str(self.root),
                        "service": service,
                        "pgid": child.pid,
                        "token": token,
                        "members": [identity],
                        "environment": environment,
                    },
                )
            except BaseException:
                if child and child.poll() is None:
                    child.terminate()
                    child.wait(timeout=5)
                raise
            finally:
                signal.pthread_sigmask(signal.SIG_SETMASK, previous)

    def start(self, selected=None, environments=None) -> None:
        selected = list(SERVICES) if selected is None else selected
        self.check_dependencies()
        self.ensure_no_external()
        missing = []
        for service in selected:
            state, members = self.inspect(service)
            if members and not self.ready(service, state):
                raise CliError(
                    f"{LABELS[service]} has an owned process but is not ready. "
                    "Inspect its log or run oshi restart (oshi saikidou)."
                )
            if not members:
                missing.append(service)
        started = []
        try:
            for service in missing:
                started.append(service)
                self.launch(service, (environments or {}).get(service))
            deadline = time.monotonic() + START_TIMEOUT
            waiting = set(selected)
            while waiting:
                for service in list(waiting):
                    state, members = self.inspect(service)
                    if not members:
                        raise CliError(
                            f"{LABELS[service]} exited during startup. "
                            f"See {self.runtime / (service + '.log')}"
                        )
                    if self.ready(service, state):
                        waiting.remove(service)
                if waiting and time.monotonic() >= deadline:
                    raise CliError(
                        f"Readiness timed out for {', '.join(sorted(waiting))}. "
                        f"See {self.runtime}/*.log"
                    )
                if waiting:
                    time.sleep(0.2)
        except BaseException:
            with finish_cleanup():
                for service in reversed(started):
                    self.stop_service(service)
            raise

    def stop_service(self, service: str) -> None:
        state, members = self.inspect(service)
        if not members:
            self.reap(service)
            return
        print(f"Stopping {LABELS[service]}…", flush=True)
        # Revalidate before each signal, including escalation. Never kill by port/name.
        for sig, timeout in ((signal.SIGTERM, STOP_TIMEOUT), (signal.SIGKILL, 3)):
            if not self.owned(state):
                break
            if sig == signal.SIGKILL:
                print(f"{LABELS[service]} did not stop gracefully; terminating its owned group.")
            with contextlib.suppress(ProcessLookupError):
                os.killpg(state["pgid"], sig)
            deadline = time.monotonic() + timeout
            while self.owned(state) and time.monotonic() < deadline:
                time.sleep(0.1)
        if self.owned(state):
            raise CliError(f"Unable to stop {service}; retained its state for another attempt.")
        self.state_path(service).unlink(missing_ok=True)
        self.reap(service)

    def reap(self, service: str) -> None:
        child = self.children.get(service)
        if child and child.poll() is not None:
            self.children.pop(service)

    def stop(self) -> None:
        with finish_cleanup():
            for service in reversed(SERVICES):
                self.stop_service(service)

    def open_browser(self) -> None:
        if not all(http_ready(service) for service in SERVICES):
            raise CliError("Dashboard is not ready. Run oshi start (oshi kaishi) first.")
        subprocess.run(["/usr/bin/open", "http://localhost:3000"], check=True)

    def tests(self) -> int:
        self.check_dependencies()
        self.ensure_no_external()
        restore = {
            service: state["environment"]
            for service in SERVICES
            if (state := self.inspect(service)[0])
        }
        stages = [
            (
                "Backend + CLI tests",
                [str(self.root / "scripts/test-backend.sh"), str(self.root / "scripts/tests")],
            ),
            *[
                (
                    f"Frontend {stage}",
                    [shutil.which("npm"), "--prefix", str(self.root / "frontend"), "run", stage],
                )
                for stage in ("lint", "typecheck", "test:integration")
            ],
        ]
        try:
            self.stop()
            for label, command in stages:
                print(f"\n== {label} ==", flush=True)
                code = run_check(command, self.root)
                if code:
                    print(f"{label} failed (exit {code}).", flush=True)
                    return code
            print("\nAll verification checks passed.", flush=True)
            return 0
        finally:
            if restore:
                print("\nRestoring previously running CLI services…", flush=True)
                with finish_cleanup():
                    self.start(list(restore), restore)


def run_check(command: list[str], root: Path) -> int:
    """Track descendants too: Playwright creates separate groups for its servers."""
    child = subprocess.Popen(command, cwd=root, start_new_session=True)
    seen = {}
    try:
        while True:
            rows = processes()
            for process in descendants(child.pid, rows):
                seen[process["pid"]] = process
            code = child.poll()
            if code is not None:
                return code
            time.sleep(0.1)
    finally:
        with finish_cleanup():
            # Give the runner first chance to close its own servers on interruption.
            if child.poll() is None:
                child.send_signal(signal.SIGINT)
                try:
                    child.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    pass
            for sig, timeout in ((signal.SIGTERM, 5), (signal.SIGKILL, 2)):
                rows = processes()
                remaining = [p for p in seen.values() if same_process(p, rows.get(p["pid"]))]
                for process in reversed(remaining):
                    with contextlib.suppress(ProcessLookupError):
                        os.kill(process["pid"], sig)
                deadline = time.monotonic() + timeout
                while remaining and time.monotonic() < deadline:
                    time.sleep(0.1)
                    rows = processes()
                    remaining = [p for p in remaining if same_process(p, rows.get(p["pid"]))]
            child.wait(timeout=3)


def supervise(service: str, token: str) -> int:
    """Detached group leader stays alive until the service's children are gone."""
    signal.pthread_sigmask(signal.SIG_UNBLOCK, {signal.SIGINT})
    signal.signal(signal.SIGHUP, signal.SIG_IGN)
    stopping = False

    def request_stop(_signum, _frame):
        nonlocal stopping
        stopping = True

    signal.signal(signal.SIGTERM, request_stop)
    signal.signal(signal.SIGINT, request_stop)
    dashboard = Dashboard()
    # Parent publishes state before this process launches any service children.
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        state = dashboard.state(service)
        if state and state["token"] == token and state["pgid"] == os.getpid():
            break
        if stopping:
            return 0
        time.sleep(0.05)
    else:
        return 1
    child = subprocess.Popen(dashboard.command(service), cwd=ROOT, stdin=subprocess.DEVNULL)
    shutdown_at = None
    while True:
        rows = processes()
        members = [p for p in rows.values() if p["pgid"] == os.getpid()]
        if members != state["members"]:
            state["members"] = members
            write_json(dashboard.state_path(service), state)
        code = child.poll()
        if (stopping or code is not None) and shutdown_at is None:
            shutdown_at = time.monotonic()
            os.killpg(os.getpid(), signal.SIGTERM)
        if shutdown_at is not None:
            if not any(p["pid"] != os.getpid() for p in members):
                return code or 0
            if time.monotonic() - shutdown_at > STOP_TIMEOUT:
                os.killpg(os.getpid(), signal.SIGKILL)
        time.sleep(0.5)


def install() -> int:
    target_dir = Path(os.environ.get("OSHI_BIN_DIR", "~/.local/bin")).expanduser().resolve()
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / "oshi"
    if target.is_symlink() or (target.exists() and WRAPPER_MARKER not in target.read_text()):
        raise CliError(f"Refusing to overwrite an unrelated command: {target}")
    binaries = sorted(
        {str(Path(path).parent) for name in ("node", "npm") if (path := shutil.which(name))}
    )
    extra_path = ":".join(binaries)
    wrapper = "\n".join(
        [
            "#!/bin/sh",
            WRAPPER_MARKER,
            f'export PATH="${{PATH}}":{shlex.quote(extra_path)}',
            f'exec {shlex.quote(sys.executable)} {shlex.quote(str(ROOT / "scripts/oshi.py"))} "$@"',
            "",
        ]
    )
    temporary = target.with_name(f".oshi.{os.getpid()}.tmp")
    try:
        temporary.write_text(wrapper)
        temporary.chmod(0o755)
        temporary.replace(target)
    finally:
        temporary.unlink(missing_ok=True)
    print(f"Installed {target}\nProject: {ROOT}")
    if str(target_dir) not in os.environ.get("PATH", "").split(os.pathsep):
        line = (
            'export PATH="$HOME/.local/bin:$PATH"'
            if target_dir == Path.home() / ".local/bin"
            else f'export PATH={shlex.quote(str(target_dir))}:"$PATH"'
        )
        print(f"\nAdd this exact line to ~/.zshrc and run it in this terminal:\n{line}")
        print("Shell startup files were not edited.")
    print("\nRun oshi status. If this repository moves, rerun scripts/install-cli.sh.")
    return 0


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if argv == ["_install"]:
        return install()
    if len(argv) == 3 and argv[0] == "_serve" and argv[1] in SERVICES:
        return supervise(argv[1], argv[2])
    parser = argparse.ArgumentParser(description="OSHI Dashboard v0.1 — local service control")
    parser.add_argument(
        "command",
        choices=COMMANDS,
        help=(
            "start/kaishi: start services; end/stop/shuuryou: stop services; "
            "restart/saikidou: restart services; status: inspect services; "
            "open/hiraku: open dashboard; test: run checks; fetch: fetch configured sources"
        ),
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Preview fetch without database changes"
    )
    parser.add_argument("--source", metavar="KEY", help="Fetch only this enabled source")
    args = parser.parse_args(argv)
    if args.source is not None and not args.source.strip():
        parser.error("--source requires a nonempty source key")
    command = COMMANDS[args.command]
    if command != "fetch" and (args.dry_run or args.source is not None):
        parser.error("--dry-run and --source are only supported by fetch")
    dashboard = Dashboard()
    with dashboard.lock():
        if command == "fetch":
            return dashboard.fetch(dry_run=args.dry_run, source=args.source)
        elif command == "status":
            dashboard.status()
        elif command == "open":
            dashboard.open_browser()
        elif command == "test":
            return dashboard.tests()
        elif command == "stop":
            dashboard.stop()
            dashboard.status()
            print("\nOshi stopped. 推し活、終了。")
        else:
            if command == "restart":
                dashboard.ensure_no_external()
                dashboard.stop()
            dashboard.start()
            dashboard.status()
            print("\nOshi started. 推し活、開始。")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\nCancelled; owned work was cleaned up.", file=sys.stderr)
        sys.exit(130)
    except (CliError, OSError, subprocess.SubprocessError) as error:
        print(f"oshi: {error}", file=sys.stderr)
        sys.exit(1)
