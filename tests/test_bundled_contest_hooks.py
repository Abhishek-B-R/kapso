"""The competitive-programming harness's hooks on both hosts' event shapes
(docs/plans/redesign/wp8-harness-ports.md, changes 7 to 9):
`require-scorer-run` asks once for a results file of the scorer-cli
skill's shape, written after the solution's last change, for every seed of
the task root's list, and has no opinion without a list; `deny-shell-submit`
denies a raw submission in the shell where the task root's descriptor names
a procedure and nothing else; `require-insurance` asks once for the first
submission in the ledger the descriptor names and has no opinion without a
descriptor; a corrupt evidence file blocks through the launcher line rather
than passing; the manifest lists the three on implementation only."""

import json
import os
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
SCORED = {
    "0001": {"score": 10.0, "spread": 0.5, "runtime_ms": 100, "status": "ok"},
    "0002": {"score": 0.0, "spread": 0.0, "runtime_ms": 2100, "status": "time-limit"},
    "0003": {"score": 7.5, "spread": 0.2, "runtime_ms": 900, "status": "ok"},
}


def run_hook(name, script, cwd, event):
    completed = subprocess.run([sys.executable, str(HOOKS / name / script)], input=json.dumps(event),
                               capture_output=True, text=True, check=True, cwd=str(cwd))
    return json.loads(completed.stdout) if completed.stdout.strip() else {}


def run_launcher(name, cwd, event):
    """The hook as the host runs it: hook.json's command line through the shell."""
    entries = json.loads((HOOKS / name / "hook.json").read_text())["hooks"]
    command = next(iter(entries.values()))[0]["hooks"][0]["command"].replace("${PLUGIN_ROOT}", str(CONTEST))
    return subprocess.run(["bash", "-c", command], input=json.dumps(event), capture_output=True, text=True, cwd=str(cwd))


def write_results(campaign, seeds, **top):
    (campaign / "results").mkdir(exist_ok=True)
    payload = {"build": "g++ -O2 src/main.cpp", "solution": "src/main.cpp", "runs": 4, "seeds": seeds, **top}
    (campaign / "results" / "scores.json").write_text(json.dumps(payload))


@pytest.fixture
def campaign(tmp_path):
    (tmp_path / "kapso_task.md").write_text("# Task\n\n## Data\n\n`kapso_datasets/` at the campaign root\n")
    (tmp_path / "kapso_datasets").mkdir()
    (tmp_path / "kapso_datasets" / "seeds.txt").write_text("0001\n0002\n\n0003\n")
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "main.cpp").write_text("int main() {}\n")
    return tmp_path


@pytest.fixture
def contest(tmp_path):
    root = tmp_path / "contest"
    root.mkdir()
    (root / "kapso_task.md").write_text("# Task\n")
    data = root / "kapso_datasets"
    data.mkdir()
    ledger = root / "artifacts" / "submissions.json"
    (data / "contest.json").write_text(json.dumps({"competition": "my-contest", "ledger": str(ledger),
                                                   "procedure": "python3 kapso_datasets/submit.py"}))
    return root


@pytest.mark.parametrize("host", sorted(STOP_EVENTS), ids=sorted(STOP_EVENTS))
def test_a_finish_is_blocked_until_every_listed_seed_is_scored(campaign, host):
    event = STOP_EVENTS[host]
    decision = run_hook("require-scorer-run", "require_scorer_run.py", campaign, event)
    assert decision["decision"] == "block" and "scores.json is missing" in decision["reason"]
    write_results(campaign, {seed: SCORED[seed] for seed in ("0001", "0002")})
    decision = run_hook("require-scorer-run", "require_scorer_run.py", campaign, event)
    assert decision["decision"] == "block" and "0003 (missing)" in decision["reason"]
    write_results(campaign, SCORED)
    assert run_hook("require-scorer-run", "require_scorer_run.py", campaign, event) == {}


@pytest.mark.parametrize("name, script", [("require-scorer-run", "require_scorer_run.py"), ("require-insurance", "require_insurance.py")])
def test_a_stop_hook_asks_once(campaign, contest, name, script):
    """With `stop_hook_active` set the session is already continuing because of a
    stop hook, and both hooks stay silent although nothing is satisfied."""
    cwd = campaign if name == "require-scorer-run" else contest
    event = {**STOP_EVENTS["claude-code"], "stop_hook_active": True}
    assert run_hook(name, script, cwd, event) == {}
    assert run_hook(name, script, cwd, STOP_EVENTS["claude-code"])["decision"] == "block"


