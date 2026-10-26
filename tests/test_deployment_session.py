"""The deployment session (docs/plans/redesign/wp5-deploy.md, change 5),
with the session's agent faked and everything else real: the workspace
as its own repository, the env file, the staging with the target skills,
the prompt, the record before and after, the engine's acceptance with
its one resume, the failures."""

import json
import os
import stat
from pathlib import Path
from types import SimpleNamespace

import pytest

import kapso.deployment.session as session_module
from kapso.core.config import load_config
from kapso.deployment.errors import DeployError
from kapso.deployment.record import FAILED, RUNNING, open_record, records
from kapso.deployment.session import run_deployment
from kapso.execution.coding_agents.base import CodingResult
from tests.handles_support import candidate_branch, git, git_workspace, make_solution

OBJECTIVE = "Raise the churn model's AUC above 0.85.\n\nRules: never touch dq/; keep retention above 0.98."
MAIN = "def predict(inputs):\n    if inputs.get('boom'):\n        raise ValueError('boom')\n    return {'ok': inputs}\n"


def result_of(target="local", **overrides):
    data = {
        "target": target, "reasoning": None, "endpoint": None,
        "run": {"kind": "function", "module": "main", "callable": "predict"}, "values": {},
        "proof": {"inputs": {"a": 1}, "output": {"ok": {"a": 1}}}, "artifacts": ["main.py"],
        "summary": "main.predict answers in the worker",
    }
    data.update(overrides)
    return data


class FakeAgent:
    """The session's agent: writes what the test scripts, records what it was told."""
    calls = []
    on_generate = staticmethod(lambda workspace: None)
    on_resume = staticmethod(lambda workspace: None)
    generate_result = None

    def __init__(self, config):
        self.config = config

    def initialize(self, workspace):
        self.workspace = Path(workspace)

    def generate_code(self, prompt, debug_mode=False, timeout_seconds=None):
        FakeAgent.calls.append({"kind": "fresh", "prompt": prompt, "config": self.config, "workspace": self.workspace})
        FakeAgent.on_generate(self.workspace)
        return FakeAgent.generate_result or CodingResult(success=True, output="done", metadata={"cli_session_id": "s1"})

    def resume(self, cli_session_id, follow_up, timeout_seconds=None, reason=None):
        FakeAgent.calls.append({"kind": "resume", "prompt": follow_up, "session": cli_session_id, "timeout": timeout_seconds, "reason": reason})
        FakeAgent.on_resume(self.workspace)
        return CodingResult(success=True, output="done", metadata={"cli_session_id": cli_session_id})

    def get_cumulative_cost(self):
        return 0.0

    def cleanup(self):
        pass


def writes(main=MAIN, **overrides):
    def write(workspace):
        if main is not None:
            (workspace / "main.py").write_text(main)
        (workspace / "kapso_deployment.json").write_text(json.dumps(result_of(**overrides)))
    return write


@pytest.fixture
def agent(monkeypatch):
    FakeAgent.calls = []
    FakeAgent.on_generate = staticmethod(writes())
    FakeAgent.on_resume = staticmethod(lambda workspace: None)
    FakeAgent.generate_result = None
    monkeypatch.setattr(session_module.CodingAgentFactory, "create", staticmethod(lambda config: FakeAgent(config)))
    monkeypatch.setattr(session_module, "readiness", lambda target: "present" if target.name in ("local", "docker") else f"missing: install {target.name}")
    monkeypatch.setattr(session_module, "docker_daemon_running", lambda: False)
    return FakeAgent


def config_with(**deployment):
    config = load_config()
    config["deployment"] = {
        "target": "auto", "cli": None, "model": None, "effort": None, "timeout": 600,
        "call_timeout": 5, "script_timeout": 5, "port_base": 48300, "port_span": 20, **deployment,
    }
    return config


@pytest.fixture
def solution(tmp_path):
    """A campaign checked out at its delivered candidate, with untracked
    data, a tracked .env, and the engine's and a host's directories."""
    campaign = tmp_path / "churn-build"
    git_workspace(campaign)
    (campaign / ".env").write_text("OTHER=1\nAPI_KEY=old\n")
    git(campaign, "add", ".env")
    git(campaign, "commit", "-q", "-m", "env")
    commit = candidate_branch(campaign, "generic_exp_0", "predict.py", "print('model')\n")
    git(campaign, "checkout", "-q", "generic_exp_0")
    (campaign / "kapso_datasets").mkdir()
    (campaign / "kapso_datasets" / "train.csv").write_text("id,y\n1,0\n")
    (campaign / ".kapso").mkdir()
    (campaign / ".kapso" / "status.json").write_text("{}")
    (campaign / ".claude" / "skills" / "x").mkdir(parents=True)
    (campaign / "kapso_task.md").write_text("task")
    return make_solution(campaign, objective=OBJECTIVE, commit=commit, branch="generic_exp_0", score=0.85)


