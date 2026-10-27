Objective    Raise the churn model's out-of-sample ROC AUC above 0.85
             without changing the prediction contract: predict.py keeps
             writing id,churn_probability for every holdout id.
Measured by  kapso_evaluation/evaluate.py, ROC AUC on the held-out rows
Baseline     0.7974 (recorded in baseline.json, bootstrap SE 0.0101;
             not rerun because enrichment must be fetched before training)
Target       0.85
Rules
  - the evaluator is never modified
  - no fitting on the holdout rows; the labels are not in the workspace
  - before training, the enrichment table must be fetched from the enrichment service with the DATA_API_KEY in .env, and a session that lacks the key asks for it through the inbox.
  - the campaign's own session must pause through the inbox when DATA_API_KEY is missing; do not train or run the training evaluator until the required enrichment fetch succeeds.
Budget       minutes=10 experiments=1
