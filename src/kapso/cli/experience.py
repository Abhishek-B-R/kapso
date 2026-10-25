"""`kapso experience`: what must exist before it can be loaded, what
exists, and sharing your bank. Design: docs/research/onboarding.md section
2; plan: docs/plans/redesign/wp3-experience.md."""

import argparse
import sys
from pathlib import Path

from kapso.core.config import load_experience_defaults
from kapso.experience import (
    HOSTED,
    HOSTED_KEY,
    MINE,
    ExperienceStore,
    bank_head,
    count_cards,
    hosted_key_missing,
    hosted_key_present,
)
from kapso.kapso import Kapso
from kapso.learning.bank_remote import bank_origin, connect_bank
from kapso.learning.update_frame import init_bank

NAME = "experience"


def cmd_experience(args) -> None:
    if args.experience_command == "add":
        _add(args)
        return
    settings = load_experience_defaults(args.config)
    home = Path(settings["bank_home"]).expanduser()
    if args.experience_command == "list":
        _list(settings, home)
    else:
        _share(args.url, home)


def _add(args) -> None:
    given = [value for value in (args.ref, args.repo, args.research) if value]
    if len(given) != 1:
        print(
            f"Error: `add` takes exactly one of `{MINE}`, `{HOSTED}`, --repo <url> or --research <question> "
            "(an index needs --name <n>)"
        )
        sys.exit(1)
    if args.repo or args.research:
        if not args.name:
            print("Error: an index needs a name: --name <n> (`kapso experience list` shows the names taken)")
            sys.exit(1)
        # The facade owns the ingestion (the preflight, the pipeline, the
        # record); it reads the config itself.
        Kapso(config=args.config).add_experience(repo=args.repo, research=args.research, name=args.name)
        return
    home = Path(load_experience_defaults(args.config)["bank_home"]).expanduser()
    if args.ref == MINE:
        if home.exists():
            head = bank_head(home)
            print(f"your bank exists at {home}: head {head[:12]}, {count_cards(home, head)} cards")
            return
        init_bank(str(home))
        print(f"created your bank at {home} (empty; learn() fills it, --experience mine serves it)")
        return
    if args.ref == HOSTED:
        if not hosted_key_present():
            print(f"Error: {hosted_key_missing()}")
            sys.exit(1)
        print(f"{HOSTED}: {HOSTED_KEY} present; `--experience {HOSTED}` mounts the gate in ideation and implementation")
        return
    print(
        f"Error: `add` creates what must exist before it is loaded: `{MINE}` or `{HOSTED}`; a bank by path "
        "or git reference needs no add (load it), and an index is ingested with --repo <url> --name <n> "
        "or --research <question> --name <n>"
    )
    sys.exit(1)


def _list(settings, home: Path) -> None:
    store = ExperienceStore(settings["banks"], settings["indexes"])
    banks = store.banks()
    indexes = store.indexes()
    key = hosted_key_present()
    if not home.exists() and not banks and not indexes and not key:
        print(
            f"no experience yet: `kapso experience add {MINE}` creates your bank (a first learn() does too); "
            f"`kapso experience add {HOSTED}` once {HOSTED_KEY} is in .env; "
            "`kapso experience add --repo <url> --name <n>` ingests a repository"
        )
        return
    if home.exists():
        head = bank_head(home)
        origin = bank_origin(home)
        remote = f"remote {origin}" if origin else "no remote (kapso experience share <url>)"
        print(f"{MINE:<13}{str(home):<44} head {head[:12]}   {count_cards(home, head)} cards   {remote}")
    else:
        print(f"{MINE:<13}not created: kapso experience add {MINE} (or a first learn())")
    print(f"{HOSTED:<13}hosted{'':<38} {'key present' if key else f'no key: put {HOSTED_KEY}=... in .env'}")
    if banks:
        print("banks you read")
        for bank in banks:
            path = Path(bank["path"])
            head = bank_head(path)
            print(f"  {bank['remote']}@{bank['rev']}   head {head[:12]}   {count_cards(path, head)} cards   {path}")
    if indexes:
        print("indexes")
        for record in indexes:
            print(f"  {record.name:<12} index {record.id[:12]}   {record.page_count} pages   ingested {record.created_at[:10]}   from {record.source}")


def _share(url: str, home: Path) -> None:
    if not home.exists():
        init_bank(str(home))
        print(f"created your bank at {home}")
    connect_bank(home, url)
    print(
        f"your bank {home} shares to {url}; learn() pushes there from now on, `kapso experience update` pulls "
        f"from there, and the intro says the cards are measured by you and your team"
    )


def add_parser(subparsers):
    parser = subparsers.add_parser(
        "experience",
        help="What a build is served that was measured before: your bank, the hosted gate, ingested corpora",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        allow_abbrev=False,
        description=(
            "Experience is loaded at the call (`--experience mine,leeroopedia`, the brief's Experience line, "
            "load_experience()); this verb makes what must exist first, lists what exists, and shares your bank."
        ),
        epilog="""
Examples:
  kapso experience add mine                                   # your bank, empty, where learn() writes
  kapso experience add leeroopedia                            # checks the key in .env
  kapso experience add --repo https://github.com/org/x --name org-x      # ingests a repository into an index
  kapso experience add --research "QLoRA memory tricks" --name qlora     # researches the web, ingests the findings
  kapso experience list                                       # mine, the hosted gate, banks you read, indexes
  kapso experience share https://github.com/acme/kapso-bank.git
  kapso build --experience mine,org-x --brief kapso-brief.md ...
""",
    )
    experience_sub = parser.add_subparsers(dest="experience_command", required=True)
    add = experience_sub.add_parser(
        "add",
        help="Create your bank (`mine`), check the hosted gate's key (`leeroopedia`), or ingest a corpus into an index",
    )
    add.add_argument("ref", type=str, nargs="?", default=None, help="`mine` or `leeroopedia`")
    add.add_argument("--repo", type=str, default=None, help="A repository URL to ingest into the index --name")
    add.add_argument("--research", type=str, default=None, help="A question to research on the web and ingest into the index --name")
    add.add_argument("--name", type=str, default=None, help="The index's name (letters, digits, dashes)")
    add.add_argument("--config", type=str, default=None, help="Config path (default: packaged config.yaml)")
    listing = experience_sub.add_parser("list", help="Every source this machine has, with its state")
    listing.add_argument("--config", type=str, default=None, help="Config path (default: packaged config.yaml)")
    share = experience_sub.add_parser("share", help="Attach a git remote to your bank and push it")
    share.add_argument("url", type=str, help="Git URL of the bank repository (https or ssh)")
    share.add_argument("--config", type=str, default=None, help="Config path (default: packaged config.yaml)")
    return cmd_experience
