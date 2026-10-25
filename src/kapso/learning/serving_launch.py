"""Serving at launch: the loaded sources pinned for one campaign (or one
host session), the intro compiled from them, the environment the gates
read. Frame-side, before any session exists; the network is never on the
path (a bank is cloned from its local home or clone, the hosted gate is
the session's own connection). Design: docs/plans/redesign/wp3-experience.md
("What a build does with the sources").

A campaign stages into `<work_dir>/.kapso/serving/`, so the harvested
trajectory carries the exact served state: one pinned clone per bank, the
serving record with the sources, and the sessions' pull log (the exposure
ladder's source). A host session stages the same under its own directory.
"""

import json
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from kapso.experience.reference import MINE
from kapso.experience.sources import SCOPE_ALL, ExperienceError, ExperienceSource
from kapso.harness.manifest import RESERVED_HARNESS_NAME as NO_HARNESS
from kapso.learning.bank import Bank
from kapso.learning.retriever import BANK_TOOLS_TEXT

HARNESS_COORDINATE = "harness"
INDEX_RECORD = "index.json"
_UNSAFE = re.compile(r"[^A-Za-z0-9_.-]+")


def task_coordinates(harness_name: Optional[str]) -> Dict[str, str]:
    """The campaign's coordinate: the loaded harness's name, or `none`."""
    return {HARNESS_COORDINATE: harness_name or NO_HARNESS}


def plan_serving(
    sources: List[ExperienceSource],
    task_coords: Dict[str, str],
    serve_dir,
    probe_budget: int,
) -> Optional[Dict[str, Any]]:
    """The serving PLAN: everything deterministic about one launch's
    serving, computed WITHOUT touching `serve_dir` (a campaign's may not
    exist yet). None without a source. `bank_serving` is exactly the
    environment stage will make true; `kg_index_path` the one index's
    record; `hosted` whether the hosted gate rides."""
    if not sources:
        return None
    serve_dir = Path(serve_dir).expanduser()
    banks = [s for s in sources if s.kind == "bank"]
    indexes = [s for s in sources if s.kind == "index"]
    if len(indexes) > 1:
        raise ExperienceError(
            "the search gates read one index per campaign; loaded: "
            + ", ".join(s.reference for s in indexes)
        )
    entries = [
        {
            "reference": s.reference, "head": s.head, "provenance": s.provenance, "scope": s.scope,
            "dir": str(serve_dir / "banks" / _dir_name(s)), "source": str(s.path),
        }
        for s in banks
    ]
    bank_serving: Dict[str, str] = {}
    if entries:
        bank_serving = {
            "KAPSO_BANKS": json.dumps([{k: e[k] for k in ("reference", "head", "dir", "provenance", "scope")} for e in entries]),
            "KAPSO_SERVING_PULL_LOG": str(serve_dir / "serving-pull.jsonl"),
            "KAPSO_TASK_HARNESS": task_coords[HARNESS_COORDINATE],
            "KAPSO_PROBE_BUDGET": str(probe_budget),
        }
    return {
        "serve_dir": str(serve_dir),
        "task": dict(task_coords),
        "banks": entries,
        "hosted": any(s.kind == "hosted" for s in sources),
        "kg_index_path": str(Path(indexes[0].path) / INDEX_RECORD) if indexes else None,
        "bank_serving": bank_serving,
        "sources": [vars(s.ref()) for s in sources],
    }


def plan_campaign_serving(
    sources: List[ExperienceSource], task_coords: Dict[str, str], work_dir, probe_budget: int,
) -> Optional[Dict[str, Any]]:
    """A campaign's plan: it serves from `<work_dir>/.kapso/serving`."""
    return plan_serving(sources, task_coords, Path(work_dir).expanduser() / ".kapso" / "serving", probe_budget)


