"""The campaign gate (docs/plans/redesign/wp7-plugin.md, change 8): the
three tools over the verbs, faked at the subprocess boundary, each
outcome as data; the receipt's keys; a receipt that does not parse
raising; the refusals (no `kapso` on PATH, inside a campaign, brief and
goal both or neither); the gate host-only, refused by `get_mcp_config`
and served by `kapso-mcp` with nothing to require; and the real server,
started in an empty directory, connecting with the campaign tools and
its brief."""

import asyncio
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

import kapso.gated_mcp.gates.campaign_gate as gate_module
from kapso.gated_mcp.gates.base import GateConfig
from kapso.gated_mcp.gates.campaign_gate import START_TOOL, STATUS_TOOL, STOP_TOOL, CampaignGate
from kapso.gated_mcp.host_session import DEFAULT_GATES, prepare_host_gates
from kapso.gated_mcp.presets import GATES, get_mcp_config
from tests.harness_support import fake_config

ROOT = Path(__file__).resolve().parent.parent


def _gate(tmp_path, config_path=None):
    return CampaignGate(GateConfig(params={"cwd": str(tmp_path), "config_path": config_path}))


def _call(gate, tool, **arguments):
    [content] = asyncio.run(gate.handle_call(tool, arguments))
    return json.loads(content.text)


@pytest.fixture
def kapso_on_path(monkeypatch):
    monkeypatch.setattr(gate_module.shutil, "which", lambda name: "/usr/local/bin/kapso")


def _fake_verb(monkeypatch, calls, *, returncode=0, stdout="", stderr="", before=None):
    def run(argv, cwd, capture_output, text):
        calls.append((argv, cwd))
        if before is not None:
            before()
        return subprocess.CompletedProcess(argv, returncode, stdout, stderr)
    monkeypatch.setattr(gate_module.subprocess, "run", run)


def test_start_runs_the_verb_detached_on_the_servers_interpreter_and_returns_the_receipt(tmp_path, monkeypatch, kapso_on_path):
    calls = []
    campaign = tmp_path / "campaign"
    receipt = tmp_path / "campaign.launch.json"
    _fake_verb(monkeypatch, calls, stdout="build started in a session of its own (pid 4242)\n", before=lambda: receipt.write_text(
        json.dumps({"pid": 4242, "log": str(tmp_path / "campaign.log"), "argv": ["build"], "started_at": "2026-10-27T10:00:00+00:00"}),
    ))
    answer = _call(
        _gate(tmp_path, "kapso-config.yaml"), START_TOOL,
        brief="kapso-brief.md", repo=".", output="campaign", evaluation="evaluation",
        budget_minutes=60, budget_experiments=3, experience=["mine", "leeroopedia"],
    )
    assert calls == [([
        sys.executable, "-m", "kapso.cli", "build", "--brief", "kapso-brief.md", "--repo", ".", "--output", "campaign",
        "--evaluation", "evaluation", "--budget-minutes", "60", "--budget-experiments", "3",
        "--experience", "mine,leeroopedia", "--config", "kapso-config.yaml", "--detach",
    ], str(tmp_path))]
    assert answer == {
        "accepted": True, "pid": 4242, "log": str(tmp_path / "campaign.log"),
        "status": str(campaign / ".kapso" / "status.json"), "watch": f"kapso watch {campaign} --follow",
        "campaign": str(campaign), "started_at": "2026-10-27T10:00:00+00:00",
    }
    # `goal` is the one-line form; the argument's config wins over the server's.
    _call(_gate(tmp_path, "kapso-config.yaml"), START_TOOL, goal="raise the AUC above 0.85", repo=".", output="campaign", config="other.yaml")
    assert calls[-1][0][3:7] == ["build", "--goal", "raise the AUC above 0.85", "--repo"] and calls[-1][0][-3:] == ["--config", "other.yaml", "--detach"]


