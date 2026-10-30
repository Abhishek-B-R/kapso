"""Stop hook on implementation: no finish before the first submission is in
the ledger.

A leaderboard task's root (`kapso_datasets/` beside the nearest task
statement at or above the session's directory that has one) holds
`contest.json`: the competition's slug, the absolute path of the ledger the
submissions are recorded in, and the procedure that submits and records,
when one exists (the kaggle-cli and contest-preflight skills). A task root
without `contest.json` is not a leaderboard contest here, and the hook has
no opinion. The ledger is `{"submissions": [...]}`; one entry for this
competition with a submission id that is on the site (`pending`, awaiting
its score, or `complete`, scored) is the insurance; one the CLI refused
(`rejected`) or the site failed to score (`error`) is not.

The hook asks once (it stays silent when the event says the session is
already continuing because of a stop hook) and catches a mistake, not a
lie: the verifier reads the submission on the site. A descriptor or a
ledger that is not JSON makes the hook fail loud, and the launcher line in
hook.json turns that failure into a blocking exit (code 2).
"""
import json
import sys
from pathlib import Path

TASK_STATEMENT = "kapso_task.md"
DATA_DIR = "kapso_datasets"
CONTEST = "contest.json"


def task_root(start: Path):
    """The data directory beside the nearest task statement at or above `start` that has one, or None."""
    for directory in (start, *start.parents):
        if (directory / TASK_STATEMENT).is_file() and (directory / DATA_DIR).is_dir():
            return directory / DATA_DIR
    return None


def block(reason: str) -> None:
    print(json.dumps({"decision": "block", "reason": reason}))


def main() -> None:
    event = json.load(sys.stdin)
    if isinstance(event, dict) and event.get("stop_hook_active"):
        sys.exit(0)
    root = task_root(Path.cwd().resolve())
    if root is None or not (root / CONTEST).is_file():
        sys.exit(0)
    contest = json.loads((root / CONTEST).read_text())  # a corrupt contest.json fails loud here
    if not isinstance(contest, dict) or not isinstance(contest.get("competition"), str) or not contest["competition"]:
        block(f"{root / CONTEST} names no competition: the task root is incomplete. Say so in the attempt notes and finish.")
        return
    if not isinstance(contest.get("ledger"), str) or not Path(contest["ledger"]).is_absolute():
        block(f"{root / CONTEST} names no absolute ledger path: the task root is incomplete. Say so in the attempt notes and finish.")
        return
    ledger_path = Path(contest["ledger"])
    if not ledger_path.is_file():
        block(f"No submission yet: the ledger {ledger_path} does not exist. Ship the insurance submission (the "
              "contest-economics skill: a valid scoring submission first, then the improvement) and record it as the "
              "kaggle-cli skill says before finishing; if no submission could be made, say why in the attempt notes and finish.")
        return
    ledger = json.loads(ledger_path.read_text())  # a corrupt ledger fails loud here
    submissions = ledger.get("submissions") if isinstance(ledger, dict) else None
    if not isinstance(submissions, list):
        block(f"{ledger_path} has no `submissions` list; write it as the kaggle-cli skill describes.")
        return
    recorded = [entry for entry in submissions
                if isinstance(entry, dict) and entry.get("competition") == contest["competition"]
                and isinstance(entry.get("submission_id"), str) and entry["submission_id"]
                and entry.get("status") in ("pending", "complete")]
    if not recorded:
        block(f"No submission yet: {ledger_path} records none for {contest['competition']} with a submission id "
              "that is pending or complete (a rejected or errored one is no insurance). Ship the insurance "
              "submission and record it before finishing.")
        return
    sys.exit(0)


if __name__ == "__main__":
    main()
