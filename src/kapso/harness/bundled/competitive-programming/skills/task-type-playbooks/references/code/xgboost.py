"""XGBoost on a flat table: a shape from a hand-written knowledge graph of past
competitions, not a method.

Parameters, the task's: `features` and `labels`, `num_classes`, the objective
(`multi:softprob` for several classes, `binary:logistic` for two,
`reg:absoluteerror` for an MAE-scored regression), `task_metric`. The split below
is a random split, right only when rows are independent (the cv-protocol skill);
the rows it holds out are an internal fold, never the task's official validation
split. `device` is "cuda" when the trees have the card to themselves (the
tabular-modeling skill), else "cpu".
"""
import numpy as np
import xgboost as xgb
from sklearn.model_selection import train_test_split

X_train, X_val, y_train, y_val = train_test_split(features, labels, test_size=0.2, random_state=0)
dtrain, dval = xgb.DMatrix(X_train, label=y_train), xgb.DMatrix(X_val, label=y_val)

params = {"objective": "multi:softprob", "num_class": num_classes, "eval_metric": "mlogloss",
          "tree_method": "hist", "device": "cuda", "learning_rate": 0.05, "max_depth": 6}
booster = xgb.train(params=params, dtrain=dtrain, num_boost_round=5000, evals=[(dval, "val")],
                    early_stopping_rounds=100, verbose_eval=100)  # stops on the validation loss, not an accuracy

val_predictions = booster.predict(dval, iteration_range=(0, booster.best_iteration + 1))
print("validation score:", task_metric(y_val, np.argmax(val_predictions, axis=1)))
