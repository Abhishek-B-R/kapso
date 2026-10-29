"""The bundled harnesses' hooks on both hosts' event shapes
(docs/plans/redesign/wp8-harness-ports.md, change 4): each copied hook
decides the same way on Claude Code's file-tool event and on Codex's
`apply_patch` event, denies with its reason, and lets the rest through;
the manifest lists each where its rule applies."""

import json
import subprocess
import sys

import pytest
import yaml

from kapso.harness import BUNDLED_ROOT

PREDICTIVE = BUNDLED_ROOT / "predictive-modelling"


def run_hook(harness, name, script, event):
    completed = subprocess.run(
        [sys.executable, str(harness / "hooks" / name / script)],
        input=json.dumps(event), capture_output=True, text=True, check=True, cwd=str(harness),
    )
    return json.loads(completed.stdout) if completed.stdout.strip() else {}


CLAUDE_WRITE = {"tool_name": "Write", "tool_input": {"file_path": "prepared/cache/db/users.parquet", "content": "x"}}
CODEX_PATCH = {"tool_name": "apply_patch", "tool_input": {"command": "*** Begin Patch\n*** Update File: prepared/cache/db/users.parquet\n*** End Patch"}}


@pytest.mark.parametrize("event", [CLAUDE_WRITE, CODEX_PATCH], ids=["claude-code", "codex"])
def test_protect_prepared_denies_a_write_under_prepared_on_both_hosts(event):
    decision = run_hook(PREDICTIVE, "protect-prepared", "protect_prepared.py", event)
    output = decision["hookSpecificOutput"]
    assert output["hookEventName"] == "PreToolUse" and output["permissionDecision"] == "deny"
    assert "prepared/" in output["permissionDecisionReason"] and "read-only" in output["permissionDecisionReason"]


@pytest.mark.parametrize("event", [
    {"tool_name": "Write", "tool_input": {"file_path": "features/users.parquet", "content": "x"}},
    {"tool_name": "apply_patch", "tool_input": {"command": "*** Begin Patch\n*** Add File: features/build.py\n*** End Patch"}},
], ids=["claude-code", "codex"])
def test_protect_prepared_lets_other_writes_through(event):
    assert run_hook(PREDICTIVE, "protect-prepared", "protect_prepared.py", event) == {}


@pytest.mark.parametrize("command", ["curl https://x/data.zip", "wget -q https://x", "pip download x | aria2c -"])
def test_deny_web_fetch_denies_the_shells_fetchers_with_this_domains_reason(command):
    decision = run_hook(PREDICTIVE, "deny-web-fetch", "deny_web_fetch.py", {"tool_name": "Bash", "tool_input": {"command": command}})
    reason = decision["hookSpecificOutput"]["permissionDecisionReason"]
    assert decision["hookSpecificOutput"]["permissionDecision"] == "deny"
    assert reason.startswith("Web fetches are off in implementation and verification") and "prepared copy" in reason


def test_deny_web_fetch_lets_other_commands_through():
    for command in ("ls prepared/", "python main.py --debug", "git status"):
        assert run_hook(PREDICTIVE, "deny-web-fetch", "deny_web_fetch.py", {"tool_name": "Bash", "tool_input": {"command": command}}) == {}


def test_the_manifest_puts_each_hook_where_its_rule_applies():
    """The prepared copy is read-only in every build module after setup (the
    setup session is the one that writes it); the web is off where a
    candidate's code is written and checked, and on in setup, where the task
    may grant a hub."""
    modules = yaml.safe_load((PREDICTIVE / "harness.yaml").read_text())["modules"]
    hooks = {module: set(entry.get("hooks", [])) for module, entry in modules.items()}
    assert "protect-prepared" not in hooks["setup"]
    for module in ("ideation", "implementation", "verification", "feedback"):
        assert "protect-prepared" in hooks[module], module
    assert {module for module, listed in hooks.items() if "deny-web-fetch" in listed} == {"implementation", "verification"}
