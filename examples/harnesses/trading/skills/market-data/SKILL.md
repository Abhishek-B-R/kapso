---
name: market-data
description: "Use the market-data server: list instruments, pull bars and calendars from the pinned snapshot, and build the snapshot from the task's data in setup. Use whenever a session needs prices."
---
# Market data

All prices come from the market-data server, which reads the pinned snapshot
under `prepared/market-data/` (built in setup from the task's data directory).
Never fetch prices from the web inside a run: the snapshot is what makes
attempts comparable, and the session hook denies curl and wget anyway.

Tools:

- `list_instruments()`: what the snapshot holds.
- `get_bars(instrument, start, end)`: closed bars between two ISO timestamps,
  inclusive, as CSV.
- `get_calendar(instrument)`: the trading days present.
- `snapshot(source, dest)`: setup only. Copies the task's data (one CSV or
  parquet file per instrument with a `timestamp` column) into a store and
  writes `MANIFEST.json` with source, instruments, range and sha256.

Pitfalls the server does not fix for you:

- Adjustments: check `MANIFEST.json` and the task statement for whether prices
  are split and dividend adjusted. Unadjusted equity series produce fake jumps.
- Survivorship: a snapshot of today's constituents overstates past returns. If
  the task statement does not address it, say so in the attempt notes.
- Sessions: a daily bar closes at the venue's close, not at midnight UTC. Join
  sources on the venue timestamp, never on the calendar date.
