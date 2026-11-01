"""An excerpt of a host's stream for the transcript-digest fixtures
(docs/plans/redesign/wp6-observability.md, change 2): the events the
digest reads, kept verbatim, with the bulk left out. Every line kept is
a line of the original; nothing is rewritten, so the digest of the
excerpt is the digest of the stream for the fields the excerpt keeps.

    python scripts/redesign/transcript_excerpt.py claude_code <stream> <out> [max-result-chars]
    python scripts/redesign/transcript_excerpt.py codex <stream> <out>

A line is long past four times the limit (default 300 characters).
Claude Code: thinking, tool progress, rate-limit and background-task
events go; a long `user` event goes unless it answers an `Agent` tool
use; an `assistant` event goes when it is thinking alone, or long with
no text (a file written whole), or a long message that is not the last
(the closing text stays); `task_progress` events go except the last per
task. Codex: `item.started` events go, a command whose output is longer
than the limit, and any long item that is not the last agent message;
everything else stays, the non-event lines included (the digest must
skip them). The digest of an excerpt is the excerpt's own: the counts
follow what was kept.
"""
import json
import sys

CLAUDE_DROPPED = {"thinking_tokens", "tool_progress", "background_tasks_changed"}


def excerpt_claude(lines, max_result_chars):
    kept = []
    agent_uses = set()
    last_progress = {}
    for number, raw in enumerate(lines):
        line = raw.rstrip("\n")
        if not line.startswith("{"):
            continue
        event = json.loads(line)
        kind = event.get("type")
        if kind == "rate_limit_event" or kind == "tool_progress":
            continue
        if kind == "system":
            subtype = event.get("subtype")
            if subtype in CLAUDE_DROPPED:
                continue
            if subtype == "task_progress":
                last_progress[event.get("task_id")] = number
                kept.append((number, line, event))
                continue
        long = len(line) > 4 * max_result_chars
        if kind == "assistant":
            parts = [part for part in (event.get("message") or {}).get("content") or [] if isinstance(part, dict)]
            for part in parts:
                if part.get("type") == "tool_use" and part.get("name") == "Agent":
                    agent_uses.add(part.get("id"))
            has_text = any(part.get("type") == "text" and part.get("text", "").strip() for part in parts)
            has_tool_use = any(part.get("type") == "tool_use" for part in parts)
            if not has_text and not has_tool_use:
                continue                      # thinking alone
            if long and not has_text:
                continue                      # a file written whole
            if long and has_text:
                last_text = number            # a long message: kept only when it is the last
                kept.append((number, line, event))
                continue
        if kind == "user":
            content = (event.get("message") or {}).get("content")
            answers_agent = isinstance(content, list) and any(
                isinstance(part, dict) and part.get("tool_use_id") in agent_uses for part in content
            )
            if long and not answers_agent:
                continue
        kept.append((number, line, event))
    out = []
    for number, line, event in kept:
        if event.get("type") == "system" and event.get("subtype") == "task_progress":
            if last_progress.get(event.get("task_id")) != number:
                continue
        if event.get("type") == "assistant" and len(line) > 4 * max_result_chars and number != last_text:
            continue
        out.append(line)
    return out


def excerpt_codex(lines, max_output_chars):
    kept = []
    last_message = None
    for number, raw in enumerate(lines):
        line = raw.rstrip("\n")
        if line.startswith('{"type":'):
            event = json.loads(line)
            if event.get("type") == "item.started":
                continue
            item = event.get("item") or {}
            if item.get("type") == "command_execution" and len(item.get("aggregated_output") or "") > max_output_chars:
                continue
            if item.get("type") == "file_change" and len(line) > 4 * max_output_chars:
                continue
            if item.get("type") == "agent_message":
                last_message = number
        kept.append((number, line))
    out = []
    for number, line in kept:
        # A long item goes, unless it is the last agent message (the closing text).
        if len(line) > 4 * max_output_chars and number != last_message:
            continue
        out.append(line)
    return out


def main(argv):
    host, source, target = argv[1], argv[2], argv[3]
    with open(source, encoding="utf-8", errors="replace") as handle:
        lines = handle.readlines()
    if host == "claude_code":
        limit = int(argv[4]) if len(argv) > 4 else 300
        out = excerpt_claude(lines, limit)
    elif host == "codex":
        limit = int(argv[4]) if len(argv) > 4 else 300
        out = excerpt_codex(lines, limit)
    else:
        raise SystemExit(f"unknown host {host!r}")
    with open(target, "w", encoding="utf-8") as handle:
        handle.write("\n".join(out) + "\n")
    print(f"{target}: {len(out)} of {len(lines)} lines")


if __name__ == "__main__":
    main(sys.argv)
