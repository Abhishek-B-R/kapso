"""The benchmark runners' solve paths (docs/plans/redesign/wp4-config.md,
change 11): each runner is entered through its own path with the
provider boundary stubbed (the sessions and the inference client) over
the real resolver, factory, staging, orchestrator and record, and what
the campaign resolves to is pinned to the former mode's values: the
roles, the inbox, the reserve and the session deadlines. A runner that
shapes its settings to the run writes a runtime file that resolves as an
override file, and the campaign runs on that file."""

import argparse
import json
import sys
import types
from pathlib import Path

import pytest

import kapso.execution.orchestrator as orchestrator_module
from kapso.core.config import load_config, read_yaml
from kapso.execution.orchestrator import OrchestratorAgent
from tests.harness_support import FakeLLM, FakeProblemHandler, NoopAgent

# The packaged codex host, which every benchmark's implementation runs on.
CODEX = ("codex", "gpt-5.6-sol", "xhigh")
FROZEN_CLOCK = 1_700_000_000.0


class FakeBenchmarkHandler(FakeProblemHandler):
    """A benchmark's handler without its data: the runner's path after
    the campaign reads a final evaluation and, for RelBench, the task's
    directories."""

    def __init__(self, work_dir=None, shared_cache_dir=None):
        self.work_dir = work_dir
        self.shared_cache_dir = shared_cache_dir

    def final_evaluate(self, path, **kwargs):
        return {"evaluated": str(path)}


@pytest.fixture
def entered(monkeypatch, tmp_path):
    """The engine's boundary stubbed: every session a NoopAgent, the
    inference client fake, no judge; `solve()` records the orchestrator
    it was called on and its arguments instead of running a campaign.
    The working directory is the test's: a runner without a workspace
    argument builds under it."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(orchestrator_module.CodingAgentFactory, "create", staticmethod(lambda config: NoopAgent(config)))
    monkeypatch.setattr(orchestrator_module, "CliInference", FakeLLM)
    monkeypatch.setattr(OrchestratorAgent, "_create_feedback_generator", lambda self: object())
    calls = []
    monkeypatch.setattr(OrchestratorAgent, "solve", lambda self, **kwargs: calls.append((self, kwargs)))
    return calls


def facts(role):
    """A resolved role, as a tuple a snapshot reads at a glance."""
    return (role.cli, role.model, role.effort, role.timeout, role.web)


def no_signal(monkeypatch, runner):
    """The runner's SIGTERM handler, kept off the test process."""
    monkeypatch.setattr(runner, "signal", types.SimpleNamespace(signal=lambda *args: None, SIGTERM=15))


def test_mle_runner_enters_the_campaign_with_the_former_mode(entered, monkeypatch):
    from benchmarks.mle import runner

    seen = {}

    def handler(competition_id, fetch_huggingface_models):
        seen["fetch_huggingface_models"] = fetch_huggingface_models
        return FakeBenchmarkHandler()

    monkeypatch.setattr(runner, "MleBenchHandler", handler)
    result = runner.solve_competition("spooky-author-identification", max_iterations=3)
    (orchestrator, kwargs), = entered
    assert orchestrator.config_path == runner.CONFIG_PATH and kwargs == {"experiment_max_iter": 3}
    assert seen == {"fetch_huggingface_models": True}
    strategy = orchestrator.search_strategy
    # Ideation on Claude Code with the packaged model; implementation and
    # the judge on codex with the mode's deadlines; the web on.
    assert facts(strategy.ideation_role) == ("claude_code", "claude-opus-5", None, None, True)
    assert facts(strategy.implementation_role) == (*CODEX, 14400.0, True)
    assert facts(strategy.judge_role) == (*CODEX, 900.0, True)
    assert strategy.params["ideation"]["gates"] == ["research", "experiment_history", "repo_memory"]
    assert strategy.params["implementation"]["gates"] == ["research", "repo_memory"]
    assert strategy.params["gate_failure_policy"] == "skip"
    assert strategy.inbox_settings["enabled"] is False
    assert orchestrator.budget_spec.finalization_reserve_seconds is None
    assert orchestrator._config_budget["min_iteration_seconds"] == 60
    assert result["private_evaluation"] == {"evaluated": strategy.workspace.workspace_dir}


def test_ale_runner_enters_the_campaign_with_the_former_mode(entered, monkeypatch):
    from benchmarks.ale import runner

    monkeypatch.setattr(runner, "AleBench", lambda problem_id: FakeBenchmarkHandler())
    result = runner.solve_problem("ahc039", max_iterations=2)
    (orchestrator, kwargs), = entered
    assert orchestrator.config_path == runner.CONFIG_PATH and kwargs == {"experiment_max_iter": 2}
    strategy = orchestrator.search_strategy
    assert facts(strategy.ideation_role) == ("claude_code", "claude-opus-5", None, None, True)
    assert facts(strategy.implementation_role) == (*CODEX, 7200.0, True)
    assert facts(strategy.judge_role) == (*CODEX, 900.0, True)
    assert strategy.params["ideation"]["gates"] == ["research", "experiment_history", "repo_memory"]
    assert strategy.inbox_settings["enabled"] is False
    assert read_yaml(runner.CONFIG_PATH)["benchmark"] == {"use_knowledge_graph": False}
    assert result["problem_id"] == "ahc039" and result["private_evaluation"] == {"evaluated": strategy.workspace.workspace_dir}


