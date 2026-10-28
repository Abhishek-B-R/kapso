"""The plugin round with the persona (docs/plans/redesign/wp9-semantic-
suite.md, change 4): every host turn is offered to the persona, DONE ends
the step as an event, the turn cap ends it as an event never a pass, both
sides land in the transcript; the scripted loop still ends on a turn that
does not ask; the planted baseline is read from the transcript; an
evaluator a session wrote is held to the fixtures' contract; the deployed
call's parity is read from the deployment's observed row against the
delivered predictions; the record's user block carries the pins."""

import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts" / "redesign"))
spec = importlib.util.spec_from_file_location("plugin_proof", ROOT / "scripts" / "redesign" / "plugin_proof.py")
proof = importlib.util.module_from_spec(spec)
spec.loader.exec_module(proof)


class FakeHost:
    name = "claude_code"

    def __init__(self, answers):
        self.answers = list(answers)
        self.prompts = []

    def turn(self, cwd, prompt, session, transcript):
        self.prompts.append(prompt)
        text, asked = self.answers.pop(0)
        with open(transcript, "a", encoding="utf-8") as out:
            out.write(json.dumps({"proof_prompt": prompt}) + "\n" + json.dumps({"type": "result", "result": text}) + "\n")
        return proof.Turn(text, 1.0, "s-1", [], asked)


def _context(tmp_path, host, user):
    ctx = proof.Context(host, ROOT, tmp_path / "work", tmp_path / "out", None, "test-box", user=user)
    (tmp_path / "work").mkdir(exist_ok=True)
    return ctx


def _persona(monkeypatch, replies):
    user = proof.UserMode("persona:ml-engineer", "claude_code")
    queue = list(replies)

    def next_message(card, task_dir, intent, history, host_message, host, settings):
        text = queue.pop(0)
        next_message.calls.append({"intent": intent, "history": list(history), "host_message": host_message})
        return proof.simulated_user.Reply(text=text, done=text == "DONE", session="p-1", seconds=0.0)
    next_message.calls = []
    monkeypatch.setattr(proof.simulated_user, "next_message", next_message)
    return user, next_message


def test_the_persona_is_offered_every_turn_and_done_ends_the_step_as_an_event(tmp_path, monkeypatch):
    user, persona = _persona(monkeypatch, ["go", "DONE"])
    host = FakeHost([("Here is the proposal. Shall I launch?", True), ("Launched. Follow with kapso watch.", False)])
    ctx = _context(tmp_path, host, user)
    (tmp_path / "work" / "README.md").write_text("# task\n")
    turns = ctx.converse("build-churn", tmp_path / "work", "/kapso:build get the AUC up", proof.go_policy, max_turns=4)
    assert [turn.text for turn in turns] == ["Here is the proposal. Shall I launch?", "Launched. Follow with kapso watch."]
    assert host.prompts == ["/kapso:build get the AUC up", "go"], "the persona's reply is the next prompt"
    assert persona.calls[0]["intent"] == proof.STEP_INTENTS["build-churn"]
    assert [turn["role"] for turn in persona.calls[1]["history"]] == ["user", "assistant", "user", "assistant"], "the whole history is offered"
    assert user.events == ["build-churn: the persona said DONE after 2 turn(s)"]
    transcript = (tmp_path / "out" / "transcripts" / "build-churn.jsonl").read_text()
    assert '"persona_reply": "go"' in transcript and '"done": true' in transcript


def test_the_turn_cap_ends_the_step_as_an_event_never_a_pass(tmp_path, monkeypatch):
    user, _ = _persona(monkeypatch, ["more", "more", "more", "more", "more", "more", "more", "more"])
    host = FakeHost([("Question?", True)] * 8)
    ctx = _context(tmp_path, host, user)
    turns = ctx.converse("watch", tmp_path / "work", "/kapso:watch", lambda t, i: None, max_turns=8)
    assert len(turns) == 8 and user.events[-1].endswith("the step is incomplete") and "watch" in user.capped
    # The cap makes even a satisfied-looking predicate incomplete.
    assert user.ended_well("watch", True) is False and user.ended_well("other", True) is True


