"""The judge (docs/plans/redesign/wp9-semantic-suite.md, change 5): the
rubrics carry the design's dimensions by name (a drift check); a step is
rendered as the user's messages and each turn's final text, on both
hosts' real row shapes, with numbered lines; the reply must be one JSON
object with exactly the rubric's dimensions, integer scores in the scale,
and at least one evidence entry whose quote is on the line it names in the
material's own file, else a judge failure that keeps the raw reply and
never passes; a conversation step is judged with all of its transcripts;
a missing one raises; two passes, each straddling item adjudicated; the
pending block is non-passing until the judging completes; the preflight
reads one JSON object. The model call is the one mock."""

import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("judge", ROOT / "scripts" / "redesign" / "judge.py")
judge = importlib.util.module_from_spec(spec)
spec.loader.exec_module(judge)
SUITE = judge.load_suite()
FIXTURES = ROOT / "tests" / "fixtures" / "semantic_transcripts"
DIMENSIONS = SUITE["tests"]["S2"]["judge"]["dimensions"]
WATCH = "judge/watch.rendered.md"


def test_the_rubrics_carry_the_designs_dimensions_by_name():
    for test, rubric in (("S2", "s2"), ("S4", "s4"), ("S1", "s1"), ("author", "author")):
        text = (judge.RUBRICS / f"{rubric}.md").read_text()
        for dimension in SUITE["tests"][test]["judge"]["dimensions"]:
            assert f"**{dimension}**" in text, (rubric, dimension)
    assert "findings the user did not know, with evidence" in (judge.RUBRICS / "s2.md").read_text()
    assert "a loader that ingests" in (judge.RUBRICS / "s1.md").read_text()


def test_a_step_is_rendered_as_the_users_messages_and_each_turns_final_text_on_both_hosts():
    claude = judge.final_texts(judge.transcript_rows(FIXTURES / "claude_code-watch.jsonl"))
    assert [turn["role"] for turn in claude] == ["user", "assistant", "user"]
    assert claude[0]["text"] == "/kapso:watch ../churn-campaign" and claude[1]["text"].startswith("**Running**") and claude[2]["text"].startswith("thanks")
    codex = judge.final_texts(judge.transcript_rows(FIXTURES / "codex-watch.jsonl"))
    assert [turn["role"] for turn in codex] == ["user", "assistant"] * 4, "the last agent message before the next prompt is the turn's final text"
    rendered = judge.render_step("watch", judge.transcript_rows(FIXTURES / "claude_code-watch.jsonl"))
    assert rendered.startswith("L1: # step watch\n") and "L3: [user]\nL4: /kapso:watch ../churn-campaign\n" in rendered


def test_the_reply_must_be_one_json_object_with_the_rubrics_dimensions_and_evidence_on_its_line(tmp_path):
    rendered = tmp_path / "judge" / "watch.rendered.md"
    rendered.parent.mkdir()
    rendered.write_text("L1: # step watch\nL2: \nL3: [assistant]\nL4: Running, iteration 1 in ideation; no score yet.\n")
    good = {"scores": {d: {"score": 4, "evidence": [{"where": f"{WATCH}:L4", "quote": "no score yet"}]} for d in DIMENSIONS}}
    assert judge.validate(judge.extract_json("```json\n" + json.dumps(good) + "\n```"), DIMENSIONS, [1, 5], tmp_path, [WATCH])["clear"]["score"] == 4
    with pytest.raises(judge.JudgeFailure, match="not one JSON object"):
        judge.extract_json("Here are my scores: {}")
    with pytest.raises(judge.JudgeFailure, match="not valid JSON"):
        judge.extract_json("{not json,}")
    with pytest.raises(judge.JudgeFailure, match="the dimensions are"):
        judge.validate({"scores": {"clear": {"score": 4, "evidence": [{"where": f"{WATCH}:L4", "quote": "no score yet"}]}}}, DIMENSIONS, [1, 5], tmp_path, [WATCH])
    with pytest.raises(judge.JudgeFailure, match="evidence is empty"):
        judge.validate({"scores": {d: {"score": 4, "evidence": []} for d in DIMENSIONS}}, DIMENSIONS, [1, 5], tmp_path, [WATCH])
    wrong = json.loads(json.dumps(good))
    wrong["scores"]["clear"]["score"] = 6
    with pytest.raises(judge.JudgeFailure, match=r"clear: the score 6 is not an integer in \[1, 5\]"):
        judge.validate(wrong, DIMENSIONS, [1, 5], tmp_path, [WATCH])
    wrong = json.loads(json.dumps(good))
    wrong["scores"]["clear"]["evidence"] = [{"where": f"{WATCH}:L4", "quote": "the best score is 0.9"}]
    with pytest.raises(judge.JudgeFailure, match="is not on"):
        judge.validate(wrong, DIMENSIONS, [1, 5], tmp_path, [WATCH])
    wrong = json.loads(json.dumps(good))
    wrong["scores"]["clear"]["evidence"] = [{"where": "judge/elsewhere.md:L1", "quote": "x"}]
    with pytest.raises(judge.JudgeFailure, match="not the material"):
        judge.validate(wrong, DIMENSIONS, [1, 5], tmp_path, [WATCH])


