"""Churn model: train on the labelled rows, predict a churn probability for
every holdout row.

Contract (the evaluator calls exactly this):

    python predict.py --data kapso_datasets --out predictions.csv

reads <data>/train.csv (with the `churned` label) and <data>/holdout.csv
(features only) and writes <out> with two columns, `id` and
`churn_probability`, one row per holdout id. The baseline is a logistic
regression on imputed, scaled numeric features and one-hot categoricals.
"""

import argparse
from pathlib import Path

import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

LABEL = "churned"
ID = "id"


def build_pipeline(features: pd.DataFrame) -> Pipeline:
    categorical = [c for c in features.columns if features[c].dtype == object or features[c].dtype == bool]
    numeric = [c for c in features.columns if c not in categorical]
    preparation = ColumnTransformer([
        ("numeric", Pipeline([
            ("impute", SimpleImputer(strategy="median")),
            ("scale", StandardScaler()),
        ]), numeric),
        ("categorical", Pipeline([
            ("impute", SimpleImputer(strategy="most_frequent")),
            ("onehot", OneHotEncoder(handle_unknown="ignore")),
        ]), categorical),
    ])
    return Pipeline([
        ("prepare", preparation),
        ("model", LogisticRegression(max_iter=1000)),
    ])


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", default="kapso_datasets")
    parser.add_argument("--out", default="predictions.csv")
    args = parser.parse_args()
    data = Path(args.data)

    train = pd.read_csv(data / "train.csv")
    holdout = pd.read_csv(data / "holdout.csv")
    labels = train.pop(LABEL).astype(int)
    features = train.drop(columns=[ID])

    pipeline = build_pipeline(features)
    pipeline.fit(features, labels)
    probabilities = pipeline.predict_proba(holdout.drop(columns=[ID]))[:, 1]

    pd.DataFrame({ID: holdout[ID], "churn_probability": probabilities}).to_csv(args.out, index=False)
    print(f"wrote {args.out}: {len(holdout)} rows")


if __name__ == "__main__":
    main()
