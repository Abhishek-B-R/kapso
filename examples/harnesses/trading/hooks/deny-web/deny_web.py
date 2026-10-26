"""PreToolUse hook on the native web tools: no web in implementation.

The evaluation window's future exists on the web, and a strategy built
with it is not a strategy. The engine's `implementation.web` switch is the
permission boundary (the tools off the allow-list and disallowed on Claude
Code, `--search` off on Codex); this hook is the harness's own rule, so a
config that leaves the switch on still meets the denial with its reason.
Codex's native web search is not a tool call its hooks see: there the
switch alone holds. Where it applies is the manifest's decision.
"""
import json
import sys

event = json.load(sys.stdin)
print(json.dumps({
    "hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "deny",
        "permissionDecisionReason": (
            f"{event.get('tool_name', 'The web')} is off in implementation: the evaluation "
            "window's future exists on the web. Market data comes from the market-data "
            "server's pinned snapshot (get_bars); the strategy families and the market "
            "structure are in the skills."
        ),
    }
}))
