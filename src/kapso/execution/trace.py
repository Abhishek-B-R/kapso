"""The trace: a campaign's record read into one view and rendered
(wp6-observability.md, change 11). `kapso trace <campaign>` and
`Kapso.trace(path)` are this module, a pure reader over what the build
wrote under `.kapso/`: the status, the launch record, the checkpoint's
node history, the solution record, every session's record with its run
entries, the serving record and the pull log. The text lays the evidence
out section by section, what S4's six questions need (what won, why,
what was voided and on what evidence, what was rejected and why, what it
cost, whether it is safe to merge): the header, the attempts, the
lessons, what was voided or rejected, the sessions that failed, the
delivered candidate. `--json` prints the same data, and `TraceView(data)`
renders it again. No verdict line: the evidence is printed, and the
reader concludes."""
import json
import re
from collections import Counter, defaultdict
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

import yaml

from kapso.execution.coding_agents.session_record import EXIT_ERROR, EXIT_REFUSED, EXIT_TIMEOUT
from kapso.execution.coding_agents.transcripts import CODEX_HOST, GATE_TOOL_PREFIX
from kapso.execution.evaluation_maintainer.registry import EvaluationRegistry
from kapso.execution.inbox import read_launch_record
from kapso.execution.observability import OperationStatusView, source_line
from kapso.execution.run_checkpoint import RunCheckpointStore
from kapso.handles import SOLUTION_RECORD, Solution
from kapso.harness.staging import SESSION_RECORD_FILE, SESSIONS_DIR
from kapso.harness.verdict import VOID
from kapso.learning.bank_invariants import INDEXED_ONLY
from kapso.learning.serving_launch import PULL_LOG_FILE, SERVING_DIR, SERVING_RECORD_FILE

SCHEMA_VERSION = 1
COMPLETE = "complete"
PARTIAL = "partial"
# Where the campaign's cost figure comes from: every session, or the
# Claude Code ones alone (Codex reports no cost).
COVERAGE_ALL = "all"
COVERAGE_CLAUDE = "claude_code"
FAILED_EXITS = (EXIT_ERROR, EXIT_TIMEOUT, EXIT_REFUSED)
# The session labels' grammar (kapso.harness.staging): an attempt's
# implementation session is its branch; its verification and feedback
# sessions prefix the branch; ideation sessions name the iteration.
IDEATION = "ideation"
VERIFICATION = "verification"
FEEDBACK = "feedback"
IMPLEMENTATION = "implementation"
ITERATION_PREFIX = "iter"
PHASE_ORDER = {IDEATION: 0, IMPLEMENTATION: 1, VERIFICATION: 2, FEEDBACK: 3}
# The hook decision that refused a tool call.
DENY = "deny"
# Display widths: the header's label column, and the clip for a
# headline (a first line shown in the compact attempt block; the full
# text is in the data and in `--branch`).
LABEL_WIDTH = 16
HEADLINE_WIDTH = 160
# A heading this short is a title, not a sentence: the headline takes the
# line after it along.
TITLE_WIDTH = 40
STATUS_DONE = "done"
# A unified diff's file header, the path after it.
DIFF_HEADER = re.compile(r"^diff --git a/(.+?) b/", re.MULTILINE)
STATUS_RUNNING = "running"
STATUS_FAILED = "failed"


def is_campaign(path) -> bool:
    return (Path(path).expanduser() / ".kapso").is_dir()


# ================================================================ reading

