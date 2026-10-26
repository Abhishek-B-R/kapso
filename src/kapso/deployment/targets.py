"""The deployment targets: skills with their scripts, bundled with the
package under `targets/<name>/` or shipped by a harness on its deployment
module (docs/plans/redesign/wp5-deploy.md, the target-skill contract).

A target is a skill directory holding `SKILL.md` (the front matter's name
and description, the workflow in the body) and `scripts/deploy.sh`, the
one script every target has and the structural mark of a deployment
workflow: a skill a harness lists on its deployment module without one
(`market-data`, a reference) is not a target. The lifecycle scripts
(`start.sh`, `stop.sh`, `health.sh`, `logs.sh`) and `run.py` are optional,
and `Software` says what it cannot do without one.

Import-light on purpose: the preflight imports this module at the top,
and the harness package imports the preflight."""

import shlex
import shutil
import subprocess
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from kapso.core.front_matter import read_front_matter
from kapso.deployment.errors import DeployError

BUNDLED_DIR = Path(__file__).resolve().parent / "targets"
AUTO = "auto"
SKILL_FILE = "SKILL.md"
SCRIPTS_DIR = "scripts"
DEPLOY_SCRIPT = "deploy.sh"
LIFECYCLE_SCRIPTS = ("start.sh", "stop.sh", "health.sh", "logs.sh")
RUN_SCRIPT = "run.py"
DEPLOYMENT_MODULE = "deployment"
BUNDLED = "bundled"
# The run kinds a result may name (the handle's `run()` dispatches on them).
FUNCTION, HTTP, SCRIPT = "function", "http", "script"
RUN_KINDS = (FUNCTION, HTTP, SCRIPT)


@dataclass(frozen=True)
class TargetSkill:
    name: str
    path: Path
    description: str
    # The tool the deploying machine needs, `{binary, install}` and an
    # optional `probe` (`{command, timeout, fix}`: what proves the tool
    # usable, the docker daemon say): read from the engine's own targets
    # only (a harness declares its tools in harness.yaml's environment,
    # which `check` reads).
    requires: Optional[Dict[str, Any]]
    # The run kinds the target's workflow ends in (`metadata.run_kinds`),
    # when the skill declares them: a result naming another is refused.
    run_kinds: Optional[Tuple[str, ...]]
    origin: str   # BUNDLED, or the harness's name

    def script(self, name: str) -> Path:
        return self.path / SCRIPTS_DIR / name

    def has_script(self, name: str) -> bool:
        return self.script(name).is_file()


