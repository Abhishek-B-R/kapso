#!/usr/bin/env python3
"""RelBench runner: one task, one campaign on the facade's build().

    python -m benchmarks.relbench.runner -s rel-f1 -t driver-position [-i N] [--workspace DIR] [--resume]
        [--time-budget-hours H] [--harness REF] [--experience REFS] [--coding-agent CLI] [--rebuild-cache]
    python -m benchmarks.relbench.runner --list

The runner keeps the task material and launches the engine: it downloads the
task into the library's cache, builds the sanitized copy (and the per-tick
snapshots of a rolling task) with the harness's sanitizer, reused across
campaigns under a marker; stages the provided grader with the task's
settings beside it; writes the Brief from the task's facts; seeds a
shape-correct baseline candidate; and runs build() with the bundled
predictive-modelling harness (or the one --harness names) and the experience
--experience loads. After the campaign it selects among the archive's
registered finals, scores the winner on test once, runs the harness's
leakage scan over its code and writes final_report.json under the task's
archive root (`benchmark.work_root` in config.yaml).
"""

import argparse
import json
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Dict, Optional

from dotenv import load_dotenv
from relbench.tasks import get_task_names
from relbench.utils import get_relbench_cache_dir

from kapso.core.config import read_yaml
from kapso.handles import Budget, Solution
from kapso.harness import BUNDLED_ROOT
from kapso.kapso import Kapso

from benchmarks.common import stage_evaluation, write_runtime_config
from benchmarks.relbench.context import build_brief
from benchmarks.relbench.scoring import ensure_sanitized_copy, final_report, pristine_task
from benchmarks.relbench.task_specs import NATIVE_DATASETS, resolve_spec

load_dotenv()

BENCH_DIR = Path(__file__).resolve().parent
CONFIG_PATH = BENCH_DIR / "config.yaml"
DATA_DIR = BENCH_DIR / "data"
EVALUATION_SUITE = DATA_DIR / "generic_eval"
STARTER_KIT = DATA_DIR / "starter_kit"
BASELINE = DATA_DIR / "generic_baseline" / "main.py"
BUNDLED_HARNESS = "predictive-modelling"
SANITIZER = BUNDLED_ROOT / BUNDLED_HARNESS / "skills" / "sanitized-copy" / "scripts" / "sanitize.py"


def list_tasks() -> None:
    print(f"\n{'=' * 70}\nRelBench native tasks (11 databases / 66 tasks)\n{'=' * 70}")
    for dataset in NATIVE_DATASETS:
        print(f"\n  {dataset}:")
        for name in get_task_names(dataset):
            print(f"    • {name}")
    print()


def solution_summary(solution: Solution) -> Dict[str, object]:
    """What the build delivered, beside the archive's selection in the report."""
    return {
        "campaign": str(solution.campaign),
        "branch": solution.branch,
        "commit": solution.commit,
        "score": solution.score,
        "stopped_reason": solution.stopped_reason,
        "experiments": solution.experiments_total,
        "cost_usd": solution.cost_usd,
        "harness": solution.harness.name if solution.harness else None,
    }


def seeded_baseline() -> str:
    """A fresh directory holding the shape-correct trivial candidate: the
    maintainer's calibration needs a runnable candidate, and the search a
    real starting parent."""
    directory = tempfile.mkdtemp(prefix="relbench_baseline_")
    shutil.copy2(BASELINE, Path(directory) / "main.py")
    return directory


