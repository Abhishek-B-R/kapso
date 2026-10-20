"""A stray non-UTF-8 byte in an evaluator's output never discards a finished run."""

import json
import subprocess
import sys
from pathlib import Path

from kapso.execution.evaluation_archive import ENTRYPOINT_NAME, rescore_run
from kapso.execution.evaluation_maintainer import TimingModel
from kapso.execution.evaluation_maintainer.maintainer import MANIFEST_MARKER
from kapso.execution.search_strategies.generic.registered_evaluation import (
    run_frame_subprocess,
)
from kapso.learning.codify_run import LocalExecutor
from tests.test_evaluation_maintainer import _workspace, make_maintainer

MANIFEST = json.dumps(
    {
        "fidelity": "fast",
        "fraction": 0.05,
        "seed": 1337,
        "items": 10,
        "total_items": 200,
        "score": 0.5,
    }
)
# Prints one byte that is not valid UTF-8, then a well-formed manifest line.
EVALUATOR = (
    "import sys; sys.stdout.buffer.write(b'progress \\xff 50%\\n'); "
    f"sys.stdout.flush(); print('{MANIFEST_MARKER} {MANIFEST}')"
)


def test_frame_run_keeps_a_completed_run_with_stray_bytes(tmp_path: Path) -> None:
    run = run_frame_subprocess(
        [sys.executable, "-c", EVALUATOR], cwd=str(tmp_path), deadline_seconds=30
    )

    assert run.completed
    assert MANIFEST_MARKER in run.stdout and "�" in run.stdout


def test_rescore_reads_the_manifest_past_a_stray_byte(tmp_path: Path) -> None:
    snapshot, run_dir = tmp_path / "snapshot", tmp_path / "run"
    snapshot.mkdir()
    run_dir.mkdir()
    (snapshot / ENTRYPOINT_NAME).write_text(EVALUATOR)
    (run_dir / "manifest.txt").write_text(f"{MANIFEST_MARKER} {MANIFEST}\n")

    assert rescore_run(snapshot, run_dir)["score"] == 0.5


def test_codify_local_run_records_output_with_a_stray_byte(tmp_path: Path) -> None:
    (tmp_path / "replay").mkdir()
    (tmp_path / "replay" / "eval.py").write_text(EVALUATOR)

    LocalExecutor({"iteration_timeout_minutes": 1}).run_evaluation(tmp_path)

    assert "�" in (tmp_path / "replay-stdout.txt").read_text()


def test_calibration_reads_the_manifest_past_a_stray_byte(tmp_path: Path) -> None:
    # The real subprocess.run, fed the arguments the maintainer passes, with
    # the evaluation command swapped for an evaluator that emits the byte.
    def run(command, **kwargs):
        return subprocess.run([sys.executable, "-c", EVALUATOR], **kwargs)

    maintainer = make_maintainer(_workspace(tmp_path), runner=run)

    timing, manifest = maintainer._run_calibration()

    assert isinstance(timing, TimingModel) and manifest["score"] == 0.5
