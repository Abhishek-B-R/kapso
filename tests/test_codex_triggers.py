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
        {"name": "not-kapso-build", "count": 0, "passed": True, "read_after": False}, {"name": "skill-fired", "count": 1, "passed": True},
    ]
    # Codex reads skills as references: the skill under test read after
    # the expected one is a pass, said as such; read first, the session
    # routed to it, and the refusal fails; alone, both fail.
    later = codex_triggers.grade(confusion["graders"], ["kapso", "kapso-build"])
    assert [g["passed"] for g in later] == [True, True] and later[0]["read_after"] is True
    assert [g["passed"] for g in codex_triggers.grade(confusion["graders"], ["kapso-build", "kapso"])] == [False, True]
    assert [g["passed"] for g in codex_triggers.grade(confusion["graders"], ["kapso-build"])] == [False, False]
    none = found["build-n01"]
    assert [g["passed"] for g in codex_triggers.grade(none["graders"], [])] == [True]
    assert [g["passed"] for g in codex_triggers.grade(none["graders"], ["kapso-review"])] == [False]
    # A run that never started is no evidence for a refusal.
    assert [g["passed"] for g in codex_triggers.grade(none["graders"], [], started=False)] == [False]
    assert [case["name"] for case in codex_triggers.cases(tag="main", pattern="setup-e*")] == ["setup-e01", "setup-e02"]


def test_a_load_is_a_read_that_succeeded():
    """A command that names a skill file without reading it, or that
    failed, loads nothing."""
    def command(text, exit_code=0):
        return json.dumps({"type": "item.completed", "item": {"type": "command_execution", "command": f"/bin/bash -lc '{text}'", "exit_code": exit_code, "status": "completed"}})
    stream = [
        command("echo .agents/skills/kapso-build/SKILL.md"),
        command("cat .agents/skills/kapso-review/SKILL.md", exit_code=1),
        command("sed -n 1,80p .agents/skills/kapso-setup/SKILL.md"),
    ]
    assert codex_triggers.loaded_skills(stream, []) == ["kapso-setup"]


def test_a_sandbox_that_never_started_is_the_machines_failure_not_a_miss(tmp_path):
    # s2-codex-5 on GCP: 123 of 138 failed runs said "bwrap: loopback: Failed
    # RTM_NEWADDR: Operation not permitted" — the session announced the skill
    # and could not read it. Such a run is classified from its own words and
    # is never a pass, never a miss: the bar is not established on it.
    stream = tmp_path / "streams" / "build-c01-1.jsonl"
    stream.parent.mkdir()
    stream.write_text('{"type":"thread.started","thread_id":"t1"}\n', encoding="utf-8")
    stream.with_suffix(".err").write_text("ERROR: bwrap: loopback: Failed RTM_NEWADDR: Operation not permitted\n", encoding="utf-8")
    assert codex_triggers.sandbox_failure(stream) == "bwrap: loopback: Failed RTM_NEWADDR: Operation not permitted"
    clean = tmp_path / "streams" / "build-c01-2.jsonl"
    clean.write_text('{"type":"thread.started","thread_id":"t2"}\n', encoding="utf-8")
    assert codex_triggers.sandbox_failure(clean) is None
    results = [
        {"case": "build-c01", "run": 1, "started": True, "loaded": [], "graders": [{"name": "kapso-build", "count": 0, "passed": False}],
         "environment": "bwrap: loopback: Failed RTM_NEWADDR: Operation not permitted", "passed": False},
        {"case": "build-c01", "run": 2, "started": True, "loaded": ["kapso-build"], "graders": [{"name": "kapso-build", "count": 1, "passed": True}],
         "environment": None, "passed": True},
    ]
    text = codex_triggers.report(results, [])
    assert text.splitlines()[2].startswith("| build-c01 | 2 | 1/2 |") and text.splitlines()[2].endswith("| 0 | 1 |")
    assert "1 run(s) failed in the sandbox before any skill could be read" in text
