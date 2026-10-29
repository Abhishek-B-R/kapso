"""Render one semantic run's record as its markdown report, and compute its
verdict.

    python report.py <record.json> <out.md>

The record's shape is in README.md; the suite's one home, `suite.json`
beside this file, names each test's required steps per host, its run-level
bars and its judge, and each step's kind and budgets. A conversation step
passes when it completed, every count is at or under its budget and every
artifact it names exists; a step of another kind when it completed, its
minutes are under the budget and its artifacts exist; a step the suite
does not know fails (a round cannot add a step nothing bounds); a deferred
step is reported and not counted among the steps, but a deferred step the
test requires fails the run. The verdict: every required step present and
passing, every present step passing, every run-level bar met by the
record's metrics, the judge present and at the bar in both passes where
the test requires one (a straddle adjudicated by a third), no judge
failure; an advisory record (an arm run on the development box) can pass
its steps and never be a fresh-machine acceptance, and the exit status
says which: 0 a pass, 1 a failure, 3 an advisory pass.
"""

import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "scripts" / "redesign"))
from judge import eligible_dimensions, resolve as resolve_judge  # noqa: E402

SUITE_PATH = Path(__file__).resolve().parent / "suite.json"
COUNT_KEYS = ("messages", "questions", "minutes", "longest_message_lines")
EXIT_PASS, EXIT_FAIL, EXIT_ADVISORY = 0, 1, 3


def load_suite(path: Path = SUITE_PATH) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def missing_artifacts(step: dict, root: Path) -> List[str]:
    return [artifact for artifact in step.get("artifacts", []) if not (root / artifact).exists()]


def step_passes(step: dict, spec: Optional[dict], root: Path) -> bool:
    """A step against the suite's entry for it: completed, within its
    budgets, its artifacts present; unknown to the suite is a failure."""
    if not spec or not step["completed"] or missing_artifacts(step, root):
        return False
    if step.get("kind", "conversation") != spec.get("kind", "conversation"):
        return False   # a conversation recorded as a shell step would escape its budgets and the judge
    if step.get("kind", "conversation") == "conversation":
        return all(step[key] <= spec[key] for key in COUNT_KEYS if key in spec)
    return "minutes" not in spec or step["minutes"] <= spec["minutes"]


def bar_verdict(metrics: dict, name: str, bar: dict) -> str:
    """`pass`, `FAIL`, or `not exercised`: a bar that names the metric
    counting the cases it rules on (`exercised_by`) and finds that count
    zero was met on no case — neither met nor failed, and the report says
    so rather than printing a vacuous pass. A missing value fails."""
    exercised_by = bar.get("exercised_by")
    if exercised_by is not None and not metrics.get(exercised_by):
        return "not exercised"
    value = metrics.get(name)
    if value is None:
        return "FAIL"
    return "pass" if ("min" not in bar or value >= bar["min"]) and ("max" not in bar or value <= bar["max"]) else "FAIL"


def judge_outcome(record: dict, spec: Optional[dict], expected_passes: int, suite: dict) -> Dict[str, object]:
    """What the judge sub-record establishes: `required`, `present`,
    `failure`, `ok`, and per dimension its final score — the minimum over
    the judged items eligible for it (the suite's `judged` list per step)
    of each item's resolved score (a straddling item's adjudication
    deciding, else the minimum over passes). The worst eligible item
    binds, and a straddle is resolved per item, not per dimension. A
    dimension the record marks advisory (`advisory_dimensions`: the
    persona nodded through the planted baseline) is reported, not
    binding."""
    judge = record.get("judge")
    outcome = {"required": spec is not None, "present": bool(judge), "failure": None, "ok": spec is None, "dimensions": {}}
    if spec is None or not judge:
        return outcome
    if judge.get("failure"):
        outcome["failure"] = judge["failure"]
        return outcome
    passes = judge["passes"]
    bar = spec["bar"]
    labels = sorted({label for p in passes for label in p.get("items", {})})
    eligible = {label: eligible_dimensions(suite, spec, label, spec["dimensions"]) for label in labels}
    finals = resolve_judge(judge, spec["dimensions"], bar, eligible)
    advisory = set((record.get("advisory_dimensions") or {}).get("dimensions", []))

    def item_straddles(dimension: str, label: str) -> bool:
        scores = [p.get("items", {}).get(label, {}).get(dimension, {}).get("score") for p in passes]
        scores = [score for score in scores if score is not None]
        return bool(scores) and min(scores) < bar <= max(scores)

    ok = len(passes) == expected_passes and bool(labels)
    for dimension in spec["dimensions"]:
        final = finals[dimension]
        outcome["dimensions"][dimension] = {
            "final": final, "advisory": dimension in advisory,
            "straddled": any(item_straddles(dimension, label) for label in labels if dimension in eligible[label]),
        }
        if dimension in advisory:
            continue
        ok = ok and final is not None and final >= bar
    outcome["ok"] = ok
    return outcome


