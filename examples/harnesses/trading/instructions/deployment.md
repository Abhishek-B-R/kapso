# Deployment

The target comes from the `deploy()` call or the Kapso config, never from this
harness. For the paper-trading target follow the paper-trading skill; for the
engine's own targets (local, docker, ...) follow the engine's workflow.

Deployment never touches a live account. The paper-trading workflow runs the
selected strategy against the broker server's paper account on the same
market-data feed the backtest used, so a divergence between paper and backtest
means a bug, not a market. Keep the deployed strategy's data access on the
market-data store (the market-data skill), and return the runner's log path as
the endpoint.
