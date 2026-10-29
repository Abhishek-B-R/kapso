"""The harnesses that ship inside the package (docs/plans/redesign/wp8-harness-ports.md,
change 2): each one passes `check` with no failure and no warning at the
packaged page budget, is named after its directory, resolves by its bare
name, and `kapso harness list` prints it under `bundled`. A port that
ships broken is caught here, not by a user."""

import sys

import pytest

import kapso.cli.harness as harness_cli
from kapso.cli import main
from kapso.core.config import load_config
from kapso.harness import BUNDLED_ROOT, check_harness, parse_reference, read_manifest
from kapso.harness.manifest import MANIFEST_FILE

BUNDLED = sorted(path for path in BUNDLED_ROOT.iterdir() if (path / MANIFEST_FILE).is_file())
PAGE_WARNING_LINES = int(load_config()["harness"]["page_warning_lines"])


@pytest.mark.parametrize("path", BUNDLED, ids=[path.name for path in BUNDLED])
def test_a_bundled_harness_checks_clean_at_the_packaged_page_budget(path):
    report = check_harness(path, page_warning_lines=PAGE_WARNING_LINES, dotenv_path="")
    assert report.failures == [], report.render()
    assert report.warnings == [], report.render()
    assert read_manifest(path).name == path.name


@pytest.mark.parametrize("path", BUNDLED, ids=[path.name for path in BUNDLED])
def test_a_bundled_harness_resolves_by_its_bare_name(path):
    reference = parse_reference(path.name)
    assert reference.kind == "bundled" and reference.path == path


def test_list_prints_every_bundled_harness_under_bundled(monkeypatch, tmp_path, capsys):
    values = {"store": str(tmp_path / "store"), "page_warning_lines": PAGE_WARNING_LINES, "setup_minutes": 20,
              "verification_minutes": 10, "verification_attempts": 2, "server_tool_timeout_seconds": 600}
    monkeypatch.setattr(harness_cli, "load_config", lambda config=None: {"harness": dict(values)})
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "argv", ["kapso", "harness", "list"])
    main()
    out = capsys.readouterr().out
    assert out.startswith("bundled\n")
    for path in BUNDLED:
        manifest = read_manifest(path)
        assert f"  {manifest.name:<24} {manifest.version:<10}" in out
