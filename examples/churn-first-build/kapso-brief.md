Objective    Raise the churn model's out-of-sample ROC AUC above 0.85
             without changing the prediction contract: predict.py keeps
             writing id,churn_probability for every holdout id.
Measured by  kapso_evaluation/evaluate.py, ROC AUC on the held-out rows
Baseline     0.797 (the shipped logistic regression, bootstrap SE 0.010)
Target       0.85
Rules
  - the evaluator is never modified
  - no fitting on the holdout rows; the labels are not in the workspace
Budget       minutes=10 iterations=4