def verdict(record: dict, suite: dict, root: Path) -> Dict[str, object]:
    test = suite["tests"][record["test"]]
    specs = suite["steps"]
    required = test["required_steps"][record["host"]]
    present = {step["name"]: step for step in record["steps"]}
    steps = {}
    for step in record["steps"]:
        if step.get("deferred"):
            steps[step["name"]] = "deferred"
        else:
            steps[step["name"]] = "pass" if step_passes(step, specs.get(step["name"]), root) else "fail"
    missing_required = [name for name in required if name not in present]
    deferred_required = [name for name in required if steps.get(name) == "deferred"]
    failed = [name for name, result in steps.items() if result == "fail"]
    metrics = record.get("metrics", {})
    bars = {name: bar_verdict(metrics, name, bar) for name, bar in test.get("bars", {}).items()}
    judge = judge_outcome(record, test.get("judge"), suite.get("judge", {}).get("passes", 2), suite)
    passed = not missing_required and not deferred_required and not failed and all(mark != "FAIL" for mark in bars.values()) and judge["ok"]
    advisory = record.get("advisory")
    return {
        "passed": passed, "advisory": advisory, "advisory_dimensions": record.get("advisory_dimensions"), "steps": steps, "missing_required": missing_required,
        "deferred_required": deferred_required, "failed": failed, "bars": bars, "judge": judge,
        "exit": EXIT_ADVISORY if passed and advisory else (EXIT_PASS if passed else EXIT_FAIL),
    }


def _short(value) -> str:
    """A pin as the report shows it: a sha256 by its first twelve
    characters, anything else whole (a path or a budget cut to twelve
    characters said nothing)."""
    text = str(value)
    return text[:12] if re.fullmatch(r"[0-9a-f]{64}", text) else text


def _counts(step: dict) -> str:
    return f"| {step['messages']} | {step['questions']} | {step['minutes']} | {step['longest_message_lines']} lines "


def _artifacts(step: dict, root: Path) -> str:
    missing = missing_artifacts(step, root)
    total = len(step.get("artifacts", []))
    return f"{total - len(missing)}/{total}" + (f" missing {', '.join(missing)}" if missing else "")


