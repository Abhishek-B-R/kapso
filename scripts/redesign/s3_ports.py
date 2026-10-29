#!/usr/bin/env python3
"""S3, the harness ports, as a record of the semantic suite
(docs/plans/redesign/wp8-harness-ports.md change 20): the four arms, the
abstraction scan and the four task swaps as the steps of one machine run,
re-derived from the arm archives without live state.

    python scripts/redesign/s3_ports.py --rederive [--record scripts/redesign/runs/s3-1]

The record directory holds `arms.json`, written by hand as the arms run:

    {"wheel_sha256": "<the wheel every machine installed>",
     "harness_pins": {"predictive-modelling": "<hash>", "competitive-programming": "<hash>"},
     "ioai_median": 0.8184,
     "runs": {"arm-ale": "s3-ale-1", "swap-ale": null, ...}}

A step whose run id is null is recorded as deferred (the report says so
and a required step deferred fails the run). Each named run is a
directory under scripts/redesign/runs/<id>/ as benchmark_machine.sh and
the arm scripts leave it: `arm.log` (the step timestamps and the
deletion line), `fetched/bench/runs/<name>/campaign/.kapso/` (the launch
record and the sessions) and the benchmark's final report. The step's
metrics are what those files evidence: the score, the sessions by kind,
the skills staged, the hooks mounted and fired, the delegates' reports, the cards
served, the cost, the machine hours and the tokens per model. The
run-level bars read the record's metrics; the scan runs live over the
bundled trees and the harness hashes are compared with the pins, so a
harness edit after the freeze is a failing bar, not a silent drift.
The verdict is report.py's, as for every test."""

import argparse
import hashlib
import json
import re
import subprocess
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tests" / "semantic"))
import report  # noqa: E402
from benchmarks.harness_scan import scan, vocabulary  # noqa: E402
from kapso.harness import BUNDLED_ROOT  # noqa: E402
from kapso.harness.hash import harness_hash  # noqa: E402

