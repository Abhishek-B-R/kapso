"""`kapso watch` completed (wp6-observability.md, change 7): the header
names the harness and the sources from the status file's own fields; a
detached launch leaves a receipt beside the log, and a campaign with no
status yet is told apart by it, starting with a live pid or stopped
with the pid gone and the log named; the campaign tree is retired."""
import inspect
import json
import os
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from kapso.execution.inbox import launch_receipt_path, read_launch_receipt
import kapso.cli.watch as watch_module
from kapso.cli.watch import cmd_watch
from kapso.execution.observability import BuildStatus, OperationStatusView, source_line

HARNESS = {"name": "trading", "version": "0.1.0", "hash": "83b6c0b60d6a" + "0" * 52, "source": "/h/trading"}
MINE = {"reference": "mine", "kind": "bank", "resolved": "/me/.kapso/bank.git", "head": "a9ddad3d302d" + "0" * 28,
        "provenance": "measured by you", "scope": "harness"}
HOSTED = {"reference": "leeroopedia", "kind": "hosted", "resolved": "https://x/mcp?token={K}", "head": None,
          "provenance": "reported by others", "scope": "all"}


def test_the_header_names_the_harness_and_the_sources(tmp_path):
    status = BuildStatus(tmp_path / "status.json", heartbeat_seconds=60, harness=HARNESS, experience=[MINE, HOSTED])
    status.phase("ideation")
    screen = OperationStatusView(tmp_path / "status.json").explain()
    lines = [line.strip("│ ") for line in screen.splitlines()]
    assert "harness: trading 0.1.0 (83b6c0b60d6a)" in lines
    assert "served: mine at a9ddad3d302d, measured by you" in lines
    assert "served: leeroopedia (hosted), reported by others" in lines
    [phase_line] = [line for line in lines if line.startswith("phase: ideation")]
    assert lines.index("harness: trading 0.1.0 (83b6c0b60d6a)") < lines.index(phase_line)
    # Without a harness or sources the header is as it was.
    bare = BuildStatus(tmp_path / "bare.json", heartbeat_seconds=60)
    assert "harness:" not in OperationStatusView(tmp_path / "bare.json").explain()
    assert "served:" not in OperationStatusView(tmp_path / "bare.json").explain()
    # The campaign tree is the trace's now.
    assert "tree" not in inspect.signature(OperationStatusView.explain).parameters
    assert not hasattr(OperationStatusView, "campaign_tree")


def test_a_source_line_per_kind():
    assert source_line({**MINE, "scope": "all"}) == "mine at a9ddad3d302d, measured by you, every scope"
    index = {"reference": "org-x", "kind": "index", "resolved": "/i/org-x", "head": "7c2d9e1f0000",
             "provenance": "reported by others", "scope": "all"}
    assert source_line(index) == "org-x (index 7c2d9e1f0000), reported by others"


def watch(path, follow=False, as_json=False):
    return cmd_watch(SimpleNamespace(path=str(path), json=as_json, follow=follow))


def test_the_receipt_tells_starting_from_stopped(tmp_path, capsys):
    campaign = tmp_path / "campaign"
    campaign.mkdir()
    assert read_launch_receipt(campaign) is None
    with pytest.raises(SystemExit):
        watch(campaign)
    assert "no status yet" in capsys.readouterr().out

    receipt = launch_receipt_path(campaign)
    assert receipt == tmp_path / "campaign.launch.json"
    log = tmp_path / "campaign.log"
    receipt.write_text(json.dumps({"pid": os.getpid(), "log": str(log), "argv": ["build"],
                                   "started_at": "2026-10-25T18:00:00+00:00"}))
    with pytest.raises(SystemExit):
        watch(campaign)
    out = capsys.readouterr().out
    assert out.startswith(f"starting (pid {os.getpid()}, launched ") and str(log) in out

    gone = subprocess.Popen([sys.executable, "-c", "pass"])
    gone.wait()
    receipt.write_text(json.dumps({"pid": gone.pid, "log": str(log), "argv": ["build"],
                                   "started_at": "2026-10-25T18:00:00+00:00"}))
    with pytest.raises(SystemExit) as stopped:
        watch(campaign, follow=True)   # nothing to wait for
    assert stopped.value.code == 1
    assert capsys.readouterr().out.strip() == f"stopped before writing a status; the log says why: {log}"

    receipt.write_text("{}")
    with pytest.raises(ValueError, match="a launch receipt carries a pid and a log"):
        read_launch_receipt(campaign)


