#!/usr/bin/env python3
"""Kaggle code-competition runner (IOAI AI Models Track practice tasks).

Runs the Kapso campaign on build() against a prepared run root (see
preflight.py), then reads the ground truth from the Kaggle leaderboard: best
publicScore among submissions made during the run window, plus a static
audit of the kernels' sources for external-resource violations.

Usage:
    python -m benchmarks.ioai2026.runner --root /path/to/run_root --hours 2
    python -m benchmarks.ioai2026.runner --root /path/to/run_root --final-eval-only

The run root's `task/` holds the preflight's statement and data; the runner
writes the contest root beside them (`task/contest_root/`: the descriptor
`contest.json`, the submission procedure, the ticket office and its limits,
the organizers' rules) and passes it as the build's data, so every session's
`kapso_datasets/` carries the harness's conventions; the ledger and the
ticket office's state live in the contest root, shared by every lane.
"""

import argparse
import csv
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
from typing import Dict, Optional

import yaml
from dotenv import load_dotenv

from kapso.core.config import read_yaml
from kapso.handles import Budget, Solution
from kapso.kapso import Kapso

from benchmarks.ioai2026 import kernel_slots
from benchmarks.ioai2026.context import PROCEDURE, build_brief
from benchmarks.ioai2026.data.generic_eval.evaluate import list_submissions, normalize_status
from benchmarks.ioai2026.submit import classify_submit_output

load_dotenv()

BENCH_DIR = Path(__file__).resolve().parent
CONFIG_PATH = str(BENCH_DIR / "config.yaml")
RULES_NAME = "RULES.md"             # the task's binding rules, pinned by the preflight
SLOTS_PATH = str(BENCH_DIR / "kernel_slots.py")
SUBMIT_PATH = str(BENCH_DIR / "submit.py")
EVALUATION_SUITE = BENCH_DIR / "data" / "generic_eval"
BUNDLED_HARNESS = "competitive-programming"
CONTEST_ROOT = "contest_root"
LEDGER = "submissions.json"

# Source patterns that indicate the kernel pulls external pretrained
# resources or data. Matches are reported, not silently fatal — a human
# reads the flagged lines before trusting (or zeroing) the score.
AUDIT_PATTERNS = [
    r"hf_hub_download",
    r"snapshot_download",
    r"torch\.hub",
    r"\btimm\b",
    r"load_dataset",
    r"https?://",
    r"from_pretrained\(\s*[\"'](?!\.|/kaggle/input|model|dataset/model)",
]


def shape_session_timeouts(config: dict, total_run_seconds: float) -> dict:
    """Per-session ceilings, bounded only by the run itself.

    There is deliberately no per-phase fraction: a phase sub-budget starved
    ideation (a member delivered 1 of 5 candidates, the selector timed out and
    the pool went unranked) while the sessions still had run budget left. The
    single enforcer is the strategy's dynamic clamp against the searchable
    budget that remains — so a session that finishes early hands its unused
    time to the next phase instead of forfeiting it.
    """
    params = config["search_strategy"]["params"]
    return {
        "ideation_timeout": int(min(
            params["ideation"]["timeout"], total_run_seconds)),
        "implementation_timeout": int(min(
            params["implementation"]["timeout"], total_run_seconds)),
    }


def build_runtime_config(task_dir: str, session_timeouts: dict,
                         shared_cache_dir: "str | None" = None,
                         node_expansion: "int | None" = None) -> str:
    """Write the per-run override file: this benchmark's own file with the
    shaped session deadlines (and the lanes) over it."""
    config = read_yaml(CONFIG_PATH)
    params = config["search_strategy"]["params"]
    params["ideation"]["timeout"] = session_timeouts["ideation_timeout"]
    params["implementation"]["timeout"] = session_timeouts["implementation_timeout"]
    if shared_cache_dir:
        params["shared_cache_dir"] = os.path.abspath(shared_cache_dir)
    if node_expansion and node_expansion > 1:
        params["node_expansion_value"] = node_expansion
        params["expansion_lane_env"] = [
            {"CUDA_VISIBLE_DEVICES": str(i)} for i in range(node_expansion)
        ]
    runtime_dir = os.path.join(task_dir, ".kapso_runtime")
    os.makedirs(runtime_dir, exist_ok=True)
    runtime_path = os.path.join(runtime_dir, "config.yaml")
    with open(runtime_path, "w") as f:
        yaml.safe_dump(config, f, sort_keys=False)
    return runtime_path


