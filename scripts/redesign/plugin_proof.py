#!/usr/bin/env python3
"""The plugin round (docs/plans/redesign/wp7-plugin.md, change 11): the
acceptance matrix's steps driven on one host by a scripted person (S2
without the simulated user and the judge), each step recorded in the
semantic record shape (tests/semantic/README.md, test `S2-mechanical`)
and rendered by tests/semantic/report.py against tests/semantic/budgets.json.

    python3 scripts/redesign/plugin_proof.py --host claude_code|codex --clone <repo> --out <dir>
        [--work <dir>] [--steps a,b,...] [--from <step>] [--wheel <path>] [--machine <name>]

Runs where the host's CLI is logged in and the package is installed with
`kapso` and `kapso-mcp` on PATH: the Claude Code half on a fresh machine,
the Codex half on the development box. The record is written after every
step, so a crash keeps what ran and `--from` continues. Every step the
matrix marks deferred for the host is recorded as such. The driver uses
the standard library and PyYAML (the examples' python3 has it).
"""

import argparse
import glob
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import time
import uuid
from datetime import datetime, timezone

import yaml
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence

CLAUDE_MODEL = "claude-opus-5-5"
CODEX_MODEL = "gpt-6-astra"
TURN_TIMEOUT = 1800
# A turn that waits for a word without a question mark: "say go and I'll launch".
APPROVAL_ASKED = re.compile(r"\b(say|reply|type|answer)\b[^\n]{0,30}\bgo\b|\b(confirm|approve|approval)\b|\bshall i\b|\bwant me to\b|\blet me know\b", re.I)
CHURN_WISH = (
    "get the churn model's ROC AUC above 0.85 without changing the prediction contract; "
    "the campaign goes to ../churn-campaign with a budget of 60 minutes and 3 experiments"
)
PAUSE_WISH = (
    "get the churn model's ROC AUC above 0.85; one rule for the brief: before training, the enrichment table "
    "must be fetched from the enrichment service with the DATA_API_KEY in .env, and a session that lacks the key "
    "asks for it through the inbox. Launch now without asking me for the key: the campaign's own session asks "
    "when it needs it. The campaign goes to ../churn-pause-campaign with a budget of 10 minutes and 1 experiment"
)
FRAUD_WISH = (
    "build a fraud scorer on data/transactions.csv that beats the rule-based one in score.py, and prove it; "
    "the campaign goes to ../fraud-campaign with a budget of 10 minutes and 1 experiment"
)
# The order the round runs in; the budgets file bounds every name.
STEP_NAMES = [
    "install", "setup", "cold-install", "build-churn", "build-pause", "watch", "triggers", "harness-export", "campaign-tools",
    "inbox", "build-fraud", "build-data-only", "build-empty-wish", "harness-new", "harness-probe", "review",
    "deploy", "learn", "learn-complete", "session-brief", "experience-share", "harness-improve",
    "campaign-session-isolation", "cold-start",
]
# Codex's explicit skill for each Claude Code command.
CODEX_SKILL = {"setup": "kapso-setup", "build": "kapso-build", "review": "kapso-review", "harness": "kapso-harness"}
CODEX_DEFERRED = {
    "cold-install": "one machine: the cold wheel install is the fresh machine's step",
    "harness-improve": "deferred on Codex by the matrix",
    "learn": "hours on the development box; the Claude Code half runs it",
    "learn-complete": "hours on the development box; the Claude Code half runs it",
    "experience-share": "deferred on Codex by the matrix",
    "cold-start": "the launcher is Claude Code's path; Codex runs kapso-mcp from PATH",
}


# ----------------------------------------------------------------- hosts
class Turn:
    def __init__(self, text: str, seconds: float, session: str, tools: List[Dict[str, Any]], asked: bool):
        self.text, self.seconds, self.session, self.tools, self.asked = text, seconds, session, tools, asked


def question_asked(text: str, tools: Sequence[Dict[str, Any]]) -> bool:
    """A turn that ends asking: the AskUserQuestion tool, or a question
    among its closing lines (an approval request is often followed by a
    sentence on why it is needed)."""
    if any(tool["name"] == "AskUserQuestion" for tool in tools):
        return True
    lines = [line.strip().rstrip("*_`)\"' ") for line in text.splitlines() if line.strip()]
    closing = "\n".join(lines[-6:])
    return any(line.endswith("?") for line in lines[-6:]) or bool(APPROVAL_ASKED.search(closing))


def lines_outside_fences(text: str) -> int:
    count, fenced = 0, False
    for line in text.splitlines():
        if line.strip().startswith("```"):
            fenced = not fenced
            continue
        if not fenced and line.strip():
            count += 1
    return count


class ClaudeHost:
    name = "claude_code"

    def command(self, verb: str, args: str = "") -> str:
        return f"/kapso:{verb} {args}".strip()

    def turn(self, cwd: Path, prompt: str, session: Optional[str], transcript: Path) -> Turn:
        sid = session or str(uuid.uuid4())
        # The turn's deadline is the `timeout` command's: a turn that
        # overstays ends with exit 124 and its stream so far, and the round
        # goes on with what it has.
        argv = ["timeout", str(TURN_TIMEOUT), "claude", "-p", "--dangerously-skip-permissions", "--output-format", "stream-json", "--verbose", "--model", CLAUDE_MODEL]
        argv += ["--resume", sid] if session else ["--session-id", sid]
        started = time.monotonic()
        run = subprocess.run(argv, input=prompt, capture_output=True, text=True, cwd=str(cwd))
        with open(transcript, "a", encoding="utf-8") as out:
            out.write(json.dumps({"proof_prompt": prompt}) + "\n" + run.stdout + ("\n" if not run.stdout.endswith("\n") else ""))
            if run.stderr.strip():
                out.write(json.dumps({"proof_stderr": run.stderr}) + "\n")
        text, tools, seconds = "", [], time.monotonic() - started
        for line in run.stdout.splitlines():
            if not line.startswith("{"):
                continue
            event = json.loads(line)
            if event.get("type") == "assistant":
                for block in event["message"].get("content", []):
                    if block.get("type") == "tool_use":
                        tools.append({"name": block["name"], "input": block.get("input", {})})
            elif event.get("type") == "result":
                text = event.get("result") or ""
                seconds = event.get("duration_ms", seconds * 1000) / 1000
                sid = event.get("session_id", sid)
        return Turn(text, seconds, sid, tools, question_asked(text, tools))


