"""The ALE-Bench problem's facts, as the Brief the runner hands build().

The statement as the benchmark ships it, the constraints, the example, the
tools' README, the scorer's invocation and the results file, the submission
contract, the contest's units. Nothing here says how to solve the problem:
that is the harness's.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional

from kapso.handles import Brief

from benchmarks.common import compute_facts, resources

SCORER_COMMAND = "python kapso_evaluation/grader.py --scores results/scores.json"


def rules(problem, runs: int) -> List[str]:
    time_limit = problem.constraints.time_limit
    memory_mb = problem.constraints.memory_limit // (1024 * 1024)
    return [
        "The solution is one C++ program, `main.cpp` at the repository root, compiled and "
        "judged as cpp23 by the official judge; a missing or misplaced file scores nothing. "
        "A `pre_run.cpp` may compute tables that `main.cpp` embeds; it runs within a minute "
        "on your machine, and the judge never runs it.",
        f"Every case runs under the problem's limits: {time_limit} seconds and {memory_mb} MB. "
        "A case the judge does not accept (a wrong answer, a time limit, a runtime error, a "
        "compilation error), or scores zero, fails the whole submission: it takes the floor "
        "score, whatever the other cases scored. Count operations from the largest inputs the "
        "constraints allow, and keep a margin for input and output.",
        f"The scorer is the official judge over the public cases: `{SCORER_COMMAND}` compiles "
        f"and judges `main.cpp` on every seed of `kapso_datasets/seeds.txt`, {runs} runs each, "
        "and writes `results/scores.json` at the repository root (the score, the spread, the "
        "runtime and the status per seed). Run it in the foreground before finishing; the "
        "evaluation runs the same judge for the score of record.",
        "No machine-learned component where the time limit cannot afford it; no library the "
        "judge's environment lacks.",
    ]


def build_brief(
    problem,
    public_seeds: List[int],
    higher_is_better: bool,
    runs: int,
    contestants: int,
    shared_cache_dir: Path,
    compute: Optional[Dict[str, object]] = None,
) -> Brief:
    """The whole problem statement, from the benchmark's own problem object:
    never clipped, and nothing in it is guidance."""
    compute = compute_facts() if compute is None else compute
    direction = "higher" if higher_is_better else "lower"
    metadata = problem.metadata
    sections = [
        f"# AtCoder Heuristic Contest problem {metadata.problem_id}: {metadata.title}",
        f"A {metadata.problem_type.value} problem from the ALE-Bench benchmark ({metadata.contest_url}); "
        f"the score type is {metadata.score_type.value}: {direction} is better. The contest ran "
        f"from {metadata.start_at.isoformat()} to {metadata.end_at.isoformat()} with {contestants} "
        "contestants on its standings.",
        "\n## Problem statement\n" + problem.statement,
        "\n## Constraints\n"
        f"Time limit: {problem.constraints.time_limit} seconds per case. Memory limit: "
        f"{problem.constraints.memory_limit // (1024 * 1024)} MB.",
        "\n## Example\nInput:\n```\n" + problem.example_input.rstrip() + "\n```\nOutput:\n```\n"
        + problem.example_output.rstrip() + "\n```",
        "\n## The local tools, as the contest shipped them\n" + problem.tool_readme,
        "\n## Scoring\n"
        f"The public cases are the {len(public_seeds)} seeds in `kapso_datasets/seeds.txt`; the "
        f"score of a submission is the sum of its case scores, the mean over {runs} runs of the "
        "official judge. The private cases decide the contest's final rank and the performance "
        "rating; they are judged once after the campaign and never shown.",
        f"\nThe shared artifact directory, `KAPSO_SHARED_CACHE_DIR`, is `{shared_cache_dir}`: "
        "it persists across experiments and campaigns of this problem. Files under "
        "`kapso_evaluation/` are not modified.",
        "\n## Compute\n" + resources(compute),
    ]
    orientation = "as it is" if higher_is_better else "negated, so that higher is better"
    return Brief(
        objective="\n".join(sections),
        measured_by=(
            f"the official judge over the public cases: the sum of the case scores, the mean "
            f"over {runs} runs ({direction} is better); a submission with a case not accepted, "
            "or scored zero, takes the floor. The evaluation in `kapso_evaluation/` runs the "
            f"judge, and the engine's score is the mean total {orientation}. The private cases, "
            "the final rank and the performance are computed once after the campaign."
        ),
        baseline=(
            "the seeded candidate `main.cpp`, which prints the example output whatever the "
            "input: it takes the floor, and nothing that fails a case ships."
        ),
        target="the top of the contest's standings: the rank and the performance the private evaluation estimates",
        rules=rules(problem, runs),
    )
