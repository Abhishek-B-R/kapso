"""Staging a module into a session: the tree each host discovers, the
hooks merged in manifest order with the plugin root expanded, the servers
beside the gates with the environment forwarded by name on codex, the
delegates carrying the module's guidance, the record and the stream path;
idempotent, two hosts in one directory, a tracked collision refused, a
changed harness refused."""

import json
import shutil
from pathlib import Path
from types import SimpleNamespace

import pytest

from kapso.core.config import load_harness_defaults
from kapso.execution.experiment_workspace.experiment_workspace import ExperimentWorkspace
from kapso.execution.coding_agents.adapters.claude_code_agent import ClaudeCodeCodingAgent
from kapso.execution.coding_agents.adapters.codex_agent import CodexCodingAgent
from kapso.execution.coding_agents.base import CodingAgentConfig
from kapso.harness import (
    GUIDANCE_HEADING,
    HARNESS_ROOT_VARIABLE,
    HarnessError,
    load_harness,
    stage_harness,
)
from tests.handles_support import git, git_workspace

TRADING = Path(__file__).resolve().parent.parent / "examples" / "harnesses" / "trading"


@pytest.fixture
def harness(tmp_path):
    copy = tmp_path / "h" / "trading"
    shutil.copytree(TRADING, copy)
    settings = dict(load_harness_defaults(), store=str(tmp_path / "store"))
    return load_harness(str(copy), settings=settings, say=lambda line: None)


def campaign_with(tmp_path: Path, *, statement: bool = False, prepared: bool = False) -> Path:
    campaign = tmp_path / "campaign"
    campaign.mkdir(exist_ok=True)
    if statement:
        (campaign / "kapso_task.md").write_text("# Task\n\nRaise the Sharpe.\n")
    if prepared:
        (campaign / "prepared" / "market-data").mkdir(parents=True)
        (campaign / "prepared" / "market-data" / "MANIFEST.json").write_text("{}")
    return campaign


def stage(harness, module, host, tmp_path, *, session="sessions/generic_exp_0", session_id="generic_exp_0", **campaign_options):
    campaign = campaign_with(tmp_path, **campaign_options)
    session_dir = campaign / session
    session_dir.mkdir(parents=True, exist_ok=True)
    return stage_harness(harness, module, session_dir=session_dir, campaign_dir=campaign, session_id=session_id, host=host)


def tree(root: Path):
    return sorted(
        p.relative_to(root).as_posix() for p in root.rglob("*")
        if (p.is_file() or p.is_symlink()) and ".git" not in p.parts
    )


