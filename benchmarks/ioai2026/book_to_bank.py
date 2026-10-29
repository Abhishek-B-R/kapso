# The IOAI book as a bank kapso serves. The book — one directory per past olympiad
# task with problem.md, idea.md and solution/ — becomes a bank the serving
# layer reads: one procedure card per entry at procedures/<uid>/card.md with
# the solution files under procedures/<uid>/code/, the card's one evidence
# entry `reported` (the score at its source, who reported it, under what
# licence, by what protocol), the card born `candidate`. The licence pass
# over the book (provenance.json, one row per entry) decides membership:
# --verdicts names the pass's verdicts a bank takes, so the shareable bank is
# `shippable-with-attribution` + `ours (shippable)` and the local-only bank
# the rest; --exclude drops entries by uid (a campaign on one of the book's
# tasks is served the bank without its own entry). --table writes the pass's
# rows with this second pass's columns. docs/plans/redesign/wp8-harness-ports.md
# change 15.
#
#   python benchmarks/ioai2026/book_to_bank.py --book DIR --provenance provenance.json \
#       --out DIR --verdicts shippable-with-attribution "ours (shippable)" \
#       [--set bank] [--exclude UID ...] [--table PATH]

import argparse
import json
import re
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from kapso.learning.bank import REPORTED_VERDICT, dump_ledger
from kapso.learning.bank_invariants import BODY_SECTIONS

VERDICTS = ("shippable-with-attribution", "ours (shippable)", "local-only", "excluded")
SHAREABLE_VERDICTS = ("shippable-with-attribution", "ours (shippable)")
SETS = ("bank", "reserve")
ROW_KEYS = (
    "uid", "set", "tier", "contest", "holds", "source_kind", "author", "urls", "licence",
    "evidence", "verdict", "files_copied", "files_ours",
)
# The book's tiers and statuses (INDEX.md), in the words the card's evidence
# carries: what the reported score rests on.
TIER_PHRASES = {
    "sure-gold": "the book's proof-grade tier",
    "claimed-max": "an author-claimed maximum under the book's review",
    "e1-active": "our reimplementation of a winner's write-up, in flight",
    "reference": "a literature survey without a score",
}
PROTOCOLS = {
    "solution-in": (
        "the solution as published at the source, copied, not re-run by us; the score is "
        "the source's own or the public leaderboard's"
    ),
    "solution-in verified": (
        "the copied solution re-run by us on the task's official grader or its mirror, "
        "the score matching the source's"
    ),
    "described": "the method as described at the source; no solution code",
    "reference-only": "a literature survey compiled by us from public sources; no task, no score",
}
PROBE = (
    "Run the solution under code/ on the task's data, or the idea on a like task, and "
    "record the measured score as a kapso trajectory: the first executed verdict."
)
_ROUTER_SECTION = re.compile(r"^## §\d+ (.+)$")
_ROUTER_ENTRY = re.compile(r"^- \S+ \[(\w+)\] ([a-z0-9-]+) — (.+)$")
_INDEX_ROW = re.compile(r"^\| ([a-z0-9-]+) \| ([^|]+) \|")
_RECORD_LINE = re.compile(r"^(status|best): (.+)$", re.M)
_HEADING = re.compile(r"^(#{1,2}) (.+)$")
_DEMOTED = re.compile(r"^(#{1,4}) ")
_UNSTATED_PREFIXES = ("none stated", "not established", "each checked page")
_OPEN_QUESTION = re.compile(r"OQ-\d+")


# --------------------------------------------------------------- the inputs

def load_rows(path: Path) -> List[Dict[str, Any]]:
    """The licence pass's rows, each checked for its keys, set and verdict:
    a row the converter cannot read stops the conversion (CLAUDE.md Rule 2)."""
    rows = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(rows, list):
        raise ValueError(f"{path}: the provenance table is not a list of rows")
    for index, row in enumerate(rows):
        label = f"{path} row {index}"
        if not isinstance(row, dict):
            raise ValueError(f"{label}: not a mapping")
        missing = [key for key in ROW_KEYS if key not in row]
        if missing:
            raise ValueError(f"{label}: missing {', '.join(missing)}")
        label = f"{label} ({row['uid']})"
        if row["verdict"] not in VERDICTS:
            raise ValueError(f"{label}: verdict {row['verdict']!r} is not one of {VERDICTS}")
        if row["set"] not in SETS:
            raise ValueError(f"{label}: set {row['set']!r} is not one of {SETS}")
        for key in ("urls", "files_copied", "files_ours"):
            if not isinstance(row[key], list):
                raise ValueError(f"{label}: {key} is not a list")
    return rows


