"""S1 of the semantic suite (docs/plans/redesign/wp9-semantic-suite.md,
change 6): the cold engineer on the Python and command-line flow.

A model with no Kapso knowledge, in a sandbox holding the public docs (the
pages docs.json navigates to, nothing else), a task view (the repository's
own README, never the example's), the package installed into a venv that
is the Python its sessions use, attempts six tasks in Python and then on
the command line, each a fresh host session that is plugin-free, server-
free and web-free (proved from the session's init event). Per attempt:
`first_try` (the counted verb's first execution succeeds, exit 0 with the
task's evidence), `wrong_calls` (errored executions of the counted verb
before success; `--help`, `doctor`, reads and searches never count),
`minutes_to_launch`, `error_led_to_fix` (an errored execution followed by
the next execution of the same verb succeeding). Then the comprehension
questions and the two counts the design names (the Python flow in twelve
lines, the CLI flow in six commands). `--package released` runs it on the
released wheel and the tag's docs, the retrospective baseline.

    python3 s1_cold_engineer.py --host claude_code --clone <clone> --out <dir> --wheel <whl> [--package released] [--steps a,b] [--advisory <reason>]
"""

import argparse
import hashlib
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence

sys.path.insert(0, str(Path(__file__).resolve().parent))
import plugin_proof  # noqa: E402
from plugin_proof import SUITE, ClaudeHost, CodexHost, record_step, shell_step, status_of, wait_for  # noqa: E402
import judge  # noqa: E402  (the shared judge-block resolver; litellm rides along, present where S1 runs)

RELEASED = SUITE["released"]["version"]
PREREQUISITE = SUITE["builds"]["prerequisite"]
# The task table: the counted verb's shapes on each surface, and the evidence.
TASKS = [
    {"number": 1, "goal": "a better churn model from the repository under ./task (its evaluator under task/evaluation, its data under task/data, the brief task/kapso-brief.md), at a budget of 10 minutes and 1 experiment, into ./campaign-1",
     "verb": "build", "evidence": "campaign-1"},
    {"number": 2, "goal": "a fraud scorer that beats the rule-based one from the repository under ./task-fraud, which has data and a brief with the protocol but no evaluator, at a budget of 10 minutes and 1 experiment, into ./campaign-2",
     "verb": "build", "evidence": "campaign-2"},
    {"number": 3, "goal": "the churn build again, under the harness at ./harness, at 10 minutes and 1 experiment, into ./campaign-3 (the task's deviation: the harness is named by its path, since no bundled harness ships yet)",
     "verb": "build", "evidence": "campaign-3", "harness": True},
    {"number": 4, "restore": "campaign-prereq", "goal": "the delivered result of the campaign at ./campaign-prereq deployed to the local target, then called once", "verb": "deploy", "evidence": "deployment"},
    {"number": 5, "restore": "campaign-prereq", "clear_learning": True, "goal": "lessons learned from the campaign at ./campaign-prereq (start the learn; it runs on its own)", "verb": "learn", "evidence": "learn-status"},
    {"number": 6, "restore": "campaign-killed", "goal": "the campaign at ./campaign-killed was interrupted before it finished; continue it from where it stopped", "verb": "resume", "evidence": "resumed"},
]
VERB_PATTERNS = {
    "build": {"cli": re.compile(r"\bkapso\s+build\b(?!.*--resume)"), "python": re.compile(r"\.build\(")},
    "deploy": {"cli": re.compile(r"\bkapso\s+deploy\b"), "python": re.compile(r"\.deploy\(")},
    "learn": {"cli": re.compile(r"\bkapso\s+learn\b"), "python": re.compile(r"\.learn\(")},
    "resume": {"cli": re.compile(r"\bkapso\s+build\b.*--resume"), "python": re.compile(r"\.build\(.*resume\s*=\s*True")},
}
NOT_COUNTED = re.compile(r"--help|\bkapso\s+doctor\b|\bkapso\s+--version\b|\bkapso\s+watch\b|\bkapso\s+trace\b")
COMPREHENSION = (
    "You have used this package for six tasks in this directory. Answer in one short paragraph each, from what you ran and saw: "
    "(1) what did the build call do and what did it return? (2) what did the deploy call do and what did it return? "
    "(3) what did the learn call do and what did it return? (4) what did the resume do? (5) what did the harness change? "
    "(6) what is the evaluator and who runs it? (7) where is the record of a campaign on disk?"
)
CLAUDE_COLD = ["--settings", json.dumps({"enabledPlugins": {"kapso@kapso": False}}), "--strict-mcp-config", "--disallowedTools", "WebFetch,WebSearch"]
CODEX_COLD = ["-c", 'mcp_servers.kapso.command="kapso-mcp"', "-c", "mcp_servers.kapso.enabled=false", "-c", 'web_search="disabled"']