def _record_dir(tmp_path, extra_transcripts=()):
    record_dir = tmp_path / "run"
    (record_dir / "transcripts").mkdir(parents=True)
    (record_dir / "transcripts" / "watch.jsonl").write_text((FIXTURES / "claude_code-watch.jsonl").read_text())
    for name in extra_transcripts:
        (record_dir / "transcripts" / name).write_text((FIXTURES / "claude_code-watch.jsonl").read_text())
    (record_dir / "record.json").write_text(json.dumps({
        "test": "S2", "host": "claude_code", "steps": [{"name": "watch", "kind": "conversation", "completed": True}, {"name": "triggers", "kind": "shell", "completed": True}],
    }))
    return record_dir


def _reply(scores):
    return json.dumps({"scores": {d: {"score": score, "evidence": [{"where": f"{WATCH}:L4", "quote": "/kapso:watch"}]} for d, score in zip(DIMENSIONS, scores)}})


def test_two_passes_judge_every_conversation_step_with_all_its_transcripts_and_a_straddle_is_adjudicated(tmp_path, monkeypatch):
    record_dir = _record_dir(tmp_path, extra_transcripts=("watch-2.jsonl",))
    replies = [_reply([5, 3, 5, 5, 5]), _reply([5, 5, 5, 5, 5]), _reply([5, 4, 5, 5, 5])]
    prompts = []
    monkeypatch.setattr(judge, "ask", lambda prompt, settings: (prompts.append(prompt), replies.pop(0))[1])
    block = judge.judge_record(record_dir, "s2", None, SUITE)
    assert block["failure"] is None and len(block["passes"]) == 2
    assert [p["items"]["watch"]["clear"]["score"] for p in block["passes"]] == [3, 5]
    assert block["adjudication"] == {"clear|watch": {"score": 4, "evidence": [{"where": f"{WATCH}:L4", "quote": "/kapso:watch"}]}}
    assert len(prompts) == 3 and "five dimensions" in prompts[0].lower() and "L4: /kapso:watch ../churn-campaign" in prompts[0]
    # The follow-up transcript was folded into the same rendered material.
    assert "watch-2" not in block["passes"][0]["items"] and (record_dir / "judge" / "watch.rendered.md").read_text().count("/kapso:watch ../churn-campaign") == 2
    written = json.loads((record_dir / "record.json").read_text())["judge"]
    assert written["model"] == SUITE["judge"]["model"] and (record_dir / "judge" / "raw-watch-pass1.txt").is_file()
    assert "triggers" not in written["passes"][0]["items"], "a shell step is not a conversation"


def test_a_malformed_reply_is_a_judge_failure_with_the_raw_reply_kept_never_a_pass(tmp_path, monkeypatch):
    record_dir = _record_dir(tmp_path)
    monkeypatch.setattr(judge, "ask", lambda prompt, settings: "I would rate this 4/5 overall.")
    with pytest.raises(judge.JudgeFailure, match="not one JSON object"):
        judge.judge_record(record_dir, "s2", None, SUITE)
    # The raw reply is kept and the on-disk record carries a non-passing
    # pending block, never a stale pass.
    assert (record_dir / "judge" / "raw-watch-pass1.txt").read_text() == "I would rate this 4/5 overall."
    assert json.loads((record_dir / "record.json").read_text())["judge"]["failure"] == "judging did not complete"
    with pytest.raises(ValueError, match="is judged by the rubric 's2', not 's4'"):
        judge.judge_record(record_dir, "s4", None, SUITE)


def test_a_conversation_step_with_no_transcript_raises(tmp_path):
    record_dir = tmp_path / "run"
    (record_dir / "transcripts").mkdir(parents=True)
    (record_dir / "record.json").write_text(json.dumps({"test": "S2", "host": "claude_code", "steps": [{"name": "watch", "kind": "conversation", "completed": True}]}))
    with pytest.raises(judge.JudgeFailure, match="watch has no transcript"):
        judge.gather_materials(record_dir, json.loads((record_dir / "record.json").read_text()), None, record_dir / "judge")


def test_main_prints_the_per_item_summary_without_crashing(tmp_path, monkeypatch, capsys):
    # main() runs the judge then prints a per-item, per-dimension summary over
    # the block it wrote; the summary must read the block's `items` shape, not
    # the model reply's `scores` key (a crash there aborts the runner's grade).
    record_dir = _record_dir(tmp_path)
    replies = [_reply([5, 5, 5, 5, 5]), _reply([5, 5, 5, 5, 5])]
    monkeypatch.setattr(judge, "ask", lambda prompt, settings: replies.pop(0))
    assert judge.main([str(record_dir), "--rubric", "s2"]) == 0
    out = capsys.readouterr().out
    assert f"watch / {DIMENSIONS[0]}: [5, 5]" in out


def test_the_preflight_reads_one_json_object(monkeypatch):
    monkeypatch.setattr(judge, "ask", lambda prompt, settings: '{"ok": true}')
    assert judge.preflight(SUITE).startswith("the judge's route answers")
    monkeypatch.setattr(judge, "ask", lambda prompt, settings: "ok")
    with pytest.raises(judge.JudgeFailure):
        judge.preflight(SUITE)
