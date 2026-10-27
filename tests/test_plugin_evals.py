"""The trigger suite under plugin/evals (docs/plans/redesign/wp7-plugin.md,
change 9): every case has a prompt with the pinned limits and at least
one Skill grader; every expected skill exists; each entry skill has its
twenty cases, twelve of its own and eight near misses, with the
confusion cases refusing the skill under test and the no-Kapso cases
refusing every Kapso skill; ten held-out paraphrases apart; the grader
patterns match the Skill tool's input in both its forms."""

import json
import re
from collections import Counter
from pathlib import Path

import yaml

from kapso.core.front_matter import read_front_matter

ROOT = Path(__file__).resolve().parent.parent
EVALS = ROOT / "plugin" / "evals"
SKILLS = {path.name for path in (ROOT / "plugin" / "skills").iterdir() if path.is_dir()}
ENTRY_SKILLS = ("kapso", "kapso-setup", "kapso-build", "kapso-harness", "kapso-review")
MODEL = "claude-opus-5-5"


def _cases():
    found = {}
    for prompt in sorted(EVALS.glob("*/prompt.md")):
        data, body = read_front_matter(prompt)
        graders = {g.stem: read_front_matter(g)[0] for g in sorted((prompt.parent / "graders").glob("*.md"))}
        found[prompt.parent.name] = (data, body.strip(), graders)
    return found


def _fires(pattern, skill):
    return any(re.search(pattern, json.dumps({"skill": name})) for name in (skill, f"kapso:{skill}"))


def test_every_case_is_pinned_and_graded_on_the_skill_tool():
    cases = _cases()
    assert len(cases) == 111
    for name, (data, body, graders) in cases.items():
        assert body, name
        assert data["model"] == MODEL and data["runs"] == 2 and data["max_turns"] == 6 and data["timeout_seconds"] == 180, name
        assert data["allowed_tools"] == ["Read", "Glob", "Grep", "Skill"], name
        assert graders and all(g["type"] == "tool_used" and g["tool"] == "Skill" for g in graders.values()), name
        assert set(data["tags"]) & {"main", "holdout"}, name


def test_each_entry_skill_has_its_twenty_cases_and_the_near_misses_refuse_the_right_thing():
    cases = _cases()
    kinds = Counter()
    for name, (data, body, graders) in cases.items():
        tags = data["tags"]
        kind, skill = tags[1], tags[2]
        kinds[(skill, kind)] += 1
        if kind in ("explicit", "implicit", "holdout"):
            assert set(graders) == {"skill-fired"} and _fires(graders["skill-fired"]["input_match"], skill), name
            assert not _fires(graders["skill-fired"]["input_match"], "kapso-evaluation") or skill == "kapso-evaluation", name
        if kind == "confusion":
            refusal = graders[f"not-{skill}"]
            assert refusal["min"] == 0 and refusal["max"] == 0 and refusal["arm"] == "both", name
            assert _fires(refusal["input_match"], skill), name
            assert not _fires(graders["skill-fired"]["input_match"], skill), name   # the expected skill is another
        if kind == "none":
            [refusal] = graders.values()
            assert refusal["min"] == 0 and refusal["max"] == 0 and refusal["arm"] == "both", name
            assert all(_fires(refusal["input_match"], name) for name in SKILLS), name
            assert "kapso" not in body.lower(), name
        if kind == "explicit":
            assert body.startswith("/kapso:"), name
    for skill in ENTRY_SKILLS:
        assert kinds[(skill, "explicit")] + kinds[(skill, "implicit")] >= 12, skill
        assert kinds[(skill, "confusion")] == 4 and kinds[(skill, "none")] == 4, skill
        assert kinds[(skill, "holdout")] == 2, skill
    assert sum(count for (skill, kind), count in kinds.items() if kind == "holdout") == 10


def test_the_skill_patterns_tell_the_six_apart():
    cases = _cases()
    pattern = cases["kapso-i01"][2]["skill-fired"]["input_match"]
    assert _fires(pattern, "kapso") and not any(_fires(pattern, other) for other in SKILLS - {"kapso"})
    pattern = cases["build-i01"][2]["skill-fired"]["input_match"]
    assert _fires(pattern, "kapso-build") and not _fires(pattern, "kapso") and not _fires(pattern, "kapso-evaluation")
    explicit = cases["setup-e01"][2]["skill-fired"]["input_match"]
    assert _fires(explicit, "setup") and _fires(explicit, "kapso-setup") and not _fires(explicit, "kapso-build")
