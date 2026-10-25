"""Prerequisites are scoped to the modules a verb runs and checked again at
the call: a deployment-only variable does not refuse a build and is
printed as advisory; a program a hook on every module runs refuses the
build with its fix line; a variable set after the load is enough."""

import json
import shutil
from pathlib import Path

import pytest

from kapso.core.config import load_harness_defaults
from kapso.handles import Budget
from kapso.harness import HarnessError, load_harness
from tests.handles_support import facade, fake_orchestrator, git_workspace, solve_result

TRADING = Path(__file__).resolve().parent.parent / "examples" / "harnesses" / "trading"


def harness_copy(tmp_path: Path, server: str, variable: str) -> Path:
    """The trading harness with one server referencing one variable."""
    copy = tmp_path / "harness"
    shutil.copytree(TRADING, copy)
    mcp = copy / "mcp.json"
    data = json.loads(mcp.read_text())
    data["mcpServers"][server]["env"] = {variable: "${" + variable + "}"}
    mcp.write_text(json.dumps(data, indent=2))
    return copy


def loaded_facade(tmp_path: Path, harness_dir: Path):
    kapso = facade()
    kapso._harness_settings = dict(load_harness_defaults(), store=str(tmp_path / "store"))
    kapso._harness = load_harness(str(harness_dir), settings=kapso._harness_settings, say=lambda line: None)
    return kapso


def test_a_deployment_only_variable_is_advisory_for_a_build(tmp_path, monkeypatch, capsys):
    monkeypatch.delenv("BROKER_API_KEY", raising=False)
    monkeypatch.chdir(tmp_path)   # no .env here
    harness_dir = harness_copy(tmp_path, "broker", "BROKER_API_KEY")
    workspace = tmp_path / "ws"
    git_workspace(workspace)
    fake_orchestrator(monkeypatch, workspace, solve_result())
    kapso = loaded_facade(tmp_path, harness_dir)
    assert [row.label for row in kapso.harness.missing if "BROKER" in row.label]

    solution = kapso.build("g", output=str(workspace), budget=Budget(experiments=1))

    assert solution.harness.name == "trading"
    out = capsys.readouterr().out
    assert "advisory: BROKER_API_KEY (env, for the broker server): add BROKER_API_KEY=... to .env  [deployment]" in out


def test_a_variable_an_implementation_server_needs_refuses_the_build(tmp_path, monkeypatch):
    monkeypatch.delenv("MARKET_TOKEN", raising=False)
    monkeypatch.chdir(tmp_path)
    harness_dir = harness_copy(tmp_path, "market-data", "MARKET_TOKEN")
    workspace = tmp_path / "ws"
    git_workspace(workspace)
    fake_orchestrator(monkeypatch, workspace, solve_result())
    kapso = loaded_facade(tmp_path, harness_dir)

    with pytest.raises(HarnessError) as caught:
        kapso.build("g", output=str(workspace), budget=Budget(experiments=1))
    message = str(caught.value)
    assert message.startswith(f"harness {kapso.harness.label()} cannot run a build on this machine; it needs:")
    assert "- MARKET_TOKEN (env, for the market-data server): add MARKET_TOKEN=... to .env  [setup, implementation, deployment]" in message
    assert message.endswith("prerequisites are checked at every call.")
    assert not (workspace / ".kapso" / "launch.json").exists()


def test_a_variable_set_after_the_load_is_enough(tmp_path, monkeypatch):
    monkeypatch.delenv("MARKET_TOKEN", raising=False)
    monkeypatch.chdir(tmp_path)
    harness_dir = harness_copy(tmp_path, "market-data", "MARKET_TOKEN")
    workspace = tmp_path / "ws"
    git_workspace(workspace)
    fake_orchestrator(monkeypatch, workspace, solve_result())
    kapso = loaded_facade(tmp_path, harness_dir)
    assert kapso.harness.missing_for(("implementation",))

    monkeypatch.setenv("MARKET_TOKEN", "present")
    solution = kapso.build("g", output=str(workspace), budget=Budget(experiments=1))
    assert solution.harness.hash == kapso.harness.hash


def test_a_program_every_module_runs_refuses_with_its_fix(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    workspace = tmp_path / "ws"
    git_workspace(workspace)
    fake_orchestrator(monkeypatch, workspace, solve_result())
    kapso = loaded_facade(tmp_path, TRADING)
    monkeypatch.setattr("kapso.harness.check.shutil.which", lambda name: None if name == "python" else "/usr/bin/" + name)

    with pytest.raises(HarnessError) as caught:
        kapso.build("g", output=str(workspace), budget=Budget(experiments=1))
    assert "python (command, for the SessionStart hook): install python and put it on PATH; on a stock Ubuntu" in str(caught.value)