# ------------------------------------------------------------ the sandbox
def navigated_pages(clone: Path) -> List[str]:
    """The public docs: every page docs.json navigates to, nothing else."""
    pages: List[str] = []

    def walk(node: Any) -> None:
        if isinstance(node, str):
            pages.append(node)
        elif isinstance(node, dict):
            for key in ("tabs", "groups", "pages", "anchors", "dropdowns"):
                if key in node:
                    walk(node[key])
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(json.loads((clone / "docs.json").read_text(encoding="utf-8"))["navigation"])
    # The navigation names pages from the repository root (`docs/index`);
    # the snapshot resolves them under the docs directory.
    return [page[len("docs/"):] if page.startswith("docs/") else page for page in pages]


def snapshot_docs(source: Path, pages: Sequence[str], into: Path) -> int:
    """The allow-listed snapshot: the navigated pages as `.mdx`, copied with
    their paths; the images beside them. Returns the count."""
    if into.exists():
        shutil.rmtree(into)
    count = 0
    for page in pages:
        file = source / f"{page}.mdx"
        if file.is_file():
            target = into / f"{page}.mdx"
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(file, target)
            count += 1
    if (source / "images").is_dir():
        shutil.copytree(source / "images", into / "images")
    return count


def task_view(example: Path, into: Path, generate: bool = True) -> None:
    """The repository as an engineer brought it: the example without its
    README (the repository's own README stands in), its data generated."""
    if into.exists():
        shutil.rmtree(into)
    shutil.copytree(example, into, ignore=shutil.ignore_patterns("campaign", "__pycache__", "data", "private", "result.json", "README.md", "run.py", "baseline.py", "baseline.json"))
    own = example / "repo" / "README.md"
    (into / "README.md").write_text(own.read_text(encoding="utf-8") if own.is_file() else f"# {example.name}\n", encoding="utf-8")
    if generate and (into / "generate.py").is_file():
        subprocess.run([sys.executable, "generate.py"], cwd=into, check=True, capture_output=True, text=True, timeout=600)


def session_init(rows: Sequence[dict]) -> Dict[str, Any]:
    """What a Claude Code session started with: the proof that the sandbox
    is cold (no plugin, no server, no Kapso command, no web tool)."""
    for row in rows:
        if row.get("type") == "system" and row.get("subtype") == "init":
            return {
                "plugins": [p.get("source") for p in row.get("plugins", []) if p.get("source", "").startswith("kapso")],
                "mcp_servers": [s.get("name") for s in row.get("mcp_servers", [])],
                "kapso_commands": [c for c in row.get("slash_commands", []) if "kapso" in c],
                "web_tools": [t for t in row.get("tools", []) if t in ("WebFetch", "WebSearch")],
            }
    return {"plugins": None, "mcp_servers": None, "kapso_commands": None, "web_tools": None}


def is_cold(init: Dict[str, Any]) -> Optional[bool]:
    """True when the session proved it is cold (no plugin, server, Kapso
    command or web tool); None when no init row carried the proof (a Codex
    session), which the sandbox step reports as not proved, never a pass."""
    if init["plugins"] is None:
        return None
    return init["plugins"] == [] and init["mcp_servers"] == [] and init["kapso_commands"] == [] and init["web_tools"] == []


