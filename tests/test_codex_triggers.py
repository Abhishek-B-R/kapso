"""The Codex trigger runner's reading of a session (docs/plans/redesign/
wp7-plugin.md, change 9): the two shapes a skill load takes, pinned by
the captured fixture; a changed shape raises instead of reading nothing;
the cases read as `claude plugin eval` reads them; the Skill graders
applied to the loaded skills as the host applies them to the tool's
input."""

import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
FIXTURE = ROOT / "tests" / "fixtures" / "codex_trigger_events.jsonl"
spec = importlib.util.spec_from_file_location("codex_triggers", ROOT / "scripts" / "redesign" / "codex_triggers.py")
codex_triggers = importlib.util.module_from_spec(spec)
spec.loader.exec_module(codex_triggers)


def _fixture_lines():
    lines = FIXTURE.read_text(encoding="utf-8").splitlines()
    stream = [line for line in lines if json.loads(line).get("type") in ("thread.started", "item.completed")]
    rollout = [line for line in lines if "payload" in json.loads(line)]
    return stream, rollout


def test_the_fixture_pins_both_shapes_of_a_skill_load():
    stream, rollout = _fixture_lines()
    assert codex_triggers.loaded_skills(stream, []) == ["kapso-build"]        # the command that read the file
    assert codex_triggers.loaded_skills([], rollout) == ["kapso-build"]       # the explicit invocation's message
    assert codex_triggers.loaded_skills(stream, rollout) == ["kapso-build"]   # once each
    assert codex_triggers.thread_id(stream) == json.loads(stream[0])["thread_id"]


def test_a_changed_shape_raises_instead_of_reading_nothing():
    stream, rollout = _fixture_lines()
    item = json.loads(stream[1])
    del item["item"]["command"]
    with pytest.raises(KeyError):
        codex_triggers.loaded_skills([json.dumps(item)], [])
    message = json.loads(rollout[0])
    del message["payload"]["role"]
    with pytest.raises(KeyError):
        codex_triggers.loaded_skills([], [json.dumps(message)])
    with pytest.raises(ValueError, match="no thread.started"):
        codex_triggers.thread_id(stream[1:])


def test_the_cases_are_read_as_the_host_reads_them_and_graded_on_the_loads():
    found = {case["name"]: case for case in codex_triggers.cases(tag="main")}
    assert "build-c01" in found and "holdout-01" not in found
    confusion = found["build-c01"]
    assert [g["name"] for g in confusion["graders"]] == ["not-kapso-build", "skill-fired"]
    assert codex_triggers.grade(confusion["graders"], ["kapso"]) == [
        {"name": "not-kapso-build", "count": 0, "passed": True}, {"name": "skill-fired", "count": 1, "passed": True},
    ]
    assert [g["passed"] for g in codex_triggers.grade(confusion["graders"], ["kapso-build", "kapso"])] == [False, True]
    none = found["build-n01"]
    assert [g["passed"] for g in codex_triggers.grade(none["graders"], [])] == [True]
    assert [g["passed"] for g in codex_triggers.grade(none["graders"], ["kapso-review"])] == [False]
    assert [case["name"] for case in codex_triggers.cases(tag="main", pattern="setup-e*")] == ["setup-e01", "setup-e02"]
