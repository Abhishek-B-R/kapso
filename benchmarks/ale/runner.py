#!/usr/bin/env python3
"""ALE-Bench runner: one problem, one campaign on the facade's build().

    python -m benchmarks.ale.runner --problem <id> [-i N] [--workspace DIR] [--resume]
        [--harness REF] [--experience REFS] [--coding-agent CLI]
    python -m benchmarks.ale.runner --problem <id> --workspace DIR --final-eval-only
    python -m benchmarks.ale.runner --list [--lite]

The runner keeps the problem material and launches the engine: it loads the
problem through the benchmark's own library, writes the task root (the
public seeds) under the archive root (`benchmark.work_root` in config.yaml),
stages the provided grader with the problem's settings beside it, writes the
Brief from the problem's statement, seeds the baseline candidate, and runs
build() with the bundled competitive-programming harness (or the one
--harness names) and the experience --experience loads. After the campaign
it judges the delivered candidate once on the private cases, estimates the
rank and the performance in the contest's own units, and writes
final_report.json.
"""

import argparse
import json
import shutil
import tempfile
import warnings
from pathlib import Path
from typing import Dict

from dotenv import load_dotenv

# The benchmark library leaks ResourceWarnings from its image handling.
warnings.filterwarnings("ignore", category=ResourceWarning, module="ale_bench")
warnings.filterwarnings("ignore", category=ResourceWarning, message="unclosed file")

import ale_bench
from ale_bench.data import ScoreType, load_problem

from kapso.core.config import read_yaml
from kapso.handles import Budget, Solution
from kapso.kapso import Kapso

from benchmarks.ale.context import build_brief
from benchmarks.ale.problems import LITE_PROBLEMS
from benchmarks.common import stage_evaluation, write_runtime_config

load_dotenv()

BENCH_DIR = Path(__file__).resolve().parent
CONFIG_PATH = BENCH_DIR / "config.yaml"
EVALUATION_SUITE = BENCH_DIR / "data" / "generic_eval"
BUNDLED_HARNESS = "competitive-programming"
FINAL_REPORT = "final_report.json"
SOLUTION = "main.cpp"
LANGUAGE = "cpp23"
SEED_LIST = "seeds.txt"


def list_problems(lite_only: bool) -> None:
    problems = LITE_PROBLEMS if lite_only else ale_bench.list_problem_ids()
    title = "ALE-Bench lite problems" if lite_only else "All ALE-Bench problems"
    print(f"\n{'=' * 60}\n{title} ({len(problems)} total)\n{'=' * 60}")
    for problem_id in sorted(problems):
        print(f"  • {problem_id}")
    print()


def baseline_program(example_output: str) -> str:
    """A valid C++ program that prints the problem's example output whatever
    the input: the maintainer's calibration needs a runnable candidate, and
    the search a starting parent that takes the floor."""
    body = example_output.rstrip("\n")
    return (
        "#include <iostream>\n"
        "#include <string>\n"
        "// The seeded baseline: it prints the example output whatever the input, and\n"
        "// scores the floor. Replace me with a real solution.\n"
        "int main() {\n"
        "    std::string line;\n"
        "    while (std::getline(std::cin, line)) {}\n"
        f"    std::cout << R\"KAPSO({body})KAPSO\" << std::endl;\n"
        "    return 0;\n"
        "}\n"
    )


def write_task_root(work_dir: Path, public_seeds) -> Path:
    """The task root the harness's hooks and skills read: the seed list."""
    task_root = work_dir / "task_root"
    task_root.mkdir(parents=True, exist_ok=True)
    (task_root / SEED_LIST).write_text("".join(f"{seed}\n" for seed in public_seeds))
    return task_root


def seeded_baseline(example_output: str) -> str:
    directory = tempfile.mkdtemp(prefix="ale_baseline_")
    (Path(directory) / SOLUTION).write_text(baseline_program(example_output))
    return directory


def solution_summary(solution: Solution) -> Dict[str, object]:
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


def final_report(work_dir: Path, problem_id: str, num_workers: int, solution: Solution, standings) -> Dict[str, object]:
    """The private cases once, on the delivered candidate's `main.cpp`, with
    the rank and the performance the benchmark estimates against the
    contest's standings (the loader's: a session refuses to hand them
    out); or the no-candidate report."""
    report: Dict[str, object] = {"problem_id": problem_id, "solution": solution_summary(solution)}
    candidate = solution.campaign / SOLUTION
    if solution.branch is None:
        report["error"] = "no candidate delivered"
    elif not candidate.is_file():
        report["error"] = f"the delivered candidate has no {SOLUTION} at the repository root"
    else:
        session = ale_bench.start(problem_id=problem_id, lite_version=False, num_workers=num_workers,
                                  run_visualization_server=False)
        private_result, final_rank, final_performance = session.private_eval(
            candidate.read_text(encoding="utf-8"), code_language=LANGUAGE,
        )
        contestants = len(standings.standings_scores)
        report["private_evaluation"] = {
            "private_score": private_result.overall_absolute_score,
            "judge_result": private_result.overall_judge_result.value,
            "final_rank": final_rank,
            "contestants": contestants,
            "rank_percentage": round(final_rank / contestants * 100, 2),
            "final_performance": final_performance,
        }
    out = work_dir / FINAL_REPORT
    out.write_text(json.dumps(report, indent=2, default=str) + "\n")
    print(f"[ale] final report -> {out}")
    return report


