"""S1's driver (docs/plans/redesign/wp9-semantic-suite.md, change 6): the
task table and the suite agree on the steps; the docs snapshot is the
pages docs.json navigates to and nothing else; a task view is the
repository's own README; a session's init event proves the sandbox cold;
the counted verb's executions are read from a session's stream (help,
doctor and reads never count; an errored execution followed by a success
is an error that led to its fix); the evidence predicates read the
artifacts a task leaves; the two counts the design names are metrics."""

import importlib.util
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts" / "redesign"))
spec = importlib.util.spec_from_file_location("s1_cold_engineer", ROOT / "scripts" / "redesign" / "s1_cold_engineer.py")
s1 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(s1)


def test_the_task_table_and_the_suite_agree_on_the_steps():
    assert [task["number"] for task in s1.TASKS] == [1, 2, 3, 4, 5, 6]
    assert all(task["verb"] in s1.VERB_PATTERNS for task in s1.TASKS)
    assert s1.STEP_NAMES == s1.SUITE["tests"]["S1"]["required_steps"]["claude_code"]


def test_the_docs_snapshot_is_the_navigated_pages_and_nothing_else(tmp_path):
    pages = s1.navigated_pages(ROOT)
    assert "index" in pages and "installation" in pages and "coding-agent-skills" in pages
    assert not any(page.startswith(("plans/", "research/")) for page in pages)
    source = tmp_path / "docs"
    (source / "plans").mkdir(parents=True)
    (source / "index.mdx").write_text("# start\n")
    (source / "plans" / "secret.mdx").write_text("# a plan\n")
    count = s1.snapshot_docs(source, ["index", "missing"], tmp_path / "snapshot")
    assert count == 1 and (tmp_path / "snapshot" / "index.mdx").is_file() and not (tmp_path / "snapshot" / "plans").exists()


def test_a_task_view_is_the_repositorys_own_readme(tmp_path):
    s1.task_view(ROOT / "examples" / "churn-first-build", tmp_path / "task", generate=False)
    readme = (tmp_path / "task" / "README.md").read_text()
    assert readme.startswith("# Churn model") and "kapso build" not in readme and "Recorded result" not in readme
    assert (tmp_path / "task" / "kapso-brief.md").is_file() and (tmp_path / "task" / "repo" / "predict.py").is_file()
    assert not (tmp_path / "task" / "run.py").exists() and not (tmp_path / "task" / "baseline.json").exists()


def test_the_init_event_proves_the_sandbox_cold():
    warm = {"type": "system", "subtype": "init", "plugins": [{"source": "kapso@kapso"}], "mcp_servers": [{"name": "plugin:kapso:kapso"}], "slash_commands": ["kapso:build", "help"], "tools": ["Bash", "WebFetch"]}
    init = s1.session_init([warm])
    assert init == {"plugins": ["kapso@kapso"], "mcp_servers": ["plugin:kapso:kapso"], "kapso_commands": ["kapso:build"], "web_tools": ["WebFetch"]} and not s1.is_cold(init)
    cold = {"type": "system", "subtype": "init", "plugins": [{"source": "cc-plugin-telemetry@builtin"}], "mcp_servers": [], "slash_commands": ["help"], "tools": ["Bash", "Read"]}
    assert s1.is_cold(s1.session_init([cold]))
    assert not s1.is_cold(s1.session_init([]))


def _stream(calls):
    """A Claude Code stream of Bash calls, each (command, errored)."""
    rows = []
    for number, (command, errored) in enumerate(calls):
        rows.append({"type": "assistant", "message": {"content": [{"type": "tool_use", "id": f"t{number}", "name": "Bash", "input": {"command": command}}]}})
        rows.append({"type": "user", "message": {"content": [{"type": "tool_result", "tool_use_id": f"t{number}", "is_error": errored, "content": "Error: x" if errored else "ok"}]}})
    return rows