def test_relbench_runner_runs_on_the_runtime_file_it_writes(entered, monkeypatch, tmp_path):
    import benchmarks.relbench.handler as handler_module
    from benchmarks.relbench import runner

    work_dir = tmp_path / "work"
    work_dir.mkdir()
    cache = tmp_path / "cache"
    monkeypatch.setattr(
        handler_module, "RelBenchHandler", lambda **kwargs: FakeBenchmarkHandler(work_dir=work_dir, shared_cache_dir=cache),
    )
    args = argparse.Namespace(
        dataset="rel-f1", task="driver-position", iterations=4, coding_agent=None, no_kg=False,
        workspace=str(tmp_path / "workspace"), resume=False, target_val=None, rebuild_cache=False,
        knowledge_file=None, experience=None, initial_repo=None, time_budget_hours=2.0,
    )
    report = runner.solve_task(args)
    (orchestrator, kwargs), = entered
    # The runtime file: this benchmark's file with the task's cache and the
    # run's budget over it, resolving as an override file, the campaign's.
    runtime = work_dir / ".kapso_runtime" / "config.yaml"
    assert orchestrator.config_path == str(runtime) and kwargs == {"experiment_max_iter": 4}
    config = load_config(str(runtime))
    assert config["search_strategy"]["params"]["shared_cache_dir"] == str(cache)
    assert config["budget"]["minutes"] == 120 and config["budget"]["reserve_minutes"] == 15
    assert config["budget"]["min_iteration_seconds"] == 1800 and config["budget"]["checkpoint_heartbeat_seconds"] == 300
    assert config["evaluation_maintainer"]["enabled"] is True and config["evaluation_maintainer"]["timeout"] == 1800
    assert config["evaluation_maintainer"]["calibration_timeout_seconds"] == 1200
    strategy = orchestrator.search_strategy
    assert str(strategy.shared_cache_dir) == str(cache)
    # The former mode: codex everywhere but the Claude member and the lens
    # planner; no web for implementation (the temporal-leakage protocol).
    assert facts(strategy.ideation_role) == (*CODEX, 86400.0, True)
    assert facts(strategy.implementation_role) == (*CODEX, 18000.0, False)
    assert facts(strategy.judge_role) == (*CODEX, 900.0, True)
    assert [facts(member) for member in strategy.ideation_ensemble] == [
        (*CODEX, None, True), ("claude_code", "claude-fable-5", "xhigh", None, True),
    ]
    assert facts(strategy.ideation_lens_planner) == ("claude_code", "claude-fable-5", "max", 600.0, True)
    assert facts(strategy.ideation_selector) == (*CODEX, None, True)
    assert strategy.params["ideation"]["candidates_per_member"] == 3
    assert strategy.params["ideation"]["ensemble_time_split"] == {"member_fraction": 0.7, "selector_fraction": 0.3}
    assert strategy.params["ideation"]["gates"] == ["experiment_history", "repo_memory", "bank"]
    assert strategy.params["implementation"]["gates"] == ["repo_memory", "bank"]
    assert strategy.node_expansion_value == 4
    assert [lane["CUDA_VISIBLE_DEVICES"] for lane in strategy.expansion_lane_env] == ["0", "1", "2", "3"]
    assert strategy.inbox_settings["enabled"] is False
    assert orchestrator.budget_spec.time_budget_seconds == 7200.0
    assert orchestrator.budget_spec.finalization_reserve_seconds == 900.0
    # The provided grader is the campaign's evaluation, fingerprinted.
    assert orchestrator._provided_evaluation_manifest
    assert report["workspace"] == str(tmp_path / "workspace") and report["cost_usd"] == 0.0


