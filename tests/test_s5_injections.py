"""S5's tooling (docs/plans/redesign/wp9-semantic-suite.md, change 8): the
provider-limit shim passes every call through and answers the
reconstructed limit only for an armed session turn, N times, counting (a
real local subprocess); the enrichment service answers the table to the
key alone and logs every request; the timeline sampler reads the stored
state beside the observed liveness; "truthful within one heartbeat" is
read from a timeline; the request's text names the variable and never a
value; the diagnosis is read for the class and the fix; the run-level
metrics aggregate the injections."""

import importlib.util
import json
import os
import stat
import subprocess
import sys
import threading
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts" / "redesign"))


def _load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / "redesign" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


s5 = _load("s5_injections")
service = _load("enrichment_service")
timeline = _load("status_timeline")


def test_the_shim_passes_through_and_answers_an_armed_session_turn_n_times(tmp_path):
    shim = tmp_path / "shim"
    shim.mkdir()
    real = tmp_path / "real-claude"
    real.write_text("#!/usr/bin/env bash\necho real: \"$@\"\n")
    real.chmod(real.stat().st_mode | stat.S_IEXEC)
    (shim / "claude").write_text(s5.SHIM)
    (shim / "claude").chmod(0o755)
    (shim / "real").write_text(str(real))
    (shim / "limit").write_text("2")
    (shim / "count").write_text("0")
    (shim / "exit").write_text("1")
    (shim / "stdout.jsonl").write_text("\n".join(json.dumps(row) for row in s5.RECONSTRUCTED_LIMIT["stdout"]) + "\n")
    (shim / "stderr.txt").write_text(s5.RECONSTRUCTED_LIMIT["stderr"] + "\n")

    def call(*args):
        return subprocess.run([str(shim / "claude"), *args], capture_output=True, text=True)

    assert call("--version").stdout == "real: --version\n", "a version call passes through"
    assert call("-p", "hello", "--output-format", "stream-json").stdout.startswith("real:"), "unarmed, a session turn passes through"
    (shim / "armed").write_text("")
    assert call("auth", "status").stdout.startswith("real:"), "armed, a non-session call still passes through"
    first = call("-p", "hello", "--output-format", "stream-json")
    rows = [json.loads(line) for line in first.stdout.splitlines()]
    assert first.returncode == 1 and rows[-1]["is_error"] and "rate_limit_error" in rows[-1]["result"] and "429" in first.stderr
    second = call("-p", "hello", "--output-format", "stream-json")
    assert second.returncode == 1 and (shim / "count").read_text().strip() == "2" and len((shim / "fired").read_text().splitlines()) == 2
    third = call("-p", "hello", "--output-format", "stream-json")
    assert third.returncode == 0 and third.stdout.startswith("real:"), "after N the CLI runs"


def test_the_enrichment_service_answers_the_key_alone_logs_with_time_and_covers_the_fixture_range(tmp_path):
    log = tmp_path / "requests.log"
    server = service.serve(0, "the-key", log, rows=13000)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    with pytest.raises(urllib.error.HTTPError) as refused:
        urllib.request.urlopen(f"http://127.0.0.1:{port}/table")
    assert refused.value.code == 401
    request = urllib.request.Request(f"http://127.0.0.1:{port}/table", headers={"Authorization": "Bearer the-key"})
    body = urllib.request.urlopen(request).read().decode()
    # The table covers the hold-out ids the evaluator scores (C010001…C013000), not an arbitrary 3000.
    assert body.startswith("id,segment,risk_score\nC000001,") and body.count("\n") == 13001 and "\nC013000," in body
    request = urllib.request.Request(f"http://127.0.0.1:{port}/enrich?customer_id=C010001", headers={"Authorization": "Bearer the-key"})
    assert json.loads(urllib.request.urlopen(request).read())["id"] == "C010001"
    server.shutdown()
    entries = [json.loads(line) for line in log.read_text().splitlines()]
    assert [entry["authorized"] for entry in entries] == [False, True, True] and entries[0]["status"] == 401
    assert all("ts" in entry for entry in entries), "every request is timestamped, so a fetch can be placed after the reply"
    assert service.row("C000001") == service.row("C000001") and service.row("C000001") != service.row("C000002")


