"""The IOAI task's facts, as the Brief the runner hands build().

The statement the preflight authored, verbatim; the competition, the data,
the clock, the submission procedure and the ledger, the session pool, the
organizers' rules as the task's rules. Nothing here says how to solve the
task: that is the harness's.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional

from kapso.handles import Brief

from benchmarks.common import compute_facts, resources

PROCEDURE = "python kapso_datasets/submit.py"


def build_brief(
    statement: str,
    competition: str,
    higher_is_better: bool,
    dataset_dir: Path,
    artifacts_dir: Path,
    deadline_utc: str,
    ledger_path: Path,
    shared_root: Path,
    pool_limits: Dict[str, int],
    rules_text: str,
    shared_cache_dir: Path,
    compute: Optional[Dict[str, object]] = None,
) -> Brief:
    """The whole task statement, from the preflight's statement and the
    campaign's facts: never clipped, and nothing in it is guidance."""
    compute = compute_facts() if compute is None else compute
    direction = "higher" if higher_is_better else "lower"
    sections = [
        statement,
        "\n## The campaign",
        f"The competition is `{competition}` on Kaggle; the kaggle CLI is installed and authenticated "
        "as the campaign's account, which every lane shares, so the competition's submissions list is "
        "the team's whole history.",
        f"The data is in `{dataset_dir}`, read-only; big files, checkpoints and logs go under "
        f"`{artifacts_dir}`. The shared artifact directory, `KAPSO_SHARED_CACHE_DIR`, is "
        f"`{shared_cache_dir}`.",
        f"The campaign's deadline is {deadline_utc} (UTC): a submission counts when it has finished "
        "scoring before it.",
        f"Every submission goes through the task root's procedure, `{PROCEDURE}` (`--kernel "
        "<owner>/<slug> --version <n>` for a code competition, `--file <path>` for a file upload, "
        "`-m \"<idea> local=<score>\"` always), which submits and records the submission in the "
        f"ledger at `{ledger_path}`; a raw `kaggle competitions submit` records nothing and is "
        "refused. The evaluation in `kapso_evaluation/` reads your candidate's recorded submission "
        "and reports its public score.",
        f"The session pool: the account runs at most {pool_limits['gpu']} GPU and {pool_limits['cpu']} "
        f"CPU interactive sessions at once, consumed by kernel pushes only; the ticket office is "
        f"`python3 {shared_root / 'kernel_slots.py'}` (`acquire gpu push --ref <owner>/<slug> --lane "
        "<you>` before a push, `release <ticket>` when the kernel goes terminal, no arguments for the "
        "protocol).",
        "\n## Compute\n" + resources(compute),
        "\n## The organizers' binding rules, as published\n" + rules_text.strip(),
    ]
    rules: List[str] = [
        f"The metric's direction: {direction} is better; the public leaderboard is the feedback, the "
        "private leaderboard decides the final rank.",
        "The organizers' binding rules (the section above, pinned at `kapso_datasets/RULES.md`) "
        "override the competition pages wherever the two disagree, except for the values the task "
        "itself publishes.",
    ]
    return Brief(
        objective="\n".join(sections),
        measured_by=(
            f"the public leaderboard score of your recorded submissions ({direction} is better): the "
            "evaluation in `kapso_evaluation/` reads your candidate's latest submission from the "
            "ledger, refreshes its status from the competition's submissions list and reports its "
            "public score; a pending submission is not yet a score (wait, then run it again), and a "
            "rejected or missing one is a failed evaluation. The private leaderboard decides the final "
            "rank, read once after the campaign."
        ),
        target="the top of the competition's public leaderboard, and the private leaderboard behind it",
        rules=rules,
    )
