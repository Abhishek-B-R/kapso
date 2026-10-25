"""The experience package retired a set of names (docs/plans/redesign/
wp3-experience.md): the serving switch, the bank verb and the learn
init-bank form, the research, learn_knowledge and index_kg verbs, the
constructor's index keyword and the build flag for it, the gate's old
bank variable, the task family and the serving scope keyword, and the
`family:` card coordinate. Nothing under the code, the tests, the
skills, the examples, the benchmarks, the bot or the published docs
names one: every executable contract and every text a model or a
person reads moved to the new design. The plans and the research notes
are history and stay; the scenario fixtures recorded before the
coordinate change keep their cards as they were served, and the one
test of the rule that such a card is not eligible keeps its fixture."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCOPE = ("src", "tests", "skills", "examples", "benchmarks", "moltbook_bot", "docs", "README.md", "docs.json")
SUFFIXES = {".py", ".md", ".mdx", ".yaml", ".yml", ".json", ".toml", ".txt", ".sh"}
EXCLUDED_PARTS = ("__pycache__", ".kapso", "plans", "research")
RETIRED = re.compile(
    r"serving\.enabled"
    r"|kapso bank\b"
    r"|learn init-bank"
    r"|\b(?:kapso|k)\.research\("
    r"|Kapso\(\)\.research\("
    r"|kapso research"
    r"|learn_knowledge"
    r"|index_kg"
    r"|kg_index="
    r"|--kg-index"
    r"|KAPSO_BANK_DIR"
    r"|KAPSO_BANK_HEAD"
    r"|KAPSO_TASK_FAMILY"
    r"|KAPSO_TASK_DATASET"
    r"|kapso-mcp --gates"
    r"|serving_scope"
    r"|\bfamily:\w"
    # The observability package (wp6-observability.md): the session
    # record is session.json, with the host's runs in it; the watch tree
    # is the trace's.
    r"|harness\.json"
    r"|kapso watch[^\n`]*--tree"
)
ALLOWED_PATHS = (
    "benchmarks/relbench/data/learning_behavior/",
    "tests/test_bank_retriever.py",
)


def _files():
    for entry in SCOPE:
        path = ROOT / entry
        if path.is_file():
            yield path
            continue
        for candidate in sorted(path.rglob("*")):
            if (
                candidate.is_file()
                and candidate.suffix in SUFFIXES
                and not any(part in EXCLUDED_PARTS for part in candidate.parts)
                and candidate != Path(__file__)
            ):
                yield candidate


def test_nothing_names_a_retired_form():
    offenders = []
    for path in _files():
        relative = path.relative_to(ROOT).as_posix()
        if relative.startswith(ALLOWED_PATHS):
            continue
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            if RETIRED.search(line):
                offenders.append(f"{relative}:{number}: {line.strip()}")
    assert offenders == [], "\n".join(offenders)
