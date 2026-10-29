"""The benchmark runners' solve paths on the facade's build()
(docs/plans/redesign/wp8-harness-ports.md, changes 11 to 14): each runner
is entered through its own path on the real facade with the engine's
boundary stubbed (the sessions, the inference client, the judge, the
preflight, `solve()`), and what the campaign resolves to is pinned: the
harness in the launch record, the staged evaluation's settings, the runtime
file's shared cache, the budget's mapping, the seeded candidate, the former
mode's roles. The IOAI runner keeps its own path until change 14."""

import argparse
import json
import sys
import types
from pathlib import Path
from types import SimpleNamespace

import pytest

import kapso.execution.orchestrator as orchestrator_module
import kapso.kapso as kapso_module
from kapso.core.config import ConfigError, load_config, read_yaml
from kapso.execution.orchestrator import OrchestratorAgent
from kapso.handles import Brief
from kapso.harness import load as harness_load
from tests.handles_support import solve_result
from tests.harness_support import FakeLLM, FakeProblemHandler, NoopAgent

# The packaged codex host, which every benchmark's implementation runs on.
CODEX = ("codex", "gpt-5.6-sol", "xhigh")
FROZEN_CLOCK = 1_700_000_000.0


class FakeBenchmarkHandler(FakeProblemHandler):
    """A benchmark's handler without its data (the IOAI runner's path)."""

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


def facade_entered(monkeypatch, tmp_path):
    """The facade's build() with the engine's boundary stubbed: every
    session a NoopAgent, the inference client fake, no judge, no preflight,
    no registry, the harness's prerequisites this machine's business; the
    orchestrator `solve()` was entered on and its arguments are recorded,
    and the delivery runs on an empty result."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(orchestrator_module.CodingAgentFactory, "create", staticmethod(lambda config: NoopAgent(config)))
    monkeypatch.setattr(orchestrator_module, "CliInference", FakeLLM)
    monkeypatch.setattr(OrchestratorAgent, "_create_feedback_generator", lambda self: object())
    monkeypatch.setattr(kapso_module, "run_preflight", lambda *a, **k: None)
    monkeypatch.setattr(kapso_module, "register_campaign", lambda *a, **k: None)
    monkeypatch.setattr(harness_load.Harness, "missing_for", lambda self, modules: [])
    entered = []
    result = solve_result(stopped_reason="budget_exhausted")

    def solve(self, *args, finish=None, **kwargs):
        entered.append((self, kwargs))
        finish(result)
        return result

    monkeypatch.setattr(OrchestratorAgent, "solve", solve)
    return entered


def launch_record(workspace):
    return json.loads((workspace / ".kapso" / "launch.json").read_text())


def facts(role):
    """A resolved role, as a tuple a snapshot reads at a glance."""
    return (role.cli, role.model, role.effort, role.timeout, role.web)


def no_signal(monkeypatch, runner):
    """The runner's SIGTERM handler, kept off the test process."""
    monkeypatch.setattr(runner, "signal", types.SimpleNamespace(signal=lambda *args: None, SIGTERM=15))


