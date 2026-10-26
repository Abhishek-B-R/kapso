"""The deployment targets as skills (docs/plans/redesign/wp5-deploy.md,
change 1): the five bundled targets meet the skill contract and ship in
the package; a harness target is a deployment skill holding
scripts/deploy.sh; the resolution and its refusals."""

import shutil
from pathlib import Path

import pytest

from kapso.core.config import load_config
from kapso.deployment.errors import DeployError
from kapso.deployment.targets import (
    AUTO,
    BUNDLED,
    BUNDLED_DIR,
    DEPLOY_SCRIPT,
    LIFECYCLE_SCRIPTS,
    RUN_SCRIPT,
    available_targets,
    bundled_targets,
    describe,
    harness_targets,
    readiness,
    resolve_target,
)
from kapso.harness import load_harness

ROOT = Path(__file__).resolve().parent.parent
TRADING = ROOT / "examples" / "harnesses" / "trading"
BUNDLED_NAMES = ["bentoml", "docker", "langgraph", "local", "modal"]


def trading_with_target(tmp_path, *, shadow=None):
    """The trading example, its paper-trading skill given the deploy
    script that makes it a target; `shadow` adds a deployment skill of
    that name beside it."""
    copy = tmp_path / "trading"
    shutil.copytree(TRADING, copy)
    scripts = copy / "skills" / "paper-trading" / "scripts"
    scripts.mkdir(exist_ok=True)
    (scripts / DEPLOY_SCRIPT).write_text("echo deployed\n")
    if shadow:
        skill = copy / "skills" / shadow
        (skill / "scripts").mkdir(parents=True)
        (skill / "SKILL.md").write_text(f"---\nname: {shadow}\ndescription: a shadow. Use when never.\n---\n# {shadow}\n")
        (skill / "scripts" / DEPLOY_SCRIPT).write_text("exit 0\n")
        manifest = copy / "harness.yaml"
        manifest.write_text(manifest.read_text().replace(
            "    skills: [market-data, paper-trading]", f"    skills: [market-data, paper-trading, {shadow}]",
        ))
    return load_harness(str(copy), settings=dict(load_config()["harness"], store=str(tmp_path / "store")), say=lambda line: None)


def test_the_five_bundled_targets_meet_the_skill_contract():
    targets = bundled_targets()
    assert [target.name for target in targets] == BUNDLED_NAMES
    for target in targets:
        assert target.origin == BUNDLED and target.path == BUNDLED_DIR / target.name
        # The choosing criteria, in the form the session reads under auto.
        assert "Use when" in target.description
        assert target.has_script(DEPLOY_SCRIPT)
    by_name = {target.name: target for target in targets}
    # The engine's own targets declare their tool; local needs none.
    assert by_name["local"].requires is None
    assert by_name["docker"].requires["binary"] == "docker" and "docker" in by_name["docker"].requires["install"]
    for name in ("modal", "bentoml", "langgraph"):
        assert by_name[name].requires["binary"] == name and f"[{name}]" in by_name[name].requires["install"]
    # The lifecycle every target with a runtime of its own manages; local
    # leaves it to the engine's worker.
    for name in ("docker", "modal", "bentoml", "langgraph"):
        assert all(by_name[name].has_script(script) for script in LIFECYCLE_SCRIPTS), name
    assert not any(by_name["local"].has_script(script) for script in LIFECYCLE_SCRIPTS)
    # The script kind's call, on the targets the SDKs serve.
    assert [name for name in BUNDLED_NAMES if by_name[name].has_script(RUN_SCRIPT)] == ["bentoml", "langgraph", "modal"]


def test_the_package_carries_the_targets():
    """A wheel built with the extension globs alone would ship SKILL.md
    without the scripts: the directories are named whole."""
    assert '"kapso.deployment" = ["targets/**/*"]' in (ROOT / "pyproject.toml").read_text()
    assert "recursive-include src/kapso/deployment/targets *" in (ROOT / "MANIFEST.in").read_text()


def test_resolution_takes_the_call_then_the_config():
    target, offered = resolve_target("docker", "auto", None)
    assert target.name == "docker" and [t.name for t in offered] == BUNDLED_NAMES
    assert resolve_target(None, "local", None)[0].name == "local"
    assert resolve_target(None, AUTO, None)[0] is None
    assert resolve_target(AUTO, "local", None)[0] is None
    with pytest.raises(DeployError, match=r"deploy\(target='k8s'\): no such target; the targets are auto, bentoml, docker, langgraph, local, modal \(bundled\)$"):
        resolve_target("k8s", "auto", None)


def test_a_harness_target_is_a_deployment_skill_holding_the_deploy_script(tmp_path):
    harness = trading_with_target(tmp_path)
    [target] = harness_targets(harness)
    # market-data is listed on the deployment module as a reference, with
    # no scripts/deploy.sh: not a target.
    assert target.name == "paper-trading" and target.origin == "trading" and target.requires is None
    assert readiness(target) == "unverified"
    offered = available_targets(harness)
    assert describe(offered) == "auto, bentoml, docker, langgraph, local, modal (bundled) and paper-trading (the trading harness's)"
    assert resolve_target("paper-trading", "auto", harness)[0].path == harness.path / "skills" / "paper-trading"
    with pytest.raises(DeployError, match=r"\(bundled\) and paper-trading \(the trading harness's\)$"):
        resolve_target("market-data", "auto", harness)


def test_a_harness_target_named_like_a_bundled_one_is_refused(tmp_path):
    harness = trading_with_target(tmp_path, shadow="docker")
    with pytest.raises(DeployError, match="harness trading: its deployment skill `docker` is named like a bundled target"):
        available_targets(harness)


def test_readiness_names_the_missing_tool(monkeypatch):
    docker = next(target for target in bundled_targets() if target.name == "docker")
    monkeypatch.setattr("kapso.deployment.targets.shutil.which", lambda name: None)
    assert readiness(docker) == "missing: install Docker: https://docs.docker.com/get-docker/ (and start its daemon)"
    monkeypatch.setattr("kapso.deployment.targets.shutil.which", lambda name: f"/usr/bin/{name}")
    assert readiness(docker) == "present"
