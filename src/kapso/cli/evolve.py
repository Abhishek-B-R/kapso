"""`kapso evolve`: build software from a goal."""

import argparse
import sys
from pathlib import Path

from kapso.kapso import Kapso, DEFAULT_MAX_ITERATIONS
from kapso.cli.common import (
    AVAILABLE_AGENTS,
    _default_log,
    _detach,
    _print_evolve_summary,
    _without_detach_flags,
)

NAME = "evolve"


def cmd_evolve(args) -> None:
    """Handle the evolve command - build software from goals."""
    # Get goal text
    if args.goal_file:
        with open(args.goal_file) as f:
            goal = f.read()
    elif args.goal:
        goal = args.goal
    elif args.resume:
        goal = None   # a resume takes the goal from the checkpoint
    else:
        print("Error: --goal or --goal-file required for evolve command")
        sys.exit(1)

    if args.detach:
        if not args.output:
            print(
                "Error: --detach needs --output: the campaign directory is "
                "where its status file lives and its log goes beside"
            )
            sys.exit(1)
        campaign = Path(args.output).expanduser().resolve()
        _detach(
            "kapso evolve",
            _without_detach_flags(sys.argv[1:]),
            log_path=(
                Path(args.log).expanduser().resolve() if args.log
                else _default_log(campaign)
            ),
            campaign=campaign,
        )
        return

    # Create Kapso instance with optional KG index
    kapso = Kapso(config_path=args.config, kg_index=args.kg_index)

    # Build solution
    solution = kapso.evolve(
        goal=goal,
        output_path=args.output,
        max_iterations=args.iterations,
        time_budget_minutes=args.time_budget_minutes,
        cost_budget=args.cost_budget,
        finalization_reserve_minutes=args.finalization_reserve_minutes,
        mode=args.mode,
        coding_agent=args.coding_agent,
        eval_dir=args.eval_dir,
        data_dir=args.data_dir,
        initial_repo=args.initial_repo,
        resume=args.resume,
    )

    _print_evolve_summary(solution)


def add_parser(subparsers):
    evolve_parser = subparsers.add_parser(
        "evolve",
        help="Build software from goals",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  kapso evolve --goal "Build a web scraper for news articles"
  kapso evolve --goal-file problem.txt --iterations 20
  kapso evolve --goal "Build a classifier" --eval-dir ./eval/ --data-dir ./data/
  kapso evolve --goal "Build a classifier" --output ./campaign --detach   # returns at once; follow with kapso watch
  kapso evolve --output ./campaign --resume      # goal and flags from the launch record
"""
    )

    # Goal specification
    goal_group = evolve_parser.add_mutually_exclusive_group()
    goal_group.add_argument("-g", "--goal", type=str, help="Goal/problem description (a resume takes it from the checkpoint)")
    goal_group.add_argument("-f", "--goal-file", type=str, help="File containing goal")

    # Basic options
    evolve_parser.add_argument(
        "-i", "--iterations", type=int, default=None,
        help=f"Max iterations (default: {DEFAULT_MAX_ITERATIONS}; a resume keeps the launch's)",
    )
    evolve_parser.add_argument("-o", "--output", type=str, help="Output directory")
    evolve_parser.add_argument(
        "--time-budget-minutes",
        type=float,
        default=None,
        help="Wall-clock budget for the campaign (durable across resumes)",
    )
    evolve_parser.add_argument(
        "--cost-budget",
        type=float,
        default=None,
        help="Best-effort spend budget in USD",
    )
    evolve_parser.add_argument(
        "--finalization-reserve-minutes",
        type=float,
        default=None,
        help="Wall-clock escrowed for final checkout and evaluation",
    )
    evolve_parser.add_argument(
        "--resume",
        action="store_true",
        help="Continue the compatible checkpoint in --output",
    )
    evolve_parser.add_argument(
        "--detach",
        action="store_true",
        help="Start the campaign in a session of its own and return at once "
             "with its pid, log, status path and the watch command (needs --output)",
    )
    evolve_parser.add_argument(
        "--log", type=str, default=None,
        help="Where a detached run's output goes (default: <output>.log beside the campaign)",
    )
    # Configuration options
    evolve_parser.add_argument("-m", "--mode", type=str, help="Config mode (GENERIC, MINIMAL)")
    evolve_parser.add_argument("-a", "--coding-agent", type=str, choices=AVAILABLE_AGENTS, help="Coding agent")

    evolve_parser.add_argument(
        "--config", type=str, default=None,
        help="Config path (default: packaged config.yaml)",
    )

    # Directory options
    evolve_parser.add_argument("--eval-dir", type=str, help="Evaluation files directory")
    evolve_parser.add_argument("--data-dir", type=str, help="Data files directory")
    evolve_parser.add_argument("--initial-repo", type=str, help="Initial repository (path or GitHub URL)")

    # Knowledge graph
    evolve_parser.add_argument("--kg-index", type=str, help="Path to KG index file")
    return cmd_evolve
