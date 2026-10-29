"""A simple Implementation of Catboost (from the benchmark's graph; the task's own inputs where the original named a public dataset)."""
import numpy as np
import pandas as pd
from catboost import CatBoostClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score

X, y = frame.drop(columns=[target]), frame[target]  # the task's frame and target column


X_train, X_test, y_train, y_test = train_test_split(X, y, stratify=y, random_state=0)

model = CatBoostClassifier(iterations=100, learning_rate=0.1, depth=6, verbose=20, random_state=0)
model.fit(X_train, y_train, cat_features=categorical_columns)

preds = model.predict(X_test)
print("Accuracy:", accuracy_score(y_test, preds))
