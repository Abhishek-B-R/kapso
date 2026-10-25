"""The verbs on a finished build: deploy and learn take the harness from
the object when one is loaded (the build's name, any version) and from
the record otherwise; a different name, a source that is gone, and an
unmet requirement of the verb's own module are refused by name; the
deployment module is staged into the selector's and the adapter's
sessions; the learning module into the mining lead's session at the
bundle root (removed with it, the bundle left as harvested) and into the
update run's lead and codex workers; the trajectory manifest carries the
build's harness and the learning one when it differs."""

import json
import shutil
from pathlib import Path
from types import SimpleNamespace

import pytest

import kapso.deployment.adapter.agent as adapter_module
import kapso.deployment.selector.agent as selector_module
from kapso.core.config import load_harness_defaults
from kapso.deployment.adapter.agent import AdapterAgent
from kapso.deployment.selector.agent import SelectorAgent
from kapso.execution.coding_agents.base import CodingResult
from kapso.handles import HarnessRef
from kapso.harness import HARNESS_ROOT_VARIABLE, HarnessError, load_harness
from kapso.learning.mining import FORMAT_DOC_NAME, MiningFrame
from kapso.learning.trajectory_store import TrajectoryStore, save_trajectory
from kapso.learning.update_frame import UpdateFrame
from tests.test_bank_retriever import card_text
from tests.test_mining_frame import MINING_CONFIG, FakeFactory, FakeLead, write_valid_mined
from tests.test_trajectory_store import TRAJECTORY_ID, build_work_dir, make_store
from tests.test_update_frame import good_lead, make_batch, make_config, seed_bank_home
from kapso.kapso import Kapso, _source_is_reachable
from tests.handles_support import facade, make_solution

TRADING = Path(__file__).resolve().parent.parent / "examples" / "harnesses" / "trading"


@pytest.fixture
def harness_dir(tmp_path):
    copy = tmp_path / "harness" / "trading"
    shutil.copytree(TRADING, copy)
    return copy


def loaded(tmp_path, harness_dir):
    return load_harness(str(harness_dir), settings=dict(load_harness_defaults(), store=str(tmp_path / "store")), say=lambda line: None)


def solution_with(tmp_path, harness, campaign_name="campaign"):
    campaign = tmp_path / campaign_name
    campaign.mkdir(exist_ok=True)
    return make_solution(campaign, harness=harness.ref() if harness is not None else None)


def kapso_for(tmp_path, harness_dir=None) -> Kapso:
    kapso = facade()
    kapso._harness_settings = dict(load_harness_defaults(), store=str(tmp_path / "store"))
    if harness_dir is not None:
        kapso._harness = loaded(tmp_path, harness_dir)
    return kapso


# ------------------------------------------------------------- resolution

def test_the_records_harness_is_resolved_again_when_none_is_loaded(tmp_path, harness_dir):
    harness = loaded(tmp_path, harness_dir)
    solution = solution_with(tmp_path, harness)
    resolved = kapso_for(tmp_path)._harness_for(solution, verb="deploy")
    assert resolved.hash == harness.hash and resolved.path == harness_dir.resolve()


def test_a_loaded_harness_of_another_version_is_allowed_and_said(tmp_path, harness_dir, capsys):
    built_with = loaded(tmp_path, harness_dir)
    solution = solution_with(tmp_path, built_with)
    manifest = harness_dir / "harness.yaml"
    manifest.write_text(manifest.read_text().replace("version: 0.1.0", "version: 0.2.0"))
    kapso = kapso_for(tmp_path, harness_dir)
    resolved = kapso._harness_for(solution, verb="deploy")
    assert resolved.version == "0.2.0"
    out = capsys.readouterr().out
    assert "for the deploy; the build ran with trading 0.1.0" in out


def test_a_loaded_harness_of_another_name_is_refused(tmp_path, harness_dir):
    solution = solution_with(tmp_path, loaded(tmp_path, harness_dir))
    other = tmp_path / "other"
    shutil.copytree(harness_dir, other)
    manifest = other / "harness.yaml"
    manifest.write_text(manifest.read_text().replace("name: trading", "name: lending"))
    with pytest.raises(HarnessError, match="was built with harness trading 0.1.0; the loaded harness is lending"):
        kapso_for(tmp_path, other)._harness_for(solution, verb="deploy")


