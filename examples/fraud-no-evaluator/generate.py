"""Deterministic card transactions with a fraud label and no evaluator.

Seeded, byte-identical on any machine with the same NumPy and pandas; the
hashes in MANIFEST.json say whether they are. Writes data/transactions.csv
(every row labelled) and MANIFEST.json.
"""

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

SEED = 20261025
ROWS = 20_000
HERE = Path(__file__).resolve().parent


def main() -> None:
    rng = np.random.default_rng(SEED)
    amount = np.round(np.exp(rng.normal(3.6, 1.1, ROWS)), 2)
    hour = rng.integers(0, 24, ROWS)
    merchant_category = rng.integers(0, 12, ROWS)
    distance_from_home_km = np.round(np.exp(rng.normal(2.0, 1.3, ROWS)), 1)
    days_since_last_txn = np.round(rng.exponential(3.0, ROWS), 1)
    txn_count_24h = rng.poisson(2.0, ROWS)
    is_foreign = (rng.random(ROWS) < 0.08).astype(int)
    card_age_days = rng.integers(10, 3650, ROWS)
    online = (rng.random(ROWS) < 0.45).astype(int)

    night = ((hour >= 1) & (hour <= 5)).astype(float)
    # Coefficients chosen so the task has room: under the brief's protocol
    # the shipped rules score 0.09 PR-AUC and gradient boosting with no
    # feature work 0.55 (measured 2026-10-24 on this generator's data).
    logit = -6.0 + 2.0 * (
        1.1 * (amount > 400)
        + 0.9 * night
        + 1.6 * is_foreign
        + 0.015 * np.minimum(distance_from_home_km, 200)
        + 0.35 * np.minimum(txn_count_24h, 8)
        - 0.0004 * card_age_days
        + 0.7 * online * (amount > 150)
        + 0.8 * ((merchant_category == 7) & (amount > 250))
        + 0.9 * (txn_count_24h >= 5) * (days_since_last_txn < 0.5)
    ) + rng.normal(0, 0.3, ROWS)
    fraud = (rng.random(ROWS) < 1 / (1 + np.exp(-logit))).astype(int)

    frame = pd.DataFrame({
        "id": np.arange(1, ROWS + 1),
        "amount": amount,
        "hour": hour,
        "merchant_category": merchant_category,
        "distance_from_home_km": distance_from_home_km,
        "days_since_last_txn": days_since_last_txn,
        "txn_count_24h": txn_count_24h,
        "is_foreign": is_foreign,
        "card_age_days": card_age_days,
        "online": online,
        "fraud": fraud,
    })
    (HERE / "data").mkdir(exist_ok=True)
    path = HERE / "data" / "transactions.csv"
    frame.to_csv(path, index=False, lineterminator="\n")
    manifest = {
        "seed": SEED,
        "rows": ROWS,
        "fraud_rate": round(float(fraud.mean()), 4),
        "files": {"data/transactions.csv": hashlib.sha256(path.read_bytes()).hexdigest()},
    }
    (HERE / "MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"wrote {path} ({ROWS} rows, fraud rate {manifest['fraud_rate']:.2%})")


if __name__ == "__main__":
    main()
