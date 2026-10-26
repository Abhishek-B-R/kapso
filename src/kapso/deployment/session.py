"""The deployment session (docs/plans/redesign/wp5-deploy.md, "The
session", "The engine's acceptance", "The workspace"): one session on a
copy of the solution, staged with the harness's deployment module and
the engine's target skills, that adapts the copy, deploys it with the
target's scripts, proves one call and writes the result file; then the
engine's own checks, one resume with the finding, and the record's
completion. `run_deployment` is what `Kapso.deploy()` calls."""

import json
import os
import re
import shutil
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import git

from kapso.core.preflight import docker_daemon_running
from kapso.core.prompt_loader import load_prompt, optional_block, render_prompt
from kapso.core.roles import SPEC_KEYS, SessionRole, resolve_spec
from kapso.deployment.errors import DeployError
from kapso.deployment.handle import FUNCTION, HTTP, RUN_KINDS, SCRIPT, Software
from kapso.deployment.record import DEPLOYING, FAILED, RUNNING, DeploymentRecord, now, start_record
from kapso.deployment.targets import AUTO, TargetSkill, readiness, resolve_target
from kapso.execution.coding_agents.factory import CodingAgentFactory
from kapso.harness.staging import host_for, open_skill_instruction, skills_dir, stage_harness

RESULT_FILE = "kapso_deployment.json"
ENV_FILE = ".env"
DEPLOYMENT_MODULE = "deployment"
DEPLOYMENT_PROMPT = "deployment/deployment_prompt.md"
RESUME_REASON = "deployment result"
# What the copy leaves behind: the campaign's repository and the engine's
# and the hosts' own directories; the staging mounts the statement and
# the prepared resources again for a harness build.
COPY_IGNORE = (
    ".git", ".kapso", ".claude", ".agents", ".codex", "kapso_task.md", "prepared",
    "__pycache__", ".pytest_cache", ".mypy_cache", ".venv", "venv", "node_modules",
)
ALLOWED_TOOLS = ["Edit", "Read", "Write", "Bash", "Glob", "Grep"]
ENV_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
RUN_KEYS = {FUNCTION: ("module", "callable"), HTTP: ("url", "path"), SCRIPT: ()}
COMMITTER = git.Actor("Kapso", "kapso@leeroo.com")


def deployment_role(config: Dict[str, Any], coding_agent: Optional[str]) -> SessionRole:
    """The deployment session's spec over the hosts table: the call's host,
    else the block's `cli`, else the build's host; the block's model and
    effort, else the host entry's."""
    block = config["deployment"]
    spec = {key: block[key] for key in SPEC_KEYS if block.get(key) is not None}
    if coding_agent is not None:
        spec["cli"] = coding_agent
    host = spec.get("cli") or config["search_strategy"]["params"]["host"]
    return resolve_spec(config["hosts"], host, spec, name=DEPLOYMENT_MODULE, origin=DEPLOYMENT_MODULE)


def check_env(env: Dict[str, str]) -> None:
    for name, value in env.items():
        if not ENV_NAME.match(str(name)):
            raise DeployError(f"env: {name!r} is not a variable name (letters, digits and underscores, not starting with a digit)")
        if "\n" in str(value):
            raise DeployError(f"env: the value of {name} holds a newline, which no runtime's env file carries")


def write_env_file(workspace: Path, env: Dict[str, str]) -> Optional[Path]:
    """The caller's variables in `.env` at the workspace root: an existing
    file's other lines kept, the call's keys winning, owner-only (the
    file holds secrets). None when there is nothing to write."""
    if not env:
        return None
    path = workspace / ENV_FILE
    kept: List[str] = []
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            key = line.split("=", 1)[0].strip()
            if not line.strip() or line.lstrip().startswith("#") or key not in env:
                kept.append(line)
    path.write_text("\n".join(kept + [f"{key}={value}" for key, value in env.items()]) + "\n", encoding="utf-8")
    os.chmod(path, 0o600)
    return path


def refuse_dirty(campaign: Path) -> None:
    """What was evaluated is the delivered commit: tracked files that
    differ from it are refused by name."""
    status = git.Repo(campaign).git.status("--porcelain", "--untracked-files=no").strip()
    if status:
        names = sorted(line.split(maxsplit=1)[-1] for line in status.splitlines())
        raise DeployError(
            f"{campaign}: tracked files differ from the delivered commit ({', '.join(names)}); "
            f"commit or discard the changes first"
        )


