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

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

from kapso.harness.manifest import MANIFEST_FILE, valid_name

BUNDLED_ROOT = Path(__file__).resolve().parent / "bundled"
GITHUB_URL = "https://github.com/{owner}/{repo}.git"
DEFAULT_REV = "HEAD"
FORMS = (
    "  trading                                            a bundled harness, by name\n"
    "  ./harness/trading                                  a directory, used in place\n"
    "  git+https://github.com/acme/harnesses@v3#trading   a git repository, a revision, a subdirectory\n"
    "  acme/harnesses@v3#trading                          the same, GitHub shorthand (owner/repo with @rev or #subdirectory)"
)
_SCHEMES = ("http://", "https://", "ssh://", "git://", "file://")
_SHORTHAND = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
_UNSAFE = re.compile(r"[^A-Za-z0-9_.-]+")


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
        host, segments = _host_and_segments(self.url or "")
        tail = [s[:-4] if s.endswith(".git") else s for s in segments[-2:]]
        return _UNSAFE.sub("-", "-".join([host or "local", *tail]))

    def describe(self) -> str:
        if self.kind == "git":
            where = f"{self.url}@{self.rev}"
            return f"{where}#{self.subdirectory}" if self.subdirectory else where
        return str(self.path)


def parse_reference(text: str, *, cwd: Optional[Path] = None, bundled_root: Path = BUNDLED_ROOT) -> HarnessReference:
    raw = text.strip()
    if not raw:
        raise HarnessReferenceError(f"an empty harness reference; the forms are:\n{FORMS}")
    if raw.startswith("git+"):
        return _git(raw, raw[4:])
    if raw.startswith(_SCHEMES) or (":" in raw and "@" in raw.split(":", 1)[0] and "://" not in raw):
        return _git(raw, raw)   # a URL with a scheme, or scp-like git@host:owner/repo
    if valid_name(raw) and (bundled_root / raw / MANIFEST_FILE).is_file():
        return HarnessReference(raw=raw, kind="bundled", path=bundled_root / raw)
    base = Path(cwd) if cwd is not None else Path.cwd()
    candidate = Path(raw).expanduser()
    directory = (candidate if candidate.is_absolute() else base / candidate).resolve()
    if directory.is_dir():
        return HarnessReference(raw=raw, kind="path", path=directory)
    if ("@" in raw or "#" in raw) and _SHORTHAND.match(raw.split("@", 1)[0].split("#", 1)[0]):
        owner, repo = raw.split("@", 1)[0].split("#", 1)[0].split("/")
        spec = GITHUB_URL.format(owner=owner, repo=repo) + raw[len(owner) + 1 + len(repo):]
        return _git(raw, spec)
    if valid_name(raw):
        raise HarnessReferenceError(
            f"no bundled harness named `{raw}` and no directory {directory}; the forms are:\n{FORMS}"
        )
    raise HarnessReferenceError(
        f"no directory {directory} (and `{raw}` is not a bundled name or a git reference); the forms are:\n{FORMS}"
    )


def _git(raw: str, spec: str) -> HarnessReference:
    """`<url>[@rev][#subdirectory]`; the rev's `@` is the last one in the
    URL's path, after the authority, so a user part (`git@host`,
    `ssh://git@host`) is left alone and a rev may hold a slash."""
    subdirectory = ""
    if "#" in spec:
        spec, subdirectory = spec.rsplit("#", 1)
        subdirectory = subdirectory.strip("/")
    if "://" in spec:
        scheme, rest = spec.split("://", 1)
        authority, slash, path = rest.partition("/")
        head = f"{scheme}://{authority}{slash}"
    elif ":" in spec and "@" in spec.split(":", 1)[0]:
        authority, colon, path = spec.partition(":")
        head = f"{authority}{colon}"
    else:
        head, path = "", spec
    rev = DEFAULT_REV
    if "@" in path:
        path, rev = path.rsplit("@", 1)
    url = head + path
    if not url or not rev:
        raise HarnessReferenceError(f"`{raw}` is not a git reference; the forms are:\n{FORMS}")
    return HarnessReference(raw=raw, kind="git", url=url, rev=rev, subdirectory=subdirectory)


def _host_and_segments(url: str):
    if "://" in url:
        parsed = urlparse(url)
        return parsed.hostname or "", [s for s in parsed.path.split("/") if s]
    if ":" in url:   # scp-like git@host:owner/repo.git
        user_host, path = url.split(":", 1)
        host = user_host.split("@", 1)[-1]
        return host, [s for s in path.split("/") if s]
    return "", [s for s in url.split("/") if s]
