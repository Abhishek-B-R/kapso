"""Deterministic synthetic churn data for the semantic fixtures.

Byte-identical output for the same arguments, so every run of the suite
sees the same rows. The label carries real signal behind noise: contract
type, payment method, charges with an interaction, support tickets, a
usage trend, late payments, autopay, and a tenure curve, plus three columns
of pure noise and a 2% missing rate on two numeric columns. A logistic
regression on one-hot features (repo/predict.py) lands near 0.80 AUC; a
gradient-boosting model with no feature work reaches about 0.83, and a
model that finds the thresholds, the interaction and the tenure curve has
headroom above that.

    python generate.py            # writes data/, private/, evaluation/private_dir.txt, MANIFEST.json

data/train.csv            agent-visible, with the label
data/holdout.csv          agent-visible, features only, the rows to predict
private/holdout_labels.csv  the answers; nothing under private/ is copied into a workspace
evaluation/private_dir.txt  the absolute path of private/, read by the evaluator
"""

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

SEED = 20261024
N_TRAIN = 10_000
N_HOLDOUT = 3_000
MISSING_RATE = 0.02
CONTRACTS = ["month-to-month", "one-year", "two-year"]
PAYMENTS = ["card", "bank-transfer", "electronic-check", "mailed-check"]
PLANS = ["basic", "plus", "premium"]
REGIONS = ["north", "south", "east", "west"]
SEGMENTS = ["a", "b", "c"]
FEATURE_COLUMNS = [
    "id", "tenure_months", "monthly_charges", "contract", "payment_method", "plan",
    "region", "support_tickets", "usage_trend", "late_payments", "has_partner",
    "autopay", "discount_pct", "devices", "ref_score", "signup_day", "segment",
]
LABEL = "churned"


def make_frame(rng: np.random.Generator, n: int, first_id: int) -> pd.DataFrame:
    tenure = rng.integers(0, 72, n)
    monthly = np.round(np.clip(rng.normal(65, 25, n), 15, 150), 2)
    contract = rng.choice(CONTRACTS, n, p=[0.55, 0.25, 0.20])
    payment = rng.choice(PAYMENTS, n)
    plan = rng.choice(PLANS, n, p=[0.5, 0.3, 0.2])
    region = rng.choice(REGIONS, n)
    tickets = rng.poisson(0.8, n)
    usage_trend = np.round(rng.normal(0, 1, n), 3)
    late_payments = rng.binomial(3, 0.15, n)
    has_partner = rng.random(n) < 0.45
    autopay = rng.random(n) < 0.6
    discount = np.round(rng.random(n) * 30 * (rng.random(n) < 0.3), 1)
    devices = rng.integers(1, 6, n)
    ref_score = np.round(rng.normal(0, 1, n), 3)          # noise
    signup_day = rng.integers(0, 365, n)                   # noise
    segment = rng.choice(SEGMENTS, n)                      # noise

    month_to_month = contract == "month-to-month"
    # Linear terms a logistic regression finds, plus thresholds, an
    # interaction and a tenure curve that only a flexible model finds: the
    # headroom above the baseline is deliberate.
    logit = (
        -2.6
        + 0.9 * month_to_month
        + 0.5 * (payment == "electronic-check")
        + 0.010 * (monthly - 65)
        + 2.0 * month_to_month * (monthly > 90)            # interaction
        + 0.2 * tickets
        + 1.4 * (tickets >= 3)                              # threshold
        - 0.3 * usage_trend
        + 1.2 * (np.abs(usage_trend) > 1.5)                 # big swings either way
        + 0.4 * late_payments
        - 0.5 * autopay
        + 2.2 * np.exp(-tenure / 6.0)                       # new customers churn
        + 0.08 * np.maximum(tenure - 60, 0)                 # and the very old drift away
        - 0.02 * discount
        - 0.3 * has_partner
    )
    probability = 1.0 / (1.0 + np.exp(-1.3 * logit))
    churned = rng.random(n) < probability

    frame = pd.DataFrame({
        "id": [f"C{first_id + i:06d}" for i in range(n)],
        "tenure_months": tenure,
        "monthly_charges": monthly,
        "contract": contract,
        "payment_method": payment,
        "plan": plan,
        "region": region,
        "support_tickets": tickets,
        "usage_trend": usage_trend,
        "late_payments": late_payments,
        "has_partner": has_partner,
        "autopay": autopay,
        "discount_pct": discount,
        "devices": devices,
        "ref_score": ref_score,
        "signup_day": signup_day,
        "segment": segment,
        LABEL: churned,
    })
    for column in ("monthly_charges", "usage_trend"):
        frame.loc[rng.random(n) < MISSING_RATE, column] = np.nan
    return frame


def write_csv(frame: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False, float_format="%.3f", lineterminator="\n")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--root", default=str(Path(__file__).resolve().parent), help="the fixture directory")
    args = parser.parse_args()
    root = Path(args.root).resolve()

    rng = np.random.default_rng(SEED)
    train = make_frame(rng, N_TRAIN, 1)
    holdout = make_frame(rng, N_HOLDOUT, N_TRAIN + 1)

    write_csv(train, root / "data" / "train.csv")
    write_csv(holdout[FEATURE_COLUMNS], root / "data" / "holdout.csv")
    write_csv(holdout[["id", LABEL]], root / "private" / "holdout_labels.csv")
    (root / "evaluation" / "private_dir.txt").write_text(str(root / "private") + "\n", encoding="utf-8")

    manifest = {
        "seed": SEED,
        "rows": {"train": N_TRAIN, "holdout": N_HOLDOUT},
        "features": len(FEATURE_COLUMNS) - 1,
        "label": LABEL,
        "positive_rate": {
            "train": round(float(train[LABEL].mean()), 4),
            "holdout": round(float(holdout[LABEL].mean()), 4),
        },
        "sha256": {
            "data/train.csv": sha256(root / "data" / "train.csv"),
            "data/holdout.csv": sha256(root / "data" / "holdout.csv"),
            "private/holdout_labels.csv": sha256(root / "private" / "holdout_labels.csv"),
        },
    }
    (root / "MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