def test_a_refused_launch_is_data_and_a_receipt_that_does_not_parse_raises(tmp_path, monkeypatch, kapso_on_path):
    calls = []
    _fake_verb(monkeypatch, calls, returncode=1, stderr="Error: the evaluation directory holds a result.json\n")
    assert _call(_gate(tmp_path), START_TOOL, brief="kapso-brief.md", repo=".", output="campaign") == {
        "accepted": False, "exit": 1, "error": "Error: the evaluation directory holds a result.json",
    }
    _fake_verb(monkeypatch, calls, before=lambda: (tmp_path / "campaign.launch.json").write_text("{not json"))
    with pytest.raises(json.JSONDecodeError):
        _call(_gate(tmp_path), START_TOOL, brief="kapso-brief.md", repo=".", output="campaign")


def test_start_refuses_before_the_verb_without_kapso_on_path_and_with_brief_and_goal_both_or_neither(tmp_path, monkeypatch):
    calls = []
    _fake_verb(monkeypatch, calls)
    monkeypatch.setattr(gate_module.shutil, "which", lambda name: None)
    answer = _call(_gate(tmp_path), START_TOOL, brief="kapso-brief.md", repo=".", output="campaign")
    assert answer["accepted"] is False and answer["exit"] is None and "/kapso:setup" in answer["error"]
    monkeypatch.setattr(gate_module.shutil, "which", lambda name: "/usr/local/bin/kapso")
    for arguments in ({"brief": "b.md", "goal": "g"}, {}):
        answer = _call(_gate(tmp_path), START_TOOL, repo=".", output="campaign", **arguments)
        assert answer == {"accepted": False, "exit": None, "error": "pass exactly one of `brief` (a file's path) and `goal` (one line)"}
    assert calls == []


def test_every_tool_refuses_inside_a_campaign_directory(tmp_path, monkeypatch, kapso_on_path):
    calls = []
    _fake_verb(monkeypatch, calls)
    (tmp_path / ".kapso").mkdir()
    (tmp_path / ".kapso" / "experiment_history.json").write_text("{}")
    inside = tmp_path / "sessions" / "generic_exp_1"
    inside.mkdir(parents=True)
    gate = _gate(inside)
    for tool, arguments in ((START_TOOL, {"brief": "b.md", "repo": ".", "output": "x"}), (STATUS_TOOL, {"path": "x"}), (STOP_TOOL, {"path": "x"})):
        answer = _call(gate, tool, **arguments)
        expected = {"error": f"this session runs inside the campaign at {tmp_path}: a campaign never launches, reads or stops a campaign; run the verb from the project directory"}
        expected.update({START_TOOL: {"accepted": False}, STOP_TOOL: {"stopped": False}}.get(tool, {}))
        assert answer == expected
    assert calls == []


def test_status_returns_the_verbs_json_with_its_exit_code(tmp_path, monkeypatch):
    calls = []
    _fake_verb(monkeypatch, calls, stdout=json.dumps({"state": "running", "phase": "implementation"}))
    assert _call(_gate(tmp_path), STATUS_TOOL, path="../campaign") == {"state": "running", "phase": "implementation", "exit": 0}
    assert calls[-1] == ([sys.executable, "-m", "kapso.cli", "watch", "../campaign", "--json"], str(tmp_path))
    # A launch that died before its status: the state and the exit code travel together.
    _fake_verb(monkeypatch, calls, returncode=1, stdout=json.dumps({"state": "stopped", "pid": 7, "log": "/l", "started_at": "t"}))
    assert _call(_gate(tmp_path), STATUS_TOOL, path="../campaign") == {"state": "stopped", "pid": 7, "log": "/l", "started_at": "t", "exit": 1}
    _fake_verb(monkeypatch, calls, returncode=2, stderr="kapso watch: error: unrecognized arguments")
    assert _call(_gate(tmp_path), STATUS_TOOL, path="../campaign") == {"exit": 2, "error": "kapso watch: error: unrecognized arguments"}


