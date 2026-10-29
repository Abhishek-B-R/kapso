"""docs.json: every page the navigation lists exists, every page under
docs/ is listed exactly once, and every retired path redirects to a page
that exists — so a merge or a move never leaves a link that worked
yesterday pointing at nothing (docs/plans/redesign/wp10-docs-examples.md,
change 3)."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = json.loads((ROOT / "docs.json").read_text(encoding="utf-8"))


def listed_pages(node, out):
    if isinstance(node, dict):
        for key in ("tabs", "groups", "pages"):
            if key in node:
                listed_pages(node[key], out)
    elif isinstance(node, list):
        for item in node:
            listed_pages(item, out)
    elif isinstance(node, str):
        out.append(node)
    return out


def test_every_listed_page_exists_and_every_page_is_listed_once():
    listed = listed_pages(DOCS["navigation"], [])
    assert len(listed) == len(set(listed)), [p for p in listed if listed.count(p) > 1]
    missing = [page for page in listed if not (ROOT / f"{page}.mdx").is_file()]
    assert missing == []
    on_disk = {str(path.relative_to(ROOT))[:-4] for path in (ROOT / "docs").rglob("*.mdx")}
    unlisted = sorted(on_disk - set(listed))
    assert unlisted == [], unlisted


def test_every_redirect_lands_on_a_page_that_exists():
    # A destination resolves as Mintlify serves it: an anchor stripped, a
    # directory path landing on its index page; a redirect never chains
    # into another redirect, and a live page is never a redirect's source.
    listed = set(listed_pages(DOCS["navigation"], []))
    sources = {redirect["source"] for redirect in DOCS["redirects"]}
    for redirect in DOCS["redirects"]:
        destination = redirect["destination"].split("#")[0]
        page = destination.lstrip("/")
        assert page in listed or f"{page}/index" in listed, redirect
        assert destination not in sources, redirect
        assert redirect["source"].lstrip("/") not in listed, redirect


def test_the_pages_the_design_retired_redirect():
    # Regression: the six Trajectory-learning paths land on the two Learn pages.
    sources = {r["source"]: r["destination"] for r in DOCS["redirects"]}
    for name in ("overview", "bank", "serving"):
        assert sources[f"/docs/learning/{name}"] == "/docs/learn/what-learn-produces"
    for name in ("pipeline", "graders", "development"):
        assert sources[f"/docs/learning/{name}"] == "/docs/learn/development-mode"
    # The Start page the plugin page absorbed.
    assert sources["/docs/agent-access"] == "/docs/coding-agent-skills"
