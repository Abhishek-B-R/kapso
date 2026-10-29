"""ALE-Bench provided grader — the official scorer over the public cases.

Compiles and judges the candidate's `main.cpp` (cpp23) at the repository
root through the benchmark's own session (the Docker judge), on every public
case, and prints the machine-readable manifest line the search parses as the
score of record: the sum of the case scores, averaged over the configured
runs. It also writes the per-seed results file the harness's scorer-cli skill
describes, on request. The private cases and the rating are never computed
here: the runner computes them once, after the campaign.

CLI (the registered entrypoint delegates here verbatim):
    python kapso_evaluation/grader.py --fidelity fast|full [--fraction F] [--seed S]
    python kapso_evaluation/grader.py --scores results/scores.json [--runs N]

Fidelity: `fast` is one run over the public cases; `full` is `runs` runs
(the task's setting). `fraction`/`seed` are echoed into the manifest.

Configuration: `task.json` beside this file, written by the runner:
    problem_id           the problem in the benchmark's registry
    higher_is_better     the problem's score type
    runs                 the runs per full evaluation
    num_workers          the judge's parallel case workers
    floor_score          the score a failed submission takes (the contest's
                         all-or-nothing rule: a case not accepted, or scored
                         zero, fails the submission)

The engine optimises one score, higher is better: the manifest's `score` is
the mean total oriented that way (negated when lower is better), or the
floor oriented the same way for a failed submission; `raw_score` is the
mean total as the contest counts it.
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from pathlib import Path
from typing import Dict, List

import ale_bench
from ale_bench.result import JudgeResult

MANIFEST_MARKER = "KAPSO_EVAL_MANIFEST"
TASK_FILE = "task.json"
SOLUTION = "main.cpp"
LANGUAGE = "cpp23"
STATUS_BY_JUDGE = {
    JudgeResult.ACCEPTED: "ok",
    JudgeResult.WRONG_ANSWER: "wrong-answer",
    JudgeResult.TIME_LIMIT_EXCEEDED: "time-limit",
    JudgeResult.RUNTIME_ERROR: "runtime-error",
    JudgeResult.MEMORY_LIMIT_EXCEEDED: "runtime-error",
    JudgeResult.OUTPUT_LIMIT_EXCEEDED: "runtime-error",
    JudgeResult.COMPILATION_ERROR: "runtime-error",
    JudgeResult.INTERNAL_ERROR: "runtime-error",
}


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
    return Path(__file__).resolve().parent.parent


def read_solution() -> str:
    solution = _repo_root() / SOLUTION
    if not solution.is_file():
        print(f"[grader] {SOLUTION} not found at the repository root — the solution is one {SOLUTION}")
        sys.exit(3)
    return solution.read_text(encoding="utf-8")


def open_session(settings: dict):
    return ale_bench.start(
        problem_id=settings["problem_id"], lite_version=False,
        num_workers=int(settings["num_workers"]), run_visualization_server=False,
    )


def evaluate(session, code: str, runs: int) -> Dict[str, object]:
    """The public cases judged `runs` times: per seed the mean score, the
    spread, the longest run and the worst status; the mean total; whether
    every case of every run was accepted with a non-zero score."""
    per_seed: Dict[str, Dict[str, object]] = {}
    totals: List[float] = []
    seeds = [str(seed) for seed in session.public_seeds]
    scores_by_seed = {seed: [] for seed in seeds}
    runtime_by_seed = {seed: 0.0 for seed in seeds}
    status_by_seed = {seed: "ok" for seed in seeds}
    for index in range(runs):
        result = session.public_eval(code, code_language=LANGUAGE)
        totals.append(float(result.overall_absolute_score))
        print(f"[grader] run {index + 1}/{runs}: {result.overall_judge_result.value}, total {result.overall_absolute_score}")
        for seed, case in zip(seeds, result.case_results):
            scores_by_seed[seed].append(float(case.absolute_score))
            runtime_by_seed[seed] = max(runtime_by_seed[seed], float(case.execution_time))
            status = STATUS_BY_JUDGE[case.judge_result]
            if status != "ok" or case.absolute_score == 0:
                status_by_seed[seed] = status if status != "ok" else "wrong-answer"
    for seed in seeds:
        scores = scores_by_seed[seed]
        per_seed[seed] = {
            "score": statistics.fmean(scores),
            "spread": statistics.pstdev(scores) if len(scores) > 1 else 0.0,
            "runtime_ms": int(round(runtime_by_seed[seed] * 1000)),
            "status": status_by_seed[seed],
        }
    valid = all(entry["status"] == "ok" for entry in per_seed.values())
    return {"seeds": per_seed, "total": statistics.fmean(totals), "valid": valid, "runs": runs}


def write_scores(path: Path, evaluation: Dict[str, object]) -> None:
    """The results file the harness's scorer-cli skill describes."""
    payload = {
        "build": f"the official judge, {LANGUAGE}",
        "solution": SOLUTION,
        "runs": evaluation["runs"],
        "seeds": evaluation["seeds"],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n")
    print(f"[grader] results -> {path}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fidelity", choices=["fast", "full"])
    parser.add_argument("--fraction", type=float, default=1.0)
    parser.add_argument("--seed", type=int, default=1337)
    parser.add_argument("--scores", metavar="PATH", help="write the per-seed results file here instead of the manifest")
    parser.add_argument("--runs", type=int, default=None, help="with --scores: the runs per seed (the task's setting when absent)")
    args = parser.parse_args()
    if not args.fidelity and not args.scores:
        parser.error("--fidelity or --scores is required")

    settings = task_settings()
    higher = bool(settings["higher_is_better"])
    code = read_solution()
    session = open_session(settings)
    if args.scores:
        runs = args.runs if args.runs is not None else int(settings["runs"])
        target = Path(args.scores)
        if not target.is_absolute():
            target = _repo_root() / target   # the attempt's root, wherever the command ran from
        write_scores(target, evaluate(session, code, runs))
        return
    runs = 1 if args.fidelity == "fast" else int(settings["runs"])
    evaluation = evaluate(session, code, runs)
    failed = [seed for seed, entry in evaluation["seeds"].items() if entry["status"] != "ok"]
    raw = float(evaluation["total"])
    score = oriented(raw if evaluation["valid"] else float(settings["floor_score"]), higher)
    print(f"[grader] PUBLIC SCORE: mean total {raw} over {runs} run(s) ({'higher' if higher else 'lower'} is better); "
          + ("every case accepted" if evaluation["valid"] else f"failed cases: {', '.join(failed)} (the floor applies)"))
    manifest = {
        "fidelity": args.fidelity,
        "fraction": args.fraction,
        "seed": args.seed,
        "items": len(evaluation["seeds"]),
        "total_items": len(evaluation["seeds"]),
        "score": score,
        "raw_score": raw,
        "higher_is_better": higher,
        "valid": evaluation["valid"],
        "failed_cases": failed,
        "runs": runs,
    }
    print(f"{MANIFEST_MARKER} {json.dumps(manifest)}")


if __name__ == "__main__":
    main()