class CodexHost:
    name = "codex"

    def command(self, verb: str, args: str = "") -> str:
        return f"${CODEX_SKILL.get(verb, 'kapso')} {verb if verb not in CODEX_SKILL else ''} {args}".replace("  ", " ").strip()

    def turn(self, cwd: Path, prompt: str, session: Optional[str], transcript: Path) -> Turn:
        last = cwd / ".proof-last.txt"
        argv = ["timeout", str(TURN_TIMEOUT), "codex", "exec", "--json", "--skip-git-repo-check", "--sandbox", "danger-full-access", "-C", str(cwd), "-m", CODEX_MODEL, "-o", str(last)]
        if session:
            argv += ["resume", session, "-"]
        else:
            argv.append(prompt)
        started = time.monotonic()
        run = subprocess.run(argv, input=prompt if session else None, capture_output=True, text=True, cwd=str(cwd))
        seconds = time.monotonic() - started
        with open(transcript, "a", encoding="utf-8") as out:
            out.write(json.dumps({"proof_prompt": prompt}) + "\n" + run.stdout + ("\n" if not run.stdout.endswith("\n") else ""))
            if run.stderr.strip():
                out.write(json.dumps({"proof_stderr": run.stderr}) + "\n")
        tools, sid = [], session or ""
        for line in run.stdout.splitlines():
            if not line.startswith("{"):
                continue
            event = json.loads(line)
            if event.get("type") == "thread.started":
                sid = event["thread_id"]
            item = event.get("item") or {}
            if event.get("type") == "item.completed" and item.get("type") == "command_execution":
                tools.append({"name": "Bash", "input": {"command": item.get("command", "")}})
            elif event.get("type") == "item.completed" and item.get("type") == "mcp_tool_call":
                tools.append({"name": f"mcp__{item.get('server')}__{item.get('tool')}", "input": item.get("arguments", {})})
        text = last.read_text(encoding="utf-8") if last.exists() else ""
        if last.exists():
            last.unlink()
        return Turn(text, seconds, sid, tools, question_asked(text, tools))


# --------------------------------------------------------------- context
class Context:
    def __init__(self, host, clone: Path, work: Path, out: Path, wheel: Optional[Path], machine: str, learn_model: Optional[str] = None):
        self.host, self.clone, self.work, self.out, self.wheel, self.machine = host, clone, work, out, wheel, machine
        self.learn_model = learn_model
        self.state_file = out / "state.json"
        self.state: Dict[str, Any] = json.loads(self.state_file.read_text()) if self.state_file.exists() else {}
        (out / "transcripts").mkdir(parents=True, exist_ok=True)
        (out / "artifacts").mkdir(parents=True, exist_ok=True)

    def save(self) -> None:
        self.state_file.write_text(json.dumps(self.state, indent=1) + "\n", encoding="utf-8")

    def shell(self, command: str, cwd: Optional[Path] = None, timeout: int = 1800, check: bool = True) -> subprocess.CompletedProcess:
        run = subprocess.run(["bash", "-c", command], capture_output=True, text=True, cwd=str(cwd or self.work), timeout=timeout)
        with open(self.out / "shell.log", "a", encoding="utf-8") as log:
            log.write(f"$ {command}\n{run.stdout}{run.stderr}[exit {run.returncode}]\n")
        if check and run.returncode != 0:
            raise RuntimeError(f"{command!r} exited {run.returncode}: {run.stderr.strip()[:500]}")
        return run

    def artifact(self, name: str, text: str) -> str:
        path = self.out / "artifacts" / name
        path.write_text(text, encoding="utf-8")
        return f"artifacts/{name}"

    def copy_artifact(self, source: Path, name: str) -> str:
        target = self.out / "artifacts" / name
        if source.is_dir():
            if target.exists():
                shutil.rmtree(target)
            shutil.copytree(source, target)
        else:
            shutil.copy2(source, target)
        return f"artifacts/{name}"

    def converse(self, step: str, cwd: Path, opening: str, answer: Callable[[str, int], Optional[str]], max_turns: int = 8) -> List[Turn]:
        transcript = self.out / "transcripts" / f"{step}.jsonl"
        turns: List[Turn] = []
        session, prompt = None, opening
        for index in range(max_turns):
            turn = self.host.turn(cwd, prompt, session, transcript)
            turns.append(turn)
            session = turn.session
            if not turn.asked:
                break
            reply = answer(turn.text, index)
            if reply is None:
                break
            prompt = reply
        return turns

    def fixture(self, name: str, target: str, generate: bool = True) -> Path:
        """A copy of an example under the work directory, its data generated,
        the session's credentials in its `.env`."""
        path = self.work / target
        if path.exists():
            shutil.rmtree(path)
        shutil.copytree(self.clone / "examples" / name, path, ignore=shutil.ignore_patterns("campaign", "__pycache__", "data", "private"))
        if generate:
            self.shell("python3 generate.py", cwd=path, timeout=600)
        self.seed_env(path)
        return path

    def seed_env(self, project: Path) -> None:
        """A host session's shell carries no `CLAUDE_CODE_OAUTH_TOKEN` (the
        host keeps its own token from its tools), so a machine logged in
        by token puts it in the project's `.env`, the doctor's fix line;
        a machine with a stored login has nothing to seed."""
        token = os.environ.get("CLAUDE_CODE_OAUTH_TOKEN")
        if token:
            with open(project / ".env", "a", encoding="utf-8") as env:
                env.write(f"CLAUDE_CODE_OAUTH_TOKEN={token}\n")


def project_config(project: Path, blocks: Dict[str, Any]) -> Path:
    """The project's kapso-config.yaml with `blocks` merged over what it
    holds; the skills pass it on every line."""
    path = project / "kapso-config.yaml"
    current = yaml.safe_load(path.read_text(encoding="utf-8")) if path.is_file() else {}
    current = current or {}
    for key, value in blocks.items():
        current[key] = {**current.get(key, {}), **value} if isinstance(value, dict) and isinstance(current.get(key), dict) else value
    path.write_text(yaml.safe_dump(current, sort_keys=False), encoding="utf-8")
    return path


def effective_config(ctx: "Context", project: Path) -> Dict[str, Any]:
    return yaml.safe_load(ctx.shell("kapso doctor --show-config" + (" --config kapso-config.yaml" if (project / "kapso-config.yaml").is_file() else ""), cwd=project).stdout)