def test_the_counted_verbs_executions_are_read_from_the_stream(tmp_path):
    rows = _stream([("kapso build --help", False), ("kapso doctor build", False), ("cat docs/index.mdx", False), ("kapso build --brief b.md --output campaign-1", True), ("kapso build --brief b.md --repo repo --output campaign-1 --detach", False)])
    found = s1.executions(rows, "build", "cli", tmp_path)
    assert [entry["errored"] for entry in found] == [True, False]
    metrics = s1.attempt_metrics(found, evidence=True, started=0.0, evidence_at=90.0)
    assert metrics == {"first_try": False, "wrong_calls": 1, "minutes_to_launch": 1.5, "error_led_to_fix": True, "executions": 2, "evidence": True}
    assert s1.attempt_metrics(found[1:], evidence=True, started=0.0, evidence_at=60.0)["first_try"] is True
    assert s1.attempt_metrics([], evidence=False, started=0.0, evidence_at=None)["first_try"] is False
    # The Python surface counts a script that carries the call, run with python.
    (tmp_path / "run_build.py").write_text("from kapso import Kapso, Brief\nsolution = Kapso().build(Brief.read('task/kapso-brief.md'), repo='task/repo', output='campaign-1')\nprint(solution.explain())\n")
    (tmp_path / "look.py").write_text("print('hello')\n")
    rows = _stream([("./venv/bin/python look.py", False), ("cat run_build.py", False), ("./venv/bin/python run_build.py", False)])
    found = s1.executions(rows, "build", "python", tmp_path)
    assert len(found) == 1 and found[0]["errored"] is False
    assert s1.executions(_stream([("kapso build --output c --resume --detach", False)]), "resume", "cli", tmp_path)
    assert not s1.executions(_stream([("kapso build --output c --resume --detach", False)]), "build", "cli", tmp_path)


def test_the_evidence_predicates_read_what_a_task_leaves(tmp_path):
    sandbox = tmp_path
    prereq = sandbox / "campaign-prereq"
    assert not s1.evidence_of(s1.TASKS[0], sandbox, prereq)
    (sandbox / "campaign-1" / ".kapso").mkdir(parents=True)
    (sandbox / "campaign-1" / ".kapso" / "status.json").write_text(json.dumps({"state": "running", "harness": None}))
    assert s1.evidence_of(s1.TASKS[0], sandbox, prereq)
    (sandbox / "campaign-3" / ".kapso").mkdir(parents=True)
    (sandbox / "campaign-3" / ".kapso" / "status.json").write_text(json.dumps({"state": "running", "harness": None}))
    assert not s1.evidence_of(s1.TASKS[2], sandbox, prereq), "the harness task needs the harness in the status"
    (sandbox / "campaign-3" / ".kapso" / "status.json").write_text(json.dumps({"state": "running", "harness": "trading 0.1.0"}))
    assert s1.evidence_of(s1.TASKS[2], sandbox, prereq)
    (prereq / ".kapso" / "deployments" / "1").mkdir(parents=True)
    assert not s1.evidence_of(s1.TASKS[3], sandbox, prereq)
    (prereq / ".kapso" / "deployments" / "1" / "deployment.json").write_text("{}")
    assert s1.evidence_of(s1.TASKS[3], sandbox, prereq)
    (sandbox / "task" / "learning" / "status").mkdir(parents=True)
    assert not s1.evidence_of(s1.TASKS[4], sandbox, prereq)
    (sandbox / "task" / "learning" / "status" / "learn-1.json").write_text("{}")
    assert s1.evidence_of(s1.TASKS[4], sandbox, prereq)
    (sandbox / "campaign-killed" / ".kapso").mkdir(parents=True)
    (sandbox / "campaign-killed" / ".kapso" / "status.json").write_text(json.dumps({"state": "running", "pid": os.getpid()}))
    assert s1.evidence_of(s1.TASKS[5], sandbox, prereq)
    (sandbox / "campaign-killed" / ".kapso" / "status.json").write_text(json.dumps({"state": "running", "pid": 2 ** 22 - 1}))
    assert not s1.evidence_of(s1.TASKS[5], sandbox, prereq)


def test_the_two_counts_and_the_run_metrics(tmp_path):
    (tmp_path / "a.py").write_text("import kapso\n\n# a comment\nx = 1\n")
    (tmp_path / "b.py").write_text("y = 2\n")
    assert s1.python_lines(tmp_path, ["a.py", "b.py", "missing.py"]) == 3
    record = {"steps": [
        {"name": "task1-python", "kind": "attempt", "metrics": {"first_try": True, "wrong_calls": 0, "error_led_to_fix": None}},
        {"name": "task1-cli", "kind": "attempt", "metrics": {"first_try": False, "wrong_calls": 2, "error_led_to_fix": True}},
        {"name": "task2-cli", "kind": "attempt", "metrics": {"first_try": False, "wrong_calls": 1, "error_led_to_fix": False}},
        {"name": "flow-counts", "kind": "shell", "metrics": {"python_lines": 9, "cli_commands": 5}},
    ], "metrics": {"comprehension_correct": 1.0}}
    assert s1.run_metrics(record) == {"first_try_count": 1, "errors_led_to_fix": 0.5, "comprehension_correct": 1.0, "python_lines": 9, "cli_commands": 5}
