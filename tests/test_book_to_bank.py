"""benchmarks/ioai2026/book_to_bank.py: a fixture book converts into a bank
the read model accepts, the facade loads by path and the serving layer
renders with its code payload and the "reported by others" line; the
licence pass's verdicts decide membership and an exclusion drops one entry;
a corrupt provenance row, an uncovered entry or markdown in a payload
raises (CLAUDE.md Rule 2); the second pass's columns are mechanical."""

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from benchmarks.ioai2026.book_to_bank import (
    PROBE,
    PROTOCOLS,
    SHAREABLE_VERDICTS,
    TIER_PHRASES,
    VERDICTS,
    load_rows,
    render_pass,
    write_table,
    GENERATED_BEGIN,
    GENERATED_END,
    render_table,
    stated_licence,
    write_bank,
)
from kapso.core.config import load_config
from kapso.experience.sources import bank_head
from kapso.learning.bank import Bank
from kapso.learning.bank_invariants import body_confidence_text, body_contract_gaps
from kapso.learning.retriever import render_cards, render_index
from tests.handles_support import facade
from tests.test_experience_reference import settings_for

STAMP = datetime(2026, 10, 29, 12, 0, tzinfo=timezone.utc)
TASK = {"harness": "competitive-programming"}
FLOORS = load_config()["learning"]["update_crew"]["body_floors"]

ALPHA_IDEA = """# Alpha — solution idea

## Idea

**FixMatch-style semi-supervised training of a pretrained small convolutional
network** wins when only a few dozen labels exist: the unlabeled bulk is
pseudo-labelled from a weak view at a high confidence threshold and trained on
a strong view, so the labelled set only names what the structure already
separates.

- Split the labelled rows from the pool.
- Train twenty epochs with a four-to-one unlabeled ratio.

Inference is a plain argmax over the test images, written as the competition's
submission file with the zero-padded identifier column and the class name as a
string, exactly as the sample submission shows, with no manual labels anywhere
in the pipeline.

## Provenance

- Preferred artifact: the winner-contributed notebook from the organizers'
  repository, credited in its community README; the score claimed in the
  notebook is a private leaderboard figure which the public board matches
  closely.

## Verification

Not yet run by us; the notebook's own executed outputs show the claimed score
and the public leaderboard's top entry sits within a point of it.

status: solution-in
best: confirmed — winner 0.79 ~= LB top 0.79590
"""

ALPHA_PROBLEM = """# Alpha (A contest round 0)

## Setting and prediction target

Semi-supervised image classification of scans into four classes, with about
two percent of the training set labelled; the intended skill is learning from
the unlabeled bulk rather than from the few labels.

## Binding constraints

- No manual labelling; one pretrained backbone family; twenty minutes of
  kernel runtime.

## Source links

- Problem: https://example.org/competitions/alpha
"""

BETA_IDEA = """# Idea

The official answer key is the marked variant of the question sheet, so a
solver treats this as curriculum recall: read the marked options, reproduce
the reasoning for each, and write short structured essays that hit every
bullet the prompt enumerates; nothing here is a coding task.

# Provenance

- The organizers' repository publishes the answer key as a PDF under a
  share-alike licence.

# Verification

Not run: there is no code to run.

status: described
best: confirmed — answer key extractable
"""

GAMMA_IDEA = """# Gamma — solution idea

## Idea

Two steps, each cheap:
- Hough circles find every coin and its diameter.
- A small network conditioned on the diameter names the coin.

A diameter-conditioned classifier beats an end-to-end detector at this data
size because the geometry is fully specified by the circle finder.

## Provenance

- Verbatim contestant notebooks from the unofficial mirror.

## Verification

Re-run by us on the official scorer: one hundred of one hundred.

status: solution-in verified
best: confirmed — 100/100
"""

INDEX = """# Fixture book

| uid | tier | status | best | note |
|---|---|---|---|---|
| alpha-task | sure-gold | solution-in | confirmed | winner 0.79 ~= LB top 0.79590 |
| beta-task | sure-gold | described | confirmed | answer key extractable |
| gamma-task | claimed-max | solution-in verified | confirmed | 100/100 |
"""

