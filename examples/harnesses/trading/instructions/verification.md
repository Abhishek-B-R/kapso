# Verification

Keep the evaluation honest. Do these on every attempt, in this order:

1. Run the lookahead-scan skill's script on the final diff. A finding the
   attempt notes do not justify is evidence against the attempt.
2. Ask the lookahead-auditor for the judgment a pattern cannot make. Give it
   the task statement, the diff and the evaluation output.
3. Decide validity. A look-ahead or leakage finding with evidence voids the
   attempt; say so in the verdict with the evidence. Otherwise register the
   measurement.

What look-ahead looks like: backward shifts, centred windows, joins on a future
timestamp, resampling that closes a bar before its last trade, features built
from the whole series, indicators fitted on the full window.

What leakage looks like: any read of the out-of-sample window outside the
evaluation command, test data in a cache, labels used as features, a parameter
chosen by looking at the evaluation output.

What impossible numbers look like: a Sharpe far above the asset class's
history, no losing months, turnover the cost model should have punished, a
trade count too small for the statistics. Treat them as evidence of a bug until
shown otherwise. The backtesting skill says how to read the output.