def stage_contest_root(task_dir: str, competition: str, higher_is_better: bool,
                       window: tuple, kernel_slots_limits: dict, listing: dict, fresh: bool) -> str:
    """The contest root: the descriptor (the competition, the ledger, the
    procedure, the metric's direction, the campaign window's start and end,
    the submissions listing's page size and timeout), the procedure, the
    ticket office with its limits, and the task's binding rules — the
    preflight's pinned copy under the task. A new campaign (`fresh`) starts
    the two ledgers afresh: a submission of an earlier launch is not this
    campaign's insurance, and a stale ticket ledger holds phantom tickets.
    A resume keeps them: they are the campaign's state."""
    root = os.path.join(task_dir, CONTEST_ROOT)
    os.makedirs(root, exist_ok=True)
    shutil.copy2(SUBMIT_PATH, os.path.join(root, "submit.py"))
    shutil.copy2(SLOTS_PATH, os.path.join(root, "kernel_slots.py"))
    shutil.copy2(os.path.join(task_dir, RULES_NAME), os.path.join(root, RULES_NAME))
    with open(os.path.join(root, kernel_slots.CONFIG_NAME), "w") as f:
        json.dump({**kernel_slots_limits, "higher_is_better": higher_is_better}, f, indent=2)
    if fresh:
        for stale_ledger in (os.path.join(root, kernel_slots.LEDGER_NAME), os.path.join(root, LEDGER)):
            if os.path.isfile(stale_ledger):
                os.remove(stale_ledger)
    with open(os.path.join(root, "contest.json"), "w") as f:
        json.dump({
            "competition": competition,
            "ledger": os.path.join(root, LEDGER),
            "procedure": PROCEDURE,
            "higher_is_better": higher_is_better,
            "window_start": window[0],
            "window_end": window[1],
            "shared_root": root,
            "list_page_size": int(listing["submissions_page_size"]),
            "list_timeout_seconds": int(listing["timeout_seconds"]),
        }, f, indent=2)
    return root


def audit_kernel(kernel_dir: str) -> list:
    """Static scan of the kernel sources for external-resource pulls."""
    findings = []
    for dirpath, _, filenames in os.walk(kernel_dir):
        for name in filenames:
            if not name.endswith(".py"):
                continue
            path = os.path.join(dirpath, name)
            with open(path, encoding="utf-8") as f:
                for lineno, line in enumerate(f, 1):
                    for pattern in AUDIT_PATTERNS:
                        if re.search(pattern, line):
                            findings.append(
                                f"{os.path.relpath(path, kernel_dir)}:"
                                f"{lineno}: [{pattern}] {line.strip()}"
                            )
    return findings


def best_public_score(submissions: list, since_utc_iso: str, until_utc_iso: str,
                      higher_is_better: bool) -> dict:
    """The best public score in the metric's direction among the
    submissions dated inside the window; a submission's status is the
    CLI's word (complete, error, pending)."""
    since_key = since_utc_iso.replace("T", " ")[:19]
    until_key = until_utc_iso.replace("T", " ")[:19]
    considered, best = [], None
    for sub in submissions:
        date_key = str(sub.get("date", "")).replace("T", " ")[:19]
        if not since_key <= date_key <= until_key:
            continue
        raw_score = str(sub.get("publicScore", "") or "").strip()
        entry = {
            "date": date_key,
            "status": normalize_status(sub.get("status")),
            "description": str(sub.get("description", "")),
            "publicScore": raw_score,
        }
        considered.append(entry)
        if re.fullmatch(r"-?\d+(\.\d+)?", raw_score):
            score = float(raw_score)
            if best is None or (score > best["score"] if higher_is_better else score < best["score"]):
                best = {"score": score, **entry}
    return {"best": best, "submissions": considered}


