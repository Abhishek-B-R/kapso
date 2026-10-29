"""RelBench provided grader — the immutable scoring logic for generic search.

Runs the candidate's `main.py` as an isolated child subprocess, scores the
resulting validation predictions with the OFFICIAL relbench metrics against
the sanitized copy (test labels are physically absent from it), archives
full-fidelity runs for final selection, and prints the machine-readable
manifest line the search parses as the score of record.

Self-contained by design: imports only stdlib + numpy + relbench + the
vendored archive contract (kapso_eval_archive.py, byte-identical to the
framework master), never candidate modules — candidate code runs in the child
process only.

CLI (the registered entrypoint delegates here verbatim):
    python kapso_evaluation/grader.py --fidelity fast|full [--fraction F] [--seed S]
    python kapso_evaluation/grader.py --rescore RUN_DIR
    python kapso_evaluation/grader.py --void RUN --reason "..."

`--rescore` recomputes an archived run's score of record from its STORED
predictions — no candidate code executes — and prints the manifest line.
Final selection ranks head-stamped finals exclusively through this mode.

Fidelity semantics for THIS suite (see README.md): the evaluation cost lives
in the candidate's training build, not in scoring items. `fast` runs
`main.py --debug` (the contract's cheap-build mode); `full` runs `main.py`.
Both score the complete official validation split; the item set never
shrinks. `fraction`/`seed` are echoed into the manifest for grant validation.

Configuration: `task.json` beside this file, written by the runner that
stages the evaluation directory (the directory is integrity-protected, so
the task's identity travels with the grader):
    dataset, task            the task's identity in the library's registry
    primary_metric           e.g. "mae", "link_prediction_map"
    higher_is_better         the metric's direction
    work_dir                 the archive root (runs/run_NNNN/ under it)
    full_timeout, debug_timeout   the candidate's caps, seconds
    cache_dir                the sanitized copy the candidate's process reads
    rolling_root             the per-tick snapshots, or null under the flat regime

The engine optimises one score, higher is better: the manifest's `score` is
the metric oriented that way (negated when lower is better) and
`raw_score` is the metric itself, with `higher_is_better` beside it.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import numpy as np
from relbench.base import RecommendationTask, TaskType
from relbench.datasets import dataset_registry
from relbench.tasks import task_registry

# Sibling import of the vendored archive contract: this file runs as a script
# (sys.path[0] is the suite dir) but is also loaded by tests via importlib
# from an arbitrary cwd — anchor the suite dir explicitly either way.
_SUITE_DIR = str(Path(__file__).resolve().parent)
if _SUITE_DIR not in sys.path:
    sys.path.insert(0, _SUITE_DIR)
import kapso_eval_archive as archive_contract

MANIFEST_MARKER = "KAPSO_EVAL_MANIFEST"
TASK_FILE = "task.json"
POLL_SECONDS = 1.0


def task_settings() -> dict:
    """The task's settings from `task.json` beside this file; a missing file is a staging error."""
    path = Path(__file__).resolve().parent / TASK_FILE
    if not path.is_file():
        print(f"[grader] missing {path}: the runner stages the evaluation directory with the task's settings")
        sys.exit(2)
    return json.loads(path.read_text(encoding="utf-8"))


def open_task(settings: dict):
    """The task read from the sanitized copy the settings name, with both the
    dataset's and the task's cache directories bound to it: the library's own
    cache variable plays no part in scoring."""
    dataset_name, task_name = settings["dataset"], settings["task"]
    cache = Path(settings["cache_dir"])
    dataset_cls, dataset_args, dataset_kwargs = dataset_registry[dataset_name]
    dataset = dataset_cls(*dataset_args, **{**dataset_kwargs, "cache_dir": str(cache / dataset_name)})
    task_cls, task_args, task_kwargs = task_registry[dataset_name][task_name]
    return task_cls(dataset, *task_args, **{**task_kwargs, "cache_dir": str(cache / dataset_name / "tasks" / task_name)})


def oriented(score: float, higher_is_better: bool) -> float:
    return score if higher_is_better else -score


def _repo_root() -> Path:
    """The candidate repo root: the parent of this suite's directory."""
    return Path(__file__).resolve().parent.parent


def _session_id() -> str:
    """Identity of the session invoking this grader.

    Sessions run in per-session git worktrees laid out as
    .../sessions/<session_name>/; outside that layout (baseline runs,
    calibration) the repo-root directory name is the identity. Recorded in
    every manifest and archive label so run provenance is exact, not
    forensic.
    """
    parts = _repo_root().parts
    if "sessions" in parts:
        idx = parts.index("sessions")
        if idx + 1 < len(parts):
            return parts[idx + 1]
    return _repo_root().name


