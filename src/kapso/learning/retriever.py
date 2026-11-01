# Retriever — serving v2: agentic retrieval over the bank.
#
# Design: serving-agentic-redesign.md (supersedes §5.1's push/pull split).
# Push is an INTRODUCTION only — what the bank is and the three tools; no
# card content is selected or injected by the frame. Selection belongs to
# the reading agent: `render_index` returns the WHOLE BANK as book-index
# lines (name + hero + score + applies-when), and the agent opens cards
# with `render_cards` at two depths (body / body+evidence). The one
# filter on either surface is the scope rule (wp3-experience.md): your
# own bank at its default scope serves the cards whose scope covers the
# task's harness coordinate, `mine:all` and every bank you read serve
# everything; relevance judgment belongs to the reader; quarantine is law
# (decoys and retired states, frame-side, silent). Rank in the index is
# plain reliability order — no discounts, no k caps, no ranking cut. Everything here is a pure function of (task, bank
# checkout, bank_head): no agent, no clock, no randomness — the hindcast
# replays it at historical heads, byte-identical.
#
# Every tool call appends to a JSONL pull log — the serving record's
# exposure ladder source: `indexed` (index line shown) → `read` (body
# rendered) → `evidence-read` (body + reliability + evidence rendered).
# Attribution binds at `read` and above.

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from kapso.experience.reference import SCOPE_ALL
from kapso.experience.sources import PROVENANCE_REPORTED
from kapso.learning.bank import REPORTED_VERDICT, SERVABLE_STATES, Bank, Card
from kapso.learning.bank_invariants import INDEXED_ONLY, usage_claims_serving

# Probe-queue row grammar: the derived index is one file, readable by
# crews and parsed by the serve-time offer — structural constant, not a knob.
PROBE_QUEUE_RELPATH = "index/probe-queue.md"
_PROBE_ROW_PATTERN = re.compile(r"^\d+\. \[card:([a-z0-9][a-z0-9-]*)\] \(([^)]*)\) — (.+)$")

# The intro is the entire push surface (serving-agentic-redesign.md §4):
# what the bank is, the three tools in reading order, and the arbitrate
# line. No census, no card content, no citation instruction — the citation
# convention lives in the module prompts. The intro itself is compiled
# from the loaded sources (kapso.learning.serving_launch); this is the
# tools' part of it.
BANK_TOOLS_TEXT = """Three tools, in reading order:
- bank_index() — the whole bank as one index page: card name, one-liner,
  score, and when it applies. Cheap; call it whenever your next decision
  might have been faced before.
- bank_get_card(cards) — full card bodies (procedures include their code
  path).
- bank_get_card_with_evidence(cards) — the card plus its reliability and
  evidence trail, for due diligence before you stake real budget on its
  advice."""

# Probe offers ride card reads (§3.2), never the index or the intro. The
# cost clause is the wave-A lesson: a probe protocol silently adopted as
# the default gate taxed every experiment on a large dataset.
_PROBE_COST_CLAUSE = (
    "This is an optional measurement offer, not your default gate: adopt "
    "its protocol only if it is affordable at this dataset's scale, and "
    "say so explicitly. An ignored probe stays queued."
)


def _tension_pairs(cards: List[Card]) -> List[Tuple[str, str]]:
    """Co-serving guard input: contradicts pairs inside one returned set —
    always named, never silently side by side."""
    names = {card.name for card in cards}
    pairs: List[Tuple[str, str]] = []
    for card in cards:
        for other in card.frontmatter.get("contradicts") or []:
            pair = tuple(sorted((card.name, str(other))))
            if str(other) in names and pair not in pairs:
                pairs.append(pair)
    return pairs


def _gaps(eligible: List[Card]) -> List[str]:
    """The honest "what the bank does not know" — stated, never padded."""
    gaps = []
    if not any(card.type == "insight" for card in eligible):
        gaps.append("no insight in the bank covers this task's scope")
    if not any(card.type == "procedure" for card in eligible):
        gaps.append("no procedure in the bank covers this task's scope")
    return gaps


# ------------------------------------------------------------------ index

def _index_row(card: Card) -> Dict[str, Any]:
    return {
        "card": card.name,
        "version": (card.frontmatter.get("provenance") or {}).get("version"),
        "state": card.state,
        "score": card.score,
        "exposure": "indexed",
    }


