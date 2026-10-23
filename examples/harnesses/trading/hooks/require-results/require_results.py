"""Stop hook: an implementation session does not end without its results.

The backtesting skill says every attempt saves results/equity_curve.csv and
results/trades.csv; the reviewers read them. When the session tries to stop
without them, the hook asks for one more pass with the reason. It asks once:
when the CLI reports that the session is already continuing because of a stop
hook, the hook lets it end, so a session that truly cannot produce results is
not trapped. The manifest lists it on implementation only.
"""
import json
import sys
from pathlib import Path

REQUIRED = ("results/equity_curve.csv", "results/trades.csv")

event = json.load(sys.stdin)
if event.get("stop_hook_active"):
    sys.exit(0)
missing = [name for name in REQUIRED if not Path(name).is_file()]
if not missing:
    sys.exit(0)
print(json.dumps({
    "decision": "block",
    "reason": (
        f"The attempt is unfinished: {', '.join(missing)} not saved. Run the evaluation or "
        "the backtest that produces them (the backtesting skill says how), save them, then "
        "finish. If the attempt failed before any backtest ran, say so in the attempt notes "
        "and finish."
    ),
}))