def _run_child(cmd: list, cwd: Path, env: dict, deadline: float) -> None:
    """Run the candidate to completion or the deadline, streaming its output.

    The child writes to a log file and the loop prints what arrived while it
    polls, so a bounded wait needs no exception: at the deadline the whole
    process group is killed and the grader exits with the time-limit code."""
    with tempfile.TemporaryFile(mode="w+", encoding="utf-8", errors="replace") as log:
        proc = subprocess.Popen(cmd, cwd=cwd, env=env, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        printed = 0
        while True:
            log.flush()
            log.seek(printed)
            chunk = log.read()
            if chunk:
                print(chunk, end="")
                printed += len(chunk)
            if proc.poll() is not None:
                break
            if time.time() > deadline:
                os.killpg(os.getpgid(proc.pid), 9)
                proc.wait()
                print("[grader] candidate exceeded its time limit and was killed")
                sys.exit(4)
            time.sleep(POLL_SECONDS)
    if proc.returncode != 0:
        print(f"[grader] candidate exited non-zero ({proc.returncode})")
        sys.exit(5)


def _candidate_command(fidelity: str) -> list:
    root = _repo_root()
    if not (root / "main.py").exists():
        print("[grader] main.py not found at repo root — the solution must be main.py")
        sys.exit(3)
    return [sys.executable, "main.py"] + (["--debug"] if fidelity == "fast" else [])


def _timeout(settings: dict, fidelity: str) -> int:
    return int(settings["debug_timeout"] if fidelity == "fast" else settings["full_timeout"])


def run_candidate(settings: dict, fidelity: str, run_data_dir: Path) -> None:
    cmd = _candidate_command(fidelity)
    timeout = _timeout(settings, fidelity)
    env = os.environ.copy()
    env["RELBENCH_CACHE_DIR"] = settings["cache_dir"]
    env["KAPSO_RUN_DATA_DIR"] = str(run_data_dir)
    env["PYTHONUNBUFFERED"] = "1"
    print(f"[grader] running candidate: {' '.join(cmd)} (timeout {timeout}s)")
    _run_child(cmd, _repo_root(), env, time.time() + timeout)


def run_candidate_rolling(settings: dict, fidelity: str, run_data_dir: Path, rolling_root: Path) -> None:
    """Rolling harness (EVALUATION_PROTOCOL.md): one candidate invocation per
    tick, each seeing ONLY that tick's snapshot cache; predictions assembled
    into the official row order. Downstream scoring/archiving is unchanged."""
    root = _repo_root()
    cmd = _candidate_command(fidelity)
    deadline = time.time() + _timeout(settings, fidelity)

    vectors = {}
    for split, out_name in (("val", "val_predictions.npy"), ("test", "test_predictions.npy")):
        snaps = sorted(rolling_root.glob(f"{split}_*"))
        if not snaps:
            print(f"[grader] rolling root has no {split} snapshots: {rolling_root}")
            sys.exit(2)
        parts, indices = [], []
        for snap in snaps:
            stage = Path(tempfile.mkdtemp(prefix=f"relbench_tick_{snap.name}_"))
            shutil.copytree(snap, stage / "cache", copy_function=os.link)
            tick_out = stage / "out"
            tick_out.mkdir()
            env = os.environ.copy()
            env["RELBENCH_CACHE_DIR"] = str(stage / "cache")
            env["KAPSO_RUN_DATA_DIR"] = str(tick_out)
            env["PYTHONUNBUFFERED"] = "1"
            print(f"[grader] rolling tick {snap.name} "
                  f"({int(deadline - time.time())}s left)")
            _run_child(cmd, root, env, deadline)
            task_dirs = list((stage / "cache").glob("*/tasks/*"))
            idx = np.load(task_dirs[0] / "indices.npy")
            pred_path = tick_out / "test_predictions.npy"
            if not pred_path.exists():
                print(f"[grader] contract violation: tick {snap.name} wrote no test_predictions.npy")
                sys.exit(6)
            pred = np.asarray(np.load(pred_path, allow_pickle=False), dtype=np.float64)
            if pred.ndim == 2 and pred.shape[1] == 1:
                pred = pred[:, 0]
            if len(pred) != len(idx):
                print(f"[grader] contract violation: tick {snap.name} predictions "
                      f"{len(pred)} != {len(idx)} rows")
                sys.exit(6)
            parts.append(pred)
            indices.append(idx)
            shutil.rmtree(stage, ignore_errors=True)
        flat_idx = np.concatenate(indices)
        vector = np.zeros(int(flat_idx.max()) + 1, dtype=np.float64)
        vector[flat_idx] = np.concatenate(parts)
        np.save(run_data_dir / out_name, vector)
        vectors[split] = len(flat_idx)
    print(f"[grader] rolling assembly complete: val={vectors['val']} test={vectors['test']} rows")


def load_and_score(settings: dict, run_data_dir: Path):
    primary = settings["primary_metric"]
    task = open_task(settings)
    val_table = task.get_table("val", mask_input_cols=False)
    n_val = len(val_table)
    n_test = len(task.get_table("test"))

    val_path = run_data_dir / "val_predictions.npy"
    test_path = run_data_dir / "test_predictions.npy"
    for p, n in ((val_path, n_val), (test_path, n_test)):
        if not p.exists():
            print(f"[grader] contract violation: {p.name} was not written")
            sys.exit(6)

    val_pred = np.load(val_path, allow_pickle=False)
    test_pred = np.load(test_path, allow_pickle=False)

    if isinstance(task, RecommendationTask):
        expected = (n_val, task.eval_k)
        if val_pred.shape != expected or not np.issubdtype(val_pred.dtype, np.integer):
            print(f"[grader] contract violation: val predictions must be int {expected}, got {val_pred.shape} {val_pred.dtype}")
            sys.exit(6)
    else:
        val_arr = np.asarray(val_pred, dtype=np.float64)
        if val_arr.ndim == 2 and val_arr.shape[1] == 1 and task.task_type != TaskType.MULTICLASS_CLASSIFICATION:
            val_pred = val_arr[:, 0]
        if len(val_pred) != n_val or not np.all(np.isfinite(np.asarray(val_pred, dtype=np.float64))):
            print(f"[grader] contract violation: val predictions wrong length or non-finite")
            sys.exit(6)

    val_metrics = {k: float(v) for k, v in task.evaluate(val_pred, val_table).items()}
    if primary not in val_metrics:
        print(f"[grader] primary metric {primary} missing from {sorted(val_metrics)}")
        sys.exit(7)
    return val_metrics, val_pred, test_pred, n_val


def archive_full_run(settings: dict, run_data_dir: Path, val_metrics: dict, evaluator_id: str) -> str:
    """Persist a full-fidelity run for final selection. Fast runs are never
    archived: their debug-mode predictions are pipeline checks, not results.

    Every archive is stamped with the evaluator that produced it and the
    evaluator tree is snapshotted once per version — final selection pools
    head-stamped finals only and rescored them through the snapshot, so runs
    measured under a superseded evaluator never compete with head runs.
    """
    work_dir = Path(settings["work_dir"])
    run_dir = archive_contract.allocate_run_dir(work_dir / "runs")
    for name in ("val_predictions.npy", "test_predictions.npy"):
        shutil.copy2(run_data_dir / name, run_dir / name)
    (run_dir / "private" / "metrics.json").write_text(
        json.dumps({"val": val_metrics, "test": {}}, indent=2)
    )
    # Selection eligibility label. Every archive starts "pending"; the search
    # stamps exactly one run per session "final" (its registered result) and
    # the rest "superseded"; candidates may stamp "self-voided" via --void.
    # Final selection picks ONLY among "final" runs stamped with the head
    # evaluator.
    archive_contract.write_selection_label(
        run_dir, session=_session_id(), evaluator_id=evaluator_id
    )
    archive_contract.snapshot_evaluator_tree(
        work_dir, Path(__file__).resolve().parent, evaluator_id
    )
    # Snapshot the candidate's code for the final audit and claims package
    # (same filters as the tree-path archiver: no git internals, no
    # evaluation suite, no oversized files).
    root = _repo_root()
    code_dir = run_dir / "code"
    for f in root.rglob("*"):
        if not f.is_file() or ".git" in f.parts or "kapso_evaluation" in f.parts or "__pycache__" in f.parts:
            continue
        if f.stat().st_size > 2_000_000:
            continue
        dest = code_dir / f.relative_to(root)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(f, dest)
    return run_dir.name


def void_run(run_name: str, reason: str) -> None:
    """Candidate-initiated disqualification of one of THIS session's archived
    runs (e.g. a pre-fix evaluation later found leaky). Voided runs are
    excluded from final selection. Cross-session voids are refused: a session
    may only retract its own work. Refusals raise loudly (vendored contract),
    which fails the CLI with the reason in the traceback."""
    session = _session_id()
    record = archive_contract.void_run(
        Path(task_settings()["work_dir"]) / "runs",
        run_name,
        session=session,
        reason=reason,
    )
    print(f"KAPSO_EVAL_VOID {json.dumps({'run': run_name, 'session': session, 'reason': record['reason']})}")


def rescore_archived_run(run_path: str) -> None:
    """Recompute an archived run's score of record from its stored artifacts.

    Executes no candidate code: the archive already holds the prediction
    vectors, and this evaluator version scores them exactly as its run mode
    would. Final selection invokes this for every head-stamped final and
    cross-checks the result against the archive-time manifest, so an edited
    stored score becomes a loud failure instead of a winning forgery.
    """
    run_dir = Path(run_path)
    if not run_dir.is_dir():
        print(f"[grader] --rescore: no archived run directory at {run_dir}")
        sys.exit(9)
    settings = task_settings()
    primary, higher = settings["primary_metric"], bool(settings["higher_is_better"])
    val_metrics, _val_pred, _test_pred, n_val = load_and_score(settings, run_dir)
    label = json.loads((run_dir / "private" / "selection.json").read_text())
    manifest = {
        "fidelity": "full",
        "fraction": 1.0,
        "seed": 1337,
        "items": n_val,
        "total_items": n_val,
        "score": oriented(val_metrics[primary], higher),
        "raw_score": val_metrics[primary],
        "higher_is_better": higher,
        "run": run_dir.name,
        "session": label["session"],
        "mode": "rescore",
        "evaluator_id": archive_contract.fingerprint_tree(
            Path(__file__).resolve().parent
        ),
        "metrics": val_metrics,
    }
    print(f"{MANIFEST_MARKER} {json.dumps(manifest)}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fidelity", choices=["fast", "full"])
    parser.add_argument("--fraction", type=float, default=1.0)
    parser.add_argument("--seed", type=int, default=1337)
    parser.add_argument("--void", metavar="RUN",
                        help="disqualify one of this session's archived runs")
    parser.add_argument("--reason", default="",
                        help="required with --void: why the run is invalid")
    parser.add_argument("--rescore", metavar="RUN_DIR",
                        help="recompute an archived run's score of record "
                             "from its stored predictions (no candidate code)")
    args = parser.parse_args()

    if args.void:
        void_run(args.void, args.reason)
        return
    if args.rescore:
        rescore_archived_run(args.rescore)
        return
    if not args.fidelity:
        parser.error("--fidelity is required unless --void/--rescore is given")

    settings = task_settings()
    primary, higher = settings["primary_metric"], bool(settings["higher_is_better"])
    run_data_dir = Path(tempfile.mkdtemp(prefix="relbench_eval_"))
    rolling_root = settings["rolling_root"]
    if rolling_root:
        run_candidate_rolling(settings, args.fidelity, run_data_dir, Path(rolling_root))
    else:
        run_candidate(settings, args.fidelity, run_data_dir)
    val_metrics, _val_pred, _test_pred, n_val = load_and_score(settings, run_data_dir)

    evaluator_id = archive_contract.fingerprint_tree(
        Path(__file__).resolve().parent
    )
    archived = ""
    if args.fidelity == "full":
        archived = archive_full_run(settings, run_data_dir, val_metrics, evaluator_id)

    print(f"[grader] OFFICIAL VALIDATION METRICS: {json.dumps(val_metrics)} "
          f"({primary}, {'higher' if higher else 'lower'} is better)")
    if archived:
        print(f"[grader] archived as {archived}")
    manifest = {
        "fidelity": args.fidelity,
        "fraction": args.fraction,
        "seed": args.seed,
        "items": n_val,
        "total_items": n_val,
        "score": oriented(val_metrics[primary], higher),
        "raw_score": val_metrics[primary],
        "higher_is_better": higher,
        "run": archived,
        "session": _session_id(),
        "evaluator_id": evaluator_id,
    }
    manifest_line = f"{MANIFEST_MARKER} {json.dumps(manifest)}"
    if archived:
        # Durable copy OUTSIDE the session workspace: if the session (and
        # its stdout) is gone before this line is ever read, kapso's
        # teardown guard recovers the score of record from the archive.
        runs_root = Path(settings["work_dir"]) / "runs"
        (runs_root / archived / "manifest.txt").write_text(
            manifest_line + "\n"
        )
    print(manifest_line)
    shutil.rmtree(run_data_dir, ignore_errors=True)


if __name__ == "__main__":
    main()
