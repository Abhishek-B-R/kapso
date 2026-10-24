"""Score transactions for fraud: the starting point, three hand-written rules.

Contract: python score.py --data <dir-with-transactions.csv> --out scores.csv
writes id,fraud_probability for every transaction in the input, in order.
"""

import argparse
from pathlib import Path

import pandas as pd


def score(frame: pd.DataFrame) -> pd.Series:
    probability = pd.Series(0.02, index=frame.index)
    probability[frame["amount"] > 400] = 0.30
    probability[(frame["is_foreign"] == 1) & (frame["amount"] > 150)] = 0.60
    probability[(frame["hour"].between(1, 5)) & (frame["online"] == 1)] = 0.45
    return probability


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    frame = pd.read_csv(Path(args.data) / "transactions.csv")
    pd.DataFrame({"id": frame["id"], "fraud_probability": score(frame)}).to_csv(
        args.out, index=False, lineterminator="\n"
    )
    print(f"scored {len(frame)} transactions -> {args.out}")


if __name__ == "__main__":
    main()
