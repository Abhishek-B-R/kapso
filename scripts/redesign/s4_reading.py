"""S4 of the semantic suite (docs/plans/redesign/wp9-semantic-suite.md,
change 7): the trace is legible without the agent.

A reader who did not watch the run (a model on each host, a cold session
with no plugin, no server and no web) is given only `kapso trace`'s text
and the campaign directory, and answers the six questions: what won, why,
what was voided and on what evidence, what was rejected and why, what it
cost, whether it is safe to merge. The fact sheet is extracted by the
driver from the trace's JSON and the delivered branch's history, checked
once by hand, kept out of the reader's directory, and handed to the judge
with the reader's answers (`judge.py --rubric s4 --inputs judge/reading-
<host>.md ...`); `--grade` then reads the judge's block into the record's
metrics. "Not established" is a correct answer where the record does not
settle it.

    python3 s4_reading.py --campaign <dir> --out <dir> --clone <clone> [--readers claude_code,codex] [--advisory <reason>]
    python3 s4_reading.py --out <dir> --grade
"""

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

sys.path.insert(0, str(Path(__file__).resolve().parent))
import plugin_proof  # noqa: E402
import judge as judge_module  # noqa: E402
from plugin_proof import SUITE, ClaudeHost, CodexHost, record_step, shell_step  # noqa: E402
from s1_cold_engineer import CLAUDE_COLD, CODEX_COLD, plugin_proof_rows, session_init, is_cold  # noqa: E402

QUESTIONS = [
    ("what won", "What won: which branch the campaign delivered and at what score."),
    ("why", "Why that one: what made it the delivered candidate, with the evidence the record holds."),
    ("what was voided and on what evidence", "What was voided, and on what evidence."),
    ("what was rejected and why", "What was rejected, and why."),
    ("what it cost", "What it cost, and how complete that figure is."),
    ("safe to merge", "Whether the delivered branch is safe to merge into the repository, and what that rests on."),
]
PROMPT = (
    "You did not watch this run. In this directory: `trace.txt`, the campaign's record rendered by `kapso trace`, and `campaign/`, the campaign directory "
    "itself (its `.kapso/` holds the files the trace was rendered from, its git history holds the delivered branch). From these alone, answer the six "
    "questions below, each in a short paragraph that names the file or line the answer rests on. Where the record does not settle a question, say "
    "\"not established\" and why. Use no web.\n\n" + "\n".join(f"{number}. {text}" for number, (_, text) in enumerate(QUESTIONS, 1))
)
STEP_NAMES = ["fact-sheet", "reading-claude_code", "reading-codex"]


# ------------------------------------------------------------ the sheet
LABEL_GLOBS = ("*holdout_labels.csv", "*/private/*")


def labels_in_history(campaign: Path, delivered_commit: Optional[str]) -> Optional[bool]:
    """Whether the hold-out labels are in the DELIVERED commit's own
    ancestry (a merge of that branch carries them into the repository):
    searched by the label filename and the private path, not one hard-coded
    directory, and down the delivered commit's history only, never `--all`
    (a label on an abandoned branch is not merged). None when the campaign
    has no repository or the delivered commit is unknown."""
    if not (campaign / ".git").exists() or not delivered_commit:
        return None
    run = subprocess.run(["git", "-C", str(campaign), "log", "--oneline", delivered_commit, "--", *LABEL_GLOBS], capture_output=True, text=True)
    return run.returncode == 0 and bool(run.stdout.strip())


