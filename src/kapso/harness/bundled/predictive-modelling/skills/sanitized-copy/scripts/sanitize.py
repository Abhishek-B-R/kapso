"""Build the sanitized, read-only copy of a relational benchmark database for one task.

Everything a candidate must not see is physically absent from the copy, so a
process reading it, through the library or straight from the files, cannot
leak a label even by accident:

- a forecasting or recommendation task: every table truncated at the test
  cutoff (the pristine cache holds rows after it, from which future labels
  could be rebuilt); the test task table reduced to the seed time and the
  entity (the source entity for a recommendation task, whose ground-truth
  destination list is otherwise kept by the library's masking);
- an autocomplete task: the database keeps its rows after the cutoff (the
  test entities exist only there), the target column of the rows after the
  cutoff is blanked, and the columns the task removes (the ones its target
  derives from) are dropped from the stored tables;
- the training and validation task tables copied whole, labels included
  (tuning on validation is the protocol; the two-model contract governs it);
- every file a real copy (never a link into the pristine cache), no archives
  copied, the whole tree read-only, and a marker that names what was done,
  so a copy is never sanitized twice and a download in a candidate's process
  fails loudly instead of restoring pristine files.

With --rolling, one snapshot per evaluation tick (the per-row seed-time
regime): tables truncated at the tick; a training table of every window
closed by the tick, relabelled from the snapshot itself; a test table of
that tick's rows; an empty, schema-correct validation table; the rows'
positions in the official split for the grader's assembly.

    python3 sanitize.py --dataset <name> --task <name> --source <library cache> --out prepared/cache [--rolling]

Needs the relbench package (the task's own library, not a harness
requirement). Run it in a fresh interpreter: the library caches tables in
memory and a pristine table must not carry across.
"""
import argparse
import json
import os
import shutil
import stat
from pathlib import Path

import numpy as np
import pandas as pd
from relbench.base import AutoCompleteTask, RecommendationTask, Table
from relbench.datasets import dataset_registry
from relbench.tasks import task_registry

BOOLEAN_TARGET_MAP = {"t": 1, "f": 0, "true": 1, "false": 0}
MARKER = "SANITIZED.json"


def open_from(source: Path, dataset_name: str, task_name: str):
    """The dataset and the task read from `source`, whatever the library's
    own cache variable says: both registry entries' cache directories are
    replaced, the task's as well as the dataset's."""
    if dataset_name not in dataset_registry:
        raise SystemExit(f"unknown dataset {dataset_name!r}")
    if task_name not in task_registry.get(dataset_name, {}):
        raise SystemExit(f"unknown task {dataset_name}/{task_name}")
    dataset_cls, dataset_args, dataset_kwargs = dataset_registry[dataset_name]
    dataset = dataset_cls(*dataset_args, **{**dataset_kwargs, "cache_dir": str(source / dataset_name)})
    task_cls, task_args, task_kwargs = task_registry[dataset_name][task_name]
    task_cache = str(source / dataset_name / "tasks" / task_name)
    task = task_cls(dataset, *task_args, **{**task_kwargs, "cache_dir": task_cache})
    return dataset, task, task_kwargs


def coerce_boolean_target(table, target_col):
    """A text boolean target ('t'/'f') becomes 0/1 in place: the library's
    own metrics reject string labels. Unknown strings raise."""
    if target_col not in table.df.columns:
        return table
    column = table.df[target_col]
    if column.dtype != object:
        return table
    lowered = column.astype(str).str.lower()
    unknown = set(lowered.unique()) - set(BOOLEAN_TARGET_MAP)
    if unknown:
        raise ValueError(f"target column {target_col!r} holds non-boolean strings {sorted(unknown)}")
    table.df[target_col] = lowered.map(BOOLEAN_TARGET_MAP).astype(int)
    return table


def copy_database(src: Path, dst: Path) -> None:
    """A real copy of every table file: no link shares an inode with the
    pristine cache, so nothing written to the copy can reach it."""
    dst.mkdir(parents=True, exist_ok=True)
    for item in sorted(src.rglob("*")):
        target = dst / item.relative_to(src)
        if item.is_dir():
            target.mkdir(parents=True, exist_ok=True)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(item, target)


