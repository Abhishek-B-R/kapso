"""Staging a harness into one session: the module's pages as the "Domain
guidance" block, its skills where the host discovers them, its servers
beside the engine's gates, its delegates as the host's sub-agents carrying
the same guidance, its hooks merged into the file the host reads, the
environment, the prepared resources and the task statement, and a record
of what was staged. One function, called at every site that constructs a
coding-agent session. Design: docs/research/harness-design.md sections 3
and 5; the plan: docs/plans/redesign/wp2-harness.md ("Staging").

Idempotent (a second call on the same directory and host replaces what it
wrote) and safe under concurrency (each host's files have fixed names and
are written whole). Refused before anything is written when the session
directory already tracks a path it would write, and when the harness
changed since it was loaded.
"""

import json
import os
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import git

from kapso.harness.check import read_front_matter
from kapso.harness.hash import harness_hash
from kapso.harness.hooks import expand_plugin_root, merge_hooks
from kapso.harness.load import Harness, HarnessError
from kapso.harness.manifest import MODULES

HARNESS_ROOT_VARIABLE = "KAPSO_HARNESS_ROOT"
TASK_STATEMENT_FILE = "kapso_task.md"
PREPARED_DIR = "prepared"
CLAUDE_HOST = "claude_code"
CODEX_HOST = "codex"
HOST_OF_AGENT = {
    "claude_code": CLAUDE_HOST,
    "oss_claude_code": CLAUDE_HOST,
    "vertex_claude_code": CLAUDE_HOST,
    "codex": CODEX_HOST,
}
_SKILLS_DIR = {CLAUDE_HOST: Path(".claude") / "skills", CODEX_HOST: Path(".agents") / "skills"}
_HOOKS_FILE = {CLAUDE_HOST: Path(".claude") / "harness-hooks.json", CODEX_HOST: Path(".codex") / "hooks.json"}
_AGENTS_PATH = {CLAUDE_HOST: Path(".claude") / "harness-agents.json", CODEX_HOST: Path(".codex") / "harness-agents"}
_OPEN_SKILL = {CLAUDE_HOST: "/{name}", CODEX_HOST: "${name}"}
_ASK_AGENT = {
    CLAUDE_HOST: 'the Agent tool with subagent_type "{name}"',
    CODEX_HOST: 'spawn the agent role "{name}" and wait for its reply',
}
GUIDANCE_HEADING = "## Domain guidance"


def host_for(agent_type: str) -> str:
    if agent_type not in HOST_OF_AGENT:
        raise HarnessError(
            f"a harness stages into {', '.join(sorted(set(HOST_OF_AGENT.values())))} sessions; "
            f"coding agent {agent_type!r} has no staging"
        )
    return HOST_OF_AGENT[agent_type]


@dataclass
class StagedHarness:
    module: str
    host: str
    session_dir: Path
    session_id: str
    guidance: str                                   # "" without a harness
    agent_specific: Dict[str, Any] = field(default_factory=dict)   # keys for CodingAgentConfig.agent_specific
    mcp_servers: Dict[str, Any] = field(default_factory=dict)      # the harness servers, host-shaped, beside the gates
    allowed_tools: List[str] = field(default_factory=list)         # `mcp__<server>` per mounted server
    env: Dict[str, str] = field(default_factory=dict)              # KAPSO_HARNESS_ROOT
    record: Dict[str, Any] = field(default_factory=dict)

    def merged_agent_specific(self, own: Dict[str, Any]) -> Dict[str, Any]:
        """The session's own keys over the staged ones; `env_overrides` and
        `mcp_servers` are merged, not replaced."""
        merged = {**self.agent_specific, **own}
        merged["env_overrides"] = {**self.env, **(own.get("env_overrides") or {})}
        merged["mcp_servers"] = {**(own.get("mcp_servers") or {}), **self.mcp_servers}
        return merged


def no_harness(module: str, host: str, session_dir: Path, session_id: str) -> StagedHarness:
    """What a session gets without a harness: nothing."""
    return StagedHarness(module=module, host=host, session_dir=Path(session_dir), session_id=session_id, guidance="")


def stage_harness(
    harness: Optional[Harness],
    module: str,
    *,
    session_dir: Path,
    campaign_dir: Path,
    session_id: str,
    host: str,
) -> StagedHarness:
    """Stage one module of the harness into one session directory."""
    session_dir = Path(session_dir)
    campaign_dir = Path(campaign_dir)
    if harness is None:
        return no_harness(module, host, session_dir, session_id)
    if module not in MODULES:
        raise ValueError(f"unknown module {module!r}; the modules are {', '.join(MODULES)}")
    if host not in _SKILLS_DIR:
        raise HarnessError(f"unknown host {host!r}; the hosts are {', '.join(_SKILLS_DIR)}")
    current = harness_hash(harness.path)
    if current != harness.hash:
        raise HarnessError(
            f"the harness changed since launch: {harness.label()} recorded, "
            f"{harness.name} now hashes {current[:12]}; {harness.restore_hint()}"
        )
    stager = _Stager(harness, module, session_dir, campaign_dir, session_id, host)
    stager.refuse_tracked_collisions()
    stager.mount_campaign_files()
    stager.skills()
    stager.servers()
    stager.hooks()
    stager.agents()
    stager.record()
    return stager.staged


