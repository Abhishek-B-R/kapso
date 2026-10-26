"""The real orchestrator over the real strategy (wp6-observability.md,
change 13): construction walks the orchestrator-to-factory seam and
writes the real status file. Without an embeddings key the history store
is recency-only and construction still succeeds; the status after
construction carries the harness and the sources from its first write; a
constructor setup that raises is published as the campaign's failure."""
import json
import shutil
from pathlib import Path

import pytest

from kapso.execution.search_strategies.generic.strategy import GenericSearch
from kapso.kapso import Kapso
from tests.handles_support import git_workspace
from tests.harness_support import real_orchestrator

TRADING = Path(__file__).resolve().parent.parent / "examples" / "harnesses" / "trading"
MINE = {"reference": "mine", "kind": "bank", "resolved": "/me/.kapso/bank.git", "head": "a" * 40,
        "provenance": "measured by you", "scope": "harness"}


def status_of(workspace: Path) -> dict:
    return json.loads((workspace / ".kapso" / "status.json").read_text())


def test_construction_without_an_embeddings_key_writes_the_status(tmp_path, monkeypatch):
    workspace = tmp_path / "campaign"
    git_workspace(workspace)
    orchestrator = real_orchestrator(monkeypatch, workspace)
    assert isinstance(orchestrator.search_strategy, GenericSearch)
    status = status_of(workspace)
    assert status["operation"] == "build" and status["state"] == "starting" and status["phase"] == "setup"
    assert status["harness"] is None and status["experience"] == []


def test_the_status_after_construction_carries_the_harness_and_the_sources(tmp_path, monkeypatch):
    harness_dir = tmp_path / "harness" / "trading"
    shutil.copytree(TRADING, harness_dir)
    kapso = Kapso()
    kapso._harness_settings["store"] = str(tmp_path / "store")
    harness = kapso.load_harness(str(harness_dir))
    workspace = tmp_path / "campaign"
    git_workspace(workspace)
    orchestrator = real_orchestrator(monkeypatch, workspace, harness=harness, experience=[MINE])
    assert orchestrator.search_strategy.harness is harness
    status = status_of(workspace)
    assert status["harness"] == harness.ref_dict() and status["experience"] == [MINE]


def test_a_constructor_setup_that_raises_publishes_failed(tmp_path, monkeypatch):
    workspace = tmp_path / "campaign"
    git_workspace(workspace)

    def broken(self, eval_dir, data_dir):
        raise RuntimeError("the evaluation directory is not readable")

    monkeypatch.setattr(GenericSearch, "_setup_kapso_directories", broken)
    with pytest.raises(RuntimeError, match="not readable"):
        real_orchestrator(monkeypatch, workspace)
    status = status_of(workspace)
    assert status["state"] == "failed" and "not readable" in status["error"]