# ----------------------------------------------------------- the metrics
def executions(rows: Sequence[dict], verb: str, surface: str, sandbox: Path) -> List[Dict[str, Any]]:
    """The counted verb's executions in a session, in order, each with
    whether it errored: on the command line a Bash call whose command
    carries the verb; in Python a Bash call running a script whose text
    carries the call. Help, doctor, watch, trace, reads and searches are
    never counted."""
    pattern = VERB_PATTERNS[verb][surface]
    found: List[Dict[str, Any]] = []
    pending: Dict[str, Dict[str, Any]] = {}
    for row in rows:
        if row.get("type") == "assistant":
            for block in row["message"].get("content", []):
                if block.get("type") != "tool_use" or block.get("name") != "Bash":
                    continue
                command = block.get("input", {}).get("command", "")
                text = command
                if surface == "python":
                    scripts = re.findall(r"\b(\S+\.py)\b", command)
                    text = "\n".join((sandbox / script).read_text(encoding="utf-8", errors="replace") for script in scripts if (sandbox / script).is_file())
                    if not re.search(r"\bpython3?\b", command):
                        continue
                if NOT_COUNTED.search(command):
                    continue
                if pattern.search(text):
                    entry = {"command": command, "errored": None}
                    pending[block["id"]] = entry
                    found.append(entry)
        elif row.get("type") == "user":
            for block in row["message"].get("content", []):
                if block.get("type") == "tool_result" and block.get("tool_use_id") in pending:
                    content = block.get("content")
                    result = content if isinstance(content, str) else "".join(part.get("text", "") for part in content or [] if isinstance(part, dict))
                    pending.pop(block["tool_use_id"])["errored"] = bool(block.get("is_error")) or _looks_errored(result)
        elif row.get("type") == "item.completed" and (row.get("item") or {}).get("type") == "command_execution":
            # Codex's shape: the command and its exit status in one row.
            item = row["item"]
            command = item.get("command", "")
            run_text = command
            if surface == "python":
                scripts = re.findall(r"\b(\S+\.py)\b", command)
                run_text = "\n".join((sandbox / script).read_text(encoding="utf-8", errors="replace") for script in scripts if (sandbox / script).is_file())
                if not re.search(r"\bpython3?\b", command):
                    continue
            if NOT_COUNTED.search(command):
                continue
            if pattern.search(run_text):
                exit_code = item.get("exit_code")
                errored = (exit_code not in (0, None)) or _looks_errored(item.get("aggregated_output") or "")
                found.append({"command": command, "errored": errored})
    return found


def _looks_errored(text: str) -> bool:
    return bool(re.search(r"Traceback \(most recent call last\)|^Error:|error: ", text, re.M))


def attempt_metrics(found: Sequence[Dict[str, Any]], evidence: bool, started: float, evidence_at: Optional[float]) -> Dict[str, Any]:
    """`first_try`, `wrong_calls`, `minutes_to_launch`, `error_led_to_fix`
    from the executions and the evidence."""
    successes = [index for index, entry in enumerate(found) if entry["errored"] is False]
    first_success = successes[0] if successes else None
    wrong = len([entry for entry in found[: first_success if first_success is not None else len(found)] if entry["errored"]])
    led_to_fix = None
    if wrong:
        # One step: exactly one errored call, and it was followed by the success.
        led_to_fix = first_success is not None and wrong == 1
    return {
        "first_try": bool(found) and found[0]["errored"] is False and evidence,
        "wrong_calls": wrong,
        "minutes_to_launch": round((evidence_at - started) / 60, 1) if evidence_at else None,
        "error_led_to_fix": led_to_fix,
        "executions": len(found),
        "evidence": evidence,
    }


def python_lines(sandbox: Path, scripts: Sequence[str]) -> int:
    count = 0
    for script in scripts:
        path = sandbox / script
        if path.is_file():
            count += sum(1 for line in path.read_text(encoding="utf-8", errors="replace").splitlines() if line.strip() and not line.strip().startswith("#"))
    return count