def deploy(solution, agent, **kwargs):
    arguments = dict(config=config_with(), target="local", env=None, options=None, coding_agent=None, harness=None)
    arguments.update(kwargs)
    return run_deployment(solution, **arguments)


def test_a_named_target_deploys_and_the_record_runs(solution, agent):
    software = deploy(solution, agent, env={"API_KEY": "secret"}, options={"schedule": "daily"})
    campaign = solution.campaign
    record = open_record(campaign)
    assert record.state == RUNNING and record.data["target"] == "local" and record.data["target_requested"] == "local"
    assert record.data["result"]["summary"] == "main.predict answers in the worker" and record.data["finished"]
    assert record.data["commit"] == solution.commit and record.data["branch"] == "generic_exp_0"
    assert record.data["host"] == "claude_code:claude-opus-5" and record.data["env_names"] == ["API_KEY"] and record.data["options"] == {"schedule": "daily"}
    # The workspace: the solution's tree with its untracked data, without
    # the engine's and the host's directories, its own repository.
    workspace = record.workspace
    assert (workspace / "predict.py").is_file() and (workspace / "kapso_datasets" / "train.csv").is_file()
    assert not (workspace / ".kapso").exists() and not (workspace / ".claude" / "skills" / "x").exists() and not (workspace / "kapso_task.md").exists()
    assert git(workspace, "log", "--oneline").count("\n") == 0 and git(workspace, "log", "-1", "--format=%s") == f"deployment 1 of churn-build at {solution.commit[:12]}"
    assert git(campaign, "status", "--porcelain", "--untracked-files=no") == ""   # the campaign untouched
    # The env file: the campaign's other lines kept, the call's keys winning, owner-only.
    env_file = workspace / ".env"
    assert env_file.read_text() == "OTHER=1\nAPI_KEY=secret\n" and stat.S_IMODE(env_file.stat().st_mode) == 0o600
    # The target skill staged into the session and copied beside the record.
    assert (workspace / ".claude" / "skills" / "local" / "scripts" / "deploy.sh").is_file()
    assert (record.target_dir / "scripts" / "deploy.sh").is_file()
    session = json.loads((campaign / ".kapso" / "sessions" / "deployment" / "1" / "session.json").read_text())
    assert session["engine_skills"] == ["local"] and session["harness"] is None
    # The session's prompt and configuration.
    [call] = agent.calls
    assert OBJECTIVE in call["prompt"] and str(workspace / "kapso_deployment.json") in call["prompt"]
    assert "The target is `local`. Open its skill with `/local`" in call["prompt"]
    assert "API_KEY" in call["prompt"] and "secret" not in call["prompt"] and "schedule = daily" in call["prompt"]
    env = call["config"].agent_specific["env_overrides"]
    assert env["KAPSO_DEPLOYMENT_NAME"] == record.data["deployment_name"] and env["KAPSO_PORT"] == str(record.data["port"])
    assert env["KAPSO_TARGET_DIR"] == str(workspace / ".claude" / "skills" / "local") and env["KAPSO_ENV_FILE"] == str(env_file)
    assert env["KAPSO_OPTION_SCHEDULE"] == "daily" and call["config"].agent_specific["timeout"] == 600
    # The handle runs the deployment the engine just proved.
    assert software.run({"b": 2}) == {"status": "success", "output": {"ok": {"b": 2}}} and software.proof["inputs"] == {"a": 1}
    software.stop()


def test_under_auto_the_prompt_offers_the_targets_with_their_readiness(solution, agent):
    agent.on_generate = staticmethod(writes(reasoning="a plain Python model; local is present"))
    software = deploy(solution, agent, target=None)
    [call] = agent.calls
    prompt = call["prompt"]
    assert "Choose the target first." in prompt
    assert "- local — Runs the solution in a Python process on this machine" in prompt and "open with `/local` — present" in prompt
    assert "- docker — " in prompt and "— present, the daemon does not answer: start Docker" in prompt
    assert "- modal — " in prompt and "— missing: install modal" in prompt
    assert "KAPSO_TARGET_DIR" not in call["config"].agent_specific["env_overrides"]
    record = open_record(solution.campaign)
    assert record.data["target_requested"] == "auto" and record.data["target"] == "local"
    assert record.data["reasoning"] == "a plain Python model; local is present"
    assert [(o["name"], o["ready"]) for o in record.data["offered"]] == [
        ("bentoml", "missing: install bentoml"), ("docker", "present, the daemon does not answer: start Docker"),
        ("langgraph", "missing: install langgraph"), ("local", "present"), ("modal", "missing: install modal"),
    ]
    assert sorted(p.name for p in (record.workspace / ".claude" / "skills").iterdir()) == ["bentoml", "docker", "langgraph", "local", "modal"]
    software.stop()