def test_a_recorded_source_that_is_gone_is_refused_with_the_way_out(tmp_path, harness_dir):
    solution = solution_with(tmp_path, loaded(tmp_path, harness_dir))
    shutil.rmtree(harness_dir)
    with pytest.raises(HarnessError) as caught:
        kapso_for(tmp_path)._harness_for(solution, verb="learn")
    assert f"from {harness_dir.resolve()}, which is not here" in str(caught.value)
    assert "pass --harness <ref> (or load one) pointing at a copy of trading 0.1.0" in str(caught.value)


def test_a_solution_without_a_harness_resolves_none(tmp_path):
    solution = solution_with(tmp_path, None)
    assert kapso_for(tmp_path)._harness_for(solution, verb="deploy") is None


def test_the_verbs_refuse_on_their_own_modules_requirements(tmp_path, harness_dir, monkeypatch):
    mcp = harness_dir / "mcp.json"
    data = json.loads(mcp.read_text())
    data["mcpServers"]["broker"]["env"] = {"BROKER_API_KEY": "${BROKER_API_KEY}"}
    mcp.write_text(json.dumps(data, indent=2))
    monkeypatch.delenv("BROKER_API_KEY", raising=False)
    monkeypatch.chdir(tmp_path)
    solution = solution_with(tmp_path, loaded(tmp_path, harness_dir))
    kapso = kapso_for(tmp_path)
    # The broker is a deployment server: learn does not need it, deploy does.
    assert kapso._harness_for(solution, verb="learn").name == "trading"
    with pytest.raises(HarnessError, match="cannot run a deploy on this machine") as caught:
        kapso._harness_for(solution, verb="deploy")
    assert "BROKER_API_KEY (env, for the broker server)" in str(caught.value)


# -------------------------------------------------------------- the sessions

class RecordingAgent:
    calls = []

    def __init__(self, config):
        self.config = config

    def initialize(self, workspace):
        self.workspace = workspace

    def generate_code(self, prompt, debug_mode=False, timeout_seconds=None):
        RecordingAgent.calls.append({"config": self.config, "prompt": prompt, "workspace": self.workspace})
        return CodingResult(success=True, output='{"strategy": "local", "provider": null, "interface": "cli", "resources": {}}')

    def get_cumulative_cost(self):
        return 0.0

    def cleanup(self):
        pass


def test_the_selector_and_the_adapter_carry_the_deployment_module(tmp_path, harness_dir, monkeypatch):
    RecordingAgent.calls = []
    monkeypatch.setattr(selector_module.CodingAgentFactory, "create", staticmethod(lambda config: RecordingAgent(config)))
    monkeypatch.setattr(adapter_module.CodingAgentFactory, "create", staticmethod(lambda config: RecordingAgent(config)))
    harness = loaded(tmp_path, harness_dir)
    campaign = tmp_path / "campaign"
    campaign.mkdir()
    page = (harness_dir / "instructions" / "deployment.md").read_text().strip()

    selector = SelectorAgent(coding_agent_type="claude_code", model="m", harness=harness)
    selector._query_agent(str(campaign), "Raise the Sharpe", ["local", "docker"])
    [call] = RecordingAgent.calls
    assert page in call["prompt"] and "- paper-trading — " in call["prompt"] and "- broker — " in call["prompt"]
    assert call["prompt"].index("Raise the Sharpe") < call["prompt"].index(page)
    specific = call["config"].agent_specific
    assert set(specific["mcp_servers"]) >= {"market-data", "broker"} and specific["settings_path"].endswith(".claude/harness-hooks.json")
    assert (campaign / ".claude" / "skills" / "paper-trading" / "SKILL.md").is_file()
    assert (campaign / ".kapso" / "sessions" / "deployment" / "selector" / "session.json").is_file()

    adapted = tmp_path / "campaign_adapted_local"
    adapted.mkdir()
    adapter = AdapterAgent(coding_agent_type="claude_code", model="m", harness=harness)
    adapter._campaign_dir = campaign
    adapter._run_agent("claude_code", "m", str(adapted), "Adapt the winner for local.")
    call = RecordingAgent.calls[-1]
    assert page in call["prompt"] and call["prompt"].startswith("Adapt the winner for local.")
    assert (adapted / ".claude" / "skills" / "market-data" / "SKILL.md").is_file()
    assert (campaign / ".kapso" / "sessions" / "deployment" / "adapter" / "claude_code" / "session.json").is_file()


