"""The simulated user (docs/plans/redesign/wp9-semantic-suite.md, change
3): the prompt carries the card, the task view's README, the step's
intent, the whole history and the host's message, nothing clipped; `DONE`
alone is the end and `DONE` inside a sentence is not; a non-zero exit, a
timeout and an empty reply raise; the vendor is the other one, by host;
the cards meet the README's contract and the pins are the files' hashes."""

import importlib.util
import json
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("simulated_user", ROOT / "scripts" / "redesign" / "simulated_user.py")
simulated_user = importlib.util.module_from_spec(spec)
spec.loader.exec_module(simulated_user)

CARDS = ROOT / "tests" / "semantic" / "personas"
SETTINGS = {"claude_code": {"vendor": "codex", "model": "gpt-6-astra", "effort": "medium"}, "codex": {"vendor": "claude_code", "model": "claude-opus-5", "effort": None}}


def _codex_stream(text):
    return "\n".join([
        json.dumps({"type": "thread.started", "thread_id": "t-1"}),
        json.dumps({"type": "item.completed", "item": {"type": "agent_message", "text": text}}),
    ]) + "\n"


def _fake_run(monkeypatch, calls, stdout, returncode=0, stderr=""):
    def run(command, **kwargs):
        calls.append((command, kwargs))
        return subprocess.CompletedProcess(command, returncode, stdout=stdout, stderr=stderr)
    monkeypatch.setattr(simulated_user.subprocess, "run", run)


@pytest.fixture
def task(tmp_path):
    (tmp_path / "README.md").write_text("# churn-work\n\nThe model is in predict.py; the metric is AUC.\n")
    return tmp_path


def test_every_card_meets_the_contract_and_is_pinned_by_its_hash():
    names = sorted(path.stem for path in CARDS.glob("*.yaml"))
    assert names == ["data-engineer", "ml-engineer", "second-engineer", "trading-author"]
    for name in names:
        card = simulated_user.load_card(CARDS / f"{name}.yaml")
        assert card.name == name and card.patience >= 1 and len(card.sha256) == 64
    assert len(simulated_user.template_sha256()) == 64


def test_the_prompt_carries_the_card_the_readme_the_intent_the_whole_history_and_the_message(task):
    card = simulated_user.load_card(CARDS / "ml-engineer.yaml")
    long_turn = "a line of the assistant's\n" * 3000
    history = [{"role": "user", "text": "go"}, {"role": "assistant", "text": long_turn, "asked": True}]
    prompt = simulated_user.build_prompt(card, (task / "README.md").read_text(), "launch the build, nothing else", history, "Shall I launch it?", asked=1)
    assert card.role in prompt and card.knows in prompt and card.pushes_back_when in prompt
    assert "The model is in predict.py; the metric is AUC." in prompt
    assert "launch the build, nothing else" in prompt and "Shall I launch it?" in prompt
    assert long_turn.rstrip() in prompt, "the history is carried whole"
    assert "asked you 1 question(s)" in prompt and f"your patience is {card.patience}" in prompt
    assert "single word DONE" in prompt


def test_a_planted_fact_is_told_as_a_certainty(task):
    card = simulated_user.load_card(CARDS / "ml-engineer.yaml")
    card.planted = "the current model's AUC is about 0.80"
    prompt = simulated_user.build_prompt(card, "readme", "intent", [], "The baseline is 0.90.", 0)
    assert "You are certain that the current model's AUC is about 0.80; if the assistant states otherwise, correct it" in prompt


def test_done_alone_ends_and_done_in_a_sentence_does_not(task, monkeypatch):
    card = simulated_user.load_card(CARDS / "ml-engineer.yaml")
    calls = []
    _fake_run(monkeypatch, calls, _codex_stream("DONE"))
    reply = simulated_user.next_message(card, task, "intent", [], "Anything else?", "claude_code", SETTINGS["claude_code"])
    assert reply.done and reply.text == "DONE" and reply.session == "t-1"
    _fake_run(monkeypatch, calls, _codex_stream("I'm DONE with the proposal, launch it."))
    reply = simulated_user.next_message(card, task, "intent", [], "Anything else?", "claude_code", SETTINGS["claude_code"])
    assert not reply.done and reply.text.startswith("I'm DONE")


def test_the_vendor_is_the_other_one_by_host_and_the_persona_has_no_tool(task, monkeypatch):
    card = simulated_user.load_card(CARDS / "ml-engineer.yaml")
    calls = []
    _fake_run(monkeypatch, calls, _codex_stream("go"))
    simulated_user.next_message(card, task, "intent", [], "Shall I?", "claude_code", SETTINGS["claude_code"])
    command = calls[-1][0]
    assert command[:2] == ["codex", "exec"] and "--sandbox" in command and command[command.index("--sandbox") + 1] == "read-only"
    assert command[command.index("-m") + 1] == "gpt-6-astra" and 'model_reasoning_effort="medium"' in command
    _fake_run(monkeypatch, calls, json.dumps({"result": "go", "session_id": "s-9"}))
    reply = simulated_user.next_message(card, task, "intent", [], "Shall I?", "codex", SETTINGS["codex"])
    command = calls[-1][0]
    assert command[:2] == ["claude", "-p"] and "--disallowedTools" in command and reply.session == "s-9"
    with pytest.raises(ValueError, match="the persona for a claude_code host is codex's"):
        simulated_user.next_message(card, task, "intent", [], "Shall I?", "claude_code", SETTINGS["codex"])


def test_a_failed_or_empty_persona_session_raises_rather_than_reading_as_satisfied(task, monkeypatch):
    card = simulated_user.load_card(CARDS / "ml-engineer.yaml")
    calls = []
    _fake_run(monkeypatch, calls, "", returncode=1, stderr="Quota exceeded")
    with pytest.raises(RuntimeError, match=r"the persona's codex session failed \(exit 1\): Quota exceeded"):
        simulated_user.next_message(card, task, "intent", [], "Shall I?", "claude_code", SETTINGS["claude_code"])
    _fake_run(monkeypatch, calls, _codex_stream(""))
    with pytest.raises(RuntimeError, match="answered nothing"):
        simulated_user.next_message(card, task, "intent", [], "Shall I?", "claude_code", SETTINGS["claude_code"])
