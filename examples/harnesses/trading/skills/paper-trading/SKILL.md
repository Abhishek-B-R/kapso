---
name: paper-trading
description: "The paper-trading deployment target: runs the selected strategy against the broker server's paper account on the pinned market-data feed, as a scheduled runner, with one cycle on demand. Use when deploy() names the paper-trading target; never for a live account."
---
# Paper trading

## What the deployment session has

The solution's repository (the strategy module, its parameters, the equity
curve) in the workspace, the harness's servers under `$KAPSO_HARNESS_ROOT`,
and the options of the `deploy()` call in the environment:
`KAPSO_OPTION_SCHEDULE` (a cron expression; every bar close when unset) and
`KAPSO_OPTION_CASH` (starting cash; the broker's when unset).

## Steps

1. Read the strategy's entry point from the solution: a `signal(bars)`
   function returning target weights, or adapt the repository's equivalent
   into one.
2. Write `deploy/run_paper.py`, the runner the target's scripts drive:
   - `run_paper.py --once` runs one cycle: pulls the latest closed bars from
     the market-data store (`read_frame` and `instrument_file` from
     `$KAPSO_HARNESS_ROOT/servers/market_data.py`), computes the target
     weights, moves the paper account to them with `PaperAccount.place_order`
     from `$KAPSO_HARNESS_ROOT/servers/broker.py` (fills at the last close,
     the backtest's convention), keeps the account state in
     `paper_account.json` across cycles so a bar already traded is never
     traded twice, and prints one JSON document: the bar it acted on, the
     orders placed, the account's equity.
   - `run_paper.py --loop` runs a cycle at each tick of the schedule
     (`KAPSO_OPTION_SCHEDULE`) until it is ended, logging each cycle's
     document on one line.
   Both read the starting cash from `KAPSO_OPTION_CASH` when it is set.
3. Run `bash "$KAPSO_TARGET_DIR/scripts/deploy.sh"`: it starts the loop in
   the background (its pid in `deploy/paper.pid`, its log in
   `deploy/paper.log`) and checks it is alive. Then prove one cycle:

   ```bash
   echo '{}' | "$KAPSO_INTERPRETER" "$KAPSO_TARGET_DIR/scripts/run.py"
   ```

4. Write the result file: `endpoint` the log's path (`deploy/paper.log`),
   `run` as `{"kind": "script"}` (a call runs one cycle on demand), no
   `values`, the artifacts (`deploy/run_paper.py`, `paper_account.json`),
   and the proof cycle's inputs (`{}`) and output.

## Never

This target has no live mode: never connect a real account from it. Keep
the strategy's data access on the market-data store (the market-data
skill).
