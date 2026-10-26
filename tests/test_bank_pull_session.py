"""Every pull event the bank gate writes carries the session it served
(wp6-observability.md, change 5): the label the staging gave the
session's gate configuration, so a read is attributed to the session
that made it however many run at once."""
import asyncio
import json

import pytest

from kapso.gated_mcp.gates.bank_gate import BankGate
from tests.test_bank_pull import build_bank
from tests.test_bank_retriever import card_text


def test_the_gate_stamps_the_session_on_every_pull_event(tmp_path, monkeypatch):
    pytest.importorskip("mcp")
    root = build_bank(tmp_path / "bank", {"a-card": card_text("a-card")})
    log = tmp_path / "pull.jsonl"
    monkeypatch.setenv("KAPSO_BANKS", json.dumps([{
        "reference": "mine", "head": "abc", "dir": str(root), "provenance": "measured by you", "scope": "all",
    }]))
    monkeypatch.setenv("KAPSO_SERVING_PULL_LOG", str(log))
    monkeypatch.setenv("KAPSO_TASK_HARNESS", "none")
    monkeypatch.setenv("KAPSO_PROBE_BUDGET", "0")
    monkeypatch.setenv("KAPSO_SESSION", "ideation/iter1")
    gate = BankGate()
    asyncio.run(gate.handle_call("bank_index", {}))
    asyncio.run(gate.handle_call("bank_get_card", {"cards": ["a-card"]}))
    events = [json.loads(line) for line in log.read_text().splitlines()]
    assert [event["tool"] for event in events] == ["bank_index", "bank_get_card"]
    assert {event["session"] for event in events} == {"ideation/iter1"}
    assert events[1]["served"][0]["card"] == "a-card"
