"""`kapso build`: build software that meets a brief, by experiment."""

import argparse
import sys
from pathlib import Path
from typing import List

from kapso.core.config import load_config
from kapso.kapso import Kapso
from kapso.handles import Brief, Budget
from kapso.execution.inbox import read_launch_record
from kapso.experience import recorded_reference
from kapso.harness import BUILD_MODULES, unmet_message
from kapso.cli.common import (
    AVAILABLE_AGENTS,
    _default_log,
    _detach,
    _inside,
    _print_build_summary,
    _without_detach_flags,
)

NAME = "build"


def cmd_build(args) -> None:
    """Handle the build command."""
    if args.brief:
        brief_path = Path(args.brief).expanduser()
        if not brief_path.is_file():
            print(f"Error: brief not found: {brief_path}", file=sys.stderr)
            sys.exit(1)
        brief = Brief.read(brief_path)
    elif args.goal_file:
        brief = Path(args.goal_file).expanduser().read_text(encoding="utf-8")
    elif args.goal:
        brief = args.goal
    elif args.resume:
        brief = None   # a resume takes the brief from the checkpoint
    else:
        print(
            "Error: --goal, --goal-file or --brief is required "
            "(a resume takes the brief from the checkpoint)",
            file=sys.stderr,
        )
        sys.exit(1)

    if args.detach:
        if not args.output:
            print(
                "Error: --detach needs --output: the campaign directory is "
                "where its status file lives and its log goes beside",
                file=sys.stderr,
            )
            sys.exit(1)
        campaign = Path(args.output).expanduser().resolve()
        if args.log and _inside(Path(args.log).expanduser().resolve(), campaign):
            print(
                "Error: --log must be outside --output: the campaign directory "
                "must be empty for seeding, and the log would be in it",
                file=sys.stderr,
            )
            sys.exit(1)
        # The harness is loaded and its prerequisites checked before the
        # fork, so the handoff below never claims a launch that would die
        # on a missing command or variable in the child's log; the
        # experience the same, so a reference that names nothing, or a
        # source that is gone, refuses here with its line. A bare resume
        # takes both from the launch record, as the build will.
        kapso = Kapso(config=args.config)
        record = read_launch_record(campaign) if args.resume else None
        ref = _harness_reference(args, brief)
        if ref is None and record is not None and record.get("harness"):
            ref = record["harness"]["source"]
        if ref is not None:
            _load_harness_or_exit(kapso, args, brief, ref=ref)
        references = _experience_references(args, brief)
        if not references and record is not None:
            references = [recorded_reference(entry) for entry in record.get("experience", [])]
        for reference in references:
            kapso.load_experience(reference)
        _detach(
            "kapso build",
            _without_detach_flags(sys.argv[1:]),
            log_path=(
                Path(args.log).expanduser().resolve() if args.log
                else _default_log(campaign)
            ),
            campaign=campaign,
        )
        return

    kapso = Kapso(config=args.config)
    _load_harness_or_exit(kapso, args, brief)
    for reference in _experience_references(args, brief):
        kapso.load_experience(reference)
    solution = kapso.build(
        brief,
        evaluation=args.evaluation,
        data=args.data,
        repo=args.repo,
        output=args.output,
        budget=Budget(
            minutes=args.budget_minutes,
            experiments=args.budget_experiments,
            usd=args.budget_usd,
            reserve_minutes=args.budget_reserve_minutes,
        ),
        resume=args.resume,
        coding_agent=args.coding_agent,
    )
    _print_build_summary(solution)


def _harness_reference(args, brief):
    """`--harness` wins over the brief's Harness line; a sentence or a
    plain-text goal names none."""
    if args.harness:
        return args.harness
    return brief.harness if isinstance(brief, Brief) else None


def _experience_references(args, brief) -> List[str]:
    """`--experience` (comma-separated) wins over the brief's Experience
    line; a sentence or a plain-text goal names none. A bare resume names
    none here: the build takes the record's list."""
    if args.experience:
        return [item.strip() for item in args.experience.split(",") if item.strip()]
    return list(brief.experience) if isinstance(brief, Brief) else []


