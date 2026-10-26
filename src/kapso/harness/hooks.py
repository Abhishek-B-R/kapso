"""Hooks: the listed `hooks/<name>/hook.json` files merged into the one
file a host reads, in manifest order, `${PLUGIN_ROOT}` expanded in every
command. Nothing is injected into events and no script learns its
module: the manifest is the whole assignment. Design:
docs/research/harness-design.md section 5.
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Sequence

PLUGIN_ROOT = "${PLUGIN_ROOT}"
# The engine's own hooks, merged first into every harness session's file
# whenever a harness is staged, user hooks or none: their commands name
# the package's path, not the harness's. `protect-harness` denies a
# file-tool write under the harness root on both hosts (a shell write is
# not caught here; the hash check at the next staging catches it).
ENGINE_HOOKS_DIR = Path(__file__).resolve().parent / "engine_hooks"
PROTECT_HARNESS = "protect-harness"
ENGINE_HOOKS = (PROTECT_HARNESS,)


def expand_plugin_root(value: Any, root: Path) -> Any:
    """`${PLUGIN_ROOT}` → the harness directory, in every string of a
    JSON-like value."""
    if isinstance(value, str):
        return value.replace(PLUGIN_ROOT, str(root))
    if isinstance(value, list):
        return [expand_plugin_root(item, root) for item in value]
    if isinstance(value, dict):
        return {key: expand_plugin_root(item, root) for key, item in value.items()}
    return value


def engine_hooks() -> Dict[str, Any]:
    """The engine's own hooks as one `{"hooks": {<event>: [entries...]}}`,
    each command's `${PLUGIN_ROOT}` expanded to the hook's own directory."""
    merged: Dict[str, List[Any]] = {}
    for name in ENGINE_HOOKS:
        directory = ENGINE_HOOKS_DIR / name.replace("-", "_")
        data = json.loads((directory / "hook.json").read_text(encoding="utf-8"))
        for event, entries in data["hooks"].items():
            merged.setdefault(event, []).extend(expand_plugin_root(entries, directory))
    return {"hooks": merged}


def merge_hooks(root: Path, names: Sequence[str]) -> Dict[str, Any]:
    """One `{"hooks": {<event>: [entries...]}}` from the named hook
    directories, each event's entries in the order the manifest lists the
    hooks (`check` has already validated every file)."""
    merged: Dict[str, List[Any]] = {}
    for name in names:
        file = Path(root) / "hooks" / name / "hook.json"
        data = json.loads(file.read_text(encoding="utf-8"))
        for event, entries in data["hooks"].items():
            merged.setdefault(event, []).extend(expand_plugin_root(entries, root))
    return {"hooks": merged}
