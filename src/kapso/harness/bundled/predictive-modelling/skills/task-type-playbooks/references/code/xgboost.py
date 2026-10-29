"""A simple Implementation of XGboost (from the benchmark's graph; the task's own inputs where the original named a public dataset)."""
import xgboost as xgb
from sklearn.model_selection import train_test_split
import numpy as np

X, y = features, labels  # the task's feature frame and target
X_train, X_val, y_train, y_val = train_test_split(X, y, test_size=0.2, random_state=42)

dtrain = xgb.DMatrix(X_train, label=y_train)
dval = xgb.DMatrix(X_val, label=y_val)

params = {
    "objective": "multi:softprob",
    "num_class": 3,
    "eval_metric": "mlogloss"
}

bst = xgb.train(
    params=params,
    dtrain=dtrain,
    num_boost_round=500,
    evals=[(dval, "val")],
    early_stopping_rounds=20,
    verbose_eval=10
)

pred = np.argmax(bst.predict(dval), axis=1)
print("Accuracy:", (pred == y_val).mean())
