"""The content hash of a harness directory: what every record carries so a
run and a lesson name the exact harness that produced them.

sha256 over every regular file under the directory, in sorted relative
order, each as its relative path, a NUL, its bytes, a NUL; a symlink
contributes its target string instead of bytes; `.git`, `__pycache__` and
`*.pyc` are left out. Full hex; prints show the first twelve.
"""

import hashlib
from pathlib import Path
from typing import Dict

SHORT = 12
_SKIP_DIRS = {".git", "__pycache__"}
_SKIP_SUFFIXES = {".pyc"}


def harness_hash(root: Path) -> str:
    digest = hashlib.sha256()
    for relative, payload in _entries(Path(root)):
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(payload)
        digest.update(b"\0")
    return digest.hexdigest()


def harness_files(root: Path) -> Dict[str, str]:
    """Each file's own digest by its relative path: what a refusal names
    when the harness changed since it was loaded."""
    return {relative: hashlib.sha256(payload).hexdigest() for relative, payload in _entries(Path(root))}


def describe_change(recorded: Dict[str, str], current: Dict[str, str]) -> str:
    """`changed a, b; added c; removed d` between two file digests."""
    changed = sorted(path for path in recorded if path in current and recorded[path] != current[path])
    added = sorted(set(current) - set(recorded))
    removed = sorted(set(recorded) - set(current))
    return "; ".join(
        f"{label} {', '.join(paths)}"
        for label, paths in (("changed", changed), ("added", added), ("removed", removed)) if paths
    )


def short(hash_hex: str) -> str:
    return hash_hex[:SHORT]


def _entries(root: Path):
    """Every file in sorted relative order with its payload: its bytes, or
    a symlink's target."""
    for path in sorted(_files(root), key=lambda p: p.relative_to(root).as_posix()):
        payload = str(path.readlink()).encode("utf-8") if path.is_symlink() else path.read_bytes()
        yield path.relative_to(root).as_posix(), payload


def _files(root: Path):
    for path in root.rglob("*"):
        relative = path.relative_to(root)
        if any(part in _SKIP_DIRS for part in relative.parts):
            continue
        if path.suffix in _SKIP_SUFFIXES:
            continue
        if path.is_symlink() or path.is_file():
            yield path
