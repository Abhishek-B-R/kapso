"""scripts/check_claims.py: the two claim rules of the docs design
(docs/plans/docs-and-examples-redesign.md, Checks) on fixture pages — a
words-out phrase in prose fails and in code does not, the front-page-only
section binds only the front pages, a result beside a metric word with no
provenance fails while one with provenance, a provenance table's row, a
threshold to one decimal and a heading do not — and the shipped pages
pass."""

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("check_claims", ROOT / "scripts" / "check_claims.py")
check_claims = importlib.util.module_from_spec(spec)
sys.modules["check_claims"] = check_claims
spec.loader.exec_module(check_claims)

LISTS = {"everywhere": ["self-improving", "team of agents"], "front": ["judge"]}


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


def test_the_shipped_pages_pass():
    # Regression: the public pages hold to both rules — a hit is fixed on
    # its page, never by widening the allow-list without a note in the plan.
    lists = check_claims.words_out()
    hits = [finding for path in check_claims.pages() for finding in check_claims.scan(path, lists)]
    assert hits == []
