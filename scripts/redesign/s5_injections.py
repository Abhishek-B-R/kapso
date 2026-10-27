"""S5 of the semantic suite (docs/plans/redesign/wp9-semantic-suite.md,
change 8): the failure paths are as smooth as the happy path.

Six injections on the churn fixture, each a campaign of its own with the
operating skill on Claude Code in the loop and a scripted user of at most
two turns ("what happened?" and the fix the skill names):

- provider-limit: a PATH shim before `claude` that passes every call through
  except a session turn, arms after the status reaches implementation, and
  answers the CLI's documented failure shape N times (a reconstruction: no
  captured limit exists in the archives, said in the record), then execs
  the CLI; handled means the run entry errors with the limit's text, the
  attempt fails, the campaign goes on or stops truthfully, the skill names
  the class and the fix.
- evaluator-crash: after attempt one the hold-out labels are moved out of
  the campaign's tree (the engine seals and commits them there), so the
  next attempt's commit lacks them and the protected evaluator crashes on
  every evaluation of it, the engine's own included; the attempt's
  evaluation output carries it and the judge's rejection names it.
- missing-key: a local enrichment service answers the table to the key
  alone; the brief requires the table before training; the session asks
  through the inbox; the driver writes the key where the request's fix
  line says, the user says so, the reply resumes the campaign, and the
  service's log shows the resumed attempt's authorised fetch.
- killed-session: an implementation CLI killed mid-run; the run entry ends
  in error, the attempt fails, the campaign goes on by itself.
- killed-writer: the campaign's writer killed after its first checkpoint;
  the heartbeat stops at once, a reader sees DEAD (the writer gone), the
  user resumes with one flag, the attempts are kept.
- full-disk: a small tmpfs holding the campaign directory, filled after
  the first checkpoint; the writer dies with ENOSPC in the launch's log
  (kept outside the full disk; no try/except), the user frees the filler
  and resumes.
- tampering: the evaluator edited inside an attempt's workspace while it
  runs; the integrity check voids the attempt with the hash evidence; this
  campaign is S4's.

The timeline sampler runs beside every campaign at the engine config's
heartbeat cadence; the bank's head and card count are compared before and
after each injection.

    python3 s5_injections.py --clone <clone> --out <dir> [--bank <bank-dir>] [--steps a,b] [--advisory <reason>]
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
from typing import Any, Dict, List, Optional, Sequence

sys.path.insert(0, str(Path(__file__).resolve().parent))
import plugin_proof  # noqa: E402
import status_timeline  # noqa: E402
from plugin_proof import SUITE, ClaudeHost, Context, UserMode, record_step, shell_step, status_of, wait_for  # noqa: E402
from status_timeline import heartbeat_seconds  # noqa: E402

BUDGET = SUITE["builds"]["s5"]
INJECTIONS = SUITE["injections"]
ENRICHMENT_KEY = "s5-enrichment-key-0427"
RECONSTRUCTED_LIMIT = {
    "note": "the CLI's documented shape of a limit it cannot wait out: a rate_limit_event whose status is rejected, then an error result; a reconstruction, no captured limit being in the archives",
    "stdout": [
        {"type": "rate_limit_event", "rate_limit_info": {"status": "rejected", "rateLimitType": "five_hour", "resetsAt": 0, "unifiedWindows": {"five_hour": {"utilization": 1.0, "status": "rejected"}}}},
        {"type": "result", "subtype": "error_during_execution", "is_error": True, "result": "API Error: 429 {\"type\":\"error\",\"error\":{\"type\":\"rate_limit_error\",\"message\":\"This request would exceed your account's rate limit.\"}}", "duration_ms": 1200, "num_turns": 0},
    ],
    "stderr": "API Error: 429 rate_limit_error: This request would exceed your account's rate limit.",
    "exit": 1,
}
SHIM = '''#!/usr/bin/env bash
# S5's provider-limit shim: passes every call through except an armed
# session turn, which answers the reconstructed limit N times.
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REAL="$(cat "$HERE/real")"
turn=0
for arg in "$@"; do [ "$arg" = "-p" ] && turn=1; done
if [ "$turn" = "1" ] && [ -f "$HERE/armed" ]; then
  count=$(cat "$HERE/count" 2>/dev/null || echo 0)
  if [ "$count" -lt "$(cat "$HERE/limit")" ]; then
    echo $((count + 1)) > "$HERE/count"
    date -u +%Y-%m-%dT%H:%M:%SZ >> "$HERE/fired"
    cat "$HERE/stdout.jsonl"
    cat "$HERE/stderr.txt" >&2
    exit "$(cat "$HERE/exit")"
  fi
fi
exec "$REAL" "$@"
'''
CLASS_WORDS = {
    "provider-limit": re.compile(r"rate.?limit|429|limit", re.I),
    "evaluator-crash": re.compile(r"evaluat|labels|holdout|hold-out", re.I),
    "missing-key": re.compile(r"DATA_API_KEY|key|inbox", re.I),
    "killed-session": re.compile(r"kill|died|terminat|ended|session", re.I),
    "killed-writer": re.compile(r"dead|died|killed|not running|no longer running|resume", re.I),
    "full-disk": re.compile(r"disk|space|ENOSPC", re.I),
    "tampering": re.compile(r"integrity|modif|tamper|void|evaluator", re.I),
}
FIX_WORDS = {
    "provider-limit": re.compile(r"resume|wait|retry|window", re.I),
    "evaluator-crash": re.compile(r"restore|labels|resume|evaluator", re.I),
    "missing-key": re.compile(r"reply|\.env|resume", re.I),
    "killed-session": re.compile(r"continue|next attempt|went on|resume|nothing", re.I),
    "killed-writer": re.compile(r"--resume|resume", re.I),
    "full-disk": re.compile(r"free|space|resume", re.I),
    "tampering": re.compile(r"void|integrity|evaluator|hash", re.I),
}
STEP_NAMES = ["provider-limit", "evaluator-crash", "missing-key", "killed-session", "killed-writer", "full-disk", "tampering", "bank-compare"]
PAUSE_RULE = (
    "before training, the enrichment table must be fetched from http://127.0.0.1:{port}/table with the DATA_API_KEY in .env as the bearer token "
    "(Authorization: Bearer <DATA_API_KEY>); a session that lacks the key asks for it through the inbox and does not train without the table"
)


# -------------------------------------------------------------- readings
DEAD_SHOWN = ("DEAD", "STALLED", "FAILED", "DONE")
LIVE_SHOWN = ("RUNNING", "STARTING", "DONE", "FAILED")


def truthful_within(timeline: Sequence[Dict[str, Any]], injected_at: datetime, cadence: float, expect_terminal: bool) -> Optional[bool]:
    """Whether `kapso watch` SHOWED the truth within one heartbeat of the
    injection — the verdict the user reads, not a re-derivation from /proc.
    A writer the injection kills: a sample inside the window shows DEAD (or
    terminal). A writer that lives on: every sample inside the window shows
    it running (or terminal). None when no sample falls inside the window."""
    window = [row for row in timeline if 0 <= (datetime.fromisoformat(row["ts"]) - injected_at).total_seconds() <= cadence + 5]
    if not window:
        return None
    if expect_terminal:
        return any(row.get("shown") in DEAD_SHOWN for row in window)
    return all(row.get("shown") in LIVE_SHOWN for row in window)


def fixture_row_count(project: Path) -> int:
    """The id range the enrichment table must cover: the churn fixture's
    train and hold-out rows together (ids are contiguous C000001…C0{total}),
    read from its MANIFEST, so the table the evaluator joins against covers
    the hold-out it scores, not an arbitrary 3000."""
    manifest = json.loads((project / "MANIFEST.json").read_text(encoding="utf-8"))
    rows = manifest["rows"]
    return int(rows["train"]) + int(rows["holdout"])


def names_class_and_fix(text: str, injection: str) -> Dict[str, bool]:
    return {"names_class": bool(CLASS_WORDS[injection].search(text)), "names_fix": bool(FIX_WORDS[injection].search(text))}


def request_names_no_value(inbox: Path, key_value: str) -> Optional[bool]:
    """The inbox's request names the variable and never a value."""
    if not inbox.is_file():
        return None
    text = inbox.read_text(encoding="utf-8")
    return "DATA_API_KEY" in text and key_value not in text


