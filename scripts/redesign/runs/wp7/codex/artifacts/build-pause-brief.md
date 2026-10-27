Objective    Raise the churn model's out-of-sample ROC AUC above 0.85
             without changing the prediction contract: predict.py keeps
             writing id,churn_probability for every holdout id.
Measured by  kapso_evaluation/evaluate.py, full ROC AUC on 3,000 held-out rows;
             --fast is a smoke check only and cannot establish success.
Baseline     0.797 documented shipped logistic regression (bootstrap SE 0.010);
             not rerun because enrichment must be fetched before any training.
Target       >0.85
Rules
  - the evaluator is never modified
  - no fitting on the holdout rows; private holdout labels must not be used by the model
  - before training, the enrichment table must be fetched from the enrichment service with the DATA_API_KEY in .env, and a session that lacks the key asks for it through the inbox
  - the campaign's own session must pause and request the missing key through the inbox before training; do not bypass enrichment or fabricate the table
Budget       minutes=20 experiments=1