def test_mle_runner_builds_on_the_facade_with_the_bundled_harness(monkeypatch, tmp_path):
    """Change 12: the competition's data prepared under the archive root, the
    staged grader's task.json with the direction, the caps and the floor,
    no data directory (the Brief names the data by path), the seeded
    baseline, the bundled harness, the former mode's roles."""
    pytest.importorskip("mlebench")
    from benchmarks.mle import runner

    entered = facade_entered(monkeypatch, tmp_path)
    competition = SimpleNamespace(
        id="spooky-author-identification", name="Spooky Author Identification", competition_type="simple",
        description="# Overview\n\nWho wrote it?", grader=SimpleNamespace(is_lower_better=True),
    )
    monkeypatch.setattr(runner.registry, "get_competition", lambda competition_id: competition)

    def fake_prepare(competition, data_dir):
        data_dir.mkdir(parents=True, exist_ok=True)
        (data_dir / "sample_submission.csv").write_text("id,EAP,HPL,MWS\nid1,0.4,0.3,0.3\n")
        return data_dir

    monkeypatch.setattr(runner, "prepare_data", fake_prepare)
    monkeypatch.setattr(runner, "build_brief", lambda *a, **k: Brief(objective="Kaggle competition spooky", measured_by="held-out log loss, lower is better"))
    reports = []
    monkeypatch.setattr(runner, "final_report", lambda work_dir, competition_, solution: reports.append((work_dir, solution)) or {"final": "report"})
    args = argparse.Namespace(competition="spooky-author-identification", iterations=3, coding_agent=None,
                              workspace=str(tmp_path / "workspace"), resume=False, harness=None, experience=None,
                              time_budget_hours=None)
    assert runner.solve_competition(args) == {"final": "report"}
    (orchestrator, kwargs), = entered
    assert kwargs["experiment_max_iter"] == 3 and kwargs["time_budget_minutes"] is None
    work_dir = tmp_path / "tmp" / "mle" / "spooky-author-identification"
    assert json.loads((work_dir / "evaluation" / "task.json").read_text()) == {
        "competition_id": "spooky-author-identification", "higher_is_better": False, "data_dir": str(work_dir / "data"),
        "full_timeout": 28800, "debug_timeout": 1200, "floor_score": 1000000000.0,
    }
    assert (work_dir / "evaluation" / "grader.py").is_file()
    launch = launch_record(tmp_path / "workspace")
    assert launch["harness"]["name"] == "predictive-modelling" and launch["data_dir"] is None
    assert launch["eval_dir"] == str(work_dir / "evaluation") and launch["experiments"] == 3
    assert (tmp_path / "workspace" / "main.py").read_text().startswith('"""Baseline candidate seeded into every MLE-bench')
    (reported_work_dir, delivered), = reports
    assert reported_work_dir == work_dir and delivered.harness.name == "predictive-modelling"
    strategy = orchestrator.search_strategy
    assert orchestrator.config_path == str(work_dir / ".kapso_runtime" / "config.yaml")
    assert str(strategy.shared_cache_dir) == str(work_dir / "shared_cache")
    # Ideation on Claude Code with the packaged model; implementation and
    # the judge on codex with the mode's deadlines; the web on.
    assert facts(strategy.ideation_role) == ("claude_code", "claude-opus-5", None, None, True)
    assert facts(strategy.implementation_role) == (*CODEX, 14400.0, True)
    assert facts(strategy.judge_role) == (*CODEX, 900.0, True)
    assert strategy.params["ideation"]["gates"] == ["research", "experiment_history", "repo_memory", "bank"]
    assert strategy.params["implementation"]["gates"] == ["research", "repo_memory", "bank"]
    assert strategy.params["gate_failure_policy"] == "skip"
    assert strategy.inbox_settings["enabled"] is False
    assert orchestrator._provided_evaluation_manifest