def fact_sheet(trace: Dict[str, Any], labels: Optional[bool]) -> Dict[str, Any]:
    """The six answers as the record has them, extracted mechanically. A
    rejection is an attempt the engine did not count (the trace's `voided`,
    whose reason is a void or a "judged not valid"/"rejected:"); a scored
    attempt that simply lost is a runner-up, reported apart, not a
    rejection (the engine's own semantics, base.py: a rejected attempt has
    no score)."""
    header, delivered = trace["header"], trace["delivered"]
    attempts = {attempt["branch"]: attempt for attempt in trace["attempts"]}
    winner = attempts.get(delivered.get("branch")) if delivered else None
    voided = trace.get("voided") or []
    # The trace's `voided` holds both: an integrity/harness void and a
    # judge rejection, each with its reason. Split them by substance, so
    # the two questions get distinct keys: the engine words an integrity
    # failure "rejected: Provided evaluation integrity check failed
    # (changed: evaluate.py)" (s4-claude-1), and a void it is — the design's
    # "voided on the hash evidence"; a judge's "not valid" is the rejection.
    def is_void(entry: Dict[str, Any]) -> bool:
        reason = str(entry.get("reason", "")).lower()
        return reason.startswith("void") or "integrity" in reason
    voids = [entry for entry in voided if is_void(entry)]
    rejections = [entry for entry in voided if not is_void(entry)]
    # What the dollar figure covers: the sessions whose runs carry no cost
    # (a Codex session reports none), named by host, beside the header's
    # own coverage word — a reader who says "not established" for the
    # whole is reading the record right.
    every_session = list(trace.get("sessions") or []) + [session for attempt in trace["attempts"] for session in attempt.get("sessions", [])]
    unpriced = [session.get("host") for session in every_session if session.get("runs") and all(run.get("cost_usd") is None for run in session["runs"])]
    runners_up = [
        {"branch": attempt["branch"], "score": attempt["evaluation"].get("score")}
        for attempt in trace["attempts"]
        if attempt["evaluation"].get("score") is not None and delivered and attempt["branch"] != delivered.get("branch")
    ]
    cost = header["cost"]
    verification = winner.get("verification") if winner else None
    merge_facts = {
        "verification": verification if verification is not None else "no verification ran (no harness): not established by a verifier",
        "integrity": "no integrity error on the delivered attempt" if winner and not winner["evaluation"].get("integrity_error") else (winner["evaluation"].get("integrity_error") if winner else "no delivered attempt"),
        "labels_in_history": {True: "the hold-out labels are in the delivered commit's own history: a merge of the branch would carry them into the repository", False: "the hold-out labels are not in the delivered commit's history: a merge does not carry them", None: "not established: no repository or no delivered commit"}[labels],
        "files_changed": delivered.get("files_changed", []) if delivered else [],
    }
    return {
        "what won": {"branch": delivered.get("branch") if delivered else None, "commit": delivered.get("commit") if delivered else None,
                     "score": winner["evaluation"].get("score") if winner else None, "provenance": winner["evaluation"].get("provenance") if winner else None,
                     "goal_achieved": trace.get("state")},
        "why": {"idea": winner.get("idea") if winner else None, "judge": winner.get("judge") if winner else None, "score": winner["evaluation"].get("score") if winner else None},
        "what was voided and on what evidence": voids or "nothing voided",
        "what was rejected and why": rejections or f"nothing rejected (the header counts {header.get('rejected', 0)}); the scored runners-up were {runners_up or 'none'}",
        "what it cost": {"usd": cost.get("usd"), "coverage": cost.get("coverage"), "unpriced_runs": cost.get("unpriced_runs"),
                         "sessions_without_a_cost": {host: unpriced.count(host) for host in sorted(set(unpriced))} or "none: every session priced"},
        "safe to merge": merge_facts,
        "scored_not_delivered": runners_up,
    }


def render_sheet(facts: Dict[str, Any]) -> str:
    lines = ["# The fact sheet (extracted from the record; the reader never saw it)", ""]
    for key, _ in QUESTIONS:
        lines.append(f"## {key}")
        lines.append("```json")
        lines.append(json.dumps(facts[key], indent=2))
        lines.append("```")
        lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------- driver
class S4:
    def __init__(self, args: argparse.Namespace):
        self.args = args
        self.out = Path(args.out).resolve()
        (self.out / "transcripts").mkdir(parents=True, exist_ok=True)
        (self.out / "artifacts").mkdir(parents=True, exist_ok=True)
        (self.out / "judge").mkdir(parents=True, exist_ok=True)
        self.campaign = Path(args.campaign).resolve() if args.campaign else None

    def artifact(self, name: str, text: str) -> str:
        (self.out / "artifacts" / name).write_text(text, encoding="utf-8")
        return f"artifacts/{name}"

    def step_fact_sheet(self) -> Dict[str, Any]:
        started = time.monotonic()
        text = subprocess.run(["kapso", "trace", str(self.campaign)], capture_output=True, text=True)
        data = subprocess.run(["kapso", "trace", str(self.campaign), "--json"], capture_output=True, text=True)
        if text.returncode != 0 or data.returncode != 0:
            return shell_step("fact-sheet", False, [self.artifact("trace.err", text.stderr + data.stderr)], (time.monotonic() - started) / 60, ["kapso trace failed"])
        trace = json.loads(data.stdout)
        delivered_commit = (trace.get("delivered") or {}).get("commit")
        facts = fact_sheet(trace, labels_in_history(self.campaign, delivered_commit))
        (self.out / "judge" / "fact-sheet.md").write_text(render_sheet(facts), encoding="utf-8")
        artifacts = [self.artifact("trace.txt", text.stdout), self.artifact("trace.json", data.stdout), self.artifact("fact-sheet.json", json.dumps(facts, indent=2))]
        return shell_step("fact-sheet", True, artifacts, (time.monotonic() - started) / 60, ["the fact sheet extracted from the trace and the branch's history; checked by hand once; under judge/, never in the reader's directory"])

    def step_reading(self, host_name: str) -> Dict[str, Any]:
        reading = self.out / "work" / f"reading-{host_name}"
        if reading.exists():
            shutil.rmtree(reading)
        reading.mkdir(parents=True)
        shutil.copy(self.out / "artifacts" / "trace.txt", reading / "trace.txt")
        shutil.copytree(self.campaign, reading / "campaign", symlinks=True, ignore=shutil.ignore_patterns("judge"))
        host = ClaudeHost(CLAUDE_COLD) if host_name == "claude_code" else CodexHost(CODEX_COLD)
        transcript = self.out / "transcripts" / f"reading-{host_name}.jsonl"
        turn = host.turn(reading, PROMPT, None, transcript)
        init = session_init(plugin_proof_rows(transcript)) if host_name == "claude_code" else None
        sheet = (self.out / "judge" / "fact-sheet.md").read_text(encoding="utf-8")
        (self.out / "judge" / f"reading-{host_name}.md").write_text(f"# The reader's answers ({host_name})\n\n{turn.text}\n\n{sheet}", encoding="utf-8")
        step = record_step(f"reading-{host_name}", [turn], bool(turn.text.strip()) and (init is None or is_cold(init)),
                           [self.artifact(f"reading-{host_name}.txt", turn.text)], ["graded by the judge against the fact sheet (the s4 rubric); the metrics filled by --grade"], kind="reading")
        step["metrics"] = {"correct": None, "cold": is_cold(init) if init else None}
        return step


