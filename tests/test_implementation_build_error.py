"""A build session that died is a fact the lane carries: run_implementation
returns the session's error beside its output, so the node can be marked
rather than read from the prose the error was folded into."""

from types import SimpleNamespace

import pytest

import kapso.execution.coding_agents.adapters.claude_code_agent as claude_module
import kapso.gated_mcp as gated_mcp_module
from kapso.execution.memories.repo_memory import RepoMemoryManager
from kapso.execution.search_strategies.generic.implementation import (
    run_implementation,
)

from test_implementation_web import MCP_TOOL, FakeWorkspace


def run_session(tmp_path, monkeypatch, result):
    """Drive run_implementation with an agent whose one session ends as ``result``."""

    class FakeAgent:
        def __init__(self, config):
            pass

        def initialize(self, workspace):
            pass

        def generate_code(self, prompt):
            return result

        def get_cumulative_cost(self):
            return 0.0

        def cleanup(self):
            pass

    monkeypatch.setattr(claude_module, "ClaudeCodeCodingAgent", FakeAgent)
    monkeypatch.setattr(
        gated_mcp_module, "get_mcp_config", lambda **kw: ({}, [MCP_TOOL])
    )
    monkeypatch.setattr(
        RepoMemoryManager,
        "ensure_exists_in_worktree",
        classmethod(lambda cls, folder: {}),
    )
    monkeypatch.setattr(
        RepoMemoryManager,
        "render_summary_and_toc",
        classmethod(lambda cls, doc, max_chars=2500: "memory"),
    )
    return run_implementation(
        solution="the plan",
        problem="the problem",
        branch_name="candidate-1",
        parent_branch_name="main",
        ideation_repo_memory_sections_consulted=None,
        lane_index=0,
        workspace=FakeWorkspace(str(tmp_path)),
        llm=None,
        registered_evaluation_manifest=None,
        sync_registered_evaluation=lambda folder: None,
        implementation_gates=["repo_memory"],
        gate_failure_policy="skip",
        implementation_cli="claude_code",
        implementation_model="the-model",
        implementation_fallback_model=None,
        implementation_web=False,
        claude_auth_settings={"auth_mode": "oauth"},
        env_strip=[],
        env_defaults={},
        lane_env=None,
        session_effort=None,
        clamped_timeout=lambda seconds: seconds,
        implementation_timeout=600,
        session_stream_path=lambda branch: str(tmp_path / f"{branch}.jsonl"),
        build_prompt=lambda **kw: "the prompt",
        previous_errors_text="",
        lane_brief="",
        note_session_started=lambda: None,
        note_session_end_facts=lambda facts: None,
        await_registered_evaluation=lambda output: None,
    )


def test_dead_session_returns_its_error_beside_its_output(tmp_path, monkeypatch):
    output, _, _, suspended, build_error = run_session(
        tmp_path, monkeypatch, SimpleNamespace(
            success=False, output="partial work",
            metadata={"tool_calls": []}, error="provider kill",
        ),
    )
    assert build_error == "provider kill"
    assert output == "Implementation failed: provider kill\n\npartial work"
    assert suspended is None


def test_finished_session_returns_no_error(tmp_path, monkeypatch):
    output, _, _, suspended, build_error = run_session(
        tmp_path, monkeypatch, SimpleNamespace(
            success=True, output="<score>null</score>",
            metadata={"tool_calls": []}, error=None,
        ),
    )
    assert build_error is None
    assert output == "<score>null</score>"
    assert suspended is None


def test_dead_session_without_an_error_message_fails_loud(tmp_path, monkeypatch):
    with pytest.raises(RuntimeError, match="failed without an error message"):
        run_session(
            tmp_path, monkeypatch, SimpleNamespace(
                success=False, output="", metadata={"tool_calls": []}, error=None,
            ),
        )
