"""The starting strategy: a long-only moving-average cross.

The contract the evaluation measures: `signal(bars)` takes one instrument's
bars (timestamp, open, high, low, close, volume; one row per day, ascending)
and returns a Series of the position to hold, one value per bar in [-1, 1],
using nothing after each bar's own row. The evaluation shifts it by one bar
and charges costs on every change.
"""

import pandas as pd

FAST = 20
SLOW = 100


def signal(bars: pd.DataFrame) -> pd.Series:
    close = bars["close"]
    fast = close.rolling(FAST).mean()
    slow = close.rolling(SLOW).mean()
    return (fast > slow).astype(float)
