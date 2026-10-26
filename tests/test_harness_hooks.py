"""The trading example's web hooks (docs/plans/redesign/wp4-config.md,
change 6): `deny-web` denies the native web tools on implementation with
the reason, `deny-web-fetch` denies the shell's fetchers on every module;
the manifest says where each applies."""

import json
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

TRADING = Path(__file__).resolve().parent.parent / "examples" / "harnesses" / "trading"


def run_hook(name: str, script: str, event: dict) -> dict:
    """The hook's decision for one event, as the host would read it:
    an empty mapping when the hook lets the call through."""
    completed = subprocess.run(
        [sys.executable, str(TRADING / "hooks" / name / script)],
        input=json.dumps(event), capture_output=True, text=True, check=True, cwd=str(TRADING),
    )
    return json.loads(completed.stdout) if completed.stdout.strip() else {}


@pytest.mark.parametrize("tool", ["WebSearch", "WebFetch"])
def test_deny_web_denies_the_native_tools_with_the_reason(tool):
    decision = run_hook("deny-web", "deny_web.py", {"tool_name": tool, "tool_input": {"query": "SPY 2025"}})
    output = decision["hookSpecificOutput"]
    assert output["hookEventName"] == "PreToolUse" and output["permissionDecision"] == "deny"
    assert output["permissionDecisionReason"].startswith(f"{tool} is off in implementation")
    assert "pinned snapshot" in output["permissionDecisionReason"]


@pytest.mark.parametrize("command", ["curl https://x/bars.csv", "wget -q https://x", "pip download x | aria2c -"])
def test_deny_web_fetch_denies_the_shells_fetchers(command):
    decision = run_hook("deny-web-fetch", "deny_web_fetch.py", {"tool_name": "Bash", "tool_input": {"command": command}})
    assert decision["hookSpecificOutput"]["permissionDecision"] == "deny"
    assert "Use get_bars" in decision["hookSpecificOutput"]["permissionDecisionReason"]


def test_deny_web_fetch_lets_other_commands_through():
    for command in ("ls prepared/", "python backtest.py --curl-free", "git status"):
        assert run_hook("deny-web-fetch", "deny_web_fetch.py", {"tool_name": "Bash", "tool_input": {"command": command}}) == {}


def test_the_manifest_puts_each_hook_where_its_rule_applies():
    """The native web tools are the ideation sessions' research and the
    implementation's leak: `deny-web` is the implementation module's
    alone; the shell's fetchers make attempts incomparable anywhere."""
    modules = yaml.safe_load((TRADING / "harness.yaml").read_text())["modules"]
    assert {name for name, module in modules.items() if "deny-web" in module["hooks"]} == {"implementation"}
    assert all("deny-web-fetch" in module["hooks"] for module in modules.values())
    hook = json.loads((TRADING / "hooks" / "deny-web" / "hook.json").read_text())
    assert [entry["matcher"] for entry in hook["hooks"]["PreToolUse"]] == ["WebSearch|WebFetch"]
