"""One git reference grammar for the two stores (harnesses and banks):
`<url>[@rev][#subdirectory]`, where the URL is `git+<url>`, a URL with a
scheme, an scp-like `git@host:owner/repo`, or the GitHub shorthand
`owner/repo`. The rev's `@` is the last one after the authority, so a user
part (`git@host`, `ssh://git@host`) is left alone and a rev may hold a
slash."""

import re
from dataclasses import dataclass
from typing import List, Tuple
from urllib.parse import urlparse

GITHUB_URL = "https://github.com/{owner}/{repo}.git"
DEFAULT_REV = "HEAD"
SCHEMES = ("http://", "https://", "ssh://", "git://", "file://")
SHORTHAND = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
_UNSAFE = re.compile(r"[^A-Za-z0-9_.-]+")


class GitReferenceError(ValueError):
    """A string that is not a git reference."""


@dataclass(frozen=True)
class GitReference:
    url: str
    rev: str = DEFAULT_REV
    subdirectory: str = ""

    @property
    def slug(self) -> str:
        """`<host>-<owner>-<repo>`, a store directory's stem; `local`
        stands for a host-less (file) URL."""
        host, segments = host_and_segments(self.url)
        tail = [s[:-4] if s.endswith(".git") else s for s in segments[-2:]]
        return _UNSAFE.sub("-", "-".join([host or "local", *tail]))

    def describe(self) -> str:
        where = f"{self.url}@{self.rev}"
        return f"{where}#{self.subdirectory}" if self.subdirectory else where


def looks_like_git(raw: str) -> bool:
    """A URL with a scheme, `git+`, or an scp-like `user@host:path`."""
    return raw.startswith("git+") or raw.startswith(SCHEMES) or (
        ":" in raw and "@" in raw.split(":", 1)[0] and "://" not in raw
    )


def shorthand_spec(raw: str) -> str:
    """`owner/repo[@rev][#subdirectory]` as a GitHub URL with the same tail."""
    owner, repo = raw.split("@", 1)[0].split("#", 1)[0].split("/")
    return GITHUB_URL.format(owner=owner, repo=repo) + raw[len(owner) + 1 + len(repo):]


def is_shorthand(raw: str) -> bool:
    return bool(SHORTHAND.match(raw.split("@", 1)[0].split("#", 1)[0]))


def parse_git_reference(spec: str) -> GitReference:
    """`spec` without any `git+` prefix."""
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
        raise GitReferenceError(f"`{spec}` is not a git reference")
    return GitReference(url=url, rev=rev, subdirectory=subdirectory)


def host_and_segments(url: str) -> Tuple[str, List[str]]:
    if "://" in url:
        parsed = urlparse(url)
        return parsed.hostname or "", [s for s in parsed.path.split("/") if s]
    if ":" in url:   # scp-like git@host:owner/repo.git
        user_host, path = url.split(":", 1)
        host = user_host.split("@", 1)[-1]
        return host, [s for s in path.split("/") if s]
    return "", [s for s in url.split("/") if s]
