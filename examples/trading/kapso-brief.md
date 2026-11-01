Objective    Raise the strategy's out-of-sample Sharpe above 1.0 on the 2024
             window without breaking the signal contract: strategy.py keeps
             a signal(bars) function that returns the position to hold per
             bar, in [-1, 1], from that bar and the ones before it.
Measured by  kapso_evaluation/evaluate.py: the annualised Sharpe of the
             equal-weight portfolio over 2024 after 5 basis points per unit
             of turnover, with the risk line (max drawdown, annual turnover)
             printed beside it
Baseline     0.14 (the shipped 20/100 moving-average cross; max drawdown
             0.11, annual turnover 3.5)
Target       1.0
Rules
  - a signal at bar t uses only bars at or before t; the position decided at t earns from t+1
  - the 2024 bars are read by the evaluation alone; develop on 2021 to 2023
  - every price comes from the pinned snapshot the setup session builds; no live fetches
  - the evaluator is never modified
Budget       minutes=75 experiments=2
Harness      ../harnesses/trading