def test_the_implementation_module_on_claude_code(harness, tmp_path):
    staged = stage(harness, "implementation", "claude_code", tmp_path)
    session_dir = staged.session_dir
    assert tree(session_dir) == [
        ".claude/harness-agents.json",
        ".claude/harness-hooks.json",
        ".claude/skills/backtesting/SKILL.md",
        ".claude/skills/lookahead-scan/SKILL.md",
        ".claude/skills/lookahead-scan/scripts/rules.py",
        ".claude/skills/lookahead-scan/scripts/scan.py",
        ".claude/skills/market-data/SKILL.md",
        ".claude/skills/risk-limits/SKILL.md",
    ]
    hooks_text = (session_dir / ".claude" / "harness-hooks.json").read_text()
    hooks = json.loads(hooks_text)["hooks"]
    assert "${" not in hooks_text and str(harness.path) in hooks_text
    assert list(hooks) == ["SessionStart", "PreToolUse", "PostToolUse", "Stop"]
    assert [entry.get("matcher") for entry in hooks["PreToolUse"]] == ["Bash", "Edit|Write|MultiEdit", "mcp__market-data__snapshot"]
    agents = json.loads((session_dir / ".claude" / "harness-agents.json").read_text())
    assert list(agents) == ["lookahead-auditor"]
    assert agents["lookahead-auditor"]["description"].startswith("Audits one attempt")
    assert agents["lookahead-auditor"]["prompt"].startswith(f"{GUIDANCE_HEADING} (harness trading 0.1.0)")
    assert "You audit one attempt" in agents["lookahead-auditor"]["prompt"]

    assert staged.agent_specific == {
        "stream_artifact_path": str(tmp_path / "campaign" / ".kapso" / "sessions" / "generic_exp_0" / "stream.jsonl"),
        "settings_path": str(session_dir / ".claude" / "harness-hooks.json"),
        "agents_path": str(session_dir / ".claude" / "harness-agents.json"),
    }
    assert staged.mcp_servers == {"market-data": {
        "command": "python3",
        "args": [str(harness.path / "servers" / "market_data.py")],
        "cwd": str(session_dir),
        "env": {HARNESS_ROOT_VARIABLE: str(harness.path)},
    }}
    assert staged.allowed_tools == ["mcp__market-data"]
    assert staged.env == {HARNESS_ROOT_VARIABLE: str(harness.path)}

    guidance = staged.guidance
    assert (harness.path / "instructions" / "guardrails.md").read_text().strip() in guidance
    assert (harness.path / "instructions" / "implementation.md").read_text().strip() in guidance
    assert "- backtesting — Build and run a backtest" in guidance and "`/backtesting`" in guidance
    assert '- lookahead-auditor — Audits one attempt' in guidance and 'subagent_type "lookahead-auditor"' in guidance
    assert "- market-data — its tools are named mcp__market-data__<tool>" in guidance
    assert f"- Task statement: {session_dir / 'kapso_task.md'}" in guidance
    assert f"- Harness root: ${HARNESS_ROOT_VARIABLE} = {harness.path}" in guidance

    record = json.loads((tmp_path / "campaign" / ".kapso" / "sessions" / "generic_exp_0" / "harness.json").read_text())
    assert record["module"] == "implementation" and record["host"] == "claude_code"
    assert record["harness"] == harness.ref_dict()
    assert record["skills"] == ["backtesting", "market-data", "risk-limits", "lookahead-scan"]
    assert record["hooks"][-1] == "require-results" and record["pages"] == ["guardrails.md", "implementation.md"]
    assert staged.record == record


def test_the_same_module_on_codex(harness, tmp_path):
    mcp = harness.path / "mcp.json"
    data = json.loads(mcp.read_text())
    data["mcpServers"]["market-data"]["env"] = {"MARKET_TOKEN": "${MARKET_TOKEN}", "REGION": "eu"}
    mcp.write_text(json.dumps(data, indent=2))
    settings = dict(load_harness_defaults(), store=str(tmp_path / "store"))
    harness = load_harness(str(harness.path), settings=settings, say=lambda line: None)

    staged = stage(harness, "implementation", "codex", tmp_path)
    session_dir = staged.session_dir
    assert tree(session_dir) == [
        ".agents/skills/backtesting/SKILL.md",
        ".agents/skills/lookahead-scan/SKILL.md",
        ".agents/skills/lookahead-scan/scripts/rules.py",
        ".agents/skills/lookahead-scan/scripts/scan.py",
        ".agents/skills/market-data/SKILL.md",
        ".agents/skills/risk-limits/SKILL.md",
        ".codex/harness-agents/lookahead-auditor.toml",
        ".codex/hooks.json",
    ]
    role = (session_dir / ".codex" / "harness-agents" / "lookahead-auditor.toml").read_text()
    assert role.startswith('developer_instructions = "')
    assert json.loads(role.split(" = ", 1)[1]).startswith(f"{GUIDANCE_HEADING} (harness trading 0.1.0)")
    assert staged.agent_specific["hooks_trust_bypass"] is True
    assert "settings_path" not in staged.agent_specific and "agents_path" not in staged.agent_specific
    assert staged.agent_specific["agents"] == {"lookahead-auditor": {
        "description": "Audits one attempt for look-ahead and leakage in signal timing, joins, resampling and data access, and reports pass, fail or inconclusive with evidence.",
        "config_file": str(session_dir / ".codex" / "harness-agents" / "lookahead-auditor.toml"),
    }}
    server = staged.mcp_servers["market-data"]
    assert server["approval_mode"] == "approve"
    assert server["env_vars"] == ["MARKET_TOKEN"]
    assert server["env"] == {"REGION": "eu", HARNESS_ROOT_VARIABLE: str(harness.path)}
    assert "`$backtesting`" in staged.guidance and 'spawn the agent role "lookahead-auditor"' in staged.guidance

    # Claude keeps the reference for the host to expand.
    claude = stage(harness, "implementation", "claude_code", tmp_path, session="sessions/other", session_id="other")
    assert claude.mcp_servers["market-data"]["env"]["MARKET_TOKEN"] == "${MARKET_TOKEN}"
    assert "env_vars" not in claude.mcp_servers["market-data"]


