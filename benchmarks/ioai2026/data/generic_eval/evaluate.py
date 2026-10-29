"""The IOAI task's provided evaluation: the candidate's own recorded submission.

    python kapso_evaluation/evaluate.py

Run from the repository root (the engine runs it from the candidate's
checked-out tree). It reads `kapso_datasets/contest.json` (the competition,
the ledger's absolute path, the metric's direction, the campaign window) and
the ledger the submission procedure writes; refreshes every pending entry
from the competition's submissions list (the entry's token in the message is
the attribution) and appends a newly scored entry to the shared root's
`best_score.log`; then finds this candidate's submissions by content, the
hash of its kernel source (`kernel/<code_file>`) or of its submitted file,
and reports the latest.

Outcomes are distinct results, never a zero:
    scored      the public score, oriented in the result line (exit 0)
    pending     the submission has not finished scoring: wait, run again (exit 12)
    rejected    the CLI refused the submission, or Kaggle errored it (exit 13)
    out of window   the submission predates the campaign window (exit 14)
    missing     no submission of this candidate is recorded (exit 11)
"""

import hashlib
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

CONTEST = Path("kapso_datasets") / "contest.json"
METADATA = Path("kernel") / "kernel-metadata.json"
RESULT_MARKER = "KAPSO_EVAL_MANIFEST"
BEST_SCORE_LOG = "best_score.log"
NUMBER = re.compile(r"-?\d+(\.\d+)?")
EXIT_MISSING, EXIT_PENDING, EXIT_REJECTED, EXIT_OUT_OF_WINDOW = 11, 12, 13, 14
LIST_TIMEOUT_SECONDS = 300


def parse_submissions_json(raw: str) -> list:
    """`kaggle competitions submissions --format json`, with the pagination
    noise the CLI may print before the payload; anything unparseable raises."""
    starts = [index for index in (raw.find("["), raw.find("{")) if index >= 0]
    if not starts:
        raise ValueError(f"no JSON payload in submissions output: {raw[:200]!r}")
    payload = json.loads(raw[min(starts):])
    if isinstance(payload, dict):
        payload = payload.get("submissions", [])
    if not isinstance(payload, list):
        raise ValueError("submissions payload is neither a list nor a {'submissions': [...]} object")
    return payload


def list_submissions(competition: str) -> list:
    kaggle = shutil.which("kaggle")
    if kaggle is None:
        sys.exit("the kaggle CLI is not on PATH")
    completed = subprocess.run(
        [kaggle, "competitions", "submissions", competition, "--format", "json", "-q"],
        capture_output=True, text=True, timeout=LIST_TIMEOUT_SECONDS,
    )
    if completed.returncode != 0:
        sys.exit(f"kaggle competitions submissions exited {completed.returncode}: {completed.stderr[-500:]}")
    return parse_submissions_json(completed.stdout)


def refresh(ledger: dict, rows: list, shared_root: Path) -> None:
    """Every pending entry's status, score and reference from the list, by
    its token; a newly scored entry is banked in the shared best_score.log."""
    for entry in ledger["submissions"]:
        if entry["status"] != "pending":
            continue
        token = f"[{entry['submission_id']}]"
        row = next((row for row in rows if token in str(row.get("description", ""))), None)
        if row is None:
            continue
        status = str(row.get("status", "")).lower()
        score = str(row.get("publicScore", "") or "").strip()
        entry["ref"] = row.get("ref")
        if status == "complete" and NUMBER.fullmatch(score):
            entry["status"] = "complete"
            entry["public_score"] = float(score)
            with open(shared_root / BEST_SCORE_LOG, "a", encoding="utf-8") as log:
                log.write(f"{score} {entry['submitted_at']} {entry.get('kernel_ref', '-')} {entry['message']}\n")
        elif status == "error":
            entry["status"] = "error"
            entry["output"] = str(row.get("errorDescription", ""))


def candidate_hashes() -> dict:
    """What this candidate submitted, by content: the kernel source's hash
    and the hash of every recorded file present in the tree."""
    hashes = {}
    if METADATA.is_file():
        code_file = METADATA.parent / json.loads(METADATA.read_text(encoding="utf-8"))["code_file"]
        if code_file.is_file():
            hashes["kernel_sha256"] = hashlib.sha256(code_file.read_bytes()).hexdigest()
    return hashes


def matches(entry: dict, hashes: dict) -> bool:
    if "kernel_sha256" in entry:
        return entry["kernel_sha256"] == hashes.get("kernel_sha256")
    recorded = Path(entry["file"])
    return recorded.is_file() and hashlib.sha256(recorded.read_bytes()).hexdigest() == entry["file_sha256"]


def main() -> None:
    settings = json.loads(CONTEST.read_text(encoding="utf-8"))
    ledger_path = Path(settings["ledger"])
    if not ledger_path.is_file():
        print(f"[evaluate] missing: the ledger {ledger_path} does not exist; no submission is recorded")
        sys.exit(EXIT_MISSING)
    ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
    if any(entry["status"] == "pending" for entry in ledger["submissions"]):
        refresh(ledger, list_submissions(settings["competition"]), Path(settings["shared_root"]))
        ledger_path.write_text(json.dumps(ledger, indent=2) + "\n")
    mine = [entry for entry in ledger["submissions"] if matches(entry, candidate_hashes())]
    if not mine:
        print("[evaluate] missing: no submission of this candidate (its kernel source or its file) is in the ledger; "
              "submit through kapso_datasets/submit.py")
        sys.exit(EXIT_MISSING)
    latest = max(mine, key=lambda entry: entry["submitted_at"])
    print(f"[evaluate] latest submission {latest['submission_id']} at {latest['submitted_at']}: {latest['message']}")
    if latest["submitted_at"] < settings["window_start"]:
        print(f"[evaluate] out of window: submitted before the campaign started ({settings['window_start']})")
        sys.exit(EXIT_OUT_OF_WINDOW)
    if latest["status"] in ("rejected", "error"):
        print(f"[evaluate] rejected: {latest['status']} — {latest.get('output', '')}")
        sys.exit(EXIT_REJECTED)
    if latest["status"] != "complete":
        print("[evaluate] pending: the submission has not finished scoring; wait and run the evaluation again")
        sys.exit(EXIT_PENDING)
    higher = bool(settings["higher_is_better"])
    raw = float(latest["public_score"])
    print(f"[evaluate] PUBLIC SCORE: {raw} ({'higher' if higher else 'lower'} is better)")
    print(f"{RESULT_MARKER} " + json.dumps({
        "score": raw if higher else -raw, "raw_score": raw, "higher_is_better": higher,
        "submission_id": latest["submission_id"], "ref": latest.get("ref"), "submitted_at": latest["submitted_at"],
    }))


if __name__ == "__main__":
    main()
