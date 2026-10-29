"""The competitive-programming harness's hooks on both hosts' event shapes
(docs/plans/redesign/wp8-harness-ports.md, change 7): `require-scorer-run`
blocks a finish while a seed of the task root's list lacks a scorer result,
lets it through once every seed is scored, and has no opinion when the task
root has no seed list; the manifest lists it on implementation only."""

import json
import subprocess
import sys

import pytest
import yaml

from kapso.harness import BUNDLED_ROOT

CONTEST = BUNDLED_ROOT / "competitive-programming"
HOOK = CONTEST / "hooks" / "require-scorer-run" / "require_scorer_run.py"
STOP_EVENTS = {
    "claude-code": {"hook_event_name": "Stop", "stop_hook_active": False, "session_id": "s"},
    "codex": {"hook_event_name": "Stop", "session_id": "s", "transcript_path": "/tmp/t"},
}


def run_hook(cwd, event):
    completed = subprocess.run([sys.executable, str(HOOK)], input=json.dumps(event), capture_output=True, text=True, check=True, cwd=str(cwd))
    return json.loads(completed.stdout) if completed.stdout.strip() else {}


@pytest.fixture
def campaign(tmp_path):
    (tmp_path / "kapso_task.md").write_text("# Task\n\n## Data\n\n`kapso_datasets/` at the campaign root\n")
    (tmp_path / "kapso_datasets").mkdir()
    (tmp_path / "kapso_datasets" / "seeds.txt").write_text("0001\n0002\n\n0003\n")
    return tmp_path


@pytest.mark.parametrize("host", sorted(STOP_EVENTS), ids=sorted(STOP_EVENTS))
def test_a_finish_is_blocked_until_every_listed_seed_is_scored(campaign, host):
    event = STOP_EVENTS[host]
    decision = run_hook(campaign, event)
    assert decision["decision"] == "block" and "scores.json is missing" in decision["reason"]
    (campaign / "results").mkdir()
    (campaign / "results" / "scores.json").write_text(json.dumps({"seeds": {
        "0001": {"score": 10, "runtime_ms": 100, "status": "ok"},
        "0002": {"score": 0, "runtime_ms": 2100, "status": "time-limit"},
    }}))
    decision = run_hook(campaign, event)
    assert decision["decision"] == "block" and "0003 missing" in decision["reason"]
    (campaign / "results" / "scores.json").write_text(json.dumps({"seeds": {
        "0001": {"score": 10, "runtime_ms": 100, "status": "ok"},
        "0002": {"score": 0, "runtime_ms": 2100, "status": "time-limit"},
        "0003": {"score": 7.5, "runtime_ms": 900, "status": "ok"},
    }}))
    assert run_hook(campaign, event) == {}


def test_the_hook_reads_the_task_root_from_a_session_directory_below_the_campaign(campaign):
    session = campaign / "sessions" / "attempt-1"
    session.mkdir(parents=True)
    decision = run_hook(session, STOP_EVENTS["claude-code"])
    assert decision["decision"] == "block"


def test_no_seed_list_means_no_opinion(tmp_path):
    (tmp_path / "kapso_task.md").write_text("# Task\n")
    (tmp_path / "kapso_datasets").mkdir()
    assert run_hook(tmp_path, STOP_EVENTS["codex"]) == {}
    assert run_hook(tmp_path / "kapso_datasets", STOP_EVENTS["codex"]) == {}


def test_a_malformed_results_file_is_blocked_with_the_reason(campaign):
    (campaign / "results").mkdir()
    (campaign / "results" / "scores.json").write_text(json.dumps([1, 2]))
    assert "no `seeds` mapping" in run_hook(campaign, STOP_EVENTS["claude-code"])["reason"]


def test_the_manifest_lists_the_hook_on_implementation_only():
    modules = yaml.safe_load((CONTEST / "harness.yaml").read_text())["modules"]
    listed = {module for module, entry in modules.items() if "require-scorer-run" in entry.get("hooks", [])}
    assert listed == {"implementation"}