TEST = "s3"
HOST = "machine"
STEP_NAMES = ["scan", "arm-relbench", "arm-mle", "arm-ale", "arm-ioai", "swap-relbench", "swap-ale", "swap-kaggle", "swap-ioai"]
RUNS = HERE / "runs"
REPORTS = ROOT / "tests" / "semantic" / "reports"
_STAMP = re.compile(r"^\[(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z)\] (\w+)")
_DELETED = re.compile(r"deleted \S+ after ([\d.]+)h, about \$([\d.]+)")
_SKILL = re.compile(r"skills/([a-z0-9-]+)/SKILL\.md")
_SUBMIT = re.compile(r"kaggle\s+(competitions|c)\s+submit\b")


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _stamps(log: Path) -> Dict[str, datetime]:
    """The first timestamp of each step word in an arm log."""
    found: Dict[str, datetime] = {}
    for line in log.read_text(encoding="utf-8").splitlines():
        match = _STAMP.match(line)
        if match and match.group(2) not in found:
            found[match.group(2)] = datetime.strptime(match.group(1), "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    return found


def _machine_bill(log: Path) -> Dict[str, Optional[float]]:
    match = _DELETED.search(log.read_text(encoding="utf-8"))
    if not match:
        return {"machine_hours": None, "machine_usd": None}
    return {"machine_hours": float(match.group(1)), "machine_usd": float(match.group(2))}


def _campaign_dir(run_dir: Path) -> Path:
    candidates = sorted(run_dir.glob("fetched/bench/runs/*/campaign")) + sorted(run_dir.glob("fetched/bench/runs/*/task/kapso_campaign"))
    if len(candidates) != 1:
        raise FileNotFoundError(f"{run_dir}: expected one fetched campaign, found {[str(c) for c in candidates]}")
    return candidates[0]


def _session_facts(campaign: Path) -> Dict[str, Any]:
    """What the sessions' records evidence: the sessions by module, the
    pages and skills staged into them (staged, not opened: what the host
    loaded is not in the record), the hooks mounted and the hooks fired by
    outcome where the host reports them (Claude Code; Codex reports none,
    so a Codex arm evidences a hook by its effect, the ledger's token on
    every submission), the bank tool
    calls, the delegates with a report, the Claude cost, the tokens per
    model, and the raw `kaggle competitions submit` commands seen in the
    streams (the hook's business; the ledger says what went through)."""
    modules: Counter = Counter()
    pages: set = set()
    skills: set = set()
    mounted: set = set()
    hooks: Counter = Counter()
    bank_tools: Counter = Counter()
    delegates = 0
    reports = 0
    cost = 0.0
    tokens: Dict[str, Counter] = {}
    attempts = 0
    for record_path in sorted(campaign.glob(".kapso/sessions/**/session.json")):
        record = _read_json(record_path)
        modules[str(record.get("module"))] += 1
        pages.update(str(p) for p in record.get("pages") or [])
        skills.update(str(s) for s in record.get("skills") or [])
        mounted.update(str(h) for h in record.get("hooks") or [])
        for run in record.get("runs", []):
            for hook in run.get("hooks") or []:
                hooks[f"{hook.get('name') or hook.get('event')}:{hook.get('outcome')}"] += 1
            for tool, count in (run.get("tools") or {}).items():
                if "bank_" in tool:
                    bank_tools[tool.split("__")[-1]] += int(count)
            for delegate in run.get("delegates") or []:
                delegates += 1
                reports += 1 if delegate.get("report") else 0
            if run.get("cost_usd") is not None:
                cost += float(run["cost_usd"])
            model = str(run.get("model"))
            tokens.setdefault(model, Counter())
            for key, value in (run.get("usage") or {}).items():
                if isinstance(value, (int, float)):
                    tokens[model][key] += int(value)
        for stream in record_path.parent.glob("*.jsonl"):
            for line in stream.read_text(encoding="utf-8", errors="replace").splitlines():
                if _SUBMIT.search(line) and '"command"' in line and "submit.py" not in line:
                    attempts += 1
    return {
        "sessions": dict(modules), "pages": sorted(pages), "skills_staged": sorted(skills),
        "hooks_mounted": sorted(mounted), "hooks_fired": dict(hooks),
        "bank_tools": dict(bank_tools), "delegates": delegates, "delegate_reports": reports,
        "claude_cost_usd": round(cost, 2), "tokens": {model: dict(counts) for model, counts in tokens.items()},
        "shell_submit_attempts": attempts,
    }


def _served(campaign: Path) -> Dict[str, int]:
    """The pull log: index calls, and card reads at the two depths."""
    counts: Counter = Counter()
    for log in campaign.glob(".kapso/serving/serving-pull.jsonl"):
        for line in log.read_text(encoding="utf-8").splitlines():
            entry = json.loads(line)
            counts[str(entry.get("tool"))] += 1
            if entry.get("exposure") in ("read", "evidence-read"):
                counts["cards_read"] += len(entry.get("served") or entry.get("cards") or [])
    return {"bank_index_calls": counts.get("bank_index", 0), "cards_read": counts.get("cards_read", 0)}


def _score(step: str, run_dir: Path) -> Dict[str, Any]:
    """The benchmark's final report, read for the number the bar names."""
    if step in ("arm-ale", "swap-ale"):
        reports = sorted(run_dir.glob("fetched/bench/tmp/ale/*/final_report.json"))
        if len(reports) != 1:
            raise FileNotFoundError(f"{run_dir}: expected one ALE final report, found {len(reports)}")
        data = _read_json(reports[0])
        private = data.get("private_evaluation") or {}
        return {"ale_rating": private.get("final_performance"), "ale_rank": private.get("final_rank"),
                "ale_contestants": private.get("contestants"), "delivered": data.get("solution", {}).get("score"),
                "error": data.get("error")}
    if step in ("arm-relbench", "swap-relbench"):
        reports = sorted(run_dir.glob("fetched/bench/tmp/relbench/*/final_report.json"))
        if len(reports) != 1:
            raise FileNotFoundError(f"{run_dir}: expected one RelBench final report, found {len(reports)}")
        data = _read_json(reports[0])
        return {"relbench_test_auroc": (data.get("test_metrics") or data.get("metrics") or {}).get("roc_auc"),
                "relbench_report": {k: v for k, v in data.items() if k != "scan"}}
    if step == "arm-mle":
        reports = sorted(run_dir.glob("fetched/bench/tmp/mle/*/final_report.json"))
        if len(reports) != 1:
            raise FileNotFoundError(f"{run_dir}: expected one MLE final report, found {len(reports)}")
        data = _read_json(reports[0])
        private = data.get("private_evaluation") or {}
        return {"mle_log_loss": private.get("score"), "mle_medal": private.get("medal"), "mle_report": private, "error": data.get("error")}
    if step in ("arm-ioai", "swap-kaggle", "swap-ioai"):
        results = sorted(run_dir.glob("fetched/bench/runs/*/results.json"))
        if len(results) != 1:
            raise FileNotFoundError(f"{run_dir}: expected one IOAI results.json, found {len(results)}")
        data = _read_json(results[0])
        final = data.get("final") or {}
        best = final.get("best") or {}
        public = best.get("publicScore")
        submissions = final.get("submissions") or []
        return {
            "ioai_public_score": float(public) if public not in (None, "") else None,
            "ioai_submissions": len(submissions),
            # A submission without the procedure's token in its message went around the procedure.
            "shell_submits": sum(1 for s in submissions if "[kapso-" not in str(s.get("description") or "")),
            "ioai_final": final, "delivered": data.get("solution", {}).get("score"),
            # A score with no delivered candidate is not what the step's bar means.
            "ioai_candidate_delivered": int(data.get("solution", {}).get("branch") is not None),
            "stopped_reason": data.get("solution", {}).get("stopped_reason"),
            "campaign_cost_usd": data.get("solution", {}).get("cost_usd"),
        }
    raise ValueError(f"no score reader for step {step}")


def build_step(step: str, run_id: str, record_dir: Path) -> Dict[str, Any]:
    run_dir = RUNS / run_id
    if not run_dir.is_dir():
        raise FileNotFoundError(f"{step}: no run directory {run_dir}")
    log = run_dir / "arm.log"
    stamps = _stamps(log)
    if "launch" not in stamps or "fetch" not in stamps:
        raise ValueError(f"{step}: {log} has no launch and fetch stamps")
    minutes = round((stamps["fetch"] - stamps["launch"]).total_seconds() / 60, 1)
    campaign = _campaign_dir(run_dir)
    launch = _read_json(campaign / ".kapso" / "launch.json")
    metrics = {**_score(step, run_dir), **_session_facts(campaign), **_served(campaign), **_machine_bill(log)}
    harness = launch.get("harness") or {}
    artifacts = [
        str(Path("..") / run_id / "arm.log"),
        str(Path("..") / run_id / campaign.relative_to(run_dir) / ".kapso" / "launch.json"),
    ]
    return {
        "name": step, "kind": "build", "minutes": minutes, "completed": not metrics.get("error"),
        "artifacts": artifacts, "metrics": metrics,
        "notes": [f"run {run_id}; harness {harness.get('name')} {harness.get('version')} ({str(harness.get('hash'))[:12]})"],
    }


def scan_step() -> Dict[str, Any]:
    started = datetime.now(timezone.utc)
    hits = {root.name: [str(f) for f in scan(root, vocabulary())] for root in sorted(BUNDLED_ROOT.iterdir()) if (root / "harness.yaml").is_file()}
    minutes = round((datetime.now(timezone.utc) - started).total_seconds() / 60, 2)
    total = sum(len(v) for v in hits.values())
    return {"name": "scan", "kind": "shell", "minutes": minutes, "completed": True, "artifacts": [],
            "metrics": {"scan_hits": total, "hits": hits}, "notes": [f"{len(hits)} harnesses scanned live at re-derivation"]}


def harness_edits(pins: Dict[str, str]) -> int:
    return sum(1 for name, pinned in pins.items() if harness_hash(BUNDLED_ROOT / name) != pinned)


def rederive(record_dir: Path) -> Dict[str, Any]:
    arms = _read_json(record_dir / "arms.json")
    steps: List[Dict[str, Any]] = [scan_step()]
    for step in STEP_NAMES[1:]:
        run_id = arms["runs"].get(step)
        if run_id is None:
            steps.append({"name": step, "deferred": "not run yet"})
        else:
            steps.append(build_step(step, run_id, record_dir))
    by_name = {s["name"]: s for s in steps if not s.get("deferred")}
    metrics: Dict[str, Any] = {
        "scan_hits": by_name["scan"]["metrics"]["scan_hits"],
        "harness_edits": harness_edits(arms["harness_pins"]),
    }
    for key, step in (("relbench_test_auroc", "arm-relbench"), ("mle_log_loss", "arm-mle"), ("ale_rating", "arm-ale")):
        if step in by_name:
            metrics[key] = by_name[step]["metrics"].get(key)
    if "arm-ioai" in by_name:
        score = by_name["arm-ioai"]["metrics"].get("ioai_public_score")
        metrics["ioai_public_score_above_median"] = int(score is not None and score > float(arms["ioai_median"]))
        metrics["ioai_shell_submits"] = by_name["arm-ioai"]["metrics"]["shell_submits"]
        metrics["ioai_candidate_delivered"] = by_name["arm-ioai"]["metrics"]["ioai_candidate_delivered"]
    stamps = [s for s in steps if not s.get("deferred")]
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return {
        "test": TEST, "host": HOST, "machine": "GCP benchmark machines (benchmark_machine.sh), one per arm",
        "run_id": f"{TEST}-{HOST}-{record_dir.name}", "advisory": None, "advisory_dimensions": None,
        "package": {"version": arms.get("version", "0.8.0.dev1"), "wheel_sha256": arms["wheel_sha256"]},
        "pins": {"suite_sha256": hashlib.sha256(report.SUITE_PATH.read_bytes()).hexdigest(), "wheel_sha256": arms["wheel_sha256"], **{f"harness_{k}": v for k, v in arms["harness_pins"].items()}},
        "user": {"kind": "scripted"},
        "started": arms.get("started", now), "finished": now,
        "steps": steps, "metrics": metrics, "judge": None,
        "notes": [f"re-derived {now} from the arm archives under scripts/redesign/runs/; {len(stamps)} of {len(STEP_NAMES)} steps run"]
        + [str(note) for note in arms.get("notes", [])],
        "transcripts": [],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--rederive", action="store_true", required=True)
    parser.add_argument("--record", type=Path, default=RUNS / "s3-1")
    args = parser.parse_args()
    record = rederive(args.record)
    record_path = args.record / "record.json"
    record_path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    out = REPORTS / f"{args.record.name}.md"
    out.write_text(report.render(record, report.load_suite(), args.record), encoding="utf-8")
    verdict = report.verdict(record, report.load_suite(), args.record)
    print(f"{record_path} -> {out}: exit {verdict['exit']}; steps {verdict['steps']}; bars {verdict['bars']}")
    sys.exit(verdict["exit"])


if __name__ == "__main__":
    main()
