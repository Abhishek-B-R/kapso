# The MCP server for a HOST session — the engineer's own Claude Code or
# Codex session — as opposed to the sessions Kapso spawns inside a campaign.
#
# A campaign session gets its gate configuration built per session by
# get_mcp_config(): the interpreter running Kapso, the campaign's paths, the
# pinned bank. A host's MCP file is static and read at session start, so it
# can name neither. This entry point is what it names instead: a console
# script (`kapso-mcp`, on the interpreter Kapso is installed in) that derives
# the same configuration from where the session runs and from the config,
# stages bank serving for the session, and serves the bundled gates on stdio.
#
#   claude mcp add kapso -- kapso-mcp
#   codex mcp add kapso -- kapso-mcp
#
# What rides by default: web research (the codex CLI), the repository's own
# memory when a campaign has built one, the experiment history when the
# session runs inside a campaign directory, and the lesson bank when serving
# is on. Knowledge-graph search joins with --kg-index. Each gate left out is
# named on stderr with the reason; stdout is the MCP transport.

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

from kapso.core.config import PLATFORM_CONFIG_PATH, load_config, load_mode_config
from kapso.execution.memories.repo_memory import RepoMemoryManager
from kapso.gated_mcp.presets import GATES
from kapso.gated_mcp.server import run_server
from kapso.learning.serving_launch import plan_serving, stage_serving

# The gates a host session gets without being asked. `idea` and `code`
# join when an index is named; `kg` carries the write tools and `inbox` is
# campaign-only, so neither is ever a host default.
DEFAULT_GATES = ("research", "repo_memory", "experiment_history", "bank")
INDEX_GATES = ("idea", "code")
EXPERIMENT_HISTORY_NAME = "experiment_history.json"


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


def prepare_host_gates(
    *,
    root: Path,
    requested: Sequence[str],
    config: Dict[str, Any],
    mode_config: Dict[str, Any],
    kg_index: Optional[str],
    family: str,
    session_dir: Path,
) -> HostGates:
    """Decide which of the requested gates this session can have, and
    build the environment the bundled server resolves them from. Bank
    serving is staged into `session_dir` here (a pinned clone, the
    serving record, the pull log). Request order is kept, duplicates
    dropped; an unknown gate or a campaign-only one is a configuration
    error, never silently skipped."""
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
            learning = config["learning"]
            if not learning["serving"]["enabled"]:
                notes.append(
                    "bank: off (learning.serving.enabled is false in the config)"
                )
                continue
            home = Path(learning["bank"]["local_path"]).expanduser()
            if not home.exists():
                notes.append(
                    f"bank: off (no bank home at {home}; a learn() creates one)"
                )
                continue
            plan = plan_serving(config, {"family": family}, session_dir)
            staged = stage_serving(config, {"family": family}, plan)
            env.update(staged["bank_serving"])
        elif gate in INDEX_GATES or gate == "kg":
            if not kg_index:
                notes.append(f"{gate}: off (no --kg-index)")
                continue
            env["KG_INDEX_PATH"] = str(Path(kg_index).expanduser().resolve())
        enabled.append(gate)
    return HostGates(enabled=enabled, env=env, notes=notes)


def _parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="kapso-mcp",
        description=(
            "Serve Kapso's knowledge and experience tools to the coding-agent "
            "session this runs in (stdio MCP). Add it to a host with "
            "`claude mcp add kapso -- kapso-mcp` or "
            "`codex mcp add kapso -- kapso-mcp`."
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
        "--gates", type=str, default=",".join(DEFAULT_GATES),
        help=f"Comma-separated gates to serve (default: {','.join(DEFAULT_GATES)})",
    )
    parser.add_argument(
        "--kg-index", type=str, default=None,
        help="A .index file; adds the idea and code search gates",
    )
    parser.add_argument(
        "--family", type=str, default=None,
        help="The task family the bank serves for (default: the config's default_mode, lowercased)",
    )
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> None:
    args = _parse_args(argv)
    config_path = args.config or str(PLATFORM_CONFIG_PATH)
    config = load_config(config_path)
    # A user config without a learning block inherits the packaged one,
    # as the facade does (Rule 1: one canonical home for the defaults).
    if "learning" not in config:
        config["learning"] = load_config(str(PLATFORM_CONFIG_PATH))["learning"]
    mode_config = load_mode_config(config_path)
    root = Path(args.root).expanduser().resolve() if args.root else Path.cwd()
    requested = [gate.strip() for gate in args.gates.split(",") if gate.strip()]
    if args.kg_index:
        requested.extend(INDEX_GATES)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    session_dir = (
        Path(config["learning"]["serving"]["session_root"]).expanduser()
        / f"{stamp}-{os.getpid()}"
    )
    gates = prepare_host_gates(
        root=root,
        requested=requested,
        config=config,
        mode_config=mode_config,
        kg_index=args.kg_index,
        family=args.family or str(config.get("default_mode", "GENERIC")).lower(),
        session_dir=session_dir,
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
