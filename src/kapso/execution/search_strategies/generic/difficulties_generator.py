"""Fallback technical-difficulties generator.

The implementor is the primary author of ``<technical_difficulties>``
(its output contract). When a session crashed, was deadline-killed, or
simply omitted the tag, this module reconstructs the report post-hoc: a
short read-only session on the implementation role's host over the
implementor's persisted stream artifact and the workspace, emitting the
same tag.

The trigger is purely mechanical — the field is missing — never score-
or outcome-based.
"""

import os
import re

from kapso.core.prompt_loader import load_prompt, render_prompt
from kapso.execution.coding_agents.factory import CodingAgentFactory
from kapso.core.roles import SessionRole

_TAG_PATTERN = re.compile(
    r"<technical_difficulties>\s*(.*?)\s*</technical_difficulties>",
    re.DOTALL,
)


def generate_technical_difficulties(
    role: SessionRole,
    env_strip: list,
    timeout_seconds,
    workspace_dir: str,
    solution: str,
    stream_artifact_path: str,
) -> str:
    """Reconstruct the technical-difficulties report for one session.

    Returns the report text ("" if the fallback session itself failed —
    the node then carries an empty field, which downstream extraction
    treats as "(none reported)").
    """
    template = load_prompt(
        "execution/search_strategies/generic/prompts/difficulties_fallback.md"
    )
    prompt = render_prompt(
        template,
        {
            "solution": solution,
            "stream_artifact_path": (
                stream_artifact_path
                if os.path.isfile(stream_artifact_path)
                else "(no stream artifact was persisted)"
            ),
        },
    )

    config = CodingAgentFactory.session_config(role, {
        "env_strip": env_strip,
        "allowed_tools": ["Read", "Bash"],
        "sandbox": "read-only",
        "timeout": timeout_seconds,
        "streaming": True,
        "planning_mode": False,
    })
    agent = CodingAgentFactory.create(config)
    agent.initialize(workspace_dir)
    result = agent.generate_code(prompt)
    agent.cleanup()

    if not result.success or not result.output:
        return ""
    match = _TAG_PATTERN.search(result.output)
    if match:
        return match.group(1).strip()
    return result.output.strip()
