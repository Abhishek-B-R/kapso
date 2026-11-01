"""The record's lifecycle (wp6-observability.md, change 6): the delivery
runs inside the orchestrator's protected region, so a watcher that sees
`done` finds the record; a delivery that raises is published as the
campaign's failure with no record and a checkpoint a resume can finish
from; a harness setup or a serving staging that raises is published the
same way. The orchestrator, the checkpoint store and the status writer
are real; the strategy's sessions are stubbed."""
import json
import shutil
from pathlib import Path

import pytest

import kapso.execution.orchestrator as orchestrator_module
import kapso.kapso as kapso_module
from kapso.execution.inbox import launch_receipt_path
from kapso.execution.observability import BuildStatus
from kapso.execution.orchestrator import OrchestratorAgent
from kapso.execution.run_checkpoint import RunCheckpointStore
from kapso.handles import Budget, Solution
from kapso.kapso import Kapso
from tests.handles_support import git_workspace
from tests.harness_support import ScoringFakeStrategy, patch_engine
from tests.test_bank_retriever import card_text
from tests.test_experience_reference import settings_for
from tests.test_update_frame import seed_bank_home

TRADING = Path(__file__).resolve().parent.parent / "examples" / "harnesses" / "trading"


def status_of(workspace: Path) -> dict:
    return json.loads((workspace / ".kapso" / "status.json").read_text())


def test_the_record_is_written_before_done_is_published(tmp_path, monkeypatch):
    patch_engine(monkeypatch)
    workspace = tmp_path / "campaign"
    git_workspace(workspace)
    seen = []
    original_done = BuildStatus.done

    def done_after_the_record(self, **fields):
        seen.append((workspace / ".kapso" / "solution.json").is_file())
        original_done(self, **fields)

    monkeypatch.setattr(BuildStatus, "done", done_after_the_record)
    solution = Kapso().build("Raise the Sharpe above 1", output=str(workspace), budget=Budget(experiments=1))
    assert seen == [True]
    assert status_of(workspace)["state"] == "done"
    assert Solution.open(str(workspace)).score == solution.score


def test_a_delivery_that_raises_is_published_with_a_checkpoint_a_resume_can_finish(tmp_path, monkeypatch):
    patch_engine(monkeypatch)
    workspace = tmp_path / "campaign"
    git_workspace(workspace)

    def broken_checkout(self):
        raise RuntimeError("the checkout failed: disk full")

    monkeypatch.setattr(ScoringFakeStrategy, "checkout_to_best_experiment_branch", broken_checkout)
    with pytest.raises(RuntimeError, match="disk full"):
        Kapso().build("Raise the Sharpe above 1", output=str(workspace), budget=Budget(experiments=1))
    status = status_of(workspace)
    assert status["state"] == "failed" and "disk full" in status["error"]
    assert not (workspace / ".kapso" / "solution.json").exists()
    # The checkpoint was not completed: a resume finishes the delivery.
    assert RunCheckpointStore(str(workspace)).load().status == "running"
    monkeypatch.setattr(ScoringFakeStrategy, "checkout_to_best_experiment_branch", lambda self: None)
    resumed = Kapso().build(output=str(workspace), resume=True)
    assert status_of(workspace)["state"] == "done"
    assert Solution.open(str(workspace)).stopped_reason == resumed.stopped_reason


def test_a_constructor_that_raises_after_the_status_is_born_is_published(tmp_path, monkeypatch):
    """The strategy's constructor makes the status file, and what raises
    after that, in its own tail or the orchestrator's setup, has no
    writer left to publish it: the facade marks the file failed (the
    pull-request review's finding)."""
    patch_engine(monkeypatch, real_strategy=True)
    workspace = tmp_path / "campaign"
    git_workspace(workspace)

    def broken_store(*args, **kwargs):
        raise RuntimeError("the history store could not open")

    monkeypatch.setattr(orchestrator_module, "ExperimentHistoryStore", broken_store)
    with pytest.raises(RuntimeError, match="could not open"):
        Kapso().build("Raise the Sharpe above 1", output=str(workspace), budget=Budget(experiments=1))
    status = status_of(workspace)
    assert status["state"] == "failed" and "could not open" in status["error"]
    # The receipt a detached launch left is gone once the status was born.
    assert not launch_receipt_path(workspace).exists()


def test_a_budget_that_fails_to_resolve_is_published(tmp_path, monkeypatch):
    """`solve()`'s protected region starts at its first statement: a
    budget that fails to resolve, before any session, is the campaign's
    failure on the status (the pull-request review's finding)."""
    patch_engine(monkeypatch)
    workspace = tmp_path / "campaign"
    git_workspace(workspace)

    def broken_resolve(*args, **kwargs):
        raise ValueError("a reserve larger than the budget")

    monkeypatch.setattr(orchestrator_module.BudgetSpec, "resolve", staticmethod(broken_resolve))
    with pytest.raises(ValueError, match="reserve larger"):
        Kapso().build("Raise the Sharpe above 1", output=str(workspace), budget=Budget(experiments=1))
    status = status_of(workspace)
    assert status["state"] == "failed" and "reserve larger" in status["error"]


def test_a_harness_setup_that_raises_is_published(tmp_path, monkeypatch):
    patch_engine(monkeypatch)
    harness_dir = tmp_path / "harness" / "trading"
    shutil.copytree(TRADING, harness_dir)
    workspace = tmp_path / "campaign"
    git_workspace(workspace)

    def broken_setup(self):
        raise RuntimeError("the market-data server never answered")

    monkeypatch.setattr(OrchestratorAgent, "_run_harness_setup", broken_setup)
    kapso = Kapso()
    kapso._harness_settings["store"] = str(tmp_path / "store")
    kapso.load_harness(str(harness_dir))
    with pytest.raises(RuntimeError, match="never answered"):
        kapso.build("Raise the Sharpe above 1", output=str(workspace), budget=Budget(experiments=1))
    status = status_of(workspace)
    assert status["state"] == "failed" and "never answered" in status["error"]
    assert status["harness"]["name"] == "trading"


def test_a_serving_staging_that_raises_is_published(tmp_path, monkeypatch):
    patch_engine(monkeypatch)
    home = seed_bank_home(tmp_path, {"a-card": card_text("a-card")})
    workspace = tmp_path / "campaign"
    git_workspace(workspace)

    def broken_staging(plan, sources):
        raise RuntimeError("the bank's clone failed")

    monkeypatch.setattr(kapso_module, "stage_serving", broken_staging)
    kapso = Kapso()
    kapso._experience_settings = {**settings_for(tmp_path), "bank_home": str(home)}
    kapso._bank_home = home
    kapso.load_experience("mine")
    with pytest.raises(RuntimeError, match="clone failed"):
        kapso.build("Raise the Sharpe above 1", output=str(workspace), budget=Budget(experiments=1))
    status = status_of(workspace)
    assert status["state"] == "failed" and "clone failed" in status["error"]
