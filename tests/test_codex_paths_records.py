"""The two Codex paths outside the adapters record their runs too
(wp6-observability.md, change 4): an ideation member or selector run
through `run_codex_ideation` (now `codex exec --json`, streaming beside
the ideation artifacts, its record naming that stream) and the update
crew's workers, whose launcher appends every invocation's events to the
crew's stream and closes each with its exit code, recorded by the frame
after the lead's session."""
import json
import os
from pathlib import Path

from kapso.execution.coding_agents.transcripts import codex_threads
from kapso.execution.search_strategies.generic import codex_ideation
from kapso.harness.staging import stage_harness
from kapso.learning.update_frame import UpdateFrame
from tests.test_codex_agent import fake_codex  # noqa: F401  (the fixture)


def runs(record: Path):
    return json.loads(record.read_text())["runs"]


def test_an_ideation_member_streams_json_beside_its_artifacts_and_records_its_run(tmp_path, fake_codex, monkeypatch):  # noqa: F811
    campaign = tmp_path / "campaign"
    artifacts = campaign / ".kapso" / "ideation" / "iter1"
    artifacts.mkdir(parents=True)
    staged = stage_harness(
        None, "ideation", session_dir=artifacts, campaign_dir=campaign,
        session_id="ideation/iter1/codex_m1", host="codex",
    )
    stream = codex_ideation.ideation_stream_path(str(artifacts), "codex", "m1")
    staged.merged_agent_specific({"stream_artifact_path": stream})
    argdump = tmp_path / "args.txt"
    monkeypatch.setenv("FAKE_CODEX_ARGDUMP", str(argdump))
    monkeypatch.setenv("FAKE_CODEX_MODE", "mcp")

    output, timed_out, duration, meta = codex_ideation.run_codex_ideation(
        prompt="think", model="m1", cwd=str(fake_codex), timeout_seconds=30,
        artifacts_dir=str(artifacts), web_search=False,
        record_path=staged.agent_specific["session_record_path"],
    )
    assert output == "FINAL[m1]" and not timed_out and duration >= 0
    assert "--json" in argdump.read_text().split()
    assert meta["stream_path"] == stream and '"thread.started"' in Path(stream).read_text()
    record = json.loads(staged.record_path.read_text())
    assert record["stream"] == stream
    [entry] = record["runs"]
    assert entry["exit"] == "success" and entry["cli_session_id"] == "thr-1" and entry["model"] == "m1"
    assert entry["gates"] == {"leeroopedia": {"get_page": 1, "build_plan": 1}}
    assert entry["tools"]["command_execution"] == 1 and entry["last_message"] == "ok"
    assert entry["hooks"] is None and entry["cost_usd"] is None


def test_a_killed_turns_output_is_the_agents_messages_not_the_raw_events():
    stream = "\n".join([
        "Reading prompt from stdin...",
        '{"type":"thread.started","thread_id":"t"}',
        '{"type":"item.completed","item":{"id":"i1","type":"agent_message","text":"<solution>one</solution>"}}',
        '{"type":"item.completed","item":{"id":"i2","type":"command_execution","command":"ls","status":"completed"}}',
        '{"type":"item.completed","item":{"id":"i3","type":"agent_message","text":"and two"}}',
    ])
    assert codex_ideation.agent_messages(stream) == "<solution>one</solution>\nand two"


def test_a_launchers_stream_splits_into_threads_closed_by_their_exit_lines():
    lines = [
        "Reading prompt from stdin...\n",
        '{"type":"thread.started","thread_id":"t1"}\n',
        '{"type":"item.completed","item":{"id":"i1","type":"agent_message","text":"first"}}\n',
        '{"type":"turn.completed","usage":{"input_tokens":10}}\n',
        '{"type":"kapso.exit","role":"card-writer","code":0}\n',
        '{"type":"thread.started","thread_id":"t2"}\n',
        '{"type":"kapso.exit","role":"card-merger","code":3}\n',
        '{"type":"thread.started","thread_id":"t3"}\n',
        '{"type":"item.completed","item":{"id":"i9","type":"agent_message","text":"cut"}}\n',
    ]
    threads = codex_threads(lines)
    assert [t["code"] for t in threads] == [0, 3, None]
    assert [len(t["lines"]) for t in threads] == [3, 1, 2]


def test_the_update_crews_workers_are_recorded_from_their_stream(tmp_path):
    run_dir = tmp_path / "lr_1"
    run_dir.mkdir()
    workers = stage_harness(None, "learning", session_dir=run_dir, campaign_dir=run_dir, session_id="workers", host="codex")
    stream = Path(workers.agent_specific["stream_artifact_path"])
    stream.parent.mkdir(parents=True, exist_ok=True)
    stream.write_text("".join([
        '{"type":"thread.started","thread_id":"t1"}\n',
        '{"type":"item.completed","item":{"id":"i1","type":"mcp_tool_call","server":"market-data","tool":"get_bars","result":null,"error":null,"status":"completed"}}\n',
        '{"type":"item.completed","item":{"id":"i2","type":"agent_message","text":"Handled obs-01."}}\n',
        '{"type":"turn.completed","usage":{"input_tokens":5,"output_tokens":2}}\n',
        '{"type":"kapso.exit","role":"card-writer","code":0}\n',
        '{"type":"thread.started","thread_id":"t2"}\n',
        '{"type":"kapso.exit","role":"card-merger","code":3}\n',
        '{"type":"thread.started","thread_id":"t3"}\n',
        '{"type":"turn.completed","usage":{"input_tokens":1}}\n',
    ]))
    UpdateFrame._record_workers(None, workers, "gpt-5.6-sol")
    first, second, third = runs(workers.record_path)
    assert first["exit"] == "success" and first["cli_session_id"] == "t1" and first["model"] == "gpt-5.6-sol"
    assert first["gates"] == {"market-data": {"get_bars": 1}} and first["last_message"] == "Handled obs-01."
    assert first["usage"] == {"input_tokens": 5, "output_tokens": 2} and first["started"] is None
    assert second["exit"] == "error" and second["error"] == "codex exec exited with code 3"
    assert third["exit"] == "error" and "no exit" in third["error"]
    # Without a stream there is nothing to record.
    os.unlink(stream)
    UpdateFrame._record_workers(None, workers, "gpt-5.6-sol")
    assert len(runs(workers.record_path)) == 3