def test_a_missing_reasoning_under_auto_comes_back_once(solution, agent):
    agent.on_resume = staticmethod(writes(reasoning="because"))
    software = deploy(solution, agent, target=None)
    assert [call["kind"] for call in agent.calls] == ["fresh", "resume"]
    assert agent.calls[1]["prompt"].startswith("The engine checked the deployment and found: kapso_deployment.json: `reasoning` must say why you chose local.")
    assert agent.calls[1]["session"] == "s1" and agent.calls[1]["reason"] == "deployment result" and 0 < agent.calls[1]["timeout"] <= 600
    assert open_record(solution.campaign).data["reasoning"] == "because"
    software.stop()


@pytest.mark.parametrize("script, finding", [
    (writes(target="docker"), "kapso_deployment.json names target docker; the request was local"),
    (writes(artifacts=["main.py", "missing.py"]), "artifact missing.py is not in the workspace"),
    (writes(proof={"inputs": {"boom": True}, "output": {}}), "the proof call failed: "),
    (writes(main="def other(inputs):\n    return inputs\n"), "the deployment does not answer its health check"),
    (writes(run={"kind": "http"}), "kapso_deployment.json: `run.url` must be a non-empty string for the http kind"),
    (lambda workspace: None, "no kapso_deployment.json at the workspace root"),
])
def test_a_failing_check_comes_back_once_then_fails_the_deployment(solution, agent, script, finding):
    agent.on_generate = staticmethod(script)
    with pytest.raises(DeployError, match=r"deployment 1 of .* failed: after the resume: ") as error:
        deploy(solution, agent)
    assert finding in str(error.value) and "--stop --number 1" in str(error.value)
    assert [call["kind"] for call in agent.calls] == ["fresh", "resume"] and finding in agent.calls[1]["prompt"]
    record = open_record(solution.campaign)
    assert record.state == FAILED and finding in record.data["error"]


def test_a_session_cut_at_its_deadline_is_failed_without_a_resume(solution, agent):
    agent.generate_result = CodingResult(
        success=False, output="", error="Deadline of 600s reached",
        metadata={"cli_session_id": "s1", "deadline_exceeded": True, "completed_before_kill": False},
    )
    with pytest.raises(DeployError, match="failed: the session was cut at its deadline"):
        deploy(solution, agent)
    assert [call["kind"] for call in agent.calls] == ["fresh"]
    assert open_record(solution.campaign).state == FAILED


def test_a_session_that_fails_to_run_is_failed(solution, agent):
    agent.generate_result = CodingResult(success=False, output="", error="Quota exceeded", metadata={"cli_session_id": None})
    with pytest.raises(DeployError, match="failed: the session failed: Quota exceeded"):
        deploy(solution, agent)


def test_a_dirty_campaign_and_bad_env_are_refused_before_any_record(solution, agent):
    with pytest.raises(DeployError, match="env: 'BAD NAME' is not a variable name"):
        deploy(solution, agent, env={"BAD NAME": "x"})
    with pytest.raises(DeployError, match="env: the value of A holds a newline"):
        deploy(solution, agent, env={"A": "x\ny"})
    (solution.campaign / "predict.py").write_text("changed\n")
    with pytest.raises(DeployError, match=r"tracked files differ from the delivered commit \(predict.py\); commit or discard"):
        deploy(solution, agent)
    assert records(solution.campaign) == [] and agent.calls == []


def test_the_session_follows_the_hosts_own_layout_on_codex(solution, agent):
    software = deploy(solution, agent, coding_agent="codex")
    [call] = agent.calls
    assert call["config"].agent_type == "codex" and open_record(solution.campaign).data["host"] == "codex:gpt-5.6-sol"
    assert "Open its skill with `$local`" in call["prompt"]
    assert call["config"].agent_specific["env_overrides"]["KAPSO_TARGET_DIR"].endswith(".agents/skills/local")
    software.stop()


# ------------------------------------------------------------ with a harness

TRADING = Path(__file__).resolve().parent.parent / "examples" / "harnesses" / "trading"


def trading(tmp_path):
    import shutil
    from kapso.harness import load_harness
    copy = tmp_path / "harness" / "trading"
    shutil.copytree(TRADING, copy)
    return load_harness(str(copy), settings=dict(load_config()["harness"], store=str(tmp_path / "store")), say=lambda line: None)


