"""Stop hook on implementation: no finish before the first submission is in
the ledger.

A contest task's root (`kapso_datasets/` beside the task statement, found
from the session's directory upward) holds `contest.json`, written by the
runner: the competition and the absolute path of the submission ledger
the task's submission procedure writes. A task root without `contest.json`
is not a leaderboard contest here, and the hook has no opinion. The ledger
is `{"submissions": [...]}`; one entry of any status is the insurance.
"""
import json
import sys
from pathlib import Path

TASK_STATEMENT = "kapso_task.md"
DATA_DIR = "kapso_datasets"
CONTEST = "contest.json"


def task_root(start: Path):
    for directory in (start, *start.parents):
        if (directory / TASK_STATEMENT).is_file():
            data = directory / DATA_DIR
            return data if data.is_dir() else None
    return None


def block(reason: str) -> None:
    print(json.dumps({"decision": "block", "reason": reason}))


def main() -> None:
    json.load(sys.stdin)
    root = task_root(Path.cwd().resolve())
    if root is None or not (root / CONTEST).is_file():
        sys.exit(0)
    contest = json.loads((root / CONTEST).read_text())
    ledger_path = Path(contest["ledger"])
    if not ledger_path.is_file():
        block(f"No submission yet: the ledger {ledger_path} does not exist. Ship the insurance submission through "
              "the task root's submission procedure before finishing (the contest-economics skill: a valid scoring "
              "submission first, then the improvement).")
        return
    ledger = json.loads(ledger_path.read_text())
    submissions = ledger.get("submissions") if isinstance(ledger, dict) else None
    if not isinstance(submissions, list) or not submissions:
        block(f"No submission yet: the ledger {ledger_path} lists none. Ship the insurance submission through the "
              "task root's submission procedure before finishing.")
        return
    sys.exit(0)


if __name__ == "__main__":
    main()
