"""Every paid session reaches the ledger when it ends, whatever comes after.

The campaign tests run the real orchestrator over the real GenericSearch, the
real run_implementation and the real difficulties fallback, with only the agent
faked. Each fake session charges the shared Bill, so the ledger is compared with
what was actually charged. A process slice is a new orchestrator.
"""

from pathlib import Path
from types import SimpleNamespace
from typing import Optional

import pytest

import kapso.execution.coding_agents.factory as factory_module
import kapso.gated_mcp as gated_mcp_module
from kapso.core.roles import SessionRole
from kapso.execution.experiment_workspace.experiment_session import SessionPushError
from kapso.execution.inbox import file_requests, record_reply
from kapso.execution.memories.repo_memory import RepoMemoryManager
from kapso.execution.search_strategies.generic.implementation import (
    ContinuationFailed,
    run_implementation,
)

from test_campaign_spend_durability import (
    ENTRY,
    FEEDBACK_USD,
    IDEATION_USD,
    Campaign,
)
from implementation_support import MCP_TOOL, FakeWorkspace, no_staging

IMPLEMENTATION_ROLE = SessionRole(
    name="implementation",
    cli="claude_code",
    model="the-model",
    effort=None,
    timeout=600,
    settings={"auth_mode": "oauth"},
    web=False,
)
BUILD_USD = 0.5
CONTINUATION_USD = 0.3
DIFFICULTIES_USD = 0.15