def render_index(
    bank: Bank, task_coords: Dict[str, str], section: Optional[str] = None, scope: str = SCOPE_ALL,
) -> Dict[str, Any]:
    """bank_index: the bank as book-index lines.

    One line-group per card — `[card:name] score X` / hero one-liner /
    `applies-when:` (the card's authored scope_conditions, when present) —
    reliability-ordered within `## Insights` / `## Procedures` sections,
    closing with the gaps footer. Nothing is pre-selected for the reader
    beyond the scope rule (docs/plans/redesign/wp3-experience.md): under
    `scope="harness"` (`mine` at its default) only the cards whose scope
    covers the task's coordinate are listed; under `scope="all"` (`mine:all`,
    every bank you read) the whole bank is. Relevance judgment belongs to
    the calling agent, scanning the applies-when lines with its own plan in
    mind. Quarantine stays frame-side under every scope (servable()
    excludes decoys and retired states, silently). The gaps footer reports
    scope coverage for THIS task."""
    listed_cards = list(bank.servable())
    gaps = _gaps([c for c in listed_cards if c.eligible_for(task_coords)])
    if scope != SCOPE_ALL:
        listed_cards = [c for c in listed_cards if c.eligible_for(task_coords)]
    if section:
        if section not in ("insights", "procedures"):
            raise ValueError(f"unknown index section: {section}")
        wanted = "insight" if section == "insights" else "procedure"
        listed_cards = [c for c in listed_cards if c.type == wanted]
    listed_cards.sort(key=lambda card: (-float(card.score or 0.0), card.name))

    sections: List[str] = []
    for kind, heading in (("insight", "## Insights"),
                          ("procedure", "## Procedures")):
        cards = [c for c in listed_cards if c.type == kind]
        if not cards:
            continue
        lines = [heading]
        for card in cards:
            lines.append(f"[card:{card.name}] score {card.score}")
            lines.append(f"  — {card.hero}")
            conditions = card.frontmatter.get("scope_conditions")
            if conditions:
                lines.append(
                    "  applies-when: " + " ".join(str(conditions).split())
                )
        sections.append("\n".join(lines))

    if not listed_cards:
        sections.append(
            "The bank holds NO card yet — this is its whole answer; "
            "nothing else exists."
        )
    for gap in gaps:
        sections.append(f"gaps: {gap}")
    return {
        "text": "\n\n".join(sections),
        "listed": [_index_row(card) for card in listed_cards],
        "gaps": gaps,
        "listed_count": len(listed_cards),
    }


# ------------------------------------------------------------------ cards

def probe_offers(
    bank: Bank, task_coords: Dict[str, str], probe_budget: int
) -> Dict[str, str]:
    """The serve-time probe offers: the first `probe_budget` queue rows
    whose cards are servable and eligible for this task. Offers ride card
    reads only; the cap keeps learning from cannibalizing doing. An
    ignored probe stays queued."""
    offers: Dict[str, str] = {}
    queue_path = bank.root / PROBE_QUEUE_RELPATH
    if not probe_budget or not queue_path.is_file():
        return offers
    servable_names = {card.name for card in bank.servable()}
    for line in queue_path.read_text().splitlines():
        match = _PROBE_ROW_PATTERN.match(line)
        if not match:
            continue
        name, _tier, probe_text = match.groups()
        card = bank.cards.get(name)
        if (
            card is None or name not in servable_names
            or not card.eligible_for(task_coords)
        ):
            continue
        offers[name] = probe_text
        if len(offers) >= probe_budget:
            break
    return offers


def _procedure_locations(bank: Bank, card: Card) -> List[str]:
    """A procedure's on-disk payload in the serving checkout: the code dir
    (entrypoint inside it) and the replay dir. A prose-only procedure (not
    yet code-flipped) has no code dir — the documented default is to omit
    the block rather than point at nothing."""
    lines: List[str] = []
    base = bank.root / "procedures" / card.name
    code_dir = base / "code"
    if code_dir.is_dir():
        lines.append(f"code: {code_dir}")
        entrypoint = card.frontmatter.get("entrypoint")
        if entrypoint:
            lines.append(f"entrypoint: {base / str(entrypoint)}")
    replay_dir = base / "replay"
    if replay_dir.is_dir():
        lines.append(f"replay: {replay_dir}")
    return lines


