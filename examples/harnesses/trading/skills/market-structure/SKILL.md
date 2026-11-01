---
name: market-structure
description: "The microstructure facts to check before proposing or implementing execution: sessions, auctions, funding and settlement, tick and lot sizes, per asset class. Use when an idea touches execution, timing or costs."
---
# Market structure

Check these for the task's instruments before touching execution:

- Sessions and auctions: when the bar closes, whether there is an opening or
  closing auction, holidays. Equities and futures have sessions; crypto trades
  continuously but funding settles on a schedule.
- Settlement and funding: perpetual futures pay or receive funding every few
  hours; cash equities settle T+1; FX rolls daily. These are costs or carry,
  not noise.
- Tick and lot sizes: a signal that trades below one lot is not a strategy.
- Liquidity by time of day: a fill assumed at the close of an illiquid bar is
  optimistic. Prefer the next bar's open or VWAP where the task's cost model
  allows.
- Corporate actions and expiries: splits, dividends, futures rolls. Check the
  snapshot's `MANIFEST.json` for how the data handles them.
