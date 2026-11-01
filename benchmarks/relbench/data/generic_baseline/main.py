"""Baseline candidate seeded into every RelBench campaign.

Purpose: (1) give the evaluation maintainer's registration-time calibration a
runnable candidate, (2) give the search a legitimate starting parent. Writes
shape-correct, family-appropriate trivial predictions for both splits.
Replace me with a real solution.
"""

import json
import os
import sys
from pathlib import Path

import numpy as np
from relbench.base import RecommendationTask, TaskType
from relbench.datasets import dataset_registry
from relbench.tasks import task_registry

TASK_FILE = Path("kapso_evaluation") / "task.json"


def main() -> None:
    settings = json.loads(TASK_FILE.read_text(encoding="utf-8"))
    dataset_name, task_name = settings["dataset"], settings["task"]
    # The copy this run is bound to: the evaluation sets it (a tick's
    # snapshot under the rolling regime).
    cache = Path(os.environ["RELBENCH_CACHE_DIR"])
    dataset_cls, dataset_args, dataset_kwargs = dataset_registry[dataset_name]
    dataset = dataset_cls(*dataset_args, **{**dataset_kwargs, "cache_dir": str(cache / dataset_name)})
    task_cls, task_args, task_kwargs = task_registry[dataset_name][task_name]
    task = task_cls(dataset, *task_args, **{**task_kwargs, "cache_dir": str(cache / dataset_name / "tasks" / task_name)})
    # A rolling tick's snapshot ships an EMPTY val table; the per-invocation
    # contract is test predictions for THIS tick, no val file.
    n_val = len(task.get_table("val"))
    rolling = n_val == 0
    n_test = len(task.get_table("test"))

    if isinstance(task, RecommendationTask):
        k = task.eval_k
        row = np.arange(k, dtype=np.int64)
        val_pred = np.tile(row, (n_val, 1))
        test_pred = np.tile(row, (n_test, 1))
    elif task.task_type == TaskType.BINARY_CLASSIFICATION:
        val_pred = np.full(n_val, 0.5)
        test_pred = np.full(n_test, 0.5)
    elif task.task_type == TaskType.MULTICLASS_CLASSIFICATION:
        classes = int(getattr(task, "num_classes"))
        val_pred = np.full((n_val, classes), 1.0 / classes)
        test_pred = np.full((n_test, classes), 1.0 / classes)
    else:
        train = task.get_table("train", mask_input_cols=False)
        center = float(train.df[task.target_col].median())
        val_pred = np.full(n_val, center)
        test_pred = np.full(n_test, center)

    out = os.environ["KAPSO_RUN_DATA_DIR"]
    if not rolling:
        np.save(os.path.join(out, "val_predictions.npy"), val_pred)
    np.save(os.path.join(out, "test_predictions.npy"), test_pred)
    print(
        f"[baseline] wrote trivial predictions "
        f"{'(rolling tick) ' if rolling else f'val{val_pred.shape} '}test{test_pred.shape} "
        f"(debug={'--debug' in sys.argv})"
    )


if __name__ == "__main__":
    main()
