"""`Solution.open` reads the record a build wrote, from any process: the
three shapes a build returns (delivered, waiting on the person, nothing
succeeded), what `explain()` and `diff()` say for each, the registered
evaluator, and what `open()` says before the build has returned."""

import pytest

from kapso.execution.evaluation_maintainer.registry import (
    EvaluationRegistry,
    EvaluatorVersion,
    TimingModel,
)
from kapso.execution.search_strategies.generic.feedback_generator.feedback_generator import FeedbackResult
from kapso.handles import Evaluation, Solution
from tests.handles_support import (
    candidate_branch,
    facade,
    fake_orchestrator,
    git_workspace,
    solve_result,
)


def test_a_delivered_build_reads_back_with_its_candidate_score_and_diff(tmp_path, monkeypatch):
    workspace = tmp_path / "ws"
    git_workspace(workspace)
    winner = candidate_branch(workspace, "generic_exp_2", "model.py", "improved = True\n")
    feedback = FeedbackResult(stop=True, evaluation_valid=True, feedback="AUC 0.9 beats the target", score=0.9)
    fake_orchestrator(
        monkeypatch, workspace,
        solve_result(final_feedback=feedback, stopped_reason="goal_achieved", total_cost=1.25),
        best_branch="generic_exp_2", score=0.9,
    )
    solution = facade().build("Raise AUC above 0.85", output=str(workspace))

    reopened = Solution.open(workspace)
    assert reopened == solution
    explained = reopened.explain()
    for line in (
        "Solution for: Raise AUC above 0.85",
        f"Candidate:    generic_exp_2 @ {winner}",
        "Score:        0.9",
        "Goal achieved: True",
        "Stopped:      goal_achieved",
        "Experiments:  1 this run, 1 in all",
        "Cost:         $1.250",
        "Last feedback:\nAUC 0.9 beats the target",
    ):
        assert line in explained
    assert "+improved = True" in reopened.diff()


def test_a_build_waiting_on_the_person_keeps_its_requests(tmp_path, monkeypatch):
    workspace = tmp_path / "ws"
    git_workspace(workspace)
    requests = [{"id": 1, "key": "env:OPENAI_API_KEY", "fix": "add it to .env"}]
    fake_orchestrator(monkeypatch, workspace, solve_result(stopped_reason="waiting_for_user", requests=requests))
    facade().build("g", output=str(workspace))

    reopened = Solution.open(workspace)
    assert reopened.stopped_reason == "waiting_for_user" and reopened.requests == requests
    assert reopened.branch is None and reopened.succeeded is False
    assert "Waiting on you:\n  #1  env:OPENAI_API_KEY" in reopened.explain()


def test_a_build_with_no_successful_candidate_has_no_branch_and_an_empty_diff(tmp_path, monkeypatch):
    workspace = tmp_path / "ws"
    git_workspace(workspace)
    fake_orchestrator(monkeypatch, workspace, solve_result(stopped_reason="max_iterations", stop_detail=None))
    solution = facade().build("g", output=str(workspace))

    assert (solution.branch, solution.commit, solution.score) == (None, None, None)
    assert solution.diff() == ""
    assert "Candidate:    none succeeded" in solution.explain()
    assert Solution.open(workspace) == solution


def test_the_registered_evaluator_is_recorded(tmp_path, monkeypatch):
    workspace = tmp_path / "ws"
    git_workspace(workspace)
    EvaluationRegistry(str(workspace)).register(EvaluatorVersion(
        evaluator_id="eval-1", version=1, provenance="provided", parent_evaluator=None,
        fidelity_support={}, timing=TimingModel(per_item_seconds=0.1, startup_seconds=1.0, total_items=10),
        created_at_iteration=0, reason="provided by the caller",
    ))
    fake_orchestrator(monkeypatch, workspace, solve_result(), score=0.8, best_branch="main")
    solution = facade().build("g", output=str(workspace))

    assert solution.evaluation == Evaluation(version=1, evaluator_id="eval-1", provenance="provided")
    assert Solution.open(workspace).evaluation == solution.evaluation
    assert "Score:        0.8 (evaluator v1, provided)" in solution.explain()


def test_open_before_the_build_returned_names_watch(tmp_path):
    campaign = tmp_path / "campaign"
    (campaign / ".kapso").mkdir(parents=True)
    with pytest.raises(FileNotFoundError, match="kapso watch"):
        Solution.open(campaign)


def test_open_rejects_a_record_of_another_schema(tmp_path):
    record = tmp_path / "campaign" / ".kapso" / "solution.json"
    record.parent.mkdir(parents=True)
    record.write_text('{"schema_version": 2}')
    with pytest.raises(ValueError, match="schema"):
        Solution.open(tmp_path / "campaign")
