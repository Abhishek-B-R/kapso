"""Fakes for tests that drive the generic strategy's implementation session
directly (`run_implementation`): a harness-less staging, the gate tool the
fake MCP config names, and a workspace whose sessions are a folder."""

from pathlib import Path

from kapso.harness.staging import StagedHarness

MCP_TOOL = "mcp__repo_memory__get_repo_memory_summary"


def no_staging(module, session_dir, label, agent_type):
    """What a session gets without a harness: nothing (the strategy's
    stage_harness_for, for tests that call the session functions directly)."""
    return StagedHarness(module=module, host=agent_type, session_dir=Path(session_dir), session_id=label, guidance="")


class FakeSession:
    def __init__(self, folder):
        self.session_folder = folder

    def schedule_repo_memory_update(self, *, solution_spec, run_result):
        pass


class FakeWorkspace:
    def __init__(self, folder):
        self._folder = folder

    def create_experiment_session(self, branch_name, parent_branch_name, llm=None):
        return FakeSession(self._folder)

    def finalize_session(self, session):
        pass
