"""The judge's retry (docs/plans/redesign/wp4-config.md, change 8): the
invocation's outcome is inspected before its output; a tagless answer
resumes the judge's own session with the nudge under a re-computed room,
the reason on the run entry; a session cut at its deadline, a retry
still without tags, or no room for one leave the attempt unjudged; a
missing session handle is a wiring bug; a resumed Claude session's
spend is the delta of the host's cumulative figure."""

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from kapso.execution.coding_agents.adapters.claude_code_agent import ClaudeCodeCodingAgent
from kapso.execution.coding_agents.base import CodingAgentConfig
from kapso.execution.coding_agents.session_record import EXIT_TIMEOUT, record_run, start_run
from kapso.execution.search_strategies.generic.feedback_generator.feedback_generator import FeedbackGenerator
from test_feedback_generator import TAGGED, generate, make_generator, patch_prompt


class Outcome(SimpleNamespace):
    """One scripted invocation: its output and how it ended."""


def answer(output: str) -> Outcome:
    return Outcome(success=True, error=None, output=output, metadata={"cli_session_id": "judge-1"})


def cut(output: str = "half an analysis") -> Outcome:
    return Outcome(
        success=False, error="the judge's CLI exceeded its deadline", output=output,
        metadata={"cli_session_id": "judge-1", "deadline_exceeded": True, "completed_before_kill": False},
    )


def failed_to_start(error: str) -> Outcome:
    """A login revoked, a quota exhausted, a crashed CLI: no turn, no session."""
    return Outcome(success=False, error=error, output="", metadata={"cli_session_id": None})


class ScriptedJudge:
    def __init__(self, outcomes):
        self.outcomes = list(outcomes)
        self.calls = []
        self.cost = 0.0

    def initialize(self, workspace):
        pass

    def generate_code(self, prompt, debug_mode=False, timeout_seconds=None):
        self.calls.append({"kind": "fresh", "timeout_seconds": timeout_seconds})
        self.cost += 1.0
        return self.outcomes.pop(0)

    def resume(self, cli_session_id, follow_up, timeout_seconds=None, reason=None):
        self.calls.append({"kind": "resume", "session": cli_session_id, "prompt": follow_up, "timeout_seconds": timeout_seconds, "reason": reason})
        self.cost += 0.4
        return self.outcomes.pop(0)

    def get_cumulative_cost(self):
        return self.cost


@pytest.fixture
def judged(monkeypatch):
    patch_prompt(monkeypatch)

    def run(outcomes, retry_deadline=None, timeout_seconds=300.0):
        agent = ScriptedJudge(outcomes)
        generator = make_generator(agent)
        monkeypatch.setattr(generator, "_get_commit_message", lambda *args: "msg")
        result = generator.generate(
            goal="g", idea="i", code_changes_summary="c", base_branch="main", head_branch="exp",
            evaluation_script_path="kapso_evaluation/kapso_eval.py", evaluation_result="out",
            workspace_dir="/tmp/nowhere", timeout_seconds=timeout_seconds, retry_deadline=retry_deadline,
        )
        return agent, result

    return run


def test_tagless_then_tagged_resumes_the_session_under_the_recomputed_room(judged):
    agent, result = judged([answer("no tags"), answer(TAGGED)], retry_deadline=lambda: (120.0, None))
    assert [call["kind"] for call in agent.calls] == ["fresh", "resume"]
    retry = agent.calls[1]
    assert retry["session"] == "judge-1" and retry["prompt"] == FeedbackGenerator.RETRY_PROMPT
    assert retry["timeout_seconds"] == 120.0 and retry["reason"] == "tags missing"
    assert result.unjudged == "" and result.score == 0.8
    assert result.cost_usd == pytest.approx(1.4)


def test_tagless_then_a_retry_cut_at_its_deadline_is_unjudged(judged):
    agent, result = judged([answer("no tags"), cut()], retry_deadline=lambda: (90.0, None))
    assert [call["kind"] for call in agent.calls] == ["fresh", "resume"]
    assert result.unjudged == "the judge's session ended at its deadline"
    assert result.score is None and result.feedback == ""