class RealBuildCampaign(Campaign):
    """Campaign whose build goes through the real run_implementation."""

    def __init__(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        super().__init__(tmp_path, monkeypatch)
        self.tmp_path = tmp_path
        self.resume_succeeds = True
        self.push_error: Optional[str] = None
        campaign = self

        class FakeAgent:
            def __init__(self, config):
                self.cost = 0.0
                # The difficulties fallback is the read-and-bash session.
                self.reconstructs = config.agent_specific.get("allowed_tools") == [
                    "Read",
                    "Bash",
                ]

            def initialize(self, workspace):
                pass

            def _result(self, success=True, **metadata):
                return SimpleNamespace(
                    success=success,
                    output="the build's report" if success else "",
                    error=None if success else "the CLI could not resume",
                    metadata={"tool_calls": [], **metadata},
                )

            def generate_code(self, prompt):
                if self.reconstructs:
                    self.cost = campaign.bill.charge(DIFFICULTIES_USD)["cost_usd"]
                    return self._result()
                self.cost = campaign.bill.charge(BUILD_USD)["cost_usd"]
                if campaign.ask_on_node is None:
                    return self._result()
                ((request_id, _),) = file_requests(
                    campaign.inbox, node=0, session="sid", entries=[ENTRY]
                )
                campaign.ask_on_node = None
                return self._result(
                    stopped_for_inbox=True,
                    inbox_request_ids=[request_id],
                    cli_session_id="cli-1",
                )

            def resume(self, cli_session_id, prompt):
                self.cost = campaign.bill.charge(CONTINUATION_USD)["cost_usd"]
                return self._result(success=campaign.resume_succeeds)

            def get_cumulative_cost(self):
                return self.cost

            def cleanup(self):
                pass

        monkeypatch.setattr(
            factory_module.CodingAgentFactory,
            "create",
            classmethod(lambda cls, config: FakeAgent(config)),
        )
        monkeypatch.setattr(
            gated_mcp_module, "get_mcp_config", lambda **kw: ({}, [MCP_TOOL])
        )
        monkeypatch.setattr(
            RepoMemoryManager,
            "ensure_exists_in_worktree",
            classmethod(lambda cls, folder: {}),
        )
        monkeypatch.setattr(
            RepoMemoryManager,
            "render_summary_and_toc",
            classmethod(lambda cls, doc, max_chars=2500: "memory"),
        )

    def _strategy(self):
        strategy = super()._strategy()
        strategy.__dict__.update(
            implementation_role=IMPLEMENTATION_ROLE,
            env_strip=[],
            stage_harness_for=no_staging,
            _finishing_deadline=lambda *args, **kwargs: (60, None),
            _session_stream_path=lambda branch: str(self.tmp_path / f"{branch}.jsonl"),
        )
        del strategy.__dict__["_ensure_technical_difficulties"]
        return strategy

    def _implement(self, **kwargs):
        branch_name = kwargs["branch_name"]
        if branch_name not in {head.name for head in self.repo.heads}:
            self.repo.create_head(branch_name)
        campaign = self

        class Workspace(FakeWorkspace):
            def create_experiment_session(
                self, branch_name, parent_branch_name, llm=None, continue_branch=False
            ):
                return super().create_experiment_session(
                    branch_name, parent_branch_name, llm
                )

            def finalize_session(self, session):
                if campaign.push_error:
                    raise SessionPushError(campaign.push_error)

        strategy = self.orchestrator.search_strategy
        continuation = kwargs.get("continuation")
        return run_implementation(
            stage_harness_for=no_staging,
            solution=kwargs["solution"],
            problem=kwargs["problem"],
            branch_name=branch_name,
            parent_branch_name=kwargs["parent_branch_name"],
            ideation_repo_memory_sections_consulted=None,
            lane_index=0,
            workspace=Workspace(str(self.tmp_path)),
            llm=None,
            registered_evaluation_manifest=None,
            sync_registered_evaluation=lambda folder: None,
            implementation_gates=["repo_memory"],
            gate_failure_policy="skip",
            implementation_role=IMPLEMENTATION_ROLE,
            implementation_fallback_model=None,
            env_strip=[],
            env_defaults={},
            lane_env=None,
            clamped_timeout=lambda seconds: seconds,
            session_stream_path=lambda branch: str(self.tmp_path / f"{branch}.jsonl"),
            build_prompt=lambda **kw: "the prompt",
            previous_errors_text="",
            lane_brief="",
            note_session_started=lambda: None,
            note_session_end_facts=lambda facts: None,
            note_session_spend=lambda telemetry: strategy._note_session_spend(
                kwargs["node_id"], telemetry, continued=continuation is not None
            ),
            await_registered_evaluation=lambda output: None,
            node_id=kwargs["node_id"],
            continuation=continuation,
        )


@pytest.fixture
def campaign(tmp_path, monkeypatch) -> RealBuildCampaign:
    return RealBuildCampaign(tmp_path, monkeypatch)


def _paused_on_the_inbox(campaign: RealBuildCampaign) -> None:
    campaign.inbox_enabled = True
    campaign.ask_on_node = 0
    assert campaign.open().solve(experiment_max_iter=1).stopped_reason == (
        "waiting_for_user"
    )
    record_reply(campaign.inbox, 1, "added the key")


def test_a_failed_continuation_stays_on_the_ledger(campaign):
    _paused_on_the_inbox(campaign)
    campaign.resume_succeeds = False

    with pytest.raises(ContinuationFailed):
        campaign.open(resume=True).solve(experiment_max_iter=1)

    assert campaign.bill.total == pytest.approx(
        IDEATION_USD + BUILD_USD + CONTINUATION_USD
    )
    assert campaign.checkpoint().cumulative_cost == pytest.approx(campaign.bill.total)

    # The retry is paid for too, and nothing is counted twice.
    campaign.resume_succeeds = True
    result = campaign.open(resume=True).solve(experiment_max_iter=1)
    assert campaign.bill.total == pytest.approx(
        IDEATION_USD
        + BUILD_USD
        + 2 * CONTINUATION_USD
        + DIFFICULTIES_USD
        + FEEDBACK_USD
    )
    assert result.total_cost == pytest.approx(campaign.bill.total)
    assert campaign.checkpoint().cumulative_cost == pytest.approx(campaign.bill.total)


def test_failed_continuations_count_against_the_cost_budget(campaign):
    _paused_on_the_inbox(campaign)
    campaign.resume_succeeds = False
    for _ in range(2):
        with pytest.raises(ContinuationFailed):
            campaign.open(resume=True).solve(experiment_max_iter=1)
    campaign.resume_succeeds = True
    paid = campaign.bill.total

    # The two failures alone spent the budget, so nothing more is bought.
    result = campaign.open(resume=True).solve(experiment_max_iter=5, cost_budget=paid)

    assert result.stopped_reason == "budget_exhausted"
    assert result.iterations_run == 0
    assert campaign.bill.total == pytest.approx(paid)


def test_a_continuation_whose_push_fails_stays_on_the_ledger(campaign):
    _paused_on_the_inbox(campaign)
    campaign.push_error = "origin rejected the push"

    with pytest.raises(SessionPushError):
        campaign.open(resume=True).solve(experiment_max_iter=1)

    assert campaign.bill.total == pytest.approx(
        IDEATION_USD + BUILD_USD + CONTINUATION_USD
    )
    assert campaign.checkpoint().cumulative_cost == pytest.approx(campaign.bill.total)


def test_a_continuation_counts_once(campaign):
    _paused_on_the_inbox(campaign)

    campaign.open(resume=True).solve(experiment_max_iter=1)

    node = campaign.orchestrator.search_strategy.node_history[0]
    assert node.phase_telemetry["implementation"]["cost_usd"] == pytest.approx(
        BUILD_USD + CONTINUATION_USD
    )
    assert campaign.checkpoint().cost_by_component["implementation"] == pytest.approx(
        BUILD_USD + CONTINUATION_USD
    )


def test_the_difficulties_fallback_is_on_the_ledger(campaign):
    result = campaign.open().solve(experiment_max_iter=1)

    assert campaign.bill.total == pytest.approx(
        IDEATION_USD + BUILD_USD + DIFFICULTIES_USD + FEEDBACK_USD
    )
    assert result.total_cost == pytest.approx(campaign.bill.total)
    stored = campaign.checkpoint()
    assert stored.cumulative_cost == pytest.approx(campaign.bill.total)
    assert stored.cost_by_component["technical_difficulties"] == pytest.approx(
        DIFFICULTIES_USD
    )
    node = campaign.orchestrator.search_strategy.node_history[0]
    assert node.cost_usd == pytest.approx(campaign.bill.total)


def test_the_difficulties_fallback_counts_against_the_cost_budget(campaign):
    budget = IDEATION_USD + BUILD_USD + FEEDBACK_USD + DIFFICULTIES_USD / 2

    result = campaign.open().solve(experiment_max_iter=3, cost_budget=budget)

    assert result.stop_detail == "cost_budget"
    assert result.iterations_run == 1