def solve_task(args) -> dict:
    settings = read_yaml(str(CONFIG_PATH))["benchmark"]
    work_dir = (Path(settings["work_root"]) / f"{args.dataset}--{args.task}").resolve()
    work_dir.mkdir(parents=True, exist_ok=True)
    print(f"\n{'=' * 70}\nSolving: {args.dataset} / {args.task}\n{'=' * 70}")
    print(f"  Archive root: {work_dir}")

    task = pristine_task(args.dataset, args.task)
    spec = resolve_spec(task, args.dataset, args.task, settings["timeouts"])
    source = Path(get_relbench_cache_dir())
    sanitized_copy = ensure_sanitized_copy(
        SANITIZER, source, args.dataset, args.task, work_dir / "sanitized_cache",
        rolling=False, rebuild=args.rebuild_cache,
    )
    rolling_root: Optional[Path] = None
    if spec.rolling:
        rolling_root = ensure_sanitized_copy(
            SANITIZER, source, args.dataset, args.task, work_dir / "rolling_caches",
            rolling=True, rebuild=args.rebuild_cache,
        )
    evaluation_dir = stage_evaluation(EVALUATION_SUITE, work_dir, {
        "dataset": args.dataset,
        "task": args.task,
        "primary_metric": spec.primary_metric,
        "higher_is_better": spec.maximize,
        "work_dir": str(work_dir),
        "full_timeout": spec.full_timeout,
        "debug_timeout": spec.debug_timeout,
        "poll_seconds": settings["grader_poll_seconds"],
        "cache_dir": str(sanitized_copy),
        "rolling_root": str(rolling_root) if rolling_root is not None else None,
    })
    shared_cache_dir = work_dir / "shared_cache"
    shared_cache_dir.mkdir(exist_ok=True)
    brief = build_brief(
        task, spec, sanitized_copy, rolling_root, shared_cache_dir, settings["hosted_model_api"],
    )

    kapso = Kapso(config=str(write_runtime_config(CONFIG_PATH, shared_cache_dir, work_dir,
                                                  archive_root=work_dir / "runs")))
    kapso.load_harness(args.harness or BUNDLED_HARNESS)
    for reference in (args.experience or "").split(","):
        if reference.strip():
            kapso.load_experience(reference.strip())
    budget = Budget(
        minutes=args.time_budget_hours * 60 if args.time_budget_hours is not None else None,
        experiments=args.iterations,
    )
    solution = kapso.build(
        brief,
        evaluation=str(evaluation_dir),
        data=str(STARTER_KIT),
        repo=None if args.resume else seeded_baseline(),
        output=args.workspace,
        budget=budget,
        resume=args.resume,
        coding_agent=args.coding_agent,
    )

    print("\n" + "=" * 70 + "\nFinal Evaluation (validation-selected, test reported once)\n" + "=" * 70)
    report = final_report(work_dir, evaluation_dir, task, spec, kapso.harness.path, solution_summary(solution))
    print(json.dumps(report, indent=2, default=str))
    return report


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run Kapso on a RelBench task",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("-s", "--dataset", type=str, help="Dataset name (e.g. rel-f1)")
    parser.add_argument("-t", "--task", type=str, help="Task name (e.g. driver-position)")
    parser.add_argument("-i", "--iterations", type=int, default=None, help="Budget.experiments (the config's when absent)")
    parser.add_argument("-d", "--coding-agent", type=str, default=None, help="The host every session runs on (the config's when absent)")
    parser.add_argument("--workspace", type=str, default=None, help="The campaign directory (output=); needed to resume")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--time-budget-hours", type=float, default=None, help="Budget.minutes, in hours")
    parser.add_argument("--harness", type=str, default=None, help=f"A harness reference (default: the bundled {BUNDLED_HARNESS})")
    parser.add_argument("--experience", type=str, default=None,
                        help="Comma-separated sources to serve: mine, a bank path or git reference, an index name")
    parser.add_argument("--rebuild-cache", action="store_true", help="Build the sanitized copy again")
    parser.add_argument("--list", action="store_true", help="List native RelBench tasks")
    args = parser.parse_args()

    if args.list:
        list_tasks()
        return
    if not args.dataset or not args.task:
        parser.error("--dataset and --task are required unless --list is given")
    if args.task not in get_task_names(args.dataset):
        parser.error(f"unknown task {args.task!r} for {args.dataset}; available: {get_task_names(args.dataset)}")

    report = solve_task(args)
    print("\n" + "=" * 70 + "\nCOMPLETED\n" + "=" * 70)
    print(f"Task: {args.dataset}/{args.task}")
    print(f"Selected run: {report.get('run')} | val: {report.get('val_metrics')}")
    print(f"TEST metrics: {report.get('test_metrics')}")
    print(f"Delivered: {report['solution']}")


if __name__ == "__main__":
    main()
