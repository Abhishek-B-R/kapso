"""Git-native bank sharing: the bank home's `origin` remote IS the share
target. No remote in config — a bank carries its own, exactly like any
git repo, and `kapso experience share <url>` is how one gets attached.

All subprocess calls run with GIT_TERMINAL_PROMPT=0 so a missing
credential fails loudly in seconds instead of hanging on a prompt."""

import os
import subprocess
from pathlib import Path
from typing import Optional


def _git_env() -> dict:
    env = dict(os.environ)
    env["GIT_TERMINAL_PROMPT"] = "0"
    return env


def bank_origin(home: Path) -> Optional[str]:
    """The bank's `origin` URL, or None when no remote is attached (the
    documented local-only state)."""
    result = subprocess.run(
        ["git", "--git-dir", str(home), "remote", "get-url", "origin"],
        capture_output=True, text=True, env=_git_env(),
    )
    if result.returncode != 0:
        return None
    return result.stdout.strip()


def bank_remote_error(home: Path, url: str) -> Optional[str]:
    """git's own failure text when `url` is not reachable with the
    caller's credentials; None when it is. The URL is probed directly, so
    a remote can be checked before it is attached."""
    result = subprocess.run(
        ["git", "--git-dir", str(home), "ls-remote", url],
        capture_output=True, text=True, env=_git_env(), timeout=60,
    )
    if result.returncode != 0:
        return result.stderr.strip()
    return None


def connect_bank(home: Path, url: str) -> None:
    """Attach `url` as the bank's origin and push the current bank there.
    Validates reachability before touching anything; the push is plain
    (no force) — a remote with unrelated history is rejected loudly."""
    error = bank_remote_error(home, url)
    if error:
        raise RuntimeError(
            f"bank remote {url} is not reachable with your git "
            f"credentials:\n{error}\n"
            "The bank's origin was left as it was. Fix access (ssh key / "
            "gh auth / credential helper) or the URL, then connect again."
        )
    subcommand = "set-url" if bank_origin(home) else "add"
    subprocess.run(
        ["git", "--git-dir", str(home), "remote", subcommand, "origin", url],
        check=True, env=_git_env(),
    )
    subprocess.run(
        ["git", "--git-dir", str(home), "push", "origin", "main", "--tags"],
        check=True, env=_git_env(),
    )