def make_read_only(root: Path) -> None:
    dir_mode = stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH
    file_mode = stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH
    for item in sorted(root.rglob("*"), reverse=True):
        os.chmod(item, dir_mode if item.is_dir() else file_mode)
    os.chmod(root, dir_mode)


def masked_test_table(task, test_table):
    if isinstance(task, RecommendationTask):
        keep = [test_table.time_col, task.src_entity_col]
        fkeys = {task.src_entity_col: task.src_entity_table}
    else:
        keep = [test_table.time_col, task.entity_col]
        fkeys = {task.entity_col: task.entity_table}
    # Row order is preserved: predictions align positionally.
    return keep, Table(df=test_table.df[keep].reset_index(drop=True), fkey_col_to_pkey_table=fkeys,
                       pkey_col=None, time_col=test_table.time_col)


def save_table(path: Path, table) -> None:
    """Write a table through the library (its schema metadata survives) over an existing file."""
    if path.exists():
        path.unlink()
    table.save(str(path))


def build_flat(dataset, task, task_kwargs, dataset_name, task_name, source: Path, out: Path):
    src_dataset_dir = source / dataset_name
    out_db = out / dataset_name / "db"
    out_task = out / dataset_name / "tasks" / task_name
    out_task.mkdir(parents=True)
    copy_database(src_dataset_dir / "db", out_db)
    report = {"tables": {}, "removed_columns": [], "blanked": None}
    if isinstance(task, AutoCompleteTask):
        entity_table, target_col = task_kwargs["entity_table"], task_kwargs["target_col"]
        removed = [(table, column) for table, column in task_kwargs.get("remove_columns", [])]
        for table_name in sorted({entity_table, *(table for table, _ in removed)}):
            table_file = out_db / f"{table_name}.parquet"
            table = Table.load(str(table_file))
            if table_name == entity_table:
                time_col = task.time_col
                if time_col is None or time_col not in table.df.columns:
                    raise SystemExit(f"autocomplete entity table {entity_table} has no usable time column")
                mask = table.df[time_col] > dataset.test_timestamp
                table.df.loc[mask, target_col] = None
                report["blanked"] = {"table": entity_table, "column": target_col, "rows": int(mask.sum())}
            for other, column in removed:
                if other == table_name:
                    if column not in table.df.columns:
                        raise SystemExit(f"{table_name}.{column} is named by the task as removed, and the table has no such column")
                    table.df.drop(columns=[column], inplace=True)
                    report["removed_columns"].append(f"{table_name}.{column}")
            save_table(table_file, table)
        for table_file in sorted(out_db.glob("*.parquet")):
            report["tables"][table_file.stem] = len(pd.read_parquet(table_file, columns=[]))
    else:
        db = dataset.get_db(upto_test_timestamp=True)
        for table_name, table in db.table_dict.items():
            table_file = out_db / f"{table_name}.parquet"
            if not table_file.exists():
                raise SystemExit(f"expected database table file missing: {table_file}")
            pristine_rows = len(pd.read_parquet(table_file, columns=[]))
            if pristine_rows != len(table.df):
                save_table(table_file, table)
            report["tables"][table_name] = {"pristine_rows": pristine_rows, "rows": len(table.df)}
    for split in ("train", "val"):
        if not (src_dataset_dir / "tasks" / task_name / f"{split}.parquet").exists():
            raise SystemExit(f"pristine task table missing: {src_dataset_dir / 'tasks' / task_name / split}.parquet")
        table = task.get_table(split, mask_input_cols=False)
        if not isinstance(task, RecommendationTask):
            table = coerce_boolean_target(table, task.target_col)
        table.save(str(out_task / f"{split}.parquet"))
    keep, masked = masked_test_table(task, task.get_table("test", mask_input_cols=False))
    masked.save(str(out_task / "test.parquet"))
    report["test_table"] = {"columns": keep, "rows": len(masked.df)}
    return report


