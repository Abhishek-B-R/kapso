"""The harness reference grammar: a bundled name, a path, or a git
reference. Design: docs/research/onboarding.md section 1; the plan:
docs/plans/redesign/wp2-harness.md ("The reference grammar").

Three forms, tried in this order: a bundled name (a directory under the
package's `bundled/`), a directory that exists (used in place), a git
reference (`git+<url>`, a URL with a scheme, or the GitHub shorthand
`owner/repo` with `@rev` or `#subdirectory` present). A string with a
slash and neither `@` nor `#` is a path, and a path that does not exist
is reported as one, never tried as a repository.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from kapso.core.git_reference import (
    DEFAULT_REV,
    GitReference,
    GitReferenceError,
    is_shorthand,
    looks_like_git,
    parse_git_reference,
    shorthand_spec,
)
from kapso.harness.manifest import MANIFEST_FILE, valid_name

BUNDLED_ROOT = Path(__file__).resolve().parent / "bundled"
FORMS = (
    "  trading                                            a bundled harness, by name\n"
    "  ./harness/trading                                  a directory, used in place\n"
    "  git+https://github.com/acme/harnesses@v3#trading   a git repository, a revision, a subdirectory\n"
    "  acme/harnesses@v3#trading                          the same, GitHub shorthand (owner/repo with @rev or #subdirectory)"
)


class HarnessReferenceError(ValueError):
    """A reference that matches no form, or names nothing."""


@dataclass(frozen=True)
class HarnessReference:
    raw: str
    kind: str                       # "bundled" | "path" | "git"
    path: Optional[Path] = None     # bundled: the directory under the bundled root; path: the absolute directory
    url: Optional[str] = None       # git: the clone URL
    rev: str = DEFAULT_REV          # git: a tag, a branch or a sha, as written
    subdirectory: str = ""          # git: the harness inside the repository

    @property
    def slug(self) -> str:
        """`<host>-<owner>-<repo>`, the store directory's stem for a git
        reference; `local` stands for a host-less (file) URL."""
        return GitReference(url=self.url or "", rev=self.rev, subdirectory=self.subdirectory).slug

    def describe(self) -> str:
        if self.kind == "git":
            return GitReference(url=self.url or "", rev=self.rev, subdirectory=self.subdirectory).describe()
        return str(self.path)


def parse_reference(text: str, *, cwd: Optional[Path] = None, bundled_root: Path = BUNDLED_ROOT) -> HarnessReference:
    raw = text.strip()
    if not raw:
        raise HarnessReferenceError(f"an empty harness reference; the forms are:\n{FORMS}")
    if looks_like_git(raw):
        return _git(raw, raw[4:] if raw.startswith("git+") else raw)
    if valid_name(raw) and (bundled_root / raw / MANIFEST_FILE).is_file():
        return HarnessReference(raw=raw, kind="bundled", path=bundled_root / raw)
    base = Path(cwd) if cwd is not None else Path.cwd()
    candidate = Path(raw).expanduser()
    directory = (candidate if candidate.is_absolute() else base / candidate).resolve()
    if directory.is_dir():
        return HarnessReference(raw=raw, kind="path", path=directory)
    if ("@" in raw or "#" in raw) and is_shorthand(raw):
        return _git(raw, shorthand_spec(raw))
    if valid_name(raw):
        raise HarnessReferenceError(
            f"no bundled harness named `{raw}` and no directory {directory}; the forms are:\n{FORMS}"
        )
    raise HarnessReferenceError(
        f"no directory {directory} (and `{raw}` is not a bundled name or a git reference); the forms are:\n{FORMS}"
    )


def _git(raw: str, spec: str) -> HarnessReference:
    """`<url>[@rev][#subdirectory]`, by the shared grammar."""
    if not spec.strip():
        raise HarnessReferenceError(f"`{raw}` is not a git reference; the forms are:\n{FORMS}")
    parsed = _parsed(raw, spec)
    return HarnessReference(raw=raw, kind="git", url=parsed.url, rev=parsed.rev, subdirectory=parsed.subdirectory)


def _parsed(raw: str, spec: str) -> GitReference:
    """The shared parser's own error, in this grammar's words."""
    if spec.rstrip("#") == "" or spec.endswith("@"):
        raise HarnessReferenceError(f"`{raw}` is not a git reference; the forms are:\n{FORMS}")
    return parse_git_reference(spec)
