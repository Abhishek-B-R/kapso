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


def watch(path, follow=False):
    return cmd_watch(SimpleNamespace(path=str(path), json=False, follow=follow))


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
