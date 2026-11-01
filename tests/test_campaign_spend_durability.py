"""What a campaign paid must stay on its ledger across a resume.

The harness runs the real orchestrator over the real GenericSearch with only
the paid sessions faked. Each fake session charges one Bill, the money that
actually left the account, so every test can compare the ledger with the bill
instead of with a figure worked out by hand.
"""

from pathlib import Path
from types import SimpleNamespace
from typing import Dict, Optional

import git
import pytest

import kapso.execution.orchestrator as orchestrator_module
from kapso.execution.inbox import file_requests, inbox_path, record_reply
from kapso.execution.orchestrator import OrchestratorAgent
from kapso.execution.run_checkpoint import RunCheckpointStore
from kapso.execution.search_strategies.generic.implementation import (
    SuspendedSession,
)
from kapso.execution.search_strategies.generic.strategy import GenericSearch

IDEATION_USD = 0.1
IMPLEMENTATION_USD = 0.5
FEEDBACK_USD = 0.2
ROUND_USD = IDEATION_USD + IMPLEMENTATION_USD + FEEDBACK_USD

ENTRY = {
    "kind": "env",
    "key": "env:OPENAI_API_KEY",
    "hit": "the key is missing",
    "tried": "looked in the environment",
    "fix": "add the key",
    "next_steps": "run the evaluation",
}


class Bill:
    """The money the fake sessions charged, shared by every process slice."""

    def __init__(self) -> None:
        self.total = 0.0

    def charge(self, usd: float) -> Dict[str, float]:
        self.total += usd
        return {"cost_usd": usd, "duration_seconds": 1.0}


class FakeLLM:
    def __init__(self, *args, **kwargs):
        pass

    def get_cumulative_cost(self) -> float:
        return 0.0


class FakeProblemHandler:
    honor_agent_stop = False
    maximize_scoring = True

    def get_problem_context(self) -> str:
        return "the problem"

    def deliverable_ready_reserve_seconds(self):
        return None


class FakeKnowledgeSearch:
    def close(self) -> None:
        pass