def learning_on(block: Any, model: str, replaced: str) -> Any:
    """The learning block with every crew on `model` instead of `replaced`."""
    if isinstance(block, dict):
        return {key: learning_on(value, model, replaced) for key, value in block.items()}
    if isinstance(block, list):
        return [learning_on(item, model, replaced) for item in block]
    return model if block == replaced else block


def wait_for(predicate: Callable[[], bool], seconds: int, every: int = 10) -> bool:
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(every)
    return predicate()


def status_of(campaign: Path) -> Optional[Dict[str, Any]]:
    path = campaign / ".kapso" / "status.json"
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def record_step(name: str, turns: Sequence[Turn], completed: bool, artifacts: Sequence[str], notes: Sequence[str] = (), extra_minutes: float = 0.0) -> Dict[str, Any]:
    return {
        "name": name,
        "messages": len(turns),
        "questions": sum(1 for turn in turns if turn.asked),
        "minutes": round(sum(turn.seconds for turn in turns) / 60 + extra_minutes, 1),
        "longest_message_lines": max((lines_outside_fences(turn.text) for turn in turns), default=0),
        "completed": completed,
        "artifacts": list(artifacts),
        "notes": list(notes),
    }


def shell_step(name: str, completed: bool, artifacts: Sequence[str], minutes: float, notes: Sequence[str] = ()) -> Dict[str, Any]:
    return record_step(name, [], completed, artifacts, notes, extra_minutes=round(minutes, 1))


# --------------------------------------------------------- answer policies
def go_policy(text: str, index: int) -> Optional[str]:
    lower = text.lower()
    if "key" in lower and ("api" in lower or ".env" in lower or "token" in lower):
        return "Launch anyway: the campaign's own session asks through the inbox when it needs the key. Go."
    return "go"


def setup_policy(text: str, index: int) -> Optional[str]:
    lower = text.lower()
    if "leeroopedia" in lower or "openai" in lower or "key" in lower:
        return "I have neither key; continue."
    if "harness" in lower:
        return "No harness for now."
    return "yes"


def stop_here_policy(text: str, index: int) -> Optional[str]:
    return "The first one. Stop here: do not launch anything." if index == 0 else None


HARNESS_ANSWERS = [
    ("ideation", "Vary the signal family (trend, mean reversion, volatility targeting), the lookback, and the sizing rule; one axis per attempt."),
    ("verification", "Before a candidate counts: the look-ahead scan passes, the backtest covers 2021 to 2023, and the risk line (max drawdown, annual turnover) is printed."),
    ("feedback", "Prefer robust over spectacular: a consistent Sharpe across years beats one great year; say which axis to try next."),
    ("deployment", "Paper trading only; the target is the deploy call's."),
    ("learning", "Nothing to add; the defaults."),
    ("setup", "Pin the data snapshot once and record its hash; every session reads the snapshot, never a live fetch."),
]


def harness_policy(text: str, index: int) -> Optional[str]:
    """The proposal gets "go"; a turn that asks about modules gets every
    answer its questions call for, in one reply, as a person answering a
    numbered list would."""
    lower = text.lower()
    if index == 0 and ("confirm" in lower or "go" in lower or "proposal" in lower or "write" in lower):
        return "go"
    answers = [f"{key}: {answer}" for key, answer in HARNESS_ANSWERS if key in lower]
    if answers:
        return "\n".join(answers) + "\nNothing else to add; write them in the cheapest form and run the check."
    return "Use your best judgement from the repository; nothing else to add."


# ------------------------------------------------------------------ steps
def step_install(ctx: Context) -> Dict[str, Any]:
    started = time.monotonic()
    artifacts, notes = [], []
    if ctx.host.name == "claude_code":
        ctx.shell(f"claude plugin marketplace add {ctx.clone}")
        ctx.shell("claude plugin install kapso@kapso")
        validate = ctx.shell(f"claude plugin validate {ctx.clone / 'plugin'} --strict --json", check=False)
        artifacts.append(ctx.artifact("validate.json", validate.stdout))
        details = ctx.shell("claude plugin details kapso@kapso", check=False)
        artifacts.append(ctx.artifact("details.txt", details.stdout + details.stderr))
        listing = ctx.shell("claude plugin list", check=False)
        artifacts.append(ctx.artifact("plugin-list.txt", listing.stdout))
        completed = validate.returncode == 0 and "kapso" in listing.stdout
    else:
        ctx.shell(f"codex plugin marketplace add {ctx.clone}")
        ctx.shell("codex plugin add kapso@kapso")
        probe = ctx.host.turn(ctx.work, "$kapso Do not run any command: in one sentence, say which skill you loaded and stop.", None, ctx.out / "transcripts" / "install.jsonl")
        artifacts.append(ctx.artifact("install-probe.txt", probe.text))
        completed = "kapso" in probe.text.lower()
        notes.append("Codex: the plugin's skills load by name; its MCP tools reach a session through the `codex mcp add` line the setup skill runs")
    return shell_step("install", completed, artifacts, (time.monotonic() - started) / 60, notes)


def step_setup(ctx: Context) -> Dict[str, Any]:
    project = ctx.fixture("churn-first-build", "churn")
    ctx.state["churn_project"] = str(project)
    ctx.save()
    turns = ctx.converse("setup", project, ctx.host.command("setup"), setup_policy)
    doctor = ctx.shell("kapso doctor build --json", cwd=project, check=False)
    artifacts = [ctx.artifact("setup-doctor.json", doctor.stdout)]
    rows = json.loads(doctor.stdout) if doctor.stdout.strip().startswith(("{", "[")) else {}
    checks = rows.get("checks", rows) if isinstance(rows, dict) else rows
    required_ok = all(row.get("ok") for row in checks if isinstance(row, dict) and row.get("required")) if isinstance(checks, list) else doctor.returncode == 0
    notes = ["link clicks: judged by hand from the transcript (the logins were present, so none were needed)"]
    if ctx.host.name == "codex":
        servers = ctx.shell("codex mcp list", check=False)
        artifacts.append(ctx.artifact("codex-mcp-list.txt", servers.stdout))
        notes.append("the `codex mcp add kapso -- kapso-mcp` line's effect is the mcp list artifact")
    return record_step("setup", turns, required_ok, artifacts, notes)


