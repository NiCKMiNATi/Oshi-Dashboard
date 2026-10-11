"""No test contacts Task Scheduler. Exercise its transport/configuration with doubles."""

import importlib.util
import json
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path
from unittest.mock import Mock

import pytest

SPEC = importlib.util.spec_from_file_location(
    "oshi_windows", Path(__file__).parents[1] / "oshi_windows.py"
)
cli = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(cli)
USER = "S-1-5-21-test"


@pytest.fixture
def scheduler(tmp_path, monkeypatch):
    root = tmp_path / "Oshi 日本語 & ' project"
    python = root / "backend/.venv/Scripts/python.exe"
    python.parent.mkdir(parents=True)
    python.touch()
    monkeypatch.delenv("OSHI_DATABASE_PATH", raising=False)
    monkeypatch.delenv("OSHI_SOURCES_PATH", raising=False)
    state = {"installed": False, "user": USER}
    calls = []

    def invoke(operation, project, **payload):
        assert project == root
        calls.append(operation)
        if operation == "register":
            state.update(installed=True, enabled=True, xml=payload["xml"])
        elif operation in ("enable", "disable"):
            state["enabled"] = operation == "enable"
        return state.copy()

    monkeypatch.setattr(cli, "scheduler", invoke)
    return root, state, calls


def test_idempotent_registration_disable_enable_and_run(scheduler):
    root, state, calls = scheduler
    cli.background("off", root)
    assert calls == ["status"]
    cli.background("on", root)
    original = state["xml"]
    cli.background("on", root)
    assert calls.count("register") == 1
    assert state["xml"] == original  # Does not reset the trigger start time.
    cli.background("off", root)
    cli.background("off", root)
    assert calls.count("disable") == 1
    with pytest.raises(cli.BackgroundError, match="on first"):
        cli.background("run", root)
    cli.background("on", root)
    assert calls.count("enable") == 1
    cli.background("run", root)
    assert calls[-1] == "run"


def test_task_definition_and_paths(scheduler, monkeypatch):
    root, _, _ = scheduler
    monkeypatch.setenv("OSHI_DATABASE_PATH", "local/personal db.sqlite")
    monkeypatch.chdir(root.parent)
    config = cli.configuration(root)
    assert config["database"] == str(root / "local/personal db.sqlite")
    xml = ET.fromstring(cli.task_xml(config, USER))
    ns = {"t": cli.NS}

    def value(path):
        return xml.findtext(path, namespaces=ns)

    assert value("t:Actions/t:Exec/t:Command") == str(root / "backend/.venv/Scripts/python.exe")
    assert value("t:Actions/t:Exec/t:WorkingDirectory") == str(root)
    arguments = value("t:Actions/t:Exec/t:Arguments")
    assert arguments == subprocess.list2cmdline(
        [
            "-u",
            str(root / "scripts/background_fetch.py"),
            "--database-path",
            config["database"],
            "--sources-path",
            config["sources"],
        ]
    )
    assert value("t:Settings/t:MultipleInstancesPolicy") == "IgnoreNew"
    assert value("t:Settings/t:StartWhenAvailable") == "true"
    assert value("t:Settings/t:ExecutionTimeLimit") == "PT20M"
    assert value("t:Principals/t:Principal/t:LogonType") == "InteractiveToken"
    assert value("t:Principals/t:Principal/t:RunLevel") == "LeastPrivilege"
    assert value("t:Triggers/t:TimeTrigger/t:Repetition/t:Interval") == "PT30M"
    assert value("t:Triggers/t:TimeTrigger/t:Repetition/t:Duration") is None
    trigger = xml.find("t:Triggers/t:TimeTrigger", ns)
    assert [node.tag.split("}")[-1] for node in trigger] == [
        "Enabled",
        "StartBoundary",
        "Repetition",
    ]


