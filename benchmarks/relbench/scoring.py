"""The runner's own scoring around build(): the pristine task, the sanitized
copy the harness's script builds, the staged evaluation directory, and the
final evaluation (the archive's registered finals rescored by the head
evaluator, the winner's test metrics computed once, the harness's leakage
scan over its code).

Protocol stance (EVALUATION_PROTOCOL.md): model selection happens on
validation metrics only; test labels never enter the search loop, the
candidate's process or the Brief; the candidate's process reads data only
from the sanitized copy, with test information physically removed.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import stat
import subprocess
import sys
from pathlib import Path
from typing import Dict, Optional

import numpy as np
from relbench.tasks import get_task

from kapso.execution.evaluation_archive import select_final

from benchmarks.relbench.task_specs import TaskSpec, coerce_boolean_target

SANITIZED_MARKER = "SANITIZED.json"
TASK_FILE = "task.json"
FINAL_REPORT = "final_report.json"
SCAN_SCRIPT = Path("skills") / "leakage-scan" / "scripts" / "scan.py"


def pristine_task(dataset_name: str, task_name: str):
    """The task through the library's own cache, downloaded on first use."""
    return get_task(dataset_name, task_name, download=True)


def remove_read_only_tree(path: Path) -> None:
    """Delete a tree the sanitizer made read-only."""
    for item in sorted(path.rglob("*"), reverse=True):
        os.chmod(item, stat.S_IRWXU)
    os.chmod(path, stat.S_IRWXU)
    shutil.rmtree(path)


def ensure_sanitized_copy(
    script: Path, source: Path, dataset_name: str, task_name: str, out: Path, *, rolling: bool, rebuild: bool,
) -> Path:
    """The sanitized copy (or the per-tick snapshots) at `out`, built by the
    harness's script in a fresh interpreter and reused across campaigns while
    the script and the task are the same; `rebuild` builds it again."""
    want = {
        "dataset": dataset_name,
        "task": task_name,
        "rolling": rolling,
        "script_sha256": hashlib.sha256(script.read_bytes()).hexdigest(),
    }
    meta = out.parent / f"{out.name}.meta.json"
    if not rebuild and meta.is_file() and (out / SANITIZED_MARKER).is_file() and json.loads(meta.read_text()) == want:
        print(f"[relbench] {'snapshots' if rolling else 'sanitized copy'} ready at {out}")
        return out
    if out.exists():
        remove_read_only_tree(out)
    meta.unlink(missing_ok=True)
    command = [
        sys.executable, str(script),
        "--dataset", dataset_name, "--task", task_name,
        "--source", str(source), "--out", str(out),
    ] + (["--rolling"] if rolling else [])
    print(f"[relbench] building {'snapshots' if rolling else 'the sanitized copy'}: {' '.join(command)}")
    subprocess.run(command, check=True)
    meta.write_text(json.dumps(want, indent=2) + "\n")
    return out


def stage_evaluation(suite: Path, work_dir: Path, settings: Dict[str, object]) -> Path:
    """The provided grader with the task's settings beside it, under the
    archive root; written the same way every time, so a resume's fingerprint
    of the evaluation directory holds."""
    target = work_dir / "evaluation"
    if target.exists():
        shutil.rmtree(target)
    target.mkdir(parents=True)
    for item in sorted(suite.iterdir()):
        if item.is_file():
            shutil.copy2(item, target / item.name)
    (target / TASK_FILE).write_text(json.dumps(settings, indent=2, sort_keys=True) + "\n")
    return target


def provided_file_digests(evaluation_dir: Path) -> Dict[str, str]:
    """What the benchmark shipped, byte-anchored in every evaluator snapshot."""
    return {
        item.name: hashlib.sha256(item.read_bytes()).hexdigest()
        for item in sorted(evaluation_dir.iterdir())
        if item.is_file()
    }


def scan_candidate(harness_path: Path, code_dir: Path, regime: str) -> Dict[str, object]:
    """The harness's leakage scan over the winner's archived code, in tree
    mode; a harness without the skill leaves the report saying so."""
    script = harness_path / SCAN_SCRIPT
    if not script.is_file():
        return {"script": None, "findings": [], "clean": None,
                "note": f"the harness at {harness_path} has no leakage-scan skill: nothing scanned"}
    completed = subprocess.run(
        [sys.executable, str(script), "--tree", str(code_dir), "--regime", regime],
        capture_output=True, text=True,
    )
    if completed.returncode not in (0, 1):
        raise RuntimeError(f"the leakage scan failed on {code_dir}: {completed.stderr.strip()}")
    # One JSON object per finding, one per line.
    findings = [json.loads(line) for line in completed.stdout.splitlines() if line.strip()]
    return {
        "script": str(script),
        "regime": regime,
        "findings": findings,
        "clean": completed.returncode == 0,
    }


def final_report(
    work_dir: Path,
    evaluation_dir: Path,
    task,
    spec: TaskSpec,
    harness_path: Path,
    solution: Optional[Dict[str, object]],
) -> Dict[str, object]:
    """Max rescored validation among the archive's head-stamped finals, the
    winner's test metrics once, the harness's scan over its code, and the
    build's delivered candidate beside it; written to final_report.json."""
    selection = select_final(work_dir, higher_is_better=True, provided_files=provided_file_digests(evaluation_dir))
    report: Dict[str, object] = {
        "dataset": spec.dataset_name,
        "task": spec.task_name,
        "family": spec.family,
        "primary_metric": spec.primary_metric,
        "higher_is_better": spec.maximize,
        "head_evaluator_id": selection.head_evaluator_id,
        "scored": dict(selection.scored),
        "excluded": dict(selection.excluded),
        "solution": solution,
    }
    if selection.winner_run is None:
        report["run"] = None
        report["error"] = "no registered-final run under the head evaluator: no candidate to deliver"
    else:
        run_dir = work_dir / "runs" / selection.winner_run
        metrics = json.loads((run_dir / "private" / "metrics.json").read_text())
        metrics["val"] = dict(selection.winner_metrics)
        if not metrics.get("test"):
            # The in-loop grader scores the sanitized copy and cannot score
            # test; the winner's test metrics are computed here, once.
            test_pred = np.load(run_dir / "test_predictions.npy", allow_pickle=False)
            test_table = coerce_boolean_target(task.get_table("test", mask_input_cols=False), spec.target_col)
            metrics["test"] = {k: float(v) for k, v in task.evaluate(test_pred, test_table).items()}
            (run_dir / "private" / "metrics.json").write_text(json.dumps(metrics, indent=2))
        report.update({
            "run": run_dir.name,
            "selected_by": (
                f"max rescored validation {spec.primary_metric} among head-stamped final "
                f"runs (evaluator {selection.head_evaluator_id[:12]})"
            ),
            "val_metrics": metrics["val"],
            "test_metrics": metrics["test"],
            "audit": scan_candidate(harness_path, run_dir / "code", spec.regime),
            "code_path": str(run_dir / "code"),
            "predictions": {
                "val": str(run_dir / "val_predictions.npy"),
                "test": str(run_dir / "test_predictions.npy"),
            },
        })
    out = work_dir / FINAL_REPORT
    out.write_text(json.dumps(report, indent=2, default=str) + "\n")
    print(f"[relbench] final report -> {out}")
    return report
