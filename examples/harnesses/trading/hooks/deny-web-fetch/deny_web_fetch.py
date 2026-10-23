"""PreToolUse hook on the shell tool: deny commands that fetch from the web.

Market data comes from the market-data server's pinned snapshot, so every
attempt sees the same bars. A fetch from the web makes attempts incomparable
and can pull in bars from after the evaluation window. Where it applies is
the manifest's decision: every module lists it.
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
            "Web fetches are off in this harness: all market data comes from the "
            "market-data server's pinned snapshot so attempts stay comparable. "
            "Use get_bars on the market-data server."
        ),
    }
}))
