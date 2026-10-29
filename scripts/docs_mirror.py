#!/usr/bin/env python3
"""docs/README.md's Pages section, rendered from docs.json: every group of
every tab in sidebar order, each page by its sidebar title (or its
title) with its rendered address and its file. `--check` compares the
section with the file and exits 1 on a difference; without it the
section is rewritten in place. tests/test_docs_navigation.py runs the
check, so the mirror cannot drift from the navigation.

    python3 scripts/docs_mirror.py            # rewrite the section
    python3 scripts/docs_mirror.py --check    # CI and the tests
"""

import json
import re
import sys
from pathlib import Path
from typing import List, Tuple

REPO = Path(__file__).resolve().parent.parent
DOCS_CONFIG = REPO / "docs.json"
MIRROR = REPO / "docs" / "README.md"
SITE = "https://docs.leeroo.com"
INTRO = "Every published page with its rendered address, grouped as in the sidebar. Kept here so the folder listing on GitHub points at the site.\n"
_TITLE = {field: re.compile(rf'^{field}:\s*"?(.+?)"?\s*$', re.MULTILINE) for field in ("sidebarTitle", "title")}


def page_title(page: str) -> str:
    text = (REPO / f"{page}.mdx").read_text(encoding="utf-8")
    front = text.split("---", 2)[1]
    for field in ("sidebarTitle", "title"):
        match = _TITLE[field].search(front)
        if match:
            return match.group(1)
    raise ValueError(f"{page}: no title in the front matter")


def address(page: str) -> str:
    return f"{SITE}/{page[:-len('/index')] if page.endswith('/index') else page}"


def groups(nodes, prefix: str = "") -> List[Tuple[str, List[str]]]:
    """(group name, page paths) in sidebar order; a nested group is named
    'Outer / Inner'."""
    found = []
    for group in nodes:
        name = f"{prefix}{group['group']}"
        pages = [page for page in group.get("pages", []) if isinstance(page, str)]
        if pages:
            found.append((name, pages))
        nested = [page for page in group.get("pages", []) if isinstance(page, dict)]
        if nested:
            found.extend(groups(nested, prefix=f"{name} / "))
    return found


def render() -> str:
    """The Pages section's text, from the intro to the last line."""
    navigation = json.loads(DOCS_CONFIG.read_text(encoding="utf-8"))["navigation"]
    tabs = navigation["tabs"] if isinstance(navigation, dict) else navigation
    sections = []
    for tab in tabs:
        for name, pages in groups(tab.get("groups", [])):
            lines = [f"- [{page_title(page)}]({address(page)}) — `{page}.mdx`" for page in pages]
            sections.append(f"**{name}**\n\n" + "\n".join(lines))
    return INTRO + "\n" + "\n\n".join(sections) + "\n"


def split(text: str) -> Tuple[str, str]:
    """(the file before the Pages section, the section)."""
    if text.count(INTRO) != 1:
        raise ValueError(f"{MIRROR}: the Pages intro must appear exactly once")
    head, _, _ = text.partition(INTRO)
    return head, text[len(head):]


def main() -> int:
    text = MIRROR.read_text(encoding="utf-8")
    head, section = split(text)
    wanted = render()
    if "--check" in sys.argv[1:]:
        if section == wanted:
            print("docs/README.md mirrors docs.json")
            return 0
        print("docs/README.md's Pages section differs from docs.json; run scripts/docs_mirror.py")
        return 1
    MIRROR.write_text(head + wanted, encoding="utf-8")
    print(f"docs/README.md: the Pages section rewritten from {DOCS_CONFIG.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
