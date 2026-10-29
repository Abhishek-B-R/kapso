"""Deterministic synthetic retail sources for the pipeline example.

Byte-identical output for the same arguments, so every run of the suite
sees the same rows. Three sources an engineer would recognise, each with
the defects a real export carries: customers exported twice under one id,
a country left empty, orders re-exported whole, orders with no customer or
with one the customer file never had, a status the status list does not
know, a negative amount, a currency in lower case, payments captured
twice. The shipped staging models pass the sources through untouched, so
the evaluator's assertions fail on them; a pipeline that dedupes,
normalises and quarantines at the staging layer passes them all.

    python generate.py            # writes data/ and MANIFEST.json

data/customers.csv     800 customers, 12 exported twice, 5 with no country
data/orders.csv        5,000 orders plus 60 re-exported rows; 30 without a
                       customer, 40 with a customer the file never had, 50
                       with status `unknown`, 25 with a negative amount, 200
                       with the currency in lower case
data/payments.csv      one payment per delivered or shipped order plus 40
                       captured twice; 2% off by cents, 1% off by more
"""

import argparse
import hashlib
import json
from pathlib import Path
from typing import Optional, Sequence

import numpy as np
import pandas as pd

SEED = 20261027
N_CUSTOMERS = 800
N_ORDERS = 5_000
COUNTRIES = ["US", "CA", "UK", "DE", "FR"]
STATUSES = ["placed", "shipped", "delivered", "returned", "cancelled"]
STATUS_WEIGHTS = [0.10, 0.20, 0.55, 0.08, 0.07]
METHODS = ["card", "bank_transfer", "paypal"]
HERE = Path(__file__).resolve().parent


def customers(rng: np.random.Generator) -> pd.DataFrame:
    ids = [f"C{n:04d}" for n in range(1, N_CUSTOMERS + 1)]
    signup = pd.Timestamp("2023-01-01") + pd.to_timedelta(rng.integers(0, 700, N_CUSTOMERS), unit="D")
    frame = pd.DataFrame({
        "customer_id": ids,
        "name": [f"Customer {n}" for n in range(1, N_CUSTOMERS + 1)],
        "country": rng.choice(COUNTRIES, N_CUSTOMERS, p=[0.5, 0.15, 0.15, 0.1, 0.1]),
        "signup_date": signup.strftime("%Y-%m-%d"),
    })
    frame.loc[rng.choice(N_CUSTOMERS, 5, replace=False), "country"] = ""
    twice = frame.iloc[rng.choice(N_CUSTOMERS, 12, replace=False)].copy()
    twice["name"] = twice["name"] + " (updated)"
    return pd.concat([frame, twice], ignore_index=True)


def orders(rng: np.random.Generator, customer_ids: list) -> pd.DataFrame:
    ids = [f"O{n:06d}" for n in range(1, N_ORDERS + 1)]
    dates = pd.Timestamp("2024-01-01") + pd.to_timedelta(rng.integers(0, 365, N_ORDERS), unit="D")
    frame = pd.DataFrame({
        "order_id": ids,
        "customer_id": rng.choice(customer_ids, N_ORDERS),
        "order_date": dates.strftime("%Y-%m-%d"),
        "status": rng.choice(STATUSES, N_ORDERS, p=STATUS_WEIGHTS),
        "amount": np.round(rng.lognormal(4.0, 0.6, N_ORDERS), 2),
        "currency": "USD",
    })
    rows = rng.choice(N_ORDERS, 345, replace=False)
    frame.loc[rows[:30], "customer_id"] = ""
    frame.loc[rows[30:70], "customer_id"] = [f"C{n:04d}" for n in rng.integers(9000, 9999, 40)]
    frame.loc[rows[70:120], "status"] = "unknown"
    frame.loc[rows[120:145], "amount"] = -frame.loc[rows[120:145], "amount"]
    frame.loc[rows[145:345], "currency"] = "usd"
    again = frame.iloc[rng.choice(N_ORDERS, 60, replace=False)].copy()
    return pd.concat([frame, again], ignore_index=True)


def payments(rng: np.random.Generator, order_frame: pd.DataFrame) -> pd.DataFrame:
    paid = order_frame.drop_duplicates("order_id")
    paid = paid[paid["status"].isin(["shipped", "delivered", "returned"]) & (paid["amount"] > 0)].reset_index(drop=True)
    amounts = paid["amount"].to_numpy().copy()
    cents = rng.choice(len(paid), int(0.02 * len(paid)), replace=False)
    amounts[cents] = np.round(amounts[cents] + rng.choice([-0.01, 0.01], len(cents)), 2)
    off = rng.choice(len(paid), int(0.01 * len(paid)), replace=False)
    amounts[off] = np.round(amounts[off] * rng.uniform(0.5, 0.9, len(off)), 2)
    frame = pd.DataFrame({
        "payment_id": [f"P{n:06d}" for n in range(1, len(paid) + 1)],
        "order_id": paid["order_id"].to_numpy(),
        "amount": amounts,
        "method": rng.choice(METHODS, len(paid), p=[0.7, 0.2, 0.1]),
        "paid_at": (pd.to_datetime(paid["order_date"]) + pd.to_timedelta(rng.integers(0, 5, len(paid)), unit="D")).dt.strftime("%Y-%m-%d"),
    })
    twice = frame.iloc[rng.choice(len(frame), 40, replace=False)].copy()
    return pd.concat([frame, twice], ignore_index=True)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main(argv: Optional[Sequence[str]] = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.parse_args(argv)
    rng = np.random.default_rng(SEED)
    data = HERE / "data"
    data.mkdir(exist_ok=True)
    customer_frame = customers(rng)
    order_frame = orders(rng, customer_frame["customer_id"].drop_duplicates().tolist())
    payment_frame = payments(rng, order_frame)
    for name, frame in (("customers", customer_frame), ("orders", order_frame), ("payments", payment_frame)):
        frame.to_csv(data / f"{name}.csv", index=False, lineterminator="\n")
    manifest = {
        "seed": SEED,
        "rows": {name: int(len(frame)) for name, frame in (("customers", customer_frame), ("orders", order_frame), ("payments", payment_frame))},
        "sha256": {f"data/{name}.csv": sha256(data / f"{name}.csv") for name in ("customers", "orders", "payments")},
    }
    (HERE / "MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    for name, rows in manifest["rows"].items():
        print(f"data/{name}.csv: {rows} rows")
    print("MANIFEST.json written")


if __name__ == "__main__":
    main()
