"""Baseline candidate seeded into every MLE-bench campaign.

Purpose: give the evaluation maintainer's registration-time calibration a
runnable candidate, and the search a starting parent. It writes the
competition's sample submission unchanged as `final_submission.csv` and
reports the floor score the task's settings name: the worst value of the
metric's direction, which every real candidate beats. Replace me with a
real solution.
"""

import json
import shutil
import sys
from pathlib import Path

TASK_FILE = Path("kapso_evaluation") / "task.json"
SUBMISSION = Path("final_submission.csv")


def main() -> None:
    settings = json.loads(TASK_FILE.read_text(encoding="utf-8"))
    sample = Path(settings["data_dir"]) / "sample_submission.csv"
    shutil.copyfile(sample, SUBMISSION)
    print(f"[baseline] wrote {SUBMISSION} from {sample} (debug={'--debug' in sys.argv})")
    print(f"<score>{settings['floor_score']}</score>")


if __name__ == "__main__":
    main()