def test_the_task_root_is_the_nearest_statement_with_a_data_directory(campaign):
    """A session directory below the campaign, even one holding a statement
    of its own without data beside it, resolves to the campaign's root."""
    session = campaign / "sessions" / "attempt-1"
    session.mkdir(parents=True)
    (session / "kapso_task.md").write_text("# a copy without data\n")
    assert run_hook("require-scorer-run", "require_scorer_run.py", session, STOP_EVENTS["claude-code"])["decision"] == "block"


def test_no_seed_list_means_no_opinion_and_an_empty_one_blocks(tmp_path):
    (tmp_path / "kapso_task.md").write_text("# Task\n")
    (tmp_path / "kapso_datasets").mkdir()
    assert run_hook("require-scorer-run", "require_scorer_run.py", tmp_path, STOP_EVENTS["codex"]) == {}
    assert run_hook("require-scorer-run", "require_scorer_run.py", tmp_path / "kapso_datasets", STOP_EVENTS["codex"]) == {}
    (tmp_path / "kapso_datasets" / "seeds.txt").write_text("\n\n")
    assert "lists no seed" in run_hook("require-scorer-run", "require_scorer_run.py", tmp_path, STOP_EVENTS["codex"])["reason"]


@pytest.mark.parametrize("seeds, top, fragment", [
    ({**SCORED, "0001": {**SCORED["0001"], "score": True}}, {}, "0001 (no finite numeric score)"),
    ({**SCORED, "0002": {**SCORED["0002"], "runtime_ms": -5}}, {}, "0002 (no non-negative runtime_ms)"),
    ({**SCORED, "0003": {**SCORED["0003"], "status": "fine"}}, {}, "0003 (status not one of"),
    ({**SCORED, "0003": {**SCORED["0003"], "spread": "wide"}}, {}, "0003 (no non-negative spread)"),
    (SCORED, {"build": ""}, "names no `build`"),
    (SCORED, {"solution": "src/other.cpp"}, "does not exist"),
    (SCORED, {"runs": 0}, "no positive integer `runs`"),
])
def test_a_results_file_of_the_wrong_shape_is_blocked_naming_the_problem(campaign, seeds, top, fragment):
    write_results(campaign, seeds, **top)
    decision = run_hook("require-scorer-run", "require_scorer_run.py", campaign, STOP_EVENTS["claude-code"])
    assert decision["decision"] == "block" and fragment in decision["reason"]


def test_a_malformed_results_file_is_blocked_with_the_reason(campaign):
    (campaign / "results").mkdir()
    (campaign / "results" / "scores.json").write_text(json.dumps([1, 2]))
    assert "no `seeds` mapping" in run_hook("require-scorer-run", "require_scorer_run.py", campaign, STOP_EVENTS["claude-code"])["reason"]


def test_a_solution_changed_after_the_scorer_ran_is_blocked(campaign):
    write_results(campaign, SCORED)
    results = campaign / "results" / "scores.json"
    stale = results.stat().st_mtime - 60
    os.utime(results, (stale, stale))
    decision = run_hook("require-scorer-run", "require_scorer_run.py", campaign, STOP_EVENTS["claude-code"])
    assert decision["decision"] == "block" and "changed after" in decision["reason"]


@pytest.mark.parametrize("name, relative, named", [
    ("require-scorer-run", "results/scores.json", "results/scores.json"),
    ("require-insurance", "artifacts/submissions.json", "ledger"),
])
def test_a_corrupt_evidence_file_blocks_through_the_launcher_line(campaign, contest, name, relative, named):
    """The script fails loud on a file that is not JSON; hook.json's launcher
    line turns that into exit code 2, the hosts' blocking error, with the
    traceback naming the file or its role on stderr."""
    cwd = campaign if name == "require-scorer-run" else contest
    target = cwd / relative
    target.parent.mkdir(exist_ok=True)
    target.write_text("{not json")
    completed = run_launcher(name, cwd, STOP_EVENTS["claude-code"])
    assert completed.returncode == 2 and "JSONDecodeError" in completed.stderr and named in completed.stderr


@pytest.mark.parametrize("command", [
    "kaggle competitions submit my-contest -k me/kernel -v 3 -f submission.csv -m 'idea local=0.9'",
    "cd kernel && kaggle c submit my-contest -f out.csv -m x",
    "kaggle kernels push -p kernel/ ; kaggle competitions submit my-contest -f out.csv",
    "/usr/bin/kaggle competitions submit my-contest -f out.csv -m x",
    "./venv/bin/kaggle c submit my-contest -f out.csv -m x",
    "kaggle competitions \\\n    submit my-contest -f out.csv -m x",
    "python3 -c 'import kaggle; kaggle.api.competition_submit(\"out.csv\", \"x\", \"my-contest\")'",
])
def test_a_raw_submission_in_the_shell_is_denied_where_the_root_names_a_procedure(contest, command):
    decision = run_hook("deny-shell-submit", "deny_shell_submit.py", contest, {"tool_name": "Bash", "tool_input": {"command": command}})
    output = decision["hookSpecificOutput"]
    assert output["hookEventName"] == "PreToolUse" and output["permissionDecision"] == "deny"
    assert "python3 kapso_datasets/submit.py" in output["permissionDecisionReason"]


