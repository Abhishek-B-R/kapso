"""The ALE-Bench integration on build() (docs/plans/redesign/wp8-harness-ports.md,
change 13): the Brief from the problem's facts, the seeded baseline, and the
provided grader's contract on a fake judge (the mean over runs, the floor
for a failed case, the orientation, and the results file the harness's
finish hook accepts)."""

import datetime as dt
import importlib.util
import json
import shutil
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

pytest.importorskip("ale_bench")

from ale_bench.data import ProblemType, ScoreType
from ale_bench.result import JudgeResult

from kapso.handles import Brief
from kapso.harness import BUNDLED_ROOT
from benchmarks.ale.context import SCORER_COMMAND, build_brief
from benchmarks.ale.problems import LITE_PROBLEMS
from benchmarks.ale.runner import baseline_program

REPO_ROOT = Path(__file__).parents[1]
GRADER = REPO_ROOT / "benchmarks" / "ale" / "data" / "generic_eval" / "grader.py"
SCORER_HOOK = BUNDLED_ROOT / "competitive-programming" / "hooks" / "require-scorer-run" / "require_scorer_run.py"
COMPUTE = {"has_gpu": False, "gpu_name": "", "num_cpus": 8, "mem_gb": 32}


def fake_problem(score_type=ScoreType.MINIMIZE):
    return SimpleNamespace(
        metadata=SimpleNamespace(
            problem_id="ahc039", title="Fishing", problem_type=ProblemType.BATCH, score_type=score_type,
            contest_url="https://atcoder.jp/contests/ahc039",
            start_at=dt.datetime(2024, 11, 17, 6, 0), end_at=dt.datetime(2024, 11, 17, 10, 0),
        ),
        constraints=SimpleNamespace(time_limit=2.0, memory_limit=1024 * 1024 * 1024),
        statement="# Problem\n\nCatch the fish.",
        example_input="3\n1 2 3\n",
        example_output="1 2\n3 4\n",
        tool_readme="# Tools\n\nRun `cargo run --release --bin gen`.",
    )


class TestBrief:
    def test_the_objective_holds_the_statement_the_constraints_and_the_scoring(self, tmp_path):
        brief = build_brief(fake_problem(), [1, 2, 3], False, 4, 683, tmp_path / "shared", compute=COMPUTE)
        objective = brief.objective
        assert "Catch the fish." in objective and "cargo run --release --bin gen" in objective
        assert "Time limit: 2.0 seconds per case. Memory limit: 1024 MB." in objective
        assert "the 3 seeds in `kapso_datasets/seeds.txt`" in objective and "mean over 4 runs" in objective
        assert "683 contestants" in objective and "minimize: lower is better" in objective
        assert "1 2\n3 4" in objective and str(tmp_path / "shared") in objective
        assert brief.measured_by.startswith("the official judge over the public cases") and "negated" in brief.measured_by
        assert any(SCORER_COMMAND in rule for rule in brief.rules)
        assert any("takes the floor" in rule for rule in brief.rules)
        assert any("pre_run.cpp" in rule for rule in brief.rules)
        assert Brief.parse(brief.render()) == brief

    def test_no_standing_guidance_rides_in_the_brief(self, tmp_path):
        text = build_brief(fake_problem(ScoreType.MAXIMIZE), [1], True, 2, 10, tmp_path, compute=COMPUTE).render()
        for phrase in ("Simulated annealing", "1e8", "grandmaster", "beam"):
            assert phrase not in text, phrase
        assert "maximize: higher is better" in text


def test_the_lite_roster_is_the_reported_ten():
    assert len(LITE_PROBLEMS) == 10 and "ahc039" in LITE_PROBLEMS and "ahc002" not in LITE_PROBLEMS


def test_the_seeded_baseline_compiles_and_prints_the_example_output(tmp_path):
    source = tmp_path / "main.cpp"
    source.write_text(baseline_program("1 2\n3 4\n"))
    compiler = shutil.which("g++")
    if compiler is None:
        pytest.skip("no g++ on this machine")
    subprocess.run([compiler, "-std=c++17", "-O2", "-o", str(tmp_path / "baseline"), str(source)], check=True)
    run = subprocess.run([str(tmp_path / "baseline")], input="whatever\n", capture_output=True, text=True, check=True)
    assert run.stdout == "1 2\n3 4\n"


class FakeCase:
    def __init__(self, score, judge=JudgeResult.ACCEPTED, seconds=0.5):
        self.absolute_score = score
        self.judge_result = judge
        self.execution_time = seconds


class FakeResult:
    def __init__(self, cases):
        self.case_results = cases
        accepted = all(case.judge_result == JudgeResult.ACCEPTED for case in cases)
        self.overall_judge_result = JudgeResult.ACCEPTED if accepted else JudgeResult.WRONG_ANSWER
        self.overall_absolute_score = sum(case.absolute_score for case in cases) if accepted else 0


class FakeSession:
    def __init__(self, results):
        self.public_seeds = [11, 12]
        self.results = list(results)
        self.calls = 0

    def public_eval(self, code, code_language):
        assert code_language == "cpp23" and "main" in code
        self.calls += 1
        return self.results.pop(0)