def book_entries(book: Path) -> Dict[str, Path]:
    """The book's entries: every directory holding idea.md and problem.md."""
    entries = {
        directory.name: directory
        for directory in sorted(path for path in book.iterdir() if path.is_dir())
        if (directory / "idea.md").is_file() and (directory / "problem.md").is_file()
    }
    if not entries:
        raise ValueError(f"{book}: no entry (a directory with idea.md and problem.md)")
    return entries


def rows_for(rows: List[Dict[str, Any]], entries: Dict[str, Path], which: str) -> Dict[str, Dict[str, Any]]:
    """The set's rows by uid: exactly one per book entry, none for an entry
    the book lacks."""
    by_uid: Dict[str, Dict[str, Any]] = {}
    for row in rows:
        if row["set"] != which:
            continue
        if row["uid"] in by_uid:
            raise ValueError(f"two {which} rows for {row['uid']}")
        if row["uid"] not in entries:
            raise ValueError(f"{which} row {row['uid']} names no entry of the book")
        by_uid[row["uid"]] = row
    missing = sorted(set(entries) - set(by_uid))
    if missing:
        raise ValueError(f"book entries without a {which} row: {', '.join(missing)}")
    return by_uid


def router(book: Path) -> Dict[str, Dict[str, str]]:
    """book_index.md, the book's router: each routed entry's modality tag,
    section and one-line title. A book without one routes nothing."""
    path = book / "book_index.md"
    if not path.is_file():
        return {}
    routed: Dict[str, Dict[str, str]] = {}
    section = ""
    for line in path.read_text(encoding="utf-8").splitlines():
        heading = _ROUTER_SECTION.match(line)
        if heading:
            section = heading.group(1).strip()
            continue
        entry = _ROUTER_ENTRY.match(line)
        if entry:
            tag, uid, title = entry.groups()
            routed[uid] = {"tag": tag, "section": section, "title": title.strip()}
    return routed


def index_tiers(book: Path) -> Dict[str, str]:
    """INDEX.md, the book's tier table: the tier per uid."""
    path = book / "INDEX.md"
    if not path.is_file():
        raise FileNotFoundError(f"{book}: INDEX.md (the tier table) is missing")
    tiers: Dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        match = _INDEX_ROW.match(line)
        if match and match.group(1) not in ("uid", "---"):
            tiers[match.group(1)] = match.group(2).strip()
    return tiers


def entry_record(uid: str, idea_text: str) -> Dict[str, str]:
    """The entry's own record at the foot of its idea page: `status:` (what
    the entry holds) and `best:` (the best-known score and the review's
    verdict on it), one line each."""
    record: Dict[str, str] = {}
    for key, value in _RECORD_LINE.findall(idea_text):
        if key in record:
            raise ValueError(f"{uid}: idea.md carries two `{key}:` lines")
        record[key] = value.strip()
    missing = [key for key in ("status", "best") if key not in record]
    if missing:
        raise ValueError(f"{uid}: idea.md has no `{'`, `'.join(missing)}:` line")
    return record


# ------------------------------------------------------------- the licence

def stated_licence(text: str) -> str:
    """The licence names the pass read at the source(s), "unstated" where it
    read none; "ours" for a row of our own code."""
    if text.startswith("n/a"):
        return "ours (no third-party code)"
    names = []
    for part in re.split(r"\s+//\s+", text):
        part = re.sub(r"^\[\w+\]\s*", "", part.strip())
        name = re.split(r"\s+—\s+|\s*\(|;", part, maxsplit=1)[0].strip()
        names.append("unstated" if name.lower().startswith(_UNSTATED_PREFIXES) else name)
    return " // ".join(names)


def open_questions(row: Dict[str, Any]) -> List[str]:
    return sorted(set(_OPEN_QUESTION.findall(f"{row['verdict']} {row.get('note', '')} {row['licence']}")))