def step_cold_install(ctx: Context) -> Dict[str, Any]:
    started = time.monotonic()
    wheel = ctx.wheel
    user = "proof2"
    ctx.shell(f"id -u {user} >/dev/null 2>&1 || sudo useradd -m -s /bin/bash {user}")
    if wheel.resolve() != Path("/tmp") / wheel.name:
        ctx.shell(f"sudo cp {wheel} /tmp/{wheel.name}")
    ctx.shell(f"sudo chmod 644 /tmp/{wheel.name}")
    # From the user's own home: `kapso` reads `.env` from the working
    # directory, and a directory the user cannot see is no place to run.
    script = (
        "set -e; cd ~; curl -LsSf https://astral.sh/uv/install.sh | sh >/dev/null 2>&1; export PATH=$HOME/.local/bin:$PATH; "
        f"uv tool install --python 3.12 /tmp/{wheel.name} >/dev/null 2>&1; echo kapso $(kapso --version); echo kapso-mcp $(kapso-mcp --version); "
        "echo which $(which kapso) $(which kapso-mcp)"
    )
    run = ctx.shell(f"sudo -u {user} -H bash -lc {shlex.quote(script)}", timeout=1200, check=False)
    text = run.stdout + run.stderr
    versions = re.findall(r"^(kapso|kapso-mcp) (\S+)", run.stdout, re.M)
    completed = run.returncode == 0 and len({version for _, version in versions}) == 1 and len(versions) == 2
    return shell_step("cold-install", completed, [ctx.artifact("cold-install.txt", text)], (time.monotonic() - started) / 60)


def _launch_and_wait_status(ctx: Context, project: Path, campaign: Path, wish: str, step: str, policy=go_policy) -> Dict[str, Any]:
    turns = ctx.converse(step, project, ctx.host.command("build", wish), policy, max_turns=4)
    brief = project / "kapso-brief.md"
    launched = wait_for(lambda: status_of(campaign) is not None, 180)
    artifacts = []
    if brief.is_file():
        artifacts.append(ctx.copy_artifact(brief, f"{step}-brief.md"))
    if launched:
        artifacts.append(ctx.copy_artifact(campaign / ".kapso" / "status.json", f"{step}-status.json"))
    return {"turns": turns, "launched": launched, "brief": brief.is_file(), "artifacts": artifacts}


def step_build_churn(ctx: Context) -> Dict[str, Any]:
    # The fixture again, clean: the setup step's session may have touched it.
    project = ctx.fixture("churn-first-build", "churn")
    campaign = ctx.work / "churn-campaign"
    ctx.state["churn_campaign"] = str(campaign)
    ctx.state["churn_launched_at"] = time.time()
    ctx.save()
    result = _launch_and_wait_status(ctx, project, campaign, CHURN_WISH, "build-churn")
    return record_step("build-churn", result["turns"], result["launched"] and result["brief"], result["artifacts"])


def step_build_pause(ctx: Context) -> Dict[str, Any]:
    """The injected pause for the inbox step: a brief rule naming a key
    `.env` lacks, launched beside the churn campaign at a tiny budget."""
    project = ctx.fixture("churn-first-build", "churn-pause")
    campaign = ctx.work / "churn-pause-campaign"
    if campaign.exists():
        ctx.shell(f"kapso build --output {campaign} --stop", check=False)
        shutil.rmtree(campaign)
    ctx.state["pause_campaign"] = str(campaign)
    ctx.save()
    result = _launch_and_wait_status(ctx, project, campaign, PAUSE_WISH, "build-pause")
    return record_step("build-pause", result["turns"], result["launched"] and result["brief"], result["artifacts"])


def step_watch(ctx: Context) -> Dict[str, Any]:
    project, campaign = Path(ctx.state["churn_project"]), ctx.state["churn_campaign"]
    wait_for(lambda: time.time() - ctx.state["churn_launched_at"] > 120, 130)
    first = ctx.converse("watch", project, ctx.host.command("watch", "../churn-campaign"), lambda text, index: None, max_turns=1)
    second = ctx.converse("watch-2", project, "how is the kapso campaign in ../churn-campaign going?", lambda text, index: None, max_turns=1)
    turns = first + second
    text = "\n".join(turn.text for turn in turns).lower()
    completed = all(not turn.asked for turn in turns) and any(word in text for word in ("running", "setup", "ideation", "implementation", "phase", "best"))
    return record_step("watch", turns, completed, [ctx.artifact("watch-answers.txt", "\n\n---\n\n".join(turn.text for turn in turns))])


CASE_NAME = re.compile(r"^(?P<skill>[a-z]+)-(?P<kind>[eicn])\d+$")
TRIGGER_BAR = 0.9   # eighteen of twenty per skill


def trigger_bar(out_dir: Path, host: str) -> Dict[str, Any]:
    """The suite's verdict per skill from its result file: the share of
    the skill's cases that passed every run, and the near misses that
    invoked the skill under test (a cross-skill false positive)."""
    passed: Dict[str, List[bool]] = {}
    false_positives: List[str] = []
    if host == "claude_code":
        document = json.loads((out_dir / "triggers.json").read_text(encoding="utf-8"))
        for case in document["cases"]:
            match = CASE_NAME.match(case["name"])
            if match is None:
                continue
            passed.setdefault(match.group("skill"), []).append(case["aggregates"]["score"] >= 1.0)
            for run in case["arms"]["with"]:
                if any(g["name"].startswith("not-") and not g["passed"] for g in run.get("graders", [])):
                    false_positives.append(case["name"])
    else:
        document = json.loads((out_dir / "results.json").read_text(encoding="utf-8"))
        by_case: Dict[str, List[Dict[str, Any]]] = {}
        for result in document["results"]:
            by_case.setdefault(result["case"], []).append(result)
        for name, runs in by_case.items():
            match = CASE_NAME.match(name)
            if match is None:
                continue
            passed.setdefault(match.group("skill"), []).append(all(run["passed"] for run in runs))
            if any(g["name"].startswith("not-") and not g["passed"] for run in runs for g in run["graders"]):
                false_positives.append(name)
    per_skill = {skill: f"{sum(ok)}/{len(ok)}" for skill, ok in passed.items()}
    met = bool(passed) and all(sum(ok) >= TRIGGER_BAR * len(ok) for ok in passed.values()) and not false_positives
    return {"per_skill": per_skill, "false_positives": sorted(set(false_positives)), "met": met}


