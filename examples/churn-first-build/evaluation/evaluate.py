"""The evaluation Kapso protects for the churn fixture.

    python kapso_evaluation/evaluate.py [--fast] [--timeout SECONDS]

Run from the workspace root. It runs the repository's prediction contract,
`python predict.py --data kapso_datasets --out predictions.csv`, validates
the file, scores it with ROC AUC against the labels under the private
directory named in `private_dir.txt` beside this script, writes
`result.json` beside this script in the shape the engine reads, and prints
the metric as the last line:

    auc: 0.8412

Higher is better. Exit codes: 0 scored; 2 the predictions are missing or
malformed (the reason is printed); 3 `predict.py` failed (its last lines
are printed). A timeout raises. `--fast` scores the first 600 holdout rows
only: a smoke check whose number is not comparable with a full score.
"""

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

ID = "id"
PREDICTION = "churn_probability"
LABEL = "churned"
FAST_ROWS = 600
PREDICT_COMMAND = [sys.executable, "predict.py", "--data", "kapso_datasets", "--out", "predictions.csv"]


def fail(code: int, reason: str) -> None:
    print(f"evaluation failed: {reason}")
    sys.exit(code)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--workspace", default=".", help="the workspace root; predict.py and kapso_datasets/ live there")
    parser.add_argument("--fast", action="store_true", help=f"score the first {FAST_ROWS} holdout rows only")
    parser.add_argument("--timeout", type=float, default=600.0, help="seconds predict.py may take")
    args = parser.parse_args()

    workspace = Path(args.workspace).resolve()
    here = Path(__file__).resolve().parent
    private_dir = Path((here / "private_dir.txt").read_text(encoding="utf-8").strip())
    labels = pd.read_csv(private_dir / "holdout_labels.csv")
    if args.fast:
        labels = labels.iloc[:FAST_ROWS]

    predictions_path = workspace / "predictions.csv"
    if predictions_path.exists():
        predictions_path.unlink()   # never score a stale file

    started = time.monotonic()
    run = subprocess.run(PREDICT_COMMAND, cwd=workspace, capture_output=True, text=True, timeout=args.timeout)
    if run.returncode != 0:
        print("\n".join((run.stdout + run.stderr).splitlines()[-20:]))
        fail(3, f"predict.py exited {run.returncode}")
    if not predictions_path.is_file():
        fail(2, "predict.py wrote no predictions.csv")

    predictions = pd.read_csv(predictions_path)
    if list(predictions.columns) != [ID, PREDICTION]:
        fail(2, f"predictions.csv columns are {list(predictions.columns)}, expected [{ID}, {PREDICTION}]")
    if predictions[ID].duplicated().any():
        fail(2, "predictions.csv repeats an id")
    values = predictions[PREDICTION].to_numpy(dtype=float)
    if not np.isfinite(values).all() or (values < 0).any() or (values > 1).any():
        fail(2, "churn_probability must be a finite number in [0, 1] on every row")
    merged = labels.merge(predictions, on=ID, how="left")
    if merged[PREDICTION].isna().any():
        fail(2, f"{int(merged[PREDICTION].isna().sum())} holdout ids have no prediction")

    auc = float(roc_auc_score(merged[LABEL].astype(int), merged[PREDICTION]))
    seconds = time.monotonic() - started
    summary = f"auc: {auc:.4f} (rows={len(merged)}, fast={args.fast}, seconds={seconds:.1f})"
    result = {
        "evaluation_script_path": "kapso_evaluation/evaluate.py",
        "evaluation_output": summary,
        "score": round(auc, 4),
    }
    (here / "result.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(f"rows: {len(merged)}  seconds: {seconds:.1f}  fast: {args.fast}")
    print(f"auc: {auc:.4f}")


if __name__ == "__main__":
    main()
