"""`kapso bank`: the lesson bank's share remote."""

import shutil
import sys
from pathlib import Path

from kapso.kapso import DEFAULT_CONFIG_PATH
from kapso.core.config import load_config
from kapso.learning.bank_remote import connect_bank, create_bank_repo
from kapso.learning.update_frame import init_bank

NAME = "bank"


def cmd_bank(args) -> None:
    """Attach (and optionally create) the bank's share remote. Credentials
    are git's/gh's own business — kapso never handles them."""
    config = load_config(args.config or DEFAULT_CONFIG_PATH)
    home = Path(config["learning"]["bank"]["local_path"]).expanduser()

    if args.bank_command == "create":
        if shutil.which("gh") is None:
            print("`gh` CLI not found — create the repository yourself, then:")
            print(f"  kapso bank connect https://github.com/{args.slug}.git")
            sys.exit(1)
        url = create_bank_repo(args.slug, private=not args.public)
        print(f"created {url} ({'public' if args.public else 'private'})")
    else:
        url = args.url

    if not home.exists():
        init_bank(str(home))
        print(f"initialized bank home at {home}")
    connect_bank(home, url)
    print(f"bank connected: {home} -> {url}")
    print("lessons now push automatically at the end of every learn()")


def add_parser(subparsers):
    bank_parser = subparsers.add_parser(
        "bank",
        help="Manage the lesson bank's share remote",
        description=(
            "The bank is local-only by default. `connect` attaches a git "
            "remote as its origin and pushes the bank there; `create` "
            "first creates the GitHub repository via the gh CLI. "
            "Credentials stay git's/gh's own — kapso never handles them."
        ),
    )
    bank_sub = bank_parser.add_subparsers(dest="bank_command", required=True)
    bank_connect = bank_sub.add_parser(
        "connect",
        help="Attach a git remote as the bank's origin and push the bank",
    )
    bank_connect.add_argument(
        "url", type=str, help="Git URL of the bank repository (https or ssh)"
    )
    bank_connect.add_argument(
        "--config", type=str, default=None,
        help="Config path (default: packaged config.yaml)",
    )
    bank_create = bank_sub.add_parser(
        "create",
        help="Create a GitHub repo for the bank (gh CLI) and connect it",
    )
    bank_create.add_argument(
        "slug", type=str, help="org/name for the new repository"
    )
    bank_create.add_argument(
        "--public", action="store_true",
        help="Create the repository public (default: private)",
    )
    bank_create.add_argument(
        "--config", type=str, default=None,
        help="Config path (default: packaged config.yaml)",
    )
    return cmd_bank