ROUTER = """# Book index — fixture (3 problems)

## §2 Scarce labels

- ✓ [img] alpha-task — classify scans from few labels → FixMatch (winner 0.79 ≈ LB top)

## §4 Count, detect, localize

- ✓ [tab] gamma-task — count coins → Hough circles + diameter-conditioned CNN (100/100)
"""


def row(uid, verdict, **fields):
    base = {
        "uid": uid, "set": "bank", "tier": "sure-gold", "contest": "A contest", "holds": "a notebook",
        "source_kind": "a repository", "author": "someone", "urls": ["https://github.com/example/solutions"],
        "licence": "[aicc] MIT — LICENSE file (\"Copyright 2025 AICC Organizers\" + MIT permission text)",
        "evidence": "GitHub licence API spdx_id=MIT, fetched 2026-10-29", "verdict": verdict,
        "files_copied": [], "files_ours": [],
    }
    return {**base, **fields}


def make_book(tmp_path: Path):
    book = tmp_path / "book"
    for uid, idea, problem in (
        ("alpha-task", ALPHA_IDEA, ALPHA_PROBLEM),
        ("beta-task", BETA_IDEA, "# Beta theory round\n\n## Task\n\nTwenty multiple-choice questions and five essays.\n"),
        ("gamma-task", GAMMA_IDEA, "# Gamma\n\n## Task\n\nCount and locate coins, no pretrained weights.\n"),
    ):
        (book / uid).mkdir(parents=True)
        (book / uid / "idea.md").write_text(idea)
        (book / uid / "problem.md").write_text(problem)
    (book / "alpha-task" / "solution" / "__pycache__").mkdir(parents=True)
    (book / "alpha-task" / "solution" / "solution.py").write_text("print('alpha')\n")
    (book / "alpha-task" / "solution" / "winner.ipynb").write_text('{"cells": []}\n')
    (book / "alpha-task" / "solution" / "__pycache__" / "solution.cpython-313.pyc").write_bytes(b"\x00")
    (book / "gamma-task" / "solution").mkdir()
    (book / "gamma-task" / "solution" / "main.py").write_text("print('gamma')\n")
    (book / "INDEX.md").write_text(INDEX)
    (book / "book_index.md").write_text(ROUTER)
    rows = [
        row(
            "alpha-task", "shippable-with-attribution", author="winner N. G.",
            holds="verbatim copy of the winner notebook; solution.py = our extraction",
            files_copied=["winner.ipynb"],
            files_ours=[
                "solution.py (mechanical extraction of the winner notebook — derivative, same licence)",
                "__pycache__/solution.cpython-313.pyc (our compiled byproduct; should not ship)",
                "fusion_reimpl.py (our path-adaptation of the winner notebook; inherits its status)",
                "metric_reimpl.py (our reimplementation from the write-up — idea only, no copied code)",
            ],
            note="community-contributed notebook: see OQ-3",
        ),
        row(
            "beta-task", "local-only", licence="[miko] none stated — no LICENSE file, no License sidebar entry",
            urls=["https://github.com/example/mirror"], holds="no solution/ directory; idea.md paraphrases the key",
            files_ours=["idea.md (our summary)"],
        ),
        row(
            "gamma-task", "excluded", tier="claimed-max",
            licence="[haio] CC BY-NC-SA 4.0 — LICENSE file titled \"Attribution-NonCommercial-ShareAlike 4.0\"",
            holds="verbatim contestant notebooks", files_copied=["main.py"], note="NonCommercial clause: see OQ-1",
        ),
        row(
            "delta-task", "ours (shippable)", set="reserve", licence="n/a — our code", urls=["—"],
            files_ours=["our_solution.py"],
        ),
    ]
    provenance = tmp_path / "provenance.json"
    provenance.write_text(json.dumps(rows, indent=1, ensure_ascii=False))
    return book, provenance


