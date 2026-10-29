#!/usr/bin/env python3
"""Fail when a public page breaks one of the two claim rules
(docs/plans/docs-and-examples-redesign.md, Checks).

1. A phrase of the words-out list (scripts/words_out.txt, from the
   redesign's rules for every public sentence) appears in prose — outside
   fenced code and inline code — as whole words. The list has two
   sections: phrases banned everywhere, and phrases banned on the front
   pages only (README.md, docs/index.mdx), where a word is also the name of
   something the inner pages must describe (the judge role, a host's trust
   line).
2. A result — a number quoted as one, with two or more decimals or as a
   percentage — sits beside a metric word (AUROC, accuracy, F1, MAE, NMAE,
   MAP, log loss, score, rank, ...) in a paragraph that carries no
   provenance: nothing in the paragraph says who ran it, on what, or when,
   and the paragraph is not a row of a table whose header names a
   provenance column (the benchmark pages' tables name the source per row).
   Headings are not paragraphs; a threshold written to one decimal is a
   rule, not a result.

Scans every .mdx under docs/, the repository README and the examples'
READMEs. Front matter, code fences and inline code are not prose; a
`text` or `md` fence is (a prompt the user pastes is the most-copied
sentence on a page), for the words-out rule only. A target written as
"expected" or "not measured" beside its number is not a result. A hit
prints the file, the line and the rule; the exit status is the number of
hits.
"""

import re
import sys
from pathlib import Path
from typing import Iterator, List, Tuple

REPO = Path(__file__).resolve().parent.parent
WORDS_OUT = REPO / "scripts" / "words_out.txt"
METRIC_WORDS = (
    "auroc", "auc", "accuracy", "f1", "mae", "rmse", "nmae", "map", "mrr", "log loss", "logloss", "score",
    "scores", "rank", "ranked", "percent", "medal", "leaderboard", "rating",
)
PROVENANCE_WORDS = (
    "ran", "run by", "measured", "recorded", "fetched", "published", "reported", "evaluator", "evaluated",
    "official", "benchmark", "our", "kapso", "campaign", "on 20", "in 20", "see ", "table", "below", "above",
)
_RESULT = re.compile(r"(?<![A-Za-z0-9_.-])(?:\d+\.\d{2,}|\d+(?:\.\d+)?%)(?![A-Za-z0-9_])")
_FRONT_MATTER = re.compile(r"\A---\n.*?\n---\n", re.S)
_INLINE_CODE = re.compile(r"`[^`\n]*`")
_LINK_URL = re.compile(r"\]\([^)]*\)")
_PROSE_FENCES = ("text", "md", "markdown", "")
_EXPECTED = re.compile(r"\b(expected|not measured|target|asks for|toward)\b", re.IGNORECASE)


def pages() -> List[Path]:
    return (
        [REPO / "README.md"] + sorted((REPO / "docs").rglob("*.mdx"))
        + sorted((REPO / "examples").glob("*/README.md")) + sorted((REPO / "examples" / "harnesses").glob("*/README.md"))
    )


def prose_paragraphs(text: str) -> Iterator[Tuple[int, Tuple[str, bool]]]:
    """(first line number, (paragraph, in a prose fence)) for every prose
    paragraph: code fences dropped whole, a text fence kept as prose,
    inline code and link targets blanked, front matter skipped."""
    front = _FRONT_MATTER.match(text)
    offset = text[:front.end()].count("\n") if front else 0
    body = text[front.end():] if front else text
    in_fence = False
    prose_fence = False
    paragraph: List[str] = []
    start = offset + 1
    for index, line in enumerate(body.split("\n"), start=offset + 1):
        if line.lstrip().startswith("```"):
            if in_fence:
                in_fence = prose_fence = False
                if paragraph:
                    yield start, ("\n".join(paragraph), True)
                    paragraph = []
            else:
                in_fence = True
                prose_fence = line.strip()[3:].split(" ")[0].lower() in _PROSE_FENCES
            continue
        if in_fence and not prose_fence:
            continue
        if not line.strip():
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


FRONT_PAGES = ("README.md", "docs/index.mdx")


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
    return re.compile(r"(?<![A-Za-z0-9-])" + re.escape(phrase) + r"(?![A-Za-z0-9-])", re.IGNORECASE)


def is_provenance_table_row(paragraph: str) -> bool:
    """A table whose header names a provenance column carries provenance
    per row."""
    first = paragraph.split("\n")[0]
    if not first.lstrip().startswith("|"):
        return False
    header = first.lower()
    return any(word in header for word in ("provenance", "source", "who ran", "run by", "fetched", "entry", "recorded", "best other"))


def number_claims(paragraph: str) -> List[str]:
    """The metric numbers in a paragraph with no provenance word in it."""
    lowered = paragraph.lower()
    if any(word in lowered for word in PROVENANCE_WORDS) or is_provenance_table_row(paragraph) or _EXPECTED.search(paragraph):
        return []
    hits = []
    for match in _RESULT.finditer(paragraph):
        window = lowered[max(0, match.start() - 40):match.end() + 40]
        metric = next(
            (word for word in METRIC_WORDS if re.search(r"(?<![a-z])" + re.escape(word) + r"(?![a-z])", window)), None,
        )
        if metric:
            hits.append(f"{match.group(0)} beside {metric!r}")
    return hits


def scan(path: Path, lists: dict) -> List[str]:
    findings = []
    phrases = list(lists["everywhere"])
    if str(path.relative_to(REPO)) in FRONT_PAGES:
        phrases += lists["front"]
    patterns = [(phrase, phrase_pattern(phrase)) for phrase in phrases]
    for line_number, (paragraph, in_prose_fence) in prose_paragraphs(path.read_text(encoding="utf-8")):
        for phrase, pattern in patterns:
            if pattern.search(paragraph):
                findings.append(f"{path.relative_to(REPO)}:{line_number}: words-out {phrase!r}")
        if in_prose_fence:
            continue                                   # a pasted prompt's numbers are its own
        for claim in number_claims(paragraph):
            findings.append(f"{path.relative_to(REPO)}:{line_number}: a number with no provenance: {claim}")
    return findings


def main() -> int:
    lists = words_out()
    findings: List[str] = []
    for page in pages():
        findings += scan(page, lists)
    for finding in findings:
        print(finding)
    print(f"{len(findings)} finding(s) over {len(pages())} pages")
    return min(len(findings), 125)


if __name__ == "__main__":
    sys.exit(main())
