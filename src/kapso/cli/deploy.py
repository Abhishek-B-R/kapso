"""`kapso deploy`: deploy the solution a build wrote as running software,
and stop, start, read and list what was deployed (docs/plans/redesign/
wp5-deploy.md, "The verb")."""

import argparse
import json
from pathlib import Path
from typing import Dict, List, Optional

from kapso.cli.common import AVAILABLE_AGENTS
from kapso.deployment import DeployError, Software
from kapso.deployment.record import RUNNING, records
from kapso.handles import Solution
from kapso.kapso import Kapso

NAME = "deploy"
LIFECYCLE = ("status", "stop", "start", "logs")


def pairs(values: Optional[List[str]], flag: str) -> Dict[str, str]:
    """`KEY=VALUE` arguments; a value without `=` is refused by name."""
    parsed: Dict[str, str] = {}
    for value in values or []:
        if "=" not in value:
            raise DeployError(f"{flag} takes KEY=VALUE, got {value!r}")
        key, text = value.split("=", 1)
        parsed[key] = text
    return parsed


def workspace_size(workspace: Path) -> str:
    total = sum(path.stat().st_size for path in workspace.rglob("*") if path.is_file())
    return f"{total / 1_000_000:.1f} MB"


def summary(software: Software, campaign: str) -> List[str]:
    """What a person reads after a deployment: what runs where, the call
    it proved, and the next actions pinned to this deployment's number."""
    record = json.loads(software.record.read_text(encoding="utf-8"))
    run = record["result"]["run"]
    kind = run["kind"]
    how = {
        "function": f"function — {run.get('module')}.{run.get('callable')} in a worker process",
        "http": f"http — POST {run.get('url')}{run.get('path')}",
        "script": "script — the target's scripts/run.py",
    }[kind]
    proof = record["result"]["proof"]
    lines = [
        "",
        "=" * 60,
        f"DEPLOYED: deployment {software.number} of {campaign}",
        "=" * 60,
        f"  Target:    {software.target}" + (f" (chosen: {record['reasoning']})" if record["target_requested"] == "auto" else ""),
        f"  State:     {software.state}" + (" (healthy)" if software.is_healthy() else " (not answering)"),
        f"  Run:       {how}",
        f"  Proof:     {json.dumps(proof['inputs'])} -> {json.dumps(proof['output'])}",
        f"  Endpoint:  {software.endpoint or 'none'}",
        f"  Summary:   {record['result']['summary']}",
        f"  Workspace: {software.workspace} (the solution with its data, {workspace_size(software.workspace)})",
        f"  Record:    {software.record}",
        "Next:",
        f"  Software.open({campaign!r}, {software.number}).run({json.dumps(proof['inputs'])})   # from Python",
        f"  kapso deploy {campaign} --logs --number {software.number}",
        f"  kapso deploy {campaign} --stop --number {software.number}",
        f"  kapso deploy {campaign} --start --number {software.number}",
    ]
    return lines


def lifecycle(args) -> None:
    campaign = args.campaign
    if args.status:
        found = records(Path(campaign))
        if not found:
            raise DeployError(f"{campaign} has no deployment")
        for record in found:
            healthy = ""
            if record.state == RUNNING:
                healthy = " (healthy)" if Software.open(campaign, record.number, config=args.config).is_healthy() else " (not answering)"
            print(
                f"  {record.number}  {record.state}{healthy}  {record.data['target']}  "
                f"{record.data['endpoint'] or 'no endpoint'}  {record.data['state_at']}"
            )
        return
    software = Software.open(campaign, args.number, config=args.config)
    if args.stop:
        software.stop()
        print(f"stopped deployment {software.number} of {campaign}")
    elif args.start:
        software.start()
        print(f"started deployment {software.number} of {campaign}" + (" (healthy)" if software.is_healthy() else " (not answering)"))
    else:
        print(software.logs())


def cmd_deploy(args) -> None:
    if any(getattr(args, flag) for flag in LIFECYCLE):
        lifecycle(args)
        return
    # The solution a build wrote in that directory (its .kapso/solution.json)
    solution = Solution.open(args.campaign)
    env = pairs(args.env, "--env")
    options = pairs(args.option, "--option")
    kapso = Kapso(config=args.config)
    if args.harness:
        kapso.load_harness(args.harness)
    software = kapso.deploy(
        solution, target=args.target, env=env or None, options=options or None, coding_agent=args.coding_agent,
    )
    print("\n".join(summary(software, args.campaign)))


def add_parser(subparsers):
    deploy_parser = subparsers.add_parser(
        "deploy",
        help="Deploy the solution a build wrote as running software; stop, start, read or list what was deployed",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        allow_abbrev=False,
        epilog="""
Examples:
  kapso deploy ../churn-build
  kapso deploy ../churn-build --target docker --env API_KEY=xxx
  kapso deploy ../churn-build --target paper-trading --option schedule="*/5 * * * *"
  kapso deploy ../churn-build --status
  kapso deploy ../churn-build --stop --number 2
"""
    )
    deploy_parser.add_argument(
        "campaign", type=str,
        help="The campaign directory a build wrote (holds .kapso/solution.json)",
    )
    deploy_parser.add_argument(
        "--target", type=str, default=None,
        help="Where to deploy: auto, a bundled target (local, docker, modal, bentoml, langgraph) or a harness's "
             "(default: config deployment.target)",
    )
    deploy_parser.add_argument("--env", type=str, action="append", help="A variable the software needs at runtime, KEY=VALUE (repeatable)")
    deploy_parser.add_argument("--option", type=str, action="append", help="An option for the target's workflow, KEY=VALUE (repeatable)")
    deploy_parser.add_argument(
        "--coding-agent", type=str, choices=AVAILABLE_AGENTS, default=None,
        help="The host the deployment session runs on (default: config deployment.cli, else the build's host)",
    )
    deploy_parser.add_argument(
        "--config", type=str, default=None,
        help="Config path (default: packaged config.yaml); pass the one the build used",
    )
    deploy_parser.add_argument(
        "--harness", type=str, default=None,
        help="The harness whose deployment module the session carries: the build's "
             "(from the campaign record, the default) or another version of it",
    )
    deploy_parser.add_argument("--status", action="store_true", help="List the campaign's deployments with their state instead of deploying")
    deploy_parser.add_argument("--stop", action="store_true", help="Stop a deployment (the highest number, or --number)")
    deploy_parser.add_argument("--start", action="store_true", help="Start a stopped deployment again")
    deploy_parser.add_argument("--logs", action="store_true", help="Print a deployment's logs")
    deploy_parser.add_argument("--number", type=int, default=None, help="Which deployment --stop, --start and --logs act on (default: the highest)")
    return cmd_deploy
