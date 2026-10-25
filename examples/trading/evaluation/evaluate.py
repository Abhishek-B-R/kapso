"""The evaluation Kapso protects for the trading example.

    python kapso_evaluation/evaluate.py [--fast]

Run from the workspace root. It imports `signal` from the workspace's
strategy.py, loads the development bars from kapso_datasets/bars and the
out-of-sample bars from the private directory named in private_dir.txt
beside this script, applies the one discipline that matters (a signal at
bar t is the position held during bar t+1; costs are charged on turnover),
scores the out-of-sample year as an equal-weight portfolio, writes
results/equity_curve.csv and results/trades.csv in the workspace and
result.json beside this script, and prints the risk line then the metric as
its last line:

    max_drawdown: 0.1234
    turnover: 12.3
    sharpe: 0.8412

Higher is better. Exit codes: 0 scored; 2 the signal is malformed (the
reason is printed); 3 strategy.py is missing. `--fast` scores one
instrument over the first quarter: a smoke check whose number is not
comparable with a full score.
"""

import argparse
import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

COST_PER_UNIT_TURNOVER = 0.0005      # 5 basis points
TRADING_DAYS = 252
OOS_START = "2024-01-01T00:00:00Z"
FAST_DAYS = 63
STRATEGY_FILE = "strategy.py"
SCRIPT_PATH = "kapso_evaluation/evaluate.py"


def fail(code: int, reason: str) -> None:
    print(f"evaluation failed: {reason}")
    sys.exit(code)


def load_signal(workspace: Path):
    file = workspace / STRATEGY_FILE
    if not file.is_file():
        fail(3, f"{STRATEGY_FILE} is missing from the workspace root")
    spec = importlib.util.spec_from_file_location("strategy", file)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    if not callable(getattr(module, "signal", None)):
        fail(2, f"{STRATEGY_FILE} defines no signal(bars) function")
    return module.signal


def read_bars(path: Path) -> pd.DataFrame:
    frame = pd.read_csv(path)
    frame["timestamp"] = pd.to_datetime(frame["timestamp"], utc=True)
    return frame.sort_values("timestamp").reset_index(drop=True)


def positions(signal, bars: pd.DataFrame, instrument: str) -> pd.Series:
    raw = signal(bars.copy())
    if not isinstance(raw, pd.Series) or len(raw) != len(bars):
        fail(2, f"signal({instrument}) must return a Series with one value per bar")
    values = pd.to_numeric(raw, errors="coerce").fillna(0.0)
    if (values.abs() > 1.0).any():
        fail(2, f"signal({instrument}) must stay within [-1, 1]")
    # The discipline: decided at t, held during t+1.
    return values.shift(1).fillna(0.0).reset_index(drop=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--workspace", default=".", help="the workspace root; strategy.py and kapso_datasets/ live there")
    parser.add_argument("--fast", action="store_true", help=f"one instrument, the first {FAST_DAYS} out-of-sample days")
    args = parser.parse_args()

    workspace = Path(args.workspace).resolve()
    here = Path(__file__).resolve().parent
    private_dir = Path((here / "private_dir.txt").read_text(encoding="utf-8").strip())
    dev_dir = workspace / "kapso_datasets" / "bars"
    instruments = sorted(p.stem for p in dev_dir.glob("*.csv"))
    if not instruments:
        fail(2, f"no bars under {dev_dir}")
    if args.fast:
        instruments = instruments[:1]
    signal = load_signal(workspace)

    daily = []
    trades = []
    turnover_by_instrument = []
    for instrument in instruments:
        bars = pd.concat([read_bars(dev_dir / f"{instrument}.csv"), read_bars(private_dir / f"{instrument}.csv")], ignore_index=True)
        position = positions(signal, bars, instrument)
        returns = bars["close"].pct_change().fillna(0.0)
        turnover = position.diff().abs().fillna(position.abs())
        pnl = position * returns - COST_PER_UNIT_TURNOVER * turnover
        oos = bars["timestamp"] >= pd.Timestamp(OOS_START)
        if args.fast:
            oos = oos & (oos.cumsum() <= FAST_DAYS)
        frame = pd.DataFrame({"timestamp": bars["timestamp"], "pnl": pnl, "position": position, "turnover": turnover})[oos]
        daily.append(frame.set_index("timestamp")["pnl"].rename(instrument))
        turnover_by_instrument.append(frame["turnover"].mean() * TRADING_DAYS)
        changed = frame[frame["turnover"] > 0]
        trades.append(pd.DataFrame({
            "timestamp": changed["timestamp"].dt.strftime("%Y-%m-%d"),
            "instrument": instrument,
            "position": changed["position"].round(4),
            "turnover": changed["turnover"].round(4),
        }))

    portfolio = pd.concat(daily, axis=1).mean(axis=1)
    equity = (1.0 + portfolio).cumprod()
    drawdown = float((1.0 - equity / equity.cummax()).max())
    sharpe = float(portfolio.mean() / portfolio.std() * np.sqrt(TRADING_DAYS)) if portfolio.std() > 0 else 0.0
    annual_turnover = float(np.mean(turnover_by_instrument))

    results = workspace / "results"
    results.mkdir(exist_ok=True)
    pd.DataFrame({
        "timestamp": portfolio.index.strftime("%Y-%m-%d"),
        "portfolio_return": portfolio.values.round(6),
        "equity": equity.values.round(6),
    }).to_csv(results / "equity_curve.csv", index=False)
    pd.concat(trades, ignore_index=True).to_csv(results / "trades.csv", index=False)

    lines = []
    if args.fast:
        lines.append("fast: one instrument, one quarter; not comparable with a full score")
    lines.append(f"instruments: {', '.join(instruments)}")
    lines.append(f"days: {len(portfolio)}")
    lines.append(f"max_drawdown: {drawdown:.4f}")
    lines.append(f"turnover: {annual_turnover:.1f}")
    lines.append(f"sharpe: {sharpe:.4f}")
    output = "\n".join(lines)
    (here / "result.json").write_text(json.dumps({
        "evaluation_script_path": SCRIPT_PATH,
        "evaluation_output": output,
        "score": round(sharpe, 4),
        "metrics": {"sharpe": round(sharpe, 4), "max_drawdown": round(drawdown, 4), "turnover": round(annual_turnover, 1)},
        "fast": bool(args.fast),
    }, indent=2) + "\n", encoding="utf-8")
    print(output)


if __name__ == "__main__":
    main()
