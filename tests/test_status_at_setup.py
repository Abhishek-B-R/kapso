"""The campaign status file exists from workspace setup, and `kapso watch`
waits for it instead of crashing.

Before this, the file was created in solve(), after the seed copy and the
repo-memory bootstrap (one inference session, minutes): a watcher started
right after the launch saw a traceback, and a plugin had nothing to show.
"""

import sys
from pathlib import Path
from typing import Any, Dict, List

import pytest

import kapso.cli.watch as watch_cli
from kapso.cli import main
from kapso.execution.coding_agents.base import CodingAgentConfig
from kapso.execution.coding_agents.factory import CodingAgentFactory
from kapso.execution.memories.repo_memory import RepoMemoryManager
from kapso.execution.observability import EvolveStatus, OperationStatusView
from kapso.execution.search_strategies.base import (
    SearchNode,
    SearchStrategy,
    SearchStrategyConfig,
)


# ----------------------------------------------------------------- status


def test_a_phase_at_birth_keeps_the_state_starting(tmp_path):
    status = EvolveStatus(tmp_path / "status.json", phase="setup")
    view = OperationStatusView(status.path)
    assert view.state == "starting" and view.phase == "setup"
    assert view.data["phase_started_at"] is not None
    # Only a phase of this operation is a birth phase.
    with pytest.raises(ValueError, match="unknown evolve phase"):
        EvolveStatus(tmp_path / "other.json", phase="mine")


def test_observe_attaches_the_hook_after_birth(tmp_path):
    seen: List[Dict[str, Any]] = []
    status = EvolveStatus(tmp_path / "status.json", phase="setup")
    status.observe(seen.append)
    status.update(iteration=1)
    assert seen and seen[-1]["iteration"] == 1 and seen[-1]["state"] == "running"


def test_locate_is_none_for_a_campaign_without_a_status_yet(tmp_path):
    campaign = tmp_path / "campaign"
    (campaign / ".kapso").mkdir(parents=True)
    assert OperationStatusView.locate(campaign) is None
    assert OperationStatusView.locate(tmp_path / "nowhere") is None
    with pytest.raises(FileNotFoundError, match="no status file yet"):
        OperationStatusView(campaign)
    EvolveStatus(campaign / ".kapso" / "status.json", phase="setup")
    assert OperationStatusView.locate(campaign) == campaign / ".kapso" / "status.json"


# ------------------------------------------------------------------ watch


def _run(monkeypatch, *argv: str) -> None:
    monkeypatch.setattr(sys, "argv", ["kapso", *argv])
    main()


def test_watch_without_a_status_is_one_line_and_exit_1(tmp_path, monkeypatch, capsys):
    campaign = tmp_path / "campaign"
    (campaign / ".kapso").mkdir(parents=True)
    with pytest.raises(SystemExit) as exit_info:
        _run(monkeypatch, "watch", str(campaign))
    assert exit_info.value.code == 1
    out = capsys.readouterr().out
    assert "no status yet at" in out and "status.json" in out
    assert "Traceback" not in out


def test_watch_follow_waits_for_the_status_to_appear(tmp_path, monkeypatch, capsys):
    campaign = tmp_path / "campaign"
    (campaign / ".kapso").mkdir(parents=True)
    status_file = campaign / ".kapso" / "status.json"

    def sleep_then_arrive(seconds: float) -> None:
        # The first wait is the poll for the file; later waits are the
        # follow cadence. The file arrives, already finished, on the poll.
        if not status_file.is_file():
            status = EvolveStatus(status_file, phase="setup")
            status.done(stopped_reason="goal_achieved")

    monkeypatch.setattr(watch_cli.time, "sleep", sleep_then_arrive)
    _run(monkeypatch, "watch", str(campaign), "--follow")
    out = capsys.readouterr().out
    assert out.startswith("no status yet at")
    assert "DONE" in out


# ---------------------------------------------------------- the strategy


class _SequenceLLM:
    def __init__(self, responses: List[Any]):
        self.responses = iter(responses)

    def llm_completion(self, messages, **kwargs) -> str:
        return next(self.responses)


class _FakeCodingAgent:
    def initialize(self, workspace: str) -> None:
        self.workspace = workspace

    def supports_native_git(self) -> bool:
        return False

    def cleanup(self) -> None:
        pass

    def get_cumulative_cost(self) -> float:
        return 0.0


class _MinimalStrategy(SearchStrategy):
    def run(self, context: Any, budget_progress: float = 0.0) -> None:
        return None

    def get_experiment_history(self, best_last: bool = False) -> List[SearchNode]:
        return []

    def get_best_experiment(self) -> None:
        return None

    def checkout_to_best_experiment_branch(self) -> None:
        return None

    def export_checkpoint(self) -> None:
        return None

    def import_checkpoint(self) -> None:
        return None


def test_the_status_file_exists_before_repo_memory_bootstraps(tmp_path, monkeypatch):
    seed = tmp_path / "repo"
    seed.mkdir()
    seed.joinpath("README.md").write_text("# Example\n")
    workspace = tmp_path / "campaign"
    monkeypatch.setattr(
        CodingAgentFactory, "create", classmethod(lambda cls, config: _FakeCodingAgent())
    )
    seen_at_bootstrap: Dict[str, Any] = {}

    def bootstrap(cls, *, repo_root: str, **kwargs: Any) -> None:
        # The bootstrap is the minutes-long step: the status must already
        # be on disk, in its setup phase, when it starts.
        view = OperationStatusView(Path(repo_root))
        seen_at_bootstrap.update(state=view.state, phase=view.phase)
        RepoMemoryManager.ensure_exists_in_worktree(repo_root)

    monkeypatch.setattr(
        RepoMemoryManager, "bootstrap_baseline_model", classmethod(bootstrap)
    )
    config = SearchStrategyConfig(
        problem_handler=object(),
        llm=_SequenceLLM([]),
        coding_agent_config=CodingAgentConfig(
            agent_type="fake", model="m", debug_model="m", agent_specific={}
        ),
        initial_repo=str(seed),
        status_heartbeat_seconds=60,
    )
    strategy = _MinimalStrategy(config, workspace_dir=str(workspace))

    assert seen_at_bootstrap == {"state": "starting", "phase": "setup"}
    view = OperationStatusView(workspace)
    assert view.path == workspace / ".kapso" / "status.json"
    assert view.data["heartbeat_seconds"] == 60 and view.process_alive
    assert strategy.operation_status.path == view.path
    # Campaign state, never branch content: the seed commit and the
    # repo-memory commit leave it untracked and ignored.
    assert "status.json" not in strategy.workspace.repo.git.ls_files()
    assert ".kapso/status.json" in (workspace / ".gitignore").read_text()
    strategy.operation_status.done(stopped_reason="test")