def step_triggers(ctx: Context) -> Dict[str, Any]:
    started = time.monotonic()
    which = "claude-triggers" if ctx.host.name == "claude_code" else "codex-triggers"
    main = ctx.shell(f"bash scripts/redesign/plugin_round.sh {which} --tag main", cwd=ctx.clone, timeout=10800, check=False)
    holdout = ctx.shell(f"bash scripts/redesign/plugin_round.sh {which} --tag holdout --runs 1", cwd=ctx.clone, timeout=3600, check=False)
    artifacts, notes, verdicts = [], [], []
    for label, run in (("main", main), ("holdout", holdout)):
        out_dir = run.stdout.strip().splitlines()[-1] if run.stdout.strip() else ""
        if out_dir and Path(out_dir).is_dir():
            artifacts.append(ctx.copy_artifact(Path(out_dir), f"triggers-{label}"))
            result_file = Path(out_dir) / ("triggers.json" if ctx.host.name == "claude_code" else "results.json")
            if result_file.is_file():
                verdict = trigger_bar(Path(out_dir), ctx.host.name)
                verdicts.append(verdict["met"])
                notes.append(f"{label}: {verdict['per_skill']}; cross-skill false positives: {verdict['false_positives'] or 'none'}")
            else:
                verdicts.append(False)
                notes.append(f"{label}: the suite wrote no result file (exit {run.returncode})")
        artifacts.append(ctx.artifact(f"triggers-{label}.log", run.stdout + run.stderr))
    notes.append("the bar: nine of ten of each skill's cases passing every run, no near miss invoking the skill under test; the holdout is read the same way")
    return shell_step("triggers", bool(verdicts) and all(verdicts), artifacts, (time.monotonic() - started) / 60, notes)


def step_harness_export(ctx: Context) -> Dict[str, Any]:
    started = time.monotonic()
    harness = ctx.clone / "examples" / "harnesses" / "trading"
    artifacts = []
    for host in ("claude_code", "codex"):
        target = ctx.work / f"export-{host}"
        if target.exists():
            shutil.rmtree(target)
        target.mkdir(parents=True)
        run = ctx.shell(f"kapso harness export {harness} --host {host} --to {target}", check=False)
        artifacts.append(ctx.artifact(f"export-{host}.txt", run.stdout + run.stderr))
        tree = sorted(str(path.relative_to(target)) for path in target.rglob("*") if path.is_file())
        artifacts.append(ctx.artifact(f"export-{host}-files.txt", "\n".join(tree) + "\n"))
    refused = ctx.shell(f"kapso harness export {harness} --host claude_code --to {ctx.work / 'export-claude_code'}", check=False)
    artifacts.append(ctx.artifact("export-refusal.txt", refused.stdout + refused.stderr))
    session_dir = ctx.work / "export-claude_code"
    turns = ctx.converse("harness-export", session_dir, "Using the backtesting skill in this project, tell me in three lines what timestamp discipline it asks for. Load the skill rather than guessing.", lambda text, index: None, max_turns=1) if ctx.host.name == "claude_code" else []
    skill_used = any(tool["name"] == "Skill" and "backtesting" in json.dumps(tool["input"]) for turn in turns for tool in turn.tools) if turns else True
    completed = refused.returncode != 0 and (ctx.work / "export-codex" / ".codex" / "agents" / "lookahead-auditor.toml").is_file() and skill_used
    step = record_step("harness-export", turns, completed, artifacts)
    step["minutes"] = round(step["minutes"] + (time.monotonic() - started) / 60, 1)
    return step


def step_campaign_tools(ctx: Context) -> Dict[str, Any]:
    project = Path(ctx.state["churn_project"])
    prompt = (
        "Use the kapso_build_start tool (not the shell) to start a campaign of this repository: brief kapso-brief.md, repo ., "
        "output ../tools-campaign, evaluation evaluation, data data, budget 10 minutes and 1 experiment. Then read it with "
        "kapso_status, then end it with kapso_stop, and report the three answers verbatim."
    )
    turns = ctx.converse("campaign-tools", project, prompt, lambda text, index: None, max_turns=1)
    names = [tool["name"] for turn in turns for tool in turn.tools]
    used = {tool for tool in ("kapso_build_start", "kapso_status", "kapso_stop") if any(name.endswith(tool) for name in names)}
    artifacts = [ctx.artifact("campaign-tools.txt", "\n".join(names) + "\n\n" + "\n".join(turn.text for turn in turns))]
    receipt = ctx.work / "tools-campaign.launch.json"
    if receipt.is_file():
        artifacts.append(ctx.copy_artifact(receipt, "tools-campaign.launch.json"))
    ctx.shell(f"kapso build --output {ctx.work / 'tools-campaign'} --stop", check=False)
    return record_step("campaign-tools", turns, used == {"kapso_build_start", "kapso_status", "kapso_stop"}, artifacts)


def step_inbox(ctx: Context) -> Dict[str, Any]:
    project = ctx.work / "churn-pause"
    campaign = Path(ctx.state["pause_campaign"])
    paused = wait_for(lambda: (campaign / ".kapso" / "inbox.jsonl").is_file(), 900, every=15)
    notes = [f"the injected pause arrived: {paused}"]
    turns = ctx.converse("inbox", project, ctx.host.command("inbox", "../churn-pause-campaign"), lambda text, index: None, max_turns=1)
    # The person does what the request's fix line says before saying so:
    # the key into the campaign's .env (and the project's), never the reply.
    for env in (campaign / ".env", project / ".env"):
        with open(env, "a", encoding="utf-8") as out:
            out.write("DATA_API_KEY=proof-placeholder-key\n")
    turns += ctx.converse(
        "inbox-reply", project,
        "DATA_API_KEY is in .env now, in the campaign's and the project's. There is no enrichment service to "
        "document: reply to the request that the key is in place and that it must reach 0.85 without the enrichment table.",
        lambda text, index: None, max_turns=1,
    )
    artifacts = [ctx.artifact("inbox-answers.txt", "\n\n---\n\n".join(turn.text for turn in turns))]
    inbox = campaign / ".kapso" / "inbox.jsonl"
    if inbox.is_file():
        artifacts.append(ctx.copy_artifact(inbox, "inbox.jsonl"))
    replied = inbox.is_file() and any('"reply"' in line or '"answer"' in line or '"note"' in line for line in inbox.read_text(encoding="utf-8").splitlines())
    ctx.shell(f"kapso build --output {campaign} --stop", check=False)
    return record_step("inbox", turns, paused and replied, artifacts, notes)