def use_verdict(row: Dict[str, Any]) -> str:
    """Whether the owner's own runs may be served the entry: our code and
    permissively licensed material, yes (the attribution rides in the card
    and the table); everything else is the owner's call, the open questions
    named."""
    if row["verdict"] == "ours (shippable)":
        return "yes — our own code"
    if row["verdict"] == "shippable-with-attribution":
        return "yes — attribution kept in the card and this table"
    questions = open_questions(row)
    return "owner's call" + (f" ({', '.join(questions)})" if questions else " (licence unstated or restricted)")


def publish_verdict(row: Dict[str, Any]) -> str:
    """The bank the entry goes to under the pass's verdict, with the open
    questions that qualify it."""
    bank = "shareable" if row["verdict"] in SHAREABLE_VERDICTS else "local-only"
    questions = open_questions(row)
    return f"{row['verdict']} → the {bank} bank" + (f" ({', '.join(questions)})" if questions else "")


def third_party_payload(row: Dict[str, Any]) -> str:
    copied = row["files_copied"]
    return f"{len(copied)} copied: {', '.join(copied)}" if copied else "none"


def our_files(row: Dict[str, Any]) -> str:
    """Our own files under the entry, each with its class: a derivative of a
    copied file carries that file's licence; a reimplementation is ours
    (idea only, no copied code, cited); a byproduct is not shipped."""
    kinds = []
    for item in row["files_ours"]:
        name, lowered = item.split(" ")[0], item.lower()
        if "byproduct" in lowered or ".pyc" in lowered:
            kinds.append(f"{name}: byproduct, not shipped")
        elif "reimpl" in lowered:
            kinds.append(f"{name}: our reimplementation — idea only, no copied code, cited")
        elif "derivative" in lowered or "extraction" in lowered:
            kinds.append(f"{name}: derivative of the copied file, its licence")
        else:
            kinds.append(f"{name}: ours")
    return "; ".join(kinds) if kinds else "none"


def _cell(text: Any) -> str:
    return " ".join(str(text).split()).replace("|", "\\|")