def test_a_first_run_cut_at_its_deadline_is_not_retried(judged):
    agent, result = judged([cut("<stop>false</stop><score>0.9</score>")])
    assert [call["kind"] for call in agent.calls] == ["fresh"]
    assert result.unjudged == "the judge's session ended at its deadline"
    # A killed turn's tags are not a verdict.
    assert result.score is None


def test_no_room_for_a_retry_is_unjudged_with_the_reason(judged):
    agent, result = judged([answer("no tags")], retry_deadline=lambda: (None, "the budget left 12s for the judge, under the 60s floor"))
    assert [call["kind"] for call in agent.calls] == ["fresh"]
    assert result.unjudged == "no tags, and no room for a retry (the budget left 12s for the judge, under the 60s floor)"


def test_a_tagless_answer_with_no_session_handle_raises(judged):
    """A turn that completed without the adapter naming its session is a
    wiring bug, not a tagless answer: the retry cannot resume it."""
    with pytest.raises(RuntimeError, match="recorded no cli_session_id"):
        judged([Outcome(success=True, error=None, output="no tags", metadata={})])


def test_a_judge_session_that_fails_to_start_is_unjudged_with_its_error(judged):
    """The invocation itself failed (the proof run's exhausted quota): the
    attempt is unjudged with the error, nothing is resumed, and the
    campaign goes on without a verdict rather than dying on a traceback."""
    agent, result = judged([failed_to_start("Quota exceeded for the openai-api-key secret")])
    assert [call["kind"] for call in agent.calls] == ["fresh"]
    assert result.unjudged == "the judge's session failed: Quota exceeded for the openai-api-key secret"
    assert result.score is None and result.evaluation_valid is True and result.feedback == ""


def test_the_retry_run_entry_carries_its_reason(tmp_path):
    record = tmp_path / "session.json"
    record.write_text(json.dumps({"session_dir": str(tmp_path), "runs": []}))
    first = start_run("claude_code", "claude-opus-5", str(record), None)
    record_run(first, SimpleNamespace(success=True, output="no tags", error=None, refused=False, metadata={"cli_session_id": "s1"}), None)
    # The reason is on the recorder before the launch: an invocation that
    # raises still records why it was made.
    retry = start_run("claude_code", "claude-opus-5", str(record), None, reason="tags missing")
    record_run(retry, SimpleNamespace(
        success=False, output="", error="Claude Code CLI exceeded its 60s deadline and was terminated", refused=False,
        metadata={"cli_session_id": "s1", "deadline_exceeded": True, "completed_before_kill": False},
    ), None)
    runs = json.loads(record.read_text())["runs"]
    assert [run["retry_reason"] for run in runs] == [None, "tags missing"]
    assert runs[1]["exit"] == EXIT_TIMEOUT and runs[1]["cli_session_id"] == "s1"


def test_a_resumed_claude_sessions_spend_is_the_delta_of_the_hosts_figure():
    agent = ClaudeCodeCodingAgent.__new__(ClaudeCodeCodingAgent)
    agent._cumulative_cost = 0.0
    agent._session_cost_reported = {}
    assert agent._cost_delta("s1", 1.0) == 1.0
    assert agent._cost_delta("s1", 1.4) == pytest.approx(0.4)
    # A fresh host session costs its own figure; a run without a session
    # id (killed before the host named it) counts what it reported.
    assert agent._cost_delta("s2", 0.5) == 0.5
    assert agent._cost_delta(None, 0.2) == 0.2
    assert agent._session_cost_reported == {"s1": 1.4, "s2": 0.5}


@pytest.mark.parametrize("tag", ["none", "None", "false", "null", ""])
def test_the_cards_parser_treats_the_no_card_words_alike(tag):
    generator = FeedbackGenerator.__new__(FeedbackGenerator)
    parsed = generator._parse_response(TAGGED + f"<cards_load_bearing>{tag}</cards_load_bearing>")
    assert parsed.cards_load_bearing == []
    named = generator._parse_response(TAGGED + "<cards_load_bearing>[card:a-card], b-card</cards_load_bearing>")
    assert named.cards_load_bearing == ["a-card", "b-card"]
