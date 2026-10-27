"""The semantic report's verdicts (docs/plans/redesign/wp7-plugin.md,
change 11): a step within its limits with its artifacts present passes;
a step the budgets file does not know fails, so a round cannot add a
step nothing bounds; a missing artifact fails; a deferred step is
reported and not counted; the budgets file covers every step the plugin
round's driver runs."""

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


report = _load("semantic_report", ROOT / "tests" / "semantic" / "report.py")
proof = _load("plugin_proof", ROOT / "scripts" / "redesign" / "plugin_proof.py")
BUDGETS = {name: limits for name, limits in json.loads((ROOT / "tests" / "semantic" / "budgets.json").read_text()).items() if name != "_"}


def _step(name, **fields):
    step = {"name": name, "messages": 1, "questions": 0, "minutes": 1.0, "longest_message_lines": 5, "completed": True, "artifacts": []}
    step.update(fields)
    return step


def _record(*steps):
    return {
        "test": "S2-mechanical", "host": "claude_code", "machine": "kapso-fresh-x",
        "package": {"version": "0.8.0.dev1", "wheel_sha256": "0" * 64},
        "started": "2026-10-27T00:00:00Z", "finished": "2026-10-27T01:00:00Z",
        "steps": list(steps), "transcripts": [],
    }


def test_a_step_passes_within_its_limits_with_its_artifacts_and_fails_otherwise(tmp_path):
    (tmp_path / "kapso-brief.md").write_text("Objective x\n")
    within = _step("build-churn", messages=3, questions=2, minutes=4.5, longest_message_lines=24, artifacts=["kapso-brief.md"])
    assert report.step_passes(within, BUDGETS["build-churn"], tmp_path)
    assert not report.step_passes(_step("build-churn", questions=3), BUDGETS["build-churn"], tmp_path)
    assert not report.step_passes(_step("build-churn", completed=False), BUDGETS["build-churn"], tmp_path)
    assert not report.step_passes(_step("build-churn", artifacts=["campaign/.kapso/status.json"]), BUDGETS["build-churn"], tmp_path)
    assert not report.step_passes(_step("a-step-nothing-bounds"), BUDGETS.get("a-step-nothing-bounds"), tmp_path)


def test_the_report_names_the_failures_and_leaves_a_deferred_step_uncounted(tmp_path):
    (tmp_path / "kapso-brief.md").write_text("Objective x\n")
    text = report.render(_record(
        _step("setup", questions=1, artifacts=["kapso-brief.md"]),
        _step("unbounded"),
        _step("watch", artifacts=["gone.json"]),
        {"name": "learn", "deferred": "hours"},
    ), BUDGETS, tmp_path)
    assert "| setup | 1 | 1 | 1.0 | 5 lines | yes | 1/1 | pass |" in text
    assert "| unbounded |" in text and "FAIL (no budget)" in text
    assert "| watch |" in text and "0/1 missing gone.json | FAIL |" in text
    assert "| learn | - | - | - | - | - | - | deferred: hours |" in text
    assert text.endswith("Result: FAIL (1/3 steps)\n")


def test_the_budgets_cover_every_step_of_the_round():
    assert set(proof.STEP_NAMES) <= set(BUDGETS), sorted(set(proof.STEP_NAMES) - set(BUDGETS))
    for name, limits in BUDGETS.items():
        assert limits and set(limits) <= set(report.LIMIT_KEYS), name