@pytest.mark.parametrize("change", ["project", "owner", "description"])
def test_unrelated_task_never_mutated(scheduler, change):
    root, state, calls = scheduler
    cli.background("on", root)
    if change == "project":
        config = cli.configuration(root.parent)
        state["xml"] = cli.task_xml(config, USER)
    elif change == "owner":
        state["xml"] = cli.task_xml(cli.configuration(root), "other-user")
    else:
        state["xml"] = state["xml"].replace(cli.MARKER, "unrelated:")
    for action in ("on", "off", "run", "status"):
        with pytest.raises(cli.BackgroundError, match="not changed"):
            cli.background(action, root)
        assert calls[-1] == "status"


def test_status_uses_registered_database_not_current_environment(scheduler, monkeypatch, capsys):
    root, state, _ = scheduler
    cli.background("on", root)
    state.update(
        last_run="2026-10-01T00:00:00Z",
        last_result=1,
        next_run="2026-10-01T00:30:00Z",
        state="Ready",
    )
    capsys.readouterr()
    monkeypatch.setenv("OSHI_DATABASE_PATH", "different.db")
    cli.background("status", root)
    output = capsys.readouterr().out
    assert str(root / "data/oshi.db") in output
    assert "different.db" not in output
    assert "30 minutes" in output
    assert "Last result: 1" in output
    assert "2026-10-01T00:30:00Z" in output
    cli.background("on", root)
    assert cli.owned_configuration(state, root)["database"] == str(root / "different.db")


def test_transport_uses_json_not_interpolated_shell(tmp_path, monkeypatch):
    run = Mock(
        return_value=subprocess.CompletedProcess(
            [], 0, '{"installed":false,"user":"S-1-5-21-test"}', ""
        )
    )
    monkeypatch.setattr(cli.subprocess, "run", run)
    assert cli.scheduler("status", tmp_path)["installed"] is False
    args, kwargs = run.call_args
    assert "-NoProfile" in args[0] and "-NonInteractive" in args[0]
    assert kwargs["cwd"] == tmp_path
    assert json.loads(kwargs["input"])["name"] == cli.TASK_NAME
    assert "shell" not in kwargs


@pytest.mark.parametrize(
    "outcome",
    [
        subprocess.CompletedProcess([], 1, "", "secret error"),
        subprocess.CompletedProcess([], 0, "not json", ""),
        subprocess.CompletedProcess([], 0, "[]", ""),
        subprocess.TimeoutExpired("powershell", 45),
        FileNotFoundError(),
    ],
)
def test_scheduler_failures_are_actionable_and_do_not_echo_secrets(tmp_path, monkeypatch, outcome):
    run = Mock()
    if isinstance(outcome, Exception):
        run.side_effect = outcome
    else:
        run.return_value = outcome
    monkeypatch.setattr(cli.subprocess, "run", run)
    with pytest.raises(cli.BackgroundError) as error:
        cli.scheduler("status", tmp_path)
    assert "secret" not in str(error.value)


def test_unsupported_platform_does_not_launch_anything(tmp_path, monkeypatch, capsys):
    run = Mock()
    monkeypatch.setattr(cli.subprocess, "run", run)
    assert cli.main(["background", "on"], root=tmp_path, platform="darwin") == 1
    run.assert_not_called()
    assert "requires Windows" in capsys.readouterr().err


def test_manual_fetch_command_propagates_failure(tmp_path, monkeypatch):
    run = Mock(return_value=subprocess.CompletedProcess([], 1))
    monkeypatch.setattr(cli.subprocess, "run", run)
    assert (
        cli.main(["fetch", "--dry-run", "--source", "fixture"], root=tmp_path, platform="win32")
        == 1
    )
    assert run.call_args.args[0] == [
        str(tmp_path / "backend/.venv/Scripts/python.exe"),
        "-m",
        "app.ingestion",
        "--dry-run",
        "--source",
        "fixture",
    ]


def test_definition_change_race_guard_is_in_transport():
    script = (Path(__file__).parents[1] / "windows_scheduler.ps1").read_text()
    assert "$task.Xml -cne $request.expected_xml" in script
    assert "$existing.Task.Principals.Principal.UserId -ne $userSid" in script
    assert "Stop-ScheduledTask" not in script