def build_rolling(dataset, task, dataset_name, task_name, out: Path):
    if getattr(task, "num_eval_timestamps", 1) <= 1:
        raise SystemExit(f"{dataset_name}/{task_name} has one evaluation timestamp per split: not a rolling task")
    delta = task.timedelta
    time_col, entity_col = task.time_col, task.entity_col
    full = dataset.get_db(upto_test_timestamp=False)
    splits = {split: task.get_table(split, mask_input_cols=False) for split in ("train", "val", "test")}
    starts = pd.Series(pd.concat([table.df[time_col] for table in splits.values()]).unique()).sort_values(ignore_index=True)
    count = 0
    for split in ("val", "test"):
        frame = splits[split].df.reset_index(drop=True)
        for index, tick in enumerate(sorted(frame[time_col].unique())):
            tick = pd.Timestamp(tick)
            snapshot = out / f"{split}_{index:03d}_{tick.date()}"
            db_dir = snapshot / dataset_name / "db"
            task_dir = snapshot / dataset_name / "tasks" / task_name
            db_dir.mkdir(parents=True)
            task_dir.mkdir(parents=True)
            db_snapshot = full.upto(tick)
            for name, table in db_snapshot.table_dict.items():
                table.save(str(db_dir / f"{name}.parquet"))
            closed = starts[starts + delta <= tick]
            train = task.make_table(db_snapshot, pd.Series(closed.to_numpy()))
            if len(train.df) and (train.df[time_col] + delta > tick).any():
                raise SystemExit(f"an open window leaked into {snapshot.name}'s training table")
            train.save(str(task_dir / "train.parquet"))
            rows = frame[frame[time_col] == tick]
            Table(df=rows[[time_col, entity_col]].reset_index(drop=True), fkey_col_to_pkey_table={entity_col: task.entity_table},
                  pkey_col=None, time_col=time_col).save(str(task_dir / "test.parquet"))
            # An empty, schema-correct validation table: the library regenerates
            # and saves a missing split, which a read-only tree turns into a crash.
            Table(df=splits["val"].df.iloc[0:0].reset_index(drop=True), fkey_col_to_pkey_table={entity_col: task.entity_table},
                  pkey_col=None, time_col=time_col).save(str(task_dir / "val.parquet"))
            np.save(task_dir / "indices.npy", rows.index.to_numpy())
            count += 1
    return {"snapshots": count, "val_ticks": int(splits["val"].df[time_col].nunique()),
            "test_ticks": int(splits["test"].df[time_col].nunique())}


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--task", required=True)
    parser.add_argument("--source", required=True, help="the library's pristine cache directory (holds <dataset>/db)")
    parser.add_argument("--out", required=True, help="the output directory; must not exist or be empty")
    parser.add_argument("--rolling", action="store_true", help="one snapshot per evaluation tick instead of the flat copy")
    args = parser.parse_args()
    source, out = Path(args.source).resolve(), Path(args.out).resolve()
    if not (source / args.dataset / "db").is_dir():
        raise SystemExit(f"no pristine cache for {args.dataset} at {source / args.dataset / 'db'}: download the dataset and the task first")
    if (source / MARKER).is_file():
        raise SystemExit(f"{source} is itself a sanitized copy ({MARKER} present): sanitize from the pristine cache")
    for split in ("train", "val", "test"):
        if not (source / args.dataset / "tasks" / args.task / f"{split}.parquet").is_file():
            raise SystemExit(f"pristine task table missing: {source / args.dataset / 'tasks' / args.task / split}.parquet; download the task first")
    if out.exists() and any(out.iterdir()):
        raise SystemExit(f"{out} is not empty: the sanitized copy is built once; remove it deliberately to rebuild")
    if out == source or source in out.parents:
        raise SystemExit("the output directory must not be inside the pristine cache")
    out.mkdir(parents=True, exist_ok=True)
    dataset, task, task_kwargs = open_from(source, args.dataset, args.task)
    if args.rolling:
        report = build_rolling(dataset, task, args.dataset, args.task, out)
    else:
        report = build_flat(dataset, task, task_kwargs, args.dataset, args.task, source, out)
    marker = {"dataset": args.dataset, "task": args.task, "rolling": args.rolling, "source": str(source), "report": report}
    (out / MARKER).write_text(json.dumps(marker, indent=2, default=str) + "\n")
    make_read_only(out)
    print(json.dumps(marker, indent=2, default=str))
    print(f"sanitized copy ready at {out}")


if __name__ == "__main__":
    main()
