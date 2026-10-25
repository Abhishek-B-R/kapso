"""
Bank Gate
=========
Knowledge-bank tools for campaign sessions (serving-agentic-redesign.md;
docs/plans/redesign/wp3-experience.md for the sources): `bank_index`
returns every loaded bank's eligible set as book-index lines, grouped by
source (the calling agent is the selector), `bank_get_card` renders full
card bodies from the source that holds the name, and
`bank_get_card_with_evidence` adds the reliability block and the full
evidence trail for due diligence. Eligibility and quarantine are law on
all three. Every call appends to the campaign's pull log, the serving
record's exposure ladder source (attribution binds at `read` and above).

The gate is a thin subprocess wrapper over the pure functions in
`kapso.learning.retriever`; its per-campaign parameters arrive through the
same env-injection channel the sibling gates use (set by the launching
runner, never read by core kapso code):

- KAPSO_BANKS             JSON list of the loaded banks: {reference, head, dir, provenance, scope}, each dir a pinned checkout
- KAPSO_SERVING_PULL_LOG  JSONL pull-log path inside the campaign workspace
- KAPSO_TASK_HARNESS      the task's coordinate: the loaded harness's name, or `none`
- KAPSO_PROBE_BUDGET      max probe offers riding card reads this campaign

The feedback judge never gets this gate — a judge reading the bank couples
the evaluator to the thing under evaluation (§6).
"""

import json
import logging
import os
from typing import Any, Dict, List, Optional, Tuple

try:
    from mcp.types import Tool, TextContent
    HAS_MCP = True
except ImportError:
    HAS_MCP = False
    Tool = None
    TextContent = None

from kapso.gated_mcp.gates.base import ToolGate, GateConfig

logger = logging.getLogger(__name__)


class BankGate(ToolGate):
    """Gate for the knowledge-bank tools (index / get-card / get-card-with-evidence)."""

    name = "bank"
    description = "Knowledge-bank tools (book index + full cards at two depths) over every loaded bank"

    def __init__(self, config: Optional[GateConfig] = None):
        super().__init__(config)
        self._banks: Optional[List[Tuple[Dict[str, Any], Any]]] = None
        self._offers: Optional[Dict[str, Dict[str, str]]] = None

    def _get_banks(self) -> List[Tuple[Dict[str, Any], Any]]:
        if self._banks is None:
            from kapso.learning.bank import Bank
            entries = json.loads(os.environ["KAPSO_BANKS"])
            self._banks = [(entry, Bank(entry["dir"])) for entry in entries]
        return self._banks

    def _task_coords(self) -> Dict[str, str]:
        return {"harness": os.environ["KAPSO_TASK_HARNESS"]}

    def _probe_offers(self) -> Dict[str, Dict[str, str]]:
        if self._offers is None:
            from kapso.learning.retriever import probe_offers
            budget = int(os.environ["KAPSO_PROBE_BUDGET"])
            self._offers = {
                entry["reference"]: probe_offers(bank, self._task_coords(), budget)
                for entry, bank in self._get_banks()
            }
        return self._offers

    def get_tools(self) -> List["Tool"]:
        if not HAS_MCP:
            return []
        source_property = {
            "source": {
                "type": "string",
                "description": (
                    "Optional: the loaded bank to read from, as bank_index names it "
                    "(a name held by several banks is read from the first that holds it otherwise)"
                ),
            },
        }
        return [
            Tool(
                name="bank_index",
                description=(
                    "The loaded banks' full index: every card, one line each — "
                    "name, one-liner, score, and when it applies — like the "
                    "index of a book, grouped by source with whose measurement "
                    "it is. Nothing is pre-selected or filtered for you; judge "
                    "relevance from each applies-when line against your own "
                    "plan, then open the cards worth reading with bank_get_card."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "section": {
                            "type": "string",
                            "enum": ["insights", "procedures"],
                            "description": "Optional: restrict to one section; omit for the whole index",
                        },
                    },
                },
            ),
            Tool(
                name="bank_get_card",
                description=(
                    "Full card bodies for named bank cards (title, rule, "
                    "situation, what to do, why believe it). Procedures "
                    "include their runnable code location. Anything the "
                    "index lists can be opened."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "cards": {"type": "array", "items": {"type": "string"}, "description": "Card names from bank_index"},
                        **source_property,
                    },
                    "required": ["cards"],
                },
            ),
            Tool(
                name="bank_get_card_with_evidence",
                description=(
                    "Named cards at due-diligence depth: the full body "
                    "plus the reliability block and the complete evidence "
                    "trail (per-entry trajectory, verdict, effect). Use "
                    "before staking real budget on a card's advice."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "cards": {"type": "array", "items": {"type": "string"}, "description": "Card names from bank_index"},
                        **source_property,
                    },
                    "required": ["cards"],
                },
            ),
        ]

    async def handle_call(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
    ) -> Optional[List["TextContent"]]:
        if not HAS_MCP:
            return None
        from kapso.learning.retriever import (
            append_pull_event,
            render_sources_cards,
            render_sources_index,
        )
        banks = self._get_banks()
        coords = self._task_coords()
        log_path = os.environ["KAPSO_SERVING_PULL_LOG"]
        heads = {entry["reference"]: entry["head"] for entry, _bank in banks}
        if tool_name == "bank_index":
            section = arguments.get("section") or None
            result = render_sources_index(banks, coords, section)
            append_pull_event(log_path, {
                "tool": "bank_index",
                "section": section,
                "task": coords,
                "sources": heads,
                "listed_count": result["listed_count"],
                "listed": result["listed"],
            })
            return [TextContent(type="text", text=result["text"])]
        if tool_name in ("bank_get_card", "bank_get_card_with_evidence"):
            with_evidence = tool_name == "bank_get_card_with_evidence"
            card_names = [str(n) for n in arguments.get("cards", [])]
            source = arguments.get("source") or None
            result = render_sources_cards(banks, coords, card_names, with_evidence, self._probe_offers(), source)
            append_pull_event(log_path, {
                "tool": tool_name,
                "requested": card_names,
                "source": source,
                "task": coords,
                "sources": heads,
                "served": result["served"],
                "refused": result["refused"],
                "tensions": result["tensions"],
            })
            return [TextContent(type="text", text=result["text"])]
        return None