def read_trace(path) -> "TraceView":
    """The trace of the campaign at `path`. A directory with no `.kapso/`
    is not a campaign and raises by name; a campaign still running, or
    one whose record predates the checkpoint's last write, renders
    partial from the status and the checkpoint."""
    campaign = Path(path).expanduser().resolve()
    if not is_campaign(campaign):
        raise FileNotFoundError(f"{campaign} is not a campaign directory (no .kapso/ inside)")
    status = _status(campaign)
    record = Solution.open(campaign) if (campaign / SOLUTION_RECORD).is_file() else None
    store = RunCheckpointStore(str(campaign))
    checkpoint = store.load() if store.exists() else None
    launch = read_launch_record(campaign)
    sessions = read_sessions(campaign)
    sources = _sources(campaign, record, status, launch)
    pulls = _pull_events(campaign)
    nodes = list((checkpoint.strategy_state.get("node_history") if checkpoint is not None else None) or [])
    attempts, attached = _attempts(nodes, sessions, pulls)
    data = {
        "schema_version": SCHEMA_VERSION,
        "campaign": str(campaign),
        "state": _state(status, record, checkpoint),
        "branch": None,
        "header": _header(campaign, status, record, checkpoint, launch, sessions, nodes, sources),
        "attempts": attempts,
        "sessions": [session for session in sessions if session["label"] not in attached],
        "lessons": _lessons(sources, pulls, nodes),
        "voided": _voided(nodes),
        "failures": _failures(sessions),
        "delivered": _delivered(record, nodes),
    }
    return TraceView(data)


def read_sessions(campaign: Path) -> List[Dict[str, Any]]:
    """Every session record under `.kapso/sessions/`, labelled by its
    directory, with its run entries as the adapters appended them."""
    root = Path(campaign) / SESSIONS_DIR
    if not root.is_dir():
        return []
    sessions = []
    for file in sorted(root.rglob(SESSION_RECORD_FILE)):
        record = json.loads(file.read_text(encoding="utf-8"))
        sessions.append({
            "label": file.parent.relative_to(root).as_posix(),
            "module": record["module"],
            "host": record["host"],
            "runs": list(record["runs"]),
        })
    return sessions


def failed_runs(campaign) -> List[Dict[str, Any]]:
    """The run entries of the campaign's sessions that ended `error`,
    `timeout` or `refused`, each `{label, module, host, exit, error}`:
    what `Solution.session_failures` carries."""
    return [
        {key: failure[key] for key in ("label", "module", "host", "exit", "error")}
        for failure in _failures(read_sessions(Path(campaign)))
    ]


def _status(campaign: Path) -> Optional[Dict[str, Any]]:
    located = OperationStatusView.locate(campaign)
    return OperationStatusView(located).data if located is not None else None


def _sources(campaign: Path, record, status, launch) -> List[Dict[str, Any]]:
    """What the campaign was served: the serving record (each source with
    the count served) when the launcher wrote one, else the sources the
    record, the status or the launch names."""
    serving = campaign / SERVING_DIR / SERVING_RECORD_FILE
    if serving.is_file():
        return list(yaml.safe_load(serving.read_text(encoding="utf-8"))["sources"])
    if record is not None:
        return [vars(source) for source in record.experience]
    if status is not None and status.get("experience"):
        return list(status["experience"])
    if launch is not None:
        return list(launch["experience"])
    return []