def _reliability_block(card: Card) -> str:
    reliability = card.reliability
    scores = " ".join(
        f"{dim}={reliability.get(dim)}"
        for dim in ("validity", "boundary", "coverage", "score")
    )
    lines = [
        "### Reliability",
        f"- state={card.state} version="
        f"{(card.frontmatter.get('provenance') or {}).get('version')} {scores}",
        f"- plain: {reliability.get('plain')}",
        f"- rationale: {' '.join(str(reliability.get('rationale') or '').split())}",
    ]
    return "\n".join(lines)


def _evidence_block(card: Card) -> str:
    """The full evidence trail — every entry whole (Rule 6: depth selects
    sections, never cuts within one)."""
    lines = [f"### Evidence ({len(card.evidence)} entries)"]
    for entry in card.evidence:
        source = entry.get("source") or {}
        if entry.get("verdict") == REPORTED_VERDICT:
            lines.append(
                f"- verdict={REPORTED_VERDICT} ({PROVENANCE_REPORTED}, not a kapso "
                f"measurement) url={source.get('url')} author={source.get('author')} "
                f"licence={source.get('licence')} score={source.get('score')} "
                f"protocol={source.get('protocol')}"
            )
        else:
            lines.append(
                f"- verdict={entry.get('verdict')} "
                f"trajectory={source.get('trajectory')} ref={source.get('ref')}"
            )
        for field in ("usage", "effect", "note"):
            value = entry.get(field)
            if value:
                lines.append(f"  {field}: {' '.join(str(value).split())}")
    return "\n".join(lines)


def _render_card(
    bank: Bank,
    card: Card,
    with_evidence: bool,
    offers: Dict[str, str],
) -> str:
    """One card at the requested depth: citation tag + the full v2 body
    (the body IS the engineer-facing card, carried whole — Rule 6), plus
    the procedure payload paths, the provenance line of a card whose only
    evidence is reported by others, the probe offer when one is queued,
    and — at evidence depth — the reliability block and full evidence
    trail."""
    lines = [f"[card:{card.name}]", card.body]
    locations = (
        _procedure_locations(bank, card) if card.type == "procedure" else []
    )
    if locations:
        lines.append("\n".join(locations))
    if card.reported_only:
        lines.append(
            f"*provenance:* {PROVENANCE_REPORTED} — the score is the source's, not a "
            f"kapso measurement; no campaign has run this card yet."
        )
    if card.name in offers:
        lines.append(
            f"*probe:* {offers[card.name]}\n*{_PROBE_COST_CLAUSE}*"
        )
    if with_evidence:
        lines.append(_reliability_block(card))
        lines.append(_evidence_block(card))
    return "\n\n".join(lines)


def render_cards(
    bank: Bank,
    task_coords: Dict[str, str],
    card_names: List[str],
    with_evidence: bool,
    offers: Dict[str, str],
    scope: str = SCOPE_ALL,
) -> Dict[str, Any]:
    """bank_get_card / bank_get_card_with_evidence: full cards on request.

    Anything the index shows can be opened: the scope rule that filters
    the index filters the reads the same way (a card outside the task's
    coordinate refuses by name under `scope="harness"`, and names the
    lift). Quarantine stays law: decoys refuse as unknown, and
    non-servable states refuse by name. The co-serving guard names
    contradicts pairs inside one returned set."""
    exposure = "evidence-read" if with_evidence else "read"
    decoys = bank.decoy_names
    got: List[Card] = []
    refused: List[Dict[str, str]] = []
    for name in card_names:
        card = bank.cards.get(name)
        if card is None or name in decoys:
            # Decoys refuse as unknown — naming the quarantine would mark
            # the bait (quarantine is frame-side knowledge).
            refused.append({"card": name, "reason": "no such card"})
        elif card.state not in ("candidate", "active"):
            refused.append(
                {"card": name, "reason": f"not servable (state={card.state})"}
            )
        elif scope != SCOPE_ALL and not card.eligible_for(task_coords):
            refused.append({
                "card": name,
                "reason": (
                    f"out of scope under harness:{task_coords.get('harness')} "
                    f"(scope {card.scope!r}; `mine:all` serves every card you measured)"
                ),
            })
        else:
            got.append(card)
    tensions = _tension_pairs(got)
    sections = [
        _render_card(bank, card, with_evidence, offers) for card in got
    ]
    for first, second in tensions:
        sections.append(
            f"**Contested:** [card:{first}] and [card:{second}] disagree on "
            f"overlapping scope; the boundary is unresolved — treat as "
            f"contested."
        )
    for refusal in refused:
        sections.append(f"*not served:* {refusal['card']} — {refusal['reason']}")
    return {
        "text": "\n\n".join(sections) if sections else "nothing served",
        "served": [
            {
                "card": card.name,
                "version": (card.frontmatter.get("provenance") or {}).get("version"),
                "state": card.state,
                "score": card.score,
                "exposure": exposure,
            }
            for card in got
        ],
        "refused": refused,
        "tensions": [list(pair) for pair in tensions],
    }


