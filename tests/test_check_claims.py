"""scripts/check_claims.py: the two claim rules of the docs design
(docs/plans/docs-and-examples-redesign.md, Checks) on fixture pages — a
words-out phrase in prose fails, with an `s` or `ly` ending, in the front
matter and in a manifest's strings, and in code does not; the front-page-only
section binds only the front pages; a result beside a metric word with no
provenance fails while one with provenance, a provenance table's row, a
rule's number, a target and a heading do not; a paragraph that runs into a
fence is still read — and the shipped pages pass, and the list is the
direction document's."""

import importlib.util
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("check_claims", ROOT / "scripts" / "check_claims.py")
check_claims = importlib.util.module_from_spec(spec)
sys.modules["check_claims"] = check_claims
spec.loader.exec_module(check_claims)

LISTS = {"everywhere": ["self-improving", "team of agents", "autonomous", "long-running agent"], "front": ["judge"]}
DIRECTION = ROOT / "docs" / "research" / "kapso-redesign.md"


def page(tmp_path: Path, name: str, text: str) -> Path:
    path = tmp_path / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def findings(path: Path, lists=LISTS):
    return [f.split(": ", 1)[1] for f in check_claims.scan(path, lists)]


def test_a_words_out_phrase_in_prose_fails_and_in_code_does_not(tmp_path, monkeypatch):
    monkeypatch.setattr(check_claims, "REPO", tmp_path)
    inner = page(tmp_path, "docs/x.mdx", (
        "---\ntitle: X\n---\n\nA Self-Improving loop, and a team-of-agents mention.\n\n"
        "```python\nself_improving = 1  # team of agents\n```\n\nThe `self-improving` flag names the judge.\n"
    ))
    assert findings(inner) == ["words-out 'self-improving'"]      # the hyphenated form; not in the fence, not in the code span


def test_an_inflection_of_a_phrase_is_the_phrase(tmp_path, monkeypatch):
    # Regression: "fully autonomously" and "long-running agents" passed a
    # whole-phrase match on the docs index.
    monkeypatch.setattr(check_claims, "REPO", tmp_path)
    inner = page(tmp_path, "docs/x.mdx", "Competing fully autonomously, the long-running agents ran.\n")
    assert findings(inner) == ["words-out 'autonomous'", "words-out 'long-running agent'"]
    assert findings(page(tmp_path, "docs/y.mdx", "An autonomy-first design.\n")) == []


def test_the_front_matter_is_prose_for_the_words_out_rule(tmp_path, monkeypatch):
    # Regression: a page's description said "fully autonomous" while its body said "unattended".
    monkeypatch.setattr(check_claims, "REPO", tmp_path)
    inner = page(tmp_path, "docs/x.mdx", (
        '---\ntitle: "Two autonomous sessions"\nsidebarTitle: "Sessions"\ndescription: "Unattended."\n'
        'keywords: ["autonomous AI", "olympiad"]\n---\n\nUnattended sessions.\n'
    ))
    assert findings(inner) == ["words-out 'autonomous' in the front matter's title", "words-out 'autonomous' in the front matter's keywords"]


def test_the_manifests_strings_are_prose_for_the_words_out_rule(tmp_path, monkeypatch):
    # Regression: the marketplace manifest kept the retired tagline after every plugin manifest lost it.
    monkeypatch.setattr(check_claims, "REPO", tmp_path)
    monkeypatch.setattr(check_claims, "MANIFESTS", ("store.json", "ctx.json"))
    page(tmp_path, "store.json", json.dumps({"description": "the long-running agents", "plugins": [{"description": "clean"}]}))
    page(tmp_path, "ctx.json", json.dumps({"description": "clean", "rules": ["Run it autonomously."]}))
    assert check_claims.scan_manifests(LISTS) == [
        "store.json: words-out 'long-running agent' in description",
        "ctx.json: words-out 'autonomous' in rules[0]",
    ]


def test_the_front_section_binds_the_front_pages_only(tmp_path, monkeypatch):
    monkeypatch.setattr(check_claims, "REPO", tmp_path)
    inner = page(tmp_path, "docs/build/x.mdx", "The judge reads the evaluation.\n")
    front = page(tmp_path, "docs/index.mdx", "The judge reads the evaluation.\n")
    readme = page(tmp_path, "README.md", "We judge nothing; the evaluation does.\n")
    assert findings(inner) == []
    assert findings(front) == ["words-out 'judge'"]
    assert findings(readme) == ["words-out 'judge'"]