@pytest.mark.parametrize("command", [
    "kaggle kernels push -p kernel/",
    "kaggle competitions submissions my-contest --format json",
    "kaggle competitions download my-contest -p data/",
    "python3 kapso_datasets/submit.py --version 3 -m 'idea local=0.9'",
])
def test_everything_but_a_raw_submission_passes(contest, command):
    assert run_hook("deny-shell-submit", "deny_shell_submit.py", contest, {"tool_name": "Bash", "tool_input": {"command": command}}) == {}


def test_without_a_procedure_the_raw_submission_is_the_way_to_submit(tmp_path):
    command = {"tool_name": "Bash", "tool_input": {"command": "kaggle competitions submit my-contest -f out.csv -m x"}}
    assert run_hook("deny-shell-submit", "deny_shell_submit.py", tmp_path, command) == {}
    (tmp_path / "kapso_task.md").write_text("# Task\n")
    (tmp_path / "kapso_datasets").mkdir()
    assert run_hook("deny-shell-submit", "deny_shell_submit.py", tmp_path, command) == {}
    (tmp_path / "kapso_datasets" / "contest.json").write_text(json.dumps({"competition": "my-contest", "ledger": "/tmp/l.json"}))
    assert run_hook("deny-shell-submit", "deny_shell_submit.py", tmp_path, command) == {}


@pytest.mark.parametrize("host", sorted(STOP_EVENTS), ids=sorted(STOP_EVENTS))
def test_a_finish_is_blocked_before_the_first_submission_is_in_the_ledger(contest, host):
    event = STOP_EVENTS[host]
    ledger = contest / "artifacts" / "submissions.json"
    decision = run_hook("require-insurance", "require_insurance.py", contest, event)
    assert decision["decision"] == "block" and "does not exist" in decision["reason"]
    ledger.parent.mkdir()
    ledger.write_text(json.dumps({"submissions": []}))
    assert "records none" in run_hook("require-insurance", "require_insurance.py", contest, event)["reason"]
    ledger.write_text(json.dumps({"submissions": [None, {"competition": "other", "submission_id": "1"}, {"competition": "my-contest"}]}))
    assert "records none" in run_hook("require-insurance", "require_insurance.py", contest, event)["reason"]
    # The evaluator's vocabulary: a refused (`rejected`) or failed (`error`)
    # submission is no insurance; one awaiting its score or scored is.
    for status in ("rejected", "error"):
        ledger.write_text(json.dumps({"submissions": [{"competition": "my-contest", "kernel_ref": "me/kernel", "version": 1,
                                                       "submission_id": "7", "status": status}]}))
        assert "records none" in run_hook("require-insurance", "require_insurance.py", contest, event)["reason"]
    for status in ("pending", "complete"):
        ledger.write_text(json.dumps({"submissions": [{"competition": "my-contest", "kernel_ref": "me/kernel", "version": 1,
                                                       "submission_id": "7", "status": status}]}))
        assert run_hook("require-insurance", "require_insurance.py", contest, event) == {}


@pytest.mark.parametrize("descriptor, fragment", [
    ({"ledger": "/tmp/l.json"}, "names no competition"),
    ({"competition": "my-contest", "ledger": "artifacts/submissions.json"}, "no absolute ledger path"),
])
def test_an_incomplete_descriptor_is_blocked_as_an_incomplete_root(tmp_path, descriptor, fragment):
    (tmp_path / "kapso_task.md").write_text("# Task\n")
    (tmp_path / "kapso_datasets").mkdir()
    (tmp_path / "kapso_datasets" / "contest.json").write_text(json.dumps(descriptor))
    assert fragment in run_hook("require-insurance", "require_insurance.py", tmp_path, STOP_EVENTS["codex"])["reason"]


def test_no_contest_descriptor_means_no_opinion_on_insurance(tmp_path):
    (tmp_path / "kapso_task.md").write_text("# Task\n")
    (tmp_path / "kapso_datasets").mkdir()
    assert run_hook("require-insurance", "require_insurance.py", tmp_path, STOP_EVENTS["codex"]) == {}


def test_the_manifest_lists_the_three_hooks_on_implementation_only():
    modules = yaml.safe_load((CONTEST / "harness.yaml").read_text())["modules"]
    for hook in ("require-scorer-run", "deny-shell-submit", "require-insurance"):
        listed = {module for module, entry in modules.items() if hook in entry.get("hooks", [])}
        assert listed == {"implementation"}, hook
