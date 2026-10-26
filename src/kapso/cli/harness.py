"""`kapso harness`: author, check and fetch harnesses, the domain layer a
build loads (docs/research/harness-design.md, onboarding.md section 1)."""

import argparse
import sys
from pathlib import Path

from kapso.core.config import load_config
from kapso.harness import (
    BUNDLED_ROOT,
    HarnessStore,
    check_harness,
    parse_reference,
    read_manifest,
)
from kapso.harness.manifest import MANIFEST_FILE, valid_name

NAME = "harness"
TEMPLATES = Path(__file__).resolve().parent.parent / "harness" / "templates"


def cmd_harness(args) -> None:
    settings = load_config(args.config)["harness"]
    store = HarnessStore(Path(settings["store"]))
    command = args.harness_command
    if command == "new":
        _new(args.name, Path(args.dir).expanduser() if args.dir else Path.cwd())
        return
    if command == "list":
        _list(store, settings)
        return
    reference = parse_reference(args.ref)
    if command == "remove":
        print(f"removed {store.remove(reference)}")
        return
    if command == "update":
        before, after = store.update(reference)
        if before == after:
            print(f"at {after[:12]}: a tag or a commit never moves")
        else:
            print(f"now at {after[:12]} (was {before[:12]})")
    # check, add and update: resolve (fetching when needed, and saying so),
    # then the report; a failure exits 1, what the machine lacks never does.
    fetched_before = reference.kind != "git" or store.is_fetched(reference)
    path = store.resolve(reference)
    if not fetched_before:
        print(f"fetched {path}")
    report = check_harness(path, page_warning_lines=int(settings["page_warning_lines"]))
    print(report.render())
    if report.manifest is not None:
        print(f"name     {report.manifest.name} {report.manifest.version}")
    if not report.ok():
        sys.exit(1)


def _new(name: str, parent: Path) -> None:
    """The two-file starter the authoring guide begins with."""
    if not valid_name(name):
        print(f"Error: a harness name matches [a-z0-9][a-z0-9-]*, not {name!r}", file=sys.stderr)
        sys.exit(1)
    root = parent / name
    if root.exists():
        print(f"Error: {root} exists; choose another name or directory", file=sys.stderr)
        sys.exit(1)
    (root / "instructions").mkdir(parents=True)
    (root / MANIFEST_FILE).write_text(
        (TEMPLATES / "harness.yaml").read_text(encoding="utf-8").replace("{name}", name), encoding="utf-8",
    )
    (root / "instructions" / "guardrails.md").write_text(
        (TEMPLATES / "guardrails.md").read_text(encoding="utf-8").replace("{title}", name.replace("-", " ").capitalize()),
        encoding="utf-8",
    )
    print(f"created {root}")
    print(f"  {MANIFEST_FILE}                 name, version, description; the module lists to fill")
    print("  instructions/guardrails.md   the rules every module's sessions read")
    print(f"next: edit the two files, then  kapso harness check {_shown(root)}")


def _list(store: HarnessStore, settings) -> None:
    bundled = sorted(p for p in BUNDLED_ROOT.iterdir() if (p / MANIFEST_FILE).is_file()) if BUNDLED_ROOT.is_dir() else []
    fetched = store.entries()
    if not bundled and not fetched:
        print("no harnesses yet: write one with `kapso harness new <name>`, or fetch one with "
              "`kapso harness add <git reference>`; a local directory loads by path, no add needed")
        return
    lines = int(settings["page_warning_lines"])
    if bundled:
        print("bundled")
        for path in bundled:
            manifest = read_manifest(path)
            print(f"  {manifest.name:<24} {manifest.version:<10} {_needs(path, lines)}")
    else:
        print("bundled    (none ship in this release)")
    if fetched:
        print("fetched")
        for entry in fetched:
            print(f"  {entry.name:<24} {entry.version:<10} {entry.reference}  {_needs(entry.path, lines)}")


def _needs(path: Path, page_warning_lines: int) -> str:
    report = check_harness(path, page_warning_lines=page_warning_lines)
    if not report.ok():
        return f"fails check ({len(report.failures)} failure(s))"
    if report.missing:
        return "needs " + ", ".join(row.label for row in report.missing)
    return "ready"


def _shown(path: Path) -> str:
    """A path as a person would type it: relative when it is under the
    working directory, else absolute; a bare name would be read as a
    bundled one."""
    cwd = Path.cwd()
    if path.resolve().is_relative_to(cwd):
        return f"./{path.resolve().relative_to(cwd).as_posix()}"
    return str(path.resolve())


def add_parser(subparsers):
    parser = subparsers.add_parser(
        "harness",
        help="Author, check and fetch harnesses: the domain layer a build loads",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        allow_abbrev=False,
        description=(
            "A harness is one directory per domain: instruction pages, skills, "
            "tool servers, delegates and hooks, listed per module in harness.yaml. "
            "A build loads one by bundled name, by path, or by git reference."
        ),
        epilog="""
Examples:
  kapso harness new trading                       # harness.yaml + instructions/guardrails.md
  kapso harness check ./trading                   # failures, warnings, what this machine lacks
  kapso harness add acme/harnesses@v3#trading     # fetch into the store and check
  kapso harness list                              # bundled and fetched harnesses
  kapso build --harness ./trading --brief kapso-brief.md ...
""",
    )
    sub = parser.add_subparsers(dest="harness_command", required=True)
    new = sub.add_parser("new", help="Write the two-file starter for a new harness")
    new.add_argument("name", type=str, help="The harness name: [a-z0-9][a-z0-9-]*")
    new.add_argument("--dir", type=str, default=None, help="Parent directory (default: the working directory)")
    for verb, text in (
        ("check", "Check a harness: failures, warnings, and what this machine lacks"),
        ("add", "Fetch a git reference into the store (a path is checked in place) and check it"),
        ("update", "Re-fetch a branch or HEAD reference; a tag or a commit never moves"),
        ("remove", "Delete one fetched clone, every harness in it; a path is refused"),
    ):
        command = sub.add_parser(verb, help=text)
        command.add_argument("ref", type=str, help="A bundled name, a directory, or a git reference")
        command.add_argument("--config", type=str, default=None, help="Config path (default: packaged config.yaml)")
    listing = sub.add_parser("list", help="The bundled and fetched harnesses, with what each needs")
    listing.add_argument("--config", type=str, default=None, help="Config path (default: packaged config.yaml)")
    new.add_argument("--config", type=str, default=None, help=argparse.SUPPRESS)
    return cmd_harness
