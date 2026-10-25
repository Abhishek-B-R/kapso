"""The experience homes: banks you read, fetched under `experience.banks`
(`<slug>@<rev>/` with a fetch record beside the clone, as the harness
store keeps its own), and the indexes you ingested under
`experience.indexes` (`<name>/index.json` and the pages). Your own bank
is not here: it is `learning.bank.local_path`, which `learn()` writes.
"""

import json
import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import git

from kapso.core.git_reference import DEFAULT_REV
from kapso.experience.reference import INDEX_RECORD, ExperienceReference, ExperienceReferenceError

_SHA = frozenset("0123456789abcdef")


@dataclass(frozen=True)
class IndexRecord:
    """What `add` wrote for one ingested corpus: the name, the id that
    pins it, when and from what it was made, the search backend's own
    references and the page count."""
    name: str
    id: str
    created_at: str
    source: str
    search_backend: str
    backend_refs: Dict[str, Any]
    page_count: int
    path: Path

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name, "id": self.id, "created_at": self.created_at, "source": self.source,
            "search_backend": self.search_backend, "backend_refs": self.backend_refs, "page_count": self.page_count,
        }


class ExperienceStore:
    def __init__(self, banks_root: Path, indexes_root: Path):
        self.banks_root = Path(banks_root).expanduser()
        self.indexes_root = Path(indexes_root).expanduser()

    # ------------------------------------------------------------- banks

    def clone_dir(self, reference: ExperienceReference) -> Path:
        return self.banks_root / f"{reference.slug}@{reference.rev.replace('/', '-')}"

    def record_path(self, reference: ExperienceReference) -> Path:
        clone = self.clone_dir(reference)
        return clone.with_name(clone.name + ".json")

    def is_fetched(self, reference: ExperienceReference) -> bool:
        record_file = self.record_path(reference)
        if not record_file.is_file():
            return False
        record = json.loads(record_file.read_text(encoding="utf-8"))
        if record["remote"] != reference.url or record["rev"] != reference.rev:
            raise ExperienceReferenceError(
                f"{self.clone_dir(reference)} holds {record['remote']}@{record['rev']}, fetched for another "
                f"reference that names the same directory; `kapso experience remove` is not a verb, so remove "
                f"the directory and its record by hand, or name the revision another way"
            )
        return True

    def resolve_bank(self, reference: ExperienceReference) -> Path:
        """The clone a git reference names, fetched the first time."""
        if reference.kind != "git":
            raise ExperienceReferenceError(f"{reference.raw} is not a git reference; nothing to fetch")
        if not self.is_fetched(reference):
            self.fetch(reference)
        return self.clone_dir(reference)

    def fetch(self, reference: ExperienceReference) -> Path:
        clone = self.clone_dir(reference)
        if clone.exists():
            shutil.rmtree(clone)
        if self.record_path(reference).exists():
            self.record_path(reference).unlink()
        clone.parent.mkdir(parents=True, exist_ok=True)
        repo = git.Repo.clone_from(reference.url, clone)
        if reference.rev != DEFAULT_REV:
            repo.git.checkout(reference.rev)
        self.record_path(reference).write_text(json.dumps({
            "remote": reference.url,
            "rev": reference.rev,
            "commit": repo.head.commit.hexsha,
            "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        }, indent=2) + "\n", encoding="utf-8")
        return clone

    def update(self, reference: ExperienceReference) -> Dict[str, str]:
        """Re-fetch a branch or HEAD reference; a tag or a sha is what it
        is. Returns {before, after}."""
        if not self.is_fetched(reference):
            raise ExperienceReferenceError(f"{reference.raw} was never fetched; load it once first")
        before = json.loads(self.record_path(reference).read_text(encoding="utf-8"))["commit"]
        clone = self.clone_dir(reference)
        if self.rev_is_pinned(reference, clone):
            return {"before": before, "after": before}
        self.fetch(reference)
        after = json.loads(self.record_path(reference).read_text(encoding="utf-8"))["commit"]
        return {"before": before, "after": after}

    def rev_is_pinned(self, reference: ExperienceReference, clone: Path) -> bool:
        rev = reference.rev
        if rev == DEFAULT_REV:
            return False
        repo = git.Repo(clone)
        if repo.git.ls_remote("--tags", "origin", rev).strip():
            return True
        head = repo.head.commit.hexsha
        return len(rev) >= 7 and set(rev.lower()) <= _SHA and head.startswith(rev.lower())

    def banks(self) -> List[Dict[str, Any]]:
        """Every fetched bank: its record with the clone's path."""
        found: List[Dict[str, Any]] = []
        if not self.banks_root.is_dir():
            return found
        for record_file in sorted(p for p in self.banks_root.iterdir() if p.suffix == ".json" and p.with_suffix("").is_dir()):
            record = json.loads(record_file.read_text(encoding="utf-8"))
            record["path"] = str(record_file.with_suffix(""))
            found.append(record)
        return found

    # ----------------------------------------------------------- indexes

    def index_dir(self, name: str) -> Path:
        return self.indexes_root / name

    def index_record(self, name: str) -> IndexRecord:
        file = self.index_dir(name) / INDEX_RECORD
        if not file.is_file():
            raise ExperienceReferenceError(f"no index named `{name}` under {self.indexes_root} (no {file})")
        data = json.loads(file.read_text(encoding="utf-8"))
        return IndexRecord(
            name=data["name"], id=data["id"], created_at=data["created_at"], source=data["source"],
            search_backend=data["search_backend"], backend_refs=dict(data["backend_refs"]),
            page_count=int(data["page_count"]), path=self.index_dir(name),
        )

    def write_index_record(self, record: IndexRecord) -> Path:
        directory = self.index_dir(record.name)
        directory.mkdir(parents=True, exist_ok=True)
        file = directory / INDEX_RECORD
        file.write_text(json.dumps(record.to_dict(), indent=2) + "\n", encoding="utf-8")
        return file

    def indexes(self) -> List[IndexRecord]:
        if not self.indexes_root.is_dir():
            return []
        return [
            self.index_record(p.name)
            for p in sorted(self.indexes_root.iterdir())
            if (p / INDEX_RECORD).is_file()
        ]