# ------------------------------------------------------------- evidence
def pid_alive(pid: Any) -> bool:
    """Whether a process exists, from the process table (the machines are
    Linux); no signal is sent and nothing raises."""
    return isinstance(pid, int) and Path(f"/proc/{pid}").exists()


def seed_env(project: Path) -> None:
    """The token the sessions need, from the environment the round runs in
    (the machine's login is a token in its secrets file), into the
    sandbox's `.env` as the doctor's fix line says; nothing when the
    machine has a stored login."""
    token = os.environ.get("CLAUDE_CODE_OAUTH_TOKEN")
    if token:
        with open(project / ".env", "a", encoding="utf-8") as env:
            env.write(f"CLAUDE_CODE_OAUTH_TOKEN={token}\n")


def evidence_of(task: Dict[str, Any], sandbox: Path, prereq: Path) -> bool:
    kind = task["evidence"]
    if kind.startswith("campaign-"):
        status = status_of(sandbox / kind)
        if status is None:
            return False
        return not task.get("harness") or bool(status.get("harness"))
    if kind == "deployment":
        return (prereq / ".kapso" / "deployments" / "1" / "deployment.json").is_file()
    if kind == "learn-status":
        return any(sandbox.glob("**/learning/status/*.json"))
    if kind == "resumed":
        # A resume that is still in flight (running, live pid) or that already
        # carried the killed campaign through to the end (done) are both proof
        # it continued from the checkpoint; the killed campaign on its own stays
        # stopped at the kill phase, so neither state arises without a resume.
        status = status_of(sandbox / "campaign-killed") or {}
        state = status.get("state")
        return state == "done" or (state == "running" and pid_alive(status.get("pid")))
    raise ValueError(kind)