def make_workspace(campaign: Path, record: DeploymentRecord) -> Path:
    """The solution's working tree copied without the engine's and the
    hosts' directories, then its own repository with one commit, so a
    session's git commands stop here."""
    workspace = record.workspace
    shutil.copytree(campaign, workspace, ignore=shutil.ignore_patterns(*COPY_IGNORE), symlinks=True)
    repo = git.Repo.init(workspace)
    repo.git.add("--all")
    repo.index.commit(
        f"deployment {record.number} of {campaign.name} at {record.data['commit'][:12]}",
        author=COMMITTER, committer=COMMITTER,
    )
    return workspace


def _readiness_line(target: TargetSkill) -> str:
    state = readiness(target)
    if target.name == "docker" and state == "present":
        return "present, the daemon answers" if docker_daemon_running() else "present, the daemon does not answer: start Docker"
    return state


def _target_block(target: Optional[TargetSkill], offered: List[TargetSkill], host: str, staged_skills: Path, offered_lines: List[Dict[str, str]]) -> str:
    if target is not None:
        return (
            f"The target is `{target.name}`. Open its skill with `{open_skill_instruction(host, target.name)}` and follow "
            f"it; its scripts are under $KAPSO_TARGET_DIR ({staged_skills / target.name})."
        )
    lines = ["Choose the target first. The targets available, each with how to open its skill and what this machine has for it:"]
    for candidate, line in zip(offered, offered_lines):
        lines.append(
            f"- {candidate.name} — {candidate.description} — open with `{open_skill_instruction(host, candidate.name)}` — {line['ready']}"
        )
    lines.append("")
    lines.append(
        "Decide before changing anything, write why under `reasoning` in the result, then "
        f"`export KAPSO_TARGET_DIR={staged_skills}/<the target's name>` and follow its skill."
    )
    return "\n".join(lines)


def _prompt(solution: Any, record: DeploymentRecord, target: Optional[TargetSkill], offered: List[TargetSkill],
            host: str, workspace: Path, env: Dict[str, str], options: Dict[str, str], guidance: str,
            offered_lines: List[Dict[str, str]]) -> str:
    env_block = (
        f"The caller's variables, set at runtime by the engine and in `{ENV_FILE}` at the workspace root "
        f"(`$KAPSO_ENV_FILE`): {', '.join(sorted(env))}. Never copy their values into code, images or logs."
        if env else "The caller passed no runtime variables."
    )
    options_block = (
        "The call's options, for the target's workflow (each also in your environment as `KAPSO_OPTION_<NAME>`): "
        + "; ".join(f"{name} = {value}" for name, value in options.items())
        if options else "The call passed no options."
    )
    return render_prompt(load_prompt(DEPLOYMENT_PROMPT), {
        "objective": solution.brief.objective,
        "branch": solution.branch,
        "commit": solution.commit,
        "score": "unscored" if solution.score is None else f"{solution.score}",
        "workspace": str(workspace),
        "deployment_name": record.data["deployment_name"],
        "port": str(record.data["port"]),
        "number": str(record.number),
        "record_dir": str(record.directory),
        "interpreter": record.data["interpreter"],
        "result_path": str(workspace / RESULT_FILE),
        "env_block": env_block,
        "options_block": options_block,
        "target_block": _target_block(target, offered, host, skills_dir(workspace, host), offered_lines),
        "domain_guidance": optional_block(guidance),
    })


def _variables(record: DeploymentRecord, workspace: Path, env_file: Optional[Path], options: Dict[str, str],
               target_dir: Optional[Path]) -> Dict[str, str]:
    variables = {
        "KAPSO_DEPLOYMENT_NAME": record.data["deployment_name"],
        "KAPSO_PORT": str(record.data["port"]),
        "KAPSO_NUMBER": str(record.number),
        "KAPSO_WORKSPACE": str(workspace),
        "KAPSO_RECORD_DIR": str(record.directory),
        "KAPSO_INTERPRETER": record.data["interpreter"],
    }
    if env_file is not None:
        variables["KAPSO_ENV_FILE"] = str(env_file)
    if target_dir is not None:
        variables["KAPSO_TARGET_DIR"] = str(target_dir)
    for name, value in options.items():
        variables[f"KAPSO_OPTION_{name.upper()}"] = str(value)
    return variables