def test_with_a_harness_the_session_carries_its_deployment_module_beside_the_target(solution, agent, tmp_path):
    harness = trading(tmp_path)
    software = deploy(solution, agent, harness=harness)
    [call] = agent.calls
    page = (harness.path / "instructions" / "deployment.md").read_text().strip()
    assert page in call["prompt"] and "- paper-trading — " in call["prompt"] and "- broker — " in call["prompt"]
    assert call["prompt"].index("The target is `local`") < call["prompt"].index(page)
    specific = call["config"].agent_specific
    assert set(specific["mcp_servers"]) >= {"market-data", "broker"} and specific["settings_path"].endswith(".claude/harness-hooks.json")
    assert specific["env_overrides"]["KAPSO_HARNESS_ROOT"] == str(harness.path)
    workspace = software.workspace
    assert sorted(p.name for p in (workspace / ".claude" / "skills").iterdir()) == ["local", "market-data", "paper-trading"]
    record = open_record(solution.campaign)
    assert record.data["harness"]["name"] == "trading" and record.data["harness_root"] == str(harness.path)
    session = json.loads((solution.campaign / ".kapso" / "sessions" / "deployment" / "1" / "session.json").read_text())
    assert session["skills"] == ["market-data", "paper-trading"] and session["engine_skills"] == ["local"]
    assert session["hooks"][0] == "protect-harness"
    software.stop()


def test_a_harness_changed_since_its_load_deploys_nothing(solution, agent, tmp_path):
    from kapso.harness import HarnessError
    harness = trading(tmp_path)
    page = harness.path / "instructions" / "guardrails.md"
    page.write_text(page.read_text() + "\n- edited after the load\n")
    with pytest.raises(HarnessError, match="the harness changed since launch"):
        deploy(solution, agent, harness=harness)
    assert records(solution.campaign) == [] and agent.calls == []


def test_a_harness_target_deploys_through_its_skill_and_runs_one_cycle_on_demand(solution, agent, tmp_path):
    """The trading example's paper-trading target: the session (faked)
    writes the runner the skill asks for and runs the target's deploy
    script with the deployment's variables; the engine's acceptance runs
    the health check and the proof cycle; the handle runs a cycle on
    demand, reads the log and stops the runner."""
    import os
    import subprocess
    from tests.test_target_scripts import RUN_PAPER

    def act(workspace):
        (workspace / "deploy").mkdir()
        (workspace / "deploy" / "run_paper.py").write_text(RUN_PAPER)
        env = {**os.environ, **agent.calls[-1]["config"].agent_specific["env_overrides"]}
        subprocess.run(["bash", f"{env['KAPSO_TARGET_DIR']}/scripts/deploy.sh"], cwd=workspace, env=env, check=True, capture_output=True)
        (workspace / "kapso_deployment.json").write_text(json.dumps(result_of(
            target="paper-trading", endpoint="deploy/paper.log", run={"kind": "script"},
            proof={"inputs": {}, "output": {"bar": "latest", "orders": [], "equity": 100000.0}},
            artifacts=["deploy/run_paper.py"], summary="the runner runs on the schedule",
        )))

    agent.on_generate = staticmethod(act)
    harness = trading(tmp_path)
    software = deploy(solution, agent, harness=harness, target="paper-trading", options={"schedule": "*/2 * * * *", "cash": "5000"})
    [call] = agent.calls
    env = call["config"].agent_specific["env_overrides"]
    assert env["KAPSO_TARGET_DIR"].endswith(".claude/skills/paper-trading") and env["KAPSO_OPTION_CASH"] == "5000"
    assert "The target is `paper-trading`. Open its skill with `/paper-trading`" in call["prompt"]
    record = open_record(solution.campaign)
    assert record.state == RUNNING and record.data["target"] == "paper-trading" and record.data["endpoint"] == "deploy/paper.log"
    assert (record.target_dir / "scripts" / "run.py").is_file() and record.data["harness"]["name"] == "trading"
    session = json.loads((solution.campaign / ".kapso" / "sessions" / "deployment" / "1" / "session.json").read_text())
    assert session["skills"] == ["market-data", "paper-trading"] and session["engine_skills"] == []
    assert software.run({"at": "2024-01-05"}) == {"status": "success", "output": {"bar": "2024-01-05", "orders": [], "equity": 5000.0}}
    assert software.is_healthy() and '"bar": "latest"' in software.logs()
    software.stop()
    assert not software.is_healthy() and not (software.workspace / "deploy" / "paper.pid").exists()