def load_grader(repo: Path, monkeypatch, session, higher_is_better=False):
    suite = repo / "kapso_evaluation"
    suite.mkdir(parents=True)
    shutil.copy2(GRADER, suite / "grader.py")
    (suite / "task.json").write_text(json.dumps({
        "problem_id": "ahc039", "higher_is_better": higher_is_better, "runs": 2, "num_workers": 2,
        "floor_score": 0 if higher_is_better else 1000000000000000000,
    }))
    (repo / "main.cpp").write_text("int main() { return 0; }\n")
    monkeypatch.setattr(sys, "dont_write_bytecode", True)
    spec = importlib.util.spec_from_file_location("ale_grader", suite / "grader.py")
    grader = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(grader)
    monkeypatch.setattr(grader.ale_bench, "start", lambda **kwargs: session)
    return grader


def manifest_of(out: str) -> dict:
    line = [line for line in out.splitlines() if line.startswith("KAPSO_EVAL_MANIFEST")][-1]
    return json.loads(line.split(" ", 1)[1])


class TestProvidedGrader:
    def test_full_averages_the_runs_and_orients_the_total(self, tmp_path, monkeypatch, capsys):
        session = FakeSession([
            FakeResult([FakeCase(100, seconds=1.2), FakeCase(10)]),
            FakeResult([FakeCase(120), FakeCase(10)]),
        ])
        grader = load_grader(tmp_path / "repo", monkeypatch, session)
        monkeypatch.setattr(sys, "argv", ["grader.py", "--fidelity", "full"])
        grader.main()
        manifest = manifest_of(capsys.readouterr().out)
        assert session.calls == 2 and manifest["runs"] == 2 and manifest["valid"] is True
        assert manifest["raw_score"] == 120.0 and manifest["score"] == -120.0 and manifest["items"] == 2

    def test_fast_is_one_run(self, tmp_path, monkeypatch, capsys):
        session = FakeSession([FakeResult([FakeCase(5), FakeCase(7)])])
        grader = load_grader(tmp_path / "repo", monkeypatch, session, higher_is_better=True)
        monkeypatch.setattr(sys, "argv", ["grader.py", "--fidelity", "fast"])
        grader.main()
        manifest = manifest_of(capsys.readouterr().out)
        assert session.calls == 1 and manifest["raw_score"] == 12.0 and manifest["score"] == 12.0

    def test_a_failed_case_takes_the_floor(self, tmp_path, monkeypatch, capsys):
        """The contest's all-or-nothing rule: one case not accepted, or scored
        zero, in any run, and the submission scores the floor, oriented as
        the worst value."""
        session = FakeSession([
            FakeResult([FakeCase(100), FakeCase(0, judge=JudgeResult.TIME_LIMIT_EXCEEDED, seconds=2.1)]),
            FakeResult([FakeCase(100), FakeCase(10)]),
        ])
        grader = load_grader(tmp_path / "repo", monkeypatch, session)
        monkeypatch.setattr(sys, "argv", ["grader.py", "--fidelity", "full"])
        grader.main()
        manifest = manifest_of(capsys.readouterr().out)
        assert manifest["valid"] is False and manifest["failed_cases"] == ["12"]
        assert manifest["score"] == -1000000000000000000.0 and manifest["raw_score"] == 55.0

    def test_scores_writes_the_results_file_the_harness_finish_hook_accepts(self, tmp_path, monkeypatch, capsys):
        """The candidates' scorer procedure: the per-seed file in the
        scorer-cli skill's shape, at the attempt's root, which the contest
        harness's require-scorer-run hook reads against the seed list."""
        repo = tmp_path / "repo"
        session = FakeSession([
            FakeResult([FakeCase(100, seconds=1.0), FakeCase(10, seconds=0.4)]),
            FakeResult([FakeCase(110, seconds=1.1), FakeCase(10, seconds=0.5)]),
            FakeResult([FakeCase(120, seconds=0.9), FakeCase(10, seconds=0.3)]),
        ])
        grader = load_grader(repo, monkeypatch, session)
        monkeypatch.setattr(sys, "argv", ["grader.py", "--scores", "results/scores.json", "--runs", "3"])
        grader.main()
        results = json.loads((repo / "results" / "scores.json").read_text())
        assert results["solution"] == "main.cpp" and results["runs"] == 3
        assert results["seeds"]["11"]["score"] == 110.0 and results["seeds"]["11"]["runtime_ms"] == 1100
        assert results["seeds"]["11"]["spread"] > 0 and results["seeds"]["12"]["spread"] == 0.0
        assert results["seeds"]["12"]["status"] == "ok"
        # The harness's finish hook, on the attempt as the runner stages it.
        (repo / "kapso_task.md").write_text("# Task\n")
        (repo / "kapso_datasets").mkdir()
        (repo / "kapso_datasets" / "seeds.txt").write_text("11\n12\n")
        decision = subprocess.run(
            [sys.executable, str(SCORER_HOOK)], input=json.dumps({"hook_event_name": "Stop", "stop_hook_active": False}),
            capture_output=True, text=True, check=True, cwd=str(repo),
        )
        assert decision.stdout.strip() == ""
