"""PreToolUse hook on the shell tool: deny commands that fetch from the web.

The data a candidate reads is the prepared copy and the task's data
reference, so every attempt sees the same rows and nothing dated after a
cutoff can slip in through a download. What the task grants beyond that (a
model hub, a hosted model API) is reached through the library or the API,
not through a shell fetch. Where it applies is the manifest's decision:
implementation and verification list it; setup does not, so the hub can be
read there.
"""
import json
import re
import sys

FETCHERS = re.compile(r"(^|[;&|\s])(curl|wget|aria2c)\s")

event = json.load(sys.stdin)
command = event.get("tool_input", {}).get("command", "")
if not FETCHERS.search(command):
    sys.exit(0)
print(json.dumps({
    "hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "deny",
        "permissionDecisionReason": (
            "Web fetches are off in implementation and verification: the data is the "
            "prepared copy and the task's data reference, so attempts stay comparable "
            "and nothing after a cutoff slips in. What the task grants (a hub, a hosted "
            "model API) is reached through the library or the API, as the task statement says."
        ),
    }
}))
