"""The generic strategy's parameters for direct construction in tests: the
packaged `search_strategy.params` (the one home of every default, Rule 1)
with a test's overrides merged over them, and the packaged hosts table."""

from typing import Any, Dict

from kapso.core.config import deep_merge, load_config


def generic_params(**overrides: Any) -> Dict[str, Any]:
    """The packaged parameters with ``overrides`` deep-merged over them
    (a role block given whole replaces its keys one by one)."""
    return deep_merge(load_config()["search_strategy"]["params"], overrides)


def packaged_hosts() -> Dict[str, Dict[str, Any]]:
    return dict(load_config()["hosts"])
