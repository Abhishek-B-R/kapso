"""The engine's errors at the command line (wp6-observability.md, change
10): the message alone on stderr and exit 1 for the engine's own error
classes, the preflight's report included; the traceback for anything
else; the CLI's own refusals on stderr too; a real subprocess shows the
hook installed by `main()`."""
import subprocess
import sys
from pathlib import Path

import pytest

import kapso.cli.errors as errors_module
from kapso.cli.errors import ENGINE_ERRORS, report_engine_error
from kapso.core.config import ConfigError, load_config
from kapso.core.preflight import PreflightError, Requirement
from kapso.experience.reference import ExperienceReferenceError
from kapso.harness.load import HarnessError


def test_an_engine_error_prints_its_message_alone_and_exits_one(capsys):
    error = HarnessError("the harness changed since launch: trading 0.1.0 recorded; restore it")
    with pytest.raises(SystemExit) as excinfo:
        report_engine_error(HarnessError, error, None)
    assert excinfo.value.code == 1
    captured = capsys.readouterr()
    assert captured.err == "Error: the harness changed since launch: trading 0.1.0 recorded; restore it\n"
    assert captured.out == "" and "Traceback" not in captured.err


def test_a_preflight_report_is_printed_whole(capsys):
    error = PreflightError("build", [Requirement(label="claude CLI", ok=False, fix="npm install -g @anthropic-ai/claude-code", origin="the ideation session")])
    with pytest.raises(SystemExit):
        report_engine_error(PreflightError, error, None)
    err = capsys.readouterr().err
    assert err.startswith("Error: ") and "claude CLI" in err and "npm install" in err and err.count("\n") > 1


def test_any_other_exception_keeps_its_traceback(monkeypatch):
    seen = []
    monkeypatch.setattr(sys, "__excepthook__", lambda *args: seen.append(args))
    error = TypeError("a bug")
    report_engine_error(TypeError, error, None)
    assert seen == [(TypeError, error, None)]
    assert TypeError not in ENGINE_ERRORS and ExperienceReferenceError in ENGINE_ERRORS


def test_the_command_line_shows_the_message_and_no_traceback(tmp_path):
    """A real `kapso` process: the hook `main()` installs prints the
    message, every line of it, for a harness reference that names nothing,
    and the exit code is 1."""
    run = subprocess.run(
        [sys.executable, "-m", "kapso.cli", "harness", "check", "./nowhere"],
        capture_output=True, text=True, cwd=tmp_path, timeout=120,
    )
    assert run.returncode == 1, run.stderr
    assert run.stderr.startswith("Error: no directory ") and "Traceback" not in run.stderr
    assert "the forms are:" in run.stderr and run.stderr.count("\n") > 1
    assert run.stdout == ""


def test_the_clis_own_refusals_are_on_stderr(tmp_path):
    run = subprocess.run(
        [sys.executable, "-m", "kapso.cli", "inbox", "a", "b"],
        capture_output=True, text=True, cwd=tmp_path, timeout=120,
    )
    assert run.returncode == 1
    assert run.stderr.strip() == "Error: kapso inbox takes at most a campaign directory"
    assert run.stdout == ""


def test_a_config_refusal_is_the_engines_own_error(tmp_path, capsys):
    """A stale file with `modes:`, an unknown key at depth, a missing file:
    each is a `ConfigError`, which the CLI prints as one line naming the
    file and the keys, never as a traceback (the WP4 proof run's first
    finding)."""
    stale = tmp_path / "stale.yaml"
    stale.write_text("default_mode: GENERIC\nmodes:\n  GENERIC: {}\n")
    with pytest.raises(ConfigError, match="stale.yaml: the top level: unknown keys default_mode, modes; the keys are budget,") as caught:
        load_config(str(stale))
    assert isinstance(caught.value, ENGINE_ERRORS)
    with pytest.raises(SystemExit):
        report_engine_error(ConfigError, caught.value, None)
    err = capsys.readouterr().err
    assert err.startswith(f"Error: {stale}: the top level: unknown keys default_mode, modes") and "Traceback" not in err
    deep = tmp_path / "deep.yaml"
    deep.write_text("budget:\n  minute: 5\n")
    with pytest.raises(ConfigError, match="deep.yaml: budget: unknown key minute; the keys are"):
        load_config(str(deep))
    with pytest.raises(ConfigError, match="missing.yaml: no such file"):
        load_config(str(tmp_path / "missing.yaml"))
