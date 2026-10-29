"""The MLE-bench competition's facts, as the Brief the runner hands build().

The competition's description as the benchmark ships it, the prepared
data's layout, the submission contract with the sample file, the held-out
protocol that is the search's signal, the debug and full contract with the
caps, the packages the environment refuses, the compute. Nothing here says
how to solve the competition: that is the harness's.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional

from kapso.handles import Brief

from benchmarks.common import compute_facts, directory_layout, resources


def held_out_rule() -> str:
    return (
        "The search's signal is your own held-out score: hold back a stratified ten percent "
        "of the training data, problem-aware (the unit that repeats across rows stays on one "
        "side), and train nothing on it, not even a hyperparameter; at the end of every run "
        "print its score under the competition's metric as a single float in "
        "`<score>...</score>` tags, e.g. `<score>0.96</score>`. A run without the tag has no "
        "score."
    )


def submission_rules(data_dir: Path, debug_timeout: int, full_timeout: int, forbidden: List[str]) -> List[str]:
    return [
        f"The competition's data is in `{data_dir}`, read-only, every archive already extracted; "
        "nothing under it is changed.",
        "`main.py` at the repository root is the program; on every run (debug and full) it "
        "writes `final_submission.csv` at the repository root, next to `main.py`, in the "
        "format of `sample_submission.csv`, and the file is committed with the candidate: the "
        "official grade reads it from the delivered branch, and a missing or misplaced file "
        "scores nothing.",
        f"`python main.py --debug` runs the whole pipeline on a small sample through to a valid "
        f"`final_submission.csv` (the rows it skips filled with a default) within "
        f"{debug_timeout // 60} minutes; `python main.py` rewrites every prediction within "
        f"{full_timeout // 3600:.1f} hours. The evaluation runs the debug mode as the gate, then "
        "the full mode, and validates the file after each.",
        held_out_rule(),
        f"These packages are incompatible with the environment and never imported: {', '.join(forbidden)}.",
    ]


def build_brief(
    competition,
    data_dir: Path,
    higher_is_better: bool,
    debug_timeout: int,
    full_timeout: int,
    floor_score: float,
    forbidden: List[str],
    shared_cache_dir: Path,
    compute: Optional[Dict[str, object]] = None,
) -> Brief:
    """The whole competition statement, from the benchmark's own description
    and the prepared files: never clipped, and nothing in it is guidance."""
    compute = compute_facts() if compute is None else compute
    direction = "higher" if higher_is_better else "lower"
    sections = [
        f"# Kaggle competition {competition.id} ({competition.name})",
        f"A competition from the MLE-bench benchmark ({competition.competition_type}): the best "
        f"possible score on the private test answers, graded once after the campaign. The "
        f"metric's direction: {direction} is better.",
        "\n## The competition's description, as published\n" + competition.description,
        "\n## Data\n" + directory_layout(data_dir),
        f"\nThe shared artifact directory, `KAPSO_SHARED_CACHE_DIR`, is `{shared_cache_dir}`: "
        "it persists across experiments and campaigns of this competition. Files under "
        "`kapso_evaluation/` are not modified; `kapso_evaluation/task.json` names the data "
        "directory and the caps.",
        "\n## Compute\n" + resources(compute),
    ]
    orientation = "as it is" if higher_is_better else "negated, so that higher is better"
    return Brief(
        objective="\n".join(sections),
        measured_by=(
            f"the held-out score your program prints in `<score>` tags, a stratified ten percent "
            f"of the training data held back and never trained on, under the competition's "
            f"metric ({direction} is better); the evaluation in `kapso_evaluation/` runs the "
            f"program, validates `final_submission.csv` and reads the tag, and the engine's "
            f"score is that number {orientation}. The official grade on the private test "
            "answers is computed once after the campaign on the delivered candidate and never "
            "shown."
        ),
        baseline=(
            "the seeded candidate `main.py`, which writes the sample submission unchanged and "
            f"reports the floor score {floor_score}: nothing worse ships."
        ),
        target="a medal on the competition's private leaderboard (the official grade reports the medal thresholds)",
        rules=submission_rules(data_dir, debug_timeout, full_timeout, forbidden),
    )
