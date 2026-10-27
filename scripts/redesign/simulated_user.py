"""The simulated user of the semantic suite (docs/plans/redesign/wp9-
semantic-suite.md, change 3): a persona card driving the host turn by turn
through the other vendor's CLI. Codex plays the engineer when Claude Code
is the host and the reverse; the prompt carries the card, the task view's
README, the step's intent, the whole history and the host's message,
nothing clipped; the reply is the next thing the persona would type, or
`DONE` alone when it would stop. A persona-side failure (a non-zero exit,
a timeout, an empty reply) raises: a quota-refused user is never a
satisfied one. The persona has no tool: Codex runs in an empty read-only
directory and is told to run nothing, Claude Code with every tool
disallowed.

    reply = next_message(card, task_dir, intent, history, host_message, host, settings)
"""

import hashlib
import json
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

import yaml

PERSONAS = Path(__file__).resolve().parent.parent.parent / "tests" / "semantic" / "personas"
PROMPT_TEMPLATE = PERSONAS / "prompt.md"
CARD_KEYS = ("name", "role", "expertise", "knows", "wants", "patience", "answers", "pushes_back_when")
CLAUDE_TOOLS = "Bash,Read,Edit,Write,MultiEdit,Glob,Grep,WebFetch,WebSearch,Agent,NotebookEdit,TodoWrite"
# Which vendor plays the engineer for which host: always the other one.
VENDOR_FOR_HOST = {"claude_code": "codex", "codex": "claude_code"}


@dataclass
class Reply:
    text: str
    done: bool
    session: Optional[str]
    seconds: float


@dataclass
class Card:
    name: str
    role: str
    expertise: str
    knows: str
    wants: str
    patience: int
    answers: str
    pushes_back_when: str
    planted: Optional[str] = None
    sha256: str = ""
    extra: Dict[str, Any] = field(default_factory=dict)


def load_card(path: Path) -> Card:
    """A persona card: every key of the README's contract present, the
    file's sha256 kept for the record's pins."""
    text = path.read_text(encoding="utf-8")
    data = yaml.safe_load(text)
    if not isinstance(data, dict):
        raise ValueError(f"{path}: a persona card is a mapping")
    missing = [key for key in CARD_KEYS if key not in data]
    if missing:
        raise ValueError(f"{path}: the card lacks {', '.join(missing)}")
    return Card(
        name=data["name"], role=data["role"].strip(), expertise=data["expertise"].strip(), knows=data["knows"].strip(),
        wants=data["wants"].strip(), patience=int(data["patience"]), answers=data["answers"].strip(),
        pushes_back_when=data["pushes_back_when"].strip(), planted=(data.get("planted") or "").strip() or None,
        sha256=hashlib.sha256(text.encode("utf-8")).hexdigest(),
    )


def template_sha256() -> str:
    return hashlib.sha256(PROMPT_TEMPLATE.read_bytes()).hexdigest()


def build_prompt(card: Card, readme: str, intent: str, history: Sequence[Dict[str, str]], host_message: str, asked: int) -> str:
    """The persona's prompt, whole: every message of the history as it was
    said (Rule 6: nothing bound for a model is clipped)."""
    lines = []
    for turn in history:
        lines.append(f"{turn['role']}: {turn['text']}")
        lines.append("")
    rendered = "\n".join(lines).rstrip() or "(nothing yet: this is the first thing the assistant says)"
    planted = f"You are certain that {card.planted}; if the assistant states otherwise, correct it before anything else.\n" if card.planted else ""
    return PROMPT_TEMPLATE.read_text(encoding="utf-8").format(
        name=card.name, role=card.role, expertise=card.expertise, knows=card.knows, wants=card.wants, answers=card.answers,
        pushes_back_when=card.pushes_back_when, planted=planted, readme=readme, intent=intent, history=rendered,
        host_message=host_message, asked=asked, patience=card.patience,
    )


def _codex_command(prompt: str, model: str, effort: Optional[str], scratch: Path) -> List[str]:
    command = ["codex", "exec", "--skip-git-repo-check", "--sandbox", "read-only", "-C", str(scratch), "--json", "-m", model]
    if effort:
        command += ["-c", f'model_reasoning_effort="{effort}"']
    return command + [prompt]


def _claude_command(prompt: str, model: str) -> List[str]:
    return ["claude", "-p", prompt, "--model", model, "--output-format", "json", "--disallowedTools", CLAUDE_TOOLS]


def _final_text(vendor: str, stdout: str) -> str:
    if vendor == "codex":
        final = ""
        for line in stdout.splitlines():
            if not line.startswith("{"):
                continue
            event = json.loads(line)
            if event.get("type") == "item.completed" and event["item"].get("type") == "agent_message":
                final = event["item"].get("text") or final
        return final
    return json.loads(stdout).get("result") or ""


def _session(vendor: str, stdout: str) -> Optional[str]:
    if vendor == "codex":
        for line in stdout.splitlines():
            if line.startswith("{"):
                event = json.loads(line)
                if event.get("type") == "thread.started":
                    return event.get("thread_id")
        return None
    return json.loads(stdout).get("session_id")


def next_message(card: Card, task_dir: Path, intent: str, history: Sequence[Dict[str, str]], host_message: str, host: str,
                 settings: Dict[str, Any], timeout: int = 600) -> Reply:
    """The persona's next message, from the other vendor's CLI. `settings`
    is the suite's `user.persona[host]` entry (vendor, model, effort);
    `task_dir` holds the task view whose README the persona reads."""
    vendor = VENDOR_FOR_HOST[host]
    if settings["vendor"] != vendor:
        raise ValueError(f"the persona for a {host} host is {vendor}'s, not {settings['vendor']}'s")
    readme = (task_dir / "README.md").read_text(encoding="utf-8")
    asked = sum(1 for turn in history if turn["role"] == "assistant" and turn.get("asked"))
    prompt = build_prompt(card, readme, intent, history, host_message, asked)
    with tempfile.TemporaryDirectory(prefix="persona-") as scratch:
        command = _codex_command(prompt, settings["model"], settings.get("effort"), Path(scratch)) if vendor == "codex" else _claude_command(prompt, settings["model"])
        run = subprocess.run(command, capture_output=True, text=True, timeout=timeout, cwd=scratch)
    if run.returncode != 0:
        raise RuntimeError(f"the persona's {vendor} session failed (exit {run.returncode}): {run.stderr.strip()[-2000:]}")
    text = _final_text(vendor, run.stdout).strip()
    if not text:
        raise RuntimeError(f"the persona's {vendor} session answered nothing: {run.stderr.strip()[-2000:]}")
    return Reply(text=text, done=text == "DONE", session=_session(vendor, run.stdout), seconds=0.0)
