"""Shared pieces of the CLI: the agent list, detached runs and the campaign
summary block. Each verb module imports what it needs from here; nothing
here imports a verb module."""

import json
import os
import subprocess
import sys
import warnings
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Sequence

from kapso.execution.coding_agents.factory import CodingAgentFactory
from kapso.execution.inbox import launch_receipt_path


# Available coding agents
AVAILABLE_AGENTS = [
    name
    for name in CodingAgentFactory.list_available()
    if not CodingAgentFactory.get_agent_info(name).get("inference_only", False)
]


def list_agents() -> None:
    """List available coding agents with detailed info."""
    CodingAgentFactory.print_agents_info()


# =============================================================================
# DETACHED RUNS
# =============================================================================

def _without_detach_flags(argv: Sequence[str]) -> List[str]:
    """This command line without --detach and --log, for the child."""
    kept: List[str] = []
    skip = False
    for word in argv:
        if skip:
            skip = False
        elif word == "--detach" or word.startswith("--log="):
            continue
        elif word == "--log":
            skip = True
        else:
            kept.append(word)
    return kept


def _inside(path: Path, directory: Path) -> bool:
    """Whether `path` lies under `directory` (both resolved)."""
    return path == directory or directory in path.parents


def _default_log(campaign: Path) -> Path:
    """The detached run's log: a sibling of the campaign directory, which
    must stay empty for seeding and holds only the campaign itself."""
    return campaign.with_name(campaign.name + ".log")




def _detach(label: str, argv: Sequence[str], *, log_path: Path, campaign: Path) -> None:
    """Run this very command again in a session of its own, its output in
    a log file, and return at once with what the person needs to follow
    it. A session of its own (`start_new_session`) is what outlives the
    shell call that launched it: a coding agent's tool call ends a plain
    background child when it returns, and the campaign with it (Codex,
    verified 2026-09-07); every host and the skill used to reinvent the
    nohup/setsid dance for this one flag."""
    log_path.parent.mkdir(parents=True, exist_ok=True)
    # The receipt lies beside the campaign: its directory exists before the
    # child does, so a launch under a parent not yet made still gets one.
    launch_receipt_path(campaign).parent.mkdir(parents=True, exist_ok=True)
    # The child is meant to outlive this process, so the Popen object is let
    # go while it runs; Python would otherwise print "subprocess N is still
    # running" at the end of a successful launch.
    with warnings.catch_warnings(), open(log_path, "a", encoding="utf-8") as log:
        warnings.simplefilter("ignore", ResourceWarning)
        child = subprocess.Popen(
            [sys.executable, "-m", "kapso.cli", *argv],
            stdin=subprocess.DEVNULL,
            stdout=log,
            stderr=subprocess.STDOUT,
            cwd=os.getcwd(),
            start_new_session=True,
        )
        pid = child.pid
        del child
    launch_receipt_path(campaign).write_text(json.dumps({
        "pid": pid,
        "log": str(log_path),
        "argv": list(argv),
        "started_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }, indent=2) + "\n", encoding="utf-8")
    print(f"{label} started in a session of its own (pid {pid})")
    print(f"  log:     {log_path}")
    print(f"  status:  {campaign / '.kapso' / 'status.json'}")
    print(f"  follow:  kapso watch {campaign} --follow")
    print(f"  inbox:   kapso inbox {campaign}")


def _print_build_summary(solution) -> None:
    """The block after a campaign: COMPLETED, or WAITING ON YOU when it
    paused for a reply in the inbox (design v4 §4.6), each over the
    solution's own summary. A pause is not a failure: the exit code stays 0."""
    print("\n" + "=" * 60)
    campaign = str(solution.campaign)
    if solution.stopped_reason == "waiting_for_user":
        requests = solution.requests
        target = f" {requests[0]['id']}" if len(requests) > 1 else ""
        print("WAITING ON YOU")
        print("=" * 60)
        print(solution.explain())
        print(f'Reply with:  kapso inbox reply{target} "…"   (inside {campaign})')
        print(f"Any time:    kapso inbox {campaign}")
        return
    print("COMPLETED")
    print("=" * 60)
    print(solution.explain())
