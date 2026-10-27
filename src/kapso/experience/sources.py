"""Resolving a reference into a source: what it is, where it is, its
pinned head or id, and its provenance, said in the words the sessions
read. Loading confirms a source exists and is readable; it never ingests
and never creates (onboarding.md section 2).
"""

import json
import os
import subprocess
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, Optional, Tuple

from dotenv import dotenv_values, find_dotenv

from kapso.experience.reference import (
    HOSTED,
    MINE,
    SCOPE_ALL,
    SCOPE_HARNESS,
    SCOPES,
    ExperienceReference,
    ExperienceReferenceError,
)
from kapso.experience.store import ExperienceStore
from kapso.handles import ExperienceRef

PROVENANCE_MINE = "measured by you"
PROVENANCE_TEAM = "measured by you and your team"     # `mine` with a remote attached
PROVENANCE_BANK = "measured by others"
PROVENANCE_REPORTED = "reported by others"
YOURS = (PROVENANCE_MINE, PROVENANCE_TEAM)
HOSTED_KEY = "LEEROOPEDIA_API_KEY"
MCP_PROTOCOL_VERSION = "2025-03-26"   # the streamable-HTTP MCP revision the probe speaks
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
    tool_timeout_seconds: Optional[int] = None   # the hosted gate's per-call timeout, from the config it was loaded with
    cards: Optional[int] = None

    def ref(self) -> ExperienceRef:
        return ExperienceRef(
            reference=self.reference, kind=self.kind, resolved=self.resolved, head=self.head,
            provenance=self.provenance, scope=self.scope,
        )

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
    dotenv_path: Optional[str] = None,
) -> ExperienceSource:
    """The source a reference names, pinned as it is on disk: `mine` at
    its home's head (`mine:all` lifting the scope rule), a bank you read
    at its clone's head, the hosted gate with its key present, an index
    at its id. Loading never touches the network beyond a first fetch of
    a bank you read; `update` is the network step."""
    store = ExperienceStore(settings["banks"], settings["indexes"])
    if reference.kind == MINE:
        home = Path(settings["bank_home"]).expanduser()
        if not home.exists():
            raise ExperienceError(
                f"your bank does not exist yet at {home}: `kapso experience add mine` creates it, "
                "and a first learn() creates it too"
            )
        require_bank(home, reference.raw)
        head = bank_head(home)
        return ExperienceSource(
            reference=MINE, kind="bank", resolved=str(home), head=head,
            provenance=PROVENANCE_TEAM if has_origin(home) else PROVENANCE_MINE,
            scope=reference.scope, path=home, cards=count_cards(home, head),
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
        if not hosted_key_present(dotenv_path):
            raise ExperienceError(hosted_key_missing())
        return ExperienceSource(
            reference=reference.raw, kind="hosted", resolved=hosted["url"], head=None, provenance=PROVENANCE_REPORTED,
            scope=SCOPE_ALL, url=hosted["url"], tool_timeout_seconds=int(hosted["tool_timeout_seconds"]),
        )
    record = store.index_record(reference.name)
    return ExperienceSource(
        reference=reference.raw, kind="index", resolved=str(record.path), head=record.id, provenance=PROVENANCE_REPORTED,
        scope=SCOPE_ALL, path=record.path, cards=record.page_count,
    )


def hosted_key_value(dotenv_path: Optional[str] = None) -> str:
    """The hosted gate's key, from the environment or `.env` beside the
    run; "" when absent or empty. Read to be sent to the gate, never
    printed or stored."""
    value = os.environ.get(HOSTED_KEY) or dotenv_values(
        dotenv_path if dotenv_path is not None else find_dotenv(usecwd=True)
    ).get(HOSTED_KEY)
    return value or ""


def hosted_key_present(dotenv_path: Optional[str] = None) -> bool:
    """Whether the hosted gate's key is set to something: a presence
    probe (an empty `LEEROOPEDIA_API_KEY=` is absent)."""
    return bool(hosted_key_value(dotenv_path))


def _post_json(url: str, payload: Dict[str, Any], timeout_seconds: int) -> Tuple[int, str, str]:
    """One HTTP POST of a JSON body; (status, content type, body text)."""
    request = urllib.request.Request(
        url, data=json.dumps(payload).encode("utf-8"), method="POST",
        headers={"Content-Type": "application/json", "Accept": "application/json, text/event-stream"},
    )
    with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
        return response.status, response.headers.get("Content-Type", ""), response.read().decode("utf-8")


def probe_hosted_gate(
    settings: Dict[str, Any], dotenv_path: Optional[str] = None, post: Callable[..., Tuple[int, str, str]] = _post_json,
) -> str:
    """`kapso experience add leeroopedia`'s one-time probe: an MCP
    `initialize` against the hosted server with the key on its URL.
    Returns the server's name; a refusal or an unreachable server raises
    with the status. The key goes on the wire and nowhere else."""
    hosted = settings["hosted"]
    key = hosted_key_value(dotenv_path)
    if not key:
        raise ExperienceError(hosted_key_missing())
    payload = {
        "jsonrpc": "2.0", "id": 1, "method": "initialize",
        "params": {"protocolVersion": MCP_PROTOCOL_VERSION, "capabilities": {}, "clientInfo": {"name": "kapso", "version": "probe"}},
    }
    status, content_type, body = post(hosted["url"].format(**{HOSTED_KEY: key}), payload, int(hosted["tool_timeout_seconds"]))
    if status != 200:
        raise ExperienceError(f"{HOSTED} refused the probe (HTTP {status}): check {HOSTED_KEY} in .env")
    text = body
    if "text/event-stream" in content_type:
        data = [line[5:].strip() for line in body.splitlines() if line.startswith("data:")]
        if not data:
            raise ExperienceError(f"{HOSTED} answered the probe with no message")
        text = data[0]
    answer = json.loads(text)
    if "result" not in answer:
        raise ExperienceError(f"{HOSTED} answered the probe with an error: {answer.get('error')}")
    return str((answer["result"].get("serverInfo") or {}).get("name") or HOSTED)


def hosted_key_missing() -> str:
    return (
        f"{HOSTED} needs {HOSTED_KEY}: put {HOSTED_KEY}=kpsk_... in .env beside the run (sign up at "
        "https://app.leeroopedia.com/dashboard); nothing to install"
    )


def is_bank(home: Path) -> bool:
    """A bank home is a git repository (bare or not) whose main branch
    holds the founding skeleton: index.md, insights/, procedures/."""
    listing = subprocess.run(
        ["git", "-C", str(home), "ls-tree", "--name-only", "main"], capture_output=True, text=True,
    )
    return listing.returncode == 0 and {"index.md", "insights", "procedures"} <= set(listing.stdout.split())


def source_exists(reference: ExperienceReference, *, settings: Dict[str, Any], dotenv_path: Optional[str] = None) -> bool:
    """Whether `resolve_source` would find the source: your bank made, a
    bank you read fetched, the hosted key present, an index ingested. A
    host session asks before loading what the config lists, so a missing
    source leaves its gate off instead of stopping the server."""
    store = ExperienceStore(settings["banks"], settings["indexes"])
    if reference.kind == MINE:
        return is_bank(Path(settings["bank_home"]).expanduser())
    if reference.kind == "path":
        return is_bank(reference.path)
    if reference.kind == "git":
        return store.is_fetched(reference) and is_bank(store.clone_dir(reference))
    if reference.kind == "hosted":
        return hosted_key_present(dotenv_path)
    return store.has_index(reference.name)


def require_bank(home: Path, raw: str) -> None:
    """`is_bank`, or the refusal naming what a bank is."""
    if not is_bank(home):
        raise ExperienceError(
            f"{raw} ({home}) is not a bank: a bank is a git repository whose main branch holds index.md, "
            "insights/ and procedures/ (`kapso experience add mine` makes one; a bank you read is one somebody's learn() wrote)"
        )


def bank_head(home: Path) -> str:
    """The commit a bank is at: `main` in a bare home, the checked-out
    revision in a clone (a bank read at a tag is pinned at the tag)."""
    return subprocess.run(
        ["git", "-C", str(home), "rev-parse", "HEAD"], capture_output=True, text=True, check=True,
    ).stdout.strip()


def has_origin(home: Path) -> bool:
    """Whether `mine` is shared: a remote named origin is attached."""
    origin = subprocess.run(
        ["git", "-C", str(home), "remote", "get-url", "origin"], capture_output=True, text=True,
    )
    return origin.returncode == 0


def pull_home(home: Path) -> None:
    """`kapso experience update`: `mine` with a remote attached takes the
    remote's main, so the team's lessons are served next; a history that
    does not fast-forward is an error in git's words."""
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


def experience_settings(config: Dict[str, Any]) -> Dict[str, Any]:
    """The experience homes (the config's `experience` block) with what the
    sources need from the other blocks: `bank_home` (`learning.bank.local_path`,
    where `mine` lives), `session_root` (`learning.serving.session_root`,
    where a host session stages), `probe_budget`
    (`learning.retriever.probe_budget`, the probe offers riding card reads
    per campaign) and `hosted` (`gates.leeroopedia`)."""
    settings = dict(config["experience"])
    settings["bank_home"] = config["learning"]["bank"]["local_path"]
    settings["session_root"] = config["learning"]["serving"]["session_root"]
    settings["probe_budget"] = config["learning"]["retriever"]["probe_budget"]
    settings["hosted"] = dict(config["gates"]["leeroopedia"])
    return settings