def step_build_fraud(ctx: Context) -> Dict[str, Any]:
    project = ctx.fixture("fraud-no-evaluator", "fraud")
    campaign = ctx.work / "fraud-campaign"
    result = _launch_and_wait_status(ctx, project, campaign, FRAUD_WISH, "build-fraud")
    evaluators = [str(path.relative_to(project)) for path in project.rglob("evaluate.py")]
    artifacts = result["artifacts"] + [ctx.artifact("fraud-evaluators.txt", "\n".join(evaluators) + "\n")]
    ctx.shell(f"kapso build --output {campaign} --stop", check=False)
    return record_step("build-fraud", result["turns"], result["brief"] and result["launched"], artifacts, [f"evaluator files written by the session: {evaluators}"])


def _criteria_step(ctx: Context, name: str, project: Path, wish: str) -> Dict[str, Any]:
    turns = ctx.converse(name, project, ctx.host.command("build", wish), stop_here_policy, max_turns=3)
    launched = any(path.name == "status.json" for path in ctx.work.rglob("status.json") if name in str(path))
    proposed = turns and turns[0].asked
    artifacts = [ctx.artifact(f"{name}-answers.txt", "\n\n---\n\n".join(turn.text for turn in turns))]
    return record_step(name, turns, bool(proposed) and not launched, artifacts, ["candidate criteria judged by hand from the answers artifact"])


def step_build_data_only(ctx: Context) -> Dict[str, Any]:
    project = ctx.fixture("fraud-no-evaluator", "fraud-data")
    (project / "kapso-brief.md").unlink()
    readme = project / "README.md"
    readme.write_text("# Fraud scoring\n\nLabelled transactions in data/transactions.csv and a rule-based scorer in repo/score.py.\n", encoding="utf-8")
    return _criteria_step(ctx, "build-data-only", project, "make the fraud scorer in this repository better")


def step_build_empty_wish(ctx: Context) -> Dict[str, Any]:
    project = ctx.work / "empty"
    if project.exists():
        shutil.rmtree(project)
    project.mkdir(parents=True)
    (project / "README.md").write_text("# churn-work\n\nOur churn modelling work will live here.\n", encoding="utf-8")
    ctx.seed_env(project)
    return _criteria_step(ctx, "build-empty-wish", project, "build something useful here")


def step_harness_new(ctx: Context) -> Dict[str, Any]:
    project = ctx.fixture("trading", "trading-author")
    brief = project / "kapso-brief.md"
    brief.write_text("".join(line for line in brief.read_text(encoding="utf-8").splitlines(keepends=True) if not line.startswith("Harness")), encoding="utf-8")
    ctx.state["trading_project"] = str(project)
    ctx.save()
    turns = ctx.converse("harness-new", project, ctx.host.command("harness", "new"), harness_policy, max_turns=12)
    # The session writes where the repository points (`../harnesses/trading`
    # in the README) or under the project: both are the person's.
    manifests = [
        path for path in (*project.rglob("harness.yaml"), *(ctx.work / "harnesses").rglob("harness.yaml"))
        if "campaign" not in path.parts
    ]
    artifacts = [ctx.artifact("harness-new-answers.txt", "\n\n---\n\n".join(turn.text for turn in turns))]
    green = False
    if manifests:
        harness = manifests[0].parent
        ctx.state["new_harness"] = str(harness)
        ctx.save()
        check = ctx.shell(f"kapso harness check {harness}", cwd=project, check=False)
        artifacts.append(ctx.artifact("harness-new-check.txt", check.stdout + check.stderr))
        green = check.returncode == 0 and "warn" not in check.stdout
        tree = sorted(str(path.relative_to(harness)) for path in harness.rglob("*") if path.is_file())
        shipped = ctx.clone / "examples" / "harnesses" / "trading"
        shipped_tree = sorted(str(path.relative_to(shipped)) for path in shipped.rglob("*") if path.is_file() and "__pycache__" not in path.parts)
        artifacts.append(ctx.artifact("harness-new-tree.txt", "written:\n" + "\n".join(tree) + "\n\nshipped:\n" + "\n".join(shipped_tree) + "\n"))
    return record_step("harness-new", turns, bool(manifests) and green, artifacts, ["compared with the shipped harness by hand from harness-new-tree.txt"])


def step_harness_probe(ctx: Context) -> Dict[str, Any]:
    started = time.monotonic()
    project = Path(ctx.state["trading_project"])
    harness = ctx.state.get("new_harness")
    if not harness:
        return shell_step("harness-probe", False, [], 0, ["no harness was written"])
    campaign = ctx.work / "trading-probe"
    ctx.state["probe_campaign"] = str(campaign)
    ctx.save()
    run = ctx.shell(
        f"kapso build --harness {harness} --brief kapso-brief.md --repo repo --evaluation evaluation --data data "
        f"--output {campaign} --budget-minutes 10 --budget-experiments 1 --detach", cwd=project, check=False,
    )
    done = wait_for(lambda: (status_of(campaign) or {}).get("state") in ("done", "failed"), 1500, every=20)
    artifacts = [ctx.artifact("harness-probe-launch.txt", run.stdout + run.stderr)]
    if status_of(campaign) is not None:
        artifacts.append(ctx.copy_artifact(campaign / ".kapso" / "status.json", "harness-probe-status.json"))
    return shell_step("harness-probe", run.returncode == 0 and done, artifacts, (time.monotonic() - started) / 60)


def step_review(ctx: Context) -> Dict[str, Any]:
    project, campaign = Path(ctx.state["churn_project"]), Path(ctx.state["churn_campaign"])
    finished = wait_for(lambda: (status_of(campaign) or {}).get("state") in ("done", "failed"), 4500, every=20)
    turns = ctx.converse("review", project, ctx.host.command("review", "../churn-campaign"), lambda text, index: "is it safe to merge?" if index == 0 else None, max_turns=2)
    if len(turns) == 1:
        turns += ctx.converse("review-2", project, "is the branch the campaign delivered in ../churn-campaign safe to merge?", lambda text, index: None, max_turns=1)
    artifacts = [ctx.artifact("review-answers.txt", "\n\n---\n\n".join(turn.text for turn in turns))]
    solution = campaign / ".kapso" / "solution.json"
    if solution.is_file():
        artifacts.append(ctx.copy_artifact(solution, "churn-solution.json"))
    return record_step("review", turns, finished and solution.is_file(), artifacts, [f"the churn campaign ended: {(status_of(campaign) or {}).get('state')}"])


