"""The examples' drivers (wp10-docs-examples.md, change 9): every example
is a task with a brief, a README and `run.py`; every driver compiles,
holds at most twelve lines of code (the promise examples/README.md makes),
and passes only keywords the API exposes on the Kapso method it calls, so
a driver cannot drift from the interface it demonstrates."""
import ast
import inspect
from pathlib import Path

import pytest

from kapso import Kapso

EXAMPLES = Path(__file__).resolve().parents[1] / "examples"
TASKS = sorted(path for path in EXAMPLES.iterdir() if path.is_dir() and path.name != "harnesses")
CODE_LINE_BUDGET = 12
KAPSO_METHODS = {name for name, _ in inspect.getmembers(Kapso, predicate=inspect.isfunction) if not name.startswith("_")}


def code_lines(tree: ast.Module, source: str) -> int:
    """The lines that are code: not blank, not a comment, not the module docstring."""
    first = tree.body[0] if tree.body else None
    docstring = first if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant) else None
    skipped = set(range(docstring.lineno, docstring.end_lineno + 1)) if docstring is not None else set()
    return sum(
        1 for number, line in enumerate(source.splitlines(), start=1)
        if number not in skipped and line.strip() and not line.strip().startswith("#")
    )


def test_every_example_is_a_task_with_a_driver():
    for task in TASKS:
        for name in ("README.md", "kapso-brief.md", "run.py"):
            assert (task / name).is_file(), f"{task.name} lacks {name}"


@pytest.mark.parametrize("task", TASKS, ids=[task.name for task in TASKS])
def test_a_driver_is_short_and_names_only_the_apis_keywords(task):
    driver = task / "run.py"
    source = driver.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(driver))
    assert code_lines(tree, source) <= CODE_LINE_BUDGET, f"{task.name}/run.py is over {CODE_LINE_BUDGET} lines of code"
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr in KAPSO_METHODS:
            parameters = inspect.signature(getattr(Kapso, node.func.attr)).parameters
            unknown = [keyword.arg for keyword in node.keywords if keyword.arg is not None and keyword.arg not in parameters]
            assert not unknown, f"{task.name}/run.py: {node.func.attr}() has no keyword {unknown}"
