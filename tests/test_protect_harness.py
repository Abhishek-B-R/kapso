"""The harness directory protected (docs/plans/redesign/wp4-config.md,
change 10): the engine's `protect-harness` hook is merged first into
every harness session's hooks file, user hooks or none, and listed in the
record; the script denies a file-tool write under the harness root on
both hosts' event shapes with the reason; a shell write passes the hook
and is caught by the hash check at the next staging, by name; the setup
session is told to fix the environment, never the harness."""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from kapso.core.config import load_config
from kapso.core.prompt_loader import load_prompt
from kapso.harness.hooks import ENGINE_HOOKS_DIR, PROTECT_HARNESS
from kapso.harness.load import HarnessError, load_harness
from kapso.harness.staging import stage_harness

TRADING = Path(__file__).resolve().parent.parent / "examples" / "harnesses" / "trading"
SCRIPT = ENGINE_HOOKS_DIR / "protect_harness" / "protect_harness.py"


@pytest.fixture
def harness(tmp_path):
    copy = tmp_path / "harness"
    shutil.copytree(TRADING, copy)
    return load_harness(str(copy), settings=load_config()["harness"], say=lambda line: None)


def stage(harness, module, host, campaign, session_id="generic_exp_0"):
    session_dir = campaign / "sessions" / session_id if module != "setup" else campaign
    session_dir.mkdir(parents=True, exist_ok=True)
    return stage_harness(harness, module, session_dir=session_dir, campaign_dir=campaign, session_id=session_id, host=host)


@pytest.mark.parametrize("host, file", [("claude_code", ".claude/harness-hooks.json"), ("codex", ".codex/hooks.json")])
@pytest.mark.parametrize("module", ["implementation", "learning"])
def test_the_engine_hook_is_merged_first_with_or_without_user_hooks(harness, tmp_path, host, file, module):
    staged = stage(harness, module, host, tmp_path / "campaign", session_id=f"{module}-session")
    hooks = json.loads((staged.session_dir / file).read_text())["hooks"]
    first = hooks["PreToolUse"][0]
    assert first["matcher"] == "Edit|Write|MultiEdit"
    assert first["hooks"] == [{"type": "command", "command": f"python3 {SCRIPT}"}]
    assert staged.record["hooks"][0] == PROTECT_HARNESS
    if module == "learning":
        assert list(hooks) == ["PreToolUse"] and len(hooks["PreToolUse"]) == 1 and staged.record["hooks"] == [PROTECT_HARNESS]
    else:
        assert len(hooks["PreToolUse"]) > 1 and staged.record["hooks"][1:] == list(harness.module(module).hooks)
    if host == "codex":
        assert staged.agent_specific["hooks_trust_bypass"] is True
    else:
        assert staged.agent_specific["settings_path"] == str(staged.session_dir / file)


def decision(harness_root: Path, cwd: Path, event: dict) -> dict:
    completed = subprocess.run(
        [sys.executable, str(SCRIPT)], input=json.dumps(event), capture_output=True, text=True, check=True,
        cwd=str(cwd), env={**os.environ, "KAPSO_HARNESS_ROOT": str(harness_root)},
    )
    return json.loads(completed.stdout) if completed.stdout.strip() else {}


def test_the_script_denies_a_write_under_the_harness_on_both_hosts_shapes(harness, tmp_path):
    session = tmp_path / "session"
    session.mkdir()
    page = harness.path / "instructions" / "guardrails.md"
    # Claude Code's file tools name the file.
    denied = decision(harness.path, session, {"tool_name": "Write", "tool_input": {"file_path": str(page)}})
    reason = denied["hookSpecificOutput"]["permissionDecisionReason"]
    assert denied["hookSpecificOutput"]["permissionDecision"] == "deny"
    assert reason.startswith(f"{page} is under the harness directory") and "never the harness" in reason
    # Codex's apply_patch names the files in its headers; a relative path
    # resolves against the session directory.
    relative = os.path.relpath(harness.path / "skills" / "backtesting" / "SKILL.md", session)
    patch = f"*** Begin Patch\n*** Update File: {relative}\n@@\n-old\n+new\n*** End Patch\n"
    denied = decision(harness.path, session, {"tool_name": "apply_patch", "tool_input": {"command": patch}})
    assert denied["hookSpecificOutput"]["permissionDecision"] == "deny"
    assert relative in denied["hookSpecificOutput"]["permissionDecisionReason"]
    # A write anywhere else passes.
    assert decision(harness.path, session, {"tool_name": "Write", "tool_input": {"file_path": str(session / "features.csv")}}) == {}
    assert decision(harness.path, session, {"tool_name": "apply_patch", "tool_input": {"command": "*** Begin Patch\n*** Add File: results/x.csv\n*** End Patch\n"}}) == {}


def test_a_shell_write_passes_the_hook_and_fails_the_hash_check_by_name(harness, tmp_path):
    campaign = tmp_path / "campaign"
    stage(harness, "implementation", "claude_code", campaign)
    # A shell write (nothing the hook sees) changes a page and adds a file.
    page = harness.path / "instructions" / "implementation.md"
    page.write_text(page.read_text() + "\nedited by a session's shell\n")
    (harness.path / "skills" / "backtesting" / "notes.md").write_text("new\n")
    with pytest.raises(HarnessError) as caught:
        stage(harness, "implementation", "claude_code", campaign, session_id="generic_exp_1")
    message = str(caught.value)
    assert message.startswith("the harness changed since launch: trading 0.1.0 (")
    assert "changed instructions/implementation.md; added skills/backtesting/notes.md" in message
    assert "restore the recorded content" in message


def test_the_setup_session_is_told_to_leave_the_harness_alone():
    prompt = load_prompt("execution/search_strategies/generic/prompts/harness_setup.md")
    assert "Do not modify the harness itself" in prompt
    assert "fix the environment or your own files, never the harness" in prompt
    assert "reported in your domain statement" in prompt
