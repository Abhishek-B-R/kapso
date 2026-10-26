"""The engine's own sessions in the record (docs/plans/redesign/
wp4-config.md, change 9): the difficulties reconstruction staged and
recorded under `difficulties/<branch>`, its prompt reading the branch;
the build-time inference sessions recorded under `engine/<role>/<n>`;
every build session on Claude Code mounting only the engine's servers;
each session's MCP config in its own directory; the workspace
initialising with no agent."""

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

import kapso.execution.coding_agents.factory as factory_module
from kapso.core.cli_inference import CliInference
from kapso.core.roles import resolve_role
from kapso.execution.coding_agents.adapters.claude_code_agent import ClaudeCodeCodingAgent
from kapso.execution.coding_agents.factory import CodingAgentFactory
from kapso.execution.search_strategies.base import SearchNode
from kapso.execution.search_strategies.generic.strategy import GenericSearch
from kapso.harness.staging import engine_session_record
from strategy_support import generic_params, packaged_hosts

HOSTS = packaged_hosts()


@pytest.fixture
def captured(monkeypatch):
    calls = []

    class Agent:
        def __init__(self, config):
            self.config = config

        def initialize(self, workspace):
            pass

        def generate_code(self, prompt, **kwargs):
            calls.append({"config": self.config, "prompt": prompt})
            return SimpleNamespace(
                success=True, output="<technical_difficulties>rebuilt</technical_difficulties>",
                error=None, metadata={},
            )

        def get_cumulative_cost(self):
            return 0.0

        def cleanup(self):
            pass

    monkeypatch.setattr(factory_module.CodingAgentFactory, "create", classmethod(lambda cls, config: Agent(config)))
    return calls


def test_the_reconstruction_is_staged_and_reads_the_branch(tmp_path, captured):
    s = GenericSearch.__new__(GenericSearch)
    s.harness = None
    s.workspace_dir = str(tmp_path)
    s.iteration_count = 1
    s.budget_snapshot = None
    s.budget_snapshot_monotonic = None
    s.finishing_cut = None
    s.env_strip = []
    s.implementation_role = resolve_role(HOSTS, generic_params(host="claude_code"), "implementation")
    node = SearchNode(node_id=3, branch_name="generic_exp_3", parent_branch_name="generic_exp_1", solution="the plan")

    s._ensure_technical_difficulties(node)

    assert node.technical_difficulties == "rebuilt"
    (call,) = captured
    record_path = tmp_path / ".kapso" / "sessions" / "difficulties" / "generic_exp_3" / "session.json"
    assert call["config"].agent_specific["session_record_path"] == str(record_path)
    record = json.loads(record_path.read_text())
    assert record["module"] == "implementation" and record["host"] == "claude_code" and record["harness"] is None
    assert "git log --oneline generic_exp_1..generic_exp_3" in call["prompt"]
    assert "git diff --stat generic_exp_1..generic_exp_3" in call["prompt"]
    assert call["config"].agent_specific["allowed_tools"] == ["Read", "Bash"]


def test_an_inference_session_is_recorded_under_engine_role_n(tmp_path):
    configs = []

    class Factory:
        @staticmethod
        def create(config):
            configs.append(config)
            return SimpleNamespace(
                initialize=lambda workspace: None,
                generate_code=lambda prompt, timeout_seconds=None: SimpleNamespace(success=True, output="done", error=None),
                get_cumulative_cost=lambda: 0.0,
                cleanup=lambda: None,
            )

    inference = {
        "default": {"cli": "claude_code", "model": "claude-opus-5", "effort": None, "sandbox": "read-only", "timeout_seconds": 60},
        "roles": {"repo_memory": {"timeout_seconds": 30}},
    }
    llm = CliInference(inference=inference, models={"embedding": None}, agent_factory=Factory)
    # Nothing recorded until the orchestrator names the campaign's records.
    assert llm._run_session("p", "repo_memory") == "done"
    assert "session_record_path" not in configs[0].agent_specific
    records = tmp_path / ".kapso" / "sessions"
    llm.record_session = lambda role, host, session_dir: engine_session_record(records, role, host, session_dir)
    llm._run_session("p", "repo_memory")
    llm._run_session("p", "repo_memory")
    llm._run_session("p", None)
    labels = [Path(config.agent_specific["session_record_path"]).relative_to(records).as_posix() for config in configs[1:]]
    assert labels == ["engine/repo_memory/1/session.json", "engine/repo_memory/2/session.json", "engine/default/1/session.json"]
    record = json.loads((records / "engine" / "repo_memory" / "1" / "session.json").read_text())
    assert record["module"] == "engine" and record["host"] == "claude_code" and record["runs"] == []
    assert configs[1].agent_specific["stream_artifact_path"].endswith("engine/repo_memory/1/stream.jsonl")


def test_every_build_session_mounts_only_the_engines_servers():
    role = resolve_role(HOSTS, generic_params(host="claude_code"), "judge")
    assert CodingAgentFactory.session_config(role, {}).agent_specific["strict_mcp_config"] is True


def test_two_sessions_keep_their_own_mcp_config(tmp_path):
    """Ensemble members run concurrently in one workspace: each keeps its
    MCP config with its own record, and one's cleanup leaves the other's;
    a session without a record keeps it in its workspace."""
    def agent(record):
        instance = ClaudeCodeCodingAgent.__new__(ClaudeCodeCodingAgent)
        instance.workspace = str(tmp_path)
        instance._mcp_servers = {"gated-knowledge": {"command": "kapso-mcp"}}
        instance._session_record_path = record
        instance._mcp_config_path = None
        return instance

    first = agent(str(tmp_path / ".kapso" / "sessions" / "a" / "session.json"))
    second = agent(str(tmp_path / ".kapso" / "sessions" / "b" / "session.json"))
    (tmp_path / ".kapso" / "sessions" / "a").mkdir(parents=True)
    (tmp_path / ".kapso" / "sessions" / "b").mkdir(parents=True)
    first._mcp_config_path = first._write_mcp_config()
    second._mcp_config_path = second._write_mcp_config()
    assert first._mcp_config_path == tmp_path / ".kapso" / "sessions" / "a" / ".claude_mcp" / "mcp_config.json"
    assert second._mcp_config_path == tmp_path / ".kapso" / "sessions" / "b" / ".claude_mcp" / "mcp_config.json"
    first.cleanup()
    assert not first._mcp_config_path and second._mcp_config_path.exists()
    plain = agent(None)
    assert plain._write_mcp_config() == tmp_path / ".claude_mcp" / "mcp_config.json"


def test_the_workspace_initialises_with_no_agent():
    assert not hasattr(GenericSearch, "_initialize_workspace")
