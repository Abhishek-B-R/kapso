"""The staging's engine skills (docs/plans/redesign/wp5-deploy.md, change
4): the engine's own skill directories (the deployment session's
targets) staged beside a harness's skills or with no harness at all, on
either host, named in the record, left alone by another module's staging,
and opened with the host's own syntax."""

import json
import shutil
from pathlib import Path

import pytest

from kapso.core.config import load_config
from kapso.harness import HarnessError, load_harness, stage_harness
from kapso.harness.staging import open_skill_instruction

TRADING = Path(__file__).resolve().parent.parent / "examples" / "harnesses" / "trading"
SKILLS_DIR = {"claude_code": ".claude/skills", "codex": ".agents/skills"}


@pytest.fixture
def engine_skills(tmp_path):
    skills = []
    for name in ("alpha", "beta"):
        skill = tmp_path / "engine" / name
        (skill / "scripts").mkdir(parents=True)
        (skill / "SKILL.md").write_text(f"---\nname: {name}\ndescription: the {name} target. Use when testing.\n---\n")
        (skill / "scripts" / "deploy.sh").write_text("exit 0\n")
        skills.append(skill)
    return skills


@pytest.fixture
def harness(tmp_path):
    copy = tmp_path / "h" / "trading"
    shutil.copytree(TRADING, copy)
    return load_harness(str(copy), settings=dict(load_config()["harness"], store=str(tmp_path / "store")), say=lambda line: None)


@pytest.mark.parametrize("host", ["claude_code", "codex"])
def test_without_a_harness_the_engine_skills_land_and_the_record_names_them(tmp_path, engine_skills, host):
    campaign = tmp_path / "campaign"
    workspace = campaign / ".kapso" / "deployments" / "1" / "workspace"
    workspace.mkdir(parents=True)
    staged = stage_harness(
        None, "deployment", session_dir=workspace, campaign_dir=campaign, session_id="deployment/1", host=host,
        engine_skills=engine_skills,
    )
    for name in ("alpha", "beta"):
        assert (workspace / SKILLS_DIR[host] / name / "SKILL.md").is_file()
        assert (workspace / SKILLS_DIR[host] / name / "scripts" / "deploy.sh").is_file()
    record = json.loads(staged.record_path.read_text())
    assert record["harness"] is None and record["skills"] == [] and record["engine_skills"] == ["alpha", "beta"]
    assert staged.guidance == "" and staged.record_path == campaign / ".kapso" / "sessions" / "deployment" / "1" / "session.json"


def test_with_a_harness_the_engine_skills_sit_beside_the_modules_and_survive_another_staging(tmp_path, engine_skills, harness):
    campaign = tmp_path / "campaign"
    workspace = campaign / "ws"
    workspace.mkdir(parents=True)
    staged = stage_harness(
        harness, "deployment", session_dir=workspace, campaign_dir=campaign, session_id="deployment/1",
        host="claude_code", engine_skills=engine_skills[:1],
    )
    skills = workspace / ".claude" / "skills"
    assert sorted(p.name for p in skills.iterdir()) == ["alpha", "market-data", "paper-trading"]
    assert staged.record["skills"] == ["market-data", "paper-trading"] and staged.record["engine_skills"] == ["alpha"]
    # The guidance is the harness's: the engine's targets are the prompt's
    # own list, rendered with the host's syntax.
    assert "- paper-trading — " in staged.guidance and "alpha" not in staged.guidance
    # Another module staged into the same directory removes the harness's
    # skills it does not list and leaves the engine's.
    stage_harness(harness, "ideation", session_dir=workspace, campaign_dir=campaign, session_id="ideation", host="claude_code")
    assert sorted(p.name for p in skills.iterdir()) == ["alpha", "market-structure", "strategy-families"]


def test_the_hosts_own_way_to_open_a_skill():
    assert open_skill_instruction("claude_code", "docker") == "/docker"
    assert open_skill_instruction("codex", "docker") == "$docker"
    with pytest.raises(HarnessError, match="unknown host 'gemini'"):
        open_skill_instruction("gemini", "docker")
    with pytest.raises(HarnessError, match="unknown host 'gemini'"):
        stage_harness(None, "deployment", session_dir=Path("/tmp"), campaign_dir=Path("/tmp"), session_id="d", host="gemini", engine_skills=[Path("/tmp")])
