"""PreToolUse hook on the native web tools: no web in implementation and
verification.

A candidate's data is the task's data and the sanitized copy; what the
task grants beyond them (a hub, a hosted model API, external data) was
fetched in setup and lives under prepared/. The engine's `implementation.web`
switch is the permission boundary (the tools off the allow-list and
disallowed on Claude Code, `--search` off on Codex); this hook is the
harness's own rule, so a config that leaves the switch on still meets the
denial with its reason. Codex's native web search is not a tool call its
hooks see: there the switch alone holds. Where it applies is the
manifest's decision.
"""
import json
import sys

event = json.load(sys.stdin)
print(json.dumps({
    "hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "deny",
        "permissionDecisionReason": (
            f"{event.get('tool_name', 'The web')} is off in implementation and verification: a "
            "candidate reads the task's data and the sanitized copy, and what the task granted "
            "was fetched in setup under prepared/. The practices and the libraries' traps are in "
            "the skills."
        ),
    }
}))