def test_ale_runner_builds_on_the_facade_with_the_bundled_harness(monkeypatch, tmp_path):
    """Change 13: the task root with the public seeds as the data, the staged
    grader's task.json with the direction from the problem's metadata, the
    runs and the floor, the seeded baseline printing the example output,
    the contest harness, the former mode's roles."""
    pytest.importorskip("ale_bench")
    from ale_bench.data import ProblemType, ScoreType
    from benchmarks.ale import runner

    entered = facade_entered(monkeypatch, tmp_path)
    problem = SimpleNamespace(
        metadata=SimpleNamespace(problem_id="ahc039", title="Fishing", problem_type=ProblemType.BATCH, score_type=ScoreType.MINIMIZE),
        example_output="1 2\n3 4\n",
    )
    seeds = SimpleNamespace(public=[1, 2, 3], private=[4, 5])
    standings = SimpleNamespace(standings_scores=[(1, 100), (2, 50), (3, 0)])
    monkeypatch.setattr(runner, "load_problem", lambda problem_id, lite_version: (problem, seeds, standings, None, None))
    monkeypatch.setattr(runner, "build_brief", lambda *a, **k: Brief(objective="AHC problem ahc039", measured_by="the public cases' total, lower is better"))
    reports = []
    monkeypatch.setattr(runner, "final_report", lambda work_dir, problem_id, num_workers, solution: reports.append((work_dir, problem_id, num_workers)) or {"final": "report"})
    args = argparse.Namespace(problem="ahc039", iterations=2, coding_agent=None, workspace=str(tmp_path / "workspace"),
                              resume=False, harness=None, experience=None, time_budget_hours=None)
    assert runner.solve_problem(args) == {"final": "report"}
    (orchestrator, kwargs), = entered
    assert kwargs["experiment_max_iter"] == 2
    work_dir = tmp_path / "tmp" / "ale" / "ahc039"
    assert json.loads((work_dir / "evaluation" / "task.json").read_text()) == {
        "problem_id": "ahc039", "higher_is_better": False, "runs": 4, "num_workers": 25, "floor_score": 1000000000000000000,
    }
    assert (work_dir / "task_root" / "seeds.txt").read_text() == "1\n2\n3\n"
    launch = launch_record(tmp_path / "workspace")
    assert launch["harness"]["name"] == "competitive-programming" and launch["data_dir"] == str(work_dir / "task_root")
    assert (tmp_path / "workspace" / "kapso_datasets" / "seeds.txt").read_text() == "1\n2\n3\n"
    baseline = (tmp_path / "workspace" / "main.cpp").read_text()
    assert 'R"KAPSO(1 2\n3 4)KAPSO"' in baseline and "int main()" in baseline
    assert reports == [(work_dir, "ahc039", 25)]
    strategy = orchestrator.search_strategy
    assert facts(strategy.ideation_role) == ("claude_code", "claude-opus-5", None, None, True)
    assert facts(strategy.implementation_role) == (*CODEX, 7200.0, True)
    assert facts(strategy.judge_role) == (*CODEX, 900.0, True)
    assert strategy.params["ideation"]["gates"] == ["research", "experiment_history", "repo_memory", "bank"]
    assert strategy.inbox_settings["enabled"] is False
    assert orchestrator._provided_evaluation_manifest


def test_relbench_runner_builds_on_the_facade_with_the_bundled_harness(monkeypatch, tmp_path):
    """Change 11: the harness in the launch record, the staged evaluation's
    task.json and the oriented direction, the runtime file's shared cache,
    the budget's mapping, the seeded baseline, and the former mode's roles
    on the orchestrator the campaign was entered on."""
    pytest.importorskip("relbench")
    from benchmarks.relbench import runner
    from benchmarks.relbench.task_specs import ENTITY_REGRESSION, TaskSpec

    entered = facade_entered(monkeypatch, tmp_path)
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
    launch = launch_record(tmp_path / "workspace")
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


