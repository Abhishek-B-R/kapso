"""The IOAI task's provided evaluation: the candidate's own recorded submission.

    python kapso_evaluation/evaluate.py

Run from the repository root (the engine runs it from the candidate's
checked-out tree). It reads `kapso_datasets/contest.json` (the competition,
the ledger's absolute path, the metric's direction, the campaign window,
the listing's page size and timeout) and the ledger the submission
procedure writes; refreshes every pending entry from the competition's
submissions list, every page of it (the entry's token in the message is
the attribution), merged into the ledger as it is on disk under the
procedure's lock, and appends a newly scored entry to the shared root's
`best_score.log`; then finds this candidate's submissions by content, the
hash of the repository-relative file the procedure recorded (its kernel
source or its uploaded file), and reports the latest.

Outcomes are distinct results, never a zero:
    scored      the public score, oriented in the result line (exit 0)
    pending     the submission has not finished scoring: wait, run again (exit 12)
    rejected    the CLI refused the submission, or Kaggle errored it (exit 13)
    out of window   the submission falls outside the campaign window (exit 14)
    missing     no submission of this candidate is recorded (exit 11)
"""

import fcntl
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

CONTEST = Path("kapso_datasets") / "contest.json"
RESULT_MARKER = "KAPSO_EVAL_MANIFEST"
BEST_SCORE_LOG = "best_score.log"
NUMBER = re.compile(r"-?\d+(\.\d+)?")
NEXT_PAGE = re.compile(r"Next Page Token\s*=\s*(\S+)")
NO_SUBMISSIONS = "No submissions found"
EXIT_MISSING, EXIT_PENDING, EXIT_REJECTED, EXIT_OUT_OF_WINDOW = 11, 12, 13, 14


def normalize_status(raw) -> str:
    """The CLI prints its enum's repr (`SubmissionStatus.COMPLETE`); the
    bare word, lowercased, is the vocabulary: complete, error, pending."""
    return str(raw or "").rsplit(".", 1)[-1].strip().lower()


def parse_submissions_page(raw: str) -> tuple:
    """One page of `kaggle competitions submissions --format json`: the rows
    and the next page's token (None on the last page). The CLI prints the
    token line beside the payload, and a competition with no submission
    prints a sentence, not JSON; anything else unparseable raises."""
    starts = [index for index in (raw.find("["), raw.find("{")) if index >= 0]
    if not starts:
        if NO_SUBMISSIONS in raw:
            return [], None
        raise ValueError(f"no JSON payload in submissions output: {raw!r}")
    start = min(starts)
    payload, end = json.JSONDecoder().raw_decode(raw[start:])
    if isinstance(payload, dict):
        payload = payload.get("submissions", [])
    if not isinstance(payload, list):
        raise ValueError("submissions payload is neither a list nor a {'submissions': [...]} object")
    token = NEXT_PAGE.search(raw[:start] + raw[start + end:])
    return payload, (token.group(1) if token else None)


def list_submissions(kaggle: str, competition: str, page_size: int, timeout_seconds: int) -> list:
    """Every submission of the competition, page by page: the CLI's default
    page holds twenty rows, which a campaign's history outgrows."""
    rows, token, seen = [], None, set()
    while True:
        command = [kaggle, "competitions", "submissions", competition, "--format", "json", "-q",
                   "--page-size", str(page_size)]
        if token:
            command += ["--page-token", token]
        completed = subprocess.run(command, capture_output=True, text=True, timeout=timeout_seconds)
        if completed.returncode != 0:
            raise RuntimeError(f"kaggle competitions submissions exited {completed.returncode}: {completed.stderr}")
        page, token = parse_submissions_page(completed.stdout)
        rows.extend(page)
        if not token:
            return rows
        if token in seen:
            raise RuntimeError(f"kaggle competitions submissions repeats the page token {token}")
        seen.add(token)


