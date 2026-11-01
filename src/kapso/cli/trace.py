"""`kapso trace`: a campaign's record read after the fact, as text or as
JSON (wp6-observability.md, change 11). A pure reader — never writes."""

import argparse
import json
import sys
from pathlib import Path

from kapso.execution.trace import is_campaign
from kapso.kapso import Kapso

NAME = "trace"


def cmd_trace(args) -> None:
    campaign = Path(args.campaign).expanduser()
    if not is_campaign(campaign):
        print(f"Error: {campaign} is not a campaign directory (no .kapso/ inside)", file=sys.stderr)
        sys.exit(1)
    view = Kapso.trace(str(campaign))
    if args.branch:
        branches = [attempt["branch"] for attempt in view.attempts]
        if args.branch not in branches:
            print(
                f"Error: no attempt on branch {args.branch}; the attempts are: {', '.join(branches) or 'none'}",
                file=sys.stderr,
            )
            sys.exit(1)
        view = view.narrow(args.branch)
    if args.json:
        print(json.dumps(view.data, indent=1))
    else:
        print(view.explain())


def add_parser(subparsers):
    parser = subparsers.add_parser(
        "trace",
        help="Read a campaign's record: the attempts, the lessons, what was voided, what was delivered",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        allow_abbrev=False,
        description=(
            "The campaign's record laid out section by section: the header, every attempt with its "
            "sessions and runs (the hooks that fired, the delegates asked, the gates called, what each "
            "cost), the lessons served and which an attempt used, what was voided or rejected and on what "
            "evidence, the sessions that failed, the delivered candidate. A campaign still running renders "
            "partial; `kapso watch` follows it live."
        ),
        epilog="""
Examples:
  kapso trace ../campaign                          # every section, the attempts compact
  kapso trace ../campaign --branch generic_exp_1   # one attempt with its evidence in full
  kapso trace ../campaign --json                   # the same as data, for a script or a skill
""",
    )
    parser.add_argument("campaign", type=str, help="The campaign directory a build wrote")
    parser.add_argument("--branch", type=str, default=None, help="Narrow the attempts to this branch, shown in full")
    parser.add_argument("--json", action="store_true", help="Print the trace as JSON")
    return cmd_trace
