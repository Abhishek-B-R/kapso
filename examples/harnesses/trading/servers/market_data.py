"""market-data server: bars, calendar and snapshots from a pinned local store.

Tools read `prepared/market-data` under the session workspace by default, the
snapshot setup built from the task's data. A store holds one CSV or parquet file
per instrument with a `timestamp` column and OHLCV columns, plus MANIFEST.json
with the source, the range and a content hash. Also importable as a library:
the broker server and a deployed runner reuse `instrument_file` and `read_frame`.
"""
import hashlib
import json
import shutil
from pathlib import Path

import pandas as pd
from mcp.server.fastmcp import FastMCP

DEFAULT_STORE = Path("prepared/market-data")
BAR_SUFFIXES = (".csv", ".parquet")
server = FastMCP("market-data")


def store_dir(root: str | None) -> Path:
    path = Path(root) if root else DEFAULT_STORE
    if not path.is_dir():
        raise FileNotFoundError(f"no market-data store at {path}; build one with snapshot()")
    return path


def instrument_file(store: Path, instrument: str) -> Path:
    matches = [p for p in store.iterdir() if p.stem == instrument and p.suffix in BAR_SUFFIXES]
    if not matches:
        raise FileNotFoundError(f"no instrument {instrument} in {store}")
    return matches[0]


def read_frame(path: Path) -> pd.DataFrame:
    frame = pd.read_parquet(path) if path.suffix == ".parquet" else pd.read_csv(path)
    if "timestamp" not in frame.columns:
        raise ValueError(f"{path} has no timestamp column")
    frame["timestamp"] = pd.to_datetime(frame["timestamp"], utc=True)
    return frame.sort_values("timestamp").reset_index(drop=True)


def utc(moment: str) -> pd.Timestamp:
    stamp = pd.Timestamp(moment)
    return stamp.tz_localize("UTC") if stamp.tzinfo is None else stamp.tz_convert("UTC")


@server.tool()
def list_instruments(root: str | None = None) -> list[str]:
    """Instruments in the store, one file per instrument."""
    return sorted(p.stem for p in store_dir(root).iterdir() if p.suffix in BAR_SUFFIXES)


@server.tool()
def get_bars(instrument: str, start: str, end: str, root: str | None = None) -> str:
    """Bars for one instrument between two ISO timestamps, inclusive, as CSV."""
    frame = read_frame(instrument_file(store_dir(root), instrument))
    window = frame[(frame["timestamp"] >= utc(start)) & (frame["timestamp"] <= utc(end))]
    return window.to_csv(index=False)


@server.tool()
def get_calendar(instrument: str, root: str | None = None) -> list[str]:
    """The distinct trading days present for an instrument, as ISO dates."""
    frame = read_frame(instrument_file(store_dir(root), instrument))
    return sorted({stamp.date().isoformat() for stamp in frame["timestamp"]})


@server.tool()
def snapshot(source: str, dest: str = str(DEFAULT_STORE)) -> dict:
    """Copy the task's data directory into a pinned store and write MANIFEST.json."""
    src, out = Path(source), Path(dest)
    files = sorted(p for p in src.iterdir() if p.suffix in BAR_SUFFIXES) if src.is_dir() else []
    if not files:
        raise FileNotFoundError(f"{src} is not a directory holding .csv or .parquet files")
    out.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256()
    starts, ends = [], []
    for path in files:
        shutil.copy2(path, out / path.name)
        digest.update(path.read_bytes())
        frame = read_frame(path)
        starts.append(frame["timestamp"].iloc[0])
        ends.append(frame["timestamp"].iloc[-1])
    manifest = {
        "source": str(src.resolve()),
        "instruments": [p.stem for p in files],
        "start": min(starts).isoformat(),
        "end": max(ends).isoformat(),
        "sha256": digest.hexdigest(),
    }
    (out / "MANIFEST.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


if __name__ == "__main__":
    server.run()