# ---------------------------------------------------------------- driver
class S1:
    def __init__(self, args: argparse.Namespace):
        self.args = args
        self.clone = Path(args.clone).resolve()
        self.out = Path(args.out).resolve()
        self.sandbox = Path(args.sandbox).resolve() if args.sandbox else self.out / "sandbox"
        (self.out / "transcripts").mkdir(parents=True, exist_ok=True)
        (self.out / "artifacts").mkdir(parents=True, exist_ok=True)
        extra = CLAUDE_COLD if args.host == "claude_code" else CODEX_COLD
        self.host = ClaudeHost(extra) if args.host == "claude_code" else CodexHost(extra)
        self.venv = self.sandbox / "venv"
        self.env = {**os.environ, "PATH": f"{self.venv / 'bin'}{os.pathsep}{os.environ['PATH']}"}

    def shell(self, command: str, cwd: Optional[Path] = None, check: bool = True, timeout: int = 1800) -> subprocess.CompletedProcess:
        run = subprocess.run(["bash", "-c", command], capture_output=True, text=True, cwd=str(cwd or self.sandbox), timeout=timeout, env=self.env)
        with open(self.out / "shell.log", "a", encoding="utf-8") as log:
            log.write(f"$ {command}\n{run.stdout}{run.stderr}[exit {run.returncode}]\n")
        if check and run.returncode != 0:
            raise RuntimeError(f"{command}: exit {run.returncode}: {run.stderr[-2000:]}")
        return run

    def artifact(self, name: str, text: str) -> str:
        (self.out / "artifacts" / name).write_text(text, encoding="utf-8")
        return f"artifacts/{name}"

    def turn(self, step: str, prompt: str):
        transcript = self.out / "transcripts" / f"{step}.jsonl"
        os.environ["PATH"] = self.env["PATH"]
        return self.host.turn(self.sandbox, prompt, None, transcript), transcript

    # -- steps --
    def step_sandbox(self) -> Dict[str, Any]:
        started = time.monotonic()
        self.sandbox.mkdir(parents=True, exist_ok=True)
        if self.args.package == "released":
            docs_source = self.out / "released-docs"
            if docs_source.exists():
                shutil.rmtree(docs_source)
            docs_source.mkdir()
            self.shell(f"git -C {self.clone} archive v{RELEASED} docs docs.json | tar -x -C {docs_source}", cwd=self.out)
            pages = navigated_pages(docs_source)
            count = snapshot_docs(docs_source / "docs", pages, self.sandbox / "docs")
            self.shell(f"python3 -m venv {self.venv} && {self.venv}/bin/pip install -q 'leeroo-kapso=={RELEASED}'", cwd=self.out, timeout=900)
        else:
            pages = navigated_pages(self.clone)
            count = snapshot_docs(self.clone / "docs", pages, self.sandbox / "docs")
            self.shell(f"python3 -m venv {self.venv} && {self.venv}/bin/pip install -q {self.args.wheel}", cwd=self.out, timeout=900)
        task_view(self.clone / "examples" / "churn-first-build", self.sandbox / "task")
        task_view(self.clone / "examples" / "fraud-no-evaluator", self.sandbox / "task-fraud")
        if (self.sandbox / "harness").exists():
            shutil.rmtree(self.sandbox / "harness")
        shutil.copytree(self.clone / "examples" / "harnesses" / "trading", self.sandbox / "harness", ignore=shutil.ignore_patterns("__pycache__"))
        (self.sandbox / ".env").write_text("", encoding="utf-8")
        seed_env(self.sandbox)
        version = self.shell(f"{self.venv}/bin/python -c 'import kapso; print(kapso.__version__)'", check=False)
        cli = self.shell("command -v kapso && kapso --version", check=False)
        probe, transcript = self.turn("sandbox", "Say only the word ready.")
        init = session_init(plugin_proof_rows(transcript))
        cold = is_cold(init)
        isolated = (cold is True) if self.args.host == "claude_code" else True
        proof = {True: "proved cold from the session's init", False: "NOT cold (the init carried a plugin, server, command or web tool)", None: "not provable from the stream; the CODEX_COLD flags set the isolation"}[cold]
        artifacts = [self.artifact("sandbox.json", json.dumps({"pages": count, "import": version.stdout.strip(), "cli": cli.stdout.strip(), "init": init, "cold": cold}, indent=2))]
        return shell_step("sandbox", version.returncode == 0 and cli.returncode == 0 and isolated, artifacts, (time.monotonic() - started) / 60,
                          [f"{count} public pages; the package {version.stdout.strip()} in the sandbox's venv; isolation: {proof}"])

    def _build(self, name: str, example: str, minutes: int, experiments: int, kill_after: Optional[int] = None) -> Dict[str, Any]:
        started = time.monotonic()
        project = self.sandbox / f"prereq-{name}"
        task_view(self.clone / "examples" / example, project)
        campaign = self.sandbox / name
        if campaign.exists():
            self.shell(f"kapso build --output {campaign} --stop", check=False)
            shutil.rmtree(campaign)
        launch = self.shell(f"kapso build --brief kapso-brief.md --evaluation evaluation --data data --repo repo --output {campaign} --budget-minutes {minutes} --budget-experiments {experiments} --detach", cwd=project, check=False)
        if kill_after:
            wait_for(lambda: (status_of(campaign) or {}).get("phase") not in (None, "setup"), kill_after * 60, every=15)
            pid = (status_of(campaign) or {}).get("pid")
            os.kill(int(pid), signal.SIGKILL)
            done = True
        else:
            done = wait_for(lambda: (status_of(campaign) or {}).get("state") in ("done", "failed"), minutes * 60 + 900, every=30)
        status = status_of(campaign) or {}
        return shell_step(f"prerequisite-{'campaign' if not kill_after else 'killed'}", launch.returncode == 0 and done, [self.artifact(f"{name}-status.json", json.dumps(status, indent=2))],
                          (time.monotonic() - started) / 60, [f"delivered: {(status.get('best') or {}).get('score')}" if not kill_after else f"the writer killed at {kill_after} minutes, phase {status.get('phase')}"], kind="build")

    def _snapshot(self, name: str) -> None:
        snap = self.sandbox / ".snap" / name
        if snap.exists():
            shutil.rmtree(snap)
        snap.parent.mkdir(parents=True, exist_ok=True)
        if (self.sandbox / name).exists():
            shutil.copytree(self.sandbox / name, snap, symlinks=True)

    def _restore(self, name: str) -> None:
        snap = self.sandbox / ".snap" / name
        live = self.sandbox / name
        if not snap.exists():
            return
        if live.exists():
            self.shell(f"kapso build --output {live} --stop", check=False)
            shutil.rmtree(live)
        shutil.copytree(snap, live, symlinks=True)

    def step_prerequisite_campaign(self) -> Dict[str, Any]:
        step = self._build("campaign-prereq", "churn-first-build", PREREQUISITE["minutes"], PREREQUISITE["experiments"])
        self._snapshot("campaign-prereq")
        return step

    def step_prerequisite_killed(self) -> Dict[str, Any]:
        step = self._build("campaign-killed", "churn-first-build", PREREQUISITE["minutes"], PREREQUISITE["experiments"], kill_after=5)
        self._snapshot("campaign-killed")
        return step

    def step_attempt(self, task: Dict[str, Any], surface: str) -> Dict[str, Any]:
        name = f"task{task['number']}-{surface}"
        how = "in Python: write a script in this directory and run it with ./venv/bin/python" if surface == "python" else "on the command line, with the kapso command on PATH"
        prompt = (
            "You are an engineer who has never used Kapso. The package is installed in this directory's venv (./venv/bin/python; the kapso command is on PATH); "
            "its documentation is under ./docs (start at docs/index.mdx and docs/installation.mdx). Read only what is in this directory; use no web. "
            f"The task: {task['goal']}. Do it {how}. When it is done, say in one line what you ran and what came back."
        )
        started = time.time()
        for leftover in (self.sandbox / task["evidence"],) if task["evidence"].startswith("campaign-") else ():
            if leftover.exists():
                self.shell(f"kapso build --output {leftover} --stop", check=False)
                shutil.rmtree(leftover)
        if task.get("restore"):
            self._restore(task["restore"])
        if task.get("clear_learning"):
            for status in self.sandbox.glob("**/learning/status"):
                shutil.rmtree(status, ignore_errors=True)
        turn, transcript = self.turn(name, prompt)
        rows = plugin_proof_rows(transcript)
        found = executions(rows, task["verb"], surface, self.sandbox)
        evidence = evidence_of(task, self.sandbox, self.sandbox / "campaign-prereq")
        metrics = attempt_metrics(found, evidence, started, time.time() if evidence else None)
        scripts = sorted({script for entry in found for script in re.findall(r"\b(\S+\.py)\b", entry["command"]) if (self.sandbox / script).is_file()}) if surface == "python" else []
        metrics["scripts"] = scripts
        metrics["commands"] = [entry["command"] for entry in found] if surface == "cli" else []
        artifacts = [self.artifact(f"{name}-answer.txt", turn.text), self.artifact(f"{name}-executions.json", json.dumps(found, indent=2))]
        step = record_step(name, [turn], bool(evidence), artifacts, kind="attempt")
        step["metrics"] = metrics
        return step

    def step_comprehension(self) -> Dict[str, Any]:
        turn, transcript = self.turn("comprehension", COMPREHENSION)
        facts = {
            "build": "launches a campaign (detached on the command line: a receipt and a status file; in Python it returns a Solution when the campaign ends)",
            "deploy": "ships the delivered branch to a target and proves one call; the deployment's record under the campaign's .kapso/deployments/",
            "learn": "starts the learning crews over the campaign's record, detached, with a status file under the project's learning/status/",
            "resume": "continues a campaign from its checkpoint with --resume (one flag; the attempts kept)",
            "harness": "the domain layer a build loads: pages, skills, delegates, hooks staged into every session; named in the status",
            "evaluator": "the script the campaign protects and runs on every candidate; the metric on its last line; result.json beside it",
            "record": "the campaign directory's .kapso/: solution.json, status.json, the sessions and attempts; Solution.open reads it; kapso trace renders it",
        }
        key = "\n".join(f"- {verb}: {fact}" for verb, fact in facts.items())
        self.artifact("comprehension-facts.json", json.dumps(facts, indent=2))
        answers = f"# The engineer's answers\n\n{turn.text}\n\n# The key (what each call does; the engineer never saw it)\n\n{key}\n"
        artifacts = [self.artifact("comprehension-answers.txt", answers), "artifacts/comprehension-facts.json"]
        return record_step("comprehension", [turn], bool(turn.text.strip()), artifacts, ["the answers and the key handed to the judge (the s1 rubric); --grade reads the comprehension dimension into comprehension_correct"], kind="reading")

    def step_flow_counts(self, record: Dict[str, Any]) -> Dict[str, Any]:
        started = time.monotonic()
        # Per task, so a filename reused across tasks is not conflated; the
        # bar is per flow (one task's path), so report the longest.
        per_task_lines, per_task_commands, detail = {}, {}, {}
        for step in record["steps"]:
            if step.get("kind") != "attempt":
                continue
            metrics = step.get("metrics", {})
            if metrics.get("scripts"):
                per_task_lines[step["name"]] = python_lines(self.sandbox, metrics["scripts"])
            if metrics.get("commands"):
                per_task_commands[step["name"]] = len(metrics["commands"])
            detail[step["name"]] = {"scripts": metrics.get("scripts", []), "commands": metrics.get("commands", [])}
        metrics = {"python_lines": max(per_task_lines.values(), default=0), "cli_commands": max(per_task_commands.values(), default=0)}
        step = shell_step("flow-counts", True, [self.artifact("flow-counts.json", json.dumps({**metrics, "per_task_python_lines": per_task_lines, "per_task_cli_commands": per_task_commands, "detail": detail}, indent=2))], (time.monotonic() - started) / 60,
                          ["python_lines and cli_commands are the longest single task's flow (the bar is per flow); the per-task figures are kept; a script read in its final state is a known limit when a filename is reused within a task"])
        step["metrics"] = metrics
        return step