def test_ideation_gets_its_own_lists_and_nothing_more(harness, tmp_path):
    staged = stage(harness, "ideation", "claude_code", tmp_path)
    assert tree(staged.session_dir) == [
        ".claude/harness-hooks.json",
        ".claude/skills/market-structure/SKILL.md",
        ".claude/skills/strategy-families/SKILL.md",
    ]
    assert staged.mcp_servers == {} and staged.allowed_tools == []
    assert "agents_path" not in staged.agent_specific
    assert "### Delegates" not in staged.guidance and "### Tool servers" not in staged.guidance
    assert (harness.path / "instructions" / "ideation.md").read_text().strip() in staged.guidance


def test_a_module_without_an_entry_still_gets_its_pages(harness, tmp_path):
    staged = stage(harness, "learning", "codex", tmp_path)
    assert tree(staged.session_dir) == []
    assert (harness.path / "instructions" / "guardrails.md").read_text().strip() in staged.guidance
    assert (harness.path / "instructions" / "learning.md").read_text().strip() in staged.guidance
    assert staged.agent_specific == {"stream_artifact_path": str(tmp_path / "campaign" / ".kapso" / "sessions" / "generic_exp_0" / "stream.jsonl")}


def test_no_harness_stages_nothing(tmp_path):
    staged = stage_harness(None, "implementation", session_dir=tmp_path, campaign_dir=tmp_path, session_id="x", host="codex")
    assert staged.guidance == "" and staged.agent_specific == {} and staged.mcp_servers == {}
    assert tree(tmp_path) == []
    # Without a harness a session keeps exactly the keys it had.
    assert staged.merged_agent_specific({"timeout": 5}) == {"timeout": 5}


def test_the_statement_and_prepared_resources_reach_a_session_directory(harness, tmp_path):
    staged = stage(harness, "implementation", "claude_code", tmp_path, statement=True, prepared=True)
    session_dir = staged.session_dir
    assert (session_dir / "kapso_task.md").read_text() == "# Task\n\nRaise the Sharpe.\n"
    assert (session_dir / "prepared").is_symlink()
    assert (session_dir / "prepared" / "market-data" / "MANIFEST.json").is_file()
    assert "- Prepared resources: prepared/market-data" in staged.guidance
    assert staged.record["prepared"] == ["market-data"]

    # At the campaign root nothing is copied or linked, and the statement
    # path is the campaign's own.
    campaign = tmp_path / "campaign"
    at_root = stage_harness(harness, "feedback", session_dir=campaign, campaign_dir=campaign, session_id="feedback/x", host="claude_code")
    assert not (campaign / "prepared").is_symlink()
    assert f"- Task statement: {campaign / 'kapso_task.md'}" in at_root.guidance


