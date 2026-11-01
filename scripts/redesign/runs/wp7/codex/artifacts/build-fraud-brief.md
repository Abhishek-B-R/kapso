Objective    Build a fraud scorer on data/transactions.csv that beats the rule-based one in score.py, and prove it.
             Achieve held-out average precision above 0.50 and above the measured rule baseline 0.0939496813,
             preserving python score.py --data <directory> --out <csv> and id,fraud_probability in input order.
Measured by  python kapso_evaluation/evaluate.py; full pr_auc is sklearn average_precision_score.
             Protected evaluation/private/holdout.csv contains 4,000 held-out labelled rows from the original
             20,000-row data, stratified 80/20 with seed 7. The evaluator supplies unlabelled transactions
             to score.py in a temporary --data directory. Fit using kapso_datasets/transactions.csv only
             (16,000 labelled training rows); persist any trained artifacts needed for scoring arbitrary inputs.
Baseline     0.0939496813 average precision, measured on the fixed 4,000-row holdout with repo/score.py.
Target       pr_auc > 0.50, the existing repository brief's proposed target, and strictly above baseline.
Rules
  - Never modify the protected evaluator or its private data.
  - Never inspect private holdout data or labels, fit on them, or access the original unsplit source data.
  - Use only training rows for fitting and model selection; exclude id as a model feature.
  - Preserve the CLI contract; score every supplied transaction exactly once in input order.
  - Probabilities must be finite and within [0,1].
  - --fast is a smoke check only; its score cannot establish success.
  - Report full evaluation evidence and comparison to baseline; do not claim future-time or unseen-card generalization.
Budget       minutes=10 experiments=1