def _pull_events(campaign: Path) -> List[Dict[str, Any]]:
    """The pull log's events; a malformed line raises, the log is
    evidence."""
    log = campaign / SERVING_DIR / PULL_LOG_FILE
    if not log.is_file():
        return []
    events = []
    for number, line in enumerate(log.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            raise ValueError(f"{log}:{number}: an empty line in the pull log")
        events.append(json.loads(line))
    return events


def _state(status, record, checkpoint) -> str:
    if status is None or status["state"] != STATUS_DONE or record is None or checkpoint is None:
        return PARTIAL
    return COMPLETE if record.experiments_total == checkpoint.completed_iterations else PARTIAL


def _first(*values):
    for value in values:
        if value is not None:
            return value
    return None


def _header(campaign, status, record, checkpoint, launch, sessions, nodes, sources) -> Dict[str, Any]:
    brief = _first(
        record.brief.to_dict() if record is not None else None,
        launch["brief"] if launch is not None else None,
    )
    evaluator = None
    if record is not None and record.evaluator is not None:
        evaluator = {"version": record.evaluator.version, "provenance": record.evaluator.provenance}
    elif record is None:
        head = EvaluationRegistry(str(campaign)).head()
        if head is not None:
            evaluator = {"version": head.version, "provenance": head.provenance}
    cost = _first(
        record.cost_usd if record is not None else None,
        checkpoint.cumulative_cost if checkpoint is not None else None,
    )
    return {
        "objective": brief["objective"] if brief is not None else None,
        "harness": _first(
            vars(record.harness) if record is not None and record.harness is not None else None,
            status.get("harness") if status is not None else None,
            launch["harness"] if launch is not None else None,
        ),
        "experience": [source_line(source) for source in sources],
        "evaluator": evaluator,
        "budget": status.get("budget") if status is not None else None,
        "cost": {
            "usd": cost,
            "coverage": COVERAGE_CLAUDE if any(session["host"] == CODEX_HOST for session in sessions) else COVERAGE_ALL,
        },
        "stopped_reason": _first(
            record.stopped_reason if record is not None else None,
            status.get("stopped_reason") if status is not None else None,
        ),
        "stop_detail": _first(
            record.stop_detail if record is not None else None,
            status.get("stop_detail") if status is not None else None,
        ),
        "experiments": _first(
            record.experiments_total if record is not None else None,
            checkpoint.completed_iterations if checkpoint is not None else None,
            0,
        ),
        "rejected": (
            record.rejected_candidates if record is not None
            else sum(not node["evaluation_valid"] for node in nodes)
        ),
        "delivered": {
            "branch": record.branch if record is not None else None,
            "commit": record.commit if record is not None else None,
        },
        "status": (
            {"state": status["state"], "phase": status.get("phase"), "error": status.get("error")}
            if status is not None else None
        ),
    }


def _owner(label: str) -> Tuple[str, Any]:
    """Which attempt a session label belongs to: `("branch", name)` for
    an implementation, verification or feedback session, `("iteration",
    n)` for an ideation session (`ideation/iter<n>/<member>`)."""
    head, _, rest = label.partition("/")
    if head == IDEATION:
        iteration, _, _ = rest.partition("/")
        return ("iteration", int(iteration[len(ITERATION_PREFIX):]))
    if head in (VERIFICATION, FEEDBACK):
        return ("branch", rest)
    return ("branch", head)


def _attempts(nodes, sessions, pulls) -> Tuple[List[Dict[str, Any]], Set[str]]:
    """One attempt per node of the checkpoint's history, in order, with
    the sessions that belong to it (its branch's, and the ideation of
    its iteration: the n-th node is iteration n's)."""
    attempts: List[Dict[str, Any]] = []
    attached: Set[str] = set()
    for index, node in enumerate(nodes):
        keys = {("branch", node["branch_name"]), ("iteration", index + 1)}
        own = sorted(
            (session for session in sessions if _owner(session["label"]) in keys),
            key=lambda session: (PHASE_ORDER.get(session["module"], len(PHASE_ORDER)), session["label"]),
        )
        attached.update(session["label"] for session in own)
        attempts.append({
            "node": node["node_id"],
            "parent": node["parent_branch_name"],
            "branch": node["branch_name"],
            "idea": node["solution"],
            "sessions": own,
            "evaluation": {
                "score": node["score"],
                "valid": node["evaluation_valid"],
                "provenance": node["evaluation_provenance"],
                "integrity_error": node["evaluation_integrity_error"] or None,
                "output": node["evaluation_output"],
            },
            "verification": node["verification"],
            "judge": {"stop": node["should_stop"], "valid": node["evaluation_valid"], "feedback": node["feedback"]},
            "cards": {
                "read": _cards_read(pulls, [session["label"] for session in own]),
                "load_bearing": list(node["cards_load_bearing"]),
            },
            "cost_usd": node["cost_usd"],
            "duration_seconds": node["duration_seconds"],
        })
    return attempts, attached


def _served_to(event: Dict[str, Any], labels: Iterable[str]) -> bool:
    """Whether a pull event was made by one of the sessions: the gate
    records the label it serves (`generic_exp_0`, `ideation/iter1`), the
    ideation one a prefix of its members' records."""
    session = event["session"]
    return any(label == session or label.startswith(session + "/") for label in labels)


def _cards_read(pulls, labels) -> List[str]:
    read: Set[str] = set()
    for event in pulls:
        if _served_to(event, labels):
            read.update(row["card"] for row in event.get("served", []) if row["exposure"] != INDEXED_ONLY)
    return sorted(read)


def _lessons(sources, pulls, nodes) -> List[Dict[str, Any]]:
    """One entry per source served: who read which of its cards (the
    pull log, by the session the gate served) and which the judge found
    load-bearing per node (a card belongs to the sources that served
    it)."""
    exposed: Dict[str, Set[str]] = defaultdict(set)          # card -> sources that listed or served it
    for event in pulls:
        for row in event.get("listed", []) + event.get("served", []):
            exposed[row["card"]].add(row["source"])
    lessons = []
    for source in sources:
        reference = source["reference"]
        read_by: Dict[str, Set[str]] = defaultdict(set)
        for event in pulls:
            for row in event.get("served", []):
                if row["source"] == reference and row["exposure"] != INDEXED_ONLY:
                    read_by[event["session"]].add(row["card"])
        load_bearing_by = {}
        for node in nodes:
            cards = [card for card in node["cards_load_bearing"] if reference in exposed[card]]
            if cards:
                load_bearing_by[str(node["node_id"])] = cards
        lessons.append({
            "reference": reference,
            "kind": source["kind"],
            "provenance": source["provenance"],
            "head": source["head"],
            "served": source.get("cards"),
            "read_by": {session: sorted(cards) for session, cards in sorted(read_by.items())},
            "load_bearing_by": load_bearing_by,
        })
    return lessons


def _voided(nodes) -> List[Dict[str, Any]]:
    """Every attempt the campaign did not count, with the evidence: the
    harness's void verdict and its findings, the integrity rejection and
    the evaluation's output, or the judge's invalidation."""
    voided = []
    for node in nodes:
        if node["evaluation_valid"]:
            continue
        verification = node["verification"]
        if verification is not None and verification["verdict"] == VOID:
            reason = f"void: {verification['summary']}"
            evidence = [f"{finding['rule']}: {finding['evidence']}" for finding in verification["findings"]]
        elif node["evaluation_integrity_error"]:
            reason = f"rejected: {node['evaluation_integrity_error']}"
            evidence = [node["evaluation_output"]] if node["evaluation_output"] else []
        else:
            reason = "judged not valid (the judge's words are in the attempt)"
            evidence = [node["evaluation_output"]] if node["evaluation_output"] else []
        voided.append({"node": node["node_id"], "branch": node["branch_name"], "reason": reason, "evidence": evidence})
    return voided


def _failures(sessions) -> List[Dict[str, Any]]:
    """Every run that ended `error`, `timeout` or `refused`, and whether
    every run of its kind (module on host) in the campaign did."""
    outcomes: Dict[Tuple[str, str], List[bool]] = defaultdict(list)
    for session in sessions:
        for run in session["runs"]:
            outcomes[(session["module"], session["host"])].append(run["exit"] in FAILED_EXITS)
    failures = []
    for session in sessions:
        for run in session["runs"]:
            if run["exit"] in FAILED_EXITS:
                failures.append({
                    "label": session["label"],
                    "module": session["module"],
                    "host": session["host"],
                    "exit": run["exit"],
                    "error": run["error"],
                    "every_run": all(outcomes[(session["module"], session["host"])]),
                })
    return failures


def _delivered(record, nodes) -> Optional[Dict[str, Any]]:
    """The delivered candidate: the files it changed are those its
    branch's diff against the seed names (the node's `code_diff`), not
    what a session's editing tools wrote, which a shell command bypasses."""
    if record is None or record.branch is None:
        return None
    node = next((node for node in nodes if node["branch_name"] == record.branch), None)
    return {
        "branch": record.branch,
        "commit": record.commit,
        "base_commit": record.base_commit,
        "files_changed": diff_files(node["code_diff"]) if node is not None else [],
        "verification": record.verification,
        "feedback": record.feedback,
    }


def diff_files(diff: str) -> List[str]:
    """The paths a unified diff names, sorted and unique."""
    return sorted(set(DIFF_HEADER.findall(diff or "")))


# ================================================================ the view

class TraceView:
    """The trace as data (`data`, what `--json` prints) and as text
    (`explain()`); `attempts` and `delivered` are the sections a script
    reads most; `narrow(branch)` keeps one attempt with its evidence in
    full."""

    def __init__(self, data: Dict[str, Any]):
        if not isinstance(data, dict) or data.get("schema_version") != SCHEMA_VERSION:
            raise ValueError(f"not a trace of schema {SCHEMA_VERSION}")
        self.data = data

    @property
    def attempts(self) -> List[Dict[str, Any]]:
        return self.data["attempts"]

    @property
    def delivered(self) -> Optional[Dict[str, Any]]:
        return self.data["delivered"]

    def narrow(self, branch: str) -> "TraceView":
        matching = [attempt for attempt in self.attempts if attempt["branch"] == branch]
        if not matching:
            names = ", ".join(attempt["branch"] for attempt in self.attempts) or "none"
            raise ValueError(f"no attempt on branch {branch!r}; the attempts are: {names}")
        data = deepcopy(self.data)
        data["attempts"] = matching
        data["branch"] = branch
        return TraceView(data)

    def explain(self) -> str:
        return render(self.data)


# ================================================================ the text

def render(data: Dict[str, Any]) -> str:
    full = data["branch"] is not None
    lines = _header_lines(data)
    lines += ["", "ATTEMPTS"]
    if data["attempts"]:
        for attempt in data["attempts"]:
            lines += _attempt_lines(attempt, full)
    else:
        lines.append("  none recorded yet")
    if data["sessions"]:
        lines += ["", "OTHER SESSIONS"]
        for session in data["sessions"]:
            lines += _session_lines(session, full)
    lines += ["", "LESSONS"] + (_lesson_lines(data["lessons"]) or ["  nothing served"])
    lines += ["", "VOIDED OR REJECTED"] + (_voided_lines(data["voided"]) or ["  none"])
    lines += ["", "SESSIONS FAILED"] + (_failure_lines(data["failures"]) or ["  none"])
    lines += ["", "DELIVERED"] + _delivered_lines(data)
    return "\n".join(lines)


def _row(label: str, value: Any) -> str:
    return f"{label:<{LABEL_WIDTH}}{value}"


def _header_lines(data: Dict[str, Any]) -> List[str]:
    header = data["header"]
    lines = [f"trace of {data['campaign']} — {_state_line(data)}"]
    lines.append(_row("objective", _headline(header["objective"]) if header["objective"] else "not recorded"))
    harness = header["harness"]
    lines.append(_row("harness", f"{harness['name']} {harness['version']} ({harness['hash'][:12]})" if harness else "none"))
    if header["experience"]:
        for label in header["experience"]:
            lines.append(_row("served", label))
    else:
        lines.append(_row("served", "nothing"))
    evaluator = header["evaluator"]
    lines.append(_row(
        "evaluator",
        f"v{evaluator['version']}, {evaluator['provenance']}" if evaluator
        else "none registered: the agent's own evaluation",
    ))
    budget = header["budget"]
    if budget and budget.get("total_min"):
        lines.append(_row("budget", f"{float(budget.get('elapsed_min') or 0.0):.1f} of {float(budget['total_min']):.1f} min"))
    cost = header["cost"]
    if cost["usd"] is None:
        lines.append(_row("cost", "not recorded"))
    else:
        coverage = " (Claude Code sessions only; Codex reports no cost)" if cost["coverage"] == COVERAGE_CLAUDE else ""
        lines.append(_row("cost", f"${cost['usd']:.3f}{coverage}"))
    stopped = header["stopped_reason"] or "not stopped"
    if header["stop_detail"]:
        stopped += f" ({header['stop_detail']})"
    experiments = f"{header['experiments']} experiment{'s' if header['experiments'] != 1 else ''}"
    if header["rejected"]:
        experiments += f", {header['rejected']} rejected"
    lines.append(_row("stopped", f"{stopped}; {experiments}"))
    delivered = header["delivered"]
    lines.append(_row(
        "delivered",
        f"{delivered['branch']} @ {delivered['commit'][:12]}" if delivered["branch"] else "none succeeded",
    ))
    if data["branch"] is not None:
        lines.append(_row("showing", f"the attempt on {data['branch']}, in full"))
    return lines


def _state_line(data: Dict[str, Any]) -> str:
    if data["state"] == COMPLETE:
        return COMPLETE
    status = data["header"]["status"]
    if status is None:
        return f"{PARTIAL}: no status yet"
    if status["state"] == STATUS_FAILED:
        return f"{PARTIAL}: the campaign failed: {status['error']}"
    if status["state"] == STATUS_DONE:
        return f"{PARTIAL}: the record predates the checkpoint's last write"
    phase = f" (phase {status['phase']})" if status["phase"] else ""
    return f"{PARTIAL}: the campaign is {status['state']}{phase}"


def _attempt_lines(attempt: Dict[str, Any], full: bool) -> List[str]:
    head = f"node {attempt['node']}  {attempt['branch']}  from {attempt['parent']}"
    if attempt["duration_seconds"] is not None:
        head += f"  {attempt['duration_seconds'] / 60:.1f} min"
    if attempt["cost_usd"] is not None:
        head += f"  ${attempt['cost_usd']:.3f}"
    lines = [head]
    if full:
        lines.append("  idea")
        lines += _indent(attempt["idea"] or "(none recorded)", "    ")
    else:
        lines.append(_row("  idea", _headline(attempt["idea"]) if attempt["idea"] else "(none recorded)"))
    lines.append("  sessions")
    if attempt["sessions"]:
        for session in attempt["sessions"]:
            lines += _session_lines(session, full, indent="    ")
    else:
        lines.append("    none recorded")
    evaluation = attempt["evaluation"]
    measured = f"score {evaluation['score']} ({evaluation['provenance']})" if evaluation["score"] is not None else f"no score ({evaluation['provenance']})"
    measured += ", valid" if evaluation["valid"] else ", not valid"
    if evaluation["integrity_error"]:
        measured += f"; integrity: {evaluation['integrity_error']}"
    lines.append(_row("  evaluation", measured))
    if full and evaluation["output"]:
        lines.append("  evaluation output")
        lines += _indent(evaluation["output"], "    ")
    verification = attempt["verification"]
    if verification is None:
        lines.append(_row("  verification", "none (no harness verification)"))
    elif full:
        lines.append(_row("  verification", verification["verdict"]))
        lines += _indent(verification["summary"], "    ")
        for finding in verification["findings"]:
            lines += _indent(f"- {finding['rule']}: {finding['evidence']}", "    ")
    else:
        lines.append(_row("  verification", f"{verification['verdict']}: {_headline(verification['summary'])}"))
    judge = attempt["judge"]
    verdict = ("valid" if judge["valid"] else "not valid") + (", stop" if judge["stop"] else ", continue")
    if full:
        lines.append(_row("  judge", verdict))
        lines += _indent(judge["feedback"] or "(no feedback recorded)", "    ")
    else:
        lines.append(_row("  judge", f"{verdict}: {_headline(judge['feedback']) if judge['feedback'] else '(no feedback recorded)'}"))
    cards = attempt["cards"]
    lines.append(_row("  cards read", f"{len(cards['read'])}: {', '.join(cards['read'])}" if cards["read"] else "none"))
    lines.append(_row(
        "  load-bearing", f"{len(cards['load_bearing'])}: {', '.join(cards['load_bearing'])}" if cards["load_bearing"] else "none",
    ))
    return lines


def _session_lines(session: Dict[str, Any], full: bool, indent: str = "  ") -> List[str]:
    lines = []
    if not session["runs"]:
        lines.append(f"{indent}{session['label']:<30} {session['host']:<11} no run recorded")
        return lines
    for number, run in enumerate(session["runs"], start=1):
        label = session["label"] if number == 1 else f"  run {number}"
        lines.append(f"{indent}{label:<30} {session['host']:<11} {_run_summary(run)}")
        if full:
            lines += _run_detail(run, indent + "    ")
    return lines


def _run_summary(run: Dict[str, Any]) -> str:
    parts = [f"{run['exit']:<8}"]
    parts.append(f"{run['duration_seconds'] / 60:5.1f} min" if run["duration_seconds"] is not None else "    - min")
    if run["cost_usd"] is not None:
        parts.append(f"${run['cost_usd']:.3f}")
    elif run["usage"]:
        parts.append(f"{_tokens(run['usage'])} tokens")
    else:
        parts.append("cost n/a")
    parts.append(f"{run['turns']} turns")
    tools = {name: count for name, count in run["tools"].items() if not name.startswith(GATE_TOOL_PREFIX)}
    if tools:
        top = sorted(tools.items(), key=lambda item: (-item[1], item[0]))
        shown = ", ".join(f"{name} {count}" for name, count in top[:5])
        if len(top) > 5:
            shown += f", +{len(top) - 5} more"
        parts.append(f"tools {shown}")
    if run["gates"]:
        parts.append("gates " + ", ".join(f"{server} {sum(tools.values())}" for server, tools in sorted(run["gates"].items())))
    if run["hooks"] is None:
        parts.append("hooks not reported by this host")
    elif run["hooks"]:
        denied = sum(hook["decision"] == DENY for hook in run["hooks"])
        parts.append(f"hooks {len(run['hooks'])} fired" + (f", {denied} denied" if denied else ""))
    delegates = [delegate for delegate in run["delegates"] if "receivers" not in delegate]
    if delegates:
        parts.append("delegates " + ", ".join(
            f"{delegate.get('name')} {delegate.get('status')}" for delegate in delegates
        ))
    collab = Counter(delegate.get("name") for delegate in run["delegates"] if "receivers" in delegate)
    if collab:
        # Codex's collaboration calls: the verb, not a delegate's name.
        parts.append("collab " + ", ".join(f"{verb} {count}" for verb, count in sorted(collab.items())))
    if run["error"] and run["exit"] != EXIT_ERROR and run["exit"] != EXIT_TIMEOUT and run["exit"] != EXIT_REFUSED:
        parts.append(f"error {_headline(run['error'])}")
    elif run["error"]:
        parts.append(_headline(run["error"]))
    return "  ".join(parts)


def _run_detail(run: Dict[str, Any], indent: str) -> List[str]:
    """Everything a run entry holds, in full: the error, the host's own
    errors, each hook's decision, each delegate's report, the files
    changed, the closing message."""
    lines = []
    if run["model"]:
        lines.append(f"{indent}model {run['model']}" + (f"; host session {run['cli_session_id']}" if run["cli_session_id"] else ""))
    if run["error"]:
        lines.append(f"{indent}error")
        lines += _indent(run["error"], indent + "  ")
    for message in run["host_errors"]:
        lines.append(f"{indent}host error")
        lines += _indent(message, indent + "  ")
    for hook in run["hooks"] or []:
        decision = hook["decision"] or "no decision"
        reason = f": {hook['reason']}" if hook["reason"] else ""
        lines.append(f"{indent}hook {hook['event']} {hook['name']} -> {decision}{reason}")
    for delegate in run["delegates"]:
        if "receivers" in delegate:
            lines.append(f"{indent}collab {delegate.get('name')} ({delegate.get('status')})")
            if delegate.get("prompt"):
                lines += _indent(delegate["prompt"], indent + "  ")
            continue
        lines.append(f"{indent}delegate {delegate.get('name')} ({delegate.get('status')})")
        if delegate.get("report"):
            lines += _indent(delegate["report"], indent + "  ")
    if run["files_changed"]:
        lines.append(f"{indent}files changed: {', '.join(run['files_changed'])}")
    if run["last_message"]:
        lines.append(f"{indent}closing message")
        lines += _indent(run["last_message"], indent + "  ")
    return lines


def _lesson_lines(lessons: List[Dict[str, Any]]) -> List[str]:
    lines = []
    for lesson in lessons:
        label = source_line(lesson)
        if lesson["kind"] == "bank":
            served = f"{lesson['served']} cards served" if lesson["served"] is not None else "count not recorded"
            lines.append(f"{label}: {served}")
            if not lesson["read_by"]:
                lines.append("  read by nobody")
            for session, cards in lesson["read_by"].items():
                lines.append(f"  read by {session} ({len(cards)}): {', '.join(cards)}")
            for node, cards in lesson["load_bearing_by"].items():
                lines.append(f"  load-bearing in node {node} ({len(cards)}): {', '.join(cards)}")
        else:
            lines.append(f"{label}: served through its gate; the sessions' gates columns count the calls")
    return lines


def _voided_lines(voided: List[Dict[str, Any]]) -> List[str]:
    lines = []
    for entry in voided:
        lines += _indent(f"node {entry['node']}  {entry['branch']}  {entry['reason']}", "")
        for evidence in entry["evidence"]:
            lines += _indent(f"- {evidence}", "    ")
        if not entry["evidence"]:
            lines.append("    (no evidence recorded)")
    return lines


def _failure_lines(failures: List[Dict[str, Any]]) -> List[str]:
    lines = []
    for failure in failures:
        lines += _indent(
            f"{failure['label']}  {failure['module']} on {failure['host']}  {failure['exit']}: {failure['error'] or '(no error text)'}", "",
        )
    kinds = sorted({(failure["module"], failure["host"]) for failure in failures if failure["every_run"]})
    if kinds:
        lines.append("every run failed: " + ", ".join(f"{module} on {host}" for module, host in kinds))
    return lines


def _delivered_lines(data: Dict[str, Any]) -> List[str]:
    delivered = data["delivered"]
    if delivered is None:
        return ["none succeeded"]
    lines = [f"{delivered['branch']} @ {delivered['commit'][:12]} (base {delivered['base_commit'][:12]})"]
    lines.append(_row("files changed", ", ".join(delivered["files_changed"]) if delivered["files_changed"] else "none recorded"))
    verification = delivered["verification"]
    if verification is None:
        lines.append(_row("verification", "none (no harness verification)"))
    else:
        lines.append(_row("verification", verification["verdict"]))
        lines += _indent(verification["summary"], "  ")
        for finding in verification["findings"]:
            lines += _indent(f"- {finding['rule']}: {finding['evidence']}", "  ")
    own = next((attempt for attempt in data["attempts"] if attempt["branch"] == delivered["branch"]), None)
    if own is not None:
        evaluation = own["evaluation"]
        integrity = f"{evaluation['provenance']}; " + (f"integrity error: {evaluation['integrity_error']}" if evaluation["integrity_error"] else "intact")
        lines.append(_row("integrity", integrity))
        fired, denials = 0, []
        for session in own["sessions"]:
            for run in session["runs"]:
                for hook in run["hooks"] or []:
                    fired += 1
                    if hook["decision"] == DENY:
                        denials.append(f"{session['label']}: {hook['name']} ({hook['event']}){': ' + hook['reason'] if hook['reason'] else ''}")
        hooks = f"{fired} fired in its sessions" + (f", {len(denials)} denied" if denials else ", none denied") if fired else "none fired in its sessions"
        lines.append(_row("hooks", hooks))
        for denial in denials:
            lines.append(f"  {denial}")
        failed = [
            f"{session['label']}: {run['exit']}: {run['error']}"
            for session in own["sessions"] for run in session["runs"] if run["exit"] in FAILED_EXITS
        ]
        lines.append(_row("failures", "none in its sessions" if not failed else f"{len(failed)} in its sessions"))
        for line in failed:
            lines += _indent(line, "  ")
    lines.append("judge")
    lines += _indent(delivered["feedback"] or "(no feedback recorded)", "  ")
    return lines


def _tokens(usage: Dict[str, Any]) -> str:
    """A host's token usage in one figure: the input, cached included, and
    the output."""
    inputs = int(usage.get("input_tokens") or 0)
    outputs = int(usage.get("output_tokens") or 0)
    return f"{inputs / 1000:.0f}k in, {outputs / 1000:.1f}k out"


def _headline(text: str, width: int = HEADLINE_WIDTH) -> str:
    """The first line that says something, clipped for the compact view;
    a short title (`# Core Idea`) takes the line after it along. The data
    keeps the whole text."""
    lines = [line.strip() for line in (text or "").splitlines() if line.strip()]
    if not lines:
        return ""
    head = lines[0].lstrip("#").strip()
    if lines[0].startswith("#") and len(head) <= TITLE_WIDTH and len(lines) > 1:
        head = f"{head}: {lines[1].lstrip('#').strip()}"
    return head if len(head) <= width else head[: width - 1] + "…"


def _indent(text: str, prefix: str) -> List[str]:
    return [f"{prefix}{line}" if line else "" for line in (text or "").splitlines()] or [prefix.rstrip() or ""]
