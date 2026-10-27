"""The semantic report's verdicts (docs/plans/redesign/wp9-semantic-suite.md,
change 2): a conversation step within its budgets with its artifacts
present passes and a step of another kind on completion, minutes and
artifacts; a step the suite does not know fails, so a run cannot add a
step nothing bounds; a deferred step is reported and not counted, but a
required one deferred fails the run; a missing required step fails; the
run-level bars read the record's metrics; a required judge must be present
at the bar in both passes, a straddle adjudicated, a judge failure never a
pass; an advisory record passes its steps and is never a fresh-machine
acceptance; the suite knows every step the drivers run; the plugin
round's committed records render in the second shape."""

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
SUITE = report.load_suite()


def _step(name, **fields):
    kind = SUITE["steps"].get(name, {}).get("kind", "conversation")
    step = {"name": name, "kind": kind, "minutes": 1.0, "completed": True, "artifacts": [], "notes": []}
    if kind == "conversation":
        step.update({"messages": 1, "questions": 0, "longest_message_lines": 5})
    else:
        step["metrics"] = {}
    step.update(fields)
    return step


def _record(test, host, steps, **fields):
    record = {
        "test": test, "host": host, "machine": "kapso-fresh-x", "run_id": f"{test}-{host}-20261027T000000Z", "advisory": None,
        "package": {"version": "0.8.0.dev1", "wheel_sha256": "0" * 64}, "pins": {"wheel_sha256": "0" * 64},
        "user": {"kind": "scripted", "card": None, "interventions": []},
        "started": "2026-10-27T00:00:00Z", "finished": "2026-10-27T01:00:00Z",
        "steps": list(steps), "metrics": {}, "notes": [], "transcripts": [],
    }
    record.update(fields)
    return record


def _complete(test, host):
    return [_step(name) for name in SUITE["tests"][test]["required_steps"][host]]


def _judge(scores_per_pass, adjudication=None, failure=None):
    dimensions = SUITE["tests"]["S2"]["judge"]["dimensions"]
    judge = {"vendor": "gemini", "model": "vertex_ai/gemini-4-argon", "route": "litellm", "prompt_path": "judge/prompt.md", "raw_paths": [],
             "passes": [{"scores": {d: {"score": score, "evidence": []} for d in dimensions}} for score in scores_per_pass]}
    if adjudication is not None:
        judge["adjudication"] = {d: {"score": adjudication, "evidence": []} for d in dimensions}
    if failure:
        judge["failure"] = failure
    return judge


def test_a_conversation_step_passes_within_its_budgets_with_its_artifacts_and_fails_otherwise(tmp_path):
    (tmp_path / "kapso-brief.md").write_text("Objective x\n")
    spec = SUITE["steps"]["build-churn"]
    assert report.step_passes(_step("build-churn", messages=3, questions=2, minutes=4.5, longest_message_lines=12, artifacts=["kapso-brief.md"]), spec, tmp_path)
    assert not report.step_passes(_step("build-churn", questions=3), spec, tmp_path)
    assert not report.step_passes(_step("build-churn", longest_message_lines=13), spec, tmp_path)
    assert not report.step_passes(_step("build-churn", completed=False), spec, tmp_path)
    assert not report.step_passes(_step("build-churn", artifacts=["campaign/.kapso/status.json"]), spec, tmp_path)
    assert not report.step_passes(_step("a-step-nothing-bounds"), SUITE["steps"].get("a-step-nothing-bounds"), tmp_path)


def test_a_step_of_another_kind_passes_on_completion_minutes_and_artifacts(tmp_path):
    spec = SUITE["steps"]["provider-limit"]
    assert report.step_passes(_step("provider-limit", minutes=50.0, metrics={"user_messages": 2}), spec, tmp_path)
    assert not report.step_passes(_step("provider-limit", minutes=61.0), spec, tmp_path)
    assert not report.step_passes(_step("provider-limit", completed=False), spec, tmp_path)


def test_the_verdict_requires_every_required_step_present_and_passing(tmp_path):
    passing = _record("S2-mechanical", "claude_code", _complete("S2-mechanical", "claude_code"))
    assert report.verdict(passing, SUITE, tmp_path)["passed"] and report.verdict(passing, SUITE, tmp_path)["exit"] == report.EXIT_PASS
    steps = _complete("S2-mechanical", "claude_code")
    steps[5] = {"name": steps[5]["name"], "deferred": "hours"}
    deferred = report.verdict(_record("S2-mechanical", "claude_code", steps), SUITE, tmp_path)
    assert not deferred["passed"] and deferred["deferred_required"] == [steps[5]["name"]]
    missing = report.verdict(_record("S2-mechanical", "claude_code", _complete("S2-mechanical", "claude_code")[:-1]), SUITE, tmp_path)
    assert not missing["passed"] and missing["missing_required"] == ["cold-start"]
    text = report.render(_record("S2-mechanical", "claude_code", steps), SUITE, tmp_path)
    assert "required steps deferred: watch" in text and text.startswith("# S2-mechanical on claude_code")
    # A step beyond the required ones must pass too, and an unknown one cannot.
    extra = report.verdict(_record("S2-mechanical", "claude_code", [*_complete("S2-mechanical", "claude_code"), _step("unbounded")]), SUITE, tmp_path)
    assert not extra["passed"] and extra["failed"] == ["unbounded"]