def test_stop_returns_the_writers_pid_from_the_status_or_the_refusal(tmp_path, monkeypatch):
    calls = []
    campaign = tmp_path / "c"
    (campaign / ".kapso").mkdir(parents=True)
    (campaign / ".kapso" / "status.json").write_text(json.dumps({"state": "running", "pid": 4242}))
    _fake_verb(monkeypatch, calls, stdout=f"stopped the campaign at {campaign} (pid 4242)\n")
    assert _call(_gate(tmp_path, "kapso-config.yaml"), STOP_TOOL, path="c") == {"stopped": True, "pid": 4242}
    assert calls[-1] == ([sys.executable, "-m", "kapso.cli", "build", "--output", str(campaign), "--stop", "--config", "kapso-config.yaml"], str(tmp_path))
    _fake_verb(monkeypatch, calls, returncode=1, stderr=f"Error: the campaign at {campaign} is done; nothing to stop\n")
    assert _call(_gate(tmp_path), STOP_TOOL, path="c") == {"stopped": False, "exit": 1, "error": f"Error: the campaign at {campaign} is done; nothing to stop"}
    assert calls[-1][0] == [sys.executable, "-m", "kapso.cli", "build", "--output", str(campaign), "--stop"]


def test_a_tilde_output_is_under_the_home_directory_not_the_working_one(tmp_path, monkeypatch, kapso_on_path):
    monkeypatch.setenv("HOME", str(tmp_path))
    calls = []
    project = tmp_path / "project"
    project.mkdir()
    receipt = tmp_path / "campaign.launch.json"
    _fake_verb(monkeypatch, calls, stdout="build started (pid 1)\n", before=lambda: receipt.write_text(
        json.dumps({"pid": 1, "log": "l", "argv": [], "started_at": "t"}),
    ))
    answer = _call(_gate(project), START_TOOL, goal="g", repo=".", output="~/campaign")
    assert answer["accepted"] is True and answer["campaign"] == str(tmp_path / "campaign")


def test_the_gate_is_host_only(tmp_path, monkeypatch):
    assert GATES["campaign"].host_only is True and GATES["campaign"].required_env == []
    with pytest.raises(ValueError, match="host-only gate\\(s\\) campaign: kapso-mcp serves them to a host session"):
        get_mcp_config(["research", "campaign"])
    assert DEFAULT_GATES[-1] == "campaign"
    gates = prepare_host_gates(
        root=tmp_path, requested=["campaign"], config=fake_config(), sources=[],
        session_dir=tmp_path / "s", probe_budget=1,
    )
    assert gates.enabled == ["campaign"] and gates.env == {} and gates.notes == []


def test_the_real_server_connects_in_an_empty_directory_and_lists_the_campaign_tools(tmp_path):
    """`kapso-mcp` in a bare directory, no codex on PATH: it connects, its
    brief names what is off and why, and the campaign tools are listed."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    os.symlink(shutil.which("git"), bin_dir / "git")
    project = tmp_path / "project"
    project.mkdir()
    env = {
        "PATH": str(bin_dir), "HOME": os.environ["HOME"],
        "PYTHONPATH": os.environ.get("PYTHONPATH", str(ROOT / "src")),
    }

    async def probe():
        params = StdioServerParameters(
            command=sys.executable, args=["-m", "kapso.gated_mcp.host_session", "--root", str(project)], env=env, cwd=str(project),
        )
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as session:
                started = await session.initialize()
                listed = await session.list_tools()
                return started.instructions, sorted(tool.name for tool in listed.tools)

    instructions, names = asyncio.run(probe())
    assert names == sorted(GATES["campaign"].tools)
    assert instructions.startswith("## Kapso tools in this session (kapso-mcp ")
    assert "- on: campaign\n" in instructions and "- research: off (the codex CLI is not on PATH)" in instructions
