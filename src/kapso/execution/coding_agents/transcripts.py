"""The hosts' transcripts read into a run's digest (wp6-observability.md):
one parser per host over the stream its adapter writes, the same keys
for both, null where a host has nothing to say. The adapters hand a
digest the lines their own invocation appended to the stream, so a
resumed session's second run is digested alone; the trace and the
session record are the digests' only readers.

Lines that are not events (merged stderr, the CLI's own text, warnings)
are skipped, as the adapters' parsers skip them; an event-shaped line
that does not parse raises, since the stream is evidence."""
import json
import re
from collections import Counter, defaultdict
from typing import Any, Dict, Iterable, List, Optional, Set

CLAUDE_HOST = "claude_code"
CODEX_HOST = "codex"
HOSTS = (CLAUDE_HOST, CODEX_HOST)

# The gates' tools reach a Claude Code session as mcp__<server>__<tool>.
GATE_TOOL_PREFIX = "mcp__"
# Claude Code's delegate task; its other task kinds are background shells.
DELEGATE_TASK = "local_agent"
DELEGATE_TOOL = "Agent"
# A hook that blocks a tool call reaches the model as the tool's error
# result, `<event>:<matcher> hook error: <what the hook printed>`, not as
# a hook_response event; the record keeps it as a denial all the same.
HOOK_ERROR = re.compile(r"^(?P<event>[A-Za-z]+):(?P<matcher>\S+) hook error: (?P<reason>.+)", re.DOTALL)
HOOK_DENY = "deny"
HOOK_BLOCKING = "blocking"
# The tools that write a file, and the input key naming it.
EDIT_TOOLS = {"Write": "file_path", "Edit": "file_path", "MultiEdit": "file_path", "NotebookEdit": "notebook_path"}
# What an event line starts with, per host.
CLAUDE_EVENT_HEAD = "{"
CODEX_EVENT_HEAD = '{"type":'


def digest_stream(host: str, lines: Iterable[str]) -> Dict[str, Any]:
    """The digest of one invocation's lines on the named host."""
    if host == CLAUDE_HOST:
        return digest_claude(lines)
    if host == CODEX_HOST:
        return digest_codex(lines)
    raise ValueError(f"no transcript digest for host {host!r}; the hosts are {', '.join(HOSTS)}")


def _empty() -> Dict[str, Any]:
    return {
        "model": None,
        "cli_session_id": None,
        "servers": [],
        "turns": 0,
        "duration_ms": None,
        "cost_cumulative": None,
        "usage": None,
        "tools": {},
        "gates": {},
        "hooks": None,
        "delegates": [],
        "errors": [],
        "files": [],
        "last_message": None,
    }


def _events(lines: Iterable[str], head: str):
    for raw in lines:
        line = raw.strip()
        if not line.startswith(head):
            continue
        yield json.loads(line)


def _hook_decision(output: str) -> Dict[str, Optional[str]]:
    """What a hook decided, from the JSON it printed: a permission
    decision with its reason (PreToolUse), a block with its reason (Stop,
    PostToolUse), or context added; nothing when it printed no JSON."""
    text = output.strip()
    if not text.startswith("{"):
        return {"decision": None, "reason": None}
    data = json.loads(text)
    specific = data.get("hookSpecificOutput") or {}
    if specific.get("permissionDecision"):
        return {"decision": specific["permissionDecision"], "reason": specific.get("permissionDecisionReason")}
    if data.get("decision"):
        return {"decision": data["decision"], "reason": data.get("reason")}
    if specific.get("additionalContext"):
        return {"decision": "context", "reason": None}
    return {"decision": None, "reason": None}