def test_the_scripted_loop_still_ends_on_a_turn_that_does_not_ask(tmp_path):
    host = FakeHost([("Proposal. Go?", True), ("Launched.", False), ("never reached", True)])
    ctx = _context(tmp_path, host, proof.UserMode("scripted", "claude_code"))
    turns = ctx.converse("build-churn", tmp_path / "work", "/kapso:build x", proof.go_policy, max_turns=4)
    assert [turn.text for turn in turns] == ["Proposal. Go?", "Launched."] and host.prompts[1] == "go"
    with pytest.raises(ValueError, match="scripted or persona"):
        proof.UserMode("robot", "claude_code")


def test_the_planted_baseline_is_read_from_the_transcript(tmp_path):
    transcript = tmp_path / "build-churn.jsonl"
    rows = [{"type": "result", "result": "The baseline is 0.90 per the brief; target 0.85. Go?"}, {"persona_reply": "No: it's about 0.80 (0.797 held out). Fix the baseline, then go.", "done": False}]
    transcript.write_text("\n".join(json.dumps(row) for row in rows) + "\n")
    assert proof.pushed_back(transcript) is True
    rows[1] = {"persona_reply": "go", "done": False}
    transcript.write_text("\n".join(json.dumps(row) for row in rows) + "\n")
    assert proof.pushed_back(transcript) is False
    transcript.write_text(json.dumps({"type": "result", "result": "The baseline is 0.797. Go?"}) + "\n" + json.dumps({"persona_reply": "go"}) + "\n")
    assert proof.pushed_back(transcript) is None, "nothing to push back on"


def test_the_task_view_is_the_repositorys_own_readme_with_the_planted_line(tmp_path):
    project = tmp_path / "churn"
    (project / "repo").mkdir(parents=True)
    (project / "repo" / "README.md").write_text("# Churn model\n\npredict.py trains and predicts.\n")
    (project / "kapso-brief.md").write_text("Objective    x\nBaseline     0.797 (the shipped logistic regression)\nTarget       0.85\n")
    (project / "README.md").write_text("# Your first build\n\nkapso build --brief kapso-brief.md ...\nRecorded result: 0.8474\n")
    user = proof.UserMode("persona:ml-engineer", "claude_code")
    ctx = _context(tmp_path, FakeHost([]), user)
    proof.plant_baseline(ctx, project)
    readme = (project / "README.md").read_text()
    assert readme.startswith("# Churn model") and "kapso build" not in readme and "0.8474" not in readme
    assert readme.rstrip().endswith(proof.PLANTED_BASELINE)
    assert "Baseline     0.90 (the shipped logistic regression)" in (project / "kapso-brief.md").read_text()
    assert user.card.planted == proof.PLANTED_TRUTH and any("planted" in act for act in user.interventions)


def test_an_evaluator_a_session_wrote_is_held_to_the_contract(tmp_path):
    project = tmp_path / "fraud"
    (project / "repo").mkdir(parents=True)
    (project / "data").mkdir()
    (project / "data" / "transactions.csv").write_text("id,amount\n1,10\n")
    good = project / "kapso_evaluation"
    good.mkdir()
    good.joinpath("evaluate.py").write_text(
        "import json, pathlib\n"
        "here = pathlib.Path(__file__).resolve().parent\n"
        "assert pathlib.Path('kapso_datasets/transactions.csv').is_file()\n"
        "(here / 'result.json').write_text(json.dumps({'evaluation_script_path': 'kapso_evaluation/evaluate.py', 'evaluation_output': 'auprc: 0.5', 'score': 0.5}))\n"
        "print('rows: 1')\nprint('auprc: 0.5')\n"
    )
    ctx = _context(tmp_path, FakeHost([]), proof.UserMode("scripted", "claude_code"))
    assert proof.evaluator_contract(ctx, project, "kapso_evaluation/evaluate.py") == "ok"
    good.joinpath("evaluate.py").write_text("print('done, no metric line')\n")
    assert proof.evaluator_contract(ctx, project, "kapso_evaluation/evaluate.py").startswith("the last line is not `name: value`")
    good.joinpath("evaluate.py").write_text("print('auprc: 0.5')\n")
    assert proof.evaluator_contract(ctx, project, "kapso_evaluation/evaluate.py") == "no result.json beside the script"
    good.joinpath("evaluate.py").write_text("import sys\nprint('evaluation failed: no transactions')\nsys.exit(2)\n")
    assert proof.evaluator_contract(ctx, project, "kapso_evaluation/evaluate.py").startswith("exit 2")


