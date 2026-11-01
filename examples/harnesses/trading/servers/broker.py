"""broker server, paper mode only: a simulated account filled at the last close.

Importable as a library by a deployed runner (`PaperAccount`) and served as MCP
tools for agents. State lives in `paper_account.json` in the working directory.
Fills use the latest bar at or before the order time from the market-data store,
so a deployed strategy sees the same feed the backtest did. Connecting a real
broker is a different server, not a flag on this one.
"""
import json
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from market_data import DEFAULT_STORE, instrument_file, read_frame, utc

STATE_FILE = Path("paper_account.json")
STARTING_CASH = 1_000_000.0
server = FastMCP("broker")


class PaperAccount:
    def __init__(self, state_file: Path = STATE_FILE, store: Path = DEFAULT_STORE) -> None:
        self.state_file = state_file
        self.store = store
        self.state = (
            json.loads(state_file.read_text(encoding="utf-8"))
            if state_file.exists()
            else {"cash": STARTING_CASH, "positions": {}, "orders": []}
        )

    def last_close(self, instrument: str, at: str) -> float:
        frame = read_frame(instrument_file(self.store, instrument))
        before = frame[frame["timestamp"] <= utc(at)]
        if before.empty:
            raise ValueError(f"no bar for {instrument} at or before {at}")
        return float(before["close"].iloc[-1])

    def place_order(self, instrument: str, side: str, quantity: float, at: str) -> dict:
        if side not in ("buy", "sell"):
            raise ValueError(f"side must be buy or sell, got {side!r}")
        if quantity <= 0:
            raise ValueError("quantity must be positive")
        price = self.last_close(instrument, at)
        signed = quantity if side == "buy" else -quantity
        self.state["cash"] -= signed * price
        self.state["positions"][instrument] = self.state["positions"].get(instrument, 0.0) + signed
        order = {"instrument": instrument, "side": side, "quantity": quantity, "price": price, "at": utc(at).isoformat()}
        self.state["orders"].append(order)
        self.state_file.write_text(json.dumps(self.state, indent=2), encoding="utf-8")
        return order


@server.tool()
def get_account() -> dict:
    """Cash, positions and the order log of the paper account."""
    return PaperAccount().state


@server.tool()
def place_order(instrument: str, side: str, quantity: float, at: str) -> dict:
    """Fill a market order at the last close at or before `at` (an ISO timestamp)."""
    return PaperAccount().place_order(instrument, side, quantity, at)


if __name__ == "__main__":
    server.run()
