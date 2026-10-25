# The MCP server for a HOST session — the engineer's own Claude Code or
# Codex session — as opposed to the sessions Kapso spawns inside a campaign.
#
# A campaign session gets its gate configuration built per session by
# get_mcp_config(): the interpreter running Kapso, the campaign's paths, the
# loaded experience. A host's MCP file is static and read at session start,
# so it can name none of these. This entry point is what it names instead:
# a console script (`kapso-mcp`, on the interpreter Kapso is installed in)
# that derives the same configuration from where the session runs and from
# what `--experience` loads, stages the serving for the session, and serves
# the bundled gates on stdio.
#
#   claude mcp add kapso -- kapso-mcp --experience mine
#   codex mcp add kapso -- kapso-mcp --experience mine,org-x
#
# What rides by what the directory holds: web research (the codex CLI), the
# repository's own memory when a campaign has built one, the experiment
# history when the session runs inside a campaign directory. What rides by
# what is loaded (docs/plans/redesign/wp3-experience.md): the bank gate over
# every loaded bank, the search gates over a loaded index. Each gate left
# out is named on stderr with the reason; stdout is the MCP transport.

import argparse
import asyncio
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from kapso.core.config import PLATFORM_CONFIG_PATH, load_experience_defaults, load_mode_config
from kapso.execution.memories.repo_memory import RepoMemoryManager
from kapso.experience.reference import parse_experience_reference
from kapso.experience.sources import ExperienceSource, resolve_source
from kapso.gated_mcp.presets import GATES
from kapso.gated_mcp.server import run_server
from kapso.learning.serving_launch import plan_serving, stage_serving, task_coordinates

# The gates a host session gets without being asked. `idea` and `code`
# join when an index is loaded; `kg` carries the write tools and `inbox` is
# campaign-only, so neither is ever a host default.
DEFAULT_GATES = ("research", "repo_memory", "experiment_history", "bank")
INDEX_GATES = ("idea", "code")
EXPERIMENT_HISTORY_NAME = "experiment_history.json"
LOAD_HINT = "kapso-mcp --experience"


@dataclass
class HostGates:
    """What a host session is served: the gates, the environment the
    bundled server reads them from, and one line per gate left out."""

    enabled: List[str]
    env: Dict[str, str]
    notes: List[str] = field(default_factory=list)


def repository_root(start: Path) -> Path:
    """The git top level `start` is inside, else `start` itself."""
    probe = subprocess.run(
        ["git", "-C", str(start), "rev-parse", "--show-toplevel"],
        capture_output=True, text=True,
    )
    if probe.returncode != 0:
        return start
    return Path(probe.stdout.strip()).resolve()


def campaign_directory(start: Path) -> Optional[Path]:
    """The nearest ancestor of `start` (itself included) that holds a
    campaign's experiment history, else None."""
    for candidate in (start, *start.parents):
        if (candidate / ".kapso" / EXPERIMENT_HISTORY_NAME).is_file():
            return candidate
    return None


def load_sources(text: Optional[str], settings: Dict[str, Any]) -> List[ExperienceSource]:
    """The sources `--experience` names, comma-separated, each resolved
    as `build` resolves them: a bad reference or a missing source stops
    the server with the line that would make it."""
    sources: List[ExperienceSource] = []
    for raw in [part.strip() for part in (text or "").split(",") if part.strip()]:
        reference = parse_experience_reference(raw, indexes_root=Path(settings["indexes"]))
        sources.append(resolve_source(reference, settings=settings))
    return sources


