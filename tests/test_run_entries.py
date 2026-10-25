"""The run entries the adapters append to a session's record
(wp6-observability.md, change 3): one per host invocation, written in
the adapter's own `finally`, so a session that succeeds, fails, times
out, pauses for the inbox, is refused by the model's safeguards, resumes
or raises is recorded as it happened; the Codex adapter the same with
null where its host reports nothing. The fake Claude Code CLI is a real
subprocess emitting stream-json events (as test_streaming_cost_and_deadline
drives it); the fake Codex is the executable test_codex_agent installs."""
import json
import sys
from pathlib import Path

import pytest

from kapso.execution.coding_agents.adapters.claude_code_agent import ClaudeCodeCodingAgent
from kapso.execution.coding_agents.adapters.codex_agent import CodexCodingAgent
from kapso.execution.coding_agents.base import CodingAgentConfig
from kapso.execution.coding_agents.session_record import run_exit
from tests.test_codex_agent import fake_codex  # noqa: F401  (the fixture)
from tests.test_streaming_cost_and_deadline import stream_event


def session_record(tmp_path: Path) -> Path:
    """A session's record as the staging writes it, with no runs yet."""
    record = tmp_path / ".kapso" / "sessions" / "generic_exp_0" / "session.json"
    record.parent.mkdir(parents=True)
    record.write_text(json.dumps({
        "module": "implementation", "host": "claude_code", "harness": None,
        "session_dir": str(tmp_path), "pages": [], "skills": [], "mcp_servers": [], "agents": [],
        "hooks": [], "prepared": [], "stream": str(record.parent / "stream.jsonl"), "runs": [],
    }, indent=2) + "\n")
    return record


def claude_agent(tmp_path, monkeypatch, record: Path, *, timeout=30) -> ClaudeCodeCodingAgent:
    config = CodingAgentConfig(
        agent_type="claude_code", model="test-model", debug_model="test-model",
        agent_specific={
            "timeout": timeout, "streaming": False,
            "stream_artifact_path": str(record.parent / "stream.jsonl"),
            "session_record_path": str(record),
        },
    )
    agent = ClaudeCodeCodingAgent(config)
    agent.workspace = str(tmp_path)
    monkeypatch.setattr(agent, "_get_changed_files", lambda: ["strategy.py"])
    monkeypatch.setattr(agent, "_get_env", lambda: None)
    return agent


def run_script(agent, monkeypatch, script: str, *, resume=None):
    fake_cmd = [sys.executable, "-u", "-c", script]
    monkeypatch.setattr(agent, "_build_command", lambda model, resume_session_id=None: fake_cmd)
    if resume is not None:
        return agent.resume(resume, "go on", timeout_seconds=agent._timeout)
    return agent.generate_code("prompt", timeout_seconds=agent._timeout)


def runs(record: Path):
    return json.loads(record.read_text())["runs"]


INIT = stream_event({"type": "system", "subtype": "init", "session_id": "s-1", "model": "test-model",
                     "mcp_servers": [{"name": "gated-knowledge", "status": "connected"}], "tools": []})
TOOL_USE = stream_event({"type": "assistant", "message": {"content": [
    {"type": "tool_use", "id": "t1", "name": "mcp__gated-knowledge__bank_index", "input": {}},
    {"type": "text", "text": "reading the bank"},
]}})
HOOK = stream_event({"type": "system", "subtype": "hook_response", "hook_event": "PreToolUse",
                     "hook_name": "PreToolUse:deny-snapshot", "exit_code": 0, "outcome": "success",
                     "output": json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse",
                                                                   "permissionDecision": "deny",
                                                                   "permissionDecisionReason": "built once"}})})


def result_event(text, cost, *, turns=3, error=False):
    return stream_event({"type": "result", "result": text, "total_cost_usd": cost, "num_turns": turns,
                         "duration_ms": 1200, "is_error": error, "session_id": "s-1"})


def test_a_successful_turn_leaves_one_entry_with_its_digest(tmp_path, monkeypatch):
    record = session_record(tmp_path)
    agent = claude_agent(tmp_path, monkeypatch, record)
    # The files changed are the host's own account (the edit tools'
    # inputs), relative to the session directory; the adapter's git
    # status (stubbed to another answer here) is not the record's source.
    write = stream_event({"type": "assistant", "message": {"content": [
        {"type": "tool_use", "id": "t2", "name": "Write",
         "input": {"file_path": str(tmp_path / "strategy.py"), "content": "x"}},
        {"type": "tool_use", "id": "t3", "name": "Edit", "input": {"file_path": "/elsewhere/notes.md"}},
    ]}})
    script = "\n".join([INIT, TOOL_USE, write, HOOK, result_event("done", 0.75)])
    result = run_script(agent, monkeypatch, script)
    assert result.success and not result.refused
    [entry] = runs(record)
    assert entry["exit"] == "success" and entry["error"] is None
    assert entry["model"] == "test-model" and entry["cli_session_id"] == "s-1"
    assert entry["turns"] == 3 and entry["cost_usd"] == 0.75 and entry["cost_cumulative"] == 0.75
    assert entry["tools"] == {"mcp__gated-knowledge__bank_index": 1, "Write": 1, "Edit": 1}
    assert entry["gates"] == {"gated-knowledge": {"bank_index": 1}}
    assert entry["hooks"] == [{"event": "PreToolUse", "name": "PreToolUse:deny-snapshot", "decision": "deny",
                               "reason": "built once", "exit_code": 0, "outcome": "success"}]
    assert entry["files_changed"] == ["/elsewhere/notes.md", "strategy.py"] and entry["last_message"] == "reading the bank"
    assert entry["started"] <= entry["ended"] and entry["duration_seconds"] >= 0
    assert set(entry) >= {"delegates", "usage", "host_errors"}