def render(record: dict, suite: dict, root: Path) -> str:
    result = verdict(record, suite, root)
    package = record["package"]
    lines = [f"# {record['test']} on {record['host']}", ""]
    if record.get("advisory"):
        lines.append(f"**Advisory: {record['advisory']}** (an arm run on the development box proves the flow, not its smoothness; never a fresh-machine acceptance)")
        lines.append("")
    if record.get("advisory_dimensions"):
        block = record["advisory_dimensions"]
        lines.append(f"**Advisory dimensions: {', '.join(block['dimensions'])}** ({block['reason']}; their scores are reported, not binding)")
        lines.append("")
    lines += [
        f"- run: {record.get('run_id', '-')}",
        f"- machine: {record['machine']}",
        f"- package: {package['version']} ({package['wheel_sha256'][:12]})",
        f"- started: {record['started']}  finished: {record['finished']}",
        f"- user: {record.get('user', {}).get('kind', 'scripted')}" + (f" ({record['user']['card']}, {record['user'].get('vendor')} {record['user'].get('model')})" if record.get("user", {}).get("kind") == "persona" else ""),
    ]
    pins = record.get("pins", {})
    if pins:
        lines.append("- pins: " + ", ".join(f"{key} {_short(value)}" for key, value in pins.items()))
    pinned, current = pins.get("suite_sha256"), hashlib.sha256(SUITE_PATH.read_bytes()).hexdigest()
    if pinned and pinned != current:
        lines.append(f"- suite: re-derived under suite {current[:12]}; the run pinned {pinned[:12]} (a changed suite changes the verdict, never the record)")
    lines.append("")
    conversations = [s for s in record["steps"] if s.get("deferred") or s.get("kind", "conversation") == "conversation"]
    others = [s for s in record["steps"] if not s.get("deferred") and s.get("kind", "conversation") != "conversation"]
    if conversations:
        lines += ["| step | messages | questions | minutes | longest message | completed | artifacts | verdict |", "|---|---|---|---|---|---|---|---|"]
        for step in conversations:
            if step.get("deferred"):
                lines.append(f"| {step['name']} | - | - | - | - | - | - | deferred: {step['deferred']} |")
                continue
            mark = result["steps"][step["name"]]
            text = "pass" if mark == "pass" else ("FAIL (no budget)" if step["name"] not in suite["steps"] else "FAIL")
            lines.append(f"| {step['name']} {_counts(step)}| {'yes' if step['completed'] else 'no'} | {_artifacts(step, root)} | {text} |")
        lines.append("")
    if others:
        lines += ["| step | kind | minutes | metrics | completed | artifacts | verdict |", "|---|---|---|---|---|---|---|"]
        for step in others:
            mark = result["steps"][step["name"]]
            text = "pass" if mark == "pass" else ("FAIL (no budget)" if step["name"] not in suite["steps"] else "FAIL")
            metrics = ", ".join(f"{key}={value}" for key, value in step.get("metrics", {}).items()) or "-"
            lines.append(f"| {step['name']} | {step['kind']} | {step['minutes']} | {metrics} | {'yes' if step['completed'] else 'no'} | {_artifacts(step, root)} | {text} |")
        lines.append("")
    test = suite["tests"][record["test"]]
    if test.get("bars"):
        lines += ["| bar | value | limit | verdict |", "|---|---|---|---|"]
        for name, bar in test["bars"].items():
            lines.append(f"| {name} | {record.get('metrics', {}).get(name, '-')} | {json.dumps(bar)} | {result['bars'][name]} |")
        lines.append("")
    judge = result["judge"]
    if judge["required"]:
        if judge["failure"]:
            lines += [f"Judge: FAILED ({judge['failure']}); the raw reply is kept beside the record. Not a pass.", ""]
        elif not judge["present"]:
            lines += ["Judge: none (unjudged; the hard metrics stand, the judged acceptance is not established).", ""]
        else:
            spec = test["judge"]
            sub = record["judge"]
            labels = sorted({label for p in sub["passes"] for label in p.get("items", {})})
            eligible = {label: eligible_dimensions(suite, spec, label, spec["dimensions"]) for label in labels}
            lines += [f"Judge: {sub.get('vendor')} {sub.get('model')} via {sub.get('route', '-')}, {len(sub['passes'])} pass(es), bar {spec['bar']} (the worst eligible item binds; a step's `judged` list in the suite says which dimensions it is scored on)", "",
                      "| dimension | per-pass worst item | adjudicated items | final | verdict |", "|---|---|---|---|---|"]
            for dimension in spec["dimensions"]:
                per_pass = []
                for p in sub["passes"]:
                    item_scores = [item.get(dimension, {}).get("score") for label, item in p.get("items", {}).items() if dimension in eligible.get(label, spec["dimensions"])]
                    present = [score for score in item_scores if score is not None]
                    per_pass.append(str(min(present)) if present else "-")
                adjudicated = sum(1 for key in sub.get("adjudication", {}) if key.startswith(dimension + "|"))
                outcome = judge["dimensions"].get(dimension, {})
                final = outcome.get("final")
                if outcome.get("advisory"):
                    mark = "advisory (reported, not binding)"
                else:
                    mark = "pass" if final is not None and final >= spec["bar"] else "FAIL"
                lines.append(f"| {dimension} | {', '.join(per_pass)} | {adjudicated} | {final if final is not None else '-'} | {mark} |")
            lines.append("")
    noted = [step for step in record["steps"] if step.get("notes")]
    if noted:
        lines.append("Step notes:")
        lines.extend(f"- {step['name']}: {note}" for step in noted for note in step["notes"])
        lines.append("")
    interventions = record.get("user", {}).get("interventions") or []
    if interventions:
        lines.append("The driver's own acts (named, never the persona's):")
        lines.extend(f"- {act}" for act in interventions)
        lines.append("")
    events = record.get("user", {}).get("events") or []
    if events:
        lines.append("The user's events (DONE, the turn cap):")
        lines.extend(f"- {event}" for event in events)
        lines.append("")
    if record.get("notes"):
        lines.append("Notes:")
        lines.extend(f"- {note}" for note in record["notes"])
        lines.append("")
    lines.append("Transcripts:")
    lines.extend(f"- {path}" for path in record.get("transcripts", []))
    lines.append("")
    counted = [mark for mark in result["steps"].values() if mark != "deferred"]
    reasons = []
    if result["missing_required"]:
        reasons.append("required steps missing: " + ", ".join(result["missing_required"]))
    if result["deferred_required"]:
        reasons.append("required steps deferred: " + ", ".join(result["deferred_required"]))
    if result["failed"]:
        reasons.append("steps failed: " + ", ".join(result["failed"]))
    if any(mark == "FAIL" for mark in result["bars"].values()):
        reasons.append("bars unmet: " + ", ".join(name for name, mark in result["bars"].items() if mark == "FAIL"))
    if judge["required"] and not judge["ok"]:
        reasons.append("the judge's bar not established")
    state = "PASS" if result["passed"] else "FAIL"
    if result["passed"] and record.get("advisory"):
        state = "PASS, advisory (the development box; not a fresh-machine acceptance)"
    lines.append(f"Result: {state} ({sum(1 for mark in counted if mark == 'pass')}/{len(counted)} steps" + (f"; {'; '.join(reasons)}" if reasons else "") + ")")
    return "\n".join(lines) + "\n"


def main() -> None:
    record_path = Path(sys.argv[1])
    record = json.loads(record_path.read_text(encoding="utf-8"))
    suite = load_suite()
    Path(sys.argv[2]).write_text(render(record, suite, record_path.parent), encoding="utf-8")
    sys.exit(verdict(record, suite, record_path.parent)["exit"])


if __name__ == "__main__":
    main()