class _Stager:
    def __init__(self, harness: Harness, module: str, session_dir: Path, campaign_dir: Path, session_id: str, host: str):
        self.harness = harness
        self.module = module
        self.attachments = harness.module(module)
        self.session_dir = session_dir
        self.campaign_dir = campaign_dir
        self.session_id = session_id
        self.host = host
        self.prepared = self.prepared_names()
        self.staged = StagedHarness(
            module=module, host=host, session_dir=session_dir, session_id=session_id,
            guidance=self.guidance(),
            env={HARNESS_ROOT_VARIABLE: str(harness.path)},
            agent_specific={
                "stream_artifact_path": str(self.session_record_dir() / "stream.jsonl"),
            },
        )

    # ------------------------------------------------------------- paths

    def session_record_dir(self) -> Path:
        return self.campaign_dir / ".kapso" / "sessions" / self.session_id

    def writes(self) -> List[Path]:
        """Every path under the session directory this staging writes."""
        paths = [self.session_dir / _SKILLS_DIR[self.host] / name for name in self.attachments.skills]
        if self.attachments.hooks:
            paths.append(self.session_dir / _HOOKS_FILE[self.host])
        if self.attachments.agents:
            paths.append(self.session_dir / _AGENTS_PATH[self.host])
        if not self.at_campaign_root():
            paths.append(self.session_dir / PREPARED_DIR)
            paths.append(self.session_dir / TASK_STATEMENT_FILE)
        return paths

    def at_campaign_root(self) -> bool:
        return self.session_dir.resolve() == self.campaign_dir.resolve()

    def prepared_names(self) -> Tuple[str, ...]:
        prepared = self.campaign_dir / PREPARED_DIR
        if not prepared.is_dir():
            return ()
        return tuple(sorted(p.name for p in prepared.iterdir() if p.is_dir()))

    # ----------------------------------------------------------- refusals

    def refuse_tracked_collisions(self) -> None:
        """A seed repository that tracks a path the staging would write
        (its own skill of the same name, its own .codex/hooks.json) is
        refused by name: staging never overwrites the person's files and a
        session's closing commit never carries the harness's."""
        if not (self.session_dir / ".git").exists():
            return
        repo = git.Repo(self.session_dir)
        for path in self.writes():
            relative = path.relative_to(self.session_dir).as_posix()
            if repo.git.ls_files(relative).strip():
                raise HarnessError(
                    f"harness {self.harness.name} cannot be staged into {self.session_dir}: the repository "
                    f"tracks {relative}, which the harness would write; move or rename it in the repository"
                )

    # ------------------------------------------------------------ mounting

    def mount_campaign_files(self) -> None:
        """The task statement (copied) and the prepared resources (linked)
        reach every session directory that is not the campaign root."""
        if self.at_campaign_root():
            return
        statement = self.campaign_dir / TASK_STATEMENT_FILE
        if statement.is_file():
            shutil.copy2(statement, self.session_dir / TASK_STATEMENT_FILE)
        prepared = self.campaign_dir / PREPARED_DIR
        link = self.session_dir / PREPARED_DIR
        if prepared.is_dir() and not link.exists() and not link.is_symlink():
            os.symlink(prepared.resolve(), link)

    def skills(self) -> None:
        for name in self.attachments.skills:
            target = self.session_dir / _SKILLS_DIR[self.host] / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copytree(self.harness.path / "skills" / name, target, dirs_exist_ok=True)

    def servers(self) -> None:
        if not self.attachments.mcp_servers:
            return
        defined = json.loads((self.harness.path / "mcp.json").read_text(encoding="utf-8"))["mcpServers"]
        for name in self.attachments.mcp_servers:
            entry = expand_plugin_root(defined[name], self.harness.path)
            if "command" in entry:
                entry.setdefault("cwd", str(self.session_dir))
                env = dict(entry.get("env") or {})
                env[HARNESS_ROOT_VARIABLE] = str(self.harness.path)
                if self.host == CODEX_HOST:
                    # Forwarded by name; the codex adapter writes env_vars.
                    references = [v[2:-1] for v in env.values() if _is_reference(v)]
                    env = {k: v for k, v in env.items() if not _is_reference(v)}
                    if references:
                        entry["env_vars"] = references
                entry["env"] = env
            else:
                entry.setdefault("timeout", _http_timeout_ms(self.harness))
            if self.host == CODEX_HOST:
                entry["approval_mode"] = "approve"
            self.staged.mcp_servers[name] = entry
            self.staged.allowed_tools.append(f"mcp__{name}")

    def hooks(self) -> None:
        if not self.attachments.hooks:
            return
        merged = merge_hooks(self.harness.path, self.attachments.hooks)
        file = self.session_dir / _HOOKS_FILE[self.host]
        _write_whole(file, json.dumps(merged, indent=2) + "\n")
        if self.host == CLAUDE_HOST:
            self.staged.agent_specific["settings_path"] = str(file)
        else:
            self.staged.agent_specific["hooks_trust_bypass"] = True

    def agents(self) -> None:
        if not self.attachments.agents:
            return
        prompts = {}
        for name in self.attachments.agents:
            data, body = read_front_matter(self.harness.path / "agents" / f"{name}.md")
            prompts[name] = (str(data["description"]), self.staged.guidance + "\n\n" + body.strip() + "\n")
        if self.host == CLAUDE_HOST:
            file = self.session_dir / _AGENTS_PATH[self.host]
            _write_whole(file, json.dumps(
                {name: {"description": description, "prompt": prompt} for name, (description, prompt) in prompts.items()},
                indent=2,
            ) + "\n")
            self.staged.agent_specific["agents_path"] = str(file)
        else:
            directory = self.session_dir / _AGENTS_PATH[self.host]
            roles = {}
            for name, (description, prompt) in prompts.items():
                file = directory / f"{name}.toml"
                _write_whole(file, f"developer_instructions = {json.dumps(prompt)}\n")
                roles[name] = {"description": description, "config_file": str(file)}
            self.staged.agent_specific["agents"] = roles

    def record(self) -> None:
        self.staged.record = {
            "module": self.module,
            "host": self.host,
            "harness": self.harness.ref_dict(),
            "session_dir": str(self.session_dir),
            "pages": self.page_names(),
            "skills": list(self.attachments.skills),
            "mcp_servers": list(self.attachments.mcp_servers),
            "agents": list(self.attachments.agents),
            "hooks": list(self.attachments.hooks),
            "prepared": list(self.prepared),
        }
        _write_whole(self.session_record_dir() / "harness.json", json.dumps(self.staged.record, indent=2) + "\n")

    # ------------------------------------------------------------ guidance

    def page_names(self) -> List[str]:
        names = []
        for page in ("guardrails.md", f"{self.module}.md"):
            if (self.harness.path / "instructions" / page).is_file():
                names.append(page)
        return names

    def guidance(self) -> str:
        """The block the module's prompt carries: both pages whole, then the
        attachments by name and description, then the paths."""
        lines = [f"{GUIDANCE_HEADING} (harness {self.harness.name} {self.harness.version})", ""]
        for page in self.page_names():
            lines.append((self.harness.path / "instructions" / page).read_text(encoding="utf-8").rstrip())
            lines.append("")
        if self.attachments.skills:
            lines.append("### Skills (open one when its situation arises)")
            for name in self.attachments.skills:
                data, _ = read_front_matter(self.harness.path / "skills" / name / "SKILL.md")
                lines.append(f"- {name} — {data['description']} (open with `{_OPEN_SKILL[self.host].format(name=name)}`)")
            lines.append("")
        if self.attachments.agents:
            lines.append("### Delegates (ask by name; each reads this guidance and the task statement)")
            for name in self.attachments.agents:
                data, _ = read_front_matter(self.harness.path / "agents" / f"{name}.md")
                lines.append(f"- {name} — {data['description']} (ask through {_ASK_AGENT[self.host].format(name=name)})")
            lines.append("")
        if self.attachments.mcp_servers:
            lines.append("### Tool servers")
            for name in self.attachments.mcp_servers:
                lines.append(f"- {name} — its tools are named mcp__{name}__<tool>")
            lines.append("")
        lines.append("### Paths")
        statement = self.session_dir / TASK_STATEMENT_FILE if not self.at_campaign_root() else self.campaign_dir / TASK_STATEMENT_FILE
        lines.append(f"- Task statement: {statement} (read it before anything else)")
        lines.append(f"- Harness root: ${HARNESS_ROOT_VARIABLE} = {self.harness.path}")
        if self.prepared:
            lines.append("- Prepared resources: " + ", ".join(f"{PREPARED_DIR}/{name}" for name in self.prepared))
        return "\n".join(lines).rstrip() + "\n"


def _http_timeout_ms(harness: Harness) -> int:
    """A streamable-http server's per-call timeout where the host takes one
    (codex), from the config the harness was loaded with."""
    return int(harness.settings["server_tool_timeout_seconds"]) * 1000


def _is_reference(value: Any) -> bool:
    return isinstance(value, str) and value.startswith("${") and value.endswith("}") and len(value) > 3


def _write_whole(file: Path, text: str) -> None:
    """Written to a sibling and renamed into place, so a concurrent reader
    never sees a half file and a second writer of the same content is
    harmless."""
    file.parent.mkdir(parents=True, exist_ok=True)
    temporary = file.with_name(f".{file.name}.{os.getpid()}.tmp")
    temporary.write_text(text, encoding="utf-8")
    os.replace(temporary, file)
