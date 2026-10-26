"""The run entries a session's record carries (wp6-observability.md,
change 3): one per host invocation, appended by the adapter in its own
`finally`, so a session that raises, resumes or retries is recorded as it
happened. The entry joins the host's transcript (the digest of the lines
this invocation appended to the stream) with the adapter's own result
(how it ended, the files it changed, the host's session id)."""
import json
import os
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from kapso.execution.coding_agents.base import CodingResult
from kapso.execution.coding_agents.transcripts import digest_stream

EXIT_SUCCESS = "success"
EXIT_ERROR = "error"
EXIT_TIMEOUT = "timeout"
EXIT_PAUSED = "paused"
EXIT_REFUSED = "refused"


@dataclass
class RunRecorder:
    """One invocation in flight: where the stream stood when it started
    and when; `record_path` None means the session keeps no record."""

    host: str
    model: str
    record_path: Optional[Path]
    stream_path: Optional[Path]
    offset: int
    started_at: str
    started_monotonic: float


def start_run(host: str, model: str, record_path: Optional[str], stream_path: Optional[str]) -> RunRecorder:
    stream = Path(stream_path) if stream_path else None
    offset = stream.stat().st_size if stream is not None and stream.exists() else 0
    return RunRecorder(
        host=host, model=model,
        record_path=Path(record_path) if record_path else None,
        stream_path=stream, offset=offset,
        started_at=_utcnow(), started_monotonic=time.monotonic(),
    )


def record_run(recorder: RunRecorder, result: Optional[CodingResult], error: Optional[BaseException]) -> Optional[Dict[str, Any]]:
    """Append this invocation's entry to the session's record and return
    it; nothing without a record. `error` is the exception in flight when
    the invocation raised (the caller lets it propagate). The files
    changed are the host's own account (the edit tools' inputs, the file
    changes), not a git status of the directory, which sees the engine's
    bookkeeping and misses what a session committed."""
    if recorder.record_path is None:
        return None
    digest = digest_stream(recorder.host, _appended_lines(recorder))
    metadata = result.metadata if result is not None else {}
    entry = run_entry(
        digest,
        model=recorder.model,
        # The host session this invocation's own transcript names; the
        # adapter's figure second (a Codex adapter remembers its first
        # thread across fresh invocations).
        cli_session_id=digest["cli_session_id"] or metadata.get("cli_session_id"),
        exit=run_exit(result, error),
        error=_error_text(result, error),
        files_changed=digest["files"],
        started=recorder.started_at,
        ended=_utcnow(),
        duration_seconds=round(time.monotonic() - recorder.started_monotonic, 3),
    )
    append_run(recorder.record_path, entry)
    return entry


def run_entry(
    digest: Dict[str, Any], *, model: str, cli_session_id: Optional[str], exit: str,
    error: Optional[str], files_changed: list, started: Optional[str], ended: Optional[str],
    duration_seconds: Optional[float],
) -> Dict[str, Any]:
    """One run entry's shape: the digest's fields under their own keys,
    with how the run ended and when. `cost_usd` is filled by `append_run`
    against the entry before it."""
    return {
        "started": started,
        "ended": ended,
        "duration_seconds": duration_seconds,
        "model": model,
        "cli_session_id": cli_session_id,
        "exit": exit,
        "error": error,
        "cost_usd": None,
        "cost_cumulative": digest["cost_cumulative"],
        "turns": digest["turns"],
        "usage": digest["usage"],
        "tools": digest["tools"],
        "gates": digest["gates"],
        "hooks": digest["hooks"],
        "delegates": digest["delegates"],
        "host_errors": digest["errors"],
        "files_changed": list(files_changed),
        "last_message": digest["last_message"],
    }


def append_run(record_path: Path, entry: Dict[str, Any]) -> None:
    """Append one entry to the record's `runs`, pricing it against the
    entry before it and naming the files changed relative to the session
    directory, and write the record whole."""
    record = json.loads(Path(record_path).read_text(encoding="utf-8"))
    entry["cost_usd"] = _cost_of_run(entry["cost_cumulative"], record["runs"], entry["cli_session_id"])
    entry["files_changed"] = relative_files(entry["files_changed"], record["session_dir"])
    record["runs"].append(entry)
    write_whole(Path(record_path), json.dumps(record, indent=2) + "\n")


def relative_files(files: list, session_dir: str) -> list:
    """The paths a host reported, relative to the session directory when
    under it, as they are otherwise (a file written elsewhere is still a
    fact), sorted and unique."""
    root = str(session_dir).rstrip("/") + "/"
    return sorted({path[len(root):] if path.startswith(root) else path for path in files})


def run_exit(result: Optional[CodingResult], error: Optional[BaseException]) -> str:
    """How the invocation ended: an exception in flight or no result is
    an error; the model's refusal; the inbox stop (a pause, not a
    failure); the deadline kill of a turn that had not completed; a
    failed turn; else success."""
    if error is not None or result is None:
        return EXIT_ERROR
    if result.refused:
        return EXIT_REFUSED
    if result.metadata.get("stopped_for_inbox"):
        return EXIT_PAUSED
    if result.metadata.get("deadline_exceeded") and not result.metadata.get("completed_before_kill"):
        return EXIT_TIMEOUT
    if not result.success:
        return EXIT_ERROR
    return EXIT_SUCCESS


def _error_text(result: Optional[CodingResult], error: Optional[BaseException]) -> Optional[str]:
    if error is not None:
        return f"{type(error).__name__}: {error}"
    if result is None:
        return "the invocation returned no result"
    return result.error


def _cost_of_run(cumulative: Optional[float], runs: list, cli_session_id: Optional[str]) -> Optional[float]:
    """The host reports the session's cumulative cost: a run that continues
    an earlier entry's host session costs the difference against the
    latest entry of that session that carried a figure (a run killed
    before its result event carries none, and must not reset the
    baseline); a fresh host session costs its own figure; a host that
    reports none, nothing."""
    if cumulative is None:
        return None
    for previous in reversed(runs):
        if previous.get("cli_session_id") == cli_session_id and previous.get("cost_cumulative") is not None:
            return round(max(cumulative - float(previous["cost_cumulative"]), 0.0), 6)
    return round(cumulative, 6)


def _appended_lines(recorder: RunRecorder):
    if recorder.stream_path is None or not recorder.stream_path.exists():
        return []
    with open(recorder.stream_path, "rb") as handle:
        handle.seek(recorder.offset)
        text = handle.read().decode("utf-8", errors="replace")
    return text.splitlines(keepends=True)


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def write_whole(file: Path, text: str) -> None:
    """Written to a sibling and renamed into place, so a concurrent reader
    never sees a half file and a second writer of the same content is
    harmless."""
    file.parent.mkdir(parents=True, exist_ok=True)
    temporary = file.with_name(f".{file.name}.{uuid.uuid4().hex}.tmp")
    temporary.write_text(text, encoding="utf-8")
    os.replace(temporary, file)