def test_without_a_harness_the_deploy_sessions_are_unchanged(tmp_path, monkeypatch):
    RecordingAgent.calls = []
    monkeypatch.setattr(selector_module.CodingAgentFactory, "create", staticmethod(lambda config: RecordingAgent(config)))
    campaign = tmp_path / "campaign"
    campaign.mkdir()
    SelectorAgent(coding_agent_type="claude_code", model="m")._query_agent(str(campaign), "g", ["local"])
    [call] = RecordingAgent.calls
    assert "Domain guidance" not in call["prompt"] and "settings_path" not in call["config"].agent_specific
    assert not (campaign / ".claude").exists()


# ------------------------------------------------------------------- learn

def learning_harness(tmp_path, harness_dir):
    """The trading harness with a learning module: the fixture ships pages
    only, so the module's attachments are added here."""
    manifest = harness_dir / "harness.yaml"
    manifest.write_text(manifest.read_text() + (
        "  learning:\n"
        "    skills: [backtesting]\n"
        "    mcp_servers: [market-data]\n"
        "    agents: [risk-reviewer]\n"
        "    hooks: [deny-web-fetch]\n"
    ))
    return loaded(tmp_path, harness_dir)


def test_the_mining_lead_is_staged_with_the_learning_module_and_the_bundle_is_left_as_harvested(tmp_path, harness_dir):
    harness = learning_harness(tmp_path, harness_dir)
    store = TrajectoryStore(local=str(tmp_path / "store"))
    work_dir, log = build_work_dir(tmp_path / "src")
    save_trajectory(store, TRAJECTORY_ID, work_dir=str(work_dir), campaign_log=str(log))
    bundle = store.resolve(TRAJECTORY_ID)
    seen = {}

    def snoop(workspace):
        root = Path(workspace)
        seen["skill"] = (root / ".claude" / "skills" / "backtesting" / "SKILL.md").is_file()
        seen["hooks"] = (root / ".claude" / "harness-hooks.json").is_file()
        seen["delegates"] = list(json.loads((root / ".claude" / "harness-agents.json").read_text()))
        seen["crew_agents"] = sorted(p.name for p in (root / ".claude" / "agents").glob("*.md"))
        return write_valid_mined(workspace)

    lead = FakeLead([snoop])
    factory = FakeFactory(lead)
    config = {**MINING_CONFIG, "run_root": str(tmp_path / "mining")}
    mined = MiningFrame(store, config, agent_factory=factory).mine(TRAJECTORY_ID, harness=harness)

    # The session had the module beside the crew's own agent definitions.
    assert mined == bundle / "mined"
    assert seen == {"skill": True, "hooks": True, "delegates": ["risk-reviewer"], "crew_agents": ["critic.md", "flow-writer.md"]}
    [config_used] = factory.configs
    specific = config_used.agent_specific
    assert specific["settings_path"] == str(bundle / ".claude" / "harness-hooks.json")
    assert specific["agents_path"] == str(bundle / ".claude" / "harness-agents.json")
    assert set(specific["mcp_servers"]) == {"market-data"}
    assert specific["env_overrides"] == {HARNESS_ROOT_VARIABLE: str(harness.path)}
    assert specific["streaming"] is True and specific["effort"] == "xhigh"
    prompt = lead.prompts[0]
    assert prompt.startswith("Mine this trajectory bundle")
    assert (harness_dir / "instructions" / "guardrails.md").read_text().strip() in prompt
    assert (harness_dir / "instructions" / "learning.md").read_text().strip() in prompt
    assert "- backtesting — " in prompt and "`/backtesting`" in prompt
    assert "Task statement" not in prompt      # the campaign had none
    # The staging went with the session; the bundle is as harvested, with
    # its derived view committed; the session's record and stream are in
    # the mining run's directory, never in the bundle.
    assert not (bundle / ".claude").exists() and not (bundle / FORMAT_DOC_NAME).exists()
    assert not (bundle / ".kapso").exists()
    assert store.manifest(TRAJECTORY_ID)["derived"]["mined"]["files"] > 0
    record_dir = tmp_path / "mining" / TRAJECTORY_ID.replace("/", "--") / ".kapso" / "sessions" / "lead"
    record = json.loads((record_dir / "session.json").read_text())
    assert record["module"] == "learning" and record["host"] == "claude_code" and record["skills"] == ["backtesting"]
    assert specific["stream_artifact_path"] == str(record_dir / "stream.jsonl")