def stage_serving(plan: Dict[str, Any], sources: List[ExperienceSource]) -> Dict[str, Any]:
    """Materialise a plan: one clone per bank at its pinned head, the
    intro with each source's count, the serving record. The directory may
    be created now."""
    serve_dir = Path(plan["serve_dir"])
    serve_dir.mkdir(parents=True, exist_ok=True)
    counts: Dict[str, int] = {}
    for entry in plan["banks"]:
        checkout = Path(entry["dir"])
        if checkout.exists():
            shutil.rmtree(checkout)
        checkout.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(["git", "clone", "--quiet", entry["source"], str(checkout)], check=True, capture_output=True)
        subprocess.run(["git", "-C", str(checkout), "checkout", "--quiet", entry["head"]], check=True, capture_output=True)
        head = subprocess.run(
            ["git", "-C", str(checkout), "rev-parse", "HEAD"], check=True, capture_output=True, text=True,
        ).stdout.strip()
        if head != entry["head"]:
            raise RuntimeError(f"{entry['reference']}: the clone is at {head}, not the pinned {entry['head']}")
        counts[entry["reference"]] = served_count(Bank(str(checkout)), entry["scope"], plan["task"])
    lines = source_lines(sources, counts, plan["task"])
    intro = compile_sources_intro(sources, lines)
    record_path = serve_dir / "serving-record.yaml"
    record = {
        "task": dict(plan["task"]),
        "sources": [
            {**source, **({"cards": counts[source["reference"]]} if source["reference"] in counts else {})}
            for source in plan["sources"]
        ],
    }
    with open(record_path, "w") as handle:
        yaml.safe_dump(record, handle, sort_keys=False)
    return {
        "intro": intro,
        "lines": lines,
        "bank_serving": plan["bank_serving"],
        "kg_index_path": plan["kg_index_path"],
        "hosted": plan["hosted"],
        "record_path": str(record_path),
        "sources": plan["sources"],
        "counts": counts,
    }


def prepare_campaign_serving(
    sources: List[ExperienceSource], task_coords: Dict[str, str], work_dir, probe_budget: int,
) -> Optional[Dict[str, Any]]:
    """Stage serving for one campaign launch; None without a source."""
    plan = plan_campaign_serving(sources, task_coords, work_dir, probe_budget)
    if plan is None:
        return None
    return stage_serving(plan, sources)


def served_count(bank: Bank, scope: str, task_coords: Dict[str, str]) -> int:
    """How many cards the campaign is served from one bank: every
    servable card when the scope is `all`, else the ones whose scope
    covers the task's coordinate."""
    servable = list(bank.servable())
    if scope == SCOPE_ALL:
        return len(servable)
    return sum(1 for card in servable if card.eligible_for(task_coords))


def source_lines(sources: List[ExperienceSource], counts: Dict[str, int], task_coords: Dict[str, str]) -> List[str]:
    """One line per source: what it is, how much of it is served under the
    task's coordinate, whose measurement it is. The intro and the launch
    banner both read these."""
    harness = task_coords[HARNESS_COORDINATE]
    under = f"under the {harness} harness" if harness != NO_HARNESS else "under no harness"
    lines: List[str] = []
    for source in sources:
        if source.kind == "bank":
            cards = counts.get(source.reference, 0)
            noun = f"{cards} card{'s' if cards != 1 else ''}"
            pinned = f"at head `{(source.head or '')[:12]}`, pinned for this campaign"
            if source.reference == MINE:
                where = "every scope" if source.scope == SCOPE_ALL else under
                lines.append(f"{noun} {source.provenance}, {where}, from your bank {pinned}")
            else:
                lines.append(f"{noun} from `{source.reference}`, {source.provenance}, every scope, {pinned}")
        elif source.kind == "hosted":
            lines.append(f"Leeroopedia's pages, {source.provenance}")
        else:
            pages = source.cards or 0
            lines.append(f"the `{source.reference}` corpus ({pages} page{'s' if pages != 1 else ''}), {source.provenance}")
    return lines


def compile_sources_intro(sources: List[ExperienceSource], lines: List[str]) -> str:
    """The intro the sessions read: the source lines, then how to read a
    bank and how a corpus is searched, for the kinds that are loaded."""
    text = ["## Experience (measured before)", "", "You are served:"] + [f"- {line}" for line in lines]
    if any(s.kind == "bank" for s in sources):
        text += ["", BANK_TOOLS_TEXT]
    if any(s.kind == "index" for s in sources):
        text += ["", "The corpus is searched with the `idea` and `code` tools: a query returns the pages that answer it."]
    return "\n".join(text)


def _dir_name(source: ExperienceSource) -> str:
    return _UNSAFE.sub("-", source.reference).strip("-") or "bank"
