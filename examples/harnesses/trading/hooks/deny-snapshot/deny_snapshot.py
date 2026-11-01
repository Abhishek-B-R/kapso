"""PreToolUse hook on one server tool: the snapshot is built once, in setup.

The matcher names the market-data server's snapshot tool. Where this applies
is the manifest's decision: implementation and deployment list it, the two
modules besides setup that mount the server; setup does not, so setup may
build the snapshot.
"""
import json
import sys

json.load(sys.stdin)
print(json.dumps({
    "hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "deny",
        "permissionDecisionReason": (
            "The market-data snapshot is built once, in setup. Rebuilding it now would change "
            "the data under every attempt in this run. Read the existing store with get_bars; "
            "if the task needs other data, say so in the attempt notes."
        ),
    }
}))
