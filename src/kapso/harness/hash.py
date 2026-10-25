"""The content hash of a harness directory: what every record carries so a
run and a lesson name the exact harness that produced them.

sha256 over every regular file under the directory, in sorted relative
order, each as its relative path, a NUL, its bytes, a NUL; a symlink
contributes its target string instead of bytes; `.git`, `__pycache__` and
`*.pyc` are left out. Full hex; prints show the first twelve.
"""

import hashlib
from pathlib import Path

SHORT = 12
_SKIP_DIRS = {".git", "__pycache__"}
_SKIP_SUFFIXES = {".pyc"}


def harness_hash(root: Path) -> str:
    root = Path(root)
    digest = hashlib.sha256()
    for path in sorted(_files(root), key=lambda p: p.relative_to(root).as_posix()):
        digest.update(path.relative_to(root).as_posix().encode("utf-8"))
        digest.update(b"\0")
        if path.is_symlink():
            digest.update(str(path.readlink()).encode("utf-8"))
        else:
            digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def short(hash_hex: str) -> str:
    return hash_hex[:SHORT]


def _files(root: Path):
    for path in root.rglob("*"):
        relative = path.relative_to(root)
        if any(part in _SKIP_DIRS for part in relative.parts):
            continue
        if path.suffix in _SKIP_SUFFIXES:
            continue
        if path.is_symlink() or path.is_file():
            yield path