def test_shown_state_reads_the_verdict_kapso_watch_prints():
    assert timeline.shown_state("churn-campaign   DEAD   120s ago") == "DEAD"
    assert timeline.shown_state("state: RUNNING (phase implementation)") == "RUNNING"
    assert timeline.shown_state("nothing here") is None


def test_the_sampler_records_what_watch_shows_beside_the_stored_status(tmp_path, monkeypatch):
    beat = (datetime.now(timezone.utc) - timedelta(seconds=20)).isoformat(timespec="seconds")
    calls = {"human": "churn   DEAD   200s ago", "json": json.dumps({"state": "running", "phase": "implementation", "pid": 2 ** 22 - 1, "heartbeat_at": beat, "best": None})}

    def fake_run(cmd, capture_output, text):
        out = calls["json"] if "--json" in cmd else calls["human"]
        return type("R", (), {"returncode": 0, "stdout": out, "stderr": ""})()

    monkeypatch.setattr(timeline.subprocess, "run", fake_run)
    row = timeline.sample(tmp_path / "campaign")
    assert row["shown"] == "DEAD" and row["stored"]["state"] == "running" and row["pid_alive"] is False


def _row(seconds_after, shown, base):
    return {"ts": (base + timedelta(seconds=seconds_after)).isoformat(timespec="seconds"), "shown": shown}


def test_truthful_within_one_heartbeat_is_read_from_what_watch_showed():
    base = datetime(2026, 10, 27, 10, 0, tzinfo=timezone.utc)
    assert s5.truthful_within([_row(-60, "RUNNING", base), _row(30, "DEAD", base)], base, 60.0, expect_terminal=True) is True, "watch showed DEAD within a heartbeat"
    assert s5.truthful_within([_row(-60, "RUNNING", base), _row(30, "RUNNING", base), _row(200, "DEAD", base)], base, 60.0, expect_terminal=True) is False, "still shown RUNNING a heartbeat later"
    assert s5.truthful_within([_row(-60, "RUNNING", base), _row(30, "RUNNING", base), _row(90, "RUNNING", base)], base, 60.0, expect_terminal=False) is True, "a living writer shown running"
    assert s5.truthful_within([_row(-60, "RUNNING", base), _row(30, "STALLED", base)], base, 60.0, expect_terminal=False) is False, "shown STALLED is not a happy run"
    assert s5.truthful_within([_row(-60, "RUNNING", base), _row(40, "DONE", base)], base, 60.0, expect_terminal=False) is True
    assert s5.truthful_within([_row(-60, "RUNNING", base), _row(200, "FAILED", base)], base, 60.0, expect_terminal=False) is None, "no sample inside the window"


def test_bank_state_reads_a_bare_repo_and_fails_unreadable(tmp_path):

    bare = tmp_path / "bank.git"
    work = tmp_path / "work"
    subprocess.run(["git", "init", "-q", "--bare", str(bare)], check=True)
    subprocess.run(["git", "clone", "-q", str(bare), str(work)], check=True)
    run = lambda *a: subprocess.run(["git", "-C", str(work), *a], capture_output=True, text=True, check=True)
    run("config", "user.email", "x@x")
    run("config", "user.name", "x")
    (work / "insights").mkdir()
    (work / "insights" / "a-card.md").write_text("# card\n")
    (work / "insights" / "index.md").write_text("# index\n")
    run("add", "-A")
    run("commit", "-q", "-m", "one card")
    run("push", "-q", "origin", "HEAD")
    state = s5.bank_state(bare)
    assert state["readable"] is True and state["cards"] == 1 and state["head"], "the bare bank's one card, index.md excluded"
    assert s5.bank_state(tmp_path / "nope")["readable"] is False