def test_merged_agent_specific_keeps_the_sessions_own_keys(harness, tmp_path):
    staged = stage(harness, "implementation", "claude_code", tmp_path)
    merged = staged.merged_agent_specific({
        "stream_artifact_path": "/own/stream.jsonl",
        "env_overrides": {"LANE": "1"},
        "mcp_servers": {"gated-knowledge": {"command": "python"}},
        "timeout": 60,
    })
    assert merged["stream_artifact_path"] == "/own/stream.jsonl" and merged["timeout"] == 60
    assert merged["env_overrides"] == {HARNESS_ROOT_VARIABLE: str(harness.path), "LANE": "1"}
    assert set(merged["mcp_servers"]) == {"gated-knowledge", "market-data"}
    assert merged["settings_path"] == staged.agent_specific["settings_path"]


def test_staging_is_idempotent_and_two_hosts_share_a_directory(harness, tmp_path):
    first = stage(harness, "implementation", "claude_code", tmp_path)
    again = stage(harness, "implementation", "claude_code", tmp_path)
    assert tree(first.session_dir) == tree(again.session_dir) and first.record == again.record
    codex = stage(harness, "implementation", "codex", tmp_path)
    listing = tree(codex.session_dir)
    assert ".claude/harness-hooks.json" in listing and ".codex/hooks.json" in listing
    assert ".claude/skills/backtesting/SKILL.md" in listing and ".agents/skills/backtesting/SKILL.md" in listing


def test_a_tracked_collision_is_refused_by_name(harness, tmp_path):
    campaign = campaign_with(tmp_path)
    session_dir = campaign / "sessions" / "generic_exp_0"
    git_workspace(session_dir)
    own = session_dir / ".claude" / "skills" / "backtesting" / "SKILL.md"
    own.parent.mkdir(parents=True)
    own.write_text("---\nname: backtesting\ndescription: mine\n---\n")
    git(session_dir, "add", ".claude")
    git(session_dir, "commit", "-q", "-m", "my own skill")
    with pytest.raises(HarnessError) as caught:
        stage_harness(harness, "implementation", session_dir=session_dir, campaign_dir=campaign, session_id="generic_exp_0", host="claude_code")
    assert "tracks .claude/skills/backtesting" in str(caught.value)
    assert not (session_dir / ".claude" / "harness-hooks.json").exists()
    assert own.read_text().endswith("description: mine\n---\n")


def test_a_harness_changed_since_the_load_is_refused(harness, tmp_path):
    page = harness.path / "instructions" / "guardrails.md"
    page.write_text(page.read_text() + "\n- one more rule\n")
    with pytest.raises(HarnessError, match="the harness changed since launch"):
        stage(harness, "implementation", "claude_code", tmp_path)


def test_the_adapters_carry_the_staged_keys(harness, tmp_path, monkeypatch):
    # The adapters look for their CLIs at construction; the test machine
    # need not have either, this test is about the commands they build.
    monkeypatch.setattr(shutil, "which", lambda name: f"/usr/bin/{name}")
    claude = stage(harness, "implementation", "claude_code", tmp_path)
    command = ClaudeCodeCodingAgent(CodingAgentConfig(
        agent_type="claude_code", model="m", debug_model="m",
        agent_specific=claude.merged_agent_specific({"allowed_tools": ["Read", *claude.allowed_tools]}),
    ))._build_command("m")
    assert command[command.index("--settings") + 1] == claude.agent_specific["settings_path"]
    assert command[command.index("--agents") + 1] == claude.agent_specific["agents_path"]
    assert "mcp__market-data" in command[command.index("--allowedTools") + 1]

    codex = stage(harness, "implementation", "codex", tmp_path, session="sessions/codex", session_id="codex")
    command = CodexCodingAgent(CodingAgentConfig(
        agent_type="codex", model="m", debug_model="m",
        agent_specific=codex.merged_agent_specific({"add_dirs": ["/campaign/.kapso/verification/x"]}),
    ))._exec_command("m", "/tmp/last.txt")
    assert "--dangerously-bypass-hook-trust" in command
    assert command[command.index("--add-dir") + 1] == "/campaign/.kapso/verification/x"
    joined = " ".join(command)
    assert 'mcp_servers.market-data.default_tools_approval_mode="approve"' in joined
    assert f'mcp_servers.market-data.cwd="{codex.session_dir}"' in joined
    assert 'agents.lookahead-auditor.description="Audits one attempt' in joined
    assert f'agents.lookahead-auditor.config_file="{codex.session_dir / ".codex" / "harness-agents" / "lookahead-auditor.toml"}"' in joined


