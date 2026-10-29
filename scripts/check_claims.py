#!/usr/bin/env python3
"""Fail when a public page breaks one of the two claim rules
(docs/plans/docs-and-examples-redesign.md, Checks).

1. A phrase of the words-out list (scripts/words_out.txt, from the
   redesign's rules for every public sentence) appears in prose — outside
   fenced code and inline code — as whole words, an `s` or `ly` ending
   allowed. The list has two sections: phrases banned everywhere, and
   phrases banned on the front pages only (README.md, docs/index.mdx),
   where a word is also the name of something the inner pages must
   describe (the judge role, a host's trust line). A page's front matter
   (its title, sidebar title, description and keywords) and the strings of
   the plugin's manifests and the Context7 file are prose for this rule.
2. A result — a number with a decimal part, or a percentage — sits beside
   a metric word (AUROC, accuracy, F1, MAE, NMAE, MAP, log loss, score,
   rank, rating, ...) in a paragraph that carries no provenance: no word
   of the paragraph says who ran it, on what, or when (ran, measured,
   recorded, published, submitted, graded, official, the evaluator, a
   date), and the paragraph is not a row of a table whose header names a
   provenance column (the benchmark pages' tables name the source per
   row). Headings are not paragraphs; a number marked beside itself as a
   target, expected or not measured is not a result; a number beside a
   tolerance, a band, a floor or a budget is a rule, not a result.

Scans every .mdx under docs/, the repository README, the examples' and the
benchmarks' READMEs and the plugin's skills. Code fences and inline code
are not prose; a `text` or `md` fence is (a prompt the user pastes is the
most-copied sentence on a page), for the words-out rule only. A hit prints
the file, the line and the rule; the exit status is the number of hits.
"""

import json
import re
import sys
from pathlib import Path
from typing import Iterator, List, Tuple

REPO = Path(__file__).resolve().parent.parent
WORDS_OUT = REPO / "scripts" / "words_out.txt"
METRIC_WORDS = (
    "auroc", "auc", "accuracy", "f1", "mae", "rmse", "nmae", "map", "mrr", "log loss", "logloss", "score",
    "scores", "scored", "rank", "ranked", "rating", "elo", "sharpe", "percent", "medal", "leaderboard",
)
# A word that says who ran it, on what or when; matched as a whole word.
PROVENANCE_WORDS = (
    "ran", "run by", "measured", "recorded", "fetched", "published", "reported", "submitted", "graded",
    "scored by", "evaluator", "evaluated", "official", "read on", "on 20", "in 20",
)
# A number is a target, not a result, when one of these sits beside it.
_EXPECTED = re.compile(r"\b(expected|not measured|not recorded|target|asks for|toward|reachable)\b", re.IGNORECASE)
# A number beside one of these is a rule (a tolerance, a band, a floor, a budget), not a result.
_RULE = re.compile(r"(±|\b(?:budget|floor|tolerance|band|threshold|within|seed)\b)", re.IGNORECASE)
_RESULT = re.compile(r"(?<![A-Za-z0-9_.-])(?:\d+\.\d+|\d+(?:\.\d+)?%)(?![A-Za-z0-9_])")
WINDOW = 60                                            # characters either side of a number that count as "beside"
_FRONT_MATTER = re.compile(r"\A---\n.*?\n---\n", re.S)
FRONT_KEYS = ("title", "sidebarTitle", "description", "keywords")
_INLINE_CODE = re.compile(r"`[^`\n]*`")
_LINK_URL = re.compile(r"\]\([^)]*\)")
# A card is its own paragraph: the tag lines of a card group bound it.
_CARD_TAG = re.compile(r"\s*</?Card(?:Group)?\b")
_PROSE_FENCES = ("text", "md", "markdown", "")
FRONT_PAGES = ("README.md", "docs/index.mdx")
# The manifests whose strings a store or an agent reads before any page.
MANIFESTS = (
    ".claude-plugin/marketplace.json", "plugin/.claude-plugin/plugin.json", "plugin/.codex-plugin/plugin.json",
    "plugin/.cursor-plugin/plugin.json", "context7.json",
)


def pages() -> List[Path]:
    return (
        [REPO / "README.md"] + sorted((REPO / "docs").rglob("*.mdx"))
        + sorted((REPO / "examples").glob("*/README.md")) + [REPO / "examples" / "harnesses" / "README.md"]
        + sorted((REPO / "examples" / "harnesses").glob("*/README.md")) + sorted((REPO / "benchmarks").glob("*/README.md"))
        + sorted((REPO / "plugin" / "skills").glob("*/SKILL.md"))
    )


def manifest_strings() -> List[Tuple[Path, str, str]]:
    """(file, key, text) for every description and rule the manifests carry."""
    found = []
    for relative in MANIFESTS:
        path = REPO / relative
        data = json.loads(path.read_text(encoding="utf-8"))
        if "description" in data:
            found.append((path, "description", str(data["description"])))
        for index, plugin in enumerate(data.get("plugins", [])):
            if "description" in plugin:
                found.append((path, f"plugins[{index}].description", str(plugin["description"])))
        for index, rule in enumerate(data.get("rules", [])):
            found.append((path, f"rules[{index}]", str(rule)))
    return found


def front_matter_fields(text: str) -> Iterator[Tuple[int, str, str]]:
    """(line number, key, value) for the front matter's title, sidebar
    title, description and keywords."""
    front = _FRONT_MATTER.match(text)
    if not front:
        return
    for number, line in enumerate(front.group(0).split("\n"), start=1):
        key, separator, value = line.partition(":")
        if separator and key.strip() in FRONT_KEYS:
            yield number, key.strip(), value.strip()


