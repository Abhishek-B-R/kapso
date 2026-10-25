"""A build with a harness writes one identity into the launch record, the
status file, the checkpoint and the solution record; a resume after one
byte of a page changed is refused by name with the way out; the same
content from another path proceeds; a bare resume takes the harness from
the launch record. The orchestrator, the checkpoint store and the status
writer are real; only the strategy's sessions are stubbed."""

import json
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional

import git
import pytest

import kapso.execution.orchestrator as orchestrator_module
import kapso.kapso as kapso_module
from kapso.execution.orchestrator import OrchestratorAgent
from kapso.execution.run_checkpoint import RunCheckpointIncompatibleError
from kapso.execution.search_strategies.base import SearchNode
from kapso.handles import Budget, Solution
from kapso.kapso import Kapso
from tests.handles_support import git_workspace

TRADING = Path(__file__).resolve().parent.parent / "examples" / "harnesses" / "trading"
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
    """One scored candidate per run, on a real branch of the workspace."""

    def __init__(self, workspace_dir: str, harness: Any):
        self.workspace_dir = workspace_dir
        self.workspace = FakeWorkspace(workspace_dir)
        self.harness = harness
        self.node_history: List[SearchNode] = []
        self.scores_evaluator_id = ""
        self.evaluator_transition = None
        self.registered_evaluator_id = ""

    def run(self, context: str, budget_progress: float = 0.0) -> SearchNode:
        node_id = len(self.node_history)
        branch = f"generic_exp_{node_id}"
        repo = git.Repo(self.workspace_dir)
        if branch not in {head.name for head in repo.heads}:
            repo.create_head(branch)
        node = SearchNode(node_id=node_id, branch_name=branch, solution="# idea\n", score=0.5 + node_id / 10, feedback="fine")
        self.node_history.append(node)
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


@pytest.fixture
def engine(monkeypatch, tmp_path):
    """The real orchestrator with its sessions stubbed, the inbox off, no
    preflight, and the trading harness copied where a test can edit it."""
    monkeypatch.setattr(orchestrator_module, "CliInference", FakeLLM)
    monkeypatch.setattr(orchestrator_module, "load_mode_config", lambda *a, **k: dict(FAKE_MODE_CONFIG))
    monkeypatch.setattr(kapso_module, "load_mode_config", lambda *a, **k: dict(FAKE_MODE_CONFIG))
    monkeypatch.setattr(kapso_module, "run_preflight", lambda *a, **k: None)
    monkeypatch.setattr(OrchestratorAgent, "_create_feedback_generator", lambda self, coding_agent=None: object())
    strategies: List[ScoringFakeStrategy] = []

    def create_strategy(self, coding_agent, workspace_dir, start_from_checkpoint):
        strategy = ScoringFakeStrategy(workspace_dir, self.harness)
        strategies.append(strategy)
        return strategy

    monkeypatch.setattr(OrchestratorAgent, "_create_search_strategy", create_strategy)
    harness_dir = tmp_path / "harness" / "trading"
    shutil.copytree(TRADING, harness_dir)
    workspace = tmp_path / "campaign"
    git_workspace(workspace)
    settings = dict(store=str(tmp_path / "store"))
    return workspace, harness_dir, strategies, settings


def kapso_with(harness_dir: Optional[Path], tmp_path: Path) -> Kapso:
    kapso = Kapso()
    kapso._harness_settings["store"] = str(tmp_path / "store")
    if harness_dir is not None:
        kapso.load_harness(str(harness_dir))
    return kapso


def records(workspace: Path) -> Dict[str, Any]:
    return {
        name: json.loads((workspace / ".kapso" / f"{name}.json").read_text())
        for name in ("launch", "status", "run_state", "solution")
    }


