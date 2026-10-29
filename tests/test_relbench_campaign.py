"""Campaign pipeline contracts: queue integrity, gating, the budget-bound
invocation and the runtime file. Hermetic — no LLMs, no downloads."""

import argparse
from pathlib import Path

import pytest
import yaml

# The relbench package is installed separately (pip install relbench); it is
# not a declared extra. Without it these skip rather than erroring at import.
pytest.importorskip("relbench")

from benchmarks.relbench.campaign import (CPU_LOCAL_QUEUE, CPU_SAFE_DATASETS,
                                          PROTOCOL_SENSITIVE_TASKS, ROI_QUEUE,
                                          ROLLING_VERIFIED, run_one, select_tasks)
from benchmarks.common import write_runtime_config
from benchmarks.relbench.runner import CONFIG_PATH


def test_queue_integrity():
    from relbench.tasks import get_task_names

    assert len(ROI_QUEUE) == 65 and len(set(ROI_QUEUE)) == 65
    assert "rel-mimic/patient-iculengthofstay" not in ROI_QUEUE
    for task_id in ROI_QUEUE:
        ds, task = task_id.split("/")
        assert task in get_task_names(ds), f"{task_id} not in relbench registry"
    assert len(CPU_LOCAL_QUEUE) == 39
    assert all(t.split("/")[0] in CPU_SAFE_DATASETS for t in CPU_LOCAL_QUEUE)


def test_selection_gates(tmp_path):
    done = "rel-event/user-attendance"
    (tmp_path / "rel-event--user-attendance").mkdir()
    (tmp_path / "rel-event--user-attendance" / "final_report.json").write_text("{}")
    queue = [done, "rel-f1/driver-position", "rel-hm/user-churn", "rel-f1/driver-dnf",
             "rel-avito/ad-ctr"]
    chosen = select_tasks(queue, "cpu", tmp_path, allow_sensitive=False, explicit=None)
    # done skipped; hm needs GPU; rolling tasks pass — their harness is verified
    assert chosen == ["rel-f1/driver-position", "rel-f1/driver-dnf", "rel-avito/ad-ctr"]
    chosen_gpu = select_tasks(queue, "gpu", tmp_path, allow_sensitive=True, explicit=None)
    assert chosen_gpu == ["rel-f1/driver-position", "rel-hm/user-churn", "rel-f1/driver-dnf",
                          "rel-avito/ad-ctr"]
    assert PROTOCOL_SENSITIVE_TASKS == {"rel-f1/driver-position", "rel-f1/driver-dnf",
                                        "rel-f1/driver-top3"}
    # an unverified rolling task would be blocked: simulate by construction
    assert ROLLING_VERIFIED <= PROTOCOL_SENSITIVE_TASKS


def test_a_campaign_task_is_budget_bound(capsys):
    """The runner is invoked with the wall-clock budget and nothing that
    could stop it early: no target, no note; the stop vote is advisory in
    the override file."""
    args = argparse.Namespace(iterations=100, hours_per_task=4.0, dry_run=True)
    verdict = run_one("rel-f1/driver-position", args)
    out = capsys.readouterr().out
    assert verdict["status"] == "dry-run"
    assert "--time-budget-hours 4.0" in out and "-i 100" in out and "budget-bound" in out
    assert "--target-val" not in out and "--knowledge-file" not in out


def test_the_runtime_file_carries_the_shared_cache_over_the_override(tmp_path):
    """The task's shared cache is a strategy parameter, so it lives in a
    file; the budget is build()'s argument and the file leaves it alone."""
    path = write_runtime_config(CONFIG_PATH, tmp_path / "shared", tmp_path)
    config = yaml.safe_load(Path(path).read_text())
    assert config["search_strategy"]["params"]["shared_cache_dir"] == str(tmp_path / "shared")
    assert config["budget"]["minutes"] == 600 and config["benchmark"]["work_root"] == "tmp/relbench"