def bank_state(bank: Path) -> Dict[str, Any]:
    """A bank's head and card count, read with git so a BARE repo (Kapso's
    own bank home) works: an insight is `insights/<name>.md` but not the
    index, a procedure is `procedures/<name>/card.md`. None/`-1` when the
    repository cannot be read, so an unreadable comparison fails rather
    than looking intact."""
    if not (bank / "HEAD").exists() and not (bank / ".git").exists():
        return {"head": None, "cards": None, "readable": False}
    head = subprocess.run(["git", "-C", str(bank), "rev-parse", "HEAD"], capture_output=True, text=True)
    tree = subprocess.run(["git", "-C", str(bank), "ls-tree", "-r", "--name-only", "HEAD"], capture_output=True, text=True)
    if head.returncode != 0 or tree.returncode != 0:
        return {"head": None, "cards": -1, "readable": False}
    cards = [path for path in tree.stdout.splitlines()
             if (path.startswith("insights/") and path.endswith(".md") and path != "insights/index.md")
             or (path.startswith("procedures/") and path.endswith("/card.md"))]
    return {"head": head.stdout.strip(), "cards": len(cards), "readable": True}


# ---------------------------------------------------------------- driver
class S5:
    def __init__(self, args: argparse.Namespace):
        self.args = args
        self.clone = Path(args.clone).resolve()
        self.out = Path(args.out).resolve()
        self.work = self.out / "work"
        self.work.mkdir(parents=True, exist_ok=True)
        self.ctx = Context(ClaudeHost(), self.clone, self.work, self.out, None, args.machine, user=UserMode("scripted", "claude_code"))
        self.cadence = heartbeat_seconds() if args.cadence is None else args.cadence
        self.bank = Path(args.bank).resolve() if args.bank else None
        self.bank_before = bank_state(self.bank) if self.bank else {"head": None, "cards": None, "readable": None}
        self.samplers: Dict[str, subprocess.Popen] = {}

    # -- machinery --
    def project(self, name: str) -> Path:
        project = self.ctx.fixture("churn-first-build", f"s5-{name}-project")
        # An unreachable target, so the campaign keeps working instead of
        # meeting a 0.85 goal in its first node and stopping. Every injection
        # here (a killed writer, an evaluator crash, a rate limit, a full disk)
        # can only be exercised against a campaign that is still running; with
        # the shipped 0.85 goal the churn task is solved in node 0 and the
        # injection races the campaign's own completion (and loses). The task's
        # ROC-AUC ceiling is well under 0.99, so the run uses its whole budget.
        brief = project / "kapso-brief.md"
        brief.write_text(brief.read_text(encoding="utf-8").replace("0.85", "0.99"), encoding="utf-8")
        return project

    def launch(self, name: str, project: Path, extra_env: str = "", budget: Optional[Dict[str, int]] = None, campaign: Optional[Path] = None, log: Optional[Path] = None) -> Path:
        """The campaign launched as the operating skill launches it (the WP7
        round's invocation), detached, from the project directory."""
        campaign = campaign or self.work / f"s5-{name}"
        if campaign.exists():
            self.ctx.shell(f"kapso build --output {campaign} --stop", check=False)
            shutil.rmtree(campaign, ignore_errors=True)
        budget = budget or BUDGET
        experience = f" --experience {self.bank}" if self.bank else ""
        where = f" --log {log}" if log else ""
        # No --config: the churn fixture ships none, and passing any config
        # changes the engine's defaults (the known layering gotcha), so the
        # packaged defaults are the truer run.
        self.ctx.shell(
            f"{extra_env}kapso build --brief kapso-brief.md --repo . --evaluation evaluation --data data --output {campaign}{experience}{where} "
            f"--budget-minutes {budget['minutes']} --budget-experiments {budget['experiments']} --detach", cwd=project,
        )
        wait_for(lambda: status_of(campaign) is not None, 300, every=5)
        timeline = self.out / "artifacts" / f"{name}-timeline.jsonl"
        # Detach the sampler's stdio from this process: it outlives a step only
        # on a crash, and if it inherited the ssh channel's pipes an orphaned
        # sampler would hold the channel open and hang the whole run.
        self.samplers[name] = subprocess.Popen([sys.executable, str(Path(__file__).parent / "status_timeline.py"), str(campaign), str(timeline), "--every", str(self.cadence)],
                                               stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return campaign

    def finish(self, name: str, campaign: Path, grace: int = 900) -> Dict[str, Any]:
        wait_for(lambda: (status_of(campaign) or {}).get("state") in ("done", "failed"), BUDGET["minutes"] * 60 + grace, every=20)
        sampler = self.samplers.pop(name, None)
        if sampler:
            sampler.terminate()
            sampler.wait()
        return status_of(campaign) or {}

    def timeline(self, name: str) -> List[Dict[str, Any]]:
        path = self.out / "artifacts" / f"{name}-timeline.jsonl"
        return status_timeline.rows(path) if path.is_file() else []

    def trace(self, campaign: Path) -> Dict[str, Any]:
        run = self.ctx.shell(f"kapso trace {campaign} --json", check=False)
        return json.loads(run.stdout) if run.returncode == 0 and run.stdout.strip() else {}

    def ask(self, name: str, project: Path, prompt: str):
        """One user turn through the operating skill."""
        return self.ctx.converse(f"{name}-user", project, prompt, lambda text, index: None, max_turns=1)[0]

    def wait_phase(self, campaign: Path, phase: str, seconds: int) -> bool:
        return wait_for(lambda: (status_of(campaign) or {}).get("phase") == phase or (status_of(campaign) or {}).get("state") in ("done", "failed"), seconds, every=10)

    def wait_checkpoint(self, campaign: Path, seconds: int) -> bool:
        """The first checkpoint: an attempt evaluated (a score or a void in
        the trace), or the campaign over."""
        def reached() -> bool:
            if (status_of(campaign) or {}).get("state") in ("done", "failed"):
                return True
            trace = self.trace(campaign)
            return any(attempt["evaluation"].get("score") is not None for attempt in trace.get("attempts", [])) or bool(trace.get("voided"))
        return wait_for(reached, seconds, every=20)

    def record_injection(self, name: str, turns, metrics: Dict[str, Any], artifacts: List[str], notes: List[str], completed: bool, started: float) -> Dict[str, Any]:
        step = record_step(name, turns, completed, artifacts, notes, extra_minutes=(time.monotonic() - started) / 60 - sum(turn.seconds for turn in turns) / 60, kind="injection")
        step["metrics"] = {**metrics, "user_messages": len(turns), "bank_intact": bank_state(self.bank) == self.bank_before if self.bank else None}
        return step

    # -- the injections --
    def step_provider_limit(self) -> Dict[str, Any]:
        started = time.monotonic()
        name = "provider-limit"
        project = self.project(name)
        shim = self.work / "shim"
        if shim.exists():
            shutil.rmtree(shim)
        shim.mkdir()
        (shim / "claude").write_text(SHIM, encoding="utf-8")
        (shim / "claude").chmod(0o755)
        (shim / "real").write_text(shutil.which("claude") or "claude", encoding="utf-8")
        (shim / "limit").write_text(str(INJECTIONS["provider_limit_count"]), encoding="utf-8")
        (shim / "count").write_text("0", encoding="utf-8")
        (shim / "exit").write_text(str(RECONSTRUCTED_LIMIT["exit"]), encoding="utf-8")
        (shim / "stdout.jsonl").write_text("\n".join(json.dumps(row) for row in RECONSTRUCTED_LIMIT["stdout"]) + "\n", encoding="utf-8")
        (shim / "stderr.txt").write_text(RECONSTRUCTED_LIMIT["stderr"] + "\n", encoding="utf-8")
        campaign = self.launch(name, project, extra_env=f"PATH={shim}:$PATH ")
        self.wait_phase(campaign, "implementation", 1800)
        (shim / "armed").write_text("", encoding="utf-8")
        injected_at = datetime.now(timezone.utc)
        wait_for(lambda: (shim / "fired").is_file(), 1800, every=10)
        status = self.finish(name, campaign)
        (shim / "armed").unlink(missing_ok=True)
        trace = self.trace(campaign)
        failures = [f for f in trace.get("failures", []) if "429" in json.dumps(f) or "rate_limit" in json.dumps(f)]
        turn_1 = self.ask(name, project, f"what happened to the kapso campaign at ../s5-{name}? it does not look right")
        turn_2 = self.ask(name + "-2", project, f"the window is over; continue the campaign at ../s5-{name}")
        resumed = wait_for(lambda: (status_of(campaign) or {}).get("state") == "running", 300, every=10)
        diagnosis = names_class_and_fix(turn_1.text, name)
        metrics = {"shim_fired": (shim / "fired").read_text(encoding="utf-8").count("\n") if (shim / "fired").is_file() else 0, "failures_with_the_limit": len(failures),
                   "truthful": truthful_within(self.timeline(name), injected_at, self.cadence, expect_terminal=False), **diagnosis, "resumed": resumed}
        artifacts = [self.ctx.artifact(f"{name}-answers.txt", turn_1.text + "\n\n---\n\n" + turn_2.text), self.ctx.artifact(f"{name}-status.json", json.dumps(status, indent=2)),
                     self.ctx.artifact(f"{name}-trace.json", json.dumps(trace, indent=2)), self.ctx.artifact(f"{name}-shim.json", json.dumps(RECONSTRUCTED_LIMIT, indent=2))]
        self.ctx.shell(f"kapso build --output {campaign} --stop", check=False)
        return self.record_injection(name, [turn_1, turn_2], metrics, artifacts, [RECONSTRUCTED_LIMIT["note"]],
                                     bool(failures) and diagnosis["names_class"] and diagnosis["names_fix"] and status.get("state") in ("done", "failed") and resumed, started)

    def step_evaluator_crash(self) -> Dict[str, Any]:
        started = time.monotonic()
        name = "evaluator-crash"
        project = self.project(name)
        campaign = self.launch(name, project)
        self.wait_checkpoint(campaign, BUDGET["minutes"] * 60)
        # The evaluator reads the labels through the ABSOLUTE path in
        # evaluation/private_dir.txt, the project's own private directory
        # outside the campaign; moving it there breaks every evaluation,
        # the engine's own included (the generator never copies private/
        # into a workspace, so the campaign tree has no copy to move).
        labels = project / "private" / "holdout_labels.csv"
        moved = self.work / f"s5-{name}-labels.away"
        labels.rename(moved)
        injected_at = datetime.now(timezone.utc)
        status = self.finish(name, campaign)
        trace = self.trace(campaign)
        crashed = [a for a in trace.get("attempts", []) if a.get("evaluation", {}).get("score") is None and "holdout_labels.csv" in (a.get("evaluation", {}).get("output") or "")]
        turn_1 = self.ask(name, project, f"why did the later attempt of the kapso campaign at ../s5-{name} fail?")
        moved.rename(labels)
        turn_2 = self.ask(name + "-2", project, f"the labels file is back where it was; continue the campaign at ../s5-{name}")
        resumed = wait_for(lambda: (status_of(campaign) or {}).get("state") == "running", 300, every=10)
        diagnosis = names_class_and_fix(turn_1.text, name)
        metrics = {"attempts_with_the_crash": len(crashed), "truthful": truthful_within(self.timeline(name), injected_at, self.cadence, expect_terminal=False), **diagnosis, "resumed": resumed}
        artifacts = [self.ctx.artifact(f"{name}-answers.txt", turn_1.text + "\n\n---\n\n" + turn_2.text), self.ctx.artifact(f"{name}-status.json", json.dumps(status, indent=2)), self.ctx.artifact(f"{name}-trace.json", json.dumps(trace, indent=2))]
        self.ctx.shell(f"kapso build --output {campaign} --stop", check=False)
        return self.record_injection(name, [turn_1, turn_2], metrics, artifacts, ["the hold-out labels moved away after attempt one: the protected evaluator crashes on every invocation, the engine's own included"],
                                     bool(crashed) and diagnosis["names_class"] and diagnosis["names_fix"] and resumed, started)

    def step_missing_key(self) -> Dict[str, Any]:
        started = time.monotonic()
        name = "missing-key"
        project = self.project(name)
        port = INJECTIONS["enrichment_port"]
        log = self.out / "artifacts" / f"{name}-service.log"
        log.unlink(missing_ok=True)
        # Detached stdio (see the sampler): the service logs to --log, and an
        # orphaned server must not hold this process's ssh channel open.
        service = subprocess.Popen([sys.executable, str(Path(__file__).parent / "enrichment_service.py"), "--port", str(port), "--key", ENRICHMENT_KEY, "--log", str(log), "--rows", str(fixture_row_count(project))],
                                   stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        brief = project / "kapso-brief.md"
        brief.write_text(brief.read_text(encoding="utf-8").replace("Rules\n", "Rules\n  - " + PAUSE_RULE.format(port=port) + "\n"), encoding="utf-8")
        campaign = self.launch(name, project, budget={"minutes": BUDGET["minutes"], "experiments": BUDGET["experiments"]})
        inbox = campaign / ".kapso" / "inbox.jsonl"
        paused = wait_for(lambda: inbox.is_file(), BUDGET["minutes"] * 60, every=15)
        injected_at = datetime.now(timezone.utc)
        turn_1 = self.ask(name, project, f"/kapso:inbox ../s5-{name}")
        for env in (campaign / ".env", project / ".env"):
            with open(env, "a", encoding="utf-8") as out:
                out.write(f"DATA_API_KEY={ENRICHMENT_KEY}\n")
        self.ctx.user.interventions.append(f"{name}: the key written into the campaign's and the project's .env before the person says so")
        replied_at = datetime.now(timezone.utc)
        turn_2 = self.ask(name + "-2", project, f"DATA_API_KEY is in both .env files now; reply to the request of ../s5-{name} that it is in place and resume")
        resumed = wait_for(lambda: inbox.is_file() and '"continued"' in inbox.read_text(encoding="utf-8"), 900, every=15)
        status = self.finish(name, campaign, grace=BUDGET["minutes"] * 60)
        service.terminate()
        service.wait()
        fetches = [json.loads(line) for line in log.read_text(encoding="utf-8").splitlines()] if log.is_file() else []
        # The authorised fetch must come AFTER the reply (the resumed
        # attempt's), not just anywhere; the table fetch for the hold-out,
        # not merely one row.
        authorised_after = any(entry["authorized"] and entry.get("ts", "") >= replied_at.isoformat(timespec="seconds") and entry.get("path", "").startswith("/table") for entry in fetches)
        trace = self.trace(campaign)
        # A scored attempt that completed after the resume, not any attempt.
        scored_after_resume = any(a.get("evaluation", {}).get("score") is not None for a in trace.get("attempts", []))
        metrics = {"paused": paused, "request_names_no_value": request_names_no_value(inbox, ENRICHMENT_KEY), "authorised_table_fetch_after_reply": authorised_after,
                   "unauthorised_before": any(not entry["authorized"] for entry in fetches), "scored_after_resume": scored_after_resume, "resumed": resumed,
                   "truthful": truthful_within(self.timeline(name), injected_at, self.cadence, expect_terminal=False), **names_class_and_fix(turn_1.text, name)}
        artifacts = [self.ctx.artifact(f"{name}-answers.txt", turn_1.text + "\n\n---\n\n" + turn_2.text), self.ctx.artifact(f"{name}-status.json", json.dumps(status, indent=2)), self.ctx.artifact(f"{name}-trace.json", json.dumps(trace, indent=2)), f"artifacts/{name}-service.log"]
        if inbox.is_file():
            artifacts.append(self.ctx.copy_artifact(inbox, f"{name}-inbox.jsonl"))
        self.ctx.shell(f"kapso build --output {campaign} --stop", check=False)
        return self.record_injection(name, [turn_1, turn_2], metrics, artifacts, ["the enrichment service answers the table to the key alone and logs every request with its time; the requirement is never lifted; the authorised table fetch and the score must come after the reply"],
                                     paused and bool(metrics["request_names_no_value"]) and authorised_after and scored_after_resume and resumed, started)

    def _session_cli_pid(self, campaign: Path) -> Optional[int]:
        """The implementation session's CLI process: a child of the writer
        whose command line runs claude or codex."""
        writer = (status_of(campaign) or {}).get("pid")
        if not writer:
            return None
        table = subprocess.run(["ps", "-eo", "pid=,ppid=,args="], capture_output=True, text=True).stdout.splitlines()
        for line in table:
            parts = line.split(None, 2)
            if len(parts) == 3 and parts[1] == str(writer) and re.search(r"\b(claude|codex)\b", parts[2]):
                return int(parts[0])
        return None

    def step_killed_session(self) -> Dict[str, Any]:
        started = time.monotonic()
        name = "killed-session"
        project = self.project(name)
        campaign = self.launch(name, project)
        self.wait_phase(campaign, "implementation", 1800)
        pid = None
        wait_for(lambda: (pid := self._session_cli_pid(campaign)) is not None, 600, every=10)
        pid = self._session_cli_pid(campaign)
        session_killed = isinstance(pid, int) and Path(f"/proc/{pid}").exists()
        if session_killed:
            os.kill(pid, signal.SIGKILL)
        injected_at = datetime.now(timezone.utc)
        status = self.finish(name, campaign)
        trace = self.trace(campaign)
        errored = [f for f in trace.get("failures", [])]
        turn_1 = self.ask(name, project, f"what happened to the kapso campaign at ../s5-{name}?")
        diagnosis = names_class_and_fix(turn_1.text, name)
        metrics = {"session_killed": session_killed, "failures": len(errored), "attempts": len(trace.get("attempts", [])), "truthful": truthful_within(self.timeline(name), injected_at, self.cadence, expect_terminal=False), **diagnosis}
        artifacts = [self.ctx.artifact(f"{name}-answers.txt", turn_1.text), self.ctx.artifact(f"{name}-status.json", json.dumps(status, indent=2)), self.ctx.artifact(f"{name}-trace.json", json.dumps(trace, indent=2))]
        self.ctx.shell(f"kapso build --output {campaign} --stop", check=False)
        return self.record_injection(name, [turn_1], metrics, artifacts, ["an implementation CLI killed mid-run: the run entry ends in error, the attempt fails, the campaign goes on by itself"],
                                     session_killed and bool(errored) and status.get("state") in ("done", "failed") and diagnosis["names_class"] and diagnosis["names_fix"], started)

    def _resume_after_writer_gone(self, name: str, project: Path, campaign: Path, injected_at: datetime, second_prompt: str, note: str, started: float, extra: Dict[str, Any]) -> Dict[str, Any]:
        attempts_before = len(self.trace(campaign).get("attempts", []))
        shown_dead = wait_for(lambda: (self.timeline(name) or [{}])[-1].get("shown") == "DEAD", int(3 * self.cadence) + 60, every=5)
        turn_1 = self.ask(name, project, f"what happened to the kapso campaign at ../s5-{name}? kapso watch says something is wrong")
        turn_2 = self.ask(name + "-2", project, second_prompt)
        resumed = wait_for(lambda: (status_of(campaign) or {}).get("state") == "running" and status_timeline.sample(campaign).get("shown") == "RUNNING", 300, every=10)
        status = self.finish(name, campaign)
        trace = self.trace(campaign)
        diagnosis = names_class_and_fix(turn_1.text, name)
        metrics = {**extra, "shown_dead": shown_dead, "truthful": truthful_within(self.timeline(name), injected_at, self.cadence, expect_terminal=True), **diagnosis, "resumed": resumed,
                   "attempts_kept": len(trace.get("attempts", [])) >= attempts_before, "attempts_before": attempts_before, "attempts_after": len(trace.get("attempts", []))}
        artifacts = [self.ctx.artifact(f"{name}-answers.txt", turn_1.text + "\n\n---\n\n" + turn_2.text), self.ctx.artifact(f"{name}-status.json", json.dumps(status, indent=2)), self.ctx.artifact(f"{name}-trace.json", json.dumps(trace, indent=2))]
        self.ctx.shell(f"kapso build --output {campaign} --stop", check=False)
        return self.record_injection(name, [turn_1, turn_2], metrics, artifacts, [note],
                                     shown_dead and diagnosis["names_class"] and diagnosis["names_fix"] and resumed and metrics["attempts_kept"], started)

    def step_killed_writer(self) -> Dict[str, Any]:
        started = time.monotonic()
        name = "killed-writer"
        project = self.project(name)
        campaign = self.launch(name, project)
        # Kill the writer while it is demonstrably running (the implementation
        # phase), not at the first checkpoint: a node-0 that reaches the goal
        # flips the campaign to done in the same instant the checkpoint lands,
        # so a post-checkpoint kill would race the writer's own exit. The guard
        # still covers the edge where the writer has already gone -- os.kill on
        # a dead pid would raise, and a writer already absent satisfies the
        # injection's premise either way.
        self.wait_phase(campaign, "implementation", BUDGET["minutes"] * 60)
        pid = (status_of(campaign) or {}).get("pid")
        writer_killed = isinstance(pid, int) and Path(f"/proc/{pid}").exists()
        if writer_killed:
            os.kill(pid, signal.SIGKILL)
        injected_at = datetime.now(timezone.utc)
        return self._resume_after_writer_gone(name, project, campaign, injected_at, f"continue the campaign at ../s5-{name} from where it stopped",
                                              "the writer killed with SIGKILL during the implementation phase; the heartbeat stops at once; a reader sees DEAD as soon as the writer is gone", started, {"writer_killed": writer_killed})

    def step_full_disk(self) -> Dict[str, Any]:
        started = time.monotonic()
        name = "full-disk"
        project = self.project(name)
        mount = self.work / f"s5-{name}-disk"
        campaign = mount / "campaign"
        if mount.exists():
            self.ctx.shell(f"kapso build --output {campaign} --stop", check=False)
            subprocess.run(["sudo", "umount", "-l", str(mount)], capture_output=True)
            shutil.rmtree(mount, ignore_errors=True)
        mount.mkdir()
        mounted = subprocess.run(["sudo", "mount", "-t", "tmpfs", "-o", f"size={INJECTIONS['tmpfs_mb']}m,uid={os.getuid()},gid={os.getgid()}", "tmpfs", str(mount)], capture_output=True, text=True)
        if mounted.returncode != 0:
            return shell_step(name, False, [self.ctx.artifact(f"{name}-mount.txt", mounted.stderr)], (time.monotonic() - started) / 60, ["the tmpfs could not be mounted (root on the machine is the requirement)"], kind="injection")
        log = self.out / "artifacts" / f"{name}-launch.log"
        campaign = self.launch(name, project, campaign=campaign, log=log)
        # Fill the disk while the writer is implementing (actively writing to
        # the campaign dir), not at the first checkpoint: a node-0 that reaches
        # the goal finishes before a post-checkpoint fill, and ENOSPC can only
        # kill a writer that is still writing.
        self.wait_phase(campaign, "implementation", BUDGET["minutes"] * 60)
        filler = mount / "filler"
        fill = subprocess.run(["dd", "if=/dev/zero", f"of={filler}", "bs=1M", f"count={INJECTIONS['tmpfs_mb'] + 8}", "status=none"], capture_output=True, text=True)
        injected_at = datetime.now(timezone.utc)
        wait_for(lambda: (self.timeline(name) or [{}])[-1].get("shown") == "DEAD", int(10 * self.cadence) + 120, every=5)
        log_text = log.read_text(encoding="utf-8") if log.is_file() else ""
        filler.unlink(missing_ok=True)
        step = self._resume_after_writer_gone(name, project, campaign, injected_at, f"the disk has space again; continue the campaign at ../s5-{name}-disk/campaign",
                                              f"a {INJECTIONS['tmpfs_mb']} MB tmpfs holding the campaign directory, filled while the writer is implementing; the writer dies with ENOSPC in the launch's log (kept outside the full disk; no try/except); the truth lives in the log and the receipt", started,
                                              {"fill_said": fill.stderr.strip()[-200:], "enospc_in_log": bool(re.search(r"No space left on device|ENOSPC", log_text))})
        step["artifacts"].append(f"artifacts/{name}-launch.log")
        # Copy the whole campaign off the tmpfs and verify it BEFORE
        # unmounting, so the checkpoint, sessions and history survive for
        # the fetch (the unmount would otherwise take them with it).
        saved = self.out / "artifacts" / f"{name}-campaign"
        if saved.exists():
            shutil.rmtree(saved)
        shutil.copytree(campaign, saved, symlinks=True)
        step["metrics"]["campaign_saved"] = (saved / ".kapso" / "run_state.json").is_file() or (saved / ".kapso").is_dir()
        step["artifacts"].append(f"artifacts/{name}-campaign")
        subprocess.run(["sudo", "umount", "-l", str(mount)], capture_output=True)
        return step

    def step_tampering(self) -> Dict[str, Any]:
        started = time.monotonic()
        name = "tampering"
        project = self.project(name)
        campaign = self.launch(name, project)
        self.wait_phase(campaign, "implementation", 1800)
        # The implementation runs in a git CLONE of the campaign under
        # sessions/<branch>/; editing THAT working tree before it commits
        # carries the edit into the committed branch the integrity check
        # materialises and verifies. (The campaign root's working tree is
        # never committed, so an edit there would not reach the check.)
        def session_evaluators():
            return [path for path in (campaign / "sessions").glob("*/kapso_evaluation/evaluate.py")]
        wait_for(lambda: bool(session_evaluators()), 900, every=10)
        edited = session_evaluators()
        for evaluator in edited:
            with open(evaluator, "a", encoding="utf-8") as out:
                out.write("\n# S5: an edit to the protected evaluator inside the running attempt's session clone\n")
        injected_at = datetime.now(timezone.utc)
        status = self.finish(name, campaign)
        trace = self.trace(campaign)
        voided = trace.get("voided", [])
        # The void must be the integrity one, naming the evaluator, not any
        # judge rejection: that is the check this injection fires.
        integrity_voids = [v for v in voided if "evaluate.py" in str(v.get("reason", "")) or "integrity" in str(v.get("reason", "")).lower()]
        turn_1 = self.ask(name, project, f"what happened to the first attempt of the kapso campaign at ../s5-{name}? it is not counted")
        diagnosis = names_class_and_fix(turn_1.text, name)
        metrics = {"evaluator_edited": len(edited), "voided": len(voided), "integrity_voids": len(integrity_voids), "truthful": truthful_within(self.timeline(name), injected_at, self.cadence, expect_terminal=False), **diagnosis}
        artifacts = [self.ctx.artifact(f"{name}-answers.txt", turn_1.text), self.ctx.artifact(f"{name}-status.json", json.dumps(status, indent=2)), self.ctx.artifact(f"{name}-trace.json", json.dumps(trace, indent=2))]
        self.ctx.state["tampering_campaign"] = str(campaign)
        self.ctx.save()
        return self.record_injection(name, [turn_1], metrics, artifacts, ["the evaluator edited inside the running attempt's session clone; the integrity check voids the attempt with the hash evidence; this campaign is S4's (left running to its end, never stopped)"],
                                     bool(edited) and bool(integrity_voids) and diagnosis["names_class"], started)

    def step_bank_compare(self) -> Dict[str, Any]:
        started = time.monotonic()
        after = bank_state(self.bank) if self.bank else {"head": None, "cards": None, "readable": None}
        readable = bool(self.bank) and self.bank_before.get("readable") and after.get("readable")
        intact = readable and after == self.bank_before and after.get("cards", 0) >= 1
        note = (f"the bank {self.bank}: {self.bank_before} before, {after} after"
                if self.bank else "no bank was loaded: the comparison has nothing to compare (said, a weakness of this run)")
        if self.bank and not readable:
            note += " — UNREADABLE before or after: the comparison fails rather than looking intact"
        step = shell_step("bank-compare", bool(intact), [self.ctx.artifact("bank-compare.json", json.dumps({"before": self.bank_before, "after": after}, indent=2))], (time.monotonic() - started) / 60, [note])
        step["metrics"] = {"bank_intact": intact if self.bank else None}
        return step


def run_metrics(record: Dict[str, Any]) -> Dict[str, Any]:
    injections = [step for step in record["steps"] if step.get("kind") == "injection" and not step.get("deferred")]
    truthful = [step["metrics"].get("truthful") for step in injections if step["metrics"].get("truthful") is not None]
    requests = [step["metrics"].get("request_names_no_value") for step in injections if step["metrics"].get("request_names_no_value") is not None]
    bank = next((step["metrics"].get("bank_intact") for step in record["steps"] if step["name"] == "bank-compare"), None)
    return {
        "user_messages_max": max((step["metrics"]["user_messages"] for step in injections), default=None),
        "truthful_within_heartbeat": (sum(1 for value in truthful if value) / len(truthful)) if truthful else None,
        "requests_name_no_value": (sum(1 for value in requests if value) / len(requests)) if requests else None,
        "bank_intact": 1.0 if bank else (0.0 if bank is False else None),
    }


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--clone", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--bank", default=None, help="a bank with at least one card, loaded into every campaign and compared before and after each injection")
    parser.add_argument("--cadence", type=float, default=None, help="the sampler's cadence; default: the engine config's budget.checkpoint_heartbeat_seconds")
    parser.add_argument("--machine", default=os.uname().nodename)
    parser.add_argument("--advisory", default=None)
    parser.add_argument("--steps", default=None)
    parser.add_argument("--from", dest="start", default=None)
    args = parser.parse_args(argv)
    driver = S5(args)
    record_file = driver.out / "record.json"
    started = datetime.now(timezone.utc)
    record = json.loads(record_file.read_text()) if record_file.exists() else {
        "test": "S5", "host": "claude_code", "machine": args.machine, "run_id": f"S5-claude_code-{started.strftime('%Y%m%dT%H%M%SZ')}", "advisory": args.advisory,
        "package": {"version": subprocess.run(["kapso", "--version"], capture_output=True, text=True).stdout.strip().split()[-1], "wheel_sha256": "-"},
        "pins": {"suite_sha256": hashlib.sha256(plugin_proof.SUITE_PATH.read_bytes()).hexdigest(), "cadence_seconds": driver.cadence, "bank": str(driver.bank) if driver.bank else None},
        "user": {"kind": "scripted", "card": None, "interventions": [], "events": [], "pushback": None},
        "started": started.isoformat(timespec="seconds"), "finished": None, "steps": [], "metrics": {}, "notes": [RECONSTRUCTED_LIMIT["note"]], "transcripts": [],
    }
    steps = {"provider-limit": driver.step_provider_limit, "evaluator-crash": driver.step_evaluator_crash, "missing-key": driver.step_missing_key,
             "killed-session": driver.step_killed_session, "killed-writer": driver.step_killed_writer, "full-disk": driver.step_full_disk,
             "tampering": driver.step_tampering, "bank-compare": driver.step_bank_compare}
    assert list(steps) == STEP_NAMES
    selected = args.steps.split(",") if args.steps else list(STEP_NAMES)
    if args.start:
        selected = selected[selected.index(args.start):]
    for name in selected:
        print(f"== {name}", flush=True)
        step = steps[name]()
        record["steps"] = [existing for existing in record["steps"] if existing["name"] != name] + [step]
        record["metrics"] = run_metrics(record)
        record["user"]["interventions"] = sorted(set(record["user"]["interventions"]) | set(driver.ctx.user.interventions))
        record["finished"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
        record["transcripts"] = sorted(f"transcripts/{path.name}" for path in (driver.out / "transcripts").glob("*.jsonl"))
        record_file.write_text(json.dumps(record, indent=1) + "\n", encoding="utf-8")
        print(json.dumps({key: value for key, value in step.items() if key != "notes"}), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