def test_staging_another_module_into_the_same_directory_leaves_only_its_attachments(harness, tmp_path):
    """Sessions at the campaign root follow one another (setup, the judge,
    a maintainer session): each sees exactly its module's skills, hooks
    and delegates, nothing inherited from the one before."""
    first = stage(harness, "setup", "claude_code", tmp_path, session="", session_id="harness_setup")
    root = first.session_dir
    assert (root / ".claude" / "skills" / "market-data").is_dir()
    assert json.loads((root / ".claude" / "harness-hooks.json").read_text())["hooks"].keys() >= {"SessionStart", "PreToolUse"}

    second = stage(harness, "feedback", "claude_code", tmp_path, session="", session_id="feedback/generic_exp_0")
    assert sorted(p.name for p in (root / ".claude" / "skills").iterdir()) == ["risk-limits"]
    assert json.loads((root / ".claude" / "harness-agents.json").read_text()).keys() == {"risk-reviewer"}
    assert second.record["skills"] == ["risk-limits"] and second.record["hooks"] == ["session-brief", "deny-web-fetch", "protect-prepared"]

    third = stage(harness, "learning", "claude_code", tmp_path, session="", session_id="learning")
    assert not (root / ".claude" / "harness-hooks.json").exists()
    assert not (root / ".claude" / "harness-agents.json").exists()
    assert list((root / ".claude" / "skills").iterdir()) == []
    assert third.record["skills"] == [] and third.record["hooks"] == [] and third.record["agents"] == []


def test_the_record_names_the_stream_a_session_writes(harness, tmp_path):
    staged = stage(harness, "ideation", "claude_code", tmp_path, session=".kapso/ideation/iter1", session_id="ideation/iter1/claude_code")
    record_path = staged.record_path
    assert record_path == tmp_path / "campaign" / ".kapso" / "sessions" / "ideation" / "iter1" / "claude_code" / "harness.json"
    assert json.loads(record_path.read_text())["stream"] == staged.agent_specific["stream_artifact_path"]
    # An ideation session streams beside its artifacts; the record follows it.
    elsewhere = str(tmp_path / "campaign" / ".kapso" / "ideation" / "iter1" / "claude_code_opus.stream.txt")
    merged = staged.merged_agent_specific({"stream_artifact_path": elsewhere})
    assert merged["stream_artifact_path"] == elsewhere
    assert json.loads(record_path.read_text())["stream"] == elsewhere


def test_the_ignore_writer_matches_whole_lines(tmp_path):
    """A seed whose ignore file mentions `.claude/` in a comment or ignores
    `data/prepared/` has not ignored the staged files; the writer adds the
    lines a session's closing add-all must not sweep up."""
    workspace = tmp_path / "ws"
    workspace.mkdir()
    (workspace / ".gitignore").write_text("# prepared resources live under data/prepared/\n.claude/settings.local.json\n")
    commits = []
    fake = SimpleNamespace(
        workspace_dir=str(workspace),
        repo=SimpleNamespace(git=SimpleNamespace(add=lambda paths: None, commit=lambda *args, **kwargs: commits.append(args))),
    )
    ExperimentWorkspace._ensure_workspace_gitignore(fake)
    lines = [line.strip() for line in (workspace / ".gitignore").read_text().splitlines()]
    assert "prepared" in lines and ".claude/" in lines and ".agents/" in lines and ".codex/" in lines and "kapso_task.md" in lines
    # Written once: a second pass adds nothing.
    before = (workspace / ".gitignore").read_text()
    ExperimentWorkspace._ensure_workspace_gitignore(fake)
    assert (workspace / ".gitignore").read_text() == before and len(commits) == 1