def test_the_launch_state_is_json_too_and_follow_ends_when_the_child_dies(tmp_path, capsys, monkeypatch):
    """Before a status, `--json` prints the launch state as data (a plugin
    reads it); `--follow` on a starting child re-reads the receipt while
    it waits, so a child that dies at a launch check ends the wait with
    the stopped line and exit 1 (the pull-request review's findings)."""
    campaign = tmp_path / "campaign"
    log = tmp_path / "campaign.log"
    receipt = launch_receipt_path(campaign)
    receipt.write_text(json.dumps({"pid": os.getpid(), "log": str(log), "argv": ["build"],
                                   "started_at": "2026-10-25T22:07:49+00:00"}))
    with pytest.raises(SystemExit):
        watch(campaign, as_json=True)
    state = json.loads(capsys.readouterr().out)
    assert state["state"] == "starting" and state["pid"] == os.getpid() and state["log"] == str(log)
    with pytest.raises(SystemExit):
        watch(tmp_path / "nowhere", as_json=True)
    assert json.loads(capsys.readouterr().out)["state"] == "no_status"

    gone = subprocess.Popen([sys.executable, "-c", "pass"])
    gone.wait()
    polls = []

    def sleep(seconds):
        # The child dies while the watcher waits: the receipt now names a
        # pid that is gone.
        polls.append(seconds)
        receipt.write_text(json.dumps({"pid": gone.pid, "log": str(log), "argv": ["build"],
                                       "started_at": "2026-10-25T22:07:49+00:00"}))

    monkeypatch.setattr(watch_module.time, "sleep", sleep)
    with pytest.raises(SystemExit) as stopped:
        watch(campaign, follow=True)
    assert stopped.value.code == 1 and len(polls) == 1
    out = capsys.readouterr().out
    assert out.startswith(f"starting (pid {os.getpid()}") and out.strip().endswith(f"stopped before writing a status; the log says why: {log}")


def test_a_receipt_newer_than_the_status_is_a_resume_that_started_or_died(tmp_path, capsys):
    """A detached resume writes a receipt beside a campaign that has a
    status from its earlier run: a live pid is reported above the earlier
    screen, a dead one as stopped, instead of the stale `DONE`."""
    campaign = tmp_path / "campaign"
    (campaign / ".kapso").mkdir(parents=True)
    status = BuildStatus(campaign / ".kapso" / "status.json", heartbeat_seconds=60)
    status.done(stopped_reason="max_iterations")
    receipt = launch_receipt_path(campaign)
    later = "2099-01-01T00:00:00+00:00"
    receipt.write_text(json.dumps({"pid": os.getpid(), "log": str(tmp_path / "campaign.log"), "argv": ["build", "--resume"],
                                   "started_at": later}))
    watch(campaign)
    out = capsys.readouterr().out
    assert out.startswith(f"starting again (pid {os.getpid()}") and "DONE" in out
    gone = subprocess.Popen([sys.executable, "-c", "pass"])
    gone.wait()
    receipt.write_text(json.dumps({"pid": gone.pid, "log": str(tmp_path / "campaign.log"), "argv": ["build", "--resume"],
                                   "started_at": later}))
    with pytest.raises(SystemExit) as stopped:
        watch(campaign)
    assert stopped.value.code == 1
    assert capsys.readouterr().out.strip() == f"stopped before writing a status; the log says why: {tmp_path / 'campaign.log'}"


def test_the_receipt_is_read_before_the_directory_exists(tmp_path, capsys):
    """A launch that dies at a launch check (a refused evaluation suite,
    a failed preflight) never creates the campaign directory; the receipt
    beside its log still tells what happened (the WP6 proof run's first
    launch was told `no status yet`)."""
    campaign = tmp_path / "campaign"
    log = tmp_path / "campaign.log"
    gone = subprocess.Popen([sys.executable, "-c", "pass"])
    gone.wait()
    launch_receipt_path(campaign).write_text(json.dumps({"pid": gone.pid, "log": str(log), "argv": ["build"],
                                                         "started_at": "2026-10-25T22:07:49+00:00"}))
    with pytest.raises(SystemExit) as stopped:
        watch(campaign)
    assert stopped.value.code == 1
    assert capsys.readouterr().out.strip() == f"stopped before writing a status; the log says why: {log}"
