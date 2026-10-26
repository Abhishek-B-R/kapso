"""PreToolUse hook on the file tools: the harness directory is read-only
in every session that mounts a harness.

The engine merges this hook first into every harness session's hooks
file, on both hosts (docs/plans/redesign/wp4-config.md, change 10). The
harness root is the session's `KAPSO_HARNESS_ROOT`, which the staging
sets. Both hosts' event shapes, as the trading example's protect-prepared
hook: Claude Code's file tools carry `file_path`; Codex's `apply_patch`
carries the patch text in `command`, whose header lines name the files.
Paths are resolved on both sides. A shell write is not caught here: the
hash check at the next staging catches it, by name.
"""
import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(os.environ["KAPSO_HARNESS_ROOT"]).resolve()
PATCH_FILE = re.compile(r"^\*\*\* (?:(?:Add|Update|Delete) File|Move to): (.+)$", re.MULTILINE)

event = json.load(sys.stdin)
tool_input = event.get("tool_input", {})
paths = [tool_input["file_path"]] if tool_input.get("file_path") else PATCH_FILE.findall(tool_input.get("command", ""))
touched = [
    path for path in paths
    if (target := Path.cwd().joinpath(path).resolve()) == ROOT or ROOT in target.parents
]
if not touched:
    sys.exit(0)
print(json.dumps({
    "hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "deny",
        "permissionDecisionReason": (
            f"{', '.join(touched)} is under the harness directory ({ROOT}), which is read-only in "
            "every session: fix the environment or your own files, never the harness. A harness "
            "that needs a change is reported in your final response, for its author."
        ),
    }
}))