def prepare_host_gates(
    *,
    root: Path,
    requested: Sequence[str],
    mode_config: Dict[str, Any],
    sources: Sequence[ExperienceSource],
    session_dir: Path,
    probe_budget: int,
) -> HostGates:
    """Decide which of the requested gates this session can have, and
    build the environment the bundled server resolves them from. The
    loaded banks are staged into `session_dir` here (one pinned clone
    each, the serving record, the pull log) when the bank gate is among
    the requested; a host session has no harness, so its coordinate is
    `none`. Request order is kept, duplicates dropped; an unknown gate or
    a campaign-only one is a configuration error, never silently skipped."""
    plan = plan_serving(list(sources), task_coordinates(None), session_dir, probe_budget)
    env: Dict[str, str] = {}
    enabled: List[str] = []
    notes: List[str] = []
    seen = set()
    for gate in requested:
        if gate in seen:
            continue
        seen.add(gate)
        if gate not in GATES:
            raise ValueError(
                f"unknown gate {gate!r}; the gates are {sorted(GATES)}"
            )
        if gate == "inbox":
            raise ValueError(
                "the inbox gate is campaign-only: a host session is the "
                "person, it does not ask one"
            )
        if gate == "research":
            if shutil.which("codex") is None:
                notes.append("research: off (the codex CLI is not on PATH)")
                continue
        elif gate == "repo_memory":
            repo_root = repository_root(root)
            if not (repo_root / RepoMemoryManager.MEMORY_REL_PATH).is_file():
                notes.append(
                    f"repo_memory: off (no {RepoMemoryManager.MEMORY_REL_PATH} "
                    f"under {repo_root}; a campaign builds one)"
                )
                continue
            env["REPO_MEMORY_ROOT"] = str(repo_root)
        elif gate == "experiment_history":
            campaign = campaign_directory(root)
            if campaign is None:
                notes.append(
                    "experiment_history: off (not inside a campaign directory)"
                )
                continue
            env["EXPERIMENT_HISTORY_PATH"] = str(
                campaign / ".kapso" / EXPERIMENT_HISTORY_NAME
            )
            embedding = (mode_config.get("models") or {}).get("embedding")
            if embedding:
                env["EXPERIMENT_EMBEDDING_MODEL"] = str(embedding)
        elif gate == "bank":
            if plan is None or not plan["banks"]:
                notes.append(f"bank: off (no bank loaded; {LOAD_HINT} mine)")
                continue
            env.update(stage_serving(plan, list(sources))["bank_serving"])
        elif gate in INDEX_GATES or gate == "kg":
            if plan is None or not plan["kg_index_path"]:
                notes.append(f"{gate}: off (no index loaded; {LOAD_HINT} <name>)")
                continue
            env["KG_INDEX_PATH"] = plan["kg_index_path"]
        enabled.append(gate)
    if plan is not None and plan["hosted"]:
        notes.append(
            "leeroopedia: a hosted server, not a bundled gate — add it to the "
            "host as an HTTP MCP server with your key on the URL"
        )
    return HostGates(enabled=enabled, env=env, notes=notes)


def _parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="kapso-mcp",
        description=(
            "Serve Kapso's knowledge and experience tools to the coding-agent "
            "session this runs in (stdio MCP). Add it to a host with "
            "`claude mcp add kapso -- kapso-mcp --experience mine` or "
            "`codex mcp add kapso -- kapso-mcp --experience mine`."
        ),
    )
    parser.add_argument(
        "--config", type=str, default=None,
        help="Config path (default: packaged config.yaml)",
    )
    parser.add_argument(
        "--root", type=str, default=None,
        help="The directory the session works in (default: the current directory)",
    )
    parser.add_argument(
        "--experience", type=str, default=None,
        help=(
            "Comma-separated sources to serve: mine, a bank path or git reference, "
            "an index name (see `kapso experience list`). Nothing loaded serves "
            "no bank and no index"
        ),
    )
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> None:
    args = _parse_args(argv)
    config_path = args.config or str(PLATFORM_CONFIG_PATH)
    settings = load_experience_defaults(config_path)
    mode_config = load_mode_config(config_path)
    root = Path(args.root).expanduser().resolve() if args.root else Path.cwd()
    sources = load_sources(args.experience, settings)
    requested = list(DEFAULT_GATES)
    if any(source.kind == "index" for source in sources):
        requested.extend(INDEX_GATES)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    session_dir = Path(settings["session_root"]).expanduser() / f"{stamp}-{os.getpid()}"
    gates = prepare_host_gates(
        root=root,
        requested=requested,
        mode_config=mode_config,
        sources=sources,
        session_dir=session_dir,
        probe_budget=settings["probe_budget"],
    )
    for note in gates.notes:
        print(f"kapso-mcp: {note}", file=sys.stderr)
    if not gates.enabled:
        print(
            "kapso-mcp: nothing to serve here — every requested gate is off "
            "for the reasons above",
            file=sys.stderr,
        )
        sys.exit(1)
    print(
        f"kapso-mcp: serving {', '.join(gates.enabled)} for {root}",
        file=sys.stderr,
    )
    # The bundled server reads its configuration from the environment
    # (env is the transport across the process boundary, as for campaign
    # sessions). Availability was decided above, so any miss is a bug.
    os.environ.update(gates.env)
    os.environ["MCP_ENABLED_GATES"] = ",".join(gates.enabled)
    os.environ["MCP_GATE_FAILURE_POLICY"] = "error"
    asyncio.run(run_server())


if __name__ == "__main__":
    main()
