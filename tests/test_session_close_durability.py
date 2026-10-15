"""A failed push must not cost the candidate its work (issue #131).

The session clone is the only copy of a candidate's commits until the branch
reaches origin. Closing a session must raise when the push fails and keep the
clone, and a commit that fails for a real reason must propagate instead of
being read as "nothing to commit".
"""

import shlex
import subprocess
from pathlib import Path

import git
import pytest

from kapso.execution.coding_agents.base import CodingAgentConfig
from kapso.execution.coding_agents.factory import CodingAgentFactory
from kapso.execution.experiment_workspace.experiment_session import SessionPushError
from kapso.execution.experiment_workspace.experiment_workspace import (
    ExperimentWorkspace,
)


class FakeCodingAgent:
    def initialize(self, workspace: str) -> None:
        self.workspace = workspace

    def supports_native_git(self) -> bool:
        return False

    def cleanup(self) -> None:
        pass

    def get_cumulative_cost(self) -> float:
        return 0.0


def _agent_config() -> CodingAgentConfig:
    return CodingAgentConfig(
        agent_type="fake",
        model="test-model",
        debug_model="test-model",
        agent_specific={},
    )


def _install_hook(git_dir: Path, name: str, body: str) -> Path:
    hook = git_dir / "hooks" / name
    hook.parent.mkdir(parents=True, exist_ok=True)
    hook.write_text(f"#!/bin/sh\n{body}\n")
    hook.chmod(0o755)
    return hook


@pytest.fixture
def workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> ExperimentWorkspace:
    monkeypatch.setattr(
        CodingAgentFactory,
        "create",
        classmethod(lambda cls, config: FakeCodingAgent()),
    )
    workspace = ExperimentWorkspace(
        coding_agent_config=_agent_config(),
        workspace_dir=str(tmp_path / "workspace"),
    )
    Path(workspace.workspace_dir, "README.md").write_text("# Example\n")
    workspace.repo.git.add(["README.md"])
    workspace.repo.git.commit("-m", "baseline")
    return workspace


def _candidate_session(workspace: ExperimentWorkspace):
    session = workspace.create_experiment_session(
        branch_name="candidate",
        parent_branch_name="main",
    )
    Path(session.session_folder, "candidate.txt").write_text("completed\n")
    session.repo.git.add(["candidate.txt"])
    session.repo.git.commit("-m", "feat: candidate")
    return session


def _reject_pushes(workspace: ExperimentWorkspace) -> Path:
    return _install_hook(
        Path(workspace.repo.git_dir),
        "pre-receive",
        "echo 'rejected by test hook' >&2\nexit 1",
    )


def _branch_names(workspace: ExperimentWorkspace) -> list:
    return [head.name for head in workspace.repo.heads]


def test_rejected_push_raises_and_keeps_the_candidate(workspace):
    session = _candidate_session(workspace)
    folder = Path(session.session_folder)
    _reject_pushes(workspace)

    with pytest.raises(SessionPushError) as error:
        workspace.finalize_session(session)

    message = str(error.value)
    assert str(folder) in message
    assert "rejected by test hook" in message
    assert folder.is_dir()
    assert session.repo.git.show("HEAD:candidate.txt") == "completed"
    assert "candidate" not in _branch_names(workspace)


def test_printed_recovery_command_restores_the_branch(workspace):
    session = _candidate_session(workspace)
    hook = _reject_pushes(workspace)

    with pytest.raises(SessionPushError) as error:
        workspace.finalize_session(session)

    hook.unlink()
    command = next(
        line.strip()
        for line in str(error.value).splitlines()
        if line.strip().startswith("git -C ")
    )
    subprocess.run(shlex.split(command), check=True, capture_output=True)

    assert "candidate" in _branch_names(workspace)
    assert workspace.repo.git.show("candidate:candidate.txt") == "completed"


def test_a_failing_commit_is_not_read_as_nothing_to_commit(workspace):
    session = _candidate_session(workspace)
    folder = Path(session.session_folder)
    Path(session.run_dir, "result.txt").write_text("ok\n")
    _install_hook(
        Path(session.repo.git_dir),
        "pre-commit",
        "echo 'lint failed' >&2\nexit 1",
    )

    with pytest.raises(git.GitCommandError):
        workspace.finalize_session(session)

    assert folder.is_dir()


def test_nothing_new_to_commit_still_closes_cleanly(workspace):
    session = _candidate_session(workspace)
    folder = Path(session.session_folder)
    Path(session.run_dir, "result.txt").write_text("ok\n")
    session.repo.git.add([session.run_dir])
    session.repo.git.commit("-m", "chore: run output")

    workspace.finalize_session(session)

    assert not folder.exists()
    assert "candidate" in _branch_names(workspace)
