"""The task statement the engine writes for a build with a harness: the
brief whole, the effective budget, the references, the setup session's
own statement and the prepared resources; a clone sees it and the prepared
link through the staging; the session's close commits neither; the
trading harness's prepared hook denies a write through the real link on
both event shapes."""

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from kapso.core.config import load_harness_defaults
from kapso.handles import Brief
from kapso.harness import load_harness, stage_harness
from kapso.harness.task_statement import compose_task_statement, setup_statement_path, write_task_statement
from tests.handles_support import git, git_workspace

TRADING = Path(__file__).resolve().parent.parent / "examples" / "harnesses" / "trading"
IGNORE_LINES = [".claude/", ".agents/", ".codex/", "kapso_task.md", "prepared"]


@pytest.fixture
def harness(tmp_path):
    copy = tmp_path / "h" / "trading"
    shutil.copytree(TRADING, copy)
    return load_harness(str(copy), settings=dict(load_harness_defaults(), store=str(tmp_path / "store")), say=lambda line: None)


def test_the_statement_holds_the_whole_brief_and_the_campaigns_facts(harness, tmp_path):
    objective = "Raise the Sharpe above 1\n" + "\n".join(f"- consideration {i}: " + "x" * 80 for i in range(600))
    brief = Brief(objective=objective, measured_by="backtest", rules=["no look-ahead"])
    assert len(brief.render().encode()) > 50_000
    campaign = tmp_path / "campaign"
    campaign.mkdir()
    path = write_task_statement(
        campaign, brief_text=brief.render(), harness=harness,
        budget={"experiments": 2, "minutes": 75.0, "usd": None, "reserve_minutes": None},
        evaluation_dir="/abs/evaluation", data_dir="/abs/data",
    )
    text = path.read_text()
    assert path == campaign / "kapso_task.md"
    assert brief.render().strip() in text
    assert "minutes=75.0 experiments=2 usd=none reserve_minutes=none" in text
    assert "Written by Kapso for harness trading 0.1.0" in text
    assert "`kapso_evaluation/`, provided by the person and protected" in text
    assert "`kapso_datasets/` at the campaign root, a copy of the data directory the build was given; read it there, never the original." in text
    assert "/abs/data" not in text   # the original path is not a path a session should reach
    assert "## Domain statement\n\n(the setup session has not written one)" in text
    assert "## Prepared resources\n\n(none yet)" in text


def test_the_statement_carries_the_setup_sessions_words_and_the_prepared_names(harness, tmp_path):
    campaign = tmp_path / "campaign"
    (campaign / "prepared" / "market-data").mkdir(parents=True)
    (campaign / "prepared" / "zz-later").mkdir()
    setup_statement_path(campaign).parent.mkdir(parents=True)
    setup_statement_path(campaign).write_text("Instruments BTC and ETH, hourly bars, 5 bp costs.\n")
    text = write_task_statement(
        campaign, brief_text="Objective    g", harness=harness,
        budget={}, evaluation_dir=None, data_dir=None,
    ).read_text()
    assert "## Domain statement\n\nInstruments BTC and ETH, hourly bars, 5 bp costs." in text
    assert "## Prepared resources\n\n- `prepared/market-data`\n- `prepared/zz-later`\n" in text
    assert "none provided: the campaign builds the evaluation from the brief's `Measured by` protocol" in text
    assert "no data directory was provided." in text
    # The engine composes the file; the setup session's words are a section,
    # never the whole file: the brief is still there.
    assert "## Brief\n\nObjective    g" in text
    assert compose_task_statement(
        brief_text="Objective    g", harness=harness, budget={}, evaluation_dir=None, data_dir=None,
        domain_statement="Instruments BTC and ETH, hourly bars, 5 bp costs.\n", prepared=("market-data", "zz-later"),
    ) == text


def test_a_clone_sees_the_statement_and_the_link_and_commits_neither(harness, tmp_path):
    campaign = tmp_path / "campaign"
    git_workspace(campaign)
    (campaign / ".gitignore").write_text("\n".join(IGNORE_LINES) + "\n")
    git(campaign, "add", ".gitignore")
    git(campaign, "commit", "-q", "-m", "ignore the staged paths")
    (campaign / "prepared" / "market-data").mkdir(parents=True)
    (campaign / "prepared" / "market-data" / "MANIFEST.json").write_text('{"instruments": ["BTC"]}')
    write_task_statement(campaign, brief_text="Objective    g", harness=harness, budget={}, evaluation_dir=None, data_dir=None)

    clone = tmp_path / "campaign" / "sessions" / "generic_exp_0"
    clone.parent.mkdir()
    git(tmp_path, "clone", "-q", str(campaign), str(clone))
    staged = stage_harness(harness, "implementation", session_dir=clone, campaign_dir=campaign, session_id="generic_exp_0", host="claude_code")

    assert (clone / "kapso_task.md").read_text() == (campaign / "kapso_task.md").read_text()
    assert (clone / "prepared").is_symlink() and (clone / "prepared" / "market-data" / "MANIFEST.json").is_file()
    assert ".claude/skills/backtesting/SKILL.md" in str(sorted(p.relative_to(clone) for p in clone.rglob("SKILL.md")))
    # The session's closing `git add .` has nothing of the harness to add.
    git(clone, "add", ".")
    assert git(clone, "status", "--porcelain") == ""
    assert staged.record["prepared"] == ["market-data"]


@pytest.mark.parametrize("tool_input", [
    {"file_path": "prepared/market-data/MANIFEST.json", "content": "{}"},
    {"command": "*** Begin Patch\n*** Update File: prepared/market-data/MANIFEST.json\n+x\n*** End Patch"},
])
def test_the_prepared_hook_denies_a_write_through_the_real_link_on_both_shapes(harness, tmp_path, tool_input):
    campaign = tmp_path / "campaign"
    (campaign / "prepared" / "market-data").mkdir(parents=True)
    (campaign / "prepared" / "market-data" / "MANIFEST.json").write_text("{}")
    clone = campaign / "sessions" / "s"
    clone.mkdir(parents=True)
    stage_harness(harness, "implementation", session_dir=clone, campaign_dir=campaign, session_id="s", host="claude_code")
    assert (clone / "prepared").is_symlink()

    hook = harness.path / "hooks" / "protect-prepared" / "protect_prepared.py"
    result = subprocess.run(
        [sys.executable, str(hook)], cwd=clone, input=json.dumps({"tool_input": tool_input}),
        capture_output=True, text=True, check=True,
    )
    decision = json.loads(result.stdout)["hookSpecificOutput"]
    assert decision["permissionDecision"] == "deny"
    assert "prepared/market-data/MANIFEST.json is under prepared/" in decision["permissionDecisionReason"]

    allowed = subprocess.run(
        [sys.executable, str(hook)], cwd=clone, input=json.dumps({"tool_input": {"file_path": "features/x.py"}}),
        capture_output=True, text=True, check=True,
    )
    assert allowed.stdout == ""
