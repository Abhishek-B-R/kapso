"""The competitive-programming harness's hooks on both hosts' event shapes
(docs/plans/redesign/wp8-harness-ports.md, changes 7 and 8):
`require-scorer-run` blocks a finish while a seed of the task root's list
lacks a scorer result and has no opinion without a list; `deny-shell-submit`
denies a raw submission in the shell and nothing else; `require-insurance`
blocks a finish before the first submission is in the ledger the task root
names and has no opinion without a contest descriptor; the manifest lists
the three on implementation only."""

import json
import subprocess
import sys

import pytest
import yaml

from kapso.harness import BUNDLED_ROOT

CONTEST = BUNDLED_ROOT / "competitive-programming"
HOOKS = CONTEST / "hooks"
STOP_EVENTS = {
    "claude-code": {"hook_event_name": "Stop", "stop_hook_active": False, "session_id": "s"},
    "codex": {"hook_event_name": "Stop", "session_id": "s", "transcript_path": "/tmp/t"},
}


def run_hook(name, script, cwd, event):
    completed = subprocess.run([sys.executable, str(HOOKS / name / script)], input=json.dumps(event),
                               capture_output=True, text=True, check=True, cwd=str(cwd))
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
    decision = run_hook("require-scorer-run", "require_scorer_run.py", campaign, event)
    assert decision["decision"] == "block" and "scores.json is missing" in decision["reason"]
    (campaign / "results").mkdir()
    (campaign / "results" / "scores.json").write_text(json.dumps({"seeds": {
        "0001": {"score": 10, "runtime_ms": 100, "status": "ok"},
        "0002": {"score": 0, "runtime_ms": 2100, "status": "time-limit"},
    }}))
    decision = run_hook("require-scorer-run", "require_scorer_run.py", campaign, event)
    assert decision["decision"] == "block" and "0003 missing" in decision["reason"]
    (campaign / "results" / "scores.json").write_text(json.dumps({"seeds": {
        "0001": {"score": 10, "runtime_ms": 100, "status": "ok"},
        "0002": {"score": 0, "runtime_ms": 2100, "status": "time-limit"},
        "0003": {"score": 7.5, "runtime_ms": 900, "status": "ok"},
    }}))
    assert run_hook("require-scorer-run", "require_scorer_run.py", campaign, event) == {}


def test_the_scorer_hook_reads_the_task_root_from_a_session_directory_below_the_campaign(campaign):
    session = campaign / "sessions" / "attempt-1"
    session.mkdir(parents=True)
    assert run_hook("require-scorer-run", "require_scorer_run.py", session, STOP_EVENTS["claude-code"])["decision"] == "block"


def test_no_seed_list_means_no_opinion(tmp_path):
    (tmp_path / "kapso_task.md").write_text("# Task\n")
    (tmp_path / "kapso_datasets").mkdir()
    assert run_hook("require-scorer-run", "require_scorer_run.py", tmp_path, STOP_EVENTS["codex"]) == {}
    assert run_hook("require-scorer-run", "require_scorer_run.py", tmp_path / "kapso_datasets", STOP_EVENTS["codex"]) == {}


def test_a_malformed_results_file_is_blocked_with_the_reason(campaign):
    (campaign / "results").mkdir()
    (campaign / "results" / "scores.json").write_text(json.dumps([1, 2]))
    assert "no `seeds` mapping" in run_hook("require-scorer-run", "require_scorer_run.py", campaign, STOP_EVENTS["claude-code"])["reason"]


@pytest.mark.parametrize("command", [
    "kaggle competitions submit my-contest -k me/kernel -v 3 -f submission.csv -m 'idea local=0.9'",
    "cd kernel && kaggle c submit my-contest -f out.csv -m x",
    "kaggle kernels push -p kernel/ ; kaggle competitions submit my-contest -f out.csv",
])
def test_a_raw_submission_in_the_shell_is_denied_with_the_reason(tmp_path, command):
    decision = run_hook("deny-shell-submit", "deny_shell_submit.py", tmp_path, {"tool_name": "Bash", "tool_input": {"command": command}})
    output = decision["hookSpecificOutput"]
    assert output["hookEventName"] == "PreToolUse" and output["permissionDecision"] == "deny"
    assert "submission procedure the task root provides" in output["permissionDecisionReason"]


@pytest.mark.parametrize("command", [
    "kaggle kernels push -p kernel/",
    "kaggle competitions submissions my-contest --format json",
    "kaggle competitions download my-contest -p data/",
    "python3 kapso_datasets/submit.py --version 3 -m 'idea local=0.9'",
])
def test_everything_but_a_raw_submission_passes(tmp_path, command):
    assert run_hook("deny-shell-submit", "deny_shell_submit.py", tmp_path, {"tool_name": "Bash", "tool_input": {"command": command}}) == {}


@pytest.mark.parametrize("host", sorted(STOP_EVENTS), ids=sorted(STOP_EVENTS))
def test_a_finish_is_blocked_before_the_first_submission_is_in_the_ledger(tmp_path, host):
    (tmp_path / "kapso_task.md").write_text("# Task\n")
    data = tmp_path / "kapso_datasets"
    data.mkdir()
    ledger = tmp_path / "artifacts" / "submissions.json"
    (data / "contest.json").write_text(json.dumps({"competition": "my-contest", "ledger": str(ledger)}))
    event = STOP_EVENTS[host]
    decision = run_hook("require-insurance", "require_insurance.py", tmp_path, event)
    assert decision["decision"] == "block" and "does not exist" in decision["reason"]
    ledger.parent.mkdir()
    ledger.write_text(json.dumps({"submissions": []}))
    assert "lists none" in run_hook("require-insurance", "require_insurance.py", tmp_path, event)["reason"]
    ledger.write_text(json.dumps({"submissions": [{"kernel_ref": "me/kernel", "version": 1, "submission_id": "7", "status": "pending"}]}))
    assert run_hook("require-insurance", "require_insurance.py", tmp_path, event) == {}


def test_no_contest_descriptor_means_no_opinion_on_insurance(tmp_path):
    (tmp_path / "kapso_task.md").write_text("# Task\n")
    (tmp_path / "kapso_datasets").mkdir()
    assert run_hook("require-insurance", "require_insurance.py", tmp_path, STOP_EVENTS["codex"]) == {}


def test_the_manifest_lists_the_three_hooks_on_implementation_only():
    modules = yaml.safe_load((CONTEST / "harness.yaml").read_text())["modules"]
    for hook in ("require-scorer-run", "deny-shell-submit", "require-insurance"):
        listed = {module for module, entry in modules.items() if hook in entry.get("hooks", [])}
        assert listed == {"implementation"}, hook