class Campaign:
    """One workspace, its bill, and the fault to inject into its sessions."""

    def __init__(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        self.workspace = tmp_path / "campaign"
        self.workspace.mkdir()
        self.repo = git.Repo.init(self.workspace)
        with self.repo.config_writer() as config:
            config.set_value("user", "name", "Spend Test")
            config.set_value("user", "email", "spend@example.com")
        self.workspace.joinpath("README.md").write_text("# Test\n")
        self.repo.git.add(["README.md"])
        self.repo.git.commit("-m", "initial")
        self.repo.git.branch("-M", "main")
        self.bill = Bill()
        self.inbox = inbox_path(self.workspace)
        self.inbox_enabled = False
        # Called inside a session, once its charge is on the bill.
        self.during_implementation = lambda node_id: None
        self.during_feedback = lambda node_id: None
        self.solutions = ["solution"]
        self.ask_on_node: Optional[int] = None
        self.orchestrator: Optional[OrchestratorAgent] = None
        monkeypatch.setattr(orchestrator_module, "CliInference", FakeLLM)
        monkeypatch.setattr(
            orchestrator_module,
            "load_mode_config",
            lambda config_path, mode: {
                "search_strategy": {"type": "generic", "params": {}}
            },
        )
        monkeypatch.setattr(
            OrchestratorAgent,
            "_create_feedback_generator",
            lambda agent, coding_agent=None: object(),
        )
        monkeypatch.setattr(
            OrchestratorAgent,
            "_create_search_strategy",
            lambda agent, coding_agent, workspace_dir, start_from_checkpoint: (
                self._strategy()
            ),
        )

    def _strategy(self) -> GenericSearch:
        strategy = GenericSearch.__new__(GenericSearch)
        strategy.__dict__.update(
            parent_policy="best",
            registered_evaluator_id="",
            registered_evaluation_manifest={},
            scores_evaluator_id="",
            evaluator_transition=None,
            fidelity_decision=None,
            problem_handler=FakeProblemHandler(),
            node_history=[],
            previous_errors=[],
            node_expansion_value=len(self.solutions),
            expansion_lane_env=None,
            iteration_count=0,
            workspace_dir=str(self.workspace),
            workspace=SimpleNamespace(
                workspace_dir=str(self.workspace),
                get_cumulative_cost=lambda: 0.0,
            ),
            inbox_settings={
                "enabled": self.inbox_enabled,
                "path": str(self.inbox),
                "stop_grace_seconds": 1,
            },
        )
        strategy._generate_solution = self._generate_solution
        strategy._implement = self._implement
        strategy._get_code_diff = lambda branch_name, parent_branch: "diff"
        strategy._extract_agent_result = lambda output: {}
        strategy.enforce_evaluation_integrity = lambda node: True
        strategy._generate_feedback = self._generate_feedback
        strategy._record_evaluation_attempt = lambda node: None
        strategy._ensure_technical_difficulties = lambda node: None
        return strategy

    def _generate_solution(self, problem, parent_branch):
        return list(self.solutions), [], self.bill.charge(IDEATION_USD)

    def _implement(self, **kwargs):
        telemetry = self.bill.charge(IMPLEMENTATION_USD)
        node_id = kwargs["node_id"]
        branch_name = kwargs["branch_name"]
        if branch_name not in {head.name for head in self.repo.heads}:
            self.repo.create_head(branch_name)
        if kwargs.get("continuation") is None and node_id == self.ask_on_node:
            ((request_id, _),) = file_requests(
                self.inbox,
                node=node_id,
                session="sid",
                entries=[ENTRY],
            )
            suspended = SuspendedSession([request_id], "cli-1")
            return "partial", telemetry, None, suspended, None
        self.during_implementation(node_id)
        return "output", telemetry, None, None, None

    def _generate_feedback(self, node):
        node.phase_telemetry["feedback"] = self.bill.charge(FEEDBACK_USD)
        node.score = 0.5
        node.feedback = "fine"
        self.during_feedback(node.node_id)
        return node

    def open(self, *, resume: bool = False) -> OrchestratorAgent:
        self.orchestrator = OrchestratorAgent(
            FakeProblemHandler(),
            workspace_dir=str(self.workspace),
            resume=resume,
            knowledge_search=FakeKnowledgeSearch(),
            goal="the goal",
        )
        return self.orchestrator

    def checkpoint(self):
        return RunCheckpointStore(str(self.workspace)).load()


@pytest.fixture
def campaign(tmp_path, monkeypatch) -> Campaign:
    return Campaign(tmp_path, monkeypatch)


def test_a_continuation_after_a_resume_is_on_the_ledger(campaign):
    campaign.inbox_enabled = True
    campaign.ask_on_node = 0
    assert campaign.open().solve(experiment_max_iter=1).stopped_reason == (
        "waiting_for_user"
    )
    assert campaign.checkpoint().cumulative_cost == pytest.approx(
        IDEATION_USD + IMPLEMENTATION_USD
    )
    record_reply(campaign.inbox, 1, "added the key")

    result = campaign.open(resume=True).solve(experiment_max_iter=1)

    # The same node took a second session and its judge after the restart.
    assert result.total_cost == pytest.approx(campaign.bill.total)
    stored = campaign.checkpoint()
    assert stored.cumulative_cost == pytest.approx(campaign.bill.total)
    assert stored.cost_by_component["implementation"] == pytest.approx(
        2 * IMPLEMENTATION_USD
    )
    assert stored.cost_by_component["feedback"] == pytest.approx(FEEDBACK_USD)


def test_a_continuation_after_a_resume_trips_the_cost_budget(campaign):
    campaign.inbox_enabled = True
    campaign.ask_on_node = 0
    campaign.open().solve(experiment_max_iter=1)
    record_reply(campaign.inbox, 1, "added the key")
    budget = IDEATION_USD + 2 * IMPLEMENTATION_USD

    result = campaign.open(resume=True).solve(experiment_max_iter=3, cost_budget=budget)

    assert result.stopped_reason == "budget_exhausted"
    assert result.stop_detail == "cost_budget"
    assert result.iterations_run == 1
    assert campaign.bill.total == pytest.approx(budget + FEEDBACK_USD)


def test_restored_nodes_are_not_charged_twice(campaign):
    campaign.open().solve(experiment_max_iter=1)

    result = campaign.open(resume=True).solve(experiment_max_iter=1)

    assert campaign.bill.total == pytest.approx(2 * ROUND_USD)
    assert result.total_cost == pytest.approx(campaign.bill.total)
