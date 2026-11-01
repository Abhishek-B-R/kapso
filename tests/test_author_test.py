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


def test_the_run_metrics_read_the_write_step_and_the_steps_match_the_suite():
    record = {"steps": [{"name": "write", "metrics": {"structural_gaps": 0, "contradictions": 0, "check_green": True}}]}
    assert author.run_metrics(record) == {"structural_gaps": 0, "contradictions": 0, "check_green": 1}
    red = {"steps": [{"name": "write", "metrics": {"structural_gaps": 2, "contradictions": 1, "check_green": False}}]}
    assert author.run_metrics(red) == {"structural_gaps": 2, "contradictions": 1, "check_green": 0}
    ungraded = {"steps": [{"name": "write", "metrics": {"structural_gaps": None, "contradictions": None, "check_green": True}}]}
    assert author.run_metrics(ungraded) == {"structural_gaps": None, "contradictions": None, "check_green": 1}
    assert author.run_metrics({"steps": []}) == {"structural_gaps": None, "contradictions": None, "check_green": None}
    assert author.STEP_NAMES == author.SUITE["tests"]["author"]["required_steps"]["claude_code"]
    assert set(author.SUITE["tests"]["author"]["bars"]) == {"structural_gaps", "check_green"}


def test_the_author_rubric_scores_only_the_harness_and_the_classifier_owns_the_classes():
    rubric = (ROOT / "tests" / "semantic" / "rubrics" / "author.md").read_text(encoding="utf-8")
    for dimension in author.SUITE["tests"]["author"]["judge"]["dimensions"]:
        assert f"**{dimension}**" in rubric, dimension
    # The guess classification is NOT asked of the harness judge (its JSON
    # contract rejects extra output); it lives in the author test's classifier.
    assert "classified separately" in rubric
    assert "structural_gap" in author.CLASSIFY and "contradiction" in author.CLASSIFY


def test_the_classifier_runs_twice_and_a_straddling_guess_is_adjudicated(tmp_path):
    # The test's one hard bar (structural gaps, max 0) rested on one
    # unblinded call; now two blind passes, and a third for each guess the
    # passes read differently on the one thing the bar counts.
    guesses = author.parse_guesses("GUESS: a | w | c\nGUESS: b | w | c\nGUESS: d | w | c\n")
    calls = []

    def ask(prompt, settings):
        calls.append(prompt)
        if len(calls) == 1:
            rows = [("structural_gap", 1), ("already_in_guide", 2), ("domain_decision", 3)]
        elif len(calls) == 2:
            rows = [("structural_gap", 1), ("structural_gap", 2), ("domain_decision", 3)]
        else:
            assert "2. GUESS: b" in prompt and "1. GUESS: a" not in prompt, "only the straddling guess is adjudicated"
            rows = [("already_in_guide", 2)]
        return json.dumps({"classifications": [{"index": index, "class": cls, "why": "because"} for cls, index in rows]})

    merged = author.classify_twice(guesses, "GUIDE", {}, ask, tmp_path)
    assert [row["class"] for row in merged] == ["structural_gap", "already_in_guide", "domain_decision"]
    assert [row["adjudicated"] for row in merged] == [False, True, False] and merged[1]["passes"] == ["already_in_guide", "structural_gap"]
    assert author.structural_gaps(merged) == 1 and (tmp_path / "classify-write-adjudication.txt").is_file()
    with pytest.raises(judge_module.JudgeFailure, match="straddled the bar"):
        author.merge_classifications(merged[:1], [{**merged[0], "class": "domain_decision"}], [])


def test_a_grade_against_a_guide_other_than_the_one_the_author_read_raises(tmp_path):
    (tmp_path / "artifacts").mkdir()
    (tmp_path / "artifacts" / "guide.md").write_text("the guide as read", encoding="utf-8")
    record = {"steps": [{"name": "write", "metrics": {}}], "pins": {"guide_sha256": "0" * 64}, "metrics": {}}
    with pytest.raises(RuntimeError, match="not the run's pin"):
        author.grade(record, tmp_path, tmp_path, {}, ask=lambda prompt, settings: "{}")
    import hashlib
    record["pins"]["guide_sha256"] = hashlib.sha256(b"the guide as read").hexdigest()
    graded = author.grade(record, tmp_path, tmp_path, {}, ask=lambda prompt, settings: json.dumps({"classifications": []}))
    assert graded["metrics"]["structural_gaps"] == 0, "no guess: a complete run with nothing undecided"
