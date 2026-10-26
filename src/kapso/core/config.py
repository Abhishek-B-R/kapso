"""The config: two layers, resolved by one function.

The packaged `config.yaml` beside this package is the defaults, the whole
schema at its top level. A person's own file carries only what they
change and is deep-merged over it (`kapso build --config
kapso-config.yaml`, `Kapso(config=...)`): nested mappings merge key by
key, scalars and lists replace. A top-level key the packaged file does not
name is refused by name, so a stale `modes:` or a misspelled block never
does nothing silently. One key is reserved and never read by the engine:
`benchmark`, a benchmark runner's own settings. Nothing is read from the
environment. Design: docs/plans/redesign/wp4-config.md.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

PACKAGED_CONFIG_PATH = Path(__file__).resolve().parent.parent / "config.yaml"
# The benchmark runners' own settings live under this key in their
# override files; the engine never reads it.
RUNNER_KEY = "benchmark"
# The mappings whose keys are a person's to choose (a host's name, an
# inference role, a gate, a store's parameters, an environment variable):
# an override may add keys under these, and the walk checks nothing
# below them. Everywhere else the packaged mapping is the schema.
OPEN_NAMESPACES = frozenset({
    "hosts", "inference.roles", "gates", "knowledge_search.params",
    "search_strategy.params.session_env_defaults", RUNNER_KEY,
})


class ConfigError(ValueError):
    """A config file the engine refuses: its message names the file, the
    key and the keys allowed, and is written to be read alone."""


def read_yaml(path: Any) -> Dict[str, Any]:
    """One YAML mapping from disk: a missing file raises, an empty file is
    an empty mapping, anything but a mapping is refused."""
    data = yaml.safe_load(Path(path).read_text())
    if data is None:
        return {}
    if not isinstance(data, dict):
        raise ConfigError(f"{path}: a config file is a mapping, got {type(data).__name__}")
    return data


def deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    """Merge ``override`` onto ``base`` without mutating either.

    Nested dicts merge key-by-key; scalars AND lists replace wholesale.
    """
    merged = dict(base)
    for key, value in override.items():
        if isinstance(merged.get(key), dict) and isinstance(value, dict):
            merged[key] = deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def is_packaged(config_path: Optional[str]) -> bool:
    """True when ``config_path`` is the packaged defaults: None, or the
    packaged file's own path (an install naming it explicitly)."""
    return config_path is None or Path(config_path).expanduser().resolve() == PACKAGED_CONFIG_PATH


def load_config(config_path: Optional[str] = None) -> Dict[str, Any]:
    """The effective config: the packaged defaults with the override file
    at ``config_path`` merged over them. None, or the packaged path
    itself, is the defaults alone."""
    packaged = read_yaml(PACKAGED_CONFIG_PATH)
    if is_packaged(config_path):
        return packaged
    if not Path(config_path).expanduser().is_file():
        raise ConfigError(f"{config_path}: no such file")
    override = read_yaml(config_path)
    _check_keys(override, packaged, "", str(config_path))
    return deep_merge(packaged, override)


def _check_keys(override: Dict[str, Any], packaged: Dict[str, Any], path: str, source: str) -> None:
    """An override mapping may name only the keys the packaged mapping
    names at the same path, at every depth, the open namespaces apart;
    the runner's own key is allowed at the top."""
    if path in OPEN_NAMESPACES:
        return
    allowed = set(packaged) | ({RUNNER_KEY} if not path else set())
    unknown = sorted(set(override) - allowed)
    if unknown:
        where = path or "the top level"
        keys = ", ".join(sorted(packaged))
        if not path:
            keys += f" (and `{RUNNER_KEY}`, a benchmark runner's own)"
        raise ConfigError(
            f"{source}: {where}: unknown key{'s' if len(unknown) > 1 else ''} "
            f"{', '.join(unknown)}; the keys are {keys}"
        )
    for key, value in override.items():
        if isinstance(packaged.get(key), dict):
            child = f"{path}.{key}" if path else key
            if not isinstance(value, dict):
                raise ConfigError(f"{source}: {child}: must be a mapping, got {type(value).__name__}")
            _check_keys(value, packaged[key], child, source)


def override_paths(config_path: Optional[str] = None) -> List[str]:
    """The dotted paths the override file sets over the packaged defaults,
    the runner's own key left out; empty for the defaults alone."""
    if is_packaged(config_path):
        return []
    packaged = read_yaml(PACKAGED_CONFIG_PATH)
    paths: List[str] = []

    def walk(node: Dict[str, Any], base: Dict[str, Any], prefix: str) -> None:
        for key, value in node.items():
            path = f"{prefix}{key}"
            if isinstance(value, dict) and isinstance(base.get(key), dict):
                walk(value, base[key], path + ".")
            else:
                paths.append(path)

    override = read_yaml(config_path)
    walk({k: v for k, v in override.items() if k != RUNNER_KEY}, packaged, "")
    return paths
