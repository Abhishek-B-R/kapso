"""One release number (Rule 1).

kapso.__version__ sat at 0.1.0 through five releases because nothing tied
it to pyproject.toml. This makes the drift a suite failure: bump one, the
test names the other.
"""

import json
import re
from pathlib import Path

import pytest

import kapso
from kapso.cli import build_parser
from kapso.gated_mcp.host_session import _parse_args

_PYPROJECT = Path(__file__).parent.parent / "pyproject.toml"


def test_package_version_matches_pyproject():
    match = re.search(r'^version = "([^"]+)"$', _PYPROJECT.read_text(), re.M)
    assert match, "pyproject.toml has no version line"
    assert kapso.__version__ == match.group(1)


def test_the_plugin_carries_the_same_version():
    """The plugin's manifests, the marketplace entry and the launcher's
    pin name the package's version (docs/plans/redesign/wp7-plugin.md):
    the skills' facts are written for it, and the launcher serves it."""
    root = _PYPROJECT.parent
    for manifest in (".claude-plugin/plugin.json", ".codex-plugin/plugin.json", ".cursor-plugin/plugin.json"):
        assert json.loads((root / "plugin" / manifest).read_text())["version"] == kapso.__version__, manifest
    launcher = (root / "plugin" / "scripts" / "kapso-mcp").read_text()
    assert re.search(r'^KAPSO_VERSION="([^"]+)"$', launcher, re.M).group(1) == kapso.__version__


def test_the_two_commands_print_the_version(capsys):
    """`kapso --version` and `kapso-mcp --version` agree: the setup skill
    reads both to tell one install from two."""
    with pytest.raises(SystemExit) as stop:
        build_parser().parse_args(["--version"])
    assert stop.value.code == 0 and capsys.readouterr().out.strip() == f"kapso {kapso.__version__}"
    with pytest.raises(SystemExit) as stop:
        _parse_args(["--version"])
    assert stop.value.code == 0 and capsys.readouterr().out.strip() == f"kapso-mcp {kapso.__version__}"
