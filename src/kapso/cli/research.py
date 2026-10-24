"""`kapso research`: web research for an objective."""

import argparse
import json
import sys

from kapso.kapso import Kapso

NAME = "research"

# Research depths
RESEARCH_DEPTHS = ["light", "deep"]


def cmd_research(args) -> None:
    """Handle the research command - web research for objectives."""
    # Get objective text
    if args.objective_file:
        with open(args.objective_file) as f:
            objective = f.read()
    elif args.objective:
        objective = args.objective
    else:
        print("Error: --objective or --objective-file required for research command")
        sys.exit(1)

    # Parse mode(s)
    # Default to ["idea", "implementation"] if not specified
    modes = args.mode if args.mode else ["idea", "implementation"]

    # Validate modes
    valid_modes = {"idea", "implementation", "study"}
    for m in modes:
        if m not in valid_modes:
            print(f"Error: Invalid mode '{m}'. Must be one of: idea, implementation, study")
            sys.exit(1)

    # If single mode, pass as string; if multiple, pass as list
    mode_arg = modes[0] if len(modes) == 1 else modes

    # Create Kapso instance
    kapso = Kapso(config_path=args.config)

    # Run research
    findings = kapso.research(
        objective=objective,
        mode=mode_arg,
        depth=args.depth,
    )

    # Print results
    print("\n" + "=" * 60)
    print("RESEARCH COMPLETE")
    print("=" * 60)

    # Print ideas if available
    if hasattr(findings, 'ideas'):
        ideas = findings.ideas
        if ideas:
            print("\n--- Ideas ---")
            for idea in ideas[:5]:
                print(f"  - {idea.source}: {idea.content[:100]}...")

    # Print implementations if available
    if hasattr(findings, 'implementations'):
        impls = findings.implementations
        if impls:
            print("\n--- Implementations ---")
            for impl in impls[:5]:
                print(f"  - {impl.source}: {impl.content[:100]}...")

    # Print report if available
    if hasattr(findings, 'report') and findings.report:
        print("\n--- Research Report ---")
        print(findings.report.content[:500] + "..." if len(findings.report.content) > 500 else findings.report.content)

    # Save to file if requested
    if args.output:
        output_data = {
            "objective": objective,
            "mode": modes,
            "depth": args.depth,
        }
        if hasattr(findings, 'ideas') and findings.ideas:
            output_data["ideas"] = [{"source": i.source, "content": i.content} for i in findings.ideas]
        if hasattr(findings, 'implementations') and findings.implementations:
            output_data["implementations"] = [{"source": i.source, "content": i.content} for i in findings.implementations]
        if hasattr(findings, 'report') and findings.report:
            output_data["report"] = findings.report.content

        with open(args.output, 'w') as f:
            json.dump(output_data, f, indent=2)
        print(f"\nResults saved to: {args.output}")


def add_parser(subparsers):
    research_parser = subparsers.add_parser(
        "research",
        help="Web research for objectives",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  kapso research --objective "How to optimize transformers?"
  kapso research --objective "LLM fine-tuning" --mode idea
  kapso research --objective "RAG implementation" --mode idea --mode implementation
  kapso research --objective-file topic.txt --mode study --depth deep
"""
    )

    # Objective specification
    obj_group = research_parser.add_mutually_exclusive_group()
    obj_group.add_argument("--objective", type=str, help="Research objective")
    obj_group.add_argument("--objective-file", type=str, help="File containing objective")

    # Research options
    research_parser.add_argument("--mode", type=str, action="append", help="Research mode: idea, implementation, study (can specify multiple)")
    research_parser.add_argument("--depth", type=str, choices=RESEARCH_DEPTHS, default="deep", help="Research depth (default: deep)")
    research_parser.add_argument("-o", "--output", type=str, help="Output file for results (JSON)")

    research_parser.add_argument(
        "--config", type=str, default=None,
        help="Config path (default: packaged config.yaml)",
    )
    return cmd_research