def digest_claude(lines: Iterable[str]) -> Dict[str, Any]:
    """Claude Code's `stream-json`: `system/init` for the model, the
    session and the servers mounted; `assistant` content for the tools
    (a gate's tool counted under its server) and the closing text;
    `system/hook_response` for the hooks that fired and what they
    decided, and a tool's error result for a hook that blocked the call;
    `system/task_started` of a `local_agent` for a delegate,
    joined to its progress (usage), its notification (status, summary)
    and, when it ran in the foreground, the `Agent` tool's result (the
    report); the edit tools' inputs for the files written; `result` for
    the turns, the duration and the host's cumulative cost."""
    digest = _empty()
    tools: Counter = Counter()
    gates: Dict[str, Counter] = defaultdict(Counter)
    hooks: List[Dict[str, Any]] = []
    files: Set[str] = set()
    delegates: Dict[str, Dict[str, Any]] = {}
    delegate_uses: Dict[str, Dict[str, Any]] = {}      # tool_use_id -> {name, background}
    results: Dict[str, str] = {}                       # tool_use_id -> result text
    duration_ms = 0
    for event in _events(lines, CLAUDE_EVENT_HEAD):
        kind = event.get("type")
        if kind == "system":
            subtype = event.get("subtype")
            if subtype == "init":
                if digest["model"] is None:
                    digest["model"] = event.get("model")
                    digest["cli_session_id"] = event.get("session_id")
                    digest["servers"] = [server["name"] for server in event.get("mcp_servers") or []]
            elif subtype == "hook_response":
                hooks.append({
                    "event": event.get("hook_event"),
                    "name": event.get("hook_name"),
                    **_hook_decision(event.get("output") or ""),
                    "exit_code": event.get("exit_code"),
                    "outcome": event.get("outcome"),
                })
            elif subtype == "task_started" and event.get("task_type") == DELEGATE_TASK:
                delegates[event["task_id"]] = {
                    "name": event.get("subagent_type"),
                    "tool_use_id": event.get("tool_use_id"),
                    "background": bool(event.get("is_backgrounded")),
                    "status": "started",
                    "summary": None,
                    "usage": None,
                    "report": None,
                }
            elif subtype == "task_progress" and event.get("task_id") in delegates:
                delegates[event["task_id"]]["usage"] = event.get("usage")
            elif subtype == "task_notification" and event.get("task_id") in delegates:
                delegates[event["task_id"]]["status"] = event.get("status")
                delegates[event["task_id"]]["summary"] = event.get("summary")
        elif kind == "assistant":
            for part in (event.get("message") or {}).get("content") or []:
                if not isinstance(part, dict):
                    continue
                if part.get("type") == "tool_use":
                    name = part.get("name") or ""
                    tools[name] += 1
                    if name.startswith(GATE_TOOL_PREFIX) and "__" in name[len(GATE_TOOL_PREFIX):]:
                        server, tool = name[len(GATE_TOOL_PREFIX):].split("__", 1)
                        gates[server][tool] += 1
                    if name == DELEGATE_TOOL:
                        delegate_uses[part.get("id")] = part.get("input") or {}
                    if name in EDIT_TOOLS and (part.get("input") or {}).get(EDIT_TOOLS[name]):
                        files.add(str(part["input"][EDIT_TOOLS[name]]))
                elif part.get("type") == "text" and part.get("text", "").strip():
                    digest["last_message"] = part["text"]
        elif kind == "user":
            content = (event.get("message") or {}).get("content")
            if isinstance(content, list):
                for part in content:
                    if isinstance(part, dict) and part.get("type") == "tool_result":
                        text = _result_text(part.get("content"))
                        results[part.get("tool_use_id")] = text
                        blocked = HOOK_ERROR.match(text) if part.get("is_error") else None
                        if blocked:
                            hooks.append({
                                "event": blocked["event"],
                                "name": f"{blocked['event']}:{blocked['matcher']}",
                                "decision": HOOK_DENY,
                                "reason": blocked["reason"].strip(),
                                "exit_code": None,
                                "outcome": HOOK_BLOCKING,
                            })
        elif kind == "result":
            digest["turns"] += int(event.get("num_turns") or 0)
            duration_ms += int(event.get("duration_ms") or 0)
            if event.get("total_cost_usd") is not None:
                digest["cost_cumulative"] = float(event["total_cost_usd"])
            if event.get("is_error"):
                digest["errors"].append(str(event.get("result") or event.get("subtype") or "error"))
    for delegate in delegates.values():
        # A foreground delegate's report is the Agent tool's result; a
        # background one's is what its notification carries as the summary
        # (the delegate's closing message, in full).
        if delegate["background"]:
            delegate["report"] = delegate["summary"]
        elif delegate["tool_use_id"] in results:
            delegate["report"] = results[delegate["tool_use_id"]]
    digest["duration_ms"] = duration_ms if duration_ms else None
    digest["tools"] = dict(tools)
    digest["gates"] = {server: dict(counts) for server, counts in gates.items()}
    digest["hooks"] = hooks
    digest["delegates"] = list(delegates.values())
    digest["files"] = sorted(files)
    return digest


