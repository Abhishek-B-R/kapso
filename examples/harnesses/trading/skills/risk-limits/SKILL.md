---
name: risk-limits
description: Compute and report the standard risk line (max drawdown, gross exposure, turnover, worst month) and check it against the task's limits. Use when finishing an attempt or scoring one.
---
# Risk limits

The limits are the task's; read them from the task statement. This skill fixes
the definitions so every attempt reports the same numbers.

- Max drawdown: the largest peak-to-trough fall of the equity curve, as a
  fraction of the peak, over the whole window.
- Gross exposure: the sum of absolute position weights, averaged over bars.
- Annual turnover: the sum of absolute weight changes per year.
- Worst month: the lowest calendar-month return.

The risk line, in this order, beside the return metric:

```
sharpe 1.62 | max_dd 14.8% | gross 0.95 | turnover 11.2x | worst_month -6.1%
```

An attempt without a risk line is unfinished. A number outside the task's limit
is reported as a finding with the limit it breaks, not softened.