# --------------------------------------------------------------- sources

def render_sources_index(
    banks: List[Tuple[Dict[str, Any], Bank]], task_coords: Dict[str, str], section: Optional[str] = None,
) -> Dict[str, Any]:
    """`bank_index` over every loaded bank: each bank's index under a
    heading naming the source and whose measurement it is; one bank reads
    as the plain index. `banks` pairs a serving entry (reference,
    provenance, head, scope) with its pinned checkout."""
    texts: List[str] = []
    listed: List[Dict[str, Any]] = []
    gaps: List[str] = []
    for entry, bank in banks:
        result = render_index(bank, task_coords, section, entry["scope"])
        if len(banks) > 1:
            texts.append(f"# {entry['reference']} ({entry['provenance']})\n\n{result['text']}")
        else:
            texts.append(result["text"])
        listed.extend({**row, "source": entry["reference"]} for row in result["listed"])
        gaps.extend(result["gaps"])
    return {"text": "\n\n".join(texts), "listed": listed, "gaps": gaps, "listed_count": len(listed)}


def _can_serve(entry: Dict[str, Any], bank: Bank, name: str, task_coords: Dict[str, str]) -> bool:
    """Whether one loaded bank serves a card by name: held, in a servable
    state, not quarantined, and within the bank's scope for the task."""
    card = bank.cards.get(name)
    if card is None or card.state not in SERVABLE_STATES or name in bank.decoy_names:
        return False
    return entry["scope"] == SCOPE_ALL or card.eligible_for(task_coords)


def render_sources_cards(
    banks: List[Tuple[Dict[str, Any], Bank]],
    task_coords: Dict[str, str],
    card_names: List[str],
    with_evidence: bool,
    offers_by_source: Dict[str, Dict[str, str]],
    source: Optional[str] = None,
) -> Dict[str, Any]:
    """`bank_get_card` over every loaded bank: a name is read from the
    named source, else from the first loaded bank that holds it; the
    served rows carry the source. Quarantine and state refusals are each
    bank's own (render_cards)."""
    chosen = [pair for pair in banks if source is None or pair[0]["reference"] == source]
    if source is not None and not chosen:
        return {
            "text": f"nothing served: no loaded source named {source}",
            "served": [], "tensions": [],
            "refused": [{"card": name, "reason": f"no loaded source named {source}"} for name in card_names],
        }
    by_source: Dict[str, List[str]] = {}
    unknown: List[str] = []
    for name in card_names:
        # The first loaded bank that can serve the name under its scope;
        # when none can, the first that holds it, whose refusal says why.
        holders = [entry for entry, bank in chosen if name in bank.cards]
        serving = [entry for entry, bank in chosen if _can_serve(entry, bank, name, task_coords)]
        holder = (serving or holders or [None])[0]
        if holder is None:
            unknown.append(name)
        else:
            by_source.setdefault(holder["reference"], []).append(name)
    texts: List[str] = []
    served: List[Dict[str, Any]] = []
    refused: List[Dict[str, str]] = []
    tensions: List[List[str]] = []
    for entry, bank in chosen:
        names = by_source.get(entry["reference"])
        if not names:
            continue
        result = render_cards(
            bank, task_coords, names, with_evidence, offers_by_source.get(entry["reference"], {}), entry["scope"],
        )
        texts.append(result["text"])
        served.extend({**row, "source": entry["reference"]} for row in result["served"])
        refused.extend(result["refused"])
        tensions.extend(result["tensions"])
    for name in unknown:
        refused.append({"card": name, "reason": "no such card"})
        texts.append(f"*not served:* {name} — no such card")
    return {"text": "\n\n".join(texts) if texts else "nothing served", "served": served, "refused": refused, "tensions": tensions}


# ----------------------------------------------------------- probe queue