def solve_problem(args) -> dict:
    settings = read_yaml(str(CONFIG_PATH))["benchmark"]
    work_dir = (Path(settings["work_root"]) / args.problem).resolve()
    work_dir.mkdir(parents=True, exist_ok=True)
    print(f"\n{'=' * 60}\nSolving: {args.problem}\n{'=' * 60}")
    print(f"  Archive root: {work_dir}")

    problem, seeds, standings, _rank_map, _tool_dir = load_problem(args.problem, lite_version=False)
    higher_is_better = problem.metadata.score_type == ScoreType.MAXIMIZE
    floors = settings["floor_scores"]
    floor_score = floors["higher_is_better"] if higher_is_better else floors["lower_is_better"]
    runs = int(settings["runs"])
    task_root = write_task_root(work_dir, seeds.public)
    evaluation_dir = stage_evaluation(EVALUATION_SUITE, work_dir, {
        "problem_id": args.problem,
        "higher_is_better": higher_is_better,
        "runs": runs,
        "num_workers": int(settings["num_workers"]),
        "floor_score": floor_score,
    })
    shared_cache_dir = work_dir / "shared_cache"
    shared_cache_dir.mkdir(exist_ok=True)
    brief = build_brief(problem, seeds.public, higher_is_better, runs, len(standings.standings_scores), shared_cache_dir)

    if args.final_eval_only:
        # The campaign ran already: the report on the solution the workspace holds.
        solution = Solution.open(args.workspace)
    else:
        kapso = Kapso(config=str(write_runtime_config(CONFIG_PATH, shared_cache_dir, work_dir)))
        kapso.load_harness(args.harness or BUNDLED_HARNESS)
        for reference in (args.experience or "").split(","):
            if reference.strip():
                kapso.load_experience(reference.strip())
        solution = kapso.build(
            brief,
            evaluation=str(evaluation_dir),
            data=str(task_root),
            repo=None if args.resume else seeded_baseline(problem.example_output),
            output=args.workspace,
            budget=Budget(
                minutes=args.time_budget_hours * 60 if args.time_budget_hours is not None else None,
                experiments=args.iterations,
            ),
            resume=args.resume,
            coding_agent=args.coding_agent,
        )

    print("\n" + "=" * 60 + "\nFinal Evaluation (the private cases, once)\n" + "=" * 60)
    report = final_report(work_dir, args.problem, int(settings["num_workers"]), solution, standings)
    print(json.dumps(report, indent=2, default=str))
    return report


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run Kapso on an ALE-Bench problem",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("-p", "--problem", type=str, help="Problem ID (e.g. ahc039)")
    parser.add_argument("-i", "--iterations", type=int, default=None, help="Budget.experiments (the config's when absent)")
    parser.add_argument("-d", "--coding-agent", type=str, default=None, help="The host every session runs on (the config's when absent)")
    parser.add_argument("--workspace", type=str, default=None, help="The campaign directory (output=); needed to resume")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--final-eval-only", action="store_true",
                        help="No campaign: the final report on the solution --workspace already holds")
    parser.add_argument("--time-budget-hours", type=float, default=None, help="Budget.minutes, in hours")
    parser.add_argument("--harness", type=str, default=None, help=f"A harness reference (default: the bundled {BUNDLED_HARNESS})")
    parser.add_argument("--experience", type=str, default=None,
                        help="Comma-separated sources to serve: mine, a bank path or git reference, an index name")
    parser.add_argument("--list", action="store_true", help="List all problems")
    parser.add_argument("--lite", action="store_true", help="List the lite problems")
    args = parser.parse_args()

    if args.list or args.lite:
        list_problems(lite_only=args.lite)
        return
    if not args.problem:
        parser.error("--problem is required unless --list or --lite is given")
    if args.final_eval_only and not args.workspace:
        parser.error("--final-eval-only needs --workspace, the campaign directory the build wrote")
    if args.problem not in ale_bench.list_problem_ids():
        parser.error(f"unknown problem {args.problem!r}; --list prints the registry")

    report = solve_problem(args)
    print("\n" + "=" * 60 + "\nCOMPLETED\n" + "=" * 60)
    print(f"Problem: {report['problem_id']}")
    print(f"Private evaluation: {report.get('private_evaluation', report.get('error'))}")
    print(f"Delivered: {report['solution']}")


if __name__ == "__main__":
    main()