def plugin_proof_rows(transcript: Path) -> List[dict]:
    return [json.loads(line) for line in transcript.read_text(encoding="utf-8").splitlines() if line.startswith("{")]


def run_metrics(record: Dict[str, Any]) -> Dict[str, Any]:
    """The run-level metrics the suite's bars read."""
    attempts = [step for step in record["steps"] if step.get("kind") == "attempt"]
    errored = [step for step in attempts if step["metrics"]["wrong_calls"]]
    counts = next((step["metrics"] for step in record["steps"] if step["name"] == "flow-counts"), {})
    return {
        "first_try_count": sum(1 for step in attempts if step["metrics"]["first_try"]),
        "errors_led_to_fix": (sum(1 for step in errored if step["metrics"]["error_led_to_fix"]) / len(errored)) if errored else 1.0,
        "wrong_calls_max": max((step["metrics"]["wrong_calls"] for step in attempts), default=0),
        "comprehension_correct": record.get("metrics", {}).get("comprehension_correct"),
        "python_lines": counts.get("python_lines"),
        "cli_commands": counts.get("cli_commands"),
    }


COMPREHENSION_DIMENSION = "names say what the calls do"


def grade(record: Dict[str, Any]) -> Dict[str, Any]:
    """The judge's block into the record: `comprehension_correct` is 1.0
    when the judge resolved the comprehension dimension (the answers named
    every call correctly against the key) to the bar, else 0.0."""
    block = record.get("judge") or {}
    if block.get("failure") or not block.get("passes"):
        return record
    spec = SUITE["tests"]["S1"]["judge"]
    final = judge.resolve(block, spec["dimensions"], spec["bar"]).get(COMPREHENSION_DIMENSION)
    record.setdefault("metrics", {})["comprehension_correct"] = 1.0 if final is not None and final >= spec["bar"] else 0.0
    record["metrics"] = {**record["metrics"], **run_metrics(record)}
    return record