def kernel_metadata_dirs(task_dir: str) -> list:
    """Every kernel folder under the run's task directory (the lanes' session
    clones included), by its kernel-metadata.json."""
    found = []
    for dirpath, dirnames, filenames in os.walk(task_dir):
        dirnames[:] = [name for name in dirnames if name != ".git"]
        if "kernel-metadata.json" in filenames:
            found.append(dirpath)
    return sorted(found)


def discover_run_kernels(task_dir: str) -> list:
    """Kernel refs this run pushed, read from the lanes' kernel-metadata.json.

    K-way lanes keep their own kernel folders, so there is no single
    canonical kernel path to look in; the metadata files each lane wrote
    are the authoritative record of what this run created.
    """
    refs = []
    for folder in kernel_metadata_dirs(task_dir):
        meta_path = os.path.join(folder, "kernel-metadata.json")
        with open(meta_path, encoding="utf-8") as f:
            meta = json.load(f)
        if not meta.get("id"):
            raise ValueError(f"{meta_path} has no 'id' field")
        refs.append(meta["id"])
    return sorted(set(refs))


def kernels_run_since(kaggle_bin: str, since_utc_iso: str, page_size: int,
                      timeout_seconds: int) -> list:
    """Our own kernels whose last run started at/after the campaign did.

    Local metadata alone is not enough: a lane can push a kernel and never
    record it (run 3's lane 3 did exactly that, leaving a COMPLETE kernel
    discoverable only from the account listing).
    """
    proc = subprocess.run(
        [kaggle_bin, "kernels", "list", "-m", "--sort-by", "dateRun",
         "--page-size", str(page_size), "--format", "json"],
        capture_output=True, text=True, timeout=timeout_seconds,
    )
    if proc.returncode != 0:
        raise RuntimeError(
            f"kaggle kernels list exited {proc.returncode}: {proc.stderr[-500:]}")
    if proc.stdout.strip() == "Not found":
        # The CLI's empty-state for an account with no kernels (exit 0,
        # non-JSON) — a real possibility on a fresh account after a
        # zero-push run, not a corrupt payload.
        return []
    since_key = since_utc_iso.replace("T", " ")[:19]
    return sorted(
        entry["ref"] for entry in json.loads(proc.stdout)
        if str(entry.get("lastRunTime", "")).replace("T", " ")[:19] >= since_key
    )


def kernel_status(kaggle_bin: str, ref: str, timeout_seconds: int) -> str:
    """KernelWorkerStatus for a kernel ref (COMPLETE / RUNNING / ...)."""
    proc = subprocess.run(
        [kaggle_bin, "kernels", "status", ref],
        capture_output=True, text=True, timeout=timeout_seconds,
    )
    match = re.search(r"KernelWorkerStatus\.([A-Z_]+)", proc.stdout + proc.stderr)
    return match.group(1) if match else "UNKNOWN"


def submission_matches_template(candidate_path: str, template_path: str) -> bool:
    """Same header, row count and id column (in order) as the sample file."""
    with open(template_path, newline="", encoding="utf-8") as f:
        template = list(csv.reader(f))
    with open(candidate_path, newline="", encoding="utf-8") as f:
        candidate = list(csv.reader(f))
    if len(candidate) != len(template) or candidate[0] != template[0]:
        return False
    return all(c[0] == t[0] for c, t in zip(candidate[1:], template[1:]))


