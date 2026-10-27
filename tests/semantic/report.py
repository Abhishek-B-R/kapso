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

import json
import sys
from pathlib import Path
from typing import Dict, List, Optional

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
    if step.get("kind", "conversation") == "conversation":
        return all(step[key] <= spec[key] for key in COUNT_KEYS if key in spec)
    return "minutes" not in spec or step["minutes"] <= spec["minutes"]


def bar_met(value, bar: dict) -> bool:
    if value is None:
        return False
    return ("min" not in bar or value >= bar["min"]) and ("max" not in bar or value <= bar["max"])


def judge_outcome(record: dict, spec: Optional[dict]) -> Dict[str, object]:
    """What the judge sub-record establishes: `required`, `present`,
    `failure`, `ok`, and per dimension its final score and whether it
    straddled the bar (its passes on both sides, the adjudication deciding)."""
    judge = record.get("judge")
    outcome = {"required": spec is not None, "present": bool(judge), "failure": None, "ok": spec is None, "dimensions": {}}
    if spec is None or not judge:
        return outcome
    if judge.get("failure"):
        outcome["failure"] = judge["failure"]
        return outcome
    passes = judge["passes"]
    bar = spec["bar"]
    ok = len(passes) == 2
    for dimension in spec["dimensions"]:
        scores = [p["scores"][dimension]["score"] for p in passes if dimension in p.get("scores", {})]
        if len(scores) != len(passes):
            ok = False
            outcome["dimensions"][dimension] = {"final": None, "straddled": False}
            continue
        straddled = min(scores) < bar <= max(scores)
        adjudicated = judge.get("adjudication", {}).get(dimension, {}).get("score")
        final = adjudicated if straddled and adjudicated is not None else min(scores)
        outcome["dimensions"][dimension] = {"final": final, "straddled": straddled}
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
    bars = {name: bar_met(metrics.get(name), bar) for name, bar in test.get("bars", {}).items()}
    judge = judge_outcome(record, test.get("judge"))
    passed = not missing_required and not deferred_required and not failed and all(bars.values()) and judge["ok"]
    advisory = record.get("advisory")
    return {
        "passed": passed, "advisory": advisory, "steps": steps, "missing_required": missing_required,
        "deferred_required": deferred_required, "failed": failed, "bars": bars, "judge": judge,
        "exit": EXIT_ADVISORY if passed and advisory else (EXIT_PASS if passed else EXIT_FAIL),
    }


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
    lines += [
        f"- run: {record.get('run_id', '-')}",
        f"- machine: {record['machine']}",
        f"- package: {package['version']} ({package['wheel_sha256'][:12]})",
        f"- started: {record['started']}  finished: {record['finished']}",
        f"- user: {record.get('user', {}).get('kind', 'scripted')}" + (f" ({record['user']['card']}, {record['user'].get('vendor')} {record['user'].get('model')})" if record.get("user", {}).get("kind") == "persona" else ""),
    ]
    pins = record.get("pins", {})
    if pins:
        lines.append("- pins: " + ", ".join(f"{key} {str(value)[:12]}" for key, value in pins.items()))
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
            lines.append(f"| {name} | {record.get('metrics', {}).get(name, '-')} | {json.dumps(bar)} | {'pass' if result['bars'][name] else 'FAIL'} |")
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
            lines += [f"Judge: {sub.get('vendor')} {sub.get('model')} via {sub.get('route', '-')}, {len(sub['passes'])} pass(es), bar {spec['bar']}", "",
                      "| dimension | pass 1 | pass 2 | adjudicated | final | verdict |", "|---|---|---|---|---|---|"]
            for dimension in spec["dimensions"]:
                scores = [p.get("scores", {}).get(dimension, {}).get("score", "-") for p in sub["passes"]] + ["-"] * (2 - len(sub["passes"]))
                adjudicated = sub.get("adjudication", {}).get(dimension, {}).get("score", "-")
                final = judge["dimensions"].get(dimension, {}).get("final")
                lines.append(f"| {dimension} | {scores[0]} | {scores[1]} | {adjudicated} | {final if final is not None else '-'} | {'pass' if final is not None and final >= spec['bar'] else 'FAIL'} |")
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
    if not all(result["bars"].values()):
        reasons.append("bars unmet: " + ", ".join(name for name, met in result["bars"].items() if not met))
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