def test_shareable_bank_conforms_loads_by_path_and_serves_the_code_payload(tmp_path):
    book, provenance = make_book(tmp_path)
    out = tmp_path / "banks" / "shareable"
    chosen = write_bank(book, load_rows(provenance), out, list(SHAREABLE_VERDICTS), [], "bank", STAMP)
    assert chosen == ["alpha-task"]
    bank = Bank(str(out))
    assert bank.conformance_findings() == []
    assert sorted(bank.cards) == ["alpha-task"]
    code = out / "procedures" / "alpha-task" / "code"
    assert sorted(path.name for path in code.iterdir()) == ["solution.py", "winner.ipynb"]
    assert not (out / "procedures" / "beta-task").exists() and not (out / "procedures" / "gamma-task").exists()
    assert (
        "- [alpha-task](alpha-task/card.md) — classify scans from few labels → FixMatch (winner 0.79 ≈ LB top)"
        in (out / "procedures" / "index.md").read_text()
    )
    assert "3 entries" not in (out / "index.md").read_text() and "1 entries" in (out / "index.md").read_text()

    card = bank.cards["alpha-task"]
    front = card.frontmatter
    assert (front["type"], front["representation"], front["scope"]) == ("procedure", "code", "domain")
    assert (front["tags"], front["scope_conditions"]) == (["img"], "Scarce labels")
    assert card.evidence == [{
        "source": {
            "url": "https://github.com/example/solutions",
            "author": "winner N. G.",
            "licence": "MIT",
            "score": "confirmed — winner 0.79 ~= LB top 0.79590",
            "protocol": f"{PROTOCOLS['solution-in']} ({TIER_PHRASES['sure-gold']})",
        },
        "verdict": "reported",
        "note": "verbatim copy of the winner notebook; solution.py = our extraction",
    }]
    assert card.state == "candidate" and card.score is None and card.reported_only
    assert card.reliability["plain"].startswith("tentative — reported by others (the book's proof-grade tier)")
    assert "No reliability numbers are written" in card.reliability["rationale"]
    log = front["log"]
    assert len(log) == 1 and front["provenance"] == {"version": 1}
    assert (log[0]["version"], str(log[0]["date"]), log[0]["commit"]) == (1, "2026-10-29", "book_to_bank")
    assert log[0]["change"] == (
        "Converted from the IOAI book entry alpha-task (tier sure-gold, licence verdict shippable-with-attribution)."
    )
    assert (front["probe"], front["supersedes"], front["contradicts"]) == (PROBE, None, [])

    body = card.body
    assert body.startswith(
        "# classify scans from few labels → FixMatch (winner 0.79 ≈ LB top)\n\n**Rule:** **FixMatch-style"
    )
    assert body_contract_gaps(body, FLOORS) == []
    assert body_confidence_text(body) == card.reliability["plain"]
    assert body.index("## Is this your situation?") < body.index("## What to do") < body.index("## Why believe this")
    assert "### Setting and prediction target" in body and "### Binding constraints" in body
    assert "- Split the labelled rows from the pool." in body
    assert "The solution files are under `code/`: `solution.py`, `winner.ipynb`." in body
    assert "### Provenance" in body and "### Verification" in body and "status: solution-in" in body
    assert "Reported by others: the score is the source's (" in body

    kapso = facade()
    kapso._experience_settings = settings_for(tmp_path)
    source = kapso.load_experience(str(out))
    assert (source.kind, source.cards, source.head) == ("bank", 1, bank_head(out))

    served = render_cards(bank, TASK, ["alpha-task"], True, {})
    assert f"code: {code}" in served["text"]
    assert "*provenance:* reported by others — the score is the source's, not a kapso measurement" in served["text"]
    assert "author=winner N. G. licence=MIT score=confirmed — winner 0.79 ~= LB top 0.79590" in served["text"]
    assert served["served"] == [
        {"card": "alpha-task", "version": 1, "state": "candidate", "score": None, "exposure": "evidence-read"}
    ]
    index = render_index(bank, TASK)
    assert index["listed_count"] == 1
    assert "[card:alpha-task] score None" in index["text"] and "applies-when: Scarce labels" in index["text"]


