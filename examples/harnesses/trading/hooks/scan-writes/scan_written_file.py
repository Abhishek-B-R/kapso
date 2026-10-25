"""PostToolUse hook on the file tools: scan a written Python file for look-ahead.

Advisory, not a denial: the write has happened. The hook adds the findings to
the session's context right away, so the model fixes or justifies them while
the change is fresh instead of meeting them in verification. It uses the same
rules as the lookahead-scan skill (the hook command puts the skill's scripts
directory on PYTHONPATH), so the skill, the hook and the auditor disagree on
nothing.

Both hosts' event shapes: Claude Code's file tools carry `file_path`; the
Codex `apply_patch` tool carries the patch text in `command`, whose header
lines name the files written.
"""
import json
import re
import sys
from pathlib import Path

from rules import scan_lines

PATCH_FILE = re.compile(r"^\*\*\* (?:(?:Add|Update) File|Move to): (.+)$", re.MULTILINE)

event = json.load(sys.stdin)
tool_input = event.get("tool_input", {})
written = [tool_input["file_path"]] if tool_input.get("file_path") else PATCH_FILE.findall(tool_input.get("command", ""))
findings = []
for file_path in written:
    path = Path(file_path)
    if path.suffix != ".py" or not path.is_file():
        continue
    lines = path.read_text(encoding="utf-8").splitlines()
    findings.extend(scan_lines((f"{file_path}:{number}", text) for number, text in enumerate(lines, 1)))
if not findings:
    sys.exit(0)
notes = "; ".join(f"{f['where']}: {f['rule']} ({f['line']})" for f in findings)
context = (
    f"lookahead-scan found {len(findings)} pattern(s) in the file you just wrote: {notes}. "
    "Fix each one, or write in the attempt notes why it is safe; verification treats an "
    "unjustified finding as evidence against the attempt."
)
print(json.dumps({"hookSpecificOutput": {"hookEventName": "PostToolUse", "additionalContext": context}}))
