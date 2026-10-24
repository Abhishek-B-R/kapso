#!/usr/bin/env python3
# Kapso CLI
#
# One module per verb under kapso/cli/. Each exposes NAME and
# add_parser(subparsers), which registers the verb's parser and returns
# its handler; main() wires them in the order below. Shared pieces (the
# agent and strategy lists, detached runs, the campaign summary) live in
# common.py.
#
# Usage:
#     kapso evolve --goal "Build a web scraper..."
#     kapso research --objective "How to optimize transformers?"
#     kapso learn import --subset docs/plans/learning/d1-subset.yaml
#     kapso deploy --solution-path ./solution
#     kapso index_kg --wiki-dir ./data/wikis --save-to ./data/indexes/ml.index

import argparse
import sys

from dotenv import find_dotenv, load_dotenv
# Resolve .env from the caller's CWD upward. The no-arg default anchors at
# THIS file's directory — site-packages in a pip install — so the .env the
# README tells users to create next to their project was never read.
load_dotenv(find_dotenv(usecwd=True))

from kapso.cli import bank, deploy, doctor, evolve, inbox, index_kg, learn, research, watch
from kapso.cli.common import list_agents
from kapso.execution.coding_agents.factory import CodingAgentFactory

# The verbs, in the order `kapso --help` lists them.
VERB_MODULES = (evolve, research, learn, deploy, index_kg, watch, inbox, bank, doctor)


def main():
    CodingAgentFactory.register_quiet_exit()
    # Main parser
    parser = argparse.ArgumentParser(
        description="Kapso: Long-running agents that optimize AI and Data systems, and learn from every experience",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Commands:
  evolve     Build software from goals using experimentation
  research   Web research for objectives
  learn      Trajectory learning (store, mining, updating, grading)
  deploy     Deploy solutions as running software
  index_kg   Index knowledge graph from wiki or JSON data
  watch      Watch a running evolve / learn / learn_knowledge operation
  inbox      What evolve is waiting on you for, and how to answer it
  doctor     Check this machine is ready to run Kapso

Examples:
  # Evolve a solution
  kapso evolve --goal "Build a web scraper"

  # Research a topic
  kapso research --objective "How to optimize transformers?"

  # Learn from a repository
  kapso learn import --subset docs/plans/learning/d1-subset.yaml

  # Deploy a solution
  kapso deploy --solution-path ./solution --strategy local

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
        print("\nError: Please specify a command (evolve, research, learn, deploy, index_kg, watch, inbox, bank, doctor)")
        sys.exit(1)