def test_ioai_runner_shapes_the_session_deadlines_to_the_run(entered, monkeypatch, tmp_path):
    from benchmarks.ioai2026 import runner

    root = tmp_path / "run"
    task = root / "task"
    (task / "dataset").mkdir(parents=True)
    (task / "dataset" / "statement.md").write_text("# Practice task\n\nPredict the label of every test row.\n")
    (task / "kaggle.json").write_text(json.dumps({"competition": "ioai-2026-ai-models-track-practice-task-1"}))
    repo_root = tmp_path / "repo"
    bank = repo_root / "benchmarks" / "ioai2026" / "knowledge_bank"
    bank.mkdir(parents=True)
    (bank / "INDEX.md").write_text("# Index\n")
    monkeypatch.setattr(runner, "REPO_ROOT", str(repo_root))
    # The clock frozen: the budget is the two hours, nothing spent.
    monkeypatch.setattr(runner, "time", types.SimpleNamespace(time=lambda: FROZEN_CLOCK))
    no_signal(monkeypatch, runner)
    monkeypatch.setattr(sys, "argv", ["runner", "--root", str(root), "--hours", "2", "--iterations", "5", "--skip-final-eval"])
    runner.main()
    (orchestrator, kwargs), = entered
    # Two hours, no guard, no harvest window, no reserve (the mode's).
    assert kwargs == {"experiment_max_iter": 5, "time_budget_minutes": 120, "cost_budget": None, "finalization_reserve_minutes": 0}
    runtime = task / ".kapso_runtime" / "config.yaml"
    assert orchestrator.config_path == str(runtime)
    config = load_config(str(runtime))
    params = config["search_strategy"]["params"]
    # The session ceilings shrunk to the run: min(14400, 2h).
    assert params["ideation"]["timeout"] == 7200 and params["implementation"]["timeout"] == 7200
    assert params["node_expansion_value"] == 8
    strategy = orchestrator.search_strategy
    assert facts(strategy.ideation_role) == (*CODEX, 7200.0, True)
    assert facts(strategy.implementation_role) == (*CODEX, 7200.0, True)
    assert strategy.implementation_fallback_model == "gpt-5.5"
    assert facts(strategy.judge_role) == (*CODEX, 900.0, True)
    assert [facts(member) for member in strategy.ideation_ensemble] == [
        (*CODEX, None, True), ("claude_code", "claude-fable-5", "max", None, True),
    ]
    assert facts(strategy.ideation_lens_planner) == ("claude_code", "claude-fable-5", "high", 600.0, True)
    assert facts(strategy.ideation_selector) == (*CODEX, None, True)
    assert strategy.params["ideation"]["candidates_per_member"] == 5
    assert strategy.params["ideation"]["gates"] == ["experiment_history", "repo_memory"]
    assert strategy.params["implementation"]["gates"] == ["repo_memory"]
    assert strategy.node_expansion_value == 8
    assert [lane["CUDA_VISIBLE_DEVICES"] for lane in strategy.expansion_lane_env] == [str(index) for index in range(8)]
    assert strategy.inbox_settings["enabled"] is False
    assert orchestrator._config_budget["min_iteration_seconds"] == 900
    assert orchestrator.problem_handler.insured_reserve_seconds == 300.0
    # The runner's own staging beside the task, and its summary.
    assert (task / "RULES.md").is_file() and (task / "KAGGLE_CLI.md").is_file()
    assert (task / "knowledge_bank" / "INDEX.md").is_file()
    assert json.loads((task / ".kernel_slots_config.json").read_text())["gpu"] == 2
    assert json.loads((root / "results.json").read_text())["hours"] == 2.0


def test_past_learning_runner_shapes_the_reserve_and_the_deadlines_to_the_run(entered, monkeypatch, tmp_path):
    from benchmarks.ioai2026.past_learning import runner

    root = tmp_path / "run"
    task = root / "task"
    (task / "dataset").mkdir(parents=True)
    (task / "dataset" / "statement.md").write_text("# Past contest\n\nClassify the images.\n")
    (task / "task_meta.json").write_text(json.dumps({
        "task_name": "ioai-2025-practice", "self_check_command": "python self_check.py", "metric_name": "accuracy",
    }))
    no_signal(monkeypatch, runner)
    monkeypatch.setattr(sys, "argv", ["runner", "--root", str(root), "--hours", "2", "--iterations", "6", "--skip-final-eval"])
    runner.main()
    (orchestrator, kwargs), = entered
    # Two hours less the five-minute guard; the reserve a tenth of that,
    # within its bounds.
    assert kwargs == {"experiment_max_iter": 6, "time_budget_minutes": 115, "cost_budget": None, "finalization_reserve_minutes": 11.5}
    runtime = task / ".kapso_runtime" / "config.yaml"
    assert orchestrator.config_path == str(runtime)
    config = load_config(str(runtime))
    assert config["hosts"]["claude_code"] == {"model": "claude-opus-4-8", "auth_mode": "oauth", "effort": "max"}
    strategy = orchestrator.search_strategy
    # Shaped to the run: ideation a fifth of two hours, implementation
    # three quarters; no web in either role (the leakage protocol).
    assert facts(strategy.ideation_role) == ("claude_code", "claude-opus-4-8", "max", 1440.0, False)
    assert facts(strategy.implementation_role) == ("claude_code", "claude-opus-4-8", "max", 5400.0, False)
    assert strategy.implementation_role.settings == {"auth_mode": "oauth"}
    assert facts(strategy.judge_role) == ("claude_code", "claude-opus-4-8", "xhigh", 900.0, True)
    assert [facts(member) for member in strategy.ideation_ensemble] == [
        (*CODEX, None, False), ("claude_code", "claude-fable-5", "max", None, False),
    ]
    assert facts(strategy.ideation_lens_planner) == ("claude_code", "claude-opus-4-8", "xhigh", 600.0, False)
    assert facts(strategy.ideation_selector) == ("claude_code", "claude-fable-5", "max", None, False)
    assert strategy.params["ideation"]["candidates_per_member"] == 3
    assert strategy.inbox_settings["enabled"] is False
    assert orchestrator._config_budget["min_iteration_seconds"] == 900
    assert json.loads((root / "results.json").read_text())["task"] == "ioai-2025-practice"
