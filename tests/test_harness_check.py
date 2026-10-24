"""`check`: every failure rule, every warning, and what the machine lacks,
each pinned on a copy of the trading example mutated one rule at a time;
the example itself is clean."""

import json
import shutil
from pathlib import Path

import pytest

from kapso.harness import CheckReport, check_harness

TRADING = Path(__file__).resolve().parent.parent / "examples" / "harnesses" / "trading"
BUILD_MODULES = ("setup", "ideation", "implementation", "verification", "feedback")


@pytest.fixture
def harness(tmp_path) -> Path:
    copy = tmp_path / "trading"
    shutil.copytree(TRADING, copy)
    return copy


def check(root: Path, **overrides) -> CheckReport:
    options = dict(page_warning_lines=40, dotenv_path="")
    options.update(overrides)
    return check_harness(root, **options)


def edit(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    assert old in text, (path, old)
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def edit_json(path: Path, mutate) -> None:
    data = json.loads(path.read_text(encoding="utf-8"))
    mutate(data)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


# -------------------------------------------------------------- the example

def test_the_trading_example_is_clean():
    report = check(TRADING)
    assert report.failures == []
    assert report.warnings == []
    assert report.counts == {"skills": 7, "agents": 2, "servers": 2, "hooks": 6}
    assert report.summary() == "check ok (7 skills, 2 agents, 2 servers, 6 hooks)"
    assert report.manifest is not None and report.manifest.name == "trading"


# ------------------------------------------------------------- the failures

def no_front_matter(root):
    (root / "skills" / "backtesting" / "SKILL.md").write_text("# Backtesting\n")


def wrong_skill_name(root):
    edit(root / "skills" / "backtesting" / "SKILL.md", "name: backtesting", "name: backtest")


def no_description(root):
    edit(root / "agents" / "risk-reviewer.md", "description:", "summary:")


def unresolved_skill(root):
    edit(root / "harness.yaml", "skills: [market-data]\n    mcp_servers", "skills: [market-dat]\n    mcp_servers")


def missing_agent(root):
    (root / "agents" / "risk-reviewer.md").unlink()


def no_mcp_file(root):
    (root / "mcp.json").unlink()


def renamed_server(root):
    edit_json(root / "mcp.json", lambda d: d["mcpServers"].update(brokerage=d["mcpServers"].pop("broker")))


def reserved_server(root):
    edit_json(root / "mcp.json", lambda d: d["mcpServers"].update({"gated-knowledge": {"command": "python3", "args": []}}))


def bad_server_name(root):
    edit_json(root / "mcp.json", lambda d: d["mcpServers"].update({"market.data": {"command": "python3"}}))


def server_without_transport(root):
    edit_json(root / "mcp.json", lambda d: d["mcpServers"].update(odd={"args": []}))


def literal_key(root):
    edit_json(root / "mcp.json", lambda d: d["mcpServers"]["broker"].update(env={"BROKER_API_KEY": "abc123"}))


def credential_prefix(root):
    edit_json(root / "mcp.json", lambda d: d["mcpServers"]["broker"].update(env={"REGION": "sk-abcdef"}))


def unknown_server_key(root):
    edit_json(root / "mcp.json", lambda d: d["mcpServers"]["broker"].update(model="x"))


def bad_url(root):
    edit_json(root / "mcp.json", lambda d: d["mcpServers"].update(remote={"url": "ftp://x"}))


def no_hook_file(root):
    (root / "hooks" / "deny-snapshot" / "hook.json").unlink()


def unknown_event(root):
    edit(root / "hooks" / "deny-snapshot" / "hook.json", '"PreToolUse"', '"BeforeTool"')


def missing_script(root):
    edit(root / "hooks" / "deny-snapshot" / "hook.json", "deny_snapshot.py", "deny_snap.py")


def malformed_hook_entry(root):
    edit(root / "hooks" / "require-results" / "hook.json", '"type": "command"', '"type": "shell"')


def no_requirements(root):
    (root / "requirements.txt").unlink()


def no_pages(root):
    shutil.rmtree(root / "instructions")


def unknown_manifest_key(root):
    (root / "harness.yaml").write_text((root / "harness.yaml").read_text() + "owner: me\n")


@pytest.mark.parametrize("mutate, message", [
    (no_front_matter, "skills/backtesting/SKILL.md:1: no front matter"),
    (wrong_skill_name, "front matter name 'backtest' must be `backtesting`"),
    (no_description, "agents/risk-reviewer.md:2: front matter needs a non-empty description"),
    (unresolved_skill, "modules.setup lists skill `market-dat`, and skills/market-dat/SKILL.md does not exist"),
    (missing_agent, "lists agent `risk-reviewer`, and agents/risk-reviewer.md does not exist"),
    (no_mcp_file, "lists server `market-data`, and there is no mcp.json"),
    (renamed_server, "lists server `broker`, and mcp.json has no such key"),
    (reserved_server, "server name `gated-knowledge` is the engine's own knowledge server"),
    (bad_server_name, "server name `market.data` must match [A-Za-z0-9_-]+"),
    (server_without_transport, "server `odd` has neither `command` (stdio) nor `url`"),
    (literal_key, "env.BROKER_API_KEY is a literal where a reference is expected"),
    (credential_prefix, "env.REGION looks like a credential"),
    (unknown_server_key, "server `broker`: unknown key(s) model"),
    (bad_url, "server `remote`: `url` must be an http(s) URL"),
    (no_hook_file, "lists hook `deny-snapshot`, and hooks/deny-snapshot/hook.json does not exist"),
    (unknown_event, "hooks/deny-snapshot/hook.json: unknown event `BeforeTool`"),
    (missing_script, "names ${PLUGIN_ROOT}/hooks/deny-snapshot/deny_snap.py, and hooks/deny-snapshot/deny_snap.py does not exist"),
    (malformed_hook_entry, 'hooks/require-results/hook.json: Stop: each hook is {"type": "command", "command": "..."}'),
    (no_requirements, "environment.python names requirements.txt, which does not exist"),
    (no_pages, "no instruction page"),
    (unknown_manifest_key, "harness.yaml:34: unknown key `owner`"),
])
def test_each_failure_rule(harness, mutate, message):
    mutate(harness)
    report = check(harness)
    assert any(message in str(f) for f in report.failures), [str(f) for f in report.failures]
    assert not report.ok()
    assert report.summary().startswith("check failed: ")


def test_an_unparseable_file_raises_the_parsers_error(harness):
    (harness / "mcp.json").write_text("{not json")
    with pytest.raises(json.JSONDecodeError):
        check(harness)


# -------------------------------------------------------------- the warnings

def unlisted_skill(root):
    (root / "skills" / "extra").mkdir()
    (root / "skills" / "extra" / "SKILL.md").write_text("---\nname: extra\ndescription: Spare.\n---\n")


def unmentioned_skill(root):
    # risk-limits is listed on ideation, whose page never names it.
    edit(root / "harness.yaml", "skills: [strategy-families, market-structure]",
         "skills: [strategy-families, market-structure, risk-limits]")


def long_page(root):
    page = root / "instructions" / "guardrails.md"
    page.write_text(page.read_text() + "- a rule\n" * 50)


def opaque_env(root):
    edit_json(root / "mcp.json", lambda d: d["mcpServers"]["broker"].update(env={"REGION": "a" * 30}))


def unlisted_hook(root):
    (root / "hooks" / "extra").mkdir()


def orphan_page(root):
    (root / "instructions" / "verify.md").write_text("# Verify\n")


def unlisted_server(root):
    edit_json(root / "mcp.json", lambda d: d["mcpServers"].update(spare={"command": "python3"}))


@pytest.mark.parametrize("mutate, message", [
    (unlisted_skill, "skills/extra/: defined, and no module lists it"),
    (unmentioned_skill, "instructions/ideation.md: skill `risk-limits` is listed on ideation and never named here"),
    (long_page, "instructions/guardrails.md: 7"),
    (opaque_env, "env.REGION is a long opaque value"),
    (unlisted_hook, "hooks/extra/: defined, and no module lists it"),
    (orphan_page, "instructions/verify.md: a page no module reads"),
    (unlisted_server, "server `spare` is defined, and no module lists it"),
])
def test_each_warning_rule(harness, mutate, message):
    mutate(harness)
    report = check(harness)
    assert report.failures == [], [str(f) for f in report.failures]
    assert any(message in str(w) for w in report.warnings), [str(w) for w in report.warnings]
    assert report.ok()


def test_the_page_length_threshold_comes_from_the_caller(harness):
    assert check(harness, page_warning_lines=5).warnings
    assert not check(harness, page_warning_lines=400).warnings


# --------------------------------------------------------- what is missing

def test_a_program_a_hook_runs_must_be_on_path(harness, monkeypatch):
    monkeypatch.setattr("kapso.harness.check.shutil.which", lambda name: None if name == "python" else "/usr/bin/" + name)
    report = check(harness)
    assert report.failures == []
    rows = [row for row in report.missing if row.label.startswith("python (command")]
    assert rows, [row.label for row in report.missing]
    assert "python3" in rows[0].fix and rows[0].ok is False
    # The hooks that name `python` are listed on every module, so the row
    # binds a build and a deploy alike.
    assert report.missing_for(("deployment",)) and report.missing_for(BUILD_MODULES)


def test_an_env_reference_is_a_prerequisite_of_the_modules_that_mount_the_server(harness, monkeypatch, tmp_path):
    edit_json(harness / "mcp.json", lambda d: d["mcpServers"]["broker"].update(env={"BROKER_API_KEY": "${BROKER_API_KEY}"}))
    monkeypatch.delenv("BROKER_API_KEY", raising=False)
    report = check(harness)
    assert report.failures == [] and report.warnings == []
    rows = [row for row in report.missing if row.label.startswith("BROKER_API_KEY")]
    assert rows and rows[0].modules == ("deployment",)
    assert rows[0].fix == "add BROKER_API_KEY=... to .env"
    # A build does not mount the broker, so it is advisory for a build.
    assert not [row for row in report.missing_for(BUILD_MODULES) if row.label.startswith("BROKER_API_KEY")]
    # Present in .env by name: satisfied, no value read.
    dotenv = tmp_path / ".env"
    dotenv.write_text("BROKER_API_KEY=paper\n")
    assert not [row for row in check(harness, dotenv_path=str(dotenv)).missing if row.label.startswith("BROKER_API_KEY")]


def test_requirements_are_checked_against_the_engines_interpreter(harness):
    requirements = harness / "requirements.txt"
    requirements.write_text('pyyaml>=5\nnonexistent-dist-xyz>=1\nalso-absent; python_version < "3"\n')
    report = check(harness)
    labels = [row.label for row in report.missing if row.label.startswith("python:")]
    assert labels == ["python: nonexistent-dist-xyz"]
    row = next(row for row in report.missing if row.label == "python: nonexistent-dist-xyz")
    assert "-m pip install -r " in row.fix and row.modules == tuple(__import__("kapso.harness").harness.MODULES)


def test_a_gpu_and_a_command_are_prerequisites_of_every_module(harness, monkeypatch):
    edit(harness / "harness.yaml", "environment:\n  python: requirements.txt\n",
         "environment:\n  python: requirements.txt\n  gpu: true\n  commands: [backtester]\n")
    monkeypatch.setattr("kapso.harness.check.shutil.which", lambda name: None if name in ("nvidia-smi", "backtester") else "/usr/bin/" + name)
    report = check(harness)
    labels = [row.label for row in report.missing]
    assert "backtester (command)" in labels and "a GPU (environment.gpu)" in labels


def test_render_shows_the_summary_then_each_kind(harness, monkeypatch):
    unlisted_hook(harness)
    monkeypatch.setattr("kapso.harness.check.shutil.which", lambda name: None if name == "python" else "/usr/bin/" + name)
    text = check(harness).render()
    lines = text.splitlines()
    assert lines[0] == "check ok (7 skills, 2 agents, 2 servers, 7 hooks)"
    assert any(line.startswith("  warn   hooks/extra/") for line in lines)
    assert any(line.startswith("  needs  python (command") and line.endswith("]") for line in lines)
