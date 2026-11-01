"""Kapso RelBench starter-kit helpers.

Import these from your main.py to load the task from the sanitized copy the
evaluation binds your run to, and to save predictions exactly per the
evaluation contract.

Typical skeleton:

    from kapso_datasets.common import load_task, save_predictions, is_debug, shared_cache_dir

    ctx = load_task()                     # -> TaskContext
    train, val, test = ctx.train, ctx.val, ctx.test
    db = ctx.db
    ...train on train (labels), select on val (labels), predict val+test...
    save_predictions(val_pred, test_pred)
"""

from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
from relbench.datasets import dataset_registry
from relbench.tasks import task_registry

TASK_FILE = Path("kapso_evaluation") / "task.json"


def task_settings() -> dict:
    """The task's identity, from the evaluation's `task.json` at the
    repository root (the directory your program runs from)."""
    return json.loads(TASK_FILE.read_text(encoding="utf-8"))


def is_debug() -> bool:
    return "--debug" in sys.argv


def run_data_dir() -> Path:
    """Where this run's prediction files go; the evaluation sets the variable
    for every run (export it yourself for a run by hand)."""
    d = Path(os.environ["KAPSO_RUN_DATA_DIR"])
    d.mkdir(parents=True, exist_ok=True)
    return d


def shared_cache_dir() -> Path:
    """The shared artifact directory, persistent across experiments."""
    d = Path(os.environ["KAPSO_SHARED_CACHE_DIR"])
    d.mkdir(parents=True, exist_ok=True)
    return d


@dataclass
class TaskContext:
    dataset_name: str
    task_name: str
    dataset: Any
    task: Any
    db: Any
    train: Any  # relbench Table (labels included)
    val: Any    # relbench Table (labels included; selection, and the test-predicting model only)
    test: Any   # relbench Table (seed ids + timestamps only)

    @property
    def target_col(self) -> str:
        return self.task.target_col


def open_task(dataset_name: str, task_name: str, cache: Path):
    """The dataset and the task bound to the copy at `cache` through the
    registries, both cache directories explicit: never a download."""
    dataset_cls, dataset_args, dataset_kwargs = dataset_registry[dataset_name]
    dataset = dataset_cls(*dataset_args, **{**dataset_kwargs, "cache_dir": str(cache / dataset_name)})
    task_cls, task_args, task_kwargs = task_registry[dataset_name][task_name]
    task = task_cls(dataset, *task_args, **{**task_kwargs, "cache_dir": str(cache / dataset_name / "tasks" / task_name)})
    return dataset, task


def load_task(upto_test_timestamp: bool = True) -> TaskContext:
    """Load the dataset and the task from the copy this run is bound to:
    `RELBENCH_CACHE_DIR`, set by the evaluation for every run (under the
    rolling regime, that tick's snapshot).

    For an autocomplete task pass upto_test_timestamp=False to see the
    post-cutoff entity rows as inputs (their targets are blanked); under the
    rolling regime pass False as well: the snapshot is already the tick's view.
    """
    settings = task_settings()
    dataset, task = open_task(settings["dataset"], settings["task"], Path(os.environ["RELBENCH_CACHE_DIR"]))
    db = dataset.get_db(upto_test_timestamp=upto_test_timestamp)
    return TaskContext(
        dataset_name=settings["dataset"],
        task_name=settings["task"],
        dataset=dataset,
        task=task,
        db=db,
        train=task.get_table("train"),
        val=task.get_table("val"),
        test=task.get_table("test"),
    )


def save_predictions(val_pred: np.ndarray, test_pred: np.ndarray) -> None:
    """Write both prediction files. Call this in EVERY run mode, debug included."""
    out = run_data_dir()
    np.save(out / "val_predictions.npy", np.asarray(val_pred))
    np.save(out / "test_predictions.npy", np.asarray(test_pred))
    print(
        f"[starter_kit] saved predictions: val{np.asarray(val_pred).shape} "
        f"test{np.asarray(test_pred).shape} -> {out}"
    )


def assert_temporal_safety(df, time_col: str, seed_time) -> None:
    """Guard: every row used for features must satisfy time <= seed_time."""
    bad = (df[time_col] > seed_time).sum()
    if bad:
        raise RuntimeError(
            f"TEMPORAL LEAK: {bad} rows have {time_col} after the seed time {seed_time}"
        )


def eval_map_at_k(pred: np.ndarray, true_lists, k: int) -> float:
    """Fast MAP@K identical to relbench.metrics.link_prediction_map."""
    maps = []
    for row_pred, true in zip(pred, true_lists):
        true = set(true)
        if not true:
            continue
        hits = np.array([1 if p in true else 0 for p in row_pred[:k]])
        if hits.sum() == 0:
            maps.append(0.0)
            continue
        precision_at = np.cumsum(hits) / (np.arange(k) + 1)
        maps.append(float((precision_at * hits).sum() / min(len(true), k)))
    return float(np.mean(maps)) if maps else 0.0
