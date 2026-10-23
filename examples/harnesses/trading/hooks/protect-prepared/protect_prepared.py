"""PreToolUse hook on the file tools: prepared resources are read-only.

The pinned snapshot under prepared/ is what makes attempts comparable. A
session that wants derived data writes it somewhere else. The engine's
permissions are the real boundary; this hook catches the slip through the
file tools and tells the model why.
"""
import json
import sys
from pathlib import Path

PREPARED = Path.cwd() / "prepared"

event = json.load(sys.stdin)
file_path = event.get("tool_input", {}).get("file_path", "")
if not file_path:
    sys.exit(0)
target = Path.cwd().joinpath(file_path).resolve()
if target != PREPARED and PREPARED not in target.parents:
    sys.exit(0)
print(json.dumps({
    "hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "deny",
        "permissionDecisionReason": (
            f"{file_path} is under prepared/, which is read-only: the pinned snapshot is what "
            "makes attempts comparable. Write derived data under your own directory, "
            "for example features/."
        ),
    }
}))
