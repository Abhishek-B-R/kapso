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


def test_the_enrichment_service_answers_the_key_alone_and_logs_every_request(tmp_path):
    log = tmp_path / "requests.log"
    server = service.serve(0, "the-key", log)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    with pytest.raises(urllib.error.HTTPError) as refused:
        urllib.request.urlopen(f"http://127.0.0.1:{port}/table")
    assert refused.value.code == 401
    request = urllib.request.Request(f"http://127.0.0.1:{port}/table", headers={"Authorization": "Bearer the-key"})
    body = urllib.request.urlopen(request).read().decode()
    assert body.startswith("id,segment,risk_score\nC000001,") and body.count("\n") == service.ROWS + 1
    request = urllib.request.Request(f"http://127.0.0.1:{port}/enrich?customer_id=C010001", headers={"Authorization": "Bearer the-key"})
    assert json.loads(urllib.request.urlopen(request).read())["id"] == "C010001"
    server.shutdown()
    entries = [json.loads(line) for line in log.read_text().splitlines()]
    assert [entry["authorized"] for entry in entries] == [False, True, True] and entries[0]["status"] == 401
    assert service.row("C000001") == service.row("C000001") and service.row("C000001") != service.row("C000002")


def test_the_timeline_reads_the_stored_state_beside_the_observed_liveness(tmp_path):
    campaign = tmp_path / "campaign"
    (campaign / ".kapso").mkdir(parents=True)
    assert timeline.sample(campaign)["stored"] is None
    beat = (datetime.now(timezone.utc) - timedelta(seconds=90)).isoformat(timespec="seconds")
    (campaign / ".kapso" / "status.json").write_text(json.dumps({"state": "running", "phase": "ideation", "iteration": 1, "pid": os.getpid(), "heartbeat_at": beat}))
    row = timeline.sample(campaign)
    assert row["stored"]["state"] == "running" and row["pid_alive"] is True and 85 <= row["heartbeat_age_s"] <= 95
    (campaign / ".kapso" / "status.json").write_text(json.dumps({"state": "running", "pid": 2 ** 22 - 1, "heartbeat_at": beat}))
    assert timeline.sample(campaign)["pid_alive"] is False


def _row(seconds_after, state, pid_alive, base, age=0):
    return {"ts": (base + timedelta(seconds=seconds_after)).isoformat(timespec="seconds"), "stored": {"state": state}, "pid_alive": pid_alive, "heartbeat_age_s": age}


def test_truthful_within_one_heartbeat_is_read_from_the_timeline():
    base = datetime(2026, 10, 27, 10, 0, tzinfo=timezone.utc)
    rows = [_row(-60, "running", True, base), _row(30, "running", False, base), _row(90, "running", False, base)]
    assert s5.truthful_within(rows, base, 60.0, expect_terminal=True) is True, "a killed writer seen gone within a heartbeat"
    rows = [_row(-60, "running", True, base), _row(30, "running", True, base, age=20), _row(200, "running", False, base)]
    assert s5.truthful_within(rows, base, 60.0, expect_terminal=True) is False, "a killed writer still alive a heartbeat later"
    rows = [_row(-60, "running", True, base), _row(30, "running", True, base, age=20), _row(90, "running", True, base, age=20)]
    assert s5.truthful_within(rows, base, 60.0, expect_terminal=False) is True, "a living writer alive and beating"
    rows = [_row(-60, "running", True, base), _row(30, "running", True, base, age=200)]
    assert s5.truthful_within(rows, base, 60.0, expect_terminal=False) is False, "alive but silent: a stale heartbeat"
    rows = [_row(-60, "running", True, base), _row(30, "running", False, base)]
    assert s5.truthful_within(rows, base, 60.0, expect_terminal=False) is False, "stored running, nothing runs"
    rows = [_row(-60, "running", True, base), _row(40, "done", True, base)]
    assert s5.truthful_within(rows, base, 60.0, expect_terminal=False) is True
    assert s5.truthful_within([_row(-60, "running", True, base), _row(200, "failed", True, base)], base, 60.0, expect_terminal=False) is None, "no sample inside the window"


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