def prose_paragraphs(text: str) -> Iterator[Tuple[int, Tuple[str, bool]]]:
    """(first line number, (paragraph, in a prose fence)) for every prose
    paragraph: code fences dropped whole, a text fence kept as prose,
    inline code and link targets blanked, front matter skipped. A
    paragraph that runs into a fence is flushed when the fence opens; a
    card's text is a paragraph of its own (its neighbour's provenance is
    not its own)."""
    front = _FRONT_MATTER.match(text)
    offset = text[:front.end()].count("\n") if front else 0
    body = text[front.end():] if front else text
    in_fence = False
    prose_fence = False
    paragraph: List[str] = []
    start = offset + 1
    for index, line in enumerate(body.split("\n"), start=offset + 1):
        if line.lstrip().startswith("```"):
            if paragraph:
                yield start, ("\n".join(paragraph), in_fence)
                paragraph = []
            if in_fence:
                in_fence = prose_fence = False
            else:
                in_fence = True
                prose_fence = line.strip()[3:].split(" ")[0].lower() in _PROSE_FENCES
            continue
        if in_fence and not prose_fence:
            continue
        if not line.strip() or _CARD_TAG.match(line):
            if paragraph:
                yield start, ("\n".join(paragraph), in_fence)
                paragraph = []
            continue
        if line.lstrip().startswith("#"):
            continue                                   # a heading is not prose
        if not paragraph:
            start = index
        paragraph.append(_LINK_URL.sub("](url)", _INLINE_CODE.sub("`code`", line)))
    if paragraph:
        yield start, ("\n".join(paragraph), in_fence)


def words_out() -> dict:
    """{"everywhere": [...], "front": [...]} from the list's two sections."""
    sections: dict = {"everywhere": [], "front": []}
    current = "everywhere"
    for line in WORDS_OUT.read_text(encoding="utf-8").splitlines():
        entry = line.strip()
        if not entry or entry.startswith("#"):
            continue
        if entry.startswith("[") and entry.endswith("]"):
            current = entry[1:-1]
            if current not in sections:
                raise ValueError(f"{WORDS_OUT}: unknown section {current!r}")
            continue
        sections[current].append(entry)
    return sections


def phrase_pattern(phrase: str) -> re.Pattern:
    """The phrase as whole words, an `s` or `ly` ending allowed (agents,
    autonomously)."""
    return re.compile(r"(?<![A-Za-z0-9-])" + re.escape(phrase) + r"(?:s|ly)?(?![A-Za-z0-9-])", re.IGNORECASE)


def is_provenance_table_row(paragraph: str) -> bool:
    """A table whose header names a provenance column carries provenance
    per row."""
    first = paragraph.split("\n")[0]
    if not first.lstrip().startswith("|"):
        return False
    header = first.lower()
    return any(word in header for word in ("provenance", "source", "who ran", "run by", "fetched", "entry", "recorded", "best other"))


def _has_word(text: str, word: str) -> bool:
    return re.search(r"(?<![a-z])" + re.escape(word) + r"(?![a-z])", text) is not None


def number_claims(paragraph: str) -> List[str]:
    """The metric numbers in a paragraph with no provenance word in it,
    each read with the text beside it: a target or a rule is not a
    result."""
    lowered = paragraph.lower()
    if any(_has_word(lowered, word) for word in PROVENANCE_WORDS) or is_provenance_table_row(paragraph):
        return []
    hits = []
    for match in _RESULT.finditer(paragraph):
        window = paragraph[max(0, match.start() - WINDOW):match.end() + WINDOW]
        if _EXPECTED.search(window) or _RULE.search(window):
            continue
        metric = next((word for word in METRIC_WORDS if _has_word(window.lower(), word)), None)
        if metric:
            hits.append(f"{match.group(0)} beside {metric!r}")
    return hits


def scan(path: Path, lists: dict) -> List[str]:
    findings = []
    relative = path.relative_to(REPO)
    phrases = list(lists["everywhere"])
    if str(relative) in FRONT_PAGES:
        phrases += lists["front"]
    patterns = [(phrase, phrase_pattern(phrase)) for phrase in phrases]
    text = path.read_text(encoding="utf-8")
    for line_number, key, value in front_matter_fields(text):
        for phrase, pattern in patterns:
            if pattern.search(value):
                findings.append(f"{relative}:{line_number}: words-out {phrase!r} in the front matter's {key}")
    for line_number, (paragraph, in_prose_fence) in prose_paragraphs(text):
        for phrase, pattern in patterns:
            if pattern.search(paragraph):
                findings.append(f"{relative}:{line_number}: words-out {phrase!r}")
        if in_prose_fence:
            continue                                   # a pasted prompt's numbers are its own
        for claim in number_claims(paragraph):
            findings.append(f"{relative}:{line_number}: a number with no provenance: {claim}")
    return findings


def scan_manifests(lists: dict) -> List[str]:
    patterns = [(phrase, phrase_pattern(phrase)) for phrase in lists["everywhere"]]
    findings = []
    for path, key, value in manifest_strings():
        for phrase, pattern in patterns:
            if pattern.search(value):
                findings.append(f"{path.relative_to(REPO)}: words-out {phrase!r} in {key}")
    return findings


def main() -> int:
    lists = words_out()
    findings: List[str] = scan_manifests(lists)
    for page in pages():
        findings += scan(page, lists)
    for finding in findings:
        print(finding)
    print(f"{len(findings)} finding(s) over {len(pages())} pages and {len(MANIFESTS)} manifests")
    return min(len(findings), 125)


if __name__ == "__main__":
    sys.exit(main())
