"""`kapso index_kg`: index a knowledge graph from a wiki directory or JSON data."""

import argparse
import sys

from kapso.kapso import Kapso

NAME = "index_kg"


def cmd_index_kg(args) -> None:
    """Handle the index_kg command - index knowledge graph."""
    if not args.save_to:
        print("Error: --save-to required for index_kg command")
        sys.exit(1)

    if not args.wiki_dir and not args.data_path:
        print("Error: --wiki-dir or --data-path required for index_kg command")
        sys.exit(1)

    # Create Kapso instance
    kapso = Kapso()

    # Index knowledge graph
    index_path = kapso.index_kg(
        wiki_dir=args.wiki_dir,
        data_path=args.data_path,
        save_to=args.save_to,
        search_type=args.search_type,
        force=args.force,
    )

    # Print summary
    print("\n" + "=" * 60)
    print("INDEX COMPLETE")
    print("=" * 60)
    print(f"Index saved to: {index_path}")


def add_parser(subparsers):
    index_parser = subparsers.add_parser(
        "index_kg",
        help="Index knowledge graph",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  kapso index_kg --wiki-dir ./data/wikis --save-to ./data/indexes/ml.index
  kapso index_kg --data-path ./data/kg_data.json --save-to ./data/indexes/kaggle.index
  kapso index_kg --wiki-dir ./data/wikis --save-to ./data/indexes/ml.index --force
"""
    )

    # Data source (mutually exclusive)
    data_group = index_parser.add_mutually_exclusive_group()
    data_group.add_argument("--wiki-dir", type=str, help="Wiki directory to index")
    data_group.add_argument("--data-path", type=str, help="JSON data file to index")

    # Index options
    index_parser.add_argument("--save-to", type=str, required=True, help="Path to save .index file")
    index_parser.add_argument("--search-type", type=str, help="Search backend type (kg_graph_search, kg_llm_navigation)")
    index_parser.add_argument("--force", action="store_true", help="Clear existing data before indexing")
    return cmd_index_kg
