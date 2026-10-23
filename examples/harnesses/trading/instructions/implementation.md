# Implementation

Build the chosen idea on the branch and run the task's evaluation.

- Timestamp discipline first: compute signals from a frame that stops at t,
  then shift the position by one bar. The backtesting skill has the reference
  pattern and how to read the output.
- Prices come from the market-data skill's tools, never from a file you
  fetched. Costs and slippage come from the task statement; never hard-code a
  fee.
- Develop on a subsample of the development window (one instrument, one year)
  until the pipeline is correct, then run the full evaluation once. Do not
  sweep parameters against the evaluation output.
- Before launching the evaluation, run the lookahead-scan skill's script on
  your diff. Fix every finding, or write in the attempt notes why it is safe.
  When the change touches signal timing, joins across sources or resampling,
  also ask the lookahead-auditor; its report is cheaper than a voided attempt.
- Finish with the risk line from the risk-limits skill beside the return
  metric, and save `results/equity_curve.csv` and `results/trades.csv` with
  the attempt.
