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
from kapso.core.config import ConfigError, load_config, read_yaml
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

    def apply_bank_intro(self, intro):
        self.intro = intro


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
    pytest.importorskip("mlebench")
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
    pytest.importorskip("ale_bench")
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


def test_relbench_runner_builds_on_the_facade_with_the_bundled_harness(monkeypatch, tmp_path):
    """The runner's solve path on the real facade with the engine's boundary
    stubbed (docs/plans/redesign/wp8-harness-ports.md, change 11): the
    harness in the launch record, the staged evaluation's task.json and the
    oriented direction, the runtime file's shared cache, the budget's
    mapping, the seeded baseline, and the former mode's roles on the
    orchestrator the campaign was entered on."""
    pytest.importorskip("relbench")
    import kapso.kapso as kapso_module
    from kapso.handles import Brief
    from kapso.harness import load as harness_load
    from benchmarks.relbench import runner
    from benchmarks.relbench.task_specs import ENTITY_REGRESSION, TaskSpec
    from tests.handles_support import solve_result

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(orchestrator_module.CodingAgentFactory, "create", staticmethod(lambda config: NoopAgent(config)))
    monkeypatch.setattr(orchestrator_module, "CliInference", FakeLLM)
    monkeypatch.setattr(OrchestratorAgent, "_create_feedback_generator", lambda self: object())
    monkeypatch.setattr(kapso_module, "run_preflight", lambda *a, **k: None)
    monkeypatch.setattr(kapso_module, "register_campaign", lambda *a, **k: None)
    # The bundled harness's prerequisites are this machine's business, not the test's.
    monkeypatch.setattr(harness_load.Harness, "missing_for", lambda self, modules: [])
    entered = []
    result = solve_result(stopped_reason="budget_exhausted")

    def solve(self, *args, finish=None, **kwargs):
        entered.append((self, kwargs))
        finish(result)
        return result

    monkeypatch.setattr(OrchestratorAgent, "solve", solve)
    # The task's material: no library download, no copy built, the Brief and
    # the final report as fakes; the runner's staging and launch are real.
    spec = TaskSpec(
        dataset_name="rel-f1", task_name="driver-position", family=ENTITY_REGRESSION, primary_metric="mae",
        maximize=False, full_timeout=7200, debug_timeout=900, time_col="date", target_col="position", num_eval_timestamps=40,
    )
    monkeypatch.setattr(runner, "pristine_task", lambda dataset, task: object())
    monkeypatch.setattr(runner, "resolve_spec", lambda task, dataset, name, timeouts: spec)

    def fake_copy(script, source, dataset, task, out, *, rolling, rebuild):
        out.mkdir(parents=True, exist_ok=True)
        return out

    monkeypatch.setattr(runner, "ensure_sanitized_copy", fake_copy)
    brief = Brief(objective="RelBench rel-f1/driver-position: the task's facts", measured_by="validation mae, lower is better")
    monkeypatch.setattr(runner, "build_brief", lambda *a, **k: brief)
    reports = []
    monkeypatch.setattr(runner, "final_report", lambda work_dir, evaluation_dir, task, spec_, harness_path, solution: reports.append((work_dir, harness_path, solution)) or {"final": "report"})
    args = argparse.Namespace(
        dataset="rel-f1", task="driver-position", iterations=4, coding_agent=None, workspace=str(tmp_path / "workspace"),
        resume=False, time_budget_hours=2.0, harness=None, experience=None, rebuild_cache=False,
    )
    assert runner.solve_task(args) == {"final": "report"}
    (orchestrator, kwargs), = entered
    assert kwargs["experiment_max_iter"] == 4 and kwargs["time_budget_minutes"] == 120.0
    work_dir = tmp_path / "tmp" / "relbench" / "rel-f1--driver-position"
    # The staged evaluation: the provided suite with the task's settings beside it.
    assert json.loads((work_dir / "evaluation" / "task.json").read_text()) == {
        "dataset": "rel-f1", "task": "driver-position", "primary_metric": "mae", "higher_is_better": False,
        "work_dir": str(work_dir), "full_timeout": 7200, "debug_timeout": 900,
        "cache_dir": str(work_dir / "sanitized_cache"), "rolling_root": str(work_dir / "rolling_caches"),
    }
    assert (work_dir / "evaluation" / "grader.py").is_file() and (work_dir / "evaluation" / "kapso_eval_archive.py").is_file()
    # The runtime file: this benchmark's file with the task's shared cache over it.
    runtime = work_dir / ".kapso_runtime" / "config.yaml"
    assert orchestrator.config_path == str(runtime)
    assert load_config(str(runtime))["search_strategy"]["params"]["shared_cache_dir"] == str(work_dir / "shared_cache")
    # The launch record: the bundled harness, the brief, the directories, the budget.
    launch = json.loads((tmp_path / "workspace" / ".kapso" / "launch.json").read_text())
    assert launch["harness"]["name"] == "predictive-modelling" and launch["brief"]["objective"].startswith("RelBench rel-f1")
    assert launch["eval_dir"] == str(work_dir / "evaluation") and launch["data_dir"] == str(runner.STARTER_KIT)
    assert launch["minutes"] == 120.0 and launch["experiments"] == 4
    assert (tmp_path / "workspace" / "kapso_evaluation" / "task.json").is_file()
    assert (tmp_path / "workspace" / "kapso_datasets" / "common.py").is_file()
    assert (tmp_path / "workspace" / "main.py").read_text().startswith('"""Baseline candidate')
    # The final report runs on the archive root with the loaded harness and the delivery.
    (reported_work_dir, harness_path, delivered), = reports
    assert reported_work_dir == work_dir and harness_path.name == "predictive-modelling"
    assert delivered["harness"] == "predictive-modelling" and delivered["branch"] is None
    # The former mode: codex everywhere but the Claude member and the lens
    # planner; no web for implementation (the temporal-leakage protocol).
    strategy = orchestrator.search_strategy
    assert str(strategy.shared_cache_dir) == str(work_dir / "shared_cache")
    assert facts(strategy.ideation_role) == (*CODEX, 86400.0, True)
    assert facts(strategy.implementation_role) == (*CODEX, 18000.0, False)
    assert facts(strategy.judge_role) == (*CODEX, 900.0, True)
    assert [facts(member) for member in strategy.ideation_ensemble] == [
        (*CODEX, None, True), ("claude_code", "claude-fable-5", "xhigh", None, True),
    ]
    assert facts(strategy.ideation_lens_planner) == ("claude_code", "claude-fable-5", "max", 600.0, True)
    assert strategy.params["ideation"]["gates"] == ["experiment_history", "repo_memory", "bank"]
    assert strategy.params["implementation"]["gates"] == ["repo_memory", "bank"]
    assert strategy.node_expansion_value == 4
    assert [lane["CUDA_VISIBLE_DEVICES"] for lane in strategy.expansion_lane_env] == ["0", "1", "2", "3"]
    assert strategy.inbox_settings["enabled"] is False
    # The provided grader is the campaign's evaluation, fingerprinted.
    assert orchestrator._provided_evaluation_manifest


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


@pytest.mark.parametrize("benchmark", ["relbench", "mle", "ale", "ioai2026"])
def test_every_benchmark_makes_the_stop_vote_advisory_in_its_override_file(benchmark):
    """A benchmark has no goal to reach, so the judge's stop vote is advisory
    and the campaign runs to its budget: the config key the orchestrator
    reads (docs/plans/redesign/wp8-harness-ports.md, change 10)."""
    override = Path(__file__).resolve().parent.parent / "benchmarks" / benchmark / "config.yaml"
    assert read_yaml(str(override))["search_strategy"]["params"]["honor_agent_stop"] is False


def test_a_runners_file_naming_a_host_with_no_staging_is_refused_at_construction(entered, tmp_path):
    """A benchmark runner constructs the campaign directly, past the facade
    and the doctor: the config's checks run at the orchestrator's birth."""
    config = tmp_path / "config.yaml"
    config.write_text("hosts:\n  gemini:\n    model: gemini-2.5-flash\n")
    with pytest.raises(ConfigError, match="hosts.gemini: the gemini adapter cannot host a build session"):
        OrchestratorAgent(FakeBenchmarkHandler(), config_path=str(config), workspace_dir=str(tmp_path / "w"))
