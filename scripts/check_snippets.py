#!/usr/bin/env python3
"""Fail when a documentation snippet drifts from the file it quotes.

A fenced block whose info string names a file in this repository, as in
```python examples/churn-first-build/run.py, must equal that file byte for
byte (a trailing newline aside). The pages and the examples are then one
source: a page quotes something that runs. Scans every .mdx under docs/
and the repository README. An info string whose name holds no slash is a
plain title and is not checked.
"""

import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
FENCE = re.compile(r"^(?P<indent>[ \t]*)```(?P<lang>[A-Za-z0-9_+-]+)[ \t]+(?P<path>[A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)+)[ \t]*$")


def pages():
    yield REPO / "README.md"
    yield from sorted((REPO / "docs").rglob("*.mdx"))


def quoted_blocks(page: Path):
    """(fence line number, quoted path, block text) for every fence that names a file."""
    lines = page.read_text(encoding="utf-8").splitlines()
    index = 0
    while index < len(lines):
        match = FENCE.match(lines[index])
        if match is None:
            index += 1
            continue
        fence_line = index + 1
        indent = match.group("indent")
        body = []
        index += 1
        while index < len(lines) and lines[index].strip() != "```":
            line = lines[index]
            body.append(line[len(indent):] if line.startswith(indent) else line)
            index += 1
        yield fence_line, match.group("path"), "\n".join(body)
        index += 1


def main() -> int:
    failures = []
    checked = 0
    for page in pages():
        for line, path, body in quoted_blocks(page):
            source = REPO / path
            if not source.is_file():
                failures.append(f"{page.relative_to(REPO)}:{line}: quotes {path}, which does not exist")
                continue
            checked += 1
            if body.rstrip("\n") != source.read_text(encoding="utf-8").rstrip("\n"):
                failures.append(f"{page.relative_to(REPO)}:{line}: differs from {path}")
    for failure in failures:
        print(failure)
    print(f"{checked} quoted snippet(s) checked, {len(failures)} failure(s)")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