def test_a_bundle_holding_a_staging_directory_of_its_own_is_refused_by_name(tmp_path):
    store = TrajectoryStore(local=str(tmp_path / "store"))
    work_dir, log = build_work_dir(tmp_path / "src")
    save_trajectory(store, TRAJECTORY_ID, work_dir=str(work_dir), campaign_log=str(log))
    (store.resolve(TRAJECTORY_ID) / ".agents" / "skills").mkdir(parents=True)
    frame = MiningFrame(store, {**MINING_CONFIG, "run_root": str(tmp_path / "mining")}, agent_factory=FakeFactory(FakeLead([])))
    with pytest.raises(FileExistsError, match=r"contains a \.agents directory that is not the mining crew's"):
        frame.mine(TRAJECTORY_ID)


def test_the_update_lead_and_its_workers_are_staged_with_the_learning_module(tmp_path, harness_dir):
    harness = learning_harness(tmp_path, harness_dir)
    config = make_config(tmp_path)
    store = TrajectoryStore.from_config(config)
    seed_bank_home(tmp_path, {"a-card": card_text("a-card")})
    batch = make_batch(tmp_path, store)
    lead = FakeLead([good_lead])
    factory = FakeFactory(lead)
    run_dir = UpdateFrame(store, config, agent_factory=factory).run_update(
        batch, config["learning"]["update_crew"]["run_root"], "crew_v1", harness=harness,
    )

    # The lead: the module in Claude Code's format, the guidance after its prompt.
    [config_used] = factory.configs
    specific = config_used.agent_specific
    assert specific["settings_path"] == str(run_dir / ".claude" / "harness-hooks.json")
    assert set(specific["mcp_servers"]) == {"market-data"}
    assert (run_dir / ".claude" / "skills" / "backtesting" / "SKILL.md").is_file()
    assert (run_dir / ".claude" / "agents" / "critic.md").is_file()
    page = (harness_dir / "instructions" / "learning.md").read_text().strip()
    assert page in lead.prompts[0] and "`/backtesting`" in lead.prompts[0]
    assert lead.prompts[0].index("THE LOOP") < lead.prompts[0].index(page)
    # The workers: codex's format, the launcher exporting the harness's
    # variables, reading the guidance between the role and the assignment,
    # passing the servers, the delegates and the hook trust.
    assert (run_dir / ".agents" / "skills" / "backtesting" / "SKILL.md").is_file()
    assert (run_dir / ".codex" / "hooks.json").is_file()
    assert (run_dir / ".codex" / "harness-agents" / "risk-reviewer.toml").is_file()
    launcher = (run_dir / "run-role.sh").read_text()
    assert f"export {HARNESS_ROOT_VARIABLE}={harness.path}\n" in launcher
    assert 'cat "role-prompts/$ROLE.md" harness-guidance.md "$ASSIGNMENT" | codex exec --json' in launcher
    assert "--dangerously-bypass-hook-trust" in launcher
    assert "mcp_servers.market-data.command=" in launcher and "agents.risk-reviewer.description=" in launcher
    guidance = (run_dir / "harness-guidance.md").read_text()
    assert page in guidance and "`$backtesting`" in guidance and "- risk-reviewer — " in guidance
    assert "Task statement" not in guidance
    for session, host in (("lead", "claude_code"), ("workers", "codex")):
        record = json.loads((run_dir / ".kapso" / "sessions" / session / "session.json").read_text())
        assert record["module"] == "learning" and record["host"] == host


def test_without_a_harness_the_crews_sessions_are_unchanged(tmp_path):
    config = make_config(tmp_path)
    store = TrajectoryStore.from_config(config)
    seed_bank_home(tmp_path, {"a-card": card_text("a-card")})
    batch = make_batch(tmp_path, store)
    factory = FakeFactory(FakeLead([good_lead]))
    run_dir = UpdateFrame(store, config, agent_factory=factory).run_update(
        batch, config["learning"]["update_crew"]["run_root"], "crew_v1",
    )
    launcher = (run_dir / "run-role.sh").read_text()
    assert 'cat "role-prompts/$ROLE.md" "$ASSIGNMENT" | codex exec --json' in launcher
    assert "export" not in launcher and "-c 'model_reasoning_effort=\"xhigh\"' | tee -a \"$STREAM\"" in launcher
    # Nothing staged; the sessions' records exist all the same, with no harness.
    assert not (run_dir / ".agents").exists() and not (run_dir / ".claude" / "skills").exists()
    for session in ("lead", "workers"):
        record = json.loads((run_dir / ".kapso" / "sessions" / session / "session.json").read_text())
        assert record["harness"] is None and record["skills"] == [] and record["runs"] == []
    [config_used] = factory.configs
    assert set(config_used.agent_specific) == {
        "auth_mode", "effort", "append_system_prompt", "streaming", "stream_artifact_path", "session_record_path",
    }

    mining = FakeFactory(FakeLead([write_valid_mined]))
    MiningFrame(store, {**MINING_CONFIG, "run_root": str(tmp_path / "mining")}, agent_factory=mining).mine(TRAJECTORY_ID)
    bundle = store.resolve(TRAJECTORY_ID)
    assert not (bundle / ".claude").exists()
    lead_record = json.loads(
        (tmp_path / "mining" / TRAJECTORY_ID.replace("/", "--") / ".kapso" / "sessions" / "lead" / "session.json").read_text()
    )
    assert lead_record["harness"] is None and lead_record["module"] == "learning"
    [config_used] = mining.configs
    assert set(config_used.agent_specific) == {
        "auth_mode", "effort", "append_system_prompt", "streaming", "stream_artifact_path", "session_record_path",
    }


