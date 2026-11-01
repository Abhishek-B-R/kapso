# Churn model

Predict which customers churn. `predict.py` trains on `kapso_datasets/train.csv`
(the `churned` column is the label) and writes a churn probability for every
row of `kapso_datasets/holdout.csv`:

```
python predict.py --data kapso_datasets --out predictions.csv
```

`predictions.csv` has two columns, `id` and `churn_probability`. The
evaluation in `kapso_evaluation/evaluate.py` runs that command and scores
the predictions with ROC AUC against labels it holds; higher is better.

The current model is a logistic regression on imputed numeric features and
one-hot categoricals. Keep the command and the output format; everything
else in this file is yours to change.
