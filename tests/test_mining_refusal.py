"""The mining frame and the model's refusal (wp6-observability.md, change
12): a lead turn the safeguards refused is launched again once, the same
prompt in a fresh session, and the learn status says so; a second
refusal fails the lesson loud; an ordinary result that merely names the
word is not a refusal; the repair rounds are untouched by a relaunch.
Hermetic: the lead is a fake at the provider boundary, and the real
factory is barred."""
from pathlib import Path

import pytest

import kapso.learning.mining as mining_module
from kapso.learning.mining import REFUSAL_NOTE, MINED_DIR_NAME, MiningFrame
from kapso.learning.trajectory_store import TrajectoryStore, save_trajectory
from tests.test_trajectory_store import TRAJECTORY_ID, build_work_dir

MINING_CONFIG = {
    "lead": {"cli": "claude_code", "model": "m", "effort": "xhigh", "auth_mode": "oauth"},
    "flow_writer_model": "writer-model",
    "critic_model": "critic-model",
    "timeout_minutes": 1,
    "repair_rounds": 1,
    "refusal_relaunches": 1,
    "run_root": "learning/mining",
}
REFUSAL = "API Error: 400 Your request was flagged: safeguards flagged the content"


class FakeResult:
    def __init__(self, output, *, refused=False):
        self.success = not refused
        self.output = output
        self.error = output if refused else None
        self.refused = refused


class FakeLead:
    """Each call takes the next writer: a callable over the workspace that
    returns the report, or a FakeResult as it stands."""

    def __init__(self, writers):
        self.writers = list(writers)
        self.prompts = []
        self.workspace = None

    def initialize(self, workspace):
        self.workspace = workspace

    def generate_code(self, prompt, debug_mode=False, timeout_seconds=None):
        self.prompts.append(prompt)
        writer = self.writers.pop(0)
        return writer if isinstance(writer, FakeResult) else FakeResult(writer(self.workspace))

    def cleanup(self):
        pass


class FakeFactory:
    def __init__(self, lead):
        self.lead = lead
        self.created = 0

    def create(self, config):
        self.created += 1
        return self.lead


class FakeStatus:
    def __init__(self):
        self.notes = []

    def note(self, line, **fields):
        self.notes.append(line)


def valid_mined(workspace):
    """A minimal contract-conformant mined view over build_work_dir's
    bundle (one run: run_0001)."""
    mined = Path(workspace) / MINED_DIR_NAME
    (mined / "it-1").mkdir(parents=True, exist_ok=True)
    (mined / "index.md").write_text("# Campaign\n- [it-1](it-1/index.md) — the only round\n")
    (mined / "strategy.md").write_text("## Lens 1\nbelief -> evidence -> re-aim\n")
    (mined / "operations.md").write_text("No incidents.\n")
    (mined / "artifacts.md").write_text("No shared-space artifacts.\n")
    (mined / "it-1" / "index.md").write_text("# it-1\n- [flow-1](flow-1.md) — the winning flow\n")
    (mined / "it-1" / "flow-1.md").write_text(
        "---\nflow: it-1/flow-1\nstatus: judged\nruns: [run_0001]\nsources:\n"
        "  idea: campaign.log#\"campaign started\"\n  evaluation: runs/run_0001/metrics.json\n---\n"
        "## Idea\nVerbatim idea [campaign.log#L1].\n## Evaluation\nScored 0.7136 [runs/run_0001/metrics.json].\n"
    )
    return "MINING REPORT: 1 flow written; no gaps. (safeguards flagged nothing)"


@pytest.fixture
def frame(tmp_path, monkeypatch):
    monkeypatch.setattr(
        mining_module.CodingAgentFactory, "create",
        classmethod(lambda cls, config: pytest.fail("the real factory was asked for a lead")),
    )
    monkeypatch.chdir(tmp_path)
    store = TrajectoryStore(local=str(tmp_path / "store"))
    work_dir, log = build_work_dir(tmp_path)
    save_trajectory(store, TRAJECTORY_ID, work_dir=str(work_dir), campaign_log=str(log))

    def make(writers):
        lead = FakeLead(writers)
        return MiningFrame(store, MINING_CONFIG, agent_factory=FakeFactory(lead)), lead

    return make


def test_a_refused_lead_is_launched_again_once_and_the_status_says_so(frame):
    mining, lead = frame([FakeResult(REFUSAL, refused=True), valid_mined])
    status = FakeStatus()
    mined_dir = mining.mine(TRAJECTORY_ID, status=status)
    assert (mined_dir / "mining-report.md").read_text().startswith("MINING REPORT")
    # The same prompt, launched again; no repair round was spent on it.
    assert len(lead.prompts) == 2 and lead.prompts[0] == lead.prompts[1]
    assert status.notes == [REFUSAL_NOTE]


def test_a_second_refusal_fails_the_lesson_loud(frame):
    mining, lead = frame([FakeResult(REFUSAL, refused=True), FakeResult(REFUSAL, refused=True)])
    with pytest.raises(RuntimeError, match="mining lead refused by the model's safeguards after 1 relaunch"):
        mining.mine(TRAJECTORY_ID, status=FakeStatus())
    assert len(lead.prompts) == 2


def test_a_result_that_names_the_word_is_not_a_refusal(frame):
    mining, lead = frame([valid_mined])
    status = FakeStatus()
    mining.mine(TRAJECTORY_ID, status=status)
    assert len(lead.prompts) == 1 and status.notes == []


def test_the_relaunch_budget_is_the_runs_and_a_repair_round_shares_it(frame):
    """A refusal in the repair round uses the same budget: the first launch
    was refused and relaunched, so the repair's refusal is the second."""
    mining, lead = frame([
        FakeResult(REFUSAL, refused=True),
        lambda workspace: "MINING REPORT: nothing written",   # a report, no mined view: the validator finds gaps
        FakeResult(REFUSAL, refused=True),
    ])
    with pytest.raises(RuntimeError, match="refused by the model's safeguards after 1 relaunch"):
        mining.mine(TRAJECTORY_ID, status=FakeStatus())
    assert len(lead.prompts) == 3 and "violations" in lead.prompts[2]


def test_without_a_status_the_relaunch_is_silent(frame):
    mining, lead = frame([FakeResult(REFUSAL, refused=True), valid_mined])
    mining.mine(TRAJECTORY_ID)
    assert len(lead.prompts) == 2
