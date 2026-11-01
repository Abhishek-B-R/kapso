"""PreToolUse hook on the shell tool: a raw contest submission typed in the
shell is denied where the task root names a submission procedure.

A submission spends shared quota and must leave a record in the ledger;
where `kapso_datasets/contest.json` (beside the nearest task statement at
or above the session's directory that has one) names a `procedure`, that
procedure submits and records, and the raw command records nothing.
Without a procedure the command is the way to submit (the kaggle-cli skill
says what to record), and the hook has no opinion. It is an
accidental-bypass guard on the command's common spellings (a path to the
binary, the short alias, a line continuation, the Python API's call), not
a security boundary: arbitrary shell access cannot be secured by a
pattern, and the quota is enforced by the procedure and read by the
verifier. Pushes, status polls, downloads and the submissions listing are
not touched. A corrupt descriptor fails loud, and the launcher line in
hook.json turns that into a blocking exit (code 2).
"""
import json
import re
import sys
from pathlib import Path

TASK_STATEMENT = "kapso_task.md"
DATA_DIR = "kapso_datasets"
CONTEST = "contest.json"
RAW_SUBMIT = re.compile(r"(^|[;&|(\s])[\w./~-]*kaggle\s+(competitions|c)\s+(\\\s*)?submit\b|\bcompetition_submit\s*\(")


def task_root(start: Path):
    """The data directory beside the nearest task statement at or above `start` that has one, or None."""
    for directory in (start, *start.parents):
        if (directory / TASK_STATEMENT).is_file() and (directory / DATA_DIR).is_dir():
            return directory / DATA_DIR
    return None


event = json.load(sys.stdin)
command = event.get("tool_input", {}).get("command", "") if isinstance(event, dict) else ""
if not isinstance(command, str) or not RAW_SUBMIT.search(command):
    sys.exit(0)
root = task_root(Path.cwd().resolve())
if root is None or not (root / CONTEST).is_file():
    sys.exit(0)
contest = json.loads((root / CONTEST).read_text())  # a corrupt contest.json fails loud here
procedure = contest.get("procedure") if isinstance(contest, dict) else None
if not isinstance(procedure, str) or not procedure:
    sys.exit(0)
print(json.dumps({
    "hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "deny",
        "permissionDecisionReason": (
            "A raw `kaggle competitions submit` is off on this task: a submission spends shared quota and must "
            "leave its version, id, message and score in the ledger the verifier reads. Submit through the task "
            f"root's procedure, `{procedure}`, which submits and records."
        ),
    }
}))
