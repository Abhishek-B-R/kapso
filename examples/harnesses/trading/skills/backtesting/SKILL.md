---
name: backtesting
description: Build and run a backtest with timestamp discipline, then read its output. Use when implementing a strategy, running the task's evaluation, or checking signal timing, fills and costs.
---
# Backtesting

## The reference pattern

A bar-based strategy is three frames and one shift:

```python
bars = load_bars(...)                      # one row per bar, timestamp ascending, closed bars only
signal = make_signal(bars)                 # uses rows at or before each timestamp, nothing later
position = signal.shift(1)                 # the position held during bar t was decided at t-1
pnl = position * bars["close"].pct_change() - costs(position.diff().abs())
```

The shift is the whole discipline: a signal computed at the close of bar t can
only earn the return of bar t+1. Costs are charged on turnover, with the rates
from the task statement.

## Running the task's evaluation

The evaluation command is in the task statement. Run it unchanged, from the
repository root, once the logic is settled. It is the only run that may read
the out-of-sample window. Develop on the development window with a subsample
(one instrument, one year) until the pipeline is correct, then the full window.

## Reading the output

- Count trades. Fewer than a few hundred over the window means the statistics
  are noise; say so.
- A Sharpe far above the asset class's history, no losing months, or a
  turnover the cost model should have punished are bugs until shown otherwise.
- Report the risk line beside the return line: max drawdown, average gross
  exposure, annual turnover. The risk-limits skill has the definitions.
- Save the equity curve as `results/equity_curve.csv` and the trade log as
  `results/trades.csv`; the reviewers read them, and an implementation
  session is asked to finish them before it ends.
