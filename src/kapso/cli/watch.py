"""`kapso watch`: one watch command for build / learn / experience
status files (observability design §3). Pure reader — never writes."""

import argparse
import json
import sys
import time
from pathlib import Path

from kapso.kapso import Kapso
from kapso.execution.observability import OperationStatusView

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
    the line and a wait for the file."""
    if OperationStatusView.locate(args.path) is None:
        expected = Path(args.path).expanduser()
        if expected.is_dir():
            expected = expected / ".kapso" / "status.json"
        print(
            f"no status yet at {expected} — the campaign is still starting "
            "(seeding its workspace), or nothing runs there"
        )
        if not args.follow:
            sys.exit(1)
        while OperationStatusView.locate(args.path) is None:
            time.sleep(_WATCH_FALLBACK_SECONDS)
    view = Kapso.status(args.path)
    show_tree = args.tree
    if args.json:
        print(json.dumps(view.data, indent=1))
        return
    if not args.follow:
        print(view.explain(tree=show_tree))
        return
    # Follow: re-render at the operation's own heartbeat cadence.
    interval = float(view.data.get("heartbeat_seconds") or _WATCH_FALLBACK_SECONDS)
    while True:
        view = Kapso.status(args.path)
        print("\x1b[2J\x1b[H" + view.explain(tree=show_tree), flush=True)
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
  kapso watch ./campaign                 # a workspace (-> .kapso/status.json)
  kapso watch learning/status            # newest status file in a directory
  kapso watch learning/status/learn-20260826T120000.json
  kapso watch ./campaign --follow        # live re-render until terminal
  kapso watch ./campaign --tree          # show the campaign tree
  kapso watch ./campaign --json | jq -r '[.state] | @tsv'
""",
    )
    watch_parser.add_argument(
        "path",
        help="Workspace, status file, or directory of status files",
    )
    output_group = watch_parser.add_mutually_exclusive_group()
    output_group.add_argument(
        "--json", action="store_true", help="Print the status file once, as JSON",
    )
    watch_parser.add_argument(
        "--follow", action="store_true",
        help="Re-render on each heartbeat until the operation ends",
    )
    output_group.add_argument(
        "--tree", action="store_true", help="Show the campaign tree",
    )
    return cmd_watch
