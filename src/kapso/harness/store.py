"""The harness store: fetched git references under the config's
`harness.store`, one clone per `<slug>@<rev>`, with `source.json`
recording the remote, the revision as written and the resolved commit.
A path reference is never copied; a bundled name lives in the package.
Design: docs/research/onboarding.md section 1.
"""

import json
import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Tuple

import git

from kapso.harness.manifest import MANIFEST_FILE, inspect_manifest
from kapso.harness.reference import DEFAULT_REV, HarnessReference, HarnessReferenceError

SOURCE_FILE = "source.json"
_SHA = frozenset("0123456789abcdef")


@dataclass(frozen=True)
class FetchedHarness:
    """One harness inside a fetched clone, as `kapso harness list` shows it."""
    path: Path
    name: str
    version: str
    reference: str        # the reference that fetches it: <remote>@<rev>#<subdirectory>
    commit: str


class HarnessStore:
    def __init__(self, root: Path):
        self.root = Path(root).expanduser()

    def clone_dir(self, reference: HarnessReference) -> Path:
        return self.root / f"{reference.slug}@{reference.rev.replace('/', '-')}"

    def is_fetched(self, reference: HarnessReference) -> bool:
        return (self.clone_dir(reference) / SOURCE_FILE).is_file()

    def resolve(self, reference: HarnessReference) -> Path:
        """The directory a reference names; a git reference is fetched the
        first time and used from the store afterwards."""
        if reference.kind != "git":
            return reference.path
        clone = self.clone_dir(reference)
        if not self.is_fetched(reference):
            self.fetch(reference)
        harness = clone / reference.subdirectory if reference.subdirectory else clone
        if not (harness / MANIFEST_FILE).is_file():
            raise HarnessReferenceError(
                f"{reference.raw}: no {MANIFEST_FILE} at `{reference.subdirectory or '.'}` in the repository "
                f"(fetched to {clone}); name the harness's subdirectory with #<subdirectory>"
            )
        return harness

    def fetch(self, reference: HarnessReference) -> Path:
        """Clone the remote at the revision into the store, replacing a
        previous clone of the same reference."""
        if reference.kind != "git":
            raise HarnessReferenceError(f"{reference.raw} is not a git reference; nothing to fetch")
        clone = self.clone_dir(reference)
        if clone.exists():
            shutil.rmtree(clone)
        clone.parent.mkdir(parents=True, exist_ok=True)
        repo = git.Repo.clone_from(reference.url, clone)
        if reference.rev != DEFAULT_REV:
            repo.git.checkout(reference.rev)
        (clone / SOURCE_FILE).write_text(json.dumps({
            "remote": reference.url,
            "rev": reference.rev,
            "commit": repo.head.commit.hexsha,
            "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        }, indent=2) + "\n", encoding="utf-8")
        return clone

    def update(self, reference: HarnessReference) -> Tuple[str, str]:
        """Re-fetch a branch or HEAD reference; a tag or a commit is what it
        is. Returns the commit before and after."""
        clone = self.clone_dir(reference)
        if not self.is_fetched(reference):
            raise HarnessReferenceError(f"{reference.raw} was never fetched; `kapso harness add` it first")
        before = json.loads((clone / SOURCE_FILE).read_text(encoding="utf-8"))["commit"]
        if self.rev_is_pinned(reference, clone):
            return before, before
        self.fetch(reference)
        after = json.loads((clone / SOURCE_FILE).read_text(encoding="utf-8"))["commit"]
        return before, after

    def rev_is_pinned(self, reference: HarnessReference, clone: Path) -> bool:
        """A tag or a commit sha never moves; a branch or HEAD does."""
        rev = reference.rev
        if rev == DEFAULT_REV:
            return False
        repo = git.Repo(clone)
        if repo.git.ls_remote("--tags", "origin", rev).strip():
            return True
        head = repo.head.commit.hexsha
        return len(rev) >= 7 and set(rev.lower()) <= _SHA and head.startswith(rev.lower())

    def remove(self, reference: HarnessReference) -> Path:
        """Delete one fetched clone, every harness it holds."""
        if reference.kind != "git":
            raise HarnessReferenceError(
                f"{reference.raw} is a local path; nothing was fetched, and the directory is yours to keep"
            )
        clone = self.clone_dir(reference)
        if not clone.exists():
            raise HarnessReferenceError(f"nothing fetched for {reference.raw} (looked at {clone})")
        shutil.rmtree(clone)
        return clone

    def entries(self) -> List[FetchedHarness]:
        """Every harness in every fetched clone, by clone then path."""
        found: List[FetchedHarness] = []
        if not self.root.is_dir():
            return found
        for clone in sorted(p for p in self.root.iterdir() if (p / SOURCE_FILE).is_file()):
            source = json.loads((clone / SOURCE_FILE).read_text(encoding="utf-8"))
            for manifest_file in sorted(clone.rglob(MANIFEST_FILE)):
                if ".git" in manifest_file.relative_to(clone).parts:
                    continue
                harness = manifest_file.parent
                # A manifest with findings still lists, by its directory;
                # `check` says what is wrong with it.
                manifest, _findings = inspect_manifest(harness)
                subdirectory = harness.relative_to(clone).as_posix()
                reference = f"{source['remote']}@{source['rev']}"
                if subdirectory != ".":
                    reference += f"#{subdirectory}"
                found.append(FetchedHarness(
                    path=harness,
                    name=manifest.name if manifest is not None else harness.name,
                    version=manifest.version if manifest is not None else "?",
                    reference=reference, commit=source["commit"],
                ))
        return found