def step_deploy(ctx: Context) -> Dict[str, Any]:
    project, campaign = Path(ctx.state["churn_project"]), Path(ctx.state["churn_campaign"])
    turns = ctx.converse("deploy", project, ctx.host.command("deploy", "../churn-campaign --target local"), lambda text, index: "call it once with the inputs the proof used and show me the answer" if index == 0 else None, max_turns=2)
    if len(turns) == 1:
        turns += ctx.converse("deploy-2", project, "call the deployment once with the inputs its proof used and show me the answer", lambda text, index: None, max_turns=1)
    deployment = campaign / ".kapso" / "deployments" / "1"
    artifacts = [ctx.artifact("deploy-answers.txt", "\n\n---\n\n".join(turn.text for turn in turns))]
    if deployment.is_dir():
        for name in ("record.json", "kapso_deployment.json"):
            if (deployment / name).is_file():
                artifacts.append(ctx.copy_artifact(deployment / name, f"deploy-{name}"))
    ctx.shell(f"kapso deploy {campaign} --stop --number 1", cwd=project, check=False)
    return record_step("deploy", turns, deployment.is_dir(), artifacts)


def step_learn(ctx: Context) -> Dict[str, Any]:
    project = Path(ctx.state["churn_project"])
    config = effective_config(ctx, project)
    notes = []
    if ctx.learn_model:
        # The round's accommodation: the crews on another model when the
        # token's window for the shipped one is spent; said in the record.
        project_config(project, {"learning": learning_on(config["learning"], ctx.learn_model, "claude-fable-5")})
        notes.append(f"the learning crews ran on {ctx.learn_model} for this round (--learn-model): the token's window for the shipped model was spent")
    status_dir = Path(config["learning"]["status_dir"]).expanduser()
    if not status_dir.is_absolute():
        status_dir = project / status_dir
    before = set(glob.glob(str(status_dir / "*.json"))) if status_dir.is_dir() else set()
    turns = ctx.converse("learn", project, ctx.host.command("learn", "../churn-campaign"), lambda text, index: None, max_turns=1)
    after = lambda: set(glob.glob(str(status_dir / "*.json"))) - before
    launched = wait_for(lambda: bool(after()), 180)
    ctx.state["learn_status"] = sorted(after())[-1] if after() else None
    ctx.save()
    artifacts = [ctx.artifact("learn-answers.txt", "\n".join(turn.text for turn in turns))]
    offered = any("session_sources" in turn.text for turn in turns)
    return record_step("learn", turns, launched, artifacts, [f"the serving offer (session_sources) was made: {offered}", *notes])


def step_learn_complete(ctx: Context) -> Dict[str, Any]:
    started = time.monotonic()
    status = ctx.state.get("learn_status")
    if not status:
        return shell_step("learn-complete", False, [], 0, ["no learn status appeared"])
    done = wait_for(lambda: json.loads(Path(status).read_text()).get("state") in ("done", "failed"), 9000, every=60)
    final = json.loads(Path(status).read_text())
    listing = ctx.shell("kapso experience list", cwd=Path(ctx.state["churn_project"]), check=False)
    artifacts = [ctx.artifact("learn-status.json", json.dumps(final, indent=1)), ctx.artifact("experience-list.txt", listing.stdout + listing.stderr)]
    cards = re.search(r"(\d+) cards", listing.stdout)
    return shell_step("learn-complete", done and final.get("state") == "done" and bool(cards) and int(cards.group(1)) > 0, artifacts, (time.monotonic() - started) / 60, [f"state {final.get('state')}, cards {cards.group(1) if cards else '?'}"])


def step_session_brief(ctx: Context) -> Dict[str, Any]:
    project = Path(ctx.state["churn_project"])
    project_config(project, {"experience": {"session_sources": ["mine:all"]}})
    prompt = "What experience is this session served, according to your MCP server's instructions? Then read one card from the bank with the bank tools and quote its title."
    turns = ctx.converse("session-brief", project, prompt, lambda text, index: None, max_turns=1)
    names = [tool["name"] for turn in turns for tool in turn.tools]
    bank_read = any("bank" in name for name in names)
    artifacts = [ctx.artifact("session-brief.txt", "\n".join(names) + "\n\n" + "\n".join(turn.text for turn in turns))]
    return record_step("session-brief", turns, bank_read, artifacts, ["the sources recognised in the instructions: judged by hand from the answer"])


def step_experience_share(ctx: Context) -> Dict[str, Any]:
    project = Path(ctx.state["churn_project"])
    remote = ctx.work / "bank-remote.git"
    ctx.shell(f"rm -rf {remote} && git init -q --bare {remote}")
    turns = ctx.converse("experience-share", project, ctx.host.command("experience", f"share file://{remote}"), go_policy, max_turns=3)
    second = ctx.shell(f"sudo -u proof2 -H bash -lc 'export PATH=$HOME/.local/bin:$PATH; kapso experience add file://{remote} && kapso experience list'", check=False)
    artifacts = [ctx.artifact("experience-share.txt", "\n".join(turn.text for turn in turns)), ctx.artifact("experience-second-user.txt", second.stdout + second.stderr)]
    shared = ctx.shell(f"git -C {remote} log --oneline -1", check=False).returncode == 0
    return record_step("experience-share", turns, shared and second.returncode == 0, artifacts, ["the second user's served build at a tiny budget is run by hand when the window allows; recorded here as the add and the list"])


def step_harness_improve(ctx: Context) -> Dict[str, Any]:
    project = Path(ctx.state["trading_project"])
    harness = ctx.state.get("new_harness")
    if not harness or not ctx.state.get("probe_campaign"):
        return record_step("harness-improve", [], False, [], ["no harness or no probe campaign"])
    manifest = Path(harness) / "harness.yaml"
    before = manifest.read_text(encoding="utf-8")
    turns = ctx.converse("harness-improve", project, ctx.host.command("harness", f"improve {ctx.state['probe_campaign']}"), lambda text, index: "go" if index == 0 else None, max_turns=3)
    check = ctx.shell(f"kapso harness check {harness}", cwd=project, check=False)
    artifacts = [ctx.artifact("harness-improve-answers.txt", "\n".join(turn.text for turn in turns)), ctx.artifact("harness-improve-check.txt", check.stdout + check.stderr)]
    bumped = manifest.read_text(encoding="utf-8") != before
    return record_step("harness-improve", turns, bumped and check.returncode == 0, artifacts)


