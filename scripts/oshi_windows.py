"""Thin Windows fetch/Task Scheduler CLI. No dashboard lifecycle control."""

import argparse
import json
import os
import subprocess
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TASK_NAME = "Oshi Dashboard Background Fetch"
MARKER = "Oshi Dashboard background fetch v1:"
NS = "http://schemas.microsoft.com/windows/2004/02/mit/task"


class BackgroundError(Exception):
    pass


def resolve_path(root: Path, value: str) -> Path:
    return (root / Path(value).expanduser()).resolve()


def configuration(root: Path) -> dict:
    return {
        "repository": str(root.resolve()),
        "database": str(resolve_path(root, os.getenv("OSHI_DATABASE_PATH", "data/oshi.db"))),
        "sources": str(resolve_path(root, os.getenv("OSHI_SOURCES_PATH", "local/sources.json"))),
    }


def task_xml(config: dict, user: str) -> str:
    root = Path(config["repository"])
    task = ET.Element("Task", version="1.3", xmlns=NS)

    def add(parent, tag, text=None):
        node = ET.SubElement(parent, tag)
        node.text = text
        return node

    registration = add(task, "RegistrationInfo")
    add(registration, "Description", MARKER + json.dumps(config, ensure_ascii=True))
    triggers = add(task, "Triggers")
    trigger = add(triggers, "TimeTrigger")
    # triggerBaseType uses a sequence: Enabled, StartBoundary, Repetition.
    add(trigger, "Enabled", "true")
    add(
        trigger,
        "StartBoundary",
        (datetime.now().astimezone() + timedelta(minutes=1)).isoformat(timespec="seconds"),
    )
    # Omit Duration and EndBoundary: repeat indefinitely. First run in one minute.
    repetition = add(trigger, "Repetition")
    add(repetition, "Interval", "PT30M")
    add(repetition, "StopAtDurationEnd", "false")
    principal = add(add(task, "Principals"), "Principal")
    principal.set("id", "Author")
    add(principal, "UserId", user)
    add(principal, "LogonType", "InteractiveToken")
    add(principal, "RunLevel", "LeastPrivilege")
    settings = add(task, "Settings")
    for key, value in {
        "MultipleInstancesPolicy": "IgnoreNew",
        "DisallowStartIfOnBatteries": "false",
        "StopIfGoingOnBatteries": "false",
        "StartWhenAvailable": "true",
        "RunOnlyIfNetworkAvailable": "false",
        "AllowStartOnDemand": "true",
        "Enabled": "true",
        "WakeToRun": "false",
        "ExecutionTimeLimit": "PT20M",
    }.items():
        add(settings, key, value)
    actions = add(task, "Actions")
    actions.set("Context", "Author")
    action = add(actions, "Exec")
    add(action, "Command", str(root / "backend/.venv/Scripts/python.exe"))
    add(
        action,
        "Arguments",
        subprocess.list2cmdline(
            [
                "-u",
                str(root / "scripts/background_fetch.py"),
                "--database-path",
                config["database"],
                "--sources-path",
                config["sources"],
            ]
        ),
    )
    add(action, "WorkingDirectory", str(root))
    return ET.tostring(task, encoding="unicode")


def scheduler(operation: str, root: Path, **payload) -> dict:
    # JSON stdin is data, never interpolated PowerShell source or shell quoting.
    command = [
        str(
            Path(os.environ.get("SystemRoot", r"C:\Windows"))
            / "System32/WindowsPowerShell/v1.0/powershell.exe"
        ),
        "-NoProfile",
        "-NonInteractive",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        str(root / "scripts/windows_scheduler.ps1"),
    ]
    try:
        result = subprocess.run(
            command,
            input=json.dumps({"operation": operation, "name": TASK_NAME, **payload}),
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=45,
            cwd=root,
        )
    except (OSError, subprocess.SubprocessError) as error:
        raise BackgroundError(
            f"Task Scheduler invocation failed ({type(error).__name__})."
        ) from None
    if result.returncode:
        raise BackgroundError(
            "Task Scheduler failed. Check task ownership and Windows task permissions; "
            "no elevation is requested."
        )
    try:
        data = json.loads(result.stdout.lstrip("\ufeff"))
        if not isinstance(data, dict) or not isinstance(data["installed"], bool):
            raise ValueError
        if not isinstance(data["user"], str) or not data["user"]:
            raise ValueError
        if data["installed"] and (
            not isinstance(data["enabled"], bool) or not isinstance(data["xml"], str)
        ):
            raise ValueError
        return data
    except (ValueError, KeyError, TypeError):
        raise BackgroundError("Invalid Task Scheduler status response.") from None


