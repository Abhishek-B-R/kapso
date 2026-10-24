"""`kapso deploy`: deploy a solution as running software."""

import argparse
import signal
import sys
import time

from kapso.kapso import Kapso, DeployStrategy
from kapso.handles import Solution
from kapso.cli.common import AVAILABLE_AGENTS

NAME = "deploy"

# Available deploy strategies: AUTO plus whatever strategies/ holds
DEPLOY_STRATEGIES = [member.value for member in DeployStrategy]


def cmd_deploy(args) -> None:
    """Handle the deploy command - deploy solutions."""
    # The solution a build wrote in that directory (its .kapso/solution.json)
    solution = Solution.open(args.solution_path)

    # Parse strategy (argparse already limited it to DEPLOY_STRATEGIES)
    strategy = DeployStrategy(args.strategy.lower())

    # Parse env vars
    env_vars = {}
    if args.env:
        for env_str in args.env:
            if '=' in env_str:
                key, value = env_str.split('=', 1)
                env_vars[key] = value

    # Create Kapso instance
    kapso = Kapso()

    # Deploy
    software = kapso.deploy(
        solution=solution,
        strategy=strategy,
        env_vars=env_vars if env_vars else None,
        coding_agent=args.coding_agent,
        model=args.model,
    )

    # Print summary
    print("\n" + "=" * 60)
    print("DEPLOY COMPLETE")
    print("=" * 60)
    print(f"Strategy: {strategy}")
    print(f"Code path: {solution.trace}")
    print(f"Software ready: {software.is_healthy()}")

    # If interactive mode, keep running until Ctrl+C, then stop the software.
    if args.interactive:
        print("\nSoftware deployed. Press Ctrl+C to stop.")

        def stop_and_exit(signum, frame) -> None:
            print("\nStopping software...")
            software.stop()
            print("Stopped.")
            sys.exit(0)

        signal.signal(signal.SIGINT, stop_and_exit)
        while True:
            time.sleep(1)


def add_parser(subparsers):
    deploy_parser = subparsers.add_parser(
        "deploy",
        help="Deploy solutions as running software",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  kapso deploy --solution-path ../churn-build
  kapso deploy --solution-path ../churn-build --strategy docker
  kapso deploy --solution-path ../churn-build --env API_KEY=xxx --interactive
"""
    )

    # Required options
    deploy_parser.add_argument(
        "--solution-path", type=str, required=True,
        help="The campaign directory a build wrote (holds .kapso/solution.json)",
    )

    # Deploy options
    deploy_parser.add_argument("--strategy", type=str, choices=DEPLOY_STRATEGIES, default="auto", help="Deploy strategy (default: auto)")
    deploy_parser.add_argument("--env", type=str, action="append", help="Environment variable (KEY=VALUE, can specify multiple)")
    deploy_parser.add_argument("--coding-agent", type=str, choices=AVAILABLE_AGENTS, default=None, help="Coding agent for the selector and adapter sessions (default: config deployment.coding_agent)")
    deploy_parser.add_argument("--model", type=str, default=None, help="Model that agent is asked for (default: config deployment.model)")
    deploy_parser.add_argument("--interactive", action="store_true", help="Keep running after deploy")
    return cmd_deploy
