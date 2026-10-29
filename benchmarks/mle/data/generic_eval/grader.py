"""MLE-bench provided grader — the scoring logic the maintainer registers.

Runs the candidate's `main.py` from the repository root as an isolated child
process, checks that it wrote a valid `final_submission.csv` at the root
(the competition's own validator), reads the held-out score the program
reports in `<score>` tags, and prints the machine-readable manifest line
the search parses as the score of record. The official grade on the private
answers is never computed here: the runner computes it once, after the
campaign, on the delivered candidate.

CLI (the registered entrypoint delegates here verbatim):
    python kapso_evaluation/grader.py --fidelity fast|full [--fraction F] [--seed S]

Fidelity: `fast` runs `python main.py --debug` (the contract's cheap,
whole-pipeline mode) under the debug cap; `full` runs the debug mode first
as the gate, then `python main.py` under the full cap. Both read the last
`<score>` the run printed. `fraction`/`seed` are echoed into the manifest.

Configuration: `task.json` beside this file, written by the runner that
stages the evaluation directory:
    competition_id       the competition in the benchmark's registry
    higher_is_better     the metric's direction
    data_dir             the prepared competition data, read-only
    full_timeout, debug_timeout   the candidate's caps, seconds
    floor_score          the score the seeded baseline reports

The engine optimises one score, higher is better: the manifest's `score` is
the held-out score oriented that way (negated when lower is better) and
`raw_score` is the number the program reported.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from mlebench.grade import validate_submission
from mlebench.registry import registry

MANIFEST_MARKER = "KAPSO_EVAL_MANIFEST"
TASK_FILE = "task.json"
SUBMISSION = "final_submission.csv"
SCORE_TAG = re.compile(r"<score>\s*(-?[0-9]+(?:\.[0-9]+)?(?:[eE][-+]?[0-9]+)?)\s*</score>")
POLL_SECONDS = 1.0


def task_settings() -> dict:
    """The task's settings from `task.json` beside this file; a missing file is a staging error."""
    path = Path(__file__).resolve().parent / TASK_FILE
    if not path.is_file():
        print(f"[grader] missing {path}: the runner stages the evaluation directory with the task's settings")
        sys.exit(2)
    return json.loads(path.read_text(encoding="utf-8"))


def oriented(score: float, higher_is_better: bool) -> float:
    return score if higher_is_better else -score


def _repo_root() -> Path:
    """The candidate repo root: the parent of this suite's directory."""
    return Path(__file__).resolve().parent.parent


def _run_child(cmd: list, cwd: Path, env: dict, deadline: float) -> str:
    """Run the candidate to completion or the deadline, streaming its output
    and returning it whole (the score tag is read from it)."""
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
        log.seek(0)
        output = log.read()
    if proc.returncode != 0:
        print(f"[grader] candidate exited non-zero ({proc.returncode})")
        sys.exit(5)
    return output


def run_candidate(settings: dict, debug: bool) -> str:
    root = _repo_root()
    if not (root / "main.py").exists():
        print("[grader] main.py not found at repo root — the solution must be main.py")
        sys.exit(3)
    submission = root / SUBMISSION
    if submission.exists():
        submission.unlink()
    cmd = [sys.executable, "main.py"] + (["--debug"] if debug else [])
    timeout = int(settings["debug_timeout"] if debug else settings["full_timeout"])
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    print(f"[grader] running candidate: {' '.join(cmd)} (timeout {timeout}s)")
    return _run_child(cmd, root, env, time.time() + timeout)


def check_submission(settings: dict) -> None:
    """The competition's own validator on the file the run wrote at the root."""
    submission = _repo_root() / SUBMISSION
    if not submission.is_file():
        print(f"[grader] contract violation: {SUBMISSION} was not written at the repository root")
        sys.exit(6)
    valid, message = validate_submission(submission, registry.get_competition(settings["competition_id"]))
    if not valid:
        print(f"[grader] contract violation: {SUBMISSION} is not a valid submission: {message}")
        sys.exit(6)


def reported_score(output: str) -> float:
    """The last `<score>` the program printed: the held-out score."""
    found = SCORE_TAG.findall(output)
    if not found:
        print("[grader] contract violation: the run printed no <score>...</score> tag")
        sys.exit(6)
    return float(found[-1])


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fidelity", choices=["fast", "full"], required=True)
    parser.add_argument("--fraction", type=float, default=1.0)
    parser.add_argument("--seed", type=int, default=1337)
    args = parser.parse_args()

    settings = task_settings()
    higher = bool(settings["higher_is_better"])
    output = run_candidate(settings, debug=True)
    check_submission(settings)
    if args.fidelity == "full":
        output = run_candidate(settings, debug=False)
        check_submission(settings)
    score = reported_score(output)
    print(f"[grader] HELD-OUT SCORE: {score} ({'higher' if higher else 'lower'} is better); {SUBMISSION} valid")
    manifest = {
        "fidelity": args.fidelity,
        "fraction": args.fraction,
        "seed": args.seed,
        "items": 1,
        "total_items": 1,
        "score": oriented(score, higher),
        "raw_score": score,
        "higher_is_better": higher,
        "submission": SUBMISSION,
    }
    print(f"{MANIFEST_MARKER} {json.dumps(manifest)}")


if __name__ == "__main__":
    main()
