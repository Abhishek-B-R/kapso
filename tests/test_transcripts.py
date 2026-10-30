"""The transcript digests (wp6-observability.md, change 2): one parser per
host over committed excerpts of real streams (scripts/redesign/
transcript_excerpt.py over the WP3 trading build's Claude Code sessions
and WP2's development-box Codex campaign), the same keys for both; the
events each host gives (hooks with their decisions, delegates with their
reports, the gates by server, the turns, the host's cumulative cost);
the lines that are not events skipped and an event-shaped line that
does not parse raising; a slice from a resumed turn digested alone."""
import json
from pathlib import Path

import pytest

from kapso.execution.coding_agents.transcripts import (
    CLAUDE_HOST,
    CODEX_HOST,
    TRUNCATED_LINE,
    codex_threads,
    _hook_decision,
    digest_claude,
    digest_codex,
    digest_stream,
    stream_lines,
)

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "transcripts"


def lines(name: str):
    return stream_lines((FIXTURES / name).read_text(encoding="utf-8"))


def test_a_claude_implementation_session_with_a_background_delegate():
    digest = digest_stream(CLAUDE_HOST, lines("claude_implementation.jsonl"))
    assert digest["model"] == "claude-opus-5"
    assert digest["cli_session_id"] == "f6b235b9-affd-494d-93f2-57525e4ad675"
    assert digest["servers"] == ["gated-knowledge", "market-data"]
    # Three result events: the turns and the durations add up, the cost
    # is the host's cumulative figure (the last result's).
    assert digest["turns"] == 48 and digest["duration_ms"] == 645254
    assert digest["cost_cumulative"] == 4.15394625
    assert digest["tools"] == {"Skill": 2, "Read": 1, "Bash": 6, "ListAgents": 3}
    assert digest["gates"] == {} and digest["errors"] == []
    assert digest["hooks"] == [{
        "event": "SessionStart", "name": "SessionStart:startup",
        "decision": "context", "reason": None, "exit_code": 0, "outcome": "success",
    }]
    [delegate] = digest["delegates"]
    assert delegate["name"] == "lookahead-auditor" and delegate["background"] is True
    assert delegate["status"] == "completed"
    # A background delegate's report is what its notification carries.
    assert delegate["report"] == delegate["summary"]
    assert delegate["report"].startswith("## Outcome: FAIL")
    assert digest["usage"] is None


def test_a_hook_that_blocks_a_tool_call_is_a_denial_in_the_record():
    """Claude Code reports a blocking PreToolUse hook as the tool's error
    result (`PreToolUse:Bash hook error: …`), not as a hook_response
    event: the WP6 proof run's setup session was denied a web fetch and
    the record said nothing (S4's readers found it in the log)."""
    init = json.dumps({"type": "system", "subtype": "init", "session_id": "s", "model": "m", "mcp_servers": []})
    denied = json.dumps({"type": "user", "message": {"role": "user", "content": [{
        "type": "tool_result", "is_error": True, "tool_use_id": "t1",
        "content": "PreToolUse:Bash hook error: Web fetches are off in this harness: use get_bars on the market-data server.",
    }]}})
    plain_error = json.dumps({"type": "user", "message": {"role": "user", "content": [{
        "type": "tool_result", "is_error": True, "tool_use_id": "t2", "content": "command not found: curl",
    }]}})
    digest = digest_claude([init + "\n", denied + "\n", plain_error + "\n"])
    assert digest["hooks"] == [{
        "event": "PreToolUse", "name": "PreToolUse:Bash", "decision": "deny",
        "reason": "Web fetches are off in this harness: use get_bars on the market-data server.",
        "exit_code": None, "outcome": "blocking",
    }]


def test_a_claude_verification_session_stops_its_delegate_and_reports_it():
    digest = digest_claude(lines("claude_verification.jsonl"))
    assert digest["cli_session_id"] == "7e29d2e2-a7ed-4f08-9213-6c61f7be9ff9"
    assert digest["turns"] == 28 and digest["cost_cumulative"] == 3.2776337500000006
    assert digest["tools"] == {"Bash": 6, "Skill": 1, "Read": 2, "ToolSearch": 2, "TaskStop": 1}
    [delegate] = digest["delegates"]
    assert delegate["name"] == "lookahead-auditor" and delegate["report"].startswith("## Outcome")
    assert delegate["usage"]["tool_uses"] >= 1


