"""PreToolUse hook on the file tools: prepared resources are read-only.

The pinned snapshot under prepared/ is what makes attempts comparable. A
session that wants derived data writes it somewhere else. The engine's
permissions are the real boundary; this hook catches the slip through the
file tools and tells the model why.

Both hosts' event shapes: Claude Code's file tools carry `file_path`; the
Codex `apply_patch` tool carries the patch text in `command`, whose header
lines name the files. Paths are resolved on both sides, so a `prepared`
that is a symlink into the campaign still matches.
"""
import json
import re
import sys
from pathlib import Path

PREPARED = (Path.cwd() / "prepared").resolve()
PATCH_FILE = re.compile(r"^\*\*\* (?:Add|Update|Delete|Move to) File: (.+)$", re.MULTILINE)

event = json.load(sys.stdin)
tool_input = event.get("tool_input", {})
paths = [tool_input["file_path"]] if tool_input.get("file_path") else PATCH_FILE.findall(tool_input.get("command", ""))
touched = [
    path for path in paths
    if (target := Path.cwd().joinpath(path).resolve()) == PREPARED or PREPARED in target.parents
]
if not touched:
    sys.exit(0)
print(json.dumps({
    "hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "deny",
        "permissionDecisionReason": (
            f"{', '.join(touched)} is under prepared/, which is read-only: the pinned snapshot is what "
            "makes attempts comparable. Write derived data under your own directory, "
            "for example features/."
        ),
    }
}))