def _load_harness_or_exit(kapso, args, brief, ref=None):
    """Load the harness a build names (or the one given) and refuse, before
    anything starts, while a requirement of the build's own modules is
    unmet."""
    ref = ref or _harness_reference(args, brief)
    if ref is None:
        return None
    harness = kapso.load_harness(ref)
    unmet = harness.missing_for(BUILD_MODULES)
    if unmet:
        print(unmet_message(harness, unmet, "build"))
        sys.exit(1)
    return harness


def add_parser(subparsers):
    build_parser = subparsers.add_parser(
        "build",
        help="Build software that meets a brief, by experiment",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        # No abbreviations: a `--det` the child kept would detach again, forever.
        allow_abbrev=False,
        epilog="""
Examples:
  kapso build --brief kapso-brief.md --evaluation ./evaluation --data ./data --repo . --output ../churn-build --detach
  kapso build --goal "Build a web scraper for news articles" --output ./scraper
  kapso build --goal-file problem.txt --budget-experiments 20 --output ./campaign
  kapso build --output ./campaign --resume       # brief and flags from the checkpoint and the launch record
  kapso watch ./campaign --follow                # follow a detached build
"""
    )

    goal_group = build_parser.add_mutually_exclusive_group()
    goal_group.add_argument(
        "-g", "--goal", type=str,
        help="The objective in a sentence (a resume takes the brief from the checkpoint)",
    )
    goal_group.add_argument(
        "-f", "--goal-file", type=str,
        help="A file holding the objective as plain text",
    )
    goal_group.add_argument(
        "--brief", type=str,
        help="A brief file (kapso-brief.md): objective, how it is measured, "
             "baseline, target, rules, budget",
    )

    build_parser.add_argument(
        "--evaluation", type=str,
        help="Directory holding the evaluator (copied to kapso_evaluation/, integrity-protected)",
    )
    build_parser.add_argument(
        "--data", type=str,
        help="Directory holding the data (copied to kapso_datasets/)",
    )
    build_parser.add_argument(
        "--repo", type=str,
        help="Starting repository: a local path (copied) or a GitHub URL (cloned)",
    )
    build_parser.add_argument(
        "-o", "--output", type=str,
        help="The campaign directory (empty for a fresh build): the branches, the record, the solution",
    )

    build_parser.add_argument(
        "--budget-minutes", type=float, default=None,
        help="Wall-clock budget for the campaign (durable across resumes)",
    )
    build_parser.add_argument(
        "--budget-experiments", type=int, default=None,
        help=f"Max experiments this run (default: {load_config()['budget']['experiments']}; a resume keeps the launch's)",
    )
    build_parser.add_argument(
        "--budget-usd", type=float, default=None,
        help="Best-effort model-spend budget in USD",
    )
    build_parser.add_argument(
        "--budget-reserve-minutes", type=float, default=None,
        help="Wall clock escrowed for the final checkout and evaluation",
    )
    build_parser.add_argument(
        "--harness", type=str, default=None,
        help="The harness to build with: a bundled name, a directory, or a git "
             "reference (wins over the brief's Harness line)",
    )
    build_parser.add_argument(
        "--experience", type=str, default=None,
        help="Comma-separated sources to serve: mine, mine:all, leeroopedia, a bank "
             "path or git reference, an index name (wins over the brief's Experience line)",
    )
    build_parser.add_argument(
        "--resume", action="store_true",
        help="Continue the campaign in --output from its checkpoint",
    )
    build_parser.add_argument(
        "--detach", action="store_true",
        help="Start the campaign in a session of its own and return at once "
             "with its pid, log, status path and the watch command (needs --output)",
    )
    build_parser.add_argument(
        "--log", type=str, default=None,
        help="Where a detached run's output goes (default: <output>.log beside the campaign)",
    )

    build_parser.add_argument(
        "-a", "--coding-agent", type=str, choices=AVAILABLE_AGENTS,
        help="The host every session runs on, with the model the config's hosts table "
             "gives it (default: search_strategy.params.host)",
    )
    build_parser.add_argument(
        "--config", type=str, default=None,
        help="Your override file, layered over the packaged config (default: the packaged defaults)",
    )
    return cmd_build
