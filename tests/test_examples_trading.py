"""The trading example: the generator is deterministic (the shipped
strategy scores the brief's baseline on any machine), the evaluator honours
the contract the harness's pages describe (the risk line, then `sharpe:`
last; the two result files and result.json; the exit codes), `--fast` is
marked as not comparable, and the brief names the harness."""

import importlib.util
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from kapso.handles import Brief

pytest.importorskip("pandas")

EXAMPLE = Path(__file__).resolve().parent.parent / "examples" / "trading"
EVALUATE = "kapso_evaluation/evaluate.py"


@pytest.fixture(scope="module")
def workspace(tmp_path_factory) -> Path:
    """The engine's layout: the development bars under kapso_datasets/, the
    evaluation beside them with its private-directory pointer, strategy.py
    at the root."""
    root = tmp_path_factory.mktemp("trading")
    spec = importlib.util.spec_from_file_location("trading_generate", EXAMPLE / "generate.py")
    generate = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(generate)
    generate.HERE = root / "example"
    (generate.HERE / "evaluation").mkdir(parents=True)
    generate.main()

    ws = root / "ws"
    shutil.copytree(generate.HERE / "data", ws / "kapso_datasets")
    shutil.copytree(EXAMPLE / "evaluation", ws / "kapso_evaluation",
                    ignore=shutil.ignore_patterns("private_dir.txt", "result.json", "__pycache__"))
    shutil.copy(generate.HERE / "evaluation" / "private_dir.txt", ws / "kapso_evaluation" / "private_dir.txt")
    shutil.copy(EXAMPLE / "repo" / "strategy.py", ws / "strategy.py")
    return ws


def evaluate(workspace: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, EVALUATE, *args], cwd=workspace, capture_output=True, text=True)


def test_the_shipped_strategy_scores_the_briefs_baseline(workspace):
    result = evaluate(workspace)
    assert result.returncode == 0, result.stdout + result.stderr
    lines = result.stdout.strip().splitlines()
    assert lines[-3:] == ["max_drawdown: 0.1072", "turnover: 3.5", "sharpe: 0.1384"]
    brief = Brief.read(EXAMPLE / "kapso-brief.md")
    assert brief.baseline.startswith("0.14 ")

    equity = (workspace / "results" / "equity_curve.csv").read_text().splitlines()
    trades = (workspace / "results" / "trades.csv").read_text().splitlines()
    assert equity[0] == "timestamp,portfolio_return,equity" and len(equity) == 1 + 262
    assert trades[0] == "timestamp,instrument,position,turnover" and len(trades) > 1
    record = json.loads((workspace / "kapso_evaluation" / "result.json").read_text())
    assert record["score"] == 0.1384 and record["fast"] is False
    assert record["metrics"] == {"sharpe": 0.1384, "max_drawdown": 0.1072, "turnover": 3.5}
    assert record["evaluation_output"].splitlines()[-1] == "sharpe: 0.1384"


def test_fast_is_marked_and_scores_one_instrument_over_one_quarter(workspace):
    result = evaluate(workspace, "--fast")
    lines = result.stdout.strip().splitlines()
    assert result.returncode == 0 and lines[0].startswith("fast: ")
    assert lines[1] == "instruments: ALPHA" and lines[2] == "days: 63"
    assert lines[-1].startswith("sharpe: ") and lines[-1] != "sharpe: 0.1384"
    assert json.loads((workspace / "kapso_evaluation" / "result.json").read_text())["fast"] is True
    evaluate(workspace)   # leave the full score behind for the other tests


def test_a_malformed_signal_and_a_missing_strategy_exit_with_the_reason(workspace, tmp_path):
    broken = tmp_path / "broken"
    shutil.copytree(workspace, broken, ignore=shutil.ignore_patterns("results"))
    (broken / "strategy.py").write_text("import pandas as pd\ndef signal(bars):\n    return bars['close'] * 0 + 2.0\n")
    result = evaluate(broken)
    assert result.returncode == 2 and "must stay within [-1, 1]" in result.stdout
    (broken / "strategy.py").unlink()
    result = evaluate(broken)
    assert result.returncode == 3 and "strategy.py is missing" in result.stdout


def test_the_brief_names_the_harness_and_the_budget():
    brief = Brief.read(EXAMPLE / "kapso-brief.md")
    assert brief.harness == "../harnesses/trading"
    assert brief.target == "1.0"
    assert brief.budget.minutes == 75 and brief.budget.experiments == 2
    assert len(brief.rules) == 4 and brief.rules[-1] == "the evaluator is never modified"
