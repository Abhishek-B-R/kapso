"""The author test's core (docs/plans/redesign/wp9-semantic-suite.md,
change 11): the guess grammar parses, a malformed `GUESS:` line raises
(Rule 2), the classification's shape is validated against the four
classes with one entry per guess, the structural-gap count drives the
bar, and the rubric is the design's words (drift)."""

import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts" / "redesign"))
spec = importlib.util.spec_from_file_location("author_test", ROOT / "scripts" / "redesign" / "author_test.py")
author = importlib.util.module_from_spec(spec)
spec.loader.exec_module(author)
import judge as judge_module  # noqa: E402


def test_the_guess_grammar_parses_and_a_malformed_guess_line_raises():
    text = (
        "# Guesses\n"
        "GUESS: the manifest key for skills is `skills` | write.mdx, the manifest section | chose `skills: [list]`\n"
        "prose that is not a guess\n"
        "GUESS: hooks live under hooks/<name>/ | the example | chose hooks/<name>/hook.json\n"
    )
    guesses = author.parse_guesses(text)
    assert [g.index for g in guesses] == [1, 2]
    assert guesses[0].what.startswith("the manifest key") and guesses[0].where == "write.mdx, the manifest section" and guesses[0].chose == "chose `skills: [list]`"
    with pytest.raises(ValueError, match="line 1"):
        author.parse_guesses("GUESS: only one field with no pipes\n")
    assert author.parse_guesses("no guesses here\n") == []


def test_the_classification_shape_is_validated_and_counts_structural_gaps():
    guesses = author.parse_guesses(
        "GUESS: a | w | c\nGUESS: b | w | c\nGUESS: d | w | c\n"
    )

    def ask_good(prompt, settings):
        assert "THE GUIDE" in prompt and "THE GUESSES" in prompt
        return json.dumps({"classifications": [
            {"index": 1, "class": "structural_gap", "why": "the guide never names the key"},
            {"index": 2, "class": "already_in_guide", "why": "write.mdx says it"},
            {"index": 3, "class": "domain_decision", "why": "a dbt choice"},
        ]})

    classified = author.classify_guesses(guesses, "GUIDE TEXT", {}, ask=ask_good)
    assert [row["class"] for row in classified] == ["structural_gap", "already_in_guide", "domain_decision"]
    assert author.structural_gaps(classified) == 1 and len(author.contradictions(classified)) == 0

    def ask_short(prompt, settings):
        return json.dumps({"classifications": [{"index": 1, "class": "structural_gap", "why": "x"}]})

    with pytest.raises(judge_module.JudgeFailure, match="1 entries for 3"):
        author.classify_guesses(guesses, "G", {}, ask=ask_short)

    def ask_bad_class(prompt, settings):
        return json.dumps({"classifications": [{"index": i + 1, "class": "nope", "why": "x"} for i in range(3)]})

    with pytest.raises(judge_module.JudgeFailure, match="bad classification"):
        author.classify_guesses(guesses, "G", {}, ask=ask_bad_class)
    assert author.classify_guesses([], "G", {}, ask=ask_good) == []


def test_the_run_metrics_promote_round_two_and_the_steps_match_the_suite():
    record = {"steps": [
        {"name": "round-1", "metrics": {"structural_gaps": 7, "check_green": True}},
        {"name": "guide-fixes", "metrics": {"fixes_from_round1": 5}},
        {"name": "round-2", "metrics": {"structural_gaps": 0, "check_green": True}},
    ]}
    assert author.run_metrics(record) == {"structural_gaps_round1": 7, "structural_gaps_round2": 0, "check_green_round2": 1}
    red = {"steps": [{"name": "round-2", "metrics": {"structural_gaps": 2, "check_green": False}}]}
    assert author.run_metrics(red) == {"structural_gaps_round1": None, "structural_gaps_round2": 2, "check_green_round2": 0}
    assert author.STEP_NAMES == author.SUITE["tests"]["author"]["required_steps"]["claude_code"]
    assert set(author.SUITE["tests"]["author"]["bars"]) == {"structural_gaps_round2", "check_green_round2"}


def test_the_author_rubric_is_the_designs_words():
    rubric = (ROOT / "tests" / "semantic" / "rubrics" / "author.md").read_text(encoding="utf-8")
    for dimension in author.SUITE["tests"]["author"]["judge"]["dimensions"]:
        assert f"**{dimension}**" in rubric, dimension
    assert "structural gap" in rubric and "contradiction" in rubric
