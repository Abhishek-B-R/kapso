"""The installed plugin stays out of campaign sessions
(docs/plans/redesign/wp7-plugin.md, change 8): the Claude adapter's one
settings argument switches it off, merged with the harness's hooks when
staged; the Codex adapter disables the person's own `kapso` server,
trusts the workspace and writes there the execpolicy rule refusing the
campaign verbs."""

import json
import shutil

from kapso.execution.coding_agents.adapters.claude_code_agent import PLUGIN_ID, ClaudeCodeCodingAgent
from kapso.execution.coding_agents.adapters.codex_agent import CAMPAIGN_RULES, CAMPAIGN_RULES_FILE, CodexCodingAgent
from kapso.execution.coding_agents.base import CodingAgentConfig


def _config(agent_type, **agent_specific):
    return CodingAgentConfig(agent_type=agent_type, model="m", debug_model="m", agent_specific=agent_specific)


def test_a_claude_code_session_switches_the_plugin_off_in_its_settings(tmp_path, monkeypatch):
    monkeypatch.setattr(shutil, "which", lambda name: f"/usr/bin/{name}")
    assert PLUGIN_ID == "kapso@kapso"
    bare = ClaudeCodeCodingAgent(_config("claude_code"))._build_command("m")
    assert json.loads(bare[bare.index("--settings") + 1]) == {"enabledPlugins": {PLUGIN_ID: False}}
    hooks = {"hooks": {"Stop": [{"hooks": [{"type": "command", "command": "python3 /h/require_results.py"}]}]}}
    staged_file = tmp_path / "harness-hooks.json"
    staged_file.write_text(json.dumps(hooks), encoding="utf-8")
    staged = ClaudeCodeCodingAgent(_config("claude_code", settings_path=str(staged_file)))._build_command("m")
    assert json.loads(staged[staged.index("--settings") + 1]) == {**hooks, "enabledPlugins": {PLUGIN_ID: False}}


def test_a_codex_session_disables_the_persons_server_and_refuses_the_verbs_by_rule(tmp_path, monkeypatch):
    monkeypatch.setattr(shutil, "which", lambda name: f"/usr/bin/{name}")
    workspace = tmp_path / "ws"
    workspace.mkdir()
    agent = CodexCodingAgent(_config("codex"))
    agent.initialize(str(workspace))
    assert (workspace / CAMPAIGN_RULES_FILE).read_text(encoding="utf-8") == CAMPAIGN_RULES
    for verb in ("build", "learn", "deploy"):
        assert f'prefix_rule(pattern = ["kapso", "{verb}"], decision = "forbidden", justification = "never inside a Kapso campaign session' in CAMPAIGN_RULES
    joined = " ".join(agent._exec_command("m", "/tmp/last.txt"))
    assert "-c mcp_servers.kapso.enabled=false" in joined
    assert f'-c projects."{workspace}".trust_level="trusted"' in joined
