# Trading guardrails (every module)

Read the task statement before anything else: instruments, bar frequency, the
cost and slippage model, the evaluation command and what it measures, the
development and out-of-sample windows, position and leverage limits. The task's
numbers win over anything written here.

## Standing rules

- A signal at time t uses only data stamped at or before t. A position decided
  at t earns from t+1. Fills happen no earlier than the next bar, at the price
  the task's cost model specifies.
- Every price comes from the pinned snapshot through the market-data server.
  No live fetches inside a run.
- If the task names an out-of-sample window, nothing but the registered
  evaluation reads it. Parameter choices come from the development window.
- Report risk in the task's units beside any return metric. A strategy without
  a risk line is unfinished.
- Keep the repository's stack and conventions. Add a library only when the
  implementation page says it helps and the repository has no equivalent.