def owned_configuration(status: dict, root: Path) -> dict | None:
    if not status["installed"]:
        return None
    try:
        xml = ET.fromstring(status["xml"])
        description = xml.findtext(f"{{{NS}}}RegistrationInfo/{{{NS}}}Description", "")
        if not description.startswith(MARKER):
            raise ValueError
        config = json.loads(description[len(MARKER) :])
        if Path(config["repository"]).resolve() != root.resolve():
            raise ValueError
        if xml.findtext(f"{{{NS}}}Principals/{{{NS}}}Principal/{{{NS}}}UserId") != status["user"]:
            raise ValueError
        for key in ("database", "sources"):
            if not Path(config[key]).is_absolute():
                raise ValueError
        return config
    except (ET.ParseError, ValueError, KeyError, TypeError):
        raise BackgroundError(
            "The named task belongs to another user/project or is unrecognized. "
            "It was not changed. See docs/background-fetch-windows.md for repository moves."
        ) from None


def show_status(status: dict, config: dict):
    print(f"Task: {TASK_NAME}")
    print(f"Installed: {'yes' if status['installed'] else 'no'}")
    print(f"Enabled: {'yes' if status.get('enabled') else 'no'}")
    cadence = "30 minutes (default; not installed)"
    if status["installed"]:
        xml = ET.fromstring(status["xml"])
        cadence = xml.findtext(
            f"{{{NS}}}Triggers/{{{NS}}}TimeTrigger/{{{NS}}}Repetition/{{{NS}}}Interval", "unknown"
        )
        cadence = "30 minutes" if cadence == "PT30M" else cadence
    print(f"Cadence: {cadence}")
    for label, field in (
        ("State", "state"),
        ("Last run (UTC)", "last_run"),
        ("Last result", "last_result"),
        ("Next run (UTC)", "next_run"),
    ):
        print(f"{label}: {status.get(field) if status.get(field) is not None else 'unavailable'}")
    print(
        f"Repository: {config['repository']}\nDatabase: {config['database']}\n"
        f"Sources: {config['sources']}"
    )


def background(action: str, root: Path) -> int:
    state = scheduler("status", root)
    saved = owned_configuration(state, root)
    desired = configuration(root)
    if action == "on":
        if not (root / "backend/.venv/Scripts/python.exe").is_file():
            raise BackgroundError("Windows backend virtualenv missing; run scripts/setup.ps1.")
        if saved != desired:
            state = scheduler(
                "register",
                root,
                xml=task_xml(desired, state["user"]),
                expected_xml=state.get("xml"),
            )
        elif not state["enabled"]:
            state = scheduler("enable", root, expected_xml=state["xml"])
    elif action == "off":
        if saved and state["enabled"]:
            state = scheduler("disable", root, expected_xml=state["xml"])
        print("Future runs disabled; any active fetch is allowed to finish.")
    elif action == "run":
        if not saved or not state["enabled"]:
            raise BackgroundError(
                "Run background on first; the task must be installed and enabled."
            )
        state = scheduler("run", root, expected_xml=state["xml"])
        print(
            "Run requested (IgnoreNew if already running). "
            "Check status and .runtime/background-fetch.log."
        )
    show_status(state, owned_configuration(state, root) or desired)
    return 0


def main(argv=None, *, root=ROOT, platform=sys.platform):
    parser = argparse.ArgumentParser(description="Windows Oshi manual/background fetch")
    sub = parser.add_subparsers(dest="command", required=True)
    bg = sub.add_parser("background")
    bg.add_argument("action", choices=("on", "off", "status", "run"))
    fetch = sub.add_parser("fetch")
    fetch.add_argument("--dry-run", action="store_true")
    fetch.add_argument("--source")
    args = parser.parse_args(argv)
    if platform != "win32":
        print(
            "This wrapper requires Windows; use the existing macOS CLI or python -m app.ingestion.",
            file=sys.stderr,
        )
        return 1
    root = root.resolve()
    try:
        if args.command == "background":
            return background(args.action, root)
        command = [str(root / "backend/.venv/Scripts/python.exe"), "-m", "app.ingestion"]
        if args.dry_run:
            command.append("--dry-run")
        if args.source is not None:
            command.extend(["--source", args.source])
        return subprocess.run(command, cwd=root, check=False).returncode
    except (BackgroundError, OSError) as error:
        print(f"oshi: {error}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    sys.exit(main())