def test_the_trajectory_manifest_carries_both_harness_keys(tmp_path):
    store = make_store(tmp_path)
    work_dir, log = build_work_dir(tmp_path / "src", strict=False)
    built = {"name": "trading", "version": "0.1.0", "hash": "a" * 64, "source": "/h/trading"}
    learned = {"name": "trading", "version": "0.2.0", "hash": "b" * 64, "source": "/h/trading"}
    trajectory_id = save_trajectory(
        store, TRAJECTORY_ID, work_dir=str(work_dir), campaign_log=str(log),
        contract="historical", harness=built, learning_harness=learned,
    )
    manifest = store.manifest(trajectory_id)
    assert manifest["harness"] == built and manifest["learning_harness"] == learned
    # Without a harness both keys are present and null, so a reader never
    # has to probe for them.
    plain = save_trajectory(
        make_store(tmp_path / "plain"), TRAJECTORY_ID, work_dir=str(work_dir), campaign_log=str(log), contract="historical",
    )
    assert make_store(tmp_path / "plain").manifest(plain)["harness"] is None


def test_a_loaded_harness_is_not_attached_to_a_campaign_built_without_one(tmp_path, harness_dir, capsys):
    solution = solution_with(tmp_path, None)
    with pytest.raises(HarnessError, match="was built without a harness, and a deploy runs as its build did"):
        kapso_for(tmp_path, harness_dir)._harness_for(solution, verb="deploy")
    # A learn may run under a harness the build did not have: its learning
    # module shapes the crews, the lessons keep the build's coordinate.
    learned_with = kapso_for(tmp_path, harness_dir)._harness_for(solution, verb="learn")
    assert learned_with.name == "trading"
    assert "for the learn; the build ran without one" in capsys.readouterr().out


def test_a_changed_version_at_the_recorded_source_is_said_too(tmp_path, harness_dir, capsys):
    solution = solution_with(tmp_path, loaded(tmp_path, harness_dir))
    manifest = harness_dir / "harness.yaml"
    manifest.write_text(manifest.read_text().replace("version: 0.1.0", "version: 0.2.0"))
    resolved = kapso_for(tmp_path)._harness_for(solution, verb="learn")
    assert resolved.version == "0.2.0"
    assert "for the learn; the build ran with trading 0.1.0" in capsys.readouterr().out


def test_a_recorded_git_source_counts_as_reachable():
    assert _source_is_reachable("acme/harnesses@v3#trading")
    assert _source_is_reachable("git+https://github.com/acme/harnesses@v3#trading")
    assert _source_is_reachable("git@github.com:acme/harnesses@v3#trading")
    assert not _source_is_reachable("/nowhere/at/all")


def test_the_adapter_lets_a_harness_refusal_through(tmp_path, harness_dir, monkeypatch):
    """A changed harness, a collision or a host with no staging stops the
    deploy with its message; the fallback agent is not tried without the
    harness either."""
    RecordingAgent.calls = []
    monkeypatch.setattr(adapter_module.CodingAgentFactory, "create", staticmethod(lambda config: RecordingAgent(config)))
    harness = loaded(tmp_path, harness_dir)
    page = harness_dir / "instructions" / "guardrails.md"
    page.write_text(page.read_text() + "\n- edited after the load\n")
    adapted = tmp_path / "campaign_adapted_local"
    adapted.mkdir()
    adapter = AdapterAgent(coding_agent_type="claude_code", model="m", harness=harness)
    adapter._campaign_dir = tmp_path / "campaign"
    with pytest.raises(HarnessError, match="the harness changed since launch"):
        adapter._run_with_fallback(str(adapted), "Adapt the winner for local.")
    assert RecordingAgent.calls == []
