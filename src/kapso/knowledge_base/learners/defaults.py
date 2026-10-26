"""Learner session settings for direct construction (tests, the module CLI).

`add_experience()` threads the live config's `learner.ingestor` / `learner.merger`
blocks into the learners. When a learner is built directly with partial params, the
missing keys come from the packaged config — the single source (Rule 1) — so a
default change can never leave the code and the config out of step.
"""

from typing import Any, Dict

from kapso.core.config import load_config


def learner_defaults(role: str) -> Dict[str, Any]:
    """The packaged `learner.<role>` block ("ingestor" or "merger")."""
    return dict(load_config()["learner"][role])
