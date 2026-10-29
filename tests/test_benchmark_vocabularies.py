"""The abstraction scan's committed vocabularies still match their
registries: MLE's competition ids (the mlebench registry), ALE's lite
roster (the ale_bench library), RelBench's datasets (the relbench registry)
and IOAI's competition slugs (the Kaggle registry, with the account's
credentials). Each skips when its registry is absent — the gate test over
the harnesses never does (docs/plans/redesign/wp8-harness-ports.md change 16)."""

import json
import subprocess
from pathlib import Path

import pytest

from benchmarks.ale.problems import LITE_PROBLEMS
from benchmarks.harness_scan import IOAI_COMPETITIONS, MLE_COMPETITIONS
from benchmarks.relbench.task_specs import NATIVE_DATASETS, SIZE_TIER

KAGGLE_CREDENTIALS = Path.home() / ".kaggle" / "kaggle.json"


def test_mle_competition_ids_match_the_registry():
    mlebench = pytest.importorskip("mlebench.registry")
    data = json.loads(MLE_COMPETITIONS.read_text())
    assert data["all"] == sorted(mlebench.registry.list_competition_ids())
    assert data["lite"] == sorted(mlebench.registry.get_lite_competition_ids())


def test_ale_lite_problems_are_the_librarys():
    ale_bench = pytest.importorskip("ale_bench")
    assert set(LITE_PROBLEMS) <= set(ale_bench.list_problem_ids())


def test_relbench_datasets_match_the_registry():
    datasets = pytest.importorskip("relbench.datasets")
    registered = set(datasets.dataset_registry) if hasattr(datasets, "dataset_registry") else set(datasets.get_dataset_names())
    assert set(NATIVE_DATASETS) <= registered and set(SIZE_TIER) <= registered


def test_ioai_competition_slugs_resolve_on_kaggle():
    if not KAGGLE_CREDENTIALS.is_file():
        pytest.skip("no Kaggle credentials on this machine")
    data = json.loads(IOAI_COMPETITIONS.read_text())
    for slug in data["practice"] + data["mirrors"]:
        # The files listing answers for any competition that exists, joined or
        # not (an empty table before joining); a slug that is not one is a 404.
        listing = subprocess.run(["kaggle", "competitions", "files", slug], capture_output=True, text=True)
        assert listing.returncode == 0, f"{slug} is not a competition on Kaggle: {listing.stderr.strip()[-200:]}"