STEP_NAMES = ["sandbox", "prerequisite-campaign", "prerequisite-killed", *[f"task{task['number']}-{surface}" for task in TASKS for surface in ("python", "cli")], "comprehension", "flow-counts"]


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--host", choices=["claude_code", "codex"])
    parser.add_argument("--clone")
    parser.add_argument("--out", required=True)
    parser.add_argument("--wheel", default=None, help="the wheel built from the branch (the branch's package)")
    parser.add_argument("--package", choices=["branch", "released"], default="branch", help="released: the retrospective baseline on the released wheel and the tag's docs")
    parser.add_argument("--sandbox", default=None)
    parser.add_argument("--machine", default=os.uname().nodename)
    parser.add_argument("--advisory", default=None)
    parser.add_argument("--steps", default=None)
    parser.add_argument("--from", dest="start", default=None)
    parser.add_argument("--grade", action="store_true", help="read the judge's block into comprehension_correct (on the development box)")
    args = parser.parse_args(argv)
    record_file = Path(args.out).resolve() / "record.json"
    if args.grade:
        record = grade(json.loads(record_file.read_text()))
        record_file.write_text(json.dumps(record, indent=1) + "\n", encoding="utf-8")
        print(json.dumps(record["metrics"]))
        return 0
    if not args.host or not args.clone:
        parser.error("--host and --clone are required to run the cold engineer (omitted only with --grade)")
    if args.package == "branch" and not args.wheel:
        parser.error("--wheel is the branch's package; --package released needs none")
    driver = S1(args)
    record_file = driver.out / "record.json"
    started = datetime.now(timezone.utc)
    record = json.loads(record_file.read_text()) if record_file.exists() else {
        "test": "S1", "host": args.host, "machine": args.machine, "run_id": f"S1-{args.host}-{started.strftime('%Y%m%dT%H%M%SZ')}", "advisory": args.advisory,
        "package": {"version": RELEASED if args.package == "released" else "branch", "wheel_sha256": hashlib.sha256(Path(args.wheel).read_bytes()).hexdigest() if args.wheel else "-", "released": args.package == "released"},
        "pins": {"wheel_sha256": hashlib.sha256(Path(args.wheel).read_bytes()).hexdigest() if args.wheel else "-", "suite_sha256": hashlib.sha256(plugin_proof.SUITE_PATH.read_bytes()).hexdigest()},
        "user": {"kind": "scripted", "card": None, "interventions": ["the task views: the repositories' own READMEs; the prerequisite campaigns built by the driver; the second one killed at its writer"], "events": [], "pushback": None},
        "started": started.isoformat(timespec="seconds"), "finished": None, "steps": [], "metrics": {}, "notes": [], "transcripts": [],
    }
    selected = args.steps.split(",") if args.steps else list(STEP_NAMES)
    if args.start:
        selected = selected[selected.index(args.start):]
    done = {step["name"] for step in record["steps"]}
    for name in selected:
        if name in done and not args.start:
            continue
        print(f"== {name}", flush=True)
        if name == "sandbox":
            step = driver.step_sandbox()
        elif name == "prerequisite-campaign":
            step = driver.step_prerequisite_campaign()
        elif name == "prerequisite-killed":
            step = driver.step_prerequisite_killed()
        elif name == "comprehension":
            step = driver.step_comprehension()
        elif name == "flow-counts":
            step = driver.step_flow_counts(record)
        else:
            number, surface = int(name[4]), name.split("-", 1)[1]
            step = driver.step_attempt(TASKS[number - 1], surface)
        record["steps"] = [existing for existing in record["steps"] if existing["name"] != name] + [step]
        record["metrics"] = {**record.get("metrics", {}), **run_metrics(record)}
        record["finished"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
        record["transcripts"] = sorted(f"transcripts/{path.name}" for path in (driver.out / "transcripts").glob("*.jsonl"))
        record_file.write_text(json.dumps(record, indent=1) + "\n", encoding="utf-8")
        print(json.dumps({key: value for key, value in step.items() if key not in ("notes",)}), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