def test_local_only_bank_takes_the_rest_with_a_text_procedure(tmp_path):
    book, provenance = make_book(tmp_path)
    out = tmp_path / "banks" / "local-only"
    chosen = write_bank(book, load_rows(provenance), out, ["local-only", "excluded"], [], "bank", STAMP)
    assert chosen == ["beta-task", "gamma-task"]
    bank = Bank(str(out))
    assert bank.conformance_findings() == []
    assert "alpha-task" not in bank.cards

    beta = bank.cards["beta-task"]
    assert beta.representation == "text" and not (out / "procedures" / "beta-task" / "code").exists()
    assert beta.frontmatter["tags"] == [] and "scope_conditions" not in beta.frontmatter
    assert beta.title == "beta-task"                       # not routed; its first heading is a section's
    assert "The book holds no solution code for this entry." in beta.body
    assert beta.evidence[0]["source"]["licence"] == "unstated"
    assert beta.evidence[0]["source"]["protocol"] == f"{PROTOCOLS['described']} ({TIER_PHRASES['sure-gold']})"

    gamma = bank.cards["gamma-task"]
    assert gamma.evidence[0]["source"]["licence"] == "CC BY-NC-SA 4.0"
    assert gamma.evidence[0]["source"]["protocol"].startswith(PROTOCOLS["solution-in verified"])
    assert "**Rule:** Two steps, each cheap:\n- Hough circles find every coin" in gamma.body
    assert gamma.hero.startswith("Two steps, each cheap: - Hough circles")
    assert "A diameter-conditioned classifier beats" in gamma.body.split("## What to do")[1]
    assert (out / "procedures" / "gamma-task" / "code" / "main.py").read_text() == "print('gamma')\n"

    served = render_cards(bank, TASK, ["beta-task"], False, {})
    assert "code:" not in served["text"] and "*provenance:* reported by others" in served["text"]
    table = (out / "PROVENANCE.md").read_text()
    assert "| gamma-task |" in table and "| beta-task |" in table and "alpha-task" not in table


def test_an_exclusion_drops_the_entry_and_a_typo_or_a_taken_directory_is_refused(tmp_path):
    book, provenance = make_book(tmp_path)
    rows = load_rows(provenance)
    out = tmp_path / "banks" / "arm"
    with pytest.raises(ValueError, match="no entry of the bank set has a verdict"):
        write_bank(book, rows, out, list(SHAREABLE_VERDICTS), ["alpha-task"], "bank", STAMP)
    with pytest.raises(ValueError, match="--exclude names no entry of the book: alpha-tsk"):
        write_bank(book, rows, out, list(SHAREABLE_VERDICTS), ["alpha-tsk"], "bank", STAMP)
    assert not out.exists()
    chosen = write_bank(book, rows, out, list(VERDICTS), ["alpha-task"], "bank", STAMP)
    assert chosen == ["beta-task", "gamma-task"]
    assert ", without alpha-task." in (out / "index.md").read_text()
    with pytest.raises(FileExistsError, match="a bank is written whole into a new directory"):
        write_bank(book, rows, out, list(VERDICTS), [], "bank", STAMP)


def test_a_corrupt_row_an_uncovered_entry_or_markdown_in_a_payload_raises(tmp_path):
    book, provenance = make_book(tmp_path)
    rows = json.loads(provenance.read_text())

    def written(content):
        path = tmp_path / "p.json"
        path.write_text(json.dumps(content))
        return path

    bad = [dict(r) for r in rows]
    del bad[0]["verdict"]
    with pytest.raises(ValueError, match="row 0: missing verdict"):
        load_rows(written(bad))
    bad = [dict(r) for r in rows]
    bad[1]["verdict"] = "maybe"
    with pytest.raises(ValueError, match="verdict 'maybe' is not one of"):
        load_rows(written(bad))
    bad = [dict(r) for r in rows]
    bad[2]["files_copied"] = "main.py"
    with pytest.raises(ValueError, match="files_copied is not a list"):
        load_rows(written(bad))
    with pytest.raises(ValueError, match="not a list of rows"):
        load_rows(written({"rows": []}))

    extra = rows + [dict(rows[0], uid="omega-task")]
    with pytest.raises(ValueError, match="bank row omega-task names no entry of the book"):
        write_bank(book, extra, tmp_path / "b1", list(VERDICTS), [], "bank", STAMP)
    with pytest.raises(ValueError, match="book entries without a bank row: gamma-task"):
        write_bank(book, [r for r in rows if r["uid"] != "gamma-task"], tmp_path / "b2", list(VERDICTS), [], "bank", STAMP)
    (book / "INDEX.md").write_text(INDEX.replace("| beta-task | sure-gold |", "| beta-task | bronze |"))
    with pytest.raises(ValueError, match="beta-task: tier 'bronze' is unknown"):
        write_bank(book, rows, tmp_path / "b3", list(VERDICTS), [], "bank", STAMP)
    (book / "INDEX.md").write_text(INDEX)
    (book / "alpha-task" / "solution" / "NOTES.md").write_text("notes\n")
    with pytest.raises(ValueError, match="markdown in the payload \\(NOTES.md\\) would count as a card"):
        write_bank(book, rows, tmp_path / "b4", list(VERDICTS), [], "bank", STAMP)
    assert not (tmp_path / "b4").exists()                  # nothing written before the checks pass