def test_ioai_runner_builds_on_the_facade_with_the_contest_harness(monkeypatch, tmp_path):
    """Change 14: the contest root as the data (the descriptor with the
    ledger's absolute path and the procedure, the ticket office with its
    limits, the rules pinned), the Brief from the preflight's statement, the
    session deadlines shaped to the run and the lanes in the runtime file,
    the budget's mapping, the contest harness; the final evaluation skipped."""
    from benchmarks.ioai2026 import runner

    entered = facade_entered(monkeypatch, tmp_path)
    root = tmp_path / "run"
    task = root / "task"
    (task / "dataset").mkdir(parents=True)
    (task / "dataset" / "statement.md").write_text("# Practice task\n\nPredict the label of every test row.\n")
    (task / "kaggle.json").write_text(json.dumps({"competition": "ioai-2026-ai-models-track-practice-task-1", "higher_is_better": True}))
    (task / "RULES.md").write_text("# The organizers' rules\n\n- One GPU; no internet in the kernel.\n")   # the preflight's pinned copy
    # The clock frozen: the budget is the two hours, nothing spent.
    monkeypatch.setattr(runner, "time", types.SimpleNamespace(time=lambda: FROZEN_CLOCK))
    no_signal(monkeypatch, runner)
    monkeypatch.setattr(sys, "argv", ["runner", "--root", str(root), "--hours", "2", "--iterations", "5", "--skip-final-eval"])
    runner.main()
    (orchestrator, kwargs), = entered
    # Two hours, no guard, no harvest window, no reserve (the mode's: a zero reserve is none).
    assert kwargs["experiment_max_iter"] == 5 and kwargs["time_budget_minutes"] == 120
    assert kwargs["cost_budget"] is None and kwargs["finalization_reserve_minutes"] is None
    contest_root = task / "contest_root"
    descriptor = json.loads((contest_root / "contest.json").read_text())
    assert descriptor["competition"] == "ioai-2026-ai-models-track-practice-task-1"
    assert descriptor["ledger"] == str(contest_root / "submissions.json") and descriptor["procedure"] == "python kapso_datasets/submit.py"
    assert descriptor["higher_is_better"] is True and descriptor["shared_root"] == str(contest_root)
    assert json.loads((contest_root / ".kernel_slots_config.json").read_text())["gpu"] == 2
    for name in ("submit.py", "kernel_slots.py", "RULES.md"):
        assert (contest_root / name).is_file()
    workspace = task / "kapso_campaign"
    launch = launch_record(workspace)
    assert launch["harness"]["name"] == "competitive-programming" and launch["data_dir"] == str(contest_root)
    assert launch["eval_dir"] == str(runner.EVALUATION_SUITE) and launch["minutes"] == 120 and launch["experiments"] == 5
    assert launch["brief"]["objective"].startswith("# Practice task")
    assert (workspace / "kapso_datasets" / "contest.json").is_file() and (workspace / "kapso_evaluation" / "evaluate.py").is_file()
    runtime = task / ".kapso_runtime" / "config.yaml"
    assert orchestrator.config_path == str(runtime)
    params = load_config(str(runtime))["search_strategy"]["params"]
    # The session ceilings shrunk to the run: min(14400, 2h); the task's shared cache.
    assert params["ideation"]["timeout"] == 7200 and params["implementation"]["timeout"] == 7200
    assert params["node_expansion_value"] == 8 and params["shared_cache_dir"] == str(task / "shared_cache")
    strategy = orchestrator.search_strategy
    assert facts(strategy.ideation_role) == (*CODEX, 7200.0, True)
    assert facts(strategy.implementation_role) == (*CODEX, 7200.0, True)
    assert strategy.implementation_fallback_model == "gpt-5.5"
    assert facts(strategy.judge_role) == (*CODEX, 900.0, True)
    assert [facts(member) for member in strategy.ideation_ensemble] == [
        (*CODEX, None, True), ("claude_code", "claude-fable-5", "max", None, True),
    ]
    assert facts(strategy.ideation_lens_planner) == ("claude_code", "claude-fable-5", "high", 600.0, True)
    assert strategy.params["ideation"]["candidates_per_member"] == 5
    assert strategy.params["ideation"]["gates"] == ["experiment_history", "repo_memory"]
    assert [lane["CUDA_VISIBLE_DEVICES"] for lane in strategy.expansion_lane_env] == [str(index) for index in range(8)]
    assert strategy.inbox_settings["enabled"] is False
    assert orchestrator._config_budget["min_iteration_seconds"] == 900
    results = json.loads((root / "results.json").read_text())
    assert results["hours"] == 2.0 and results["solution"]["harness"] == "competitive-programming"
    assert json.loads((root / "run_meta.json").read_text())["run_started_utc"]


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
