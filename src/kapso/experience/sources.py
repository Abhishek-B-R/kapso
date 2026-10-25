"""Resolving a reference into a source: what it is, where it is, its
pinned head or id, and its provenance, said in the words the sessions
read. Loading confirms a source exists and is readable; it never ingests
and never creates (onboarding.md section 2).
"""

import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, Optional

from dotenv import dotenv_values, find_dotenv

from kapso.experience.reference import HOSTED, MINE, ExperienceReference, ExperienceReferenceError
from kapso.experience.store import ExperienceStore
from kapso.handles import ExperienceRef

PROVENANCE_MINE = "measured by you"
PROVENANCE_BANK = "measured by others"
PROVENANCE_REPORTED = "reported by others"
SCOPE_HARNESS = "harness"
SCOPE_ALL = "all"
SCOPES = (SCOPE_HARNESS, SCOPE_ALL)
HOSTED_KEY = "LEEROOPEDIA_API_KEY"
_CARD_DIRS = ("insights/", "procedures/")


class ExperienceError(ValueError):
    """A source that cannot be loaded, with the line that would make it."""


@dataclass
class ExperienceSource:
    reference: str              # as given
    kind: str                   # "bank" | "hosted" | "index"
    resolved: str               # the bank home or clone, the gate's URL without its key, the index directory
    head: Optional[str]         # a bank's pinned commit; an index's id; None for the hosted gate
    provenance: str
    scope: str                  # "harness" | "all"
    path: Optional[Path] = None
    url: Optional[str] = None
    cards: Optional[int] = None

    def ref(self) -> ExperienceRef:
        return ExperienceRef(reference=self.reference, kind=self.kind, resolved=self.resolved, head=self.head, provenance=self.provenance)

    def label(self) -> str:
        if self.kind == "bank":
            count = f", {self.cards} card{'s' if self.cards != 1 else ''}" if self.cards is not None else ""
            every = ", every scope" if self.scope == SCOPE_ALL else ""
            return f"{self.reference} at {short(self.head)}{count}, {self.provenance}{every}"
        if self.kind == "index":
            count = f", {self.cards} page{'s' if self.cards != 1 else ''}" if self.cards is not None else ""
            return f"{self.reference} (index {short(self.head)}{count}), {self.provenance}"
        return f"{self.reference} (hosted), {self.provenance}"


def short(head: Optional[str]) -> str:
    return (head or "")[:12]


def resolve_source(
    reference: ExperienceReference,
    *,
    settings: Dict[str, Any],
    scope: str = SCOPE_HARNESS,
    dotenv_path: Optional[str] = None,
) -> ExperienceSource:
    """The source a reference names, pinned: `mine` pulled from its remote
    and at its head, a bank you read at its clone's head, the hosted gate
    with its key present, an index at its id."""
    if scope not in SCOPES:
        raise ExperienceError(f"scope must be one of {', '.join(SCOPES)}, not {scope!r}")
    store = ExperienceStore(settings["banks"], settings["indexes"])
    if reference.kind == MINE:
        home = Path(settings["bank_home"]).expanduser()
        if not home.exists():
            raise ExperienceError(
                f"your bank does not exist yet at {home}: `kapso experience add mine` creates it, "
                "and a first learn() creates it too"
            )
        require_bank(home, reference.raw)
        pull_home(home)
        head = bank_head(home)
        return ExperienceSource(
            reference=reference.raw, kind="bank", resolved=str(home), head=head, provenance=PROVENANCE_MINE,
            scope=scope, path=home, cards=count_cards(home, head),
        )
    if reference.kind == "path":
        require_bank(reference.path, reference.raw)
        head = bank_head(reference.path)
        return ExperienceSource(
            reference=reference.raw, kind="bank", resolved=str(reference.path), head=head, provenance=PROVENANCE_BANK,
            scope=SCOPE_ALL, path=reference.path, cards=count_cards(reference.path, head),
        )
    if reference.kind == "git":
        clone = store.resolve_bank(reference)
        require_bank(clone, reference.raw)
        head = bank_head(clone)
        return ExperienceSource(
            reference=reference.raw, kind="bank", resolved=str(clone), head=head, provenance=PROVENANCE_BANK,
            scope=SCOPE_ALL, path=clone, cards=count_cards(clone, head),
        )
    if reference.kind == "hosted":
        hosted = settings["hosted"]
        present = os.environ.get(HOSTED_KEY) or HOSTED_KEY in dotenv_values(
            dotenv_path if dotenv_path is not None else find_dotenv(usecwd=True)
        )
        if not present:
            raise ExperienceError(
                f"{HOSTED} needs {HOSTED_KEY}: put {HOSTED_KEY}=kpsk_... in .env beside the run (sign up at "
                "https://app.leeroopedia.com/dashboard); nothing to install"
            )
        return ExperienceSource(
            reference=reference.raw, kind="hosted", resolved=hosted["url"], head=None, provenance=PROVENANCE_REPORTED,
            scope=SCOPE_ALL, url=hosted["url"],
        )
    record = store.index_record(reference.name)
    return ExperienceSource(
        reference=reference.raw, kind="index", resolved=str(record.path), head=record.id, provenance=PROVENANCE_REPORTED,
        scope=SCOPE_ALL, path=record.path, cards=record.page_count,
    )


def require_bank(home: Path, raw: str) -> None:
    """A bank home is a git repository (bare or not) whose main branch
    holds the founding skeleton: index.md, insights/, procedures/."""
    listing = subprocess.run(
        ["git", "-C", str(home), "ls-tree", "--name-only", "main"], capture_output=True, text=True,
    )
    names = set(listing.stdout.split()) if listing.returncode == 0 else set()
    if listing.returncode != 0 or not {"index.md", "insights", "procedures"} <= names:
        raise ExperienceError(
            f"{raw} ({home}) is not a bank: a bank is a git repository whose main branch holds index.md, "
            "insights/ and procedures/ (`kapso experience add mine` makes one; a bank you read is one somebody's learn() wrote)"
        )


def bank_head(home: Path) -> str:
    return subprocess.run(
        ["git", "-C", str(home), "rev-parse", "main"], capture_output=True, text=True, check=True,
    ).stdout.strip()


def pull_home(home: Path) -> None:
    """`mine` with a remote attached pulls before it is pinned, so the
    team's lessons are served; a history that does not fast-forward is
    an error in git's words."""
    origin = subprocess.run(
        ["git", "-C", str(home), "remote", "get-url", "origin"], capture_output=True, text=True,
    )
    if origin.returncode != 0:
        return
    pulled = subprocess.run(
        ["git", "-C", str(home), "fetch", "--quiet", "origin", "main:main"],
        capture_output=True, text=True, env={**os.environ, "GIT_TERMINAL_PROMPT": "0"},
    )
    if pulled.returncode != 0:
        raise ExperienceError(
            f"your bank at {home} could not take the remote's main ({origin.stdout.strip()}):\n"
            f"{pulled.stderr.strip()}\nResolve it in the bank, then load again."
        )


def count_cards(home: Path, head: str) -> int:
    """The card files at the pinned head: `insights/*.md` and
    `procedures/*.md` but each directory's index."""
    listing = subprocess.run(
        ["git", "-C", str(home), "ls-tree", "-r", "--name-only", head], capture_output=True, text=True, check=True,
    )
    return sum(
        1 for name in listing.stdout.split()
        if name.startswith(_CARD_DIRS) and name.endswith(".md") and not name.endswith("/index.md")
    )
