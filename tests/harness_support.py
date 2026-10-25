"""Support for the harness tests that drive the real orchestrator: a fake
strategy that scores one candidate per run on a real branch and stages a
harness exactly as the real one does, a fake inference backend, and the
patches that keep the engine's sessions out of a test."""

from pathlib import Path
from typing import Any, Dict, List, Optional

import git

import kapso.execution.orchestrator as orchestrator_module
import kapso.kapso as kapso_module
from kapso.execution.coding_agents.base import CodingResult
from kapso.execution.observability import BuildStatus
from kapso.execution.orchestrator import OrchestratorAgent
from kapso.execution.search_strategies.base import SearchNode
from kapso.harness.staging import host_for, no_harness, stage_harness

FAKE_MODE_CONFIG = {"search_strategy": {"type": "generic", "params": {}}, "inbox": {"enabled": False}}


class FakeLLM:
    def __init__(self, *args, **kwargs):
        pass

    def get_cumulative_cost(self) -> float:
        return 0.0

    def create_embedding(self, text, model=None):
        return []


class FakeWorkspace:
    def __init__(self, workspace_dir: str):
        self.workspace_dir = workspace_dir

    def get_cumulative_cost(self) -> float:
        return 0.0


class ScoringFakeStrategy:
    """One scored candidate per run, on a real branch of the workspace;
    stages the harness the way the real strategy does."""

    implementation_cli = "claude_code"
    implementation_model = "test-model"
    _claude_auth_settings: Dict[str, Any] = {}
    env_strip: List[str] = []
    env_defaults: Dict[str, str] = {}
    session_effort = None
    gate_failure_policy = "warn"
    inbox_settings: Optional[Dict[str, Any]] = None

    def __init__(self, workspace_dir: str, harness: Any):
        self.workspace_dir = workspace_dir
        self.workspace = FakeWorkspace(workspace_dir)
        self.harness = harness
        self.iteration_count = 0
        self.node_history: List[SearchNode] = []
        self.scores_evaluator_id = ""
        self.evaluator_transition = None
        self.registered_evaluator_id = ""
        self.operation_status = BuildStatus(
            Path(workspace_dir) / ".kapso" / "status.json", phase="setup",
            harness=harness.ref_dict() if harness is not None else None,
        )
        self.phases: List[str] = []

    def _status_phase(self, phase: str) -> None:
        self.phases.append(phase)
        self.operation_status.phase(phase)

    def _clamped_timeout(self, seconds: float) -> float:
        return seconds

    def stage_harness_for(self, module: str, session_dir: str, label: str, agent_type: str):
        session_id = f"ideation/iter{self.iteration_count}/{label}" if module == "ideation" else label
        if self.harness is None:
            return no_harness(module, agent_type, Path(session_dir), session_id)
        return stage_harness(
            self.harness, module, session_dir=Path(session_dir), campaign_dir=Path(self.workspace_dir),
            session_id=session_id, host=host_for(agent_type),
        )

    def run(self, context: str, budget_progress: float = 0.0) -> SearchNode:
        node_id = len(self.node_history)
        branch = f"generic_exp_{node_id}"
        repo = git.Repo(self.workspace_dir)
        if branch not in {head.name for head in repo.heads}:
            repo.create_head(branch)
        node = SearchNode(node_id=node_id, branch_name=branch, solution="# idea\n", score=0.5 + node_id / 10, feedback="fine")
        self.node_history.append(node)
        self.iteration_count += 1
        return node

    def waiting_requests(self):
        return []

    def observe_budget(self, snapshot: Any) -> None:
        pass

    def observe_fidelity(self, decision: Any) -> None:
        pass

    def get_experiment_history(self, best_last: bool = False) -> List[SearchNode]:
        return list(self.node_history)

    def get_best_experiment(self) -> Optional[SearchNode]:
        return max(self.node_history, key=lambda n: n.score or 0.0) if self.node_history else None

    def get_deliverable_experiment(self) -> Optional[SearchNode]:
        return self.get_best_experiment()

    def get_deliverable_score(self) -> Optional[float]:
        best = self.get_best_experiment()
        return best.score if best else None

    def checkout_to_best_experiment_branch(self) -> Optional[str]:
        best = self.get_best_experiment()
        if best is None:
            return None
        git.Repo(self.workspace_dir).git.checkout(best.branch_name)
        return best.branch_name

    def dump_state(self) -> Dict[str, Any]:
        return {"node_history": [node.to_dict() for node in self.node_history]}

    def load_state(self, state: Dict[str, Any]) -> None:
        self.node_history = [SearchNode.from_dict(item) for item in state.get("node_history", [])]


class NoopAgent:
    """A coding-agent session that does nothing and succeeds: what the
    orchestrator's own sessions (the harness setup) run as in tests that
    are not about them."""

    def __init__(self, config):
        self.config = config

    def initialize(self, workspace: str) -> None:
        pass

    def generate_code(self, prompt: str, debug_mode: bool = False, timeout_seconds=None) -> CodingResult:
        return CodingResult(success=True, output="")

    def get_cumulative_cost(self) -> float:
        return 0.0

    def cleanup(self) -> None:
        pass


def patch_engine(monkeypatch, *, inbox: Optional[Dict[str, Any]] = None) -> List[ScoringFakeStrategy]:
    """The real orchestrator with its sessions stubbed, the facade's inbox
    registry off, no preflight; returns the strategies it creates. A
    strategy-level inbox block (path, stop_grace_seconds) makes the
    strategy report the inbox on, without the facade's registry. The
    orchestrator's own session (harness setup) runs as a NoopAgent; a test
    about it patches the factory again after this."""
    monkeypatch.setattr(orchestrator_module.CodingAgentFactory, "create", staticmethod(lambda config: NoopAgent(config)))
    monkeypatch.setattr(orchestrator_module, "CliInference", FakeLLM)
    monkeypatch.setattr(orchestrator_module, "load_mode_config", lambda *a, **k: dict(FAKE_MODE_CONFIG))
    monkeypatch.setattr(kapso_module, "load_mode_config", lambda *a, **k: dict(FAKE_MODE_CONFIG))
    monkeypatch.setattr(kapso_module, "run_preflight", lambda *a, **k: None)
    monkeypatch.setattr(OrchestratorAgent, "_create_feedback_generator", lambda self, coding_agent=None: object())
    strategies: List[ScoringFakeStrategy] = []

    def create_strategy(self, coding_agent, workspace_dir, start_from_checkpoint):
        strategy = ScoringFakeStrategy(workspace_dir, self.harness)
        if inbox is not None:
            strategy.inbox_settings = dict(inbox)
        strategies.append(strategy)
        return strategy

    monkeypatch.setattr(OrchestratorAgent, "_create_search_strategy", create_strategy)
    return strategies