def test_the_seeded_bank_is_the_fixture_as_one_commit_in_a_bare_repo(tmp_path):
    # bank-compare compared nothing in every S5 arm before 2026-10-28: no
    # bank was loaded, so "intact" was vacuous. The seed is the fixture's
    # tree, three cards, read back by the same reader the comparison uses.
    state = s5.seed_bank(ROOT / "tests" / "fixtures" / "bank_seed", tmp_path / "bank-seed.git")
    assert state["readable"] is True and state["cards"] == 3 and state["head"]
    assert (tmp_path / "bank-seed.git" / "HEAD").is_file() and not (tmp_path / "bank-seed.git.src").exists()
    assert s5.seed_bank(ROOT / "tests" / "fixtures" / "bank_seed", tmp_path / "bank-seed.git") == state, "re-seeding replaces the bank; the tree is the same"
    with pytest.raises(FileNotFoundError):
        s5.seed_bank(tmp_path / "no-such-fixture", tmp_path / "other.git")


def test_a_crash_is_read_from_the_attempts_own_sessions(tmp_path):
    # evaluator-crash read 0 crashed attempts in four arms: the session ran
    # the evaluator, and the crash sat in the session's stream, not in the
    # trace row.
    campaign = tmp_path / "campaign"
    folder = campaign / ".kapso" / "sessions" / "generic_exp_1"
    folder.mkdir(parents=True)
    (folder / "stream.jsonl").write_text(json.dumps({"type": "tool_result", "text": "FileNotFoundError: private/holdout_labels.csv"}) + "\n", encoding="utf-8")
    attempt = {"node": 1, "sessions": [{"label": "generic_exp_1", "module": "implementation"}], "evaluation": {"score": None}}
    assert s5.session_mentions(campaign, attempt, "holdout_labels.csv")
    assert not s5.session_mentions(campaign, attempt, "ENOSPC")
    assert not s5.session_mentions(campaign, {"sessions": [{"label": "missing"}]}, "holdout_labels.csv")


def test_the_request_names_the_variable_and_never_a_value_and_the_diagnosis_names_its_class(tmp_path):
    inbox = tmp_path / "inbox.jsonl"
    assert s5.request_names_no_value(inbox, "secret-value") is None
    inbox.write_text(json.dumps({"event": "requested", "key": "env:DATA_API_KEY", "hit": "the key is missing"}) + "\n")
    assert s5.request_names_no_value(inbox, "secret-value") is True
    inbox.write_text(json.dumps({"event": "requested", "key": "env:DATA_API_KEY", "hit": "found secret-value in a log"}) + "\n")
    assert s5.request_names_no_value(inbox, "secret-value") is False
    assert s5.names_class_and_fix("The campaign's writer is dead, not running; resume it with --resume.", "killed-writer") == {"names_class": True, "names_fix": True}
    assert s5.names_class_and_fix("All good, nothing to see.", "full-disk") == {"names_class": False, "names_fix": False}


def test_the_run_metrics_aggregate_the_injections():
    record = {"steps": [
        {"name": "provider-limit", "kind": "injection", "metrics": {"user_messages": 2, "truthful": True}},
        {"name": "missing-key", "kind": "injection", "metrics": {"user_messages": 2, "truthful": True, "request_names_no_value": True}},
        {"name": "killed-session", "kind": "injection", "metrics": {"user_messages": 1, "truthful": False}},
        {"name": "bank-compare", "kind": "shell", "metrics": {"bank_intact": True}},
    ]}
    assert s5.run_metrics(record) == {"user_messages_max": 2, "truthful_within_heartbeat": 2 / 3, "requests_name_no_value": 1.0, "bank_intact": 1.0}
    assert s5.STEP_NAMES == s5.SUITE["tests"]["S5"]["required_steps"]["claude_code"]
