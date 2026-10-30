"""The harnesses that ship inside the package (docs/plans/redesign/wp8-harness-ports.md,
change 2): each one passes `check` with no failure and no warning at the
packaged page budget, is named after its directory, resolves by its bare
name, and `kapso harness list` prints it under `bundled`. A port that
ships broken is caught here, not by a user."""

import re
import subprocess
import sys
from pathlib import Path

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


def test_every_bundled_file_is_tracked_by_git():
    """`.gitignore` ignores every directory named *cache*; a skill named that
    way checked clean on disk and shipped nowhere. A bundled file git does
    not track is a file the wheel will not carry."""
    tracked = subprocess.run(
        ["git", "ls-files", "--", str(BUNDLED_ROOT)], capture_output=True, text=True, check=True,
        cwd=str(BUNDLED_ROOT),
    ).stdout.splitlines()
    tracked_paths = {str((BUNDLED_ROOT / path).resolve()) for path in tracked} | {
        str(Path(line).resolve()) for line in tracked
    }
    on_disk = {str(path.resolve()) for path in BUNDLED_ROOT.rglob("*")
               if path.is_file() and "__pycache__" not in path.parts}
    untracked = sorted(path for path in on_disk if path not in tracked_paths)
    assert untracked == [], untracked


SHARED_SKILLS = ("task-type-playbooks", "cv-protocol", "ensembling", "eda-discipline", "hf-model-fetch", "tabular-modeling")
_SKILL_REFERENCE = re.compile(r"\bthe ([a-z0-9-]+) skill\b")


@pytest.mark.parametrize("path", BUNDLED, ids=[path.name for path in BUNDLED])
def test_a_skill_names_only_skills_its_own_harness_carries(path):
    """A copied skill that points at a skill its harness does not carry
    sends the session to a page that is not there (the contest harness's
    tabular skill named two modelling skills, 2026-10-30): the references
    inside the skills resolve as the pages' do."""
    skills = {skill.name for skill in (path / "skills").iterdir() if skill.is_dir()}
    unresolved = []
    for page in sorted(path.glob("skills/*/SKILL.md")) + sorted(path.glob("skills/*/references/*.md")):
        for name in sorted(set(_SKILL_REFERENCE.findall(page.read_text(encoding="utf-8")))):
            if name not in skills:
                unresolved.append(f"{page.relative_to(path)} -> the {name} skill")
    assert unresolved == [], unresolved


@pytest.mark.parametrize("skill", SHARED_SKILLS)
def test_a_modelling_skill_the_contest_harness_copies_is_identical_to_its_source(skill):
    """The port mapping has the contest harness copy the modelling skills it
    needs (a skill is a plain directory; composition is not in the design);
    a copy that drifts from its source is the bug this test catches."""
    source = BUNDLED_ROOT / "predictive-modelling" / "skills" / skill
    copy = BUNDLED_ROOT / "competitive-programming" / "skills" / skill
    source_files = {path.relative_to(source): path.read_bytes() for path in source.rglob("*") if path.is_file()}
    copy_files = {path.relative_to(copy): path.read_bytes() for path in copy.rglob("*") if path.is_file()}
    assert source_files == copy_files


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
