"""SessionStart hook: tell the session which market it is working on.

Reads the pinned snapshot's MANIFEST.json from the session workspace and adds
a two-line brief to the session's context. Before setup has built the
snapshot there is nothing to say, and the hook says nothing.
"""
import json
import sys
from pathlib import Path

MANIFEST = Path("prepared/market-data/MANIFEST.json")

event = json.load(sys.stdin)
if not MANIFEST.is_file():
    sys.exit(0)
manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
brief = (
    f"Pinned market data: {', '.join(manifest['instruments'])}, bars from {manifest['start']} "
    f"to {manifest['end']}, snapshot {manifest['sha256'][:12]}. Every price in this run comes "
    "from this snapshot through the market-data server; never fetch prices elsewhere."
)
print(json.dumps({"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": brief}}))
