"""The config every build session is constructed with, on a Claude host
and a Codex host (docs/plans/redesign/wp4-config.md, change 2): one
precedence — the adapter's structural defaults, then the host entry's
settings, then the role's effort and the session's own keys, then the
staging's merge — through `CodingAgentFactory.session_config`, which
every construction site uses."""

import inspect
from types import SimpleNamespace

import pytest

import kapso.execution.orchestrator as orchestrator_module
import kapso.execution.search_strategies.generic.difficulties_generator as difficulties_module
import kapso.execution.search_strategies.generic.ideation as ideation_module
import kapso.execution.search_strategies.generic.implementation as implementation_module
import kapso.execution.search_strategies.generic.lens_planning as lens_module
import kapso.execution.search_strategies.generic.strategy as strategy_module
from kapso.core.roles import resolve_role
from kapso.execution.coding_agents.factory import CodingAgentFactory
from kapso.execution.orchestrator import OrchestratorAgent
from kapso.harness.staging import StagedHarness
from strategy_support import generic_params, packaged_hosts

HOSTS = {
    **packaged_hosts(),
    "vertex_claude_code": {"model": "glm-5.2", "vertex_project": "p", "effort": "high"},
}


def role(host, name="implementation", **block):
    params = generic_params(host=host, **({name: block} if block else {}))
    return resolve_role(HOSTS, params, name)


def test_the_precedence_on_a_claude_host():
    config = CodingAgentFactory.session_config(role("claude_code"), {"timeout": 5, "allowed_tools": ["Read"]})
    assert config.agent_type == "claude_code" and config.model == HOSTS["claude_code"]["model"]
    assert config.debug_model == config.model
    settings = config.agent_specific
    # The adapter's structural defaults reach the session...
    assert settings["planning_mode"] is False and settings["streaming"] is True
    # ...under the host entry's settings...
    assert settings["auth_mode"] == "oauth"
    # ...under the session's own keys.
    assert settings["timeout"] == 5 and settings["allowed_tools"] == ["Read"]
    # The packaged Claude host names no effort: none is sent.
    assert settings["effort"] is None


def test_the_precedence_on_a_codex_host():
    config = CodingAgentFactory.session_config(role("codex"), {"web_search": False})
    assert config.agent_type == "codex" and config.model == HOSTS["codex"]["model"]
    settings = config.agent_specific
    assert settings["effort"] == "xhigh"                  # the host entry's
    assert settings["sandbox"] == "danger-full-access"    # the adapter's structural default
    assert settings["web_search"] is False                # the session's own key wins


def test_the_role_over_the_host_over_the_defaults():
    judge = role("codex", "judge", cli="vertex_claude_code", effort="max")
    config = CodingAgentFactory.session_config(judge, {})
    assert config.agent_type == "vertex_claude_code" and config.model == "glm-5.2"
    assert config.agent_specific["vertex_project"] == "p"         # the host entry's setting
    assert config.agent_specific["vertex_location"] == "global"   # the adapter's default
    assert config.agent_specific["effort"] == "max"               # the role's own over the host's


def test_the_staging_merges_last(tmp_path):
    staged = StagedHarness(
        module="implementation", host="claude_code", session_dir=tmp_path, session_id="s", guidance="",
        agent_specific={"settings_path": "/h/settings.json"}, env={"KAPSO_HARNESS_ROOT": "/h"},
    )
    config = CodingAgentFactory.session_config(role("claude_code"), {"env_overrides": {"A": "1"}}, staged)
    assert config.agent_specific["settings_path"] == "/h/settings.json"
    assert config.agent_specific["env_overrides"] == {"KAPSO_HARNESS_ROOT": "/h", "A": "1"}
    assert config.agent_specific["auth_mode"] == "oauth"


@pytest.fixture
def captured(monkeypatch):
    configs = []

    class Agent:
        def __init__(self, config):
            configs.append(config)

        def initialize(self, workspace):
            pass

        def generate_code(self, prompt, **kwargs):
            return SimpleNamespace(
                success=True, output="<technical_difficulties>x</technical_difficulties>",
                error=None, metadata={"tool_calls": []},
            )

        def get_cumulative_cost(self):
            return 0.0

        def cleanup(self):
            pass

    monkeypatch.setattr(CodingAgentFactory, "create", classmethod(lambda cls, config: Agent(config)))
    return configs


@pytest.mark.parametrize("host", ["claude_code", "codex"])
def test_the_judge_and_the_reconstruction_run_on_their_roles_host(host, captured, tmp_path):
    orchestrator = OrchestratorAgent.__new__(OrchestratorAgent)
    orchestrator.config = {"hosts": HOSTS}
    orchestrator.strategy_params = generic_params(host=host, judge={"timeout": 30})
    judge = orchestrator._create_feedback_generator()
    config = judge.coding_agent_config
    assert config.agent_type == host and config.model == HOSTS[host]["model"]
    assert config.agent_specific["timeout"] == 30 and config.agent_specific["streaming"] is True

    difficulties_module.generate_technical_difficulties(
        role(host), env_strip=["OPENAI_API_KEY"], timeout_seconds=60, workspace_dir=str(tmp_path),
        solution="s", stream_artifact_path=str(tmp_path / "absent.jsonl"),
    )
    config = captured[-1]
    assert config.agent_type == host and config.model == HOSTS[host]["model"]
    assert config.agent_specific["sandbox"] == "read-only"
    assert config.agent_specific["allowed_tools"] == ["Read", "Bash"]
    assert config.agent_specific["env_strip"] == ["OPENAI_API_KEY"]


def test_every_build_session_is_constructed_through_the_factory():
    """A construction site that builds a CodingAgentConfig by hand skips
    the precedence: the build modules have none."""
    for module in (
        orchestrator_module, strategy_module, ideation_module, lens_module,
        implementation_module, difficulties_module,
    ):
        assert "CodingAgentConfig(" not in inspect.getsource(module), module.__name__
