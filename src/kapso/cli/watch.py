"""`kapso watch`: one watch command for build / learn / experience
status files (observability design §3). Pure reader — never writes."""

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from kapso.kapso import DEFAULT_CONFIG_PATH, Kapso
from kapso.core.config import load_config, load_mode_config
from kapso.execution.inbox import read_launch_receipt
from kapso.execution.observability import OperationStatusView, campaign_listing, pid_alive, render_listing

NAME = "watch"

# The display cadence when a status file records no heartbeat, and the
# poll cadence while waiting for one to appear — structural, not a knob.
_WATCH_FALLBACK_SECONDS = 5


def cmd_watch(args) -> None:
    """One watch command for build / learn / experience status files
    (observability design §3). Pure reader — never writes.

    A campaign that has not written its status yet (the seconds between
    `kapso build` starting and the workspace being seeded) is one line,
    not a traceback: without --follow the line and exit 1, with --follow
    the line and a wait for the file. With no path, the campaigns the
    registry knows that are alive or waiting, and the learns and ingests
    under the status directory (`--all` for every one with its state)."""
    if args.path is None:
        if args.follow:
            print("kapso watch --follow needs a campaign to follow: kapso watch <campaign> --follow", file=sys.stderr)
            sys.exit(1)
        config_path = args.config or DEFAULT_CONFIG_PATH
        entries = campaign_listing(
            load_mode_config(config_path)["inbox"]["registry"],
            load_config(config_path)["learning"]["status_dir"],
            everything=args.all,
        )
        if args.json:
            print(json.dumps(entries, indent=1))
        elif entries:
            print(render_listing(entries))
        else:
            print("nothing running or waiting" + ("" if args.all else "; kapso watch --all lists every campaign the registry knows"))
        return
    if OperationStatusView.locate(args.path) is None:
        campaign = Path(args.path).expanduser()
        expected = campaign / ".kapso" / "status.json" if campaign.is_dir() else campaign
        # A detached launch left a receipt beside the log: the child's pid
        # tells a campaign still starting from one that died before its
        # status, and the log says why (wp6-observability.md, change 7).
        receipt = read_launch_receipt(campaign) if campaign.is_dir() else None
        if receipt is None:
            print(
                f"no status yet at {expected} — the campaign is still starting "
                "(seeding its workspace), or nothing runs there"
            )
        elif pid_alive(receipt["pid"]) is False:
            print(f"stopped before writing a status; the log says why: {receipt['log']}")
            sys.exit(1)
        else:
            launched = datetime.fromisoformat(receipt["started_at"])
            age = (datetime.now(timezone.utc) - launched).total_seconds()
            print(f"starting (pid {receipt['pid']}, launched {age:.0f}s ago; log: {receipt['log']})")
        if not args.follow:
            sys.exit(1)
        while OperationStatusView.locate(args.path) is None:
            time.sleep(_WATCH_FALLBACK_SECONDS)
    view = Kapso.status(args.path)
    if args.json:
        print(json.dumps(view.data, indent=1))
        return
    if not args.follow:
        print(view.explain())
        return
    # Follow: re-render at the operation's own heartbeat cadence.
    interval = float(view.data.get("heartbeat_seconds") or _WATCH_FALLBACK_SECONDS)
    while True:
        view = Kapso.status(args.path)
        print("\x1b[2J\x1b[H" + view.explain(), flush=True)
        if view.state in ("done", "failed"):
            return
        time.sleep(interval)


def add_parser(subparsers):
    watch_parser = subparsers.add_parser(
        "watch",
        help="Watch a running build / learn / experience operation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  kapso watch                            # every campaign alive or waiting, every learn or ingest running
  kapso watch --all                      # every campaign the registry knows, with its state
  kapso watch ./campaign                 # a workspace (-> .kapso/status.json)
  kapso watch learning/status            # newest status file in a directory
  kapso watch learning/status/learn-20260826T120000.json
  kapso watch ./campaign --follow        # live re-render until terminal
  kapso watch ./campaign --json | jq -r '[.state] | @tsv'
  kapso trace ./campaign                 # the attempts and the record, after the fact
""",
    )
    watch_parser.add_argument(
        "path", nargs="?", default=None,
        help="Workspace, status file, or directory of status files; none lists the campaigns alive or waiting",
    )
    output_group = watch_parser.add_mutually_exclusive_group()
    output_group.add_argument(
        "--json", action="store_true", help="Print the status file once, as JSON (with no path, the listing)",
    )
    watch_parser.add_argument(
        "--follow", action="store_true",
        help="Re-render on each heartbeat until the operation ends",
    )
    watch_parser.add_argument(
        "--all", action="store_true",
        help="With no path: every campaign the registry knows and every status file, with its state",
    )
    watch_parser.add_argument(
        "--config", type=str, default=None,
        help="Config whose inbox.registry and learning.status_dir the listing reads (default: packaged config.yaml)",
    )
    return cmd_watch
