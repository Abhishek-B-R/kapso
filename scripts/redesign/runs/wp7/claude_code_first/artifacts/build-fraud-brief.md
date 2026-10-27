Objective    Build a fraud scorer for data/transactions.csv that beats the
             rule-based score.py, and prove it, keeping the contract:
             score.py takes --data and --out and writes id,fraud_probability
             for every row, in input order.
Measured by  kapso_evaluation/evaluate.py, run from the workspace root: calls
             score.py on a private 20 percent hold-out (stratified on fraud,
             seed 7, 4,000 rows, 182 frauds), prints precision-recall AUC
             (average precision) as the last line "pr_auc: <value>", and
             "beats_rules: True" when the 95 percent paired bootstrap of the
             difference against the shipped rules lies above zero.
Baseline     0.0939 (the shipped three rules, on the hold-out)
Target       pr_auc above 0.50 with beats_rules: True (an untuned gradient
             boosting model scores 0.534 with interval +0.36 to +0.52 over the rules)
Rules
  - fit only on kapso_datasets/transactions.csv, the 80 percent split
  - the hold-out is never fitted on, read, or inspected
  - every transaction gets a score; none is dropped
  - the evaluator is never modified
Budget       minutes=10 experiments=1