def compile_probe_queue(bank: Bank) -> str:
    """The VoI-ranked open-probe queue — recompiled by the frame each
    update run, every input ledger-derived, no agent in the ranking.

    Rows are servable, non-decoy cards with an open `probe:` field, in three
    tiers: (1) served-unverified — voi = uncertainty (1 − validity; missing
    counts as 1) × serving exposure (evidence entries whose usage claims
    participation), heavily-served-thinly-verified first; (2) boundary —
    cards in a contradicts pair, whose probe would carve a scope; (3)
    blocked — candidates with zero outcome verdicts, promotion pending
    measurement. Remaining open probes tail the queue by name."""
    decoys = bank.decoy_names
    open_probes = [
        card for card in bank.servable()
        if card.name not in decoys
        and str(card.frontmatter.get("probe") or "").strip()
    ]
    contested = {
        card.name for card in open_probes
        if card.frontmatter.get("contradicts")
    }

    def uncertainty(card: Card) -> float:
        validity = card.reliability.get("validity")
        return 1.0 - float(validity) if isinstance(validity, (int, float)) else 1.0

    def exposure(card: Card) -> int:
        return sum(
            1 for entry in card.evidence
            if usage_claims_serving(str(entry.get("usage") or ""))
        )

    def outcomes(card: Card) -> int:
        return sum(
            1 for entry in card.evidence
            if entry.get("verdict") in ("confirm", "weaken", "refute")
        )

    tier1 = sorted(
        (card for card in open_probes if exposure(card) > 0),
        key=lambda c: (-(uncertainty(c) * exposure(c)), c.name),
    )
    listed = {card.name for card in tier1}
    tier2 = sorted(
        (c for c in open_probes if c.name in contested and c.name not in listed),
        key=lambda c: c.name,
    )
    listed |= {card.name for card in tier2}
    tier3 = sorted(
        (c for c in open_probes
         if c.state == "candidate" and outcomes(c) == 0 and c.name not in listed),
        key=lambda c: c.name,
    )
    listed |= {card.name for card in tier3}
    tail = sorted(
        (c for c in open_probes if c.name not in listed), key=lambda c: c.name
    )

    rows = []
    for card in tier1:
        voi = uncertainty(card) * exposure(card)
        rows.append((card, f"served-unverified voi={voi:.2f}"))
    rows += [(card, "boundary: contradicts unresolved") for card in tier2]
    rows += [(card, "blocked: candidate with no outcome verdict") for card in tier3]
    rows += [(card, "queued") for card in tail]

    lines = ["# Probe queue — value-of-information ranked (derived; frame-compiled)", ""]
    for index, (card, tier) in enumerate(rows, start=1):
        probe = " ".join(str(card.frontmatter["probe"]).split())
        lines.append(f"{index}. [card:{card.name}] ({tier}) — {probe}")
    if not rows:
        lines.append("(no open probes)")
    return "\n".join(lines) + "\n"


# --------------------------------------------------------------- pull log

def append_pull_event(log_path: str, event: Dict[str, Any]) -> None:
    """One serving event to the pull log — append-only JSONL beside the
    launch record; the harvester collects both and the exam derives the
    exposure ladder from it. Timestamps are operational (tool calls are
    live agent interaction, never replayed like the index)."""
    path = Path(log_path).expanduser()
    path.parent.mkdir(parents=True, exist_ok=True)
    stamped = {
        "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        **event,
    }
    with open(path, "a") as handle:
        handle.write(json.dumps(stamped) + "\n")


EXPOSURE_LEVELS = (INDEXED_ONLY, "read", "evidence-read")


def exposure_ladder(log_path) -> Dict[str, Dict[str, str]]:
    """The pull log read back: for every card name, the highest exposure
    each loaded source gave it — `{card: {source: level}}`, the shape the
    evidence check credits usage claims against (a cited name belongs to
    the source it was read from). A malformed line raises; the log is
    evidence, not a hint."""
    ladder: Dict[str, Dict[str, str]] = {}

    def raise_to(card: str, source: str, level: str) -> None:
        current = ladder.setdefault(card, {}).get(source)
        if current is None or EXPOSURE_LEVELS.index(level) > EXPOSURE_LEVELS.index(current):
            ladder[card][source] = level

    for number, line in enumerate(Path(log_path).read_text().splitlines(), start=1):
        if not line.strip():
            raise ValueError(f"{log_path}:{number}: an empty line in the pull log")
        event = json.loads(line)
        for row in event.get("listed", []):
            raise_to(row["card"], row["source"], "indexed")
        for row in event.get("served", []):
            raise_to(row["card"], row["source"], row["exposure"])
    return ladder
