"""The harness manifest and the content hash: the trading example parses to
the attachments its file lists; every structural rule names its line; the
hash follows the content and nothing else."""

import shutil
from pathlib import Path

import pytest

from kapso.harness import (
    HarnessEnvironment,
    ManifestError,
    ModuleAttachments,
    harness_hash,
    inspect_manifest,
    read_manifest,
    short,
)

TRADING = Path(__file__).resolve().parent.parent / "examples" / "harnesses" / "trading"


def write_manifest(root: Path, text: str) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    (root / "harness.yaml").write_text(text, encoding="utf-8")
    return root


MINIMAL = "schema_version: 1\nname: x\nversion: 0.1.0\ndescription: A harness.\n"


# ------------------------------------------------------------- the example

def test_the_trading_example_parses_to_its_listed_attachments():
    manifest = read_manifest(TRADING)
    assert (manifest.name, manifest.version) == ("trading", "0.1.0")
    assert manifest.environment == HarnessEnvironment(python=TRADING / "requirements.txt")
    assert manifest.module("implementation") == ModuleAttachments(
        skills=("backtesting", "market-data", "risk-limits", "lookahead-scan"),
        mcp_servers=("market-data",),
        agents=("lookahead-auditor",),
        hooks=("session-brief", "deny-web-fetch", "protect-prepared",
               "deny-snapshot", "scan-writes", "require-results"),
    )
    # A module the file leaves out has no attachments, and is not an error.
    assert manifest.module("learning") == ModuleAttachments()
    assert manifest.module("learning").empty()
    # Every listed name of a kind, in manifest order, once.
    assert manifest.listed("mcp_servers") == ("market-data", "broker")
    assert manifest.listed("agents") == ("lookahead-auditor", "risk-reviewer")


def test_the_minimal_manifest_is_identity_alone(tmp_path):
    manifest = read_manifest(write_manifest(tmp_path / "x", MINIMAL))
    assert manifest.modules == {}
    assert manifest.environment == HarnessEnvironment()
    assert manifest.module("setup").empty()


def test_an_empty_module_entry_means_no_attachments(tmp_path):
    manifest = read_manifest(write_manifest(tmp_path / "x", MINIMAL + "modules:\n  setup:\n"))
    assert manifest.module("setup") == ModuleAttachments()


# ----------------------------------------------------------------- the rules

@pytest.mark.parametrize("text, line, message", [
    ("schema_version: 2\nname: x\nversion: 0.1.0\ndescription: d\n", 1, "schema_version 2 is not supported"),
    ("name: x\nversion: 0.1.0\ndescription: d\n", 1, "`schema_version` is required"),
    (MINIMAL + "owner: me\n", 5, "unknown key `owner` in the manifest"),
    (MINIMAL + "modules:\n  verify:\n    skills: []\n", 6, "unknown key `verify` in modules"),
    (MINIMAL + "modules:\n  setup:\n    skils: [a]\n", 7, "unknown key `skils` in modules.setup"),
    (MINIMAL + "modules:\n  setup:\n    skills: a\n", 7, "modules.setup.skills must be a list"),
    (MINIMAL + "modules:\n  setup:\n    skills: [a, a]\n", 7, "`a` is listed twice"),
    (MINIMAL + "environment:\n  gpu: yes please\n", 6, "environment.gpu is true or false"),
    (MINIMAL + "environment:\n  model: gpt\n", 6, "unknown key `model` in environment"),
    ("schema_version: 1\nname: Trading\nversion: 0.1.0\ndescription: d\n", 2, "must match [a-z0-9][a-z0-9-]*"),
    ("schema_version: 1\nname: x\nversion: 0.1.0\ndescription: ''\n", 4, "description must be a non-empty string"),
    (MINIMAL + "modules:\n  setup:\n    skills: [a]\n  setup:\n    skills: [b]\n", 8, "`setup` appears twice"),
])
def test_every_structural_rule_names_its_line(tmp_path, text, line, message):
    root = write_manifest(tmp_path / "x", text)
    with pytest.raises(ManifestError) as caught:
        read_manifest(root)
    assert f"harness.yaml:{line}:" in str(caught.value)
    assert message in str(caught.value)


def test_every_finding_is_reported_at_once(tmp_path):
    # `check` shows them all; `read_manifest` raises them all.
    root = write_manifest(tmp_path / "x", MINIMAL + "owner: me\nmodules:\n  setup:\n    skils: [a]\n  verify: {}\n")
    manifest, findings = inspect_manifest(root)
    assert manifest is not None and manifest.name == "x"
    assert [str(f) for f in findings] == [
        "harness.yaml:5: unknown key `owner` in the manifest; the keys are schema_version, name, version, description, environment, modules",
        "harness.yaml:8: unknown key `skils` in modules.setup; the keys are skills, mcp_servers, agents, hooks",
        "harness.yaml:9: unknown key `verify` in modules; the keys are setup, ideation, implementation, verification, feedback, learning, deployment",
    ]
    with pytest.raises(ManifestError) as caught:
        read_manifest(root)
    assert caught.value.findings == findings


def test_a_manifest_without_an_identity_yields_no_manifest(tmp_path):
    manifest, findings = inspect_manifest(write_manifest(tmp_path / "x", "schema_version: 1\nname: Bad Name\n"))
    assert manifest is None
    assert [f.message for f in findings] == [
        "`version` is required", "`description` is required",
        "name 'Bad Name' must match [a-z0-9][a-z0-9-]*",
    ]


def test_a_missing_manifest_names_the_directory(tmp_path):
    (tmp_path / "x").mkdir()
    with pytest.raises(ManifestError, match="no harness.yaml"):
        read_manifest(tmp_path / "x")


def test_a_file_that_does_not_parse_raises_the_parsers_error(tmp_path):
    root = write_manifest(tmp_path / "x", "name: [unclosed\n")
    with pytest.raises(Exception) as caught:
        read_manifest(root)
    assert not isinstance(caught.value, ManifestError)
    assert "line" in str(caught.value)


def test_a_numeric_version_is_read_as_text(tmp_path):
    manifest = read_manifest(write_manifest(tmp_path / "x", "schema_version: 1\nname: x\nversion: 1.0\ndescription: d\n"))
    assert manifest.version == "1.0"


# ------------------------------------------------------------------ the hash

def test_the_hash_follows_the_content_and_nothing_else(tmp_path):
    copy = tmp_path / "trading"
    shutil.copytree(TRADING, copy)
    first = harness_hash(copy)
    assert first == harness_hash(copy) == harness_hash(TRADING)
    assert len(first) == 64 and len(short(first)) == 12

    (copy / "__pycache__").mkdir()
    (copy / "__pycache__" / "x.pyc").write_bytes(b"\x00")
    (copy / "servers" / "market_data.pyc").write_bytes(b"\x00")
    assert harness_hash(copy) == first

    page = copy / "instructions" / "guardrails.md"
    page.write_text(page.read_text() + " ")
    assert harness_hash(copy) != first