def test_a_failed_turn_a_timeout_and_a_pause_are_named(tmp_path, monkeypatch):
    record = session_record(tmp_path)
    agent = claude_agent(tmp_path, monkeypatch, record, timeout=2)
    failed = run_script(agent, monkeypatch, "\n".join([INIT, result_event("boom", 0.2, error=True)]))
    assert not failed.success
    hung = run_script(agent, monkeypatch, "\n".join([INIT, "import time", "time.sleep(60)"]))
    assert not hung.success and hung.metadata["deadline_exceeded"]
    first, second = runs(record)
    assert first["exit"] == "error" and first["error"] == "boom"
    assert second["exit"] == "timeout" and "deadline" in second["error"]
    # A pause is the inbox's stop, not a failure.
    paused = failed.__class__(success=True, output="", metadata={"stopped_for_inbox": True})
    assert run_exit(paused, None) == "paused"


def test_a_resumed_session_appends_a_second_entry_with_the_costs_delta(tmp_path, monkeypatch):
    record = session_record(tmp_path)
    agent = claude_agent(tmp_path, monkeypatch, record)
    run_script(agent, monkeypatch, "\n".join([INIT, result_event("first", 1.0, turns=4)]))
    run_script(agent, monkeypatch, "\n".join([INIT, result_event("second", 1.4, turns=2)]), resume="s-1")
    first, second = runs(record)
    assert first["turns"] == 4 and first["cost_usd"] == 1.0
    # The host's figure is cumulative for the session: the second run's
    # own cost is the difference, and its digest covers its own lines.
    assert second["turns"] == 2 and second["cost_cumulative"] == 1.4 and second["cost_usd"] == 0.4
    assert second["last_message"] is None  # no assistant text in its slice


def test_a_refused_turn_is_a_refusal(tmp_path, monkeypatch):
    record = session_record(tmp_path)
    agent = claude_agent(tmp_path, monkeypatch, record)
    refusal = "API Error: Fable 5's safeguards flagged this message. Details: [reasoning_extraction]"
    result = run_script(agent, monkeypatch, "\n".join([INIT, result_event(refusal, 0.01)]))
    assert result.refused and not result.success and result.error == refusal
    [entry] = runs(record)
    assert entry["exit"] == "refused" and entry["error"] == refusal


def test_an_invocation_that_raises_is_recorded_and_the_error_propagates(tmp_path, monkeypatch):
    record = session_record(tmp_path)
    agent = claude_agent(tmp_path, monkeypatch, record)

    def explode(*args, **kwargs):
        raise OSError("no such binary: claude")

    monkeypatch.setattr(agent, "_run_streaming_turn", explode)
    # The invocation records the exception in flight and lets it go on.
    with pytest.raises(OSError, match="no such binary"):
        agent._run_streaming("prompt", "test-model", 30)
    [entry] = runs(record)
    assert entry["exit"] == "error" and entry["error"] == "OSError: no such binary: claude"
    assert entry["turns"] == 0 and entry["files_changed"] == []
    # Through generate_code the adapter answers with a failed result; the
    # second invocation is recorded the same way.
    failed = agent.generate_code("prompt")
    assert not failed.success and "no such binary" in failed.error
    assert [run["exit"] for run in runs(record)] == ["error", "error"]


def test_without_a_record_nothing_is_written(tmp_path, monkeypatch):
    config = CodingAgentConfig(
        agent_type="claude_code", model="test-model", debug_model="test-model",
        agent_specific={"timeout": 30, "streaming": False},
    )
    agent = ClaudeCodeCodingAgent(config)
    agent.workspace = str(tmp_path)
    monkeypatch.setattr(agent, "_get_changed_files", lambda: [])
    monkeypatch.setattr(agent, "_get_env", lambda: None)
    result = run_script(agent, monkeypatch, "\n".join([INIT, result_event("done", 0.1)]))
    assert result.success and not (tmp_path / ".kapso").exists()


def test_the_codex_adapter_records_its_runs_with_null_where_its_host_says_nothing(tmp_path, fake_codex, monkeypatch):  # noqa: F811
    record = session_record(tmp_path)
    monkeypatch.setenv("FAKE_CODEX_MODE", "mcp")
    agent = CodexCodingAgent(CodingAgentConfig(
        agent_type="codex", model="m1", debug_model="dbg",
        agent_specific={"stream_artifact_path": str(record.parent / "stream.jsonl"),
                        "session_record_path": str(record)},
    ))
    agent.initialize(str(fake_codex))
    result = agent.generate_code("prompt", timeout_seconds=30)
    [entry] = runs(record)
    assert entry["exit"] == ("success" if result.success else "error")
    assert entry["model"] == "m1" and entry["cli_session_id"] == "thr-1"
    assert entry["hooks"] is None and entry["cost_usd"] is None and entry["cost_cumulative"] is None
    assert entry["gates"] == {"leeroopedia": {"get_page": 1, "build_plan": 1}}
    assert entry["tools"]["command_execution"] == 1

    monkeypatch.setenv("FAKE_CODEX_MODE", "fail")
    failed = agent.generate_code("prompt", timeout_seconds=30)
    assert not failed.success
    assert runs(record)[-1]["exit"] == "error" and "exited with code 3" in runs(record)[-1]["error"]