def grade(record: Dict[str, Any]) -> Dict[str, Any]:
    """The judge's block into the record: per reader the questions right,
    each question RESOLVED the way the verdict resolves it (a straddle's
    adjudication deciding, not the bare two-pass minimum), and the run's
    minimum over readers. The same resolution the final verdict uses, so a
    question adjudicated correct is not still counted wrong."""
    judge = record.get("judge") or {}
    if judge.get("failure") or not judge.get("passes"):
        return record
    dimensions = [key for key, _ in QUESTIONS]
    resolved = judge_module.resolve_items(judge, dimensions, SUITE["tests"]["S4"]["judge"]["bar"])
    bar = SUITE["tests"]["S4"]["judge"]["bar"]
    correct: Dict[str, int] = {}
    for step in record["steps"]:
        if step.get("kind") != "reading" or step["name"] not in resolved:
            continue
        scores = resolved[step["name"]]
        if any(scores[key] is None for key in dimensions):
            continue
        right = sum(1 for key in dimensions if scores[key] >= bar)
        step["metrics"]["correct"] = right
        correct[step["name"]] = right
    if correct:
        record["metrics"]["readers_correct_min"] = min(correct.values())
    return record


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--campaign", default=None, help="the campaign read (S5's tampering campaign: a void, a rejection)")
    parser.add_argument("--out", required=True)
    parser.add_argument("--clone", default=None)
    parser.add_argument("--readers", default="claude_code,codex")
    parser.add_argument("--machine", default=os.uname().nodename)
    parser.add_argument("--advisory", default=None)
    parser.add_argument("--grade", action="store_true", help="read the judge's block into the record's metrics")
    parser.add_argument("--steps", default=None)
    args = parser.parse_args(argv)
    driver = S4(args)
    record_file = driver.out / "record.json"
    started = datetime.now(timezone.utc)
    record = json.loads(record_file.read_text()) if record_file.exists() else {
        "test": "S4", "host": "claude_code", "machine": args.machine, "run_id": f"S4-{started.strftime('%Y%m%dT%H%M%SZ')}", "advisory": args.advisory,
        "package": {"version": subprocess.run(["kapso", "--version"], capture_output=True, text=True).stdout.strip().split()[-1] if shutil.which("kapso") else "-", "wheel_sha256": "-"},
        "pins": {"suite_sha256": hashlib.sha256(plugin_proof.SUITE_PATH.read_bytes()).hexdigest(), "campaign": str(driver.campaign)},
        "user": {"kind": "scripted", "card": None, "interventions": ["the fact sheet extracted by the driver and checked by hand; the readers see the trace and the campaign only"], "events": [], "pushback": None},
        "started": started.isoformat(timespec="seconds"), "finished": None, "steps": [], "metrics": {}, "notes": [], "transcripts": [],
    }
    if args.grade:
        record = grade(record)
        record_file.write_text(json.dumps(record, indent=1) + "\n", encoding="utf-8")
        print(json.dumps(record["metrics"]))
        return 0
    if not args.campaign:
        parser.error("--campaign, or --grade")
    selected = args.steps.split(",") if args.steps else ["fact-sheet", *[f"reading-{reader}" for reader in args.readers.split(",")]]
    for name in selected:
        print(f"== {name}", flush=True)
        step = driver.step_fact_sheet() if name == "fact-sheet" else driver.step_reading(name.split("-", 1)[1])
        record["steps"] = [existing for existing in record["steps"] if existing["name"] != name] + [step]
        record["finished"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
        record["transcripts"] = sorted(f"transcripts/{path.name}" for path in (driver.out / "transcripts").glob("*.jsonl"))
        record_file.write_text(json.dumps(record, indent=1) + "\n", encoding="utf-8")
        print(json.dumps({key: value for key, value in step.items() if key != "notes"}), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