def test_the_deployed_calls_parity_is_the_observed_row_against_the_delivered_predictions(tmp_path):
    campaign = tmp_path / "campaign"
    deployment = campaign / ".kapso" / "deployments" / "1"
    deployment.mkdir(parents=True)
    assert proof.deploy_parity(deployment, campaign) == "not established: no deployment record"
    (deployment / "deployment.json").write_text(json.dumps({"observed": {"id": "C010001", "churn_probability": 0.9821}}))
    assert proof.deploy_parity(deployment, campaign).startswith("not established: no observed row or no predictions.csv")
    (campaign / "predictions.csv").write_text("id,churn_probability\nC010001,0.9821\nC010002,0.1\n")
    assert proof.deploy_parity(deployment, campaign) == "same"
    (campaign / "predictions.csv").write_text("id,churn_probability\nC010001,0.5\n")
    assert proof.deploy_parity(deployment, campaign).startswith("differs (deployed 0.9821, delivered 0.5)")


def test_the_records_user_block_carries_the_personas_pins():
    user = proof.UserMode("persona:ml-engineer", "claude_code")
    block = user.record()
    assert block["kind"] == "persona" and block["card"] == "ml-engineer" and len(block["card_sha256"]) == 64
    assert block["vendor"] == "codex" and block["model"] == proof.SUITE["user"]["persona"]["claude_code"]["model"] and len(block["prompt_sha256"]) == 64
    assert proof.UserMode("scripted", "codex").record() == {"kind": "scripted", "card": None, "interventions": [], "events": [], "pushback": None}


def test_a_review_names_the_delivered_branch_or_that_nothing_was_delivered():
    # S2 on the Claude host (2026-10-28): the churn campaign missed 0.85 by
    # 0.0041 and delivered no branch; the review said so, and the predicate
    # that wanted a branch name could never pass it.
    assert proof.names_delivery("What won: kapso/exp-7 at 0.861 — merge it.", "kapso/exp-7")
    assert not proof.names_delivery("I could not read that campaign.", "kapso/exp-7")
    assert proof.names_delivery("finished at 0.8459 ROC AUC, 0.0041 below the target. The goal was not met.", None)
    assert proof.names_delivery("Nothing was delivered; do not merge.", None)
    assert not proof.names_delivery("What won: generic_exp_0 at 0.8459 — safe to merge.", None)
    # The verdict in the skill's own forms (s2-claude-2's review said "merging
    # the branch whole carries the labels" and "resume with more time" and
    # was read as giving none).
    assert proof.merge_verdict("Risks: merging the branch whole carries the labels into the repository.")
    assert proof.merge_verdict("Next action: resume with more time, kapso build --resume.")
    assert proof.merge_verdict("Not safe: the evaluator was edited.") and proof.merge_verdict("cherry-pick the one change")
    assert not proof.merge_verdict("I could not read that campaign.")


def test_a_turn_that_asks_then_shows_the_command_it_will_run_asks():
    # Two shapes the Claude host wrote on 2026-10-28 (build-churn and
    # build-data-only): the approval request, then the command it refers to.
    fenced = "Baseline measured at 0.7974.\n\nApprove the evaluation change, or edit a line of the brief. Say **go** and I'll run:\n```\nkapso build --brief kapso-brief.md --output ../churn-campaign --detach\n```\n"
    assert proof.question_asked(fenced, [])
    inline = "Approve, or edit a line. On \"go\", I'll launch it in the background:\n`kapso build --brief kapso-brief.md --output ../fraud-campaign --detach`\n"
    assert proof.question_asked(inline, [])
    # The request three lines up, the command, then its own continuation last.
    tailed = "`kapso doctor build` passed.\nSay **go** and I'll launch this:\n```\nkapso build --brief kapso-brief.md --output ../fraud-campaign --detach\n```\nOr edit a line of the brief or the evaluation first.\n"
    assert proof.question_asked(tailed, [])
    # A statement followed by a command is still no question, nor is a courtesy sign-off.
    assert not proof.question_asked("Launched. The campaign is at ../churn-campaign.\n```\nkapso watch ../churn-campaign\n```\n", [])
    assert not proof.question_asked("Launched. The campaign is at ../churn-campaign.\nLet me know if you want the full trace.\n", [])