def test_one_identity_reaches_every_record(engine, tmp_path):
    workspace, harness_dir, strategies, _ = engine
    kapso = kapso_with(harness_dir, tmp_path)
    solution = kapso.build("Raise the Sharpe above 1", output=str(workspace), budget=Budget(experiments=1))

    identity = kapso.harness.ref_dict()
    assert identity["name"] == "trading" and identity["source"] == str(harness_dir.resolve())
    assert len(identity["hash"]) == 64
    written = records(workspace)
    assert written["launch"]["harness"] == identity
    assert written["status"]["harness"] == identity
    assert written["run_state"]["harness"] == identity and written["run_state"]["harness_setup"] is None
    assert written["solution"]["harness"] == identity
    assert solution.harness.hash == identity["hash"]
    assert Solution.open(workspace).harness == solution.harness
    # The strategy was handed the same handle the facade loaded.
    assert strategies[0].harness is kapso.harness


def test_a_resume_after_an_edit_is_refused_by_name_with_the_way_out(engine, tmp_path):
    workspace, harness_dir, _, _ = engine
    first = kapso_with(harness_dir, tmp_path)
    first.build("g", output=str(workspace), budget=Budget(experiments=1))
    recorded = first.harness

    page = harness_dir / "instructions" / "guardrails.md"
    page.write_text(page.read_text() + "\n- one more rule\n")
    second = kapso_with(harness_dir, tmp_path)
    assert second.harness.hash != recorded.hash
    with pytest.raises(RunCheckpointIncompatibleError) as caught:
        second.build(output=str(workspace), resume=True)
    message = str(caught.value)
    assert "the harness changed since launch" in message
    assert recorded.label() in message and second.harness.label() in message
    assert f"`git checkout` in {harness_dir.resolve()}" in message
    assert "start a new campaign with a new --output" in message


def test_the_same_content_from_another_path_resumes(engine, tmp_path):
    workspace, harness_dir, strategies, _ = engine
    kapso_with(harness_dir, tmp_path).build("g", output=str(workspace), budget=Budget(experiments=1))
    elsewhere = tmp_path / "elsewhere" / "trading"
    shutil.copytree(harness_dir, elsewhere)
    solution = kapso_with(elsewhere, tmp_path).build(output=str(workspace), resume=True, budget=Budget(experiments=1))
    assert solution.experiments_total == 2
    # The launch record keeps the original source; the solution names the one used.
    assert records(workspace)["launch"]["harness"]["source"] == str(harness_dir.resolve())
    assert solution.harness.source == str(elsewhere.resolve())


def test_a_bare_resume_takes_the_harness_from_the_launch_record(engine, tmp_path):
    workspace, harness_dir, strategies, _ = engine
    kapso_with(harness_dir, tmp_path).build("g", output=str(workspace), budget=Budget(experiments=1))
    solution = kapso_with(None, tmp_path).build(output=str(workspace), resume=True, budget=Budget(experiments=1))
    assert solution.harness.source == str(harness_dir.resolve())
    assert strategies[-1].harness is not None and strategies[-1].harness.name == "trading"


def test_a_resume_cannot_add_or_drop_a_harness(engine, tmp_path):
    workspace, harness_dir, _, _ = engine
    kapso_with(None, tmp_path).build("g", output=str(workspace), budget=Budget(experiments=1))
    assert records(workspace)["launch"]["harness"] is None
    with pytest.raises(RunCheckpointIncompatibleError, match="launched without a harness; a resume cannot add"):
        kapso_with(harness_dir, tmp_path).build(output=str(workspace), resume=True)


def test_a_build_without_a_harness_records_none_everywhere(engine, tmp_path):
    workspace, _, strategies, _ = engine
    solution = kapso_with(None, tmp_path).build("g", output=str(workspace), budget=Budget(experiments=1))
    written = records(workspace)
    assert written["launch"]["harness"] is None and written["status"]["harness"] is None
    assert written["run_state"]["harness"] is None and written["solution"]["harness"] is None
    assert solution.harness is None and strategies[0].harness is None