def test_a_claude_setup_session_counts_the_gates_by_server():
    digest = digest_claude(lines("claude_harness_setup.jsonl"))
    assert digest["gates"] == {"market-data": {"list_instruments": 1}}
    assert digest["tools"]["mcp__market-data__list_instruments"] == 1
    assert digest["turns"] == 24 and digest["cost_cumulative"] == 0.9988595
    # A hook that printed no JSON decided nothing.
    assert digest["hooks"] == [{
        "event": "SessionStart", "name": "SessionStart:startup",
        "decision": None, "reason": None, "exit_code": 0, "outcome": "success",
    }]
    assert digest["delegates"] == [] and digest["last_message"].startswith("Setup is complete.")


def test_a_codex_implementation_session_reports_no_hooks_and_no_cost():
    digest = digest_stream(CODEX_HOST, lines("codex_implementation.jsonl"))
    assert digest["model"] is None and digest["cli_session_id"] == "01a17302-e2d3-7c93-ad03-349482a776df"
    assert digest["hooks"] is None and digest["cost_cumulative"] is None and digest["duration_ms"] is None
    assert digest["turns"] == 1 and digest["usage"]["input_tokens"] == 828666
    assert digest["tools"] == {"mcp__market-data__list_instruments": 1, "file_change": 3, "command_execution": 3}
    assert digest["gates"] == {"market-data": {"list_instruments": 1}} and digest["servers"] == ["market-data"]
    assert digest["delegates"] == [{"name": "wait", "receivers": [], "status": "completed", "prompt": None}]
    assert len(digest["errors"]) == 2 and all("bypass-hook-trust" in error for error in digest["errors"])
    assert digest["last_message"].startswith("<code_changes_summary>")
    # The files changed, from the file_change items (the host's paths).
    assert [Path(path).name for path in digest["files"]] == ["PLAN.md", "changes.log", "eval_profile.md", "strategy.py"]
    assert all(path.startswith("/") for path in digest["files"])


def test_a_codex_setup_session_and_its_diagnostics_lines():
    text = (FIXTURES / "codex_harness_setup.jsonl").read_text(encoding="utf-8")
    # The host's own lines ride the stream and are not events.
    assert "Reading prompt from stdin..." in text and "ERROR codex_core" in text
    digest = digest_codex(text.splitlines(keepends=True))
    assert digest["gates"] == {"market-data": {"snapshot": 1, "list_instruments": 1}}
    assert digest["tools"]["command_execution"] == 1 and digest["tools"]["file_change"] == 1
    assert digest["last_message"].startswith("Prepared:")


def test_a_slice_from_a_resumed_turn_is_digested_alone():
    """A resumed session appends to one stream: the second run's lines,
    from its own `init`, give its own turns, and the cumulative cost the
    adapter takes the delta of; the first run's delegate is not in it."""
    stream = lines("claude_implementation.jsonl")
    inits = [number for number, line in enumerate(stream) if '"subtype":"init"' in line]
    assert len(inits) == 3
    last = digest_claude(stream[inits[2]:])
    assert last["turns"] == 2 and last["cost_cumulative"] == 4.15394625
    assert last["delegates"] == [] and last["hooks"] == []
    assert last["cli_session_id"] == "f6b235b9-affd-494d-93f2-57525e4ad675"


def test_an_event_shaped_line_that_does_not_parse_raises_and_others_are_skipped():
    assert digest_claude(["Reading prompt from stdin...\n", "not an event\n"])["turns"] == 0
    assert digest_codex(["2026-10-25T12:10:45Z ERROR codex_core::session: failed to load skill\n"])["turns"] == 0
    # A malformed line in the body is not evidence: it raises.
    with pytest.raises(json.JSONDecodeError):
        digest_claude(['{"type": "result", "num_turns": }\n', '{"type":"system","subtype":"init"}\n'])
    with pytest.raises(json.JSONDecodeError):
        digest_codex(['{"type":"item.completed", "item": }\n', '{"type":"turn.completed","usage":{}}\n'])
    with pytest.raises(ValueError, match="no transcript digest for host 'aider'"):
        digest_stream("aider", [])