def test_the_bars_read_the_records_metrics(tmp_path):
    steps = _complete("S6", "claude_code")
    below = _record("S6", "claude_code", steps, metrics={"gap_min": -0.01, "lessons_cited": 2, "scored_observations_min": 1})
    assert not report.verdict(below, SUITE, tmp_path)["passed"]
    met = _record("S6", "claude_code", steps, metrics={"gap_min": 0.0, "lessons_cited": 2, "scored_observations_min": 1})
    assert report.verdict(met, SUITE, tmp_path)["passed"]
    absent = _record("S6", "claude_code", steps, metrics={"gap_min": 0.0})
    result = report.verdict(absent, SUITE, tmp_path)
    assert not result["passed"] and result["bars"]["lessons_cited"] is False
    assert "| gap_min | 0.0 |" in report.render(met, SUITE, tmp_path)


def test_a_required_judge_is_present_at_the_bar_in_both_passes_and_a_straddle_is_adjudicated(tmp_path):
    steps = _complete("S2", "claude_code")
    unjudged = report.verdict(_record("S2", "claude_code", steps), SUITE, tmp_path)
    assert not unjudged["passed"] and unjudged["judge"]["required"] and not unjudged["judge"]["present"]
    assert "unjudged" in report.render(_record("S2", "claude_code", steps), SUITE, tmp_path)
    failed = _record("S2", "claude_code", steps, judge=_judge([], failure="the reply held two JSON objects"))
    assert not report.verdict(failed, SUITE, tmp_path)["passed"] and "Judge: FAILED (the reply held two JSON objects)" in report.render(failed, SUITE, tmp_path)
    assert report.verdict(_record("S2", "claude_code", steps, judge=_judge([4, 5])), SUITE, tmp_path)["passed"]
    straddle = _record("S2", "claude_code", steps, judge=_judge([3, 5]))
    result = report.verdict(straddle, SUITE, tmp_path)
    assert not result["passed"] and result["judge"]["dimensions"]["clear"]["straddled"]
    adjudicated = _record("S2", "claude_code", steps, judge=_judge([3, 5], adjudication=4))
    assert report.verdict(adjudicated, SUITE, tmp_path)["passed"]
    assert "| clear | 3 | 5 | 4 | 4 | pass |" in report.render(adjudicated, SUITE, tmp_path)
    assert not report.verdict(_record("S2", "claude_code", steps, judge=_judge([2, 3])), SUITE, tmp_path)["passed"]


def test_an_advisory_record_passes_its_steps_and_is_never_a_fresh_machine_acceptance(tmp_path):
    record = _record("S2-mechanical", "codex", _complete("S2-mechanical", "codex"), advisory="the development box, the owner's Codex login")
    result = report.verdict(record, SUITE, tmp_path)
    assert result["passed"] and result["exit"] == report.EXIT_ADVISORY
    text = report.render(record, SUITE, tmp_path)
    assert text.startswith("# S2-mechanical on codex\n\n**Advisory: the development box, the owner's Codex login**")
    assert "Result: PASS, advisory (the development box; not a fresh-machine acceptance)" in text


def test_the_suite_knows_every_step_the_drivers_run_and_its_entries_hold_their_shape():
    assert set(proof.STEP_NAMES) <= set(SUITE["steps"]), sorted(set(proof.STEP_NAMES) - set(SUITE["steps"]))
    for test in SUITE["tests"].values():
        for host, names in test["required_steps"].items():
            assert host in ("claude_code", "codex") and names and set(names) <= set(SUITE["steps"]), host
        for bar in test["bars"].values():
            assert set(bar) <= {"min", "max"} and bar
        if test["judge"]:
            assert test["judge"]["dimensions"] and test["judge"]["scale"][0] <= test["judge"]["bar"] <= test["judge"]["scale"][1]
    for name, spec in SUITE["steps"].items():
        assert spec["kind"] in ("conversation", "attempt", "injection", "build", "reading", "shell"), name
        if spec["kind"] == "conversation":
            assert set(spec) - {"kind"} <= set(report.COUNT_KEYS) and spec.get("minutes"), name
        else:
            assert set(spec) - {"kind"} <= {"minutes"}, name


def test_the_plugin_rounds_records_render_in_the_second_shape(tmp_path):
    for name in ("claude_code", "claude_code_first", "codex"):
        path = ROOT / "scripts" / "redesign" / "runs" / "wp7" / name / "record.json"
        record = json.loads(path.read_text())
        assert record["run_id"].startswith("S2-mechanical-") and record["user"]["kind"] == "scripted"
        assert all(step.get("deferred") or step["kind"] == SUITE["steps"][step["name"]]["kind"] for step in record["steps"])
        text = report.render(record, SUITE, path.parent)
        assert text.startswith(f"# S2-mechanical on {record['host']}")
    assert json.loads((ROOT / "scripts" / "redesign" / "runs" / "wp7" / "codex" / "record.json").read_text())["advisory"]


def test_each_steps_notes_are_rendered_beside_the_table(tmp_path):
    step = _step("setup")
    step["notes"] = ["the link clicks judged by hand from the transcript"]
    text = report.render(_record("S2-mechanical", "claude_code", [step]), SUITE, tmp_path)
    assert "Step notes:\n- setup: the link clicks judged by hand from the transcript\n" in text