def render_table(rows: List[Dict[str, Any]]) -> str:
    """The rows as one markdown table: the first pass's columns and this
    pass's (the stated licence, use, publish, the third-party payload, our
    files)."""
    lines = [
        "| uid | tier | contest | stated licence | use | publish | third-party payload | our files "
        "| author | URL(s) | licence at the source (verbatim) | evidence |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for row in rows:
        lines.append("| " + " | ".join(_cell(cell) for cell in (
            row["uid"], row["tier"], row["contest"], stated_licence(row["licence"]), use_verdict(row),
            publish_verdict(row), third_party_payload(row), our_files(row), row["author"],
            "<br>".join(row["urls"]), row["licence"], row["evidence"],
        )) + " |")
    return "\n".join(lines)


def render_pass(rows: List[Dict[str, Any]], stamp: datetime) -> str:
    """The second pass over every row of the licence table, for the record."""
    counts = {which: [row for row in rows if row["set"] == which] for which in SETS}
    shareable = sum(1 for row in rows if row["verdict"] in SHAREABLE_VERDICTS)
    licences: Dict[str, int] = {}
    for row in rows:
        licences[stated_licence(row["licence"])] = licences.get(stated_licence(row["licence"]), 0) + 1
    parts = [
        "# Provenance and licence table — IOAI book, second pass",
        "",
        f"Written by `benchmarks/ioai2026/book_to_bank.py --table` on {stamp:%Y-%m-%d} from the first "
        "pass's `provenance.json` (one row per book entry, the licence read at every cited source). "
        "This pass adds, mechanically: the stated licence (the name the first pass read at the "
        "source, or \"unstated\"), the use verdict (whether the owner's own runs may be served the "
        "entry), the publish verdict (the bank the entry goes to: shareable for "
        "`shippable-with-attribution` and `ours (shippable)`, local-only for the rest), the "
        "third-party payload under `solution/`, and our own files with their class (a derivative of "
        "a copied file carries its licence; a reimplementation is ours — idea only, no copied code, "
        "cited; a byproduct is not shipped). The first pass's verdict column is carried whole; its "
        "open questions (OQ-n) qualify a verdict and are the owner's to answer.",
        "",
        "## Summary",
        "",
        f"- rows: {len(rows)} (bank {len(counts['bank'])}, reserve {len(counts['reserve'])}); "
        f"publish: shareable {shareable}, local-only {len(rows) - shareable}",
        "- stated licences: " + ", ".join(f"{name} {count}" for name, count in sorted(licences.items())),
    ]
    for which in SETS:
        if counts[which]:
            parts += ["", f"## {which.capitalize()} ({len(counts[which])} rows)", "", render_table(counts[which])]
    return "\n".join(parts) + "\n"


# ---------------------------------------------------------------- the card

def split_sections(text: str) -> Tuple[str, List[Tuple[str, str]]]:
    """A book page as its title (the first level-1 heading that is not a
    section's) and its level-1/2 sections in order; headings inside fenced
    code stay text."""
    title = ""
    sections: List[Tuple[str, str]] = []
    heading, buffer, in_fence = "", [], False
    for line in text.splitlines():
        if line.startswith("```"):
            in_fence = not in_fence
        match = None if in_fence else _HEADING.match(line)
        if match is None:
            buffer.append(line)
            continue
        body = "\n".join(buffer).strip()
        if heading or body:
            sections.append((heading, body))
        heading, buffer = match.group(2).strip(), []
        if match.group(1) == "#" and not title and not sections and not _is_section_name(heading):
            title, heading = heading, ""
    body = "\n".join(buffer).strip()
    if heading or body:
        sections.append((heading, body))
    return title, sections


def _is_section_name(heading: str) -> bool:
    return heading.lower() in ("idea", "provenance", "verification")


def demote(text: str) -> str:
    """Headings one level down and never above level 3, so the card's three
    sections stay its only level-2 headings; fenced code untouched."""
    lines, in_fence = [], False
    for line in text.splitlines():
        if line.startswith("```"):
            in_fence = not in_fence
        lines.append(
            line if in_fence
            else _DEMOTED.sub(lambda m: "#" * min(6, max(3, len(m.group(1)) + 1)) + " ", line)
        )
    return "\n".join(lines)


def rule_block(uid: str, idea: str) -> Tuple[str, str]:
    """The Idea section's lead paragraph as the card's rule — with the list
    it introduces when it ends in a colon — and the remainder."""
    paragraphs = [paragraph.strip() for paragraph in re.split(r"\n\s*\n", idea) if paragraph.strip()]
    if not paragraphs:
        raise ValueError(f"{uid}: the entry's idea has no paragraph")
    lead, rest = paragraphs[0], paragraphs[1:]
    if lead.endswith(":") and rest:
        lead, rest = lead + "\n" + rest[0], rest[1:]
    return lead, "\n\n".join(rest)


def card_body(
    uid: str, entry: Path, routed: Optional[Dict[str, str]], code_files: List[str], protocol: str, plain: str,
) -> str:
    """The card's body: the title, the rule, the task as the situation, the
    idea's remainder and the payload as what to do, the book's provenance
    and verification as why to believe it — the book's words carried whole
    (CLAUDE.md Rule 6) under the card template."""
    idea_title, sections = split_sections((entry / "idea.md").read_text(encoding="utf-8"))
    idea = [body for heading, body in sections if heading.lower() == "idea"]
    if idea:
        others = [(heading, body) for heading, body in sections if heading.lower() != "idea"]
    elif sections:
        idea, others = [sections[0][1]], sections[1:]
    else:
        raise ValueError(f"{uid}: idea.md has no section")
    rule, remainder = rule_block(uid, idea[0])
    title = routed["title"] if routed else (idea_title or uid)
    _, problem_sections = split_sections((entry / "problem.md").read_text(encoding="utf-8"))
    situation = demote("\n\n".join(f"## {heading}\n\n{body}" if heading else body for heading, body in problem_sections))
    payload = (
        "The solution files are under `code/`: " + ", ".join(f"`{name}`" for name in code_files) + "."
        if code_files else "The book holds no solution code for this entry."
    )
    why = demote("\n\n".join(f"## {heading}\n\n{body}" if heading else body for heading, body in others))
    parts = [
        f"# {title}",
        f"**Rule:** {rule}",
        BODY_SECTIONS[0],
        situation,
        BODY_SECTIONS[1],
        "\n\n".join(part for part in (remainder, payload) if part),
        BODY_SECTIONS[2],
        "\n\n".join(part for part in (
            why, f"Reported by others: the score is the source's ({protocol}); no kapso campaign has run this card.",
        ) if part),
        f"**Confidence:** {plain}",
    ]
    return "\n\n".join(parts)


def card_ledger(
    uid: str, row: Dict[str, Any], tier: str, best: str, routed: Optional[Dict[str, str]],
    has_code: bool, plain: str, protocol: str, stamp: datetime,
) -> Dict[str, Any]:
    urls = [url for url in row["urls"] if url.startswith("http")]
    ledger: Dict[str, Any] = {
        "type": "procedure",
        "tags": [routed["tag"]] if routed else [],
        "timestamp": stamp,
        "scope": "domain",
    }
    if routed:
        ledger["scope_conditions"] = routed["section"]
    ledger.update({
        "representation": "code" if has_code else "text",
        "evidence": [{
            "source": {
                "url": ", ".join(urls) if urls else "our own code (no external source)",
                "author": row["author"],
                "licence": stated_licence(row["licence"]),
                "score": best,
                "protocol": protocol,
            },
            "verdict": REPORTED_VERDICT,
            "note": row["holds"],
        }],
        "reliability": {
            "state": "candidate",
            "plain": plain,
            "rationale": (
                f"No kapso campaign has run this card: its one evidence entry is a score reported at "
                f"the source ({protocol}). No reliability numbers are written — a reported score is "
                f"not our measurement; the first executed verdict starts them."
            ),
        },
        "provenance": {"version": 1},
        "log": [{
            "version": 1,
            "date": f"{stamp:%Y-%m-%d}",
            "commit": "book_to_bank",
            "change": (
                f"Converted from the IOAI book entry {uid} (tier {tier}, licence verdict "
                f"{row['verdict']})."
            ),
        }],
        "supersedes": None,
        "contradicts": [],
        "probe": PROBE,
    })
    return ledger


def payload_files(solution: Path) -> List[Path]:
    """The entry's solution files, compiled byproducts left out; a markdown
    file would count as a card under procedures/, so it is refused."""
    if not solution.is_dir():
        return []
    files = sorted(
        path for path in solution.rglob("*")
        if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc"
    )
    markdown = [path for path in files if path.suffix == ".md"]
    if markdown:
        raise ValueError(f"{solution}: markdown in the payload ({', '.join(p.name for p in markdown)}) would count as a card")
    return files


# ---------------------------------------------------------------- the bank

def write_bank(
    book: Path, rows: List[Dict[str, Any]], out: Path, verdicts: List[str], exclude: List[str],
    which: str, stamp: datetime,
) -> List[str]:
    """The bank at `out`, a git repository on main: the founding skeleton,
    one procedure card per chosen entry with its payload, the included
    rows' licence table. Returns the uids converted."""
    if out.exists():
        raise FileExistsError(f"{out} exists: a bank is written whole into a new directory")
    unknown = [verdict for verdict in verdicts if verdict not in VERDICTS]
    if unknown:
        raise ValueError(f"unknown verdicts {unknown}: the pass's are {VERDICTS}")
    entries = book_entries(book)
    by_uid = rows_for(rows, entries, which)
    routed, tiers = router(book), index_tiers(book)
    typos = sorted(set(exclude) - set(entries))
    if typos:
        raise ValueError(f"--exclude names no entry of the book: {', '.join(typos)}")
    chosen = [uid for uid in sorted(entries) if by_uid[uid]["verdict"] in verdicts and uid not in exclude]
    if not chosen:
        raise ValueError(f"no entry of the {which} set has a verdict in {verdicts} (after the exclusions)")
    plans: Dict[str, Tuple[str, Dict[str, Any], List[Path]]] = {}
    for uid in chosen:
        if uid not in tiers:
            raise ValueError(f"{uid}: INDEX.md has no row for it")
        tier = tiers[uid]
        record = entry_record(uid, (entries[uid] / "idea.md").read_text(encoding="utf-8"))
        status = record["status"]
        if tier not in TIER_PHRASES:
            raise ValueError(f"{uid}: tier {tier!r} is unknown to the converter ({tuple(TIER_PHRASES)})")
        if status not in PROTOCOLS:
            raise ValueError(f"{uid}: status {status!r} is unknown to the converter ({tuple(PROTOCOLS)})")
        plain = (
            f"tentative — reported by others ({TIER_PHRASES[tier]}); not reproduced in a kapso "
            f"campaign; no counter-evidence; untested beyond its contest."
        )
        protocol = f"{PROTOCOLS[status]} ({TIER_PHRASES[tier]})"
        entry, row = entries[uid], by_uid[uid]
        files = payload_files(entry / "solution")
        names = [str(path.relative_to(entry / "solution")) for path in files]
        body = card_body(uid, entry, routed.get(uid), names, protocol, plain)
        ledger = card_ledger(uid, row, tier, record["best"], routed.get(uid), bool(files), plain, protocol, stamp)
        plans[uid] = (body, ledger, files)
    (out / "insights").mkdir(parents=True)
    (out / "procedures").mkdir()
    listing = []
    for uid in chosen:
        body, ledger, files = plans[uid]
        card_dir = out / "procedures" / uid
        card_dir.mkdir()
        for source in files:
            target = card_dir / "code" / source.relative_to(entries[uid] / "solution")
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
        (card_dir / "card.md").write_text(f"{body}\n\n---\n\n```yaml\n{dump_ledger(ledger)}```\n", encoding="utf-8")
        listing.append(f"- [{uid}]({uid}/card.md) — {body.splitlines()[0][2:]}")
    verdict_words = ", ".join(verdicts)
    (out / "index.md").write_text(
        "# IOAI book — a bank of past olympiad solutions\n\n"
        "- [insights](insights/index.md) — declarative memory\n"
        "- [procedures](procedures/index.md) — procedural memory\n\n"
        f"Converted on {stamp:%Y-%m-%d} from the IOAI book's {which} set: {len(chosen)} entries whose "
        f"licence verdict is one of {verdict_words}"
        + (f", without {', '.join(sorted(exclude))}" if exclude else "")
        + ". Every card's evidence is `reported`: a score at its source, reported by others, not a "
        "kapso measurement; the cards are candidates until a campaign measures them. Each card's "
        "ledger names its source, author and licence; PROVENANCE.md holds the licence table.\n",
        encoding="utf-8",
    )
    (out / "insights" / "index.md").write_text("# Insights\n", encoding="utf-8")
    (out / "procedures" / "index.md").write_text("# Procedures\n\n" + "\n".join(listing) + "\n", encoding="utf-8")
    (out / "sightings.md").write_text("# Sightings — pre-card observations\n", encoding="utf-8")
    (out / "log.md").write_text(
        "# Learner-run journal\n\n"
        f"- {stamp:%Y-%m-%d} book_to_bank: {len(chosen)} cards converted from the IOAI book ({which} set, "
        f"verdicts {verdict_words}); every evidence entry reported, every card a candidate.\n",
        encoding="utf-8",
    )
    (out / "PROVENANCE.md").write_text(
        "# Provenance and licence table — this bank's entries\n\n"
        + render_table([by_uid[uid] for uid in chosen]) + "\n",
        encoding="utf-8",
    )
    subprocess.run(["git", "init", "-q", "-b", "main", str(out)], check=True)
    subprocess.run(["git", "-C", str(out), "add", "-A"], check=True)
    subprocess.run(
        ["git", "-C", str(out), "commit", "-q", "-m", f"the IOAI book as a bank: {len(chosen)} cards ({verdict_words})"],
        check=True,
    )
    return chosen


def main() -> None:
    parser = argparse.ArgumentParser(description="Convert the IOAI book into a bank kapso serves.")
    parser.add_argument("--book", required=True, type=Path, help="the book's directory (one entry per subdirectory)")
    parser.add_argument("--provenance", required=True, type=Path, help="the licence pass's provenance.json")
    parser.add_argument("--out", required=True, type=Path, help="the bank to write (must not exist)")
    parser.add_argument("--verdicts", required=True, nargs="+", choices=VERDICTS, help="the verdicts the bank takes")
    parser.add_argument("--set", default="bank", choices=SETS, help="the rows' set (the book is one set)")
    parser.add_argument("--exclude", nargs="*", default=[], help="entries left out, by uid")
    parser.add_argument("--table", type=Path, help="also write the second-pass table of every row here")
    args = parser.parse_args()
    stamp = datetime.now(timezone.utc).replace(microsecond=0)
    rows = load_rows(args.provenance)
    chosen = write_bank(args.book, rows, args.out, args.verdicts, args.exclude, args.set, stamp)
    print(f"{args.out}: {len(chosen)} cards ({', '.join(args.verdicts)}) — {', '.join(chosen)}")
    if args.table:
        args.table.write_text(render_pass(rows, stamp), encoding="utf-8")
        print(f"{args.table}: the second pass over {len(rows)} rows")


if __name__ == "__main__":
    main()
