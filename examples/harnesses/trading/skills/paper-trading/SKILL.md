---
name: paper-trading
description: "The paper-trading deployment workflow: runs the selected strategy against the broker server's paper account on the pinned market-data feed, as a scheduled runner. Use when deploy() names the paper-trading target."
---
# Paper trading

## What the deployment session has

The solution's repository path, its artifacts (the strategy module, its
parameters, the equity curve), and the options of the `deploy()` call:
`schedule` (a cron expression; default every bar close) and `cash` (starting
cash; default the broker's).

## Steps

1. Read the strategy's entry point from the solution: a `signal(bars)` function
   returning target weights, or adapt the repository's equivalent into one.
2. Write `deploy/run_paper.py`. On each run it pulls the latest closed bars
   from the market-data store (`read_frame` and `instrument_file` from
   `$KAPSO_HARNESS_ROOT/servers/market_data.py`), computes the target weights,
   and moves the paper account to them with `PaperAccount.place_order` from
   `$KAPSO_HARNESS_ROOT/servers/broker.py`. Fills happen at the last close, the
   same convention as the backtest.
3. Schedule it with the `schedule` option (cron, or a background loop for
   continuous markets) and run one cycle to prove it.
4. Report the result as the engine's deployment result: the target name, the
   runner's log path as the endpoint, the artifacts written
   (`deploy/run_paper.py`, `paper_account.json`), and a summary. This workflow
   has no live mode; never connect a real account from it.
