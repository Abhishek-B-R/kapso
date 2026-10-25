# Bank tool-surface tests (serving v2): eligibility law on the
# session-facing side — the index is the whole eligible set, quarantine
# refuses unmarked, refusals are named, and every event lands in the JSONL
# pull log (Rule 9: the regressions are a decoy leaking through direct
# request, silent refusals, and the gate resolving without its campaign
# env).

import json

from kapso.gated_mcp.presets import resolve_gates
from kapso.learning.bank import Bank
from kapso.learning.retriever import (
    append_pull_event,
    render_cards,
    render_index,
    render_sources_cards,
    render_sources_index,
)
from tests.test_bank_retriever import build_bank, card_text

TASK = {"family": "entity_binary_classification", "dataset": "rel-hm"}


def make_pull_bank(tmp_path):
    root = build_bank(tmp_path, {
        "strong-card": card_text("strong-card", score=0.8),
        "weak-card": card_text("weak-card", score=0.4),
        "avito-card": card_text("avito-card", scope=["dataset:rel-avito"]),
        "retired-state-card": card_text("retired-state-card", state="retired"),
        "decoy-card": card_text("decoy-card", score=0.9),
        "tension-a": card_text("tension-a", contradicts=("tension-b",)),
        "tension-b": card_text("tension-b", contradicts=("tension-a",)),
    })
    (root / ".decoys.yaml").write_text("- decoy-card\n")
    return Bank(str(root))


def test_index_is_the_whole_bank_no_filtering(tmp_path):
    bank = make_pull_bank(tmp_path)
    result = render_index(bank, TASK)
    names = [row["card"] for row in result["listed"]]
    # no scope filtering: the out-of-scope card is LISTED (2026-08-23
    # amendment — scope is displayed information, never a gate)
    assert "avito-card" in names
    # quarantine alone stays frame-side
    assert "retired-state-card" not in names
    assert "decoy-card" not in names
    assert {"strong-card", "weak-card", "tension-a", "tension-b"} <= set(names)
    # reliability order: strong before weak
    assert names.index("strong-card") < names.index("weak-card")
    assert all(row["exposure"] == "indexed" for row in result["listed"])


def test_reads_refuse_by_name_and_keep_decoys_unmarked(tmp_path):
    bank = make_pull_bank(tmp_path)
    result = render_cards(
        bank, TASK,
        ["strong-card", "avito-card", "retired-state-card", "decoy-card",
         "no-such-card"],
        False, {},
    )
    got_names = [row["card"] for row in result["served"]]
    # anything the index lists can be opened — the out-of-scope card reads
    assert got_names == ["strong-card", "avito-card"]
    assert all(row["exposure"] == "read" for row in result["served"])
    reasons = {r["card"]: r["reason"] for r in result["refused"]}
    assert "not servable" in reasons["retired-state-card"]
    # a decoy refuses exactly like a nonexistent card — quarantine unmarked
    assert reasons["decoy-card"] == reasons["no-such-card"] == "no such card"
    # the full card body is rendered for the got card (Rule 6: never
    # clipped), title-first per format v2, with the citation tag line
    assert "[card:strong-card]" in result["text"]
    assert "# Use group-relative signals when rows compete in a pool" in result["text"]
    assert "**Confidence:**" in result["text"]


def test_pull_events_append_as_jsonl(tmp_path):
    log = tmp_path / "campaign" / "serving-pull.jsonl"
    append_pull_event(str(log), {"tool": "bank_index", "eligible": 4})
    append_pull_event(str(log), {"tool": "bank_get_card", "served": []})
    rows = [json.loads(line) for line in log.read_text().splitlines()]
    assert [row["tool"] for row in rows] == ["bank_index", "bank_get_card"]
    assert all("ts" in row for row in rows)


def test_bank_gate_resolves_only_with_campaign_env():
    resolution = resolve_gates(["bank"], policy="skip", env={})
    assert resolution.enabled_gates == ()
    missing = resolution.diagnostics[0].missing_env
    assert "KAPSO_BANKS" in missing and "KAPSO_SERVING_PULL_LOG" in missing
    assert "KAPSO_TASK_HARNESS" in missing and "KAPSO_PROBE_BUDGET" in missing
    resolution = resolve_gates(["bank"], policy="skip", env={
        "KAPSO_BANKS": "[]",
        "KAPSO_SERVING_PULL_LOG": "/tmp/pull.jsonl",
        "KAPSO_TASK_HARNESS": "none",
        "KAPSO_PROBE_BUDGET": "1",
    })
    assert resolution.enabled_gates == ("bank",)


# ------------------------------------------------------ several banks


def make_two_banks(tmp_path):
    """Two loaded banks sharing one card name, the first with a decoy."""
    first_root = build_bank(tmp_path / "first", {
        "shared-card": card_text("shared-card", score=0.8),
        "only-first": card_text("only-first"),
        "decoy-card": card_text("decoy-card", score=0.9),
    })
    (first_root / ".decoys.yaml").write_text("- decoy-card\n")
    second_root = build_bank(tmp_path / "second", {
        "shared-card": card_text("shared-card", score=0.5),
        "only-second": card_text("only-second"),
    })
    return [
        ({"reference": "mine", "head": "aaa", "dir": str(first_root),
          "provenance": "measured by you", "scope": "harness"}, Bank(str(first_root))),
        ({"reference": "acme/kapso-bank", "head": "bbb", "dir": str(second_root),
          "provenance": "measured by others", "scope": "all"}, Bank(str(second_root))),
    ]


def test_sources_index_groups_by_source_and_one_bank_reads_plain(tmp_path):
    banks = make_two_banks(tmp_path)
    result = render_sources_index(banks, TASK)
    text = result["text"]
    assert text.index("# mine (measured by you)") < text.index("# acme/kapso-bank (measured by others)")
    rows = [(row["card"], row["source"]) for row in result["listed"]]
    assert ("shared-card", "mine") in rows and ("shared-card", "acme/kapso-bank") in rows
    assert ("only-second", "acme/kapso-bank") in rows
    # quarantine stays each bank's own
    assert ("decoy-card", "mine") not in rows
    assert result["listed_count"] == len(rows) == 4
    # one bank reads as the plain index: no source heading
    alone = render_sources_index(banks[:1], TASK)
    assert alone["text"] == render_index(banks[0][1], TASK)["text"]
    assert [row["source"] for row in alone["listed"]] == ["mine", "mine"]


def test_sources_cards_read_from_the_holder_or_the_named_source(tmp_path):
    banks = make_two_banks(tmp_path)
    # a name held by both reads from the first loaded bank unless a source is named
    first = render_sources_cards(banks, TASK, ["shared-card", "only-second"], False, {})
    assert [(row["card"], row["source"]) for row in first["served"]] == [
        ("shared-card", "mine"), ("only-second", "acme/kapso-bank"),
    ]
    named = render_sources_cards(banks, TASK, ["shared-card"], False, {}, source="acme/kapso-bank")
    assert [(row["card"], row["source"]) for row in named["served"]] == [("shared-card", "acme/kapso-bank")]
    # quarantine and unknown names refuse as one bank does; a source
    # nobody loaded refuses everything by name
    refused = render_sources_cards(banks, TASK, ["decoy-card", "no-such-card"], False, {})
    assert {r["card"]: r["reason"] for r in refused["refused"]} == {
        "decoy-card": "no such card", "no-such-card": "no such card",
    }
    nobody = render_sources_cards(banks, TASK, ["shared-card"], False, {}, source="ghost")
    assert nobody["served"] == []
    assert nobody["refused"] == [{"card": "shared-card", "reason": "no loaded source named ghost"}]