def test_a_result_beside_a_metric_word_needs_provenance(tmp_path, monkeypatch):
    monkeypatch.setattr(check_claims, "REPO", tmp_path)
    bare = page(tmp_path, "docs/a.mdx", "The model reaches an AUROC of 0.82 on the holdout.\n")
    assert findings(bare) == ["a number with no provenance: 0.82 beside 'auroc'"]
    sourced = page(tmp_path, "docs/b.mdx", "The model reaches an AUROC of 0.82 on the holdout, measured by us on the provided evaluator on 2026-10-01.\n")
    assert findings(sourced) == []
    table = page(tmp_path, "docs/c.mdx", "| Task | Score | Who ran it |\n|---|---|---|\n| churn | 0.82 AUROC | our campaign, 2026-10-01 |\n")
    assert findings(table) == []
    threshold = page(tmp_path, "docs/d.mdx", "The frame rejects any score outside centre ± 0.2.\n")
    assert findings(threshold) == []
    heading = page(tmp_path, "docs/e.mdx", "### 3. Extract score\n\nThe generator parses the score.\n")
    assert findings(heading) == []
    percent = page(tmp_path, "docs/f.mdx", "Accuracy rose by 12% after the change.\n")
    assert findings(percent) == ["a number with no provenance: 12% beside 'accuracy'"]


def test_the_product_name_is_not_provenance_and_one_decimal_is_a_result(tmp_path, monkeypatch):
    # Regression: "Kapso scored 536.07" passed because the product's name counted as
    # provenance; "81.2 AUROC" passed because a result needed two decimals.
    monkeypatch.setattr(check_claims, "REPO", tmp_path)
    named = page(tmp_path, "docs/a.mdx", "Kapso scored 536.07 in the track, above the table below.\n")
    assert findings(named) == ["a number with no provenance: 536.07 beside 'scored'"]
    short = page(tmp_path, "docs/b.mdx", "Kapso leads with 81.2 AUROC over twelve tasks.\n")
    assert findings(short) == ["a number with no provenance: 81.2 beside 'auroc'"]
    ranked = page(tmp_path, "docs/c.mdx", "The rank of 3.5 came from a run graded by the official scorer on 2026-10-11.\n")
    assert findings(ranked) == []


def test_a_target_or_a_rule_is_read_beside_its_number_not_per_paragraph(tmp_path, monkeypatch):
    # Regression: one "toward" exempted a whole paragraph, including a measured baseline.
    monkeypatch.setattr(check_claims, "REPO", tmp_path)
    mixed = page(tmp_path, "docs/a.mdx", (
        "The shipped model's accuracy is 0.30 on the chart set. Much later in the same paragraph the brief asks for a rise "
        "toward 0.50 accuracy.\n"
    ))
    assert findings(mixed) == ["a number with no provenance: 0.30 beside 'accuracy'"]
    rule = page(tmp_path, "docs/b.mdx", "A candidate keeps its score within 0.5 of the floor; the budget is 1.5 hours.\n")
    assert findings(rule) == []


def test_a_paragraph_that_runs_into_a_fence_is_read(tmp_path, monkeypatch):
    # Regression: prose with no blank line before a fence was yielded as fence
    # content and skipped the number rule.
    monkeypatch.setattr(check_claims, "REPO", tmp_path)
    abutting = page(tmp_path, "docs/a.mdx", "An accuracy of 0.91 on the holdout:\n```bash\nkapso build\n```\n")
    assert findings(abutting) == ["a number with no provenance: 0.91 beside 'accuracy'"]
    pasted = page(tmp_path, "docs/b.mdx", "Paste this:\n```text\nreach an accuracy of 0.91 with a team of agents\n```\n")
    assert findings(pasted) == ["words-out 'team of agents'"]


def test_the_list_is_the_direction_documents():
    # Regression: the lint's list is a copy of the document's; a phrase added
    # to the document must reach the file (the file may hold more: the front
    # section's split, an inflection the pattern needs).
    text = DIRECTION.read_text(encoding="utf-8")
    start = text.index("- Words out:")
    bullet = text[start:text.index("\n- ", start + 1)]
    documented = re.findall(r'"([^"]+)"', bullet)
    assert len(documented) >= 10
    lists = check_claims.words_out()
    patterns = [check_claims.phrase_pattern(phrase) for phrase in lists["everywhere"] + lists["front"]]
    missing = [phrase for phrase in documented if not any(pattern.search(phrase) for pattern in patterns)]
    assert missing == []


def test_the_shipped_pages_pass():
    # Regression: the public pages and manifests hold to both rules — a hit is
    # fixed on its page, never by widening the allow-list without a note in the plan.
    lists = check_claims.words_out()
    hits = check_claims.scan_manifests(lists) + [finding for path in check_claims.pages() for finding in check_claims.scan(path, lists)]
    assert hits == []