def _requires(file: Path, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    requires = (data.get("metadata") or {}).get("requires")
    if requires is None:
        return None
    if not isinstance(requires, dict) or not isinstance(requires.get("binary"), str) or not isinstance(requires.get("install"), str):
        raise DeployError(f"{file}: metadata.requires is a mapping with `binary` and `install`")
    probe = requires.get("probe")
    if probe is not None and (
        not isinstance(probe, dict) or not isinstance(probe.get("command"), str) or not isinstance(probe.get("fix"), str)
        or isinstance(probe.get("timeout"), bool) or not isinstance(probe.get("timeout"), (int, float)) or probe["timeout"] <= 0
    ):
        raise DeployError(f"{file}: metadata.requires.probe is a mapping with `command`, `timeout` (seconds) and `fix`")
    return dict(requires)


def _run_kinds(file: Path, data: Dict[str, Any]) -> Optional[Tuple[str, ...]]:
    kinds = (data.get("metadata") or {}).get("run_kinds")
    if kinds is None:
        return None
    if not isinstance(kinds, list) or not kinds or any(kind not in RUN_KINDS for kind in kinds):
        raise DeployError(f"{file}: metadata.run_kinds lists one or more of {', '.join(RUN_KINDS)}")
    return tuple(kinds)


def _skill(path: Path, origin: str, *, engine: bool) -> TargetSkill:
    file = path / SKILL_FILE
    data, _body = read_front_matter(file)
    if not isinstance(data, dict) or data.get("name") != path.name:
        raise DeployError(f"{file}: a target skill's front matter names its directory, `{path.name}`")
    description = data.get("description")
    if not isinstance(description, str) or not description.strip():
        raise DeployError(f"{file}: a target skill's front matter carries a description")
    if not (path / SCRIPTS_DIR / DEPLOY_SCRIPT).is_file():
        raise DeployError(f"{path}: a target skill holds {SCRIPTS_DIR}/{DEPLOY_SCRIPT}")
    return TargetSkill(
        path.name, path, description.strip(), _requires(file, data) if engine else None, _run_kinds(file, data), origin,
    )


def bundled_targets() -> List[TargetSkill]:
    """The five the package ships, by name."""
    return [
        _skill(path, BUNDLED, engine=True)
        for path in sorted(BUNDLED_DIR.iterdir())
        if path.is_dir() and not path.name.startswith("_")
    ]


def harness_targets(harness: Any) -> List[TargetSkill]:
    """The harness's deployment workflows: the skills listed on its
    deployment module that hold `scripts/deploy.sh`; none without a
    harness."""
    if harness is None:
        return []
    targets = []
    for name in harness.module(DEPLOYMENT_MODULE).skills:
        path = harness.path / "skills" / name
        if (path / SCRIPTS_DIR / DEPLOY_SCRIPT).is_file():
            targets.append(_skill(path, harness.name, engine=False))
    return targets


def available_targets(harness: Any) -> List[TargetSkill]:
    """The bundled targets, then the harness's. A skill the harness lists
    on its deployment module named like a bundled target or `auto` is
    refused, a target or not: the two would land in one staged directory."""
    bundled = bundled_targets()
    taken = {target.name for target in bundled} | {AUTO}
    if harness is not None:
        for name in harness.module(DEPLOYMENT_MODULE).skills:
            if name in taken:
                raise DeployError(
                    f"harness {harness.name}: its deployment skill `{name}` is named like a bundled "
                    f"target; rename it"
                )
    return bundled + harness_targets(harness)


def describe(targets: List[TargetSkill]) -> str:
    """`auto, local, … (bundled) and paper-trading (the trading harness's)`."""
    bundled = [target.name for target in targets if target.origin == BUNDLED]
    own = [target for target in targets if target.origin != BUNDLED]
    text = f"{', '.join([AUTO, *bundled])} ({BUNDLED})"
    if own:
        text += f" and {', '.join(target.name for target in own)} (the {own[0].origin} harness's)"
    return text


def resolve_target(
    requested: Optional[str], default: str, harness: Any,
) -> Tuple[Optional[TargetSkill], List[TargetSkill]]:
    """The target a deploy runs (None under `auto`) and the targets
    offered: the call's name, else the config's default."""
    name = requested if requested is not None else default
    offered = available_targets(harness)
    if name == AUTO:
        return None, offered
    for target in offered:
        if target.name == name:
            return target, offered
    hint = "" if harness is not None else "; no harness is loaded for this build, and a harness's target needs its harness (`--harness <ref>`)"
    raise DeployError(f"deploy(target={name!r}): no such target; the targets are {describe(offered)}{hint}")


def _bounded_exit(command: str, timeout: float) -> Optional[int]:
    """The command's exit code, or None when it has not ended at the
    timeout (killed then, with what it started)."""
    process = subprocess.Popen(
        shlex.split(command), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True,
    )
    thread = threading.Thread(target=process.wait, daemon=True)
    thread.start()
    thread.join(timeout=timeout)
    if thread.is_alive():
        process.kill()
        thread.join()
        return None
    return process.returncode


def probe_failure(target: TargetSkill) -> Optional[str]:
    """Why the target's tool, present on PATH, is not usable: its probe's
    failure or silence, with the fix; None when the probe answers or the
    target has none."""
    probe = (target.requires or {}).get("probe")
    if probe is None:
        return None
    code = _bounded_exit(probe["command"], float(probe["timeout"]))
    if code is None:
        return f"`{probe['command']}` did not answer within {probe['timeout']:g} s: {probe['fix']}"
    if code != 0:
        return f"`{probe['command']}` fails: {probe['fix']}"
    return None


def readiness(target: TargetSkill) -> str:
    """What the machine has for the target, in the words the session reads
    under `auto`: `present` (the tool is on PATH and its probe, when it
    has one, answers), `present, but …` (the probe's failure and its fix),
    `missing: <install>`, `present, needs nothing` (an engine target with
    no tool) or `unverified` (a harness target, whose tools the harness
    declares)."""
    if target.requires is None:
        return "present, needs nothing" if target.origin == BUNDLED else "unverified"
    if shutil.which(target.requires["binary"]) is None:
        return f"missing: {target.requires['install']}"
    failure = probe_failure(target)
    if failure is not None:
        return f"present, but {failure}"
    probe = target.requires.get("probe")
    return "present" if probe is None else f"present, `{probe['command']}` answers"