def submit_kernel_output(kaggle_bin: str, competition: str, ref: str,
                         message: str, max_version: int,
                         timeout_seconds: int) -> tuple:
    """Submit the NEWEST submittable version; (version|None, attempt log).

    `-v` is mandatory for code competitions and the CLI exposes the version
    nowhere (neither `kernels list --format json` nor `kernels status` carries
    it), so the version is discovered by probing. The probe runs DOWNWARD:
    upward would stop at the oldest submittable version instead of the newest.
    Every attempt's output is kept — run 5 lost six kernels to rejections
    whose stderr was discarded, leaving only "no version took" behind.
    """
    attempts = []
    for version in range(max_version, 0, -1):
        proc = subprocess.run(
            [kaggle_bin, "competitions", "submit", "-c", competition,
             "-k", ref, "-v", str(version), "-f", "submission.csv",
             "-m", message],
            capture_output=True, text=True, timeout=timeout_seconds,
        )
        verdict = classify_submit_output(proc.stdout, proc.stderr)
        attempts.append({"version": version, "verdict": verdict,
                         "output": (proc.stdout + proc.stderr).strip()})
        if verdict in ("accepted", "pending"):
            return version, attempts          # pending: made, to be settled from the list
    return None, attempts


def banked_kernel_refs(ledger_path: str) -> set:
    """Kernel refs with a public score in the submissions ledger: what makes
    never-scored kernels computable. No ledger means nothing banked."""
    if not os.path.isfile(ledger_path):
        return set()
    with open(ledger_path, encoding="utf-8") as f:
        ledger = json.load(f)
    return {
        entry["kernel_ref"] for entry in ledger["submissions"]
        if entry.get("kernel_ref") and isinstance(entry.get("public_score"), (int, float))
    }


def rank_harvest_candidates(refs: list, banked: set) -> list:
    """Never-scored kernels first — alphabet cost run 5 two lanes' scores.

    A kernel with no banked score is one submission away from turning finished
    work into leaderboard value; a banked one only offers a stochastic re-roll
    (scoring re-runs the kernel). Stable within each group.
    """
    return ([r for r in refs if r not in banked]
            + [r for r in refs if r in banked])