def test_a_last_line_cut_by_a_kill_is_skipped_and_noted():
    """A host killed mid-write leaves its last line without its newline;
    the slice's digest keeps what came before and notes the cut (the
    pull-request review's finding: the record used to raise, and the
    adapter turned the raise into a failed result). The newline is the
    sign, not a closing brace: a cut inside a string of code may well end
    on a brace."""
    init = json.dumps({"type": "system", "subtype": "init", "session_id": "s", "model": "m", "mcp_servers": []})
    digest = digest_claude([init + "\n", '{"type":"assistant","message":{"content":[{"type":"text","text":"fn() {}'])
    assert digest["cli_session_id"] == "s" and digest["errors"] == [TRUNCATED_LINE]
    digest = digest_codex(['{"type":"thread.started","thread_id":"t"}\n', '{"type":"item.completed","item":{"ty'])
    assert digest["cli_session_id"] == "t" and digest["errors"] == [TRUNCATED_LINE]


def test_a_separator_inside_an_events_text_is_not_a_line_end():
    """An event's text may hold the characters `str.splitlines` takes for
    line ends (a web result's title held a U+2028 line separator: the
    record cut the event in two, raised on the half, and the RelBench
    arm of 2026-10-29 died with it). A stream splits on the newline
    alone, every line keeping its newline, and only a last line without
    one is cut."""
    title = "effects \u2028of aerobic\u2029exercise\u0085\x0c"
    search = json.dumps({"type": "item.completed", "item": {"id": "i", "type": "web_search", "query": title}}, ensure_ascii=False)
    text = '{"type":"thread.started","thread_id":"t"}\n' + search + '\n{"type":"turn.completed","usage":{"input_tokens":1}}\n'
    whole = stream_lines(text)
    assert len(whole) == 3 and all(line.endswith("\n") for line in whole)
    assert digest_codex(whole)["turns"] == 1 and digest_codex(whole)["errors"] == []
    cut = stream_lines(text + '{"type":"item.completed","item":{"ty')
    assert cut[-1] == '{"type":"item.completed","item":{"ty' and digest_codex(cut)["errors"] == [TRUNCATED_LINE]
    init = json.dumps({"type": "system", "subtype": "init", "session_id": "s", "model": "m", "mcp_servers": []})
    said = json.dumps({"type": "assistant", "message": {"content": [{"type": "text", "text": title}]}}, ensure_ascii=False)
    digest = digest_claude(stream_lines(init + "\n" + said + "\n"))
    assert digest["cli_session_id"] == "s" and digest["errors"] == []


def test_a_launcher_exit_with_no_thread_is_its_own_entry():
    """A `codex exec` that died before its first event (a bad model, a
    login, a quota) appends only the launcher's exit line; it is a thread
    with no lines and that code, so the frame records the failure."""
    lines = [
        '{"type":"kapso.exit","role":"writer","code":1}\n',
        '{"type":"thread.started","thread_id":"t2"}\n',
        '{"type":"turn.completed","usage":{"input_tokens":1}}\n',
        '{"type":"kapso.exit","role":"writer","code":0}\n',
    ]
    threads = codex_threads(lines)
    assert [(len(thread["lines"]), thread["code"]) for thread in threads] == [(0, 1), (2, 0)]


def test_a_delegates_final_usage_is_its_notifications():
    """The task notification carries the delegate's final figures; the
    progress events before it are snapshots on the way."""
    events = [
        {"type": "system", "subtype": "init", "session_id": "s", "model": "m", "mcp_servers": []},
        {"type": "system", "subtype": "task_started", "task_type": "local_agent", "task_id": "a1",
         "subagent_type": "auditor", "tool_use_id": "t1", "is_backgrounded": True},
        {"type": "system", "subtype": "task_progress", "task_id": "a1", "usage": {"total_tokens": 10}},
        {"type": "system", "subtype": "task_notification", "task_id": "a1", "status": "completed",
         "summary": "done", "usage": {"total_tokens": 25, "tool_uses": 3}},
    ]
    [delegate] = digest_claude([json.dumps(event) + "\n" for event in events])["delegates"]
    assert delegate["usage"] == {"total_tokens": 25, "tool_uses": 3} and delegate["report"] == "done"


def test_a_hooks_decision_is_read_from_what_it_printed():
    deny = json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny",
                                               "permissionDecisionReason": "the snapshot is built once"}})
    assert _hook_decision(deny) == {"decision": "deny", "reason": "the snapshot is built once"}
    block = json.dumps({"decision": "block", "reason": "results/ is missing"})
    assert _hook_decision(block) == {"decision": "block", "reason": "results/ is missing"}
    context = json.dumps({"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": "pinned"}})
    assert _hook_decision(context) == {"decision": "context", "reason": None}
    assert _hook_decision("") == {"decision": None, "reason": None}
    assert _hook_decision("plain text, not json") == {"decision": None, "reason": None}
