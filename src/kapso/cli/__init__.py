#!/usr/bin/env python3
# Kapso CLI
#
# One module per verb under kapso/cli/. Each exposes NAME and
# add_parser(subparsers), which registers the verb's parser and returns
# its handler; main() wires them in the order below. Shared pieces (the
# agent list, detached runs, the campaign summary) live in common.py.
#
# Usage:
#     kapso build --brief kapso-brief.md --output ../campaign --detach
#     kapso research --objective "How to optimize transformers?"
#     kapso learn import --subset docs/plans/learning/d1-subset.yaml
#     kapso deploy ../campaign
#     kapso index_kg --wiki-dir ./data/wikis --save-to ./data/indexes/ml.index

import argparse
import sys

from dotenv import find_dotenv, load_dotenv
# Resolve .env from the caller's CWD upward. The no-arg default anchors at
# THIS file's directory — site-packages in a pip install — so the .env the
# README tells users to create next to their project was never read.
load_dotenv(find_dotenv(usecwd=True))

from kapso.cli import bank, build, deploy, doctor, harness, inbox, index_kg, learn, research, watch
from kapso.cli.common import list_agents
from kapso.execution.coding_agents.factory import CodingAgentFactory

# The verbs, in the order `kapso --help` lists them.
VERB_MODULES = (build, harness, research, learn, deploy, index_kg, watch, inbox, bank, doctor)


def main():
    CodingAgentFactory.register_quiet_exit()
    # Main parser
    parser = argparse.ArgumentParser(
        description="Kapso: Long-running agents that optimize AI and Data systems, and learn from every experience",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Commands:
  build      Build software that meets a brief, by experiment
  harness    Author, check and fetch harnesses: the domain layer a build loads
  research   Web research for objectives
  learn      Trajectory learning (store, mining, updating, grading)
  deploy     Deploy solutions as running software
  index_kg   Index knowledge graph from wiki or JSON data
  watch      Watch a running build / learn / learn_knowledge operation
  inbox      What a build is waiting on you for, and how to answer it
  doctor     Check this machine is ready to run Kapso

Examples:
  # Build a solution
  kapso build --brief kapso-brief.md --output ../campaign --detach

  # Research a topic
  kapso research --objective "How to optimize transformers?"

  # Learn from a repository
  kapso learn import --subset docs/plans/learning/d1-subset.yaml

  # Deploy a solution
  kapso deploy ../campaign --strategy local

  # Index knowledge graph
  kapso index_kg --wiki-dir ./data/wikis --save-to ./data/indexes/ml.index
"""
    )

    # Global options
    parser.add_argument(
        "--list-agents",
        action="store_true",
        help="List available coding agents"
    )

    # Subparsers for commands
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    handlers = {module.NAME: module.add_parser(subparsers) for module in VERB_MODULES}

    # =========================================================================
    # Parse and execute
    # =========================================================================
    args = parser.parse_args()

    # Handle global options
    if args.list_agents:
        list_agents()
        return

    # Route to command handler
    if args.command in handlers:
        handlers[args.command](args)
    else:
        parser.print_help()
        print("\nError: Please specify a command (build, research, learn, deploy, index_kg, watch, inbox, bank, doctor)")
        sys.exit(1)