def step_campaign_session_isolation(ctx: Context) -> Dict[str, Any]:
    started = time.monotonic()
    campaign = Path(ctx.state["churn_campaign"])
    findings = []
    # The implementation sessions' streams are `.kapso/sessions/<branch>/stream.jsonl`,
    # the ideation sessions' `.kapso/ideation/iter<n>/<host>_<model>.stream.txt`.
    for stream in sorted([*campaign.rglob("stream.jsonl"), *campaign.rglob("*.stream.txt")]):
        for line in stream.read_text(encoding="utf-8").splitlines():
            if not line.startswith("{"):
                continue
            event = json.loads(line)
            if event.get("type") == "system" and event.get("subtype") == "init":
                tools = event.get("tools", [])
                commands = event.get("slash_commands", [])
                findings.append({
                    "session": str(stream.relative_to(campaign)),
                    "plugin_tools": [tool for tool in tools if "plugin_kapso" in tool],
                    "plugin_commands": [command for command in commands if command.startswith("kapso:")],
                    "servers": [server.get("name") for server in event.get("mcp_servers", [])],
                })
                break
    # A Codex session in the campaign carries the execpolicy rule in its
    # workspace instead; the file's presence is the evidence.
    rules = campaign / ".codex" / "rules" / "kapso-campaign.rules"
    report = {"claude_sessions": findings, "codex_rules_file": rules.is_file()}
    completed = bool(findings) and all(not f["plugin_tools"] and not f["plugin_commands"] for f in findings)
    return shell_step("campaign-session-isolation", completed, [ctx.artifact("isolation.json", json.dumps(report, indent=1))], (time.monotonic() - started) / 60)


def step_cold_start(ctx: Context) -> Dict[str, Any]:
    started = time.monotonic()
    launcher = ctx.clone / "plugin" / "scripts" / "kapso-mcp"
    timing = ctx.shell(f"TIMEFORMAT=%R; time bash {launcher} --version", check=False)
    details = ctx.shell("claude plugin details kapso@kapso", check=False)
    text = f"launcher --version: {timing.stdout.strip()} in {timing.stderr.strip()} s\n\n{details.stdout}"
    return shell_step("cold-start", timing.returncode == 0, [ctx.artifact("cold-start.txt", text)], (time.monotonic() - started) / 60, ["partial: the uvx and pipx branches resolve only once the pin is on PyPI"])


STEPS: Dict[str, Callable[[Context], Dict[str, Any]]] = {
    "install": step_install, "setup": step_setup, "cold-install": step_cold_install, "build-churn": step_build_churn,
    "build-pause": step_build_pause,
    "watch": step_watch, "triggers": step_triggers, "harness-export": step_harness_export, "campaign-tools": step_campaign_tools,
    "inbox": step_inbox, "build-fraud": step_build_fraud, "build-data-only": step_build_data_only,
    "build-empty-wish": step_build_empty_wish, "harness-new": step_harness_new, "harness-probe": step_harness_probe,
    "review": step_review, "deploy": step_deploy, "learn": step_learn, "learn-complete": step_learn_complete,
    "session-brief": step_session_brief, "experience-share": step_experience_share, "harness-improve": step_harness_improve,
    "campaign-session-isolation": step_campaign_session_isolation, "cold-start": step_cold_start,
}
assert list(STEPS) == STEP_NAMES


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--host", choices=["claude_code", "codex"], required=True)
    parser.add_argument("--clone", required=True, help="the repository clone (the local marketplace)")
    parser.add_argument("--out", required=True, help="where the record, transcripts and artifacts go")
    parser.add_argument("--work", default=None, help="the scratch root for the fixtures and campaigns (default: <out>/work)")
    parser.add_argument("--steps", default=None, help="a comma-separated subset, in the round's order")
    parser.add_argument("--from", dest="start", default=None, help="continue from this step")
    parser.add_argument("--wheel", default=None, help="the wheel the cold install uses")
    parser.add_argument("--machine", default=os.uname().nodename)
    parser.add_argument("--learn-model", default=None, help="run the learning crews on this model instead of the shipped one (said in the record)")
    args = parser.parse_args(argv)
    host = ClaudeHost() if args.host == "claude_code" else CodexHost()
    out = Path(args.out).resolve()
    work = Path(args.work).resolve() if args.work else out / "work"
    work.mkdir(parents=True, exist_ok=True)
    ctx = Context(host, Path(args.clone).resolve(), work, out, Path(args.wheel).resolve() if args.wheel else None, args.machine, args.learn_model)
    record_file = out / "record.json"
    record = json.loads(record_file.read_text()) if record_file.exists() else {
        "test": "S2-mechanical", "host": host.name, "machine": args.machine,
        "package": {"version": subprocess.run(["kapso", "--version"], capture_output=True, text=True).stdout.strip().split()[-1],
                    "wheel_sha256": subprocess.run(["sha256sum", str(ctx.wheel)], capture_output=True, text=True).stdout.split()[0] if ctx.wheel else "-"},
        "started": datetime.now(timezone.utc).isoformat(timespec="seconds"), "finished": None, "steps": [], "notes": [], "transcripts": [],
    }
    selected = args.steps.split(",") if args.steps else list(STEP_NAMES)
    if args.start:
        selected = selected[selected.index(args.start):]
    done = {step["name"] for step in record["steps"]}
    for name in selected:
        if name in done and not args.start:
            continue
        print(f"== {name}", flush=True)
        if host.name == "codex" and name in CODEX_DEFERRED:
            step = {"name": name, "deferred": CODEX_DEFERRED[name]}
        else:
            step = STEPS[name](ctx)
        record["steps"] = [existing for existing in record["steps"] if existing["name"] != name] + [step]
        record["finished"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
        record["transcripts"] = sorted(f"transcripts/{path.name}" for path in (out / "transcripts").glob("*.jsonl"))
        record_file.write_text(json.dumps(record, indent=1) + "\n", encoding="utf-8")
        print(json.dumps({key: value for key, value in step.items() if key != "notes"}), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
