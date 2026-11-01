"""Static look-ahead scan of a unified diff read from stdin.

    git diff main...HEAD | python scan.py

Prints the findings as JSON and exits 1 when there are any. The patterns move
future values onto the current timestamp; whether a hit is a bug is the
implementer's to justify and the verifier's to judge.
"""
import json
import sys

from rules import scan_lines


def added_lines(diff: str):
    current_file = None
    for line in diff.splitlines():
        if line.startswith("+++ "):
            current_file = line[4:].removeprefix("b/")
            continue
        if line.startswith("+"):
            yield current_file, line[1:]


findings = scan_lines(added_lines(sys.stdin.read()))
summary = f"{len(findings)} look-ahead pattern(s) in the added lines" if findings else "no look-ahead pattern in the added lines"
print(json.dumps({"summary": summary, "findings": findings}, indent=2))
sys.exit(1 if findings else 0)