def harvest_unsubmitted_kernels(root: str, competition: str,
                                run_started_utc: str,
                                final_eval_cfg: dict) -> dict:
    """Submit every COMPLETE kernel this run pushed, before reading scores.

    A kernel and its output live on Kaggle independently of the run box, so a
    campaign that ends before firing `competitions submit` has still produced a
    scoreable artifact — run 2 left one worth 0.83626 unshipped. Duplicate
    submissions are harmless (Kaggle scores best-of) and attributing a past
    submission to a kernel is not possible from the API, so candidates are
    deduped by output content alone rather than by guessing what was already
    sent.
    """
    timeout_seconds = final_eval_cfg["timeout_seconds"]
    task_dir = os.path.join(root, "task")
    kaggle_bin = shutil.which("kaggle")
    if not kaggle_bin:
        raise FileNotFoundError("kaggle CLI not on PATH — cannot harvest")

    refs = sorted(set(discover_run_kernels(task_dir)) | set(kernels_run_since(
        kaggle_bin, run_started_utc,
        final_eval_cfg["harvest_kernel_list_size"], timeout_seconds)))
    report = {"kernels_found": len(refs), "submitted": [], "skipped": []}
    if not refs:
        # Not every task is a code competition; one scored from an uploaded
        # file pushes no kernels, and there is nothing here to ship. Returning
        # empty keeps the leaderboard readout alive for those tasks.
        print("[harvest] no kernels from this run — nothing to harvest")
        return report

    # The sample file's directory varies per competition (timed-deps nests it
    # under dataset/archive/ — that fixed-path raise killed two runs' entire
    # leaderboard readouts). Search for it; without a template the candidates
    # are skipped loudly below, but the readout always survives.
    template_name = final_eval_cfg["submission_template"]
    template_matches = sorted(Path(task_dir, "dataset").rglob(template_name))
    template = str(template_matches[0]) if template_matches else None
    if template is None:
        print(f"[harvest] no {template_name} under dataset/ — "
              f"{len(refs)} kernels skipped unvalidated")
        report["skipped"] = [
            {"kernel": ref, "reason": f"no {template_name} template found"}
            for ref in refs
        ]
        return report
    workdir = os.path.join(root, ".harvest")
    seen_digests = {}

    # Never-scored kernels first: run 5 spent both scoring slots re-rolling
    # already-scored kernels (alphabetical order) while two unscored ones —
    # finished work one submission away from value — were bounced.
    refs = rank_harvest_candidates(refs, banked_kernel_refs(os.path.join(task_dir, CONTEST_ROOT, LEDGER)))

    # Gate every candidate down to something submittable before spending a
    # submission on it.
    ready = []
    for ref in refs:
        status = kernel_status(kaggle_bin, ref, timeout_seconds)
        if status != "COMPLETE":
            report["skipped"].append({"kernel": ref, "reason": f"status {status}"})
            continue
        dest = os.path.join(workdir, ref.replace("/", "__"))
        os.makedirs(dest, exist_ok=True)
        subprocess.run(
            [kaggle_bin, "kernels", "output", ref, "-p", dest, "--force"],
            capture_output=True, text=True, timeout=timeout_seconds,
        )
        produced = os.path.join(dest, "submission.csv")
        if not os.path.isfile(produced):
            report["skipped"].append({"kernel": ref, "reason": "no submission.csv"})
            continue
        if not submission_matches_template(produced, template):
            report["skipped"].append({"kernel": ref, "reason": "shape mismatch"})
            continue
        with open(produced, "rb") as f:
            digest = hashlib.sha256(f.read()).hexdigest()
        if digest in seen_digests:
            report["skipped"].append(
                {"kernel": ref, "reason": f"identical to {seen_digests[digest]}"})
            continue
        seen_digests[digest] = ref
        ready.append(ref)

    # Submit everything ready IMMEDIATELY. A code submission's scoring re-run
    # executes on Kaggle's backend scoring infrastructure, not in the
    # account's interactive session pool (contest 1, 2026-08-04: five
    # submissions scoring concurrently, zero rejections) — so submits are
    # never serialized behind slots. All candidates go out back-to-back with
    # in-window timestamps; the rest of the budget just polls for scores.
    deadline = time.time() + final_eval_cfg["harvest_budget_seconds"]
    poll_seconds = final_eval_cfg["harvest_poll_seconds"]
    retry_seconds = final_eval_cfg["harvest_retry_seconds"]
    pending = []          # [{kernel, version, submitted_at}]
    retried = set()

    def poll_scored():
        """Record harvest submissions that finished scoring."""
        rows = list_submissions(kaggle_bin, competition, final_eval_cfg["submissions_page_size"],
                                timeout_seconds)
        still = []
        for entry in pending:
            # Window by date: a previous run's harvest used the same message
            # for the same slug, and its scored row must not satisfy this one.
            since = datetime.fromtimestamp(
                entry["submitted_at"] - 60, timezone.utc
            ).strftime("%Y-%m-%d %H:%M:%S")
            row = next(
                (r for r in rows
                 if entry["kernel"].split("/")[-1] in str(r.get("description", ""))
                 and str(r.get("date", ""))[:19] >= since
                 and normalize_status(r.get("status")) != "pending"), None)
            if row is None:
                still.append(entry)
                continue
            entry["publicScore"] = str(row.get("publicScore", ""))
            report["submitted"].append(entry)
        pending[:] = still

    while ready and time.time() < deadline:
        ref = ready.pop(0)
        version, attempts = submit_kernel_output(
            kaggle_bin, competition, ref,
            f"harvest: {ref.split('/')[-1]} (pushed by the run, not submitted)",
            final_eval_cfg["harvest_max_kernel_version"], timeout_seconds,
        )
        if version is None:
            if ref not in retried and time.time() + retry_seconds < deadline:
                # A rejection of every version can be a transient blip;
                # one paced retry before giving up.
                retried.add(ref)
                ready.append(ref)
                print(f"[harvest] {ref}: all versions rejected — "
                      f"retrying once after {retry_seconds}s")
                time.sleep(retry_seconds)
            else:
                report["skipped"].append(
                    {"kernel": ref, "reason": "no version took",
                     "attempts": attempts})
            continue
        pending.append({"kernel": ref, "version": version,
                        "submitted_at": time.time()})
    for leftover in ready:
        report["skipped"].append(
            {"kernel": leftover, "reason": "harvest budget exhausted"})

    while pending and time.time() < deadline:
        time.sleep(min(poll_seconds, max(0.0, deadline - time.time())))
        poll_scored()

    poll_scored()
    for entry in pending:
        # Budget ran out mid-scoring: the submission is in flight and counts.
        entry["publicScore"] = ""
        report["submitted"].append(entry)

    print(f"[harvest] kernels={report['kernels_found']} "
          f"submitted={len(report['submitted'])} skipped={len(report['skipped'])}")
    return report