def _result_text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(
            part.get("text", "") for part in content if isinstance(part, dict) and part.get("type") == "text"
        )
    return ""


CODEX_THREAD_HEAD = '{"type":"thread.started"'
# The line a launcher appends after each `codex exec` it ran: the exit code
# that closes the thread's lines (kapso.learning.update_frame's workers).
EXIT_LINE_HEAD = '{"type":"kapso.exit"'


def codex_threads(lines: Iterable[str]) -> List[Dict[str, Any]]:
    """A stream several `codex exec` invocations appended to, split into
    its threads: each starts at a `thread.started` event and is closed by
    the launcher's exit line (`{"type":"kapso.exit","code":N}`), or by
    the next thread with no exit recorded. Returns `[{"lines", "code"}]`
    in order; lines before the first thread are nobody's."""
    threads: List[Dict[str, Any]] = []
    current: Optional[Dict[str, Any]] = None
    for raw in lines:
        line = raw.strip()
        if line.startswith(CODEX_THREAD_HEAD):
            current = {"lines": [raw], "code": None}
            threads.append(current)
        elif line.startswith(EXIT_LINE_HEAD) and current is not None:
            current["code"] = int(json.loads(line)["code"])
            current = None
        elif current is not None:
            current["lines"].append(raw)
    return threads


def digest_codex(lines: Iterable[str]) -> Dict[str, Any]:
    """Codex's `exec --json`: `thread.started` for the thread (the
    session), `item.completed` for the commands, the file changes, the
    gates' tools by server, the collaboration calls (a delegate spawned
    or waited for), the file changes (the files they name) and the
    agent's messages (the last one is the closing text), `error` items
    for the host's own errors, `turn.completed` for the turns and the
    token usage. Codex reports no hook events and no cost: `hooks` and
    `cost_cumulative` stay null."""
    digest = _empty()
    tools: Counter = Counter()
    gates: Dict[str, Counter] = defaultdict(Counter)
    delegates: List[Dict[str, Any]] = []
    files: Set[str] = set()
    for event in _events(lines, CODEX_EVENT_HEAD):
        kind = event.get("type")
        if kind == "thread.started":
            digest["cli_session_id"] = event.get("thread_id")
        elif kind == "turn.completed":
            digest["turns"] += 1
            digest["usage"] = event.get("usage")
        elif kind == "item.completed":
            item = event.get("item") or {}
            item_type = item.get("type")
            if item_type == "mcp_tool_call":
                server, tool = item.get("server") or "", item.get("tool") or ""
                tools[f"{GATE_TOOL_PREFIX}{server}__{tool}"] += 1
                gates[server][tool] += 1
            elif item_type in ("command_execution", "file_change"):
                tools[item_type] += 1
                for change in item.get("changes") or []:
                    files.add(str(change["path"]))
            elif item_type == "collab_tool_call":
                delegates.append({
                    "name": item.get("tool"),
                    "receivers": list(item.get("receiver_thread_ids") or []),
                    "status": item.get("status"),
                    "prompt": item.get("prompt"),
                })
            elif item_type == "agent_message" and (item.get("text") or "").strip():
                digest["last_message"] = item["text"]
            elif item_type == "error":
                digest["errors"].append(str(item.get("message") or item))
    digest["servers"] = sorted(gates)
    digest["tools"] = dict(tools)
    digest["gates"] = {server: dict(counts) for server, counts in gates.items()}
    digest["delegates"] = delegates
    digest["files"] = sorted(files)
    return digest
