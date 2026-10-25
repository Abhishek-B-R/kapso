"""A build with a harness writes one identity into the launch record, the
status file, the checkpoint and the solution record; a resume after one
byte of a page changed is refused by name with the way out; the same
content from another path proceeds; a bare resume takes the harness from
the launch record. The orchestrator, the checkpoint store and the status
writer are real; only the strategy's sessions are stubbed."""

import json
import shutil
from pathlib import Path
from typing import Any, Dict, Optional

import pytest

from kapso.execution.run_checkpoint import RunCheckpointIncompatibleError
from kapso.handles import Budget, Solution
from kapso.kapso import Kapso
from tests.handles_support import git_workspace
from tests.harness_support import patch_engine

TRADING = Path(__file__).resolve().parent.parent / "examples" / "harnesses" / "trading"


@pytest.fixture
def engine(monkeypatch, tmp_path):
    """The patched engine, a workspace, and the trading harness copied where
    a test can edit it."""
    strategies = patch_engine(monkeypatch)
    harness_dir = tmp_path / "harness" / "trading"
    shutil.copytree(TRADING, harness_dir)
    workspace = tmp_path / "campaign"
    git_workspace(workspace)
    return workspace, harness_dir, strategies


def kapso_with(harness_dir: Optional[Path], tmp_path: Path) -> Kapso:
    kapso = Kapso()
    kapso._harness_settings["store"] = str(tmp_path / "store")
    if harness_dir is not None:
        kapso.load_harness(str(harness_dir))
    return kapso


def records(workspace: Path) -> Dict[str, Any]:
    return {
        name: json.loads((workspace / ".kapso" / f"{name}.json").read_text())
        for name in ("launch", "status", "run_state", "solution")
    }


def test_one_identity_reaches_every_record(engine, tmp_path):
    workspace, harness_dir, strategies = engine
    kapso = kapso_with(harness_dir, tmp_path)
    solution = kapso.build("Raise the Sharpe above 1", output=str(workspace), budget=Budget(experiments=1))

    identity = kapso.harness.ref_dict()
    assert identity["name"] == "trading" and identity["source"] == str(harness_dir.resolve())
    assert len(identity["hash"]) == 64
    written = records(workspace)
    assert written["launch"]["harness"] == identity
    assert written["status"]["harness"] == identity
    assert written["run_state"]["harness"] == identity
    assert written["solution"]["harness"] == identity
    assert solution.harness.hash == identity["hash"]
    assert Solution.open(workspace).harness == solution.harness
    # The strategy was handed the same handle the facade loaded.
    assert strategies[0].harness is kapso.harness


def test_a_resume_after_an_edit_is_refused_by_name_with_the_way_out(engine, tmp_path):
    workspace, harness_dir, _ = engine
    first = kapso_with(harness_dir, tmp_path)
    first.build("g", output=str(workspace), budget=Budget(experiments=1))
    recorded = first.harness

    page = harness_dir / "instructions" / "guardrails.md"
    page.write_text(page.read_text() + "\n- one more rule\n")
    second = kapso_with(harness_dir, tmp_path)
    assert second.harness.hash != recorded.hash
    with pytest.raises(RunCheckpointIncompatibleError) as caught:
        second.build(output=str(workspace), resume=True)
    message = str(caught.value)
    assert "the harness changed since launch" in message
    assert recorded.label() in message and second.harness.label() in message
    assert f"`git checkout` in {harness_dir.resolve()}" in message
    assert "start a new campaign with a new --output" in message

    # The same object, which still holds the handle of the launch: the
    # directory is read again at the call, so the edit is seen too.
    with pytest.raises(RunCheckpointIncompatibleError, match="the harness changed since launch"):
        first.build(output=str(workspace), resume=True)
    assert first.harness.hash == second.harness.hash


def test_the_same_content_from_another_path_resumes(engine, tmp_path):
    workspace, harness_dir, strategies = engine
    kapso_with(harness_dir, tmp_path).build("g", output=str(workspace), budget=Budget(experiments=1))
    elsewhere = tmp_path / "elsewhere" / "trading"
    shutil.copytree(harness_dir, elsewhere)
    solution = kapso_with(elsewhere, tmp_path).build(output=str(workspace), resume=True, budget=Budget(experiments=1))
    assert solution.experiments_total == 2
    # The launch record keeps the original source; the solution names the one used.
    assert records(workspace)["launch"]["harness"]["source"] == str(harness_dir.resolve())
    assert solution.harness.source == str(elsewhere.resolve())


def test_a_bare_resume_takes_the_harness_from_the_launch_record(engine, tmp_path):
    workspace, harness_dir, strategies = engine
    kapso_with(harness_dir, tmp_path).build("g", output=str(workspace), budget=Budget(experiments=1))
    solution = kapso_with(None, tmp_path).build(output=str(workspace), resume=True, budget=Budget(experiments=1))
    assert solution.harness.source == str(harness_dir.resolve())
    assert strategies[-1].harness is not None and strategies[-1].harness.name == "trading"


def test_a_resume_cannot_add_or_drop_a_harness(engine, tmp_path):
    workspace, harness_dir, _ = engine
    kapso_with(None, tmp_path).build("g", output=str(workspace), budget=Budget(experiments=1))
    assert records(workspace)["launch"]["harness"] is None
    with pytest.raises(RunCheckpointIncompatibleError, match="launched without a harness; a resume cannot add"):
        kapso_with(harness_dir, tmp_path).build(output=str(workspace), resume=True)


def test_a_build_without_a_harness_records_none_everywhere(engine, tmp_path):
    workspace, _, strategies = engine
    solution = kapso_with(None, tmp_path).build("g", output=str(workspace), budget=Budget(experiments=1))
    written = records(workspace)
    assert written["launch"]["harness"] is None and written["status"]["harness"] is None
    assert written["run_state"]["harness"] is None and written["solution"]["harness"] is None
    assert solution.harness is None and strategies[0].harness is None