def _ended_badly(result: Any) -> Optional[str]:
    """Why the session is a failed deployment, before any result is read:
    cut at its deadline, or failed to run."""
    metadata = result.metadata
    if metadata.get("deadline_exceeded") and not metadata.get("completed_before_kill"):
        return "the session was cut at its deadline"
    if not result.success:
        return f"the session failed: {result.error or 'no output'}"
    return None


def _shape_finding(data: Any, target: Optional[TargetSkill], offered: List[TargetSkill]) -> Optional[str]:
    """What is wrong with the result file's shape, in the session's terms."""
    if not isinstance(data, dict):
        return f"{RESULT_FILE} must hold a JSON object"
    for key in ("target", "summary"):
        if not isinstance(data.get(key), str) or not data[key].strip():
            return f"{RESULT_FILE}: `{key}` must be a non-empty string"
    run = data.get("run")
    if not isinstance(run, dict) or run.get("kind") not in RUN_KINDS:
        return f"{RESULT_FILE}: `run.kind` must be one of {', '.join(RUN_KINDS)}"
    for key in RUN_KEYS[run["kind"]]:
        if not isinstance(run.get(key), str) or not run[key]:
            return f"{RESULT_FILE}: `run.{key}` must be a non-empty string for the {run['kind']} kind"
    if data.get("endpoint") is not None and not isinstance(data["endpoint"], str):
        return f"{RESULT_FILE}: `endpoint` must be a string or null"
    values = data.get("values", {})
    if not isinstance(values, dict) or not all(isinstance(k, str) and isinstance(v, str) for k, v in values.items()):
        return f"{RESULT_FILE}: `values` must be a mapping of strings"
    proof = data.get("proof")
    if not isinstance(proof, dict) or "inputs" not in proof or "output" not in proof:
        return f"{RESULT_FILE}: `proof` must hold the `inputs` of the call you proved and its `output`"
    artifacts = data.get("artifacts")
    if not isinstance(artifacts, list) or not all(isinstance(a, str) for a in artifacts):
        return f"{RESULT_FILE}: `artifacts` must list the files you wrote or changed"
    if target is not None and data["target"] != target.name:
        return f"{RESULT_FILE} names target {data['target']}; the request was {target.name}"
    if target is None:
        if data["target"] not in {candidate.name for candidate in offered}:
            return f"{RESULT_FILE} names target {data['target']}, which was not offered"
        if not isinstance(data.get("reasoning"), str) or not data["reasoning"].strip():
            return f"{RESULT_FILE}: `reasoning` must say why you chose {data['target']}"
    return None


def _check(record: DeploymentRecord, workspace: Path, target: Optional[TargetSkill], offered: List[TargetSkill],
           software_of: Any) -> Optional[str]:
    """The engine's acceptance after a completed session: the finding to
    send back, or None when the deployment runs."""
    path = workspace / RESULT_FILE
    if not path.is_file():
        return f"no {RESULT_FILE} at the workspace root; write it as the prompt says"
    data = json.loads(path.read_text(encoding="utf-8"))
    finding = _shape_finding(data, target, offered)
    if finding is not None:
        return finding
    missing = [name for name in data["artifacts"] if not (workspace / name).exists()]
    if missing:
        return f"artifact {', '.join(missing)} is not in the workspace"
    chosen = target if target is not None else next(candidate for candidate in offered if candidate.name == data["target"])
    if record.target_dir.exists():
        shutil.rmtree(record.target_dir)
    shutil.copytree(chosen.path, record.target_dir)
    record.data.update(
        target=chosen.name, reasoning=data.get("reasoning"), result=data,
        endpoint=data.get("endpoint"), values=dict(data.get("values", {})),
    )
    record.set_state(RUNNING)
    software = software_of(record)
    if not software.is_healthy():
        record.set_state(DEPLOYING)
        return "the deployment does not answer its health check (scripts/health.sh does not exit 0, or the function does not import)"
    answer = software.run(data["proof"]["inputs"])
    if answer["status"] != "success":
        software.stop()
        record.set_state(DEPLOYING)
        return f"the proof call failed: {answer['error']}"
    return None


