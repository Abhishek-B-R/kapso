"""Deterministic synthetic daily bars for the trading example.

Byte-identical output for the same seed. Three instruments, business days
from 2021 through 2024, each a random walk with a drift and a trend
component: the next day's return leans on the last twenty days' average
return, so a strategy that follows the trend has an edge and one that
fades it does not. Development bars (2021 to 2023) go under data/, the
out-of-sample year (2024) under private/, which nothing copies into a
workspace: the evaluator reads it through evaluation/private_dir.txt.

    python generate.py       # writes data/bars/, private/oos/, evaluation/private_dir.txt, MANIFEST.json

data/bars/<INSTRUMENT>.csv     agent-visible: timestamp, open, high, low, close, volume
private/oos/<INSTRUMENT>.csv   the 2024 bars; the evaluation alone reads them
evaluation/private_dir.txt     the absolute path of private/oos, read by the evaluator
"""

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

SEED = 20261025
START = "2021-01-04"
DEV_END = "2023-12-29"
OOS_END = "2024-12-31"
TREND_WINDOW = 20
# 0.35: the shipped 20/100 cross scores about 0.14 out of sample, a 10/50
# cross about 0.9, a volatility-targeted 20-day momentum above 2; the target
# of 1.0 is reachable and the baseline is not already there.
TREND_WEIGHT = 0.35
# instrument: (daily drift, daily volatility)
INSTRUMENTS = {"ALPHA": (0.00030, 0.012), "BETA": (0.00020, 0.018), "GAMMA": (0.00015, 0.009)}
HERE = Path(__file__).resolve().parent


def bars_for(name: str, drift: float, vol: float, rng: np.random.Generator) -> pd.DataFrame:
    days = pd.bdate_range(START, OOS_END)
    returns = np.zeros(len(days))
    for i in range(len(days)):
        trend = returns[max(0, i - TREND_WINDOW):i].mean() if i else 0.0
        returns[i] = drift + TREND_WEIGHT * trend + vol * rng.standard_normal()
    close = 100.0 * np.cumprod(1.0 + returns)
    open_ = np.concatenate([[100.0], close[:-1]])
    spread = np.abs(vol * rng.standard_normal(len(days)))
    high = np.maximum(open_, close) * (1.0 + spread)
    low = np.minimum(open_, close) * (1.0 - spread)
    volume = rng.integers(1_000, 10_000, len(days))
    return pd.DataFrame({
        "timestamp": days.strftime("%Y-%m-%dT00:00:00Z"),
        "open": open_.round(4), "high": high.round(4), "low": low.round(4),
        "close": close.round(4), "volume": volume,
    })


def main() -> None:
    rng = np.random.default_rng(SEED)
    dev_dir = HERE / "data" / "bars"
    oos_dir = HERE / "private" / "oos"
    dev_dir.mkdir(parents=True, exist_ok=True)
    oos_dir.mkdir(parents=True, exist_ok=True)
    manifest = {}
    for name, (drift, vol) in INSTRUMENTS.items():
        frame = bars_for(name, drift, vol, rng)
        dev = frame[frame["timestamp"] <= f"{DEV_END}T00:00:00Z"]
        oos = frame[frame["timestamp"] > f"{DEV_END}T00:00:00Z"]
        for directory, part in ((dev_dir, dev), (oos_dir, oos)):
            path = directory / f"{name}.csv"
            part.to_csv(path, index=False)
            manifest[str(path.relative_to(HERE))] = hashlib.sha256(path.read_bytes()).hexdigest()
    (HERE / "evaluation" / "private_dir.txt").write_text(str(oos_dir) + "\n", encoding="utf-8")
    (HERE / "MANIFEST.json").write_text(json.dumps({"seed": SEED, "files": manifest}, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {len(manifest)} files; development bars under data/bars, 2024 under private/oos")


if __name__ == "__main__":
    main()