def run_final_eval(root: str, competition: str, higher_is_better: bool, final_eval_cfg: dict) -> dict:
    """Read the leaderboard truth: the best public score in the metric's
    direction among the submissions dated inside the run window, read from
    every page of the competition's list at the time the report says."""
    timeout_seconds = final_eval_cfg["timeout_seconds"]
    meta_path = os.path.join(root, "run_meta.json")
    if not os.path.isfile(meta_path):
        raise FileNotFoundError(
            f"{meta_path} missing — the campaign runner writes it at launch"
        )
    with open(meta_path) as f:
        meta = json.load(f)
    run_started, window_end = meta["run_started_utc"], meta["window_end_utc"]

    kaggle_bin = shutil.which("kaggle")
    if not kaggle_bin:
        raise FileNotFoundError("kaggle CLI not on PATH — cannot read scores")

    # Ship before reading: a kernel left unsubmitted scores nothing, and the
    # harvested entries must be in flight before the leaderboard is polled.
    harvest = None
    if final_eval_cfg["harvest_unsubmitted"]:
        # The harvest waits for its own scores inside its budget, so the
        # leaderboard is read immediately after it returns.
        harvest = harvest_unsubmitted_kernels(
            root, competition, run_started, final_eval_cfg)

    rows = list_submissions(kaggle_bin, competition, final_eval_cfg["submissions_page_size"], timeout_seconds)
    report = best_public_score(rows, run_started, window_end, higher_is_better)
    report["window"] = {"start": run_started, "end": window_end}
    report["read_at"] = datetime.now(timezone.utc).isoformat()
    task_dir = os.path.join(root, "task")
    report["audit"] = {
        os.path.relpath(folder, task_dir): audit_kernel(folder)
        for folder in kernel_metadata_dirs(task_dir)
    }
    if harvest is not None:
        report["harvest"] = harvest
    return report


