Objective    Raise the churn model's out-of-sample ROC AUC above 0.85
             without changing the prediction contract: predict.py keeps
             writing id,churn_probability for every holdout id.
Measured by  kapso_evaluation/evaluate.py, ROC AUC on the 3,000 held-out rows
             (last line `auc: X`); --fast scores are smoke checks only
Baseline     0.7974 (the shipped logistic regression, bootstrap SE 0.010)
Target       0.85
Rules
  - the evaluator is never modified
  - no fitting on the holdout rows; the labels are not in the workspace
  - `python predict.py --data kapso_datasets --out predictions.csv` and its
    two-column output stay exactly as they are
Budget       minutes=30 experiments=3