def refresh(ledger: dict, rows: list, shared_root: Path) -> None:
    """Every pending entry's status, score and reference from the list, by
    its token; a newly scored entry is stamped with the time the score was
    observed and banked in the shared best_score.log."""
    for entry in ledger["submissions"]:
        if entry["status"] != "pending":
            continue
        token = f"[{entry['submission_id']}]"
        row = next((row for row in rows if token in str(row.get("description", ""))), None)
        if row is None:
            continue
        status = normalize_status(row.get("status"))
        score = str(row.get("publicScore", "") or "").strip()
        entry["ref"] = row.get("ref")
        if status == "complete" and NUMBER.fullmatch(score):
            entry["status"] = "complete"
            entry["public_score"] = float(score)
            entry["scored_at"] = datetime.now(timezone.utc).isoformat()
            with open(shared_root / BEST_SCORE_LOG, "a", encoding="utf-8") as log:
                log.write(f"{score} {entry['submitted_at']} {entry.get('kernel_ref', '-')} {entry['message']}\n")
        elif status == "error":
            entry["status"] = "error"
            entry["output"] = str(row.get("errorDescription", ""))


def write_ledger(ledger_path: Path, ledger: dict) -> None:
    """Written whole and swapped in: a reader (a hook, another lane's
    evaluation) never sees a partial file."""
    staging = ledger_path.with_name(ledger_path.name + ".tmp")
    staging.write_text(json.dumps(ledger, indent=2) + "\n", encoding="utf-8")
    os.replace(staging, ledger_path)


def refresh_ledger(ledger_path: Path, rows: list, shared_root: Path) -> dict:
    """The refresh applied to the ledger as it is on disk at merge time,
    under the procedure's lock: the listing ran outside it, and an entry a
    lane appended meanwhile is kept, not overwritten."""
    with open(ledger_path.with_suffix(ledger_path.suffix + ".lock"), "w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
        refresh(ledger, rows, shared_root)
        write_ledger(ledger_path, ledger)
        fcntl.flock(lock, fcntl.LOCK_UN)
    return ledger


def matches(entry: dict) -> bool:
    """This candidate's, by content: the repository-relative file the
    procedure recorded (the kernel source, or the uploaded file) hashes in
    this tree to the hash recorded at submit time."""
    if "kernel_sha256" in entry:
        recorded, digest = entry["code_file"], entry["kernel_sha256"]
    else:
        recorded, digest = entry["file"], entry["file_sha256"]
    path = Path(recorded)
    return not path.is_absolute() and path.is_file() and hashlib.sha256(path.read_bytes()).hexdigest() == digest


def main() -> None:
    settings = json.loads(CONTEST.read_text(encoding="utf-8"))
    ledger_path = Path(settings["ledger"])
    if not ledger_path.is_file():
        print(f"[evaluate] missing: the ledger {ledger_path} does not exist; no submission is recorded")
        sys.exit(EXIT_MISSING)
    ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
    if any(entry["status"] == "pending" for entry in ledger["submissions"]):
        kaggle = shutil.which("kaggle")
        if kaggle is None:
            sys.exit("the kaggle CLI is not on PATH")
        rows = list_submissions(kaggle, settings["competition"], int(settings["list_page_size"]),
                                int(settings["list_timeout_seconds"]))
        ledger = refresh_ledger(ledger_path, rows, Path(settings["shared_root"]))
    mine = [entry for entry in ledger["submissions"] if matches(entry)]
    if not mine:
        print("[evaluate] missing: no submission of this candidate (its kernel source or its file) is in the ledger; "
              "submit through kapso_datasets/submit.py")
        sys.exit(EXIT_MISSING)
    latest = max(mine, key=lambda entry: entry["submitted_at"])
    print(f"[evaluate] latest submission {latest['submission_id']} at {latest['submitted_at']}: {latest['message']}")
    submitted = datetime.fromisoformat(latest["submitted_at"])
    window = (datetime.fromisoformat(settings["window_start"]), datetime.fromisoformat(settings["window_end"]))
    if not window[0] <= submitted <= window[1]:
        print(f"[evaluate] out of window: submitted outside the campaign window "
              f"({settings['window_start']} to {settings['window_end']})")
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
        "scored_at": latest["scored_at"],
    }))


if __name__ == "__main__":
    main()
