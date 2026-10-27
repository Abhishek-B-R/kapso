Objective    Replace the rule-based fraud scorer in score.py with a model that
             beats it on held-out transactions, and prove it: pr_auc above the
             rules' 0.0939 by well beyond noise, keeping the contract
             (python score.py --data <dir> --out <file> writes
             id,fraud_probability for every row, in input order).
Measured by  python kapso_evaluation/evaluate.py, average precision (pr_auc)
             on a fixed 4,000-row hold-out (stratified 20%, seed 7), printed
             as the last line "pr_auc: <value>"; the judge reads that line
Baseline     0.0939 (the three rules in score.py, bootstrap SE 0.016)
Target       pr_auc above 0.50
Rules
  - fit only on kapso_datasets/transactions.csv (the 16,000-row 80%)
  - the hold-out is never fitted on and never inspected by hand
  - every transaction gets a score; none is dropped
  - the evaluator is never modified
Budget       minutes=10 experiments=1
