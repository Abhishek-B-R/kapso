"""The experience reference grammar: `mine`, `leeroopedia`, a bank path, a
bank git reference, or the name of an ingested index. Design:
docs/research/onboarding.md section 2; the plan:
docs/plans/redesign/wp3-experience.md ("The reference").

Five forms, tried in this order: the two reserved names; a path that
exists (used in place); a string with a scheme, `git+`, an `@` or a `#`,
or an `owner/repo` shorthand, as a git reference; an index name that
exists under the indexes home. A string that matches none lists the
forms; loading never ingests and never creates.
"""

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from kapso.core.git_reference import (
    DEFAULT_REV,
    GitReference,
    is_shorthand,
    looks_like_git,
    parse_git_reference,
    shorthand_spec,
)

MINE = "mine"
HOSTED = "leeroopedia"
RESERVED = (MINE, HOSTED)
INDEX_RECORD = "index.json"
FORMS = (
    "  mine                                          your own bank, the one learn() writes\n"
    "  leeroopedia                                   the hosted gate, with its key in .env\n"
    "  ./bank.git  ~/team/bank.git                   a bank home, used in place\n"
    "  acme/kapso-bank  acme/kapso-bank@v2           a bank repository you read, GitHub shorthand\n"
    "  git+https://github.com/acme/kapso-bank@main   the same, any git URL\n"
    "  org-x                                         an index ingested under that name (kapso experience add --name org-x)"
)
_NAME = re.compile(r"^[a-z0-9][a-z0-9-]*$")


class ExperienceReferenceError(ValueError):
    """A reference that matches no form, or names nothing that exists."""


@dataclass(frozen=True)
class ExperienceReference:
    raw: str
    kind: str                       # "mine" | "hosted" | "path" | "git" | "index"
    path: Optional[Path] = None     # path: the bank home; index: its directory
    url: Optional[str] = None       # git: the clone URL
    rev: str = DEFAULT_REV          # git: a tag, a branch or a sha, as written
    name: Optional[str] = None      # index: the name

    @property
    def slug(self) -> str:
        return GitReference(url=self.url or "", rev=self.rev).slug

    def describe(self) -> str:
        if self.kind == "git":
            return GitReference(url=self.url or "", rev=self.rev).describe()
        if self.kind in ("path", "index"):
            return str(self.path)
        return self.raw


def valid_index_name(name: str) -> bool:
    return bool(_NAME.match(name))


def parse_experience_reference(
    text: str, *, indexes_root: Path, cwd: Optional[Path] = None,
) -> ExperienceReference:
    raw = text.strip()
    if not raw:
        raise ExperienceReferenceError(f"an empty experience reference; the forms are:\n{FORMS}")
    if raw in RESERVED:
        return ExperienceReference(raw=raw, kind=raw if raw == MINE else "hosted")
    base = Path(cwd) if cwd is not None else Path.cwd()
    candidate = Path(raw).expanduser()
    directory = (candidate if candidate.is_absolute() else base / candidate).resolve()
    if directory.is_dir():
        return ExperienceReference(raw=raw, kind="path", path=directory)
    if looks_like_git(raw):
        parsed = parse_git_reference(raw[4:] if raw.startswith("git+") else raw)
        return ExperienceReference(raw=raw, kind="git", url=parsed.url, rev=parsed.rev)
    if is_shorthand(raw) or ("/" in raw and ("@" in raw or "#" in raw)):
        parsed = parse_git_reference(shorthand_spec(raw))
        return ExperienceReference(raw=raw, kind="git", url=parsed.url, rev=parsed.rev)
    index = Path(indexes_root).expanduser() / raw
    if valid_index_name(raw) and (index / INDEX_RECORD).is_file():
        return ExperienceReference(raw=raw, kind="index", path=index, name=raw)
    if valid_index_name(raw):
        raise ExperienceReferenceError(
            f"`{raw}` is not a reserved name, a directory, a git reference, or an index under {indexes_root} "
            f"(`kapso experience add --repo <url> --name {raw}` ingests one; `kapso experience list` shows what "
            f"exists); the forms are:\n{FORMS}"
        )
    raise ExperienceReferenceError(
        f"no directory {directory}, and `{raw}` is not a reserved name, a git reference or an index name; "
        f"the forms are:\n{FORMS}"
    )
