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

import shutil
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


@dataclass(frozen=True)
class TargetSkill:
    name: str
    path: Path
    description: str
    # The tool the deploying machine needs, `{binary, install}`: read from
    # the engine's own targets only (a harness declares its tools in
    # harness.yaml's environment, which `check` reads).
    requires: Optional[Dict[str, str]]
    origin: str   # BUNDLED, or the harness's name

    def script(self, name: str) -> Path:
        return self.path / SCRIPTS_DIR / name

    def has_script(self, name: str) -> bool:
        return self.script(name).is_file()


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
    requires = None
    if engine:
        requires = (data.get("metadata") or {}).get("requires")
        if requires is not None and (
            not isinstance(requires, dict)
            or not isinstance(requires.get("binary"), str)
            or not isinstance(requires.get("install"), str)
        ):
            raise DeployError(f"{file}: metadata.requires is a mapping with `binary` and `install`")
    return TargetSkill(path.name, path, description.strip(), dict(requires) if requires else None, origin)


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
    """The bundled targets, then the harness's; a harness target named
    like a bundled one or `auto` is refused."""
    bundled = bundled_targets()
    taken = {target.name for target in bundled} | {AUTO}
    own = harness_targets(harness)
    for target in own:
        if target.name in taken:
            raise DeployError(
                f"harness {harness.name}: its deployment skill `{target.name}` is named like a bundled "
                f"target; rename it"
            )
    return bundled + own


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
    raise DeployError(f"deploy(target={name!r}): no such target; the targets are {describe(offered)}")


def readiness(target: TargetSkill) -> str:
    """What the machine has for the target: `present` (the tool is on PATH,
    or the engine's target needs none), `missing: <install>`, or
    `unverified` (a harness target, whose tools the harness declares)."""
    if target.requires is None:
        return "present, needs nothing" if target.origin == BUNDLED else "unverified"
    if shutil.which(target.requires["binary"]) is None:
        return f"missing: {target.requires['install']}"
    return "present"
