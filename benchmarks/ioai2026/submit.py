#!/usr/bin/env python3
"""The task root's submission procedure: submit, and record it in the ledger.

    python kapso_datasets/submit.py --kernel <owner>/<slug> --version <n> -m "<idea> local=<score>"
    python kapso_datasets/submit.py --file <path> -m "<idea> local=<score>"

Run from the repository root. It reads `kapso_datasets/contest.json` (the
competition and the ledger's absolute path), submits through the kaggle CLI,
classifies the CLI's text (the exit code carries no signal on every
version), and appends one entry to the ledger under a lock: the submission
id (a token this procedure minted and put in the message, which is how the
evaluation attributes the competition's submissions list to this entry),
the kernel reference and version with the kernel source's hash, or the
file's path and hash, the message, the time, the verdict and the CLI's
output. The entry starts `pending`; the evaluation refreshes it from the
competition's submissions list. Stdlib-only and standalone: it is staged
into every session.
"""

import argparse
import fcntl
import hashlib
import json
import secrets
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

CONTEST = Path("kapso_datasets") / "contest.json"
METADATA = "kernel-metadata.json"
TOKEN_PREFIX = "kapso-"


_CLIENT_ERROR = re.compile(r"\b(400|403) Client Error\b")
_ERROR_LINE = re.compile(r"(?m)^(?:ERROR|error):")
SUCCESS = "Successfully submitted"


def classify_submit_output(stdout: str, stderr: str) -> str:
    """One label per submit attempt from the CLI's text (its exit code
    carries no signal on every version): the success phrase is accepted; an
    HTTP client error is that rejection (the phrase, never the bare number,
    which a progress bar or the message's local score also carries); a line
    that opens with an error is a rejection; anything else is pending, to
    be settled from the submissions list by the token in the message."""
    blob = stdout + stderr
    if SUCCESS in blob:
        return "accepted"
    status = _CLIENT_ERROR.search(blob)
    if status:
        return f"rejected-{status.group(1)}"
    if _ERROR_LINE.search(blob):
        return "rejected-error"
    return "pending"


def sha256_of(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def append_entry(ledger_path: Path, entry: dict) -> None:
    """One entry appended under the ledger's lock: lanes submit concurrently."""
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = ledger_path.with_suffix(ledger_path.suffix + ".lock")
    with open(lock_path, "w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        ledger = json.loads(ledger_path.read_text()) if ledger_path.is_file() else {"submissions": []}
        ledger["submissions"].append(entry)
        ledger_path.write_text(json.dumps(ledger, indent=2) + "\n")
        fcntl.flock(lock, fcntl.LOCK_UN)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--kernel", help="the kernel reference <owner>/<slug> (a code competition)")
    parser.add_argument("--version", type=int, help="the kernel version the push printed")
    parser.add_argument("--kernel-dir", default="kernel", help="the kernel folder holding kernel-metadata.json (default: kernel)")
    parser.add_argument("--output-file", default="submission.csv", help="the output file the kernel writes (a code competition)")
    parser.add_argument("--file", help="the prediction file to upload (a file-upload competition)")
    parser.add_argument("-m", "--message", required=True, help="the idea and the local score")
    args = parser.parse_args()
    if bool(args.kernel) == bool(args.file):
        parser.error("exactly one of --kernel (with --version) or --file")
    if args.kernel and args.version is None:
        parser.error("--kernel needs --version, the integer the push printed")

    settings = json.loads(CONTEST.read_text(encoding="utf-8"))
    competition, ledger_path = settings["competition"], Path(settings["ledger"])
    kaggle = shutil.which("kaggle")
    if kaggle is None:
        sys.exit("the kaggle CLI is not on PATH")
    token = TOKEN_PREFIX + secrets.token_hex(4)
    message = f"{args.message} [{token}]"
    entry = {
        "competition": competition,
        "submission_id": token,
        "message": message,
        "submitted_at": datetime.now(timezone.utc).isoformat(),
        "status": "pending",
        "public_score": None,
        "ref": None,
    }
    if args.kernel:
        metadata = json.loads((Path(args.kernel_dir) / METADATA).read_text(encoding="utf-8"))
        code_file = Path(args.kernel_dir) / metadata["code_file"]
        entry.update({"kernel_ref": args.kernel, "version": args.version, "code_file": str(code_file),
                      "kernel_sha256": sha256_of(code_file)})
        command = [kaggle, "competitions", "submit", competition, "-k", args.kernel, "-v", str(args.version),
                   "-f", args.output_file, "-m", message]
    else:
        file_path = Path(args.file)
        entry.update({"file": str(file_path), "file_sha256": sha256_of(file_path)})
        command = [kaggle, "competitions", "submit", competition, "-f", str(file_path), "-m", message]
    completed = subprocess.run(command, capture_output=True, text=True)
    verdict = classify_submit_output(completed.stdout, completed.stderr)
    entry["verdict"] = verdict
    entry["output"] = (completed.stdout + completed.stderr).strip()
    rejected = verdict.startswith("rejected")
    if rejected:
        entry["status"] = "rejected"
    append_entry(ledger_path, entry)
    print(json.dumps(entry, indent=2))
    if rejected:
        sys.exit(2)


if __name__ == "__main__":
    main()
