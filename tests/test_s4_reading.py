"""S4's driver (docs/plans/redesign/wp9-semantic-suite.md, change 7): the
fact sheet is extracted from a real trace (the second machine's churn
campaign) and the branch's history, renders the six questions, and says
"nothing voided" and "not established" where the record does; the judge's
block grades each reader by the questions right in both passes, the run
by the worst reader."""

import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts" / "redesign"))
spec = importlib.util.spec_from_file_location("s4_reading", ROOT / "scripts" / "redesign" / "s4_reading.py")
s4 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(s4)
TRACE = json.loads((ROOT / "tests" / "fixtures" / "semantic_transcripts" / "churn-trace.json").read_text())


def test_the_fact_sheet_is_extracted_from_the_trace_and_the_history():
    facts = s4.fact_sheet(TRACE, labels=True)
    assert facts["what won"]["branch"] == "generic_exp_0" and facts["what won"]["score"] == 0.847 and facts["what won"]["commit"].startswith("4223437")
    assert facts["what was voided and on what evidence"] == "nothing voided"
    assert facts["what was rejected and why"].startswith("nothing rejected")
    assert facts["what it cost"] == {"usd": 4.0038255, "coverage": "claude_code", "unpriced_runs": 0}
    merge = facts["safe to merge"]
    assert merge["labels_in_history"].startswith("the evaluation's private directory is in the branch's history")
    assert "kapso_evaluation/result.json" in merge["files_changed"] and merge["integrity"] == "no integrity error on the delivered attempt"
    assert s4.fact_sheet(TRACE, labels=None)["safe to merge"]["labels_in_history"].startswith("not established")
    sheet = s4.render_sheet(facts)
    assert all(f"## {key}" in sheet for key, _ in s4.QUESTIONS) and sheet.startswith("# The fact sheet")


def test_the_steps_and_the_questions_match_the_suite():
    assert s4.STEP_NAMES == s4.SUITE["tests"]["S4"]["required_steps"]["claude_code"]
    assert [key for key, _ in s4.QUESTIONS] == s4.SUITE["tests"]["S4"]["judge"]["dimensions"]
    assert all(text in s4.PROMPT for _, text in s4.QUESTIONS) and "not established" in s4.PROMPT


def _item(scores):
    return {key: {"score": score, "evidence": []} for (key, _), score in zip(s4.QUESTIONS, scores)}


def test_the_judges_block_grades_each_reader_by_the_questions_right_in_both_passes():
    record = {"steps": [
        {"name": "fact-sheet", "kind": "shell"},
        {"name": "reading-claude_code", "kind": "reading", "metrics": {"correct": None}},
        {"name": "reading-codex", "kind": "reading", "metrics": {"correct": None}},
    ], "metrics": {}, "judge": {"failure": None, "passes": [
        {"items": {"reading-claude_code": _item([1, 1, 1, 1, 1, 1]), "reading-codex": _item([1, 1, 0, 1, 1, 1])}},
        {"items": {"reading-claude_code": _item([1, 1, 1, 1, 1, 0]), "reading-codex": _item([1, 1, 1, 1, 1, 1])}},
    ]}}
    graded = s4.grade(record)
    assert graded["steps"][1]["metrics"]["correct"] == 5 and graded["steps"][2]["metrics"]["correct"] == 5
    assert graded["metrics"]["readers_correct_min"] == 5
    failed = {"steps": [{"name": "reading-codex", "kind": "reading", "metrics": {"correct": None}}], "metrics": {}, "judge": {"failure": "x", "passes": []}}
    assert s4.grade(failed)["metrics"] == {}
