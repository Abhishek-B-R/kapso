"""The examples' drivers (wp10-docs-examples.md, change 9): every example
is a task with a brief, a README and `run.py`; every driver compiles (a
module-level `return` or a syntax slip is caught here), holds at most twelve
lines of code (the promise examples/README.md makes), and calls the Kapso
instance only through methods the API has, with arguments its signatures
bind (a misspelled method, a missing required argument, an unknown keyword
or a positional where none is taken fails); and every `kapso` command line
the examples' READMEs show (the table's one command, the run steps) parses
against the CLI's own parsers, so a line a reader copies is one the CLI
accepts."""
import ast
import inspect
import shlex
from pathlib import Path

import pytest

from kapso import Kapso
from kapso.cli import build_parser
from kapso.cli.learn import normalize_argv
from tests.kapso_lines import PLACEHOLDER, fenced_bash_lines, inline_lines

EXAMPLES = Path(__file__).resolve().parents[1] / "examples"
TASKS = sorted(path for path in EXAMPLES.iterdir() if path.is_dir() and path.name != "harnesses")
CODE_LINE_BUDGET = 12
KAPSO_METHODS = {name for name, _ in inspect.getmembers(Kapso, predicate=inspect.isfunction) if not name.startswith("_")}
READMES = [EXAMPLES / "README.md", *sorted(EXAMPLES.glob("*/README.md"))]
COMMAND_LINES = [
    pytest.param(readme.relative_to(EXAMPLES.parent).as_posix(), line, id=f"{readme.parent.name}: {line[:60]}")
    for readme in READMES
    for text in [readme.read_text(encoding="utf-8")]
    for line in [*fenced_bash_lines(text), *inline_lines(text)]
]
ARGUMENT = object()


def code_lines(tree: ast.Module, source: str) -> int:
    """The lines that are code: not blank, not a comment, not the module docstring."""
    first = tree.body[0] if tree.body else None
    docstring = first if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant) else None
    skipped = set(range(docstring.lineno, docstring.end_lineno + 1)) if docstring is not None else set()
    return sum(
        1 for number, line in enumerate(source.splitlines(), start=1)
        if number not in skipped and line.strip() and not line.strip().startswith("#")
    )


def _is_kapso_constructor(node: ast.AST) -> bool:
    return isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "Kapso"


def kapso_calls(tree: ast.Module):
    """Every call on the Kapso instance: `Kapso().method(...)`, or `name.method(...)`
    where `name` was bound to `Kapso(...)`."""
    bound = {
        target.id
        for node in ast.walk(tree) if isinstance(node, ast.Assign) and _is_kapso_constructor(node.value)
        for target in node.targets if isinstance(target, ast.Name)
    }
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)):
            continue
        receiver = node.func.value
        if _is_kapso_constructor(receiver) or (isinstance(receiver, ast.Name) and receiver.id in bound):
            yield node


def test_every_example_is_a_task_with_a_driver():
    for task in TASKS:
        for name in ("README.md", "kapso-brief.md", "run.py"):
            assert (task / name).is_file(), f"{task.name} lacks {name}"


@pytest.mark.parametrize("task", TASKS, ids=[task.name for task in TASKS])
def test_a_driver_is_short_and_calls_the_api_as_it_is(task):
    driver = task / "run.py"
    source = driver.read_text(encoding="utf-8")
    compile(source, str(driver), "exec")                   # a module-level return or a syntax slip fails here
    tree = ast.parse(source, filename=str(driver))
    assert code_lines(tree, source) <= CODE_LINE_BUDGET, f"{task.name}/run.py is over {CODE_LINE_BUDGET} lines of code"
    calls = list(kapso_calls(tree))
    assert calls, f"{task.name}/run.py calls nothing on the Kapso instance"
    for call in calls:
        method = call.func.attr
        assert method in KAPSO_METHODS, f"{task.name}/run.py: Kapso has no method {method!r}"
        assert not any(isinstance(argument, ast.Starred) for argument in call.args), f"{task.name}/run.py: {method}() with *args"
        assert all(keyword.arg for keyword in call.keywords), f"{task.name}/run.py: {method}() with **kwargs"
        signature = inspect.signature(getattr(Kapso, method))
        # TypeError here names the missing, unknown or misplaced argument.
        signature.bind(ARGUMENT, *[ARGUMENT] * len(call.args), **{keyword.arg: ARGUMENT for keyword in call.keywords})


@pytest.mark.parametrize("source, line", COMMAND_LINES)
def test_every_command_line_the_examples_show_parses(source, line):
    words = shlex.split(PLACEHOLDER.sub("x", line).replace("…", "x"))
    build_parser().parse_args(normalize_argv(words[1:]))
