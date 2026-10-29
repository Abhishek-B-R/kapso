"""PreToolUse hook on the shell tool: a raw contest submission typed in the
shell is denied.

A submission spends shared quota and must leave a record (the kernel
version or the file's hash, the submission id, the message, the score) in
the ledger the evaluator reads; the task root's submission procedure
writes it, a raw `kaggle competitions submit` writes nothing. Pushes,
status polls, downloads and the submissions listing are not touched.
"""
import json
import re
import sys

RAW_SUBMIT = re.compile(r"(^|[;&|\s])kaggle\s+(competitions|c)\s+submit\b")

event = json.load(sys.stdin)
command = event.get("tool_input", {}).get("command", "")
if not RAW_SUBMIT.search(command):
    sys.exit(0)
print(json.dumps({
    "hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "deny",
        "permissionDecisionReason": (
            "A raw `kaggle competitions submit` is off in this harness: a submission spends shared quota and "
            "must leave its version, id, message and score in the ledger the evaluator reads. Use the "
            "submission procedure the task root provides (the task statement names it); it submits and records."
        ),
    }
}))
