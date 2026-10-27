"""The plugin's skills and commands (docs/plans/redesign/wp7-plugin.md,
changes 2 to 7): every skill's frontmatter meets the contract both hosts
read, its body stays under the cap, its Codex sidecar is beside it with
the host's own invocability control, every `kapso …` line in a fenced
block parses against the CLI's own parsers and carries the project's
config where the verb takes one, and every command hands over to a skill
that exists."""

import re
import shlex
from pathlib import Path

import pytest
import yaml

from kapso.cli import build_parser
from kapso.cli.learn import normalize_argv

ROOT = Path(__file__).resolve().parent.parent
SKILLS = ROOT / "plugin" / "skills"
COMMANDS = ROOT / "plugin" / "commands"
DESCRIPTION_CAP = 1024          # the skills spec's; Claude Code lists the first 1,536 characters
BODY_CAP = {"kapso": 350}       # lines; every other skill 500
DEFAULT_BODY_CAP = 500
PLACEHOLDER = re.compile(r"<[^>]+>")


def skill_dirs():
    return sorted(path for path in SKILLS.iterdir() if path.is_dir())


def front_matter(path: Path):
    text = path.read_text(encoding="utf-8")
    assert text.startswith("---\n"), path
    head, body = text[4:].split("\n---\n", 1)
    return yaml.safe_load(head), body


def fenced_bash_lines(text: str):
    """The `kapso …` lines of the fenced bash blocks, continuation lines
    joined, comments and prompts stripped."""
    lines = []
    for block in re.findall(r"```(?:bash|sh)\n(.*?)```", text, re.S):
        joined = block.replace("\\\n", " ")
        for raw in joined.splitlines():
            line = raw.split("#", 1)[0].strip()
            if line.startswith("$ "):
                line = line[2:]
            if line.startswith("kapso "):
                lines.append(line)
    return lines


def kapso_lines():
    found = []
    for source in [*sorted(SKILLS.rglob("SKILL.md")), *sorted(COMMANDS.glob("*.md"))] if COMMANDS.exists() else sorted(SKILLS.rglob("SKILL.md")):
        for line in fenced_bash_lines(source.read_text(encoding="utf-8")):
            found.append(pytest.param(source.relative_to(ROOT).as_posix(), line, id=f"{source.parent.name}: {line[:60]}"))
    return found


@pytest.mark.parametrize("skill", skill_dirs(), ids=lambda path: path.name)
def test_a_skills_frontmatter_body_and_sidecar_meet_the_contract(skill):
    data, body = front_matter(skill / "SKILL.md")
    assert data["name"] == skill.name
    description = data["description"]
    assert isinstance(description, str) and len(description) <= DESCRIPTION_CAP, len(description)
    assert "Use when" in description and "Do not use" in description
    assert set(data) <= {"name", "description", "user-invocable"}, sorted(data)   # the spec's core and Claude Code's menu control, nothing a host does not read
    assert len(body.splitlines()) <= BODY_CAP.get(skill.name, DEFAULT_BODY_CAP)
    sidecar = yaml.safe_load((skill / "agents" / "openai.yaml").read_text(encoding="utf-8"))
    interface = sidecar["interface"]
    assert interface["display_name"] and interface["short_description"] and interface["default_prompt"]
    assert isinstance(sidecar["policy"]["allow_implicit_invocation"], bool)
    if data.get("user-invocable") is False:
        # Hidden from Claude Code's menu, still the model's to call; Codex
        # keeps implicit invocation, its own control (no menu to hide from).
        assert sidecar["policy"]["allow_implicit_invocation"] is True


@pytest.mark.parametrize("source, line", kapso_lines())
def test_every_kapso_line_parses_and_carries_the_projects_config(source, line):
    """A line the agent copies must be one the CLI accepts, with
    `--config kapso-config.yaml` wherever the verb takes a config."""
    words = shlex.split(PLACEHOLDER.sub("x", line).replace("…", "x"))
    parser = build_parser()
    args = parser.parse_args(normalize_argv(words[1:]))
    takes_config = "config" in vars(args)
    if takes_config:
        assert args.config == "kapso-config.yaml", f"{source}: {line}"
    else:
        assert "--config" not in words, f"{source}: {line}"


@pytest.mark.skipif(not COMMANDS.exists(), reason="no commands yet")
@pytest.mark.parametrize("command", sorted(COMMANDS.glob("*.md")) if COMMANDS.exists() else [], ids=lambda path: path.stem)
def test_a_command_hands_over_to_a_skill_that_exists(command):
    data, body = front_matter(command)
    assert set(data) == {"description", "argument-hint"}, sorted(data)
    named = re.findall(r"`/kapso:(kapso[a-z-]*)`", body)
    assert named, command
    assert all((SKILLS / name).is_dir() for name in named), named
    assert "$ARGUMENTS" in body
