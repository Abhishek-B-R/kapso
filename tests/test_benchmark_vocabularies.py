"""The abstraction scan's committed vocabularies still match their
registries: MLE's competition ids (the mlebench registry), ALE's reported
problems (the ale_bench library), RelBench's databases and task names (the
relbench registry, and the runner's own maps) and IOAI's competition slugs
(the Kaggle registry, with the account's credentials). Each skips when its
registry is absent — the gate test over the harnesses never does, since the
scan imports no benchmark library (docs/plans/redesign/wp8-harness-ports.md
change 16)."""

import json
import subprocess
from pathlib import Path

import pytest

from benchmarks.ale.problems import REPORTED_PROBLEMS
from benchmarks.harness_scan import IOAI_COMPETITIONS, MLE_COMPETITIONS, RELBENCH_NAMES

KAGGLE_CREDENTIALS = Path.home() / ".kaggle" / "kaggle.json"


def test_mle_competition_ids_match_the_registry():
    mlebench = pytest.importorskip("mlebench.registry")
    data = json.loads(MLE_COMPETITIONS.read_text())
    assert data["all"] == sorted(mlebench.registry.list_competition_ids())
    assert data["lite"] == sorted(mlebench.registry.get_lite_competition_ids())


def test_ale_reported_problems_are_the_librarys():
    ale_bench = pytest.importorskip("ale_bench")
    assert set(REPORTED_PROBLEMS) <= set(ale_bench.list_problem_ids())


def test_relbench_names_match_the_registry_and_the_runners_maps():
    datasets = pytest.importorskip("relbench.datasets")
    tasks = pytest.importorskip("relbench.tasks")
    task_specs = pytest.importorskip("benchmarks.relbench.task_specs")
    data = json.loads(RELBENCH_NAMES.read_text())
    assert set(data["datasets"]) <= set(datasets.get_dataset_names())
    assert set(data["datasets"]) == set(task_specs.NATIVE_DATASETS) == set(task_specs.SIZE_TIER) == set(task_specs.DATASET_NOTES)
    assert set(data["tasks"]) == {name for dataset in data["datasets"] for name in tasks.get_task_names(dataset)}
    assert {task.partition("/")[2] for task in task_specs.PRIMARY_METRIC_OVERRIDES} <= set(data["tasks"])


def test_ioai_competition_slugs_resolve_on_kaggle():
    if not KAGGLE_CREDENTIALS.is_file():
        pytest.skip("no Kaggle credentials on this machine")
    data = json.loads(IOAI_COMPETITIONS.read_text())
    for slug in data["practice"] + data["mirrors"]:
        # The files listing answers for any competition that exists, joined or
        # not (an empty table before joining); a slug that is not one is a 404.
        listing = subprocess.run(["kaggle", "competitions", "files", slug], capture_output=True, text=True)
        assert listing.returncode == 0, f"{slug} is not a competition on Kaggle: {listing.stderr.strip()[-200:]}"