def test_the_second_pass_columns_are_mechanical(tmp_path):
    assert stated_licence('[aicc] MIT — LICENSE file ("Copyright 2025 AICC Organizers" + MIT permission text)') == "MIT"
    assert stated_licence("[awesome] MIT (licence API spdx_id=MIT)") == "MIT"
    assert stated_licence("[roai] MIT — LICENSE file // [jaredliw] none stated — no LICENSE file") == "MIT // unstated"
    assert stated_licence("[haio] CC BY-NC-SA 4.0 — LICENSE file titled \"Attribution-NonCommercial\"") == "CC BY-NC-SA 4.0"
    assert stated_licence("[ioai24zip] none stated for the zips; page footer: \"All rights reserved\"") == "unstated"
    assert stated_licence("[khanhtb] not established — the public page is a JavaScript shell") == "unstated"
    assert stated_licence("n/a — our code (task repo none stated for its own content)") == "ours (no third-party code)"

    book, provenance = make_book(tmp_path)
    rows = load_rows(provenance)
    lines = {line.split(" | ")[0][2:]: line for line in render_table(rows).splitlines()[2:]}
    # A file's class is its description's, never its name's: the adaptation
    # named `_reimpl` is a derivative; `problem.md` is ours on every row.
    problem = "problem.md: ours — our summary of the task, its source links cited (OQ-7)"
    assert (
        "| MIT | yes — attribution kept in the card and this table | shippable-with-attribution → the shareable "
        "bank (OQ-3) | 1 copied: winner.ipynb | solution.py: derivative of the copied file, its licence; "
        "__pycache__/solution.cpython-313.pyc: byproduct, not shipped; "
        "fusion_reimpl.py: derivative of the copied file, its licence; "
        f"metric_reimpl.py: our reimplementation — idea only, no copied code, cited; {problem} | winner N. G. |"
    ) in lines["alpha-task"]
    assert f"| unstated | owner's call (licence unstated or restricted) | local-only → the local-only bank | none | idea.md: ours; {problem} |" in lines["beta-task"]
    assert f"| CC BY-NC-SA 4.0 | owner's call (OQ-1) | excluded → the local-only bank (OQ-1) | 1 copied: main.py | {problem} |" in lines["gamma-task"]
    assert f"| ours (no third-party code) | yes — our own code | ours (shippable) → the shareable bank | none | our_solution.py: ours; {problem} |" in lines["delta-task"]

    text = render_pass(rows, STAMP)
    assert text.startswith(GENERATED_BEGIN + "\n") and text.endswith(GENERATED_END + "\n")
    assert "- rows: 4 (bank 3, reserve 1); publish: shareable 2, local-only 2" in text
    assert "- stated licences: CC BY-NC-SA 4.0 1, MIT 1, ours (no third-party code) 1, unstated 1" in text
    assert "## Bank (3 rows)" in text and "## Reserve (1 rows)" in text


def test_the_table_regeneration_keeps_the_hand_written_sections(tmp_path):
    # The organizers' rules, the open questions and the sources are written
    # by hand after the generated section; a regeneration replaces only the
    # section between the markers, writes a fresh file whole, and refuses
    # markers out of order.
    _book, provenance = make_book(tmp_path)
    rows = load_rows(provenance)
    table = tmp_path / "PROVENANCE.md"
    write_table(table, render_pass(rows, STAMP))
    first = table.read_text()
    assert first.startswith(GENERATED_BEGIN) and first.rstrip().endswith(GENERATED_END)
    appendix = "\n\n## Open questions for a human\n\n- OQ-1 — kept by hand.\n"
    table.write_text(first.replace("## Bank (3 rows)", "## Bank (3 rows), stale") + appendix)
    write_table(table, render_pass(rows, STAMP))
    second = table.read_text()
    assert second == first + appendix
    table.write_text(GENERATED_END + "\n" + GENERATED_BEGIN + "\n")
    with pytest.raises(ValueError, match="out of order"):
        write_table(table, render_pass(rows, STAMP))