def solution_summary(solution: Solution) -> Dict[str, object]:
    return {
        "campaign": str(solution.campaign),
        "branch": solution.branch,
        "commit": solution.commit,
        "score": solution.score,
        "stopped_reason": solution.stopped_reason,
        "experiments": solution.experiments_total,
        "cost_usd": solution.cost_usd,
        "harness": solution.harness.name if solution.harness else None,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Run Kapso on a Kaggle code competition")
    parser.add_argument("--root", required=True,
                        help="Run root from preflight.py")
    parser.add_argument("--hours", type=float, default=None,
                        help="Run wall-clock hours (default: config run_defaults.hours)")
    parser.add_argument("--guard-minutes", type=int, default=None)
    parser.add_argument("--iterations", type=int, default=None,
                        help="Budget.experiments (default: config run_defaults.iterations)")
    parser.add_argument("--coding-agent", default=None,
                        help="The host every role without a cli of its own runs on "
                             "(default: the config's search_strategy.params.host, codex here)")
    parser.add_argument("--harness", default=None,
                        help=f"A harness reference (default: the bundled {BUNDLED_HARNESS})")
    parser.add_argument("--experience", default=None,
                        help="Comma-separated sources to serve: mine, a bank path or git reference, an index name")
    parser.add_argument("--cost-budget", type=float, default=None)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--skip-final-eval", action="store_true")
    parser.add_argument("--final-eval-only", action="store_true")
    parser.add_argument("--node-expansion", type=int, default=None,
                        help="K parallel implementation lanes per round "
                             "(default: config run_defaults.node_expansion)")
    parser.add_argument("--shared-cache-dir", default=None)
    args = parser.parse_args()

    root = os.path.abspath(args.root)
    task_dir = os.path.join(root, "task")
    statement_path = os.path.join(task_dir, "dataset", "statement.md")
    kaggle_meta_path = os.path.join(task_dir, "kaggle.json")
    rules_path = os.path.join(task_dir, RULES_NAME)
    for required in (statement_path, kaggle_meta_path, rules_path):
        if not os.path.isfile(required):
            sys.exit(f"{required} missing — run preflight.py first")
    with open(kaggle_meta_path) as f:
        kaggle_meta = json.load(f)
    competition = kaggle_meta["competition"]
    higher_is_better = bool(kaggle_meta["higher_is_better"])

    config = read_yaml(CONFIG_PATH)
    mode_cfg = config["benchmark"]

    if args.final_eval_only:
        report = run_final_eval(root, competition, higher_is_better, mode_cfg["final_eval"])
        results_path = os.path.join(root, "results.json")
        with open(results_path, "w") as f:
            json.dump(report, f, indent=2)
        print(json.dumps(report, indent=2))
        return

    statement = open(statement_path, encoding="utf-8").read()
    run_defaults = mode_cfg["run_defaults"]
    hours = args.hours if args.hours is not None else run_defaults["hours"]
    iterations = args.iterations if args.iterations is not None else run_defaults["iterations"]
    node_expansion = (args.node_expansion if args.node_expansion is not None
                      else run_defaults["node_expansion"])

    total_run_seconds = hours * 3600
    # The clock starts at URL-in, not here: the preflight stamps run_meta.json
    # before it downloads, so its ~8 min is billed to the run rather than being
    # free time ahead of it (a real competition's window opens once, and the
    # download and statement authoring happen inside it). Direct runner
    # invocations with no preflight stamp start their clock now.
    meta_path = os.path.join(root, "run_meta.json")
    if os.path.isfile(meta_path):
        with open(meta_path) as f:
            started_utc = json.load(f)["run_started_utc"]
        origin_ts = datetime.fromisoformat(started_utc).timestamp()
    else:
        origin_ts = time.time()
        started_utc = datetime.fromtimestamp(origin_ts, timezone.utc).isoformat()

    deadline_ts = origin_ts + total_run_seconds
    window_end_utc = datetime.fromtimestamp(deadline_ts, timezone.utc).isoformat()
    with open(meta_path, "w") as f:
        json.dump({"run_started_utc": started_utc, "window_end_utc": window_end_utc}, f, indent=2)
    spent_minutes = (time.time() - origin_ts) / 60
    knobs = mode_cfg["session_budget"]
    guard_minutes = (args.guard_minutes if args.guard_minutes is not None
                     else knobs["guard_minutes"])
    # The campaign returns early enough for the harvest's submissions to be
    # SCORED before the deadline, not merely sent: a submission counts only if
    # it finished scoring in time, so a sweep that fires at the buzzer produces
    # entries that never reach the leaderboard. The harvest only submits
    # already-COMPLETE kernels, so this window covers the submit calls plus
    # Kaggle's scoring latency — not another kernel run.
    harvest_window = knobs["harvest_window_minutes"]
    budget_minutes = int(
        hours * 60 - spent_minutes - guard_minutes - harvest_window
    )
    if budget_minutes < knobs["min_campaign_minutes"]:
        sys.exit(
            f"only {budget_minutes} min of the {hours}h budget remain after "
            f"{spent_minutes:.1f} min of preflight — below the "
            f"{knobs['min_campaign_minutes']} min floor; nothing scoreable "
            "could finish"
        )
    # Sized to ONE submission round trip (push -> kernel run -> submit ->
    # score), not to a fraction of the run: a campaign that ends before
    # shipping scores nothing.
    reserve_minutes = knobs["finalization_reserve_minutes"]
    session_timeouts = shape_session_timeouts(config, budget_minutes * 60)

    if not shutil.which("kaggle"):
        print("WARNING: kaggle CLI not on PATH — submissions will fail")

    shared_cache_dir = args.shared_cache_dir or os.path.join(task_dir, "shared_cache")
    os.makedirs(shared_cache_dir, exist_ok=True)
    config_path = build_runtime_config(task_dir, session_timeouts,
                                       shared_cache_dir=shared_cache_dir,
                                       node_expansion=node_expansion)

    # Lanes plan against the CAMPAIGN's end, not the full window: the guard
    # and harvest carve-outs come after their deadline, and a lane aiming its
    # last submission at the outer deadline would be cut mid-flight.
    campaign_deadline_ts = deadline_ts - (guard_minutes + harvest_window) * 60
    campaign_deadline_utc = datetime.fromtimestamp(campaign_deadline_ts, timezone.utc).isoformat()

    contest_root = stage_contest_root(task_dir, competition, higher_is_better, (started_utc, window_end_utc),
                                      knobs["kernel_slots"], mode_cfg["final_eval"], fresh=not args.resume)
    artifacts_dir = os.path.join(task_dir, "artifacts")
    os.makedirs(artifacts_dir, exist_ok=True)
    brief = build_brief(
        statement=statement, competition=competition, higher_is_better=higher_is_better,
        dataset_dir=Path(task_dir, "dataset"), artifacts_dir=Path(artifacts_dir),
        deadline_utc=campaign_deadline_utc, ledger_path=Path(contest_root, LEDGER),
        shared_root=Path(contest_root), pool_limits=knobs["kernel_slots"],
        rules_text=open(rules_path, encoding="utf-8").read(), shared_cache_dir=Path(shared_cache_dir),
    )

    print(f"root={root} competition={competition} K={node_expansion} hours={hours}")
    print(f"clock started {spent_minutes:.1f} min ago (preflight); campaign "
          f"deadline {datetime.fromtimestamp(campaign_deadline_ts, timezone.utc):%H:%M:%S}"
          f" UTC, window ends "
          f"{datetime.fromtimestamp(deadline_ts, timezone.utc):%H:%M:%S} UTC")
    print(f"budget={budget_minutes} min (guard={guard_minutes} min, "
          f"harvest window={harvest_window} min, "
          f"finalization reserve={reserve_minutes:.0f} min), "
          f"iterations<={iterations}")
    print(f"session caps: ideation={session_timeouts['ideation_timeout']}s "
          f"implementation={session_timeouts['implementation_timeout']}s")

    signal.signal(signal.SIGTERM, lambda *_: sys.exit(143))

    kapso = Kapso(config=config_path)
    kapso.load_harness(args.harness or BUNDLED_HARNESS)
    for reference in (args.experience or "").split(","):
        if reference.strip():
            kapso.load_experience(reference.strip())
    budget = Budget(
        minutes=budget_minutes,
        experiments=iterations,
        usd=args.cost_budget,
        reserve_minutes=reserve_minutes if reserve_minutes > 0 else None,
    )
    solution = kapso.build(
        brief,
        evaluation=str(EVALUATION_SUITE),
        data=contest_root,
        output=os.path.join(task_dir, "kapso_campaign"),
        budget=budget,
        resume=args.resume,
        coding_agent=args.coding_agent,
    )
    print("\n=== campaign done ===")

    summary: Dict[str, object] = {
        "root": root,
        "hours": hours,
        "competition": competition,
        "solution": solution_summary(solution),
    }
    # The campaign's record first: a final evaluation that fails loud (the
    # listing refused) must not take the delivery's summary with it.
    results_path = os.path.join(root, "results.json")
    with open(results_path, "w") as f:
        json.dump(summary, f, indent=2)
    if not args.skip_final_eval:
        summary["final"] = run_final_eval(
            root, competition, higher_is_better, mode_cfg["final_eval"])
        with open(results_path, "w") as f:
            json.dump(summary, f, indent=2)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
