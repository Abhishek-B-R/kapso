"""The pipeline example: the generator is deterministic (the shipped
project scores the brief's baseline on any machine), the evaluator honours
the contract every fixture meets (the metric on its own line as the last
line, result.json in the engine's shape, a non-zero exit with the reason
on a workspace that is not a project), `--fast` is marked as not
comparable, and the brief carries the measured baseline. dbt is not a
dependency of the package: without it on PATH the suite says so and skips."""

import importlib.util
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from kapso.handles import Brief

pytest.importorskip("duckdb")
# The interpreter running the tests may carry dbt in its own bin directory
# without that directory on PATH; the evaluator calls `dbt` through PATH.
PATH = f"{Path(sys.executable).parent}{os.pathsep}{os.environ['PATH']}"
if shutil.which("dbt", path=PATH) is None:
    pytest.skip("dbt is not on PATH (pip install dbt-core dbt-duckdb)", allow_module_level=True)

EXAMPLE = Path(__file__).resolve().parent.parent / "examples" / "pipeline-dbt"
EVALUATE = "kapso_evaluation/evaluate.py"


@pytest.fixture(scope="module")
def workspace(tmp_path_factory) -> Path:
    """The engine's layout: the exports under kapso_datasets/, the evaluation
    beside them, the project at the root."""
    root = tmp_path_factory.mktemp("pipeline")
    spec = importlib.util.spec_from_file_location("pipeline_generate", EXAMPLE / "generate.py")
    generate = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(generate)
    generate.HERE = root / "example"
    generate.HERE.mkdir()
    generate.main([])
    ws = root / "ws"
    shutil.copytree(EXAMPLE / "repo", ws)
    shutil.copytree(generate.HERE / "data", ws / "kapso_datasets")
    shutil.copytree(EXAMPLE / "evaluation", ws / "kapso_evaluation", ignore=shutil.ignore_patterns("result.json", "warehouse.duckdb", "__pycache__"))
    return ws


def evaluate(workspace: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, EVALUATE, *args], cwd=workspace, capture_output=True, text=True, env={**os.environ, "PATH": PATH})


def test_the_generator_is_deterministic_and_the_shipped_project_scores_the_baseline(workspace):
    manifest = json.loads((workspace.parent / "example" / "MANIFEST.json").read_text())
    assert manifest["sha256"] == json.loads((EXAMPLE / "MANIFEST.json").read_text())["sha256"]
    run = evaluate(workspace)
    assert run.returncode == 0, run.stdout + run.stderr
    lines = run.stdout.strip().splitlines()
    assert lines[-1] == "tests_passing: 0.1538" and lines[-2] == "assertions: 2/13"
    result = json.loads((workspace / "kapso_evaluation" / "result.json").read_text())
    assert result["evaluation_script_path"] == EVALUATE and result["score"] == 0.1538
    assert result["evaluation_output"].splitlines()[-1] == "tests_passing: 0.1538"
    assert [a["assertion"] for a in result["assertions"] if a["passed"]] == ["fct_orders keeps 95% of the distinct orders exported", "the marts keep their columns"]


def test_fast_is_marked_and_scores_the_staging_layer_alone(workspace):
    run = evaluate(workspace, "--fast")
    assert run.returncode == 0, run.stdout + run.stderr
    lines = run.stdout.strip().splitlines()
    assert "not comparable with a full score" in run.stdout
    assert lines[-2] == "assertions: 0/8" and lines[-1] == "tests_passing: 0.0"


def test_a_workspace_without_a_project_exits_with_the_reason(tmp_path):
    (tmp_path / "kapso_evaluation").mkdir()
    shutil.copy(EXAMPLE / "evaluation" / "evaluate.py", tmp_path / "kapso_evaluation" / "evaluate.py")
    run = evaluate(tmp_path)
    assert run.returncode == 3 and "dbt_project.yml is missing" in run.stdout


def test_the_brief_carries_the_measured_baseline():
    brief = Brief.read(EXAMPLE / "kapso-brief.md")
    assert brief.baseline.startswith("0.15") and brief.target.startswith("1.0")
    assert json.loads((EXAMPLE / "baseline.json").read_text())["score"] == 0.1538
