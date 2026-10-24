"""`Kapso.build()`: the brief is the engine's goal, whole; budgets resolve
call over brief over launch record over config; a resume reads the brief
back from the checkpoint; the record a build writes has one pinned shape
and `Solution.open` reads it back."""

import json

import pytest

from kapso.execution.inbox import write_launch_record
from kapso.execution.run_checkpoint import RunCheckpoint, RunCheckpointStore, config_fingerprint
from kapso.execution.search_strategies.generic.feedback_generator.feedback_generator import FeedbackResult
from kapso.handles import Brief, Budget, Solution
from kapso.kapso import DEFAULT_MAX_ITERATIONS
from tests.handles_support import (
    candidate_branch,
    facade,
    fake_orchestrator,
    git_workspace,
    solve_result,
)

RECORD_KEYS = [
    "schema_version", "brief", "trace", "branch", "commit", "base_commit", "score",
    "succeeded", "stopped_reason", "stop_detail", "iterations", "cumulative_iterations",
    "cost_usd", "requests", "feedback", "evaluation", "harness", "experience",
    "invalid_evaluations", "external_metrics", "external_primary_metric", "kg_index",
    "bank_head_served",
]


def test_a_sentence_becomes_a_brief_and_the_whole_brief_is_the_engines_goal(tmp_path, monkeypatch):
    workspace = tmp_path / "ws"
    git_workspace(workspace)
    captured = fake_orchestrator(monkeypatch, workspace, solve_result())

    solution = facade().build("Raise AUC above 0.85", output=str(workspace))

    rendered = Brief(objective="Raise AUC above 0.85").render()
    assert captured["goal"] == rendered
    assert captured["handler"].problem_description == f"# Goal\n{rendered}"
    assert solution.brief == Brief(objective="Raise AUC above 0.85")
    assert solution.trace == workspace.resolve()
    assert (workspace / ".kapso" / "solution.json").is_file()
    assert Solution.open(workspace) == solution


def test_a_large_brief_reaches_the_prompt_whole(tmp_path, monkeypatch):
    """Rule 6 at the prompt boundary: every line the engineer wrote is in
    the problem description the engine hands to the model, and the goal
    text parses back to the same brief."""
    paragraphs = [f"Paragraph {i}: " + ("detail " * 60).strip() for i in range(120)]
    objective = "\n\n".join(paragraphs) + (
        "\n\nThe failing test:\n"
        "    def test_contract():\n"
        "        assert predict(rows).shape == (len(rows),)"
    )
    assert len(objective) > 50_000
    brief = Brief(
        objective=objective,
        measured_by="evaluation/evaluate.py",
        rules=["the evaluator is never modified", "no fitting on the held-out rows"],
        budget=Budget(minutes=5),
    )
    workspace = tmp_path / "ws"
    git_workspace(workspace)
    captured = fake_orchestrator(monkeypatch, workspace, solve_result())

    facade().build(brief, output=str(workspace))

    problem = captured["handler"].problem_description
    for line in objective.splitlines():
        assert line in problem
    assert "the evaluator is never modified" in problem
    assert "Measured by  evaluation/evaluate.py" in problem
    assert Brief.parse(captured["goal"]) == brief


def test_budget_precedence_is_the_call_then_the_brief_then_the_default(tmp_path, monkeypatch):
    workspace = tmp_path / "ws"
    git_workspace(workspace)
    captured = fake_orchestrator(monkeypatch, workspace, solve_result())
    brief = Brief(objective="g", budget=Budget(minutes=30, iterations=4))

    facade().build(brief, output=str(workspace), budget=Budget(iterations=2))
    assert captured["solve"] == {
        "experiment_max_iter": 2, "time_budget_minutes": 30,
        "cost_budget": None, "finalization_reserve_minutes": None,
    }

    other = tmp_path / "other"
    git_workspace(other)
    captured = fake_orchestrator(monkeypatch, other, solve_result())
    facade().build("g", output=str(other))
    assert captured["solve"]["experiment_max_iter"] == DEFAULT_MAX_ITERATIONS
    assert captured["solve"]["time_budget_minutes"] is None


def test_build_needs_a_goal_unless_resuming():
    with pytest.raises(ValueError, match="needs a goal"):
        facade().build()
    with pytest.raises(TypeError, match="string or a Brief"):
        facade().build(42)


def _checkpoint(goal: str) -> RunCheckpoint:
    return RunCheckpoint.create(
        strategy_type="generic", goal=goal, config_fingerprint=config_fingerprint({"m": 1}),
        status="running", completed_iterations=2, cumulative_cost=0.0,
        current_feedback=None, strategy_state={"node_history": []},
    )


def _launch_record(workspace, **values):
    record = {
        "config_path": None, "kg_index": None, "mode": None, "coding_agent": None,
        "output_path": str(workspace), "max_iterations": 3, "time_budget_minutes": 60.0,
        "cost_budget": None, "finalization_reserve_minutes": None, "eval_dir": None,
        "data_dir": None, "additional_context": "", "context": None, "serving_scope": None,
        "resumable_from_inbox": True, "dotenv_path": "",
    }
    record.update(values)
    write_launch_record(workspace, record)


def test_a_resume_reads_the_brief_from_the_checkpoint_and_the_budget_from_the_record(tmp_path, monkeypatch):
    workspace = tmp_path / "ws"
    git_workspace(workspace)
    brief = Brief(objective="Raise accuracy above 0.85", rules=["no peeking at the test set"])
    RunCheckpointStore(str(workspace)).save(_checkpoint(brief.render()))
    _launch_record(workspace)
    captured = fake_orchestrator(monkeypatch, workspace, solve_result(cumulative_iterations=3))

    solution = facade().build(output=str(workspace), resume=True)

    assert captured["goal"] == brief.render() and captured["resume"] is True
    assert solution.brief == brief
    assert captured["solve"]["experiment_max_iter"] == 3
    assert captured["solve"]["time_budget_minutes"] == 60.0

    # A budget named on the resume wins over the record, field by field.
    captured = fake_orchestrator(monkeypatch, workspace, solve_result(cumulative_iterations=4))
    facade().build(output=str(workspace), resume=True, budget=Budget(minutes=90))
    assert captured["solve"]["experiment_max_iter"] == 3
    assert captured["solve"]["time_budget_minutes"] == 90


def test_the_record_has_the_pinned_shape_and_names_the_delivered_commit(tmp_path, monkeypatch):
    workspace = tmp_path / "ws"
    base = git_workspace(workspace)
    winner = candidate_branch(workspace, "generic_exp_1", "model.py", "improved = True\n")
    feedback = FeedbackResult(stop=True, evaluation_valid=True, feedback="AUC 0.9 beats the target", score=0.9)
    fake_orchestrator(
        monkeypatch, workspace,
        solve_result(final_feedback=feedback, stopped_reason="goal_achieved", total_cost=1.25),
        best_branch="generic_exp_1", score=0.9,
    )

    solution = facade().build("g", output=str(workspace))

    record = json.loads((workspace / ".kapso" / "solution.json").read_text())
    assert list(record) == RECORD_KEYS
    assert record["schema_version"] == 1
    assert record["brief"] == Brief(objective="g").to_dict()
    assert (record["branch"], record["commit"], record["base_commit"]) == ("generic_exp_1", winner, base)
    assert (record["score"], record["succeeded"], record["stopped_reason"]) == (0.9, True, "goal_achieved")
    assert record["cost_usd"] == 1.25 and record["feedback"] == "AUC 0.9 beats the target"
    assert record["evaluation"] is None and record["harness"] is None and record["experience"] == []
    assert "+improved = True" in solution.diff()