def run_deployment(
    solution: Any, *, config: Dict[str, Any], target: Optional[str], env: Optional[Dict[str, str]],
    options: Optional[Dict[str, str]], coding_agent: Optional[str], harness: Any,
    agent_factory: Any = CodingAgentFactory,
) -> Software:
    """One deployment of the solution, start to finish: the record, the
    workspace, the session, the acceptance; the running `Software`, or
    `DeployError` with the record's path."""
    campaign = Path(solution.campaign).resolve()
    block = config["deployment"]
    role = deployment_role(config, coding_agent)
    host = host_for(role.cli)
    chosen, offered = resolve_target(target, block["target"], harness)
    env = dict(env or {})
    options = {str(k): str(v) for k, v in (options or {}).items()}
    check_env(env)
    refuse_dirty(campaign)
    record = start_record(
        campaign, target_requested=target if target is not None else block["target"],
        host=f"{role.cli}:{role.model}", interpreter=sys.executable, env_names=sorted(env), options=options,
        commit=solution.commit, branch=solution.branch,
        harness_built=None if solution.harness is None else {"name": solution.harness.name, "version": solution.harness.version, "hash": solution.harness.hash, "source": solution.harness.source},
        harness=None if harness is None else harness.ref_dict(),
        harness_root=None if harness is None else str(harness.path),
        port_base=int(block["port_base"]), port_span=int(block["port_span"]),
    )
    workspace = make_workspace(campaign, record)
    env_file = write_env_file(workspace, env)
    staged_targets = [chosen] if chosen is not None else list(offered)
    staged = stage_harness(
        harness, DEPLOYMENT_MODULE, session_dir=workspace, campaign_dir=campaign,
        session_id=record.data["session"], host=host, engine_skills=[candidate.path for candidate in staged_targets],
    )
    offered_lines = [{"name": candidate.name, "ready": _readiness_line(candidate)} for candidate in offered]
    record.data["offered"] = offered_lines
    record.write()
    target_dir = None if chosen is None else skills_dir(workspace, host) / chosen.name
    prompt = _prompt(solution, record, chosen, offered, host, workspace, env, options, staged.guidance, offered_lines)
    own = {
        "timeout": role.timeout,
        "env_overrides": _variables(record, workspace, env_file, options, target_dir),
        "allowed_tools": [*ALLOWED_TOOLS, *staged.allowed_tools],
        "streaming": True,
    }
    agent = agent_factory.create(agent_factory.session_config(role, own, staged))
    agent.initialize(str(workspace))
    started = time.monotonic()

    def software_of(current: DeploymentRecord) -> Software:
        return Software(current, call_timeout=block["call_timeout"], script_timeout=block["script_timeout"])

    def fail(reason: str) -> DeployError:
        agent.cleanup()
        record.data["finished"] = now()
        record.set_state(FAILED, error=reason)
        return DeployError(
            f"deployment {record.number} of {campaign} failed: {reason} (the record: {record.path}; "
            f"`kapso deploy {campaign} --stop --number {record.number}` ends what its deploy.sh may have started)"
        )

    result = agent.generate_code(prompt)
    bad = _ended_badly(result)
    if bad is not None:
        raise fail(bad)
    finding = _check(record, workspace, chosen, offered, software_of)
    if finding is not None:
        remaining = None if role.timeout is None else role.timeout - (time.monotonic() - started)
        if remaining is not None and remaining <= 0:
            raise fail(f"{finding}; no room left under the session's deadline for a resume")
        cli_session_id = result.metadata.get("cli_session_id")
        if not cli_session_id:
            raise fail(f"{finding}; the session recorded no handle to resume")
        result = agent.resume(
            cli_session_id,
            f"The engine checked the deployment and found: {finding}. Fix it and write {workspace / RESULT_FILE} again.",
            timeout_seconds=remaining, reason=RESUME_REASON,
        )
        bad = _ended_badly(result)
        if bad is not None:
            raise fail(f"{bad} (resumed for: {finding})")
        finding = _check(record, workspace, chosen, offered, software_of)
        if finding is not None:
            raise fail(f"after the resume: {finding}")
    agent.cleanup()
    record.data["finished"] = now()
    record.write()
    return software_of(record)
