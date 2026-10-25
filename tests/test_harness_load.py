"""Loading a harness: a failing one never loads, what the machine lacks
lands in `missing` with its fix and its modules, the handle's identity is
what the records carry, the config block reaches `check` from any
config file, and the facade holds one harness at a time."""

import shutil
from pathlib import Path

import pytest

from kapso.core.config import PLATFORM_CONFIG_PATH, load_harness_defaults
from kapso.handles import HarnessRef
from kapso.harness import BUILD_MODULES, DEPLOY_MODULES, HarnessError, harness_hash, load_harness, reload_harness
from kapso.kapso import Kapso

TRADING = Path(__file__).resolve().parent.parent / "examples" / "harnesses" / "trading"


def settings(tmp_path, **overrides):
    values = dict(load_harness_defaults(), store=str(tmp_path / "store"))
    values.update(overrides)
    return values


def test_a_loaded_harness_carries_its_identity_and_directory(tmp_path):
    said = []
    harness = load_harness(str(TRADING), settings=settings(tmp_path), say=said.append)
    assert (harness.name, harness.version) == ("trading", "0.1.0")
    assert harness.path == TRADING.resolve() and harness.source == str(TRADING.resolve())
    assert harness.hash == harness_hash(TRADING) and len(harness.hash) == 64
    assert harness.ref() == HarnessRef(name="trading", version="0.1.0", hash=harness.hash, source=str(TRADING.resolve()))
    assert harness.label() == f"trading 0.1.0 ({harness.hash[:12]})"
    assert harness.module("implementation").agents == ("lookahead-auditor",)
    assert said == []   # clean: no warning said, nothing fetched


def test_a_failing_harness_never_loads(tmp_path):
    copy = tmp_path / "broken"
    shutil.copytree(TRADING, copy)
    (copy / "agents" / "risk-reviewer.md").unlink()
    with pytest.raises(HarnessError) as caught:
        load_harness(str(copy), settings=settings(tmp_path))
    assert "fails check:" in str(caught.value)
    assert "lists agent `risk-reviewer`, and agents/risk-reviewer.md does not exist" in str(caught.value)


def test_warnings_are_said_and_do_not_stop_the_load(tmp_path):
    copy = tmp_path / "wordy"
    shutil.copytree(TRADING, copy)
    said = []
    harness = load_harness(str(copy), settings=settings(tmp_path, page_warning_lines=3), say=said.append)
    assert harness.name == "trading"
    assert said and all(line.startswith("warning: instructions/") for line in said)


def test_what_the_machine_lacks_is_read_into_missing_with_its_modules(tmp_path, monkeypatch):
    copy = tmp_path / "needs"
    shutil.copytree(TRADING, copy)
    manifest = copy / "harness.yaml"
    manifest.write_text(manifest.read_text().replace(
        "environment:\n  python: requirements.txt\n",
        "environment:\n  python: requirements.txt\n  commands: [backtester]\n",
    ))
    monkeypatch.setattr("kapso.harness.check.shutil.which", lambda name: None if name == "backtester" else "/usr/bin/" + name)
    harness = load_harness(str(copy), settings=settings(tmp_path), say=lambda line: None)
    [row] = [row for row in harness.missing if row.label == "backtester (command)"]
    assert row.ok is False and row.fix == "install backtester and put it on PATH"
    assert set(BUILD_MODULES) <= set(row.modules) and set(DEPLOY_MODULES) <= set(row.modules)
    assert harness.missing_for(BUILD_MODULES) and harness.missing_for(DEPLOY_MODULES)


def test_reload_sees_an_edit_made_after_the_load(tmp_path):
    copy = tmp_path / "live"
    shutil.copytree(TRADING, copy)
    first = load_harness(str(copy), settings=settings(tmp_path), say=lambda line: None)
    page = copy / "instructions" / "guardrails.md"
    page.write_text(page.read_text() + "\n- one more rule\n")
    again = reload_harness(first, settings=settings(tmp_path), say=lambda line: None)
    assert again.hash != first.hash and again.path == first.path


def test_the_harness_block_reaches_the_loader_from_any_config_file(tmp_path):
    platform = load_harness_defaults()
    assert platform["store"] == "~/.kapso/harnesses" and platform["page_warning_lines"] == 40
    assert load_harness_defaults(str(PLATFORM_CONFIG_PATH)) == platform
    bare = tmp_path / "mine.yaml"
    bare.write_text("default_mode: GENERIC\nmodes:\n  GENERIC: {}\n")
    assert load_harness_defaults(str(bare)) == platform
    tuned = tmp_path / "tuned.yaml"
    tuned.write_text("harness:\n  page_warning_lines: 5\n")
    merged = load_harness_defaults(str(tuned))
    assert merged["page_warning_lines"] == 5 and merged["store"] == platform["store"]


def test_the_facade_holds_one_harness_at_a_time(tmp_path, capsys):
    kapso = Kapso()
    assert kapso.harness is None
    first = kapso.load_harness(str(TRADING))
    assert kapso.harness is first and first.name == "trading"
    out = capsys.readouterr().out
    assert f"Harness: {first.label()} from {TRADING.resolve()}" in out

    other = tmp_path / "other"
    shutil.copytree(TRADING, other)
    (other / "harness.yaml").write_text((other / "harness.yaml").read_text().replace("version: 0.1.0", "version: 0.2.0"))
    second = kapso.load_harness(str(other))
    assert kapso.harness is second and second.version == "0.2.0" and second is not first
