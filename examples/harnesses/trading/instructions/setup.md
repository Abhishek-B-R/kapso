# Setup

Prepare the run so every later session sees the same market.

1. Read the task's data reference. Build a pinned snapshot with the
   market-data skill's `snapshot` tool: one file per instrument, closed bars
   only, and a `MANIFEST.json` with the source, the range and a content hash.
2. Write the task statement: instruments, bar frequency, the cost and slippage
   model, the evaluation command and what it measures, the development and
   out-of-sample windows if the task names them, position and leverage limits,
   the budget.
3. Return the snapshot as a prepared resource named `market-data`. Do not run a
   backtest in setup.
