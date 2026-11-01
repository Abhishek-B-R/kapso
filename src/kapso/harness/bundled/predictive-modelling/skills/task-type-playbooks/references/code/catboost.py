"""CatBoost on a flat table: a shape from a hand-written knowledge graph of past
competitions, not a method.

Parameters, the task's: `frame` and `target` (the training frame and its label
column), `categorical_columns`, `task_metric` (the task's metric, its direction from
the task statement). The split below is a stratified random split, right only when
rows are independent; grouped, forward-chained or stratified folds are the
cv-protocol skill's call, and the rows held out here are an internal fold, never the
task's official validation split.
"""
from catboost import CatBoostClassifier
from sklearn.model_selection import train_test_split

X, y = frame.drop(columns=[target]), frame[target]
X_train, X_val, y_train, y_val = train_test_split(X, y, stratify=y, random_state=0)

model = CatBoostClassifier(iterations=2000, learning_rate=0.05, depth=6, verbose=100, random_state=0)
model.fit(X_train, y_train, cat_features=categorical_columns, eval_set=(X_val, y_val), early_stopping_rounds=100)

print("validation score:", task_metric(y_val, model.predict_proba(X_val)))
