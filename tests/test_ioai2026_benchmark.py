"""Contract tests for the Kaggle code-competition benchmark on build()
(docs/plans/redesign/wp8-harness-ports.md, change 14).

What must hold: the Brief is the preflight's statement plus the campaign's
facts and the organizers' rules; the contest root carries the harness's
conventions (the descriptor, the procedure, the ticket office, the rules);
the submission procedure submits and records; the provided evaluation
attributes the ledger to the candidate by content and reports scored,
pending, rejected, out-of-window and missing as distinct outcomes; the
runner's leaderboard parsing survives CLI pagination noise and windows
submissions to the run; the preflight's root is validated fail-loud.
"""

import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

import pytest
import yaml

from kapso.handles import Brief
from benchmarks.ioai2026 import kernel_slots
from benchmarks.ioai2026.context import PROCEDURE, build_brief
from benchmarks.ioai2026.preflight import RULES_PATH, SPEC_PATH, build_prompt, validate_root
from benchmarks.ioai2026.runner import (
    CONTEST_ROOT,
    EVALUATION_SUITE,
    LEDGER,
    SUBMIT_PATH,
    audit_kernel,
    banked_kernel_refs,
    best_public_score,
    classify_submit_output,
    discover_run_kernels,
    kernel_metadata_dirs,
    parse_submissions_json,
    rank_harvest_candidates,
    kernels_run_since,
    stage_contest_root,
    submission_matches_template,
)

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "benchmarks", "ioai2026", "config.yaml")

def test_the_override_file_makes_the_stop_vote_advisory():
    # A competition has no "goal achieved" — the radar rehearsal's judges
    # voted stop at 0.982/1.0 and ended the campaign 25 min early with an
    # upload unspent. The campaign clock is the only stop: the config key.
    with open(CONFIG_PATH) as f:
        params = yaml.safe_load(f)["search_strategy"]["params"]
    assert params["honor_agent_stop"] is False


def test_staged_rules_carry_the_binding_kernel_constraints():
    # The handler deliberately states no kernel mechanics, so RULES.md is the
    # only place the agent learns them: a trim that drops the one-GPU pin or the
    # never-P100 pin would silently void submissions that still score.
    rules = open(RULES_PATH, encoding="utf-8").read()
    assert "cuda:0" in rules
    assert "NvidiaTeslaT4" in rules and "P100" in rules
    assert "the task statement's number is the authority" in rules
    assert "is 50 per task" in rules
    assert "self-contained report docstring" in rules.replace("**", "")
    assert "THEY are the authority" in rules


def test_preflight_spec_authors_no_submit_mechanics():
    # S2 (run 5): the spec used to template the file-upload submit command,
    # the preflight copied it into a kernel task's statement, and six lanes
    # burned their first submission on a 400. The statement carries modality
    # and file shape only; CLI mechanics never come from preflight authorship.
    spec = open(SPEC_PATH, encoding="utf-8").read()
    assert "modality" in spec
    assert "dataset_sources" in spec        # starter attachments must be named
    assert "competitions submit" not in spec
    assert "kernels push" not in spec


def test_harvest_template_is_found_wherever_the_dataset_nests_it(tmp_path):
    # timed-deps competitions nest the sample under dataset/archive/; the old
    # fixed dataset/submission.csv raise killed two runs' whole leaderboard
    # readouts. The search must find it, and a truly absent template must
    # skip candidates rather than raise.
    import glob, os
    nested = tmp_path / "task" / "dataset" / "archive"
    nested.mkdir(parents=True)
    (nested / "submission.csv").write_text("path,target\n")
    matches = sorted(glob.glob(
        os.path.join(str(tmp_path / "task"), "dataset", "**", "submission.csv"),
        recursive=True))
    assert matches and matches[0].endswith(os.path.join("archive", "submission.csv"))


def test_parse_submissions_json_tolerates_pagination_noise():
    raw = (
        "Next Page Token = CfDJ8ABC\n"
        '[{"date": "2026-07-22 15:30:00", "status": "complete", '
        '"publicScore": "0.71", "description": "baseline"}]'
    )
    subs = parse_submissions_json(raw)
    assert subs[0]["publicScore"] == "0.71"
    with pytest.raises(ValueError, match="JSON payload"):
        parse_submissions_json("no brackets here")


def test_best_public_score_windows_to_run_start():
    submissions = [
        {"date": "2026-07-22 10:00:00", "status": "complete",
         "publicScore": "0.99", "description": "yesterday's run"},
        {"date": "2026-07-22 15:30:00", "status": "complete",
         "publicScore": "0.41", "description": "insurance"},
        {"date": "2026-07-22 16:10:00", "status": "complete",
         "publicScore": "0.78", "description": "distill"},
        {"date": "2026-07-22 16:40:00", "status": "pending",
         "publicScore": "", "description": "still scoring"},
    ]
    report = best_public_score(submissions, "2026-07-22T15:00:00+00:00")
    assert report["best"]["score"] == 0.78
    assert len(report["submissions"]) == 3  # pre-run entry excluded


def test_audit_kernel_flags_external_pulls(tmp_path):
    kernel = tmp_path / "kernel"
    kernel.mkdir()
    (kernel / "script.py").write_text(
        "from transformers import ASTForAudioClassification\n"
        "m = ASTForAudioClassification.from_pretrained('MIT/ast-finetuned')\n"
        "ok = ASTForAudioClassification.from_pretrained('/kaggle/input/x/model')\n"
    )
    findings = audit_kernel(str(kernel))
    assert len(findings) == 1 and "MIT/ast-finetuned" in findings[0]


def test_discover_run_kernels_finds_namespaced_lane_dirs(tmp_path):
    # K-way lanes namespace their submission dirs, so there is no single
    # canonical kernel path — discovery must walk them and dedupe.
    submission = tmp_path / "task" / "submission"
    for lane, ref in (("lane0_exp_0", "u/kernel-a"), ("lane2_exp_2", "u/kernel-b"),
                      ("lane5_exp_5", "u/kernel-a")):
        (submission / lane).mkdir(parents=True)
        (submission / lane / "kernel-metadata.json").write_text(
            json.dumps({"id": ref, "code_file": "script.py"}))
    assert discover_run_kernels(str(tmp_path / "task")) == ["u/kernel-a", "u/kernel-b"]
    (submission / "broken").mkdir()
    (submission / "broken" / "kernel-metadata.json").write_text('{"title": "x"}')
    with pytest.raises(ValueError, match="'id'"):
        discover_run_kernels(str(tmp_path / "task"))


def test_submission_matches_template_gates_on_ids_not_just_size(tmp_path):
    template = tmp_path / "template.csv"
    template.write_text("path,target\naudio/a.wav,0\naudio/b.wav,0\n")
    good = tmp_path / "good.csv"
    good.write_text("path,target\naudio/a.wav,17\naudio/b.wav,3\n")
    assert submission_matches_template(str(good), str(template))
    # right row count, wrong ids — the failure a length check would miss
    reordered = tmp_path / "reordered.csv"
    reordered.write_text("path,target\naudio/b.wav,3\naudio/a.wav,17\n")
    assert not submission_matches_template(str(reordered), str(template))
    short = tmp_path / "short.csv"
    short.write_text("path,target\naudio/a.wav,17\n")
    assert not submission_matches_template(str(short), str(template))


def make_slots_task(tmp_path, gpu=2, cpu=5, ttl=600, aging=900):
    task = tmp_path / "task"
    task.mkdir(exist_ok=True)
    (task / ".kernel_slots_config.json").write_text(json.dumps(
        {"gpu": gpu, "cpu": cpu, "ttl_seconds": ttl,
         "reap_interval_seconds": 60, "verify_timeout_seconds": 30,
         "aging_seconds": aging}))
    return str(task)


def bank(task, score, ref):
    with open(os.path.join(task, "best_score.log"), "a") as f:
        f.write(f"{score} 2026-08-03T21:00:00Z {ref} idea\n")


def grab_as(task, lane, ref, priority="run", waiter_id=None, now=None, kind="push"):
    return kernel_slots.poll_once(
        task, "gpu", kind, ref, lane, priority,
        waiter_id or f"w-{lane}-{ref[-6:]}", now if now is not None else time.time())


def test_queue_orders_by_banked_evidence_within_a_tier(tmp_path):
    # Grounded in the 2026-08-03 k=8 run: unscored lanes first (their first
    # score is maximum information), then best banked public score, then
    # arrival — and round 1 (nobody scored) stays byte-identical to FIFO.
    task = make_slots_task(tmp_path, gpu=1)
    held = grab_as(task, "holder", "o/holder-k")["ticket"]
    t0 = time.time()
    assert grab_as(task, "lane2", "o/upper6-lora", now=t0)["ticket"] is None
    assert grab_as(task, "lane6", "o/imprinted-head", now=t0 + 1)["ticket"] is None
    assert grab_as(task, "lane1", "o/fresh-idea", now=t0 + 2)["ticket"] is None
    bank(task, 0.82669, "o/upper6-lora")
    bank(task, 0.86597, "o/imprinted-head")
    kernel_slots.release(task, held)
    # Arrival said lane2 first; evidence says unscored lane1, then 0.866,
    # then 0.827 — and the ranking covers sleeping-but-fresh waiters, so
    # polling order cannot jump it.
    assert grab_as(task, "lane2", "o/upper6-lora", now=t0 + 3)["ticket"] is None
    assert grab_as(task, "lane6", "o/imprinted-head", now=t0 + 4)["ticket"] is None
    assert grab_as(task, "lane1", "o/fresh-idea", now=t0 + 5)["ticket"]


def test_queue_aging_promotes_weak_lanes_but_never_into_ship(tmp_path):
    # Evidence ordering must not starve: each aging period lifts a waiting
    # request one tier step, so an aged weak lane overtakes fresh stronger
    # arrivals of the same tier — while ship (the endgame) stays untouchable.
    task = make_slots_task(tmp_path, gpu=1, aging=100)
    held = grab_as(task, "holder", "o/holder-k")["ticket"]
    t0 = time.time()
    assert grab_as(task, "weak", "o/weak-k", now=t0)["ticket"] is None
    bank(task, 0.700, "o/weak-k")
    bank(task, 0.900, "o/strong-k")
    # Real waiters heartbeat every 5s; a lane that stops polling >30s is
    # pruned and re-enqueued fresh (its age rightly resets). Aging therefore
    # accrues only for continuously-waiting lanes — model the keep-alive:
    for dt in range(25, 150, 25):
        assert grab_as(task, "weak", "o/weak-k", now=t0 + dt)["ticket"] is None
    assert grab_as(task, "strong", "o/strong-k", now=t0 + 150)["ticket"] is None
    kernel_slots.release(task, held)
    # weak has waited 1.5 aging periods -> effective tier 1; fresh strong
    # stays tier 2 despite better evidence — the aged waiter wins the slot.
    assert grab_as(task, "strong", "o/strong-k", now=t0 + 151)["ticket"] is None
    ticket = grab_as(task, "weak", "o/weak-k", now=t0 + 152)["ticket"]
    assert ticket
    # Ship dominance survives any amount of aging: an eternally-aged reroll
    # still queues behind a fresh ship request once the slot frees.
    kernel_slots.release(task, ticket)
    assert grab_as(task, "old-reroll", "o/weak-k", priority="reroll",
                   waiter_id="w-old", now=t0 + 200)["ticket"]  # takes free slot
    assert grab_as(task, "aged-run", "o/weak-k", now=t0 + 300)["ticket"] is None
    assert grab_as(task, "harvest", "o/strong-k", priority="ship",
                   now=t0 + 301)["ticket"] is None
    kernel_slots.release(task, [
        t["ticket"] for t in kernel_slots.read_ledger(
            os.path.join(task, ".kernel_slots.json"))["tickets"]["gpu"]][0])
    # both wait; ship wins the freed slot over the (aged) run waiter
    assert grab_as(task, "aged-run", "o/weak-k", now=t0 + 302)["ticket"] is None
    assert grab_as(task, "harvest", "o/strong-k", priority="ship",
                   now=t0 + 303)["ticket"]


def test_lane_identity_survives_shell_quote_artifacts(tmp_path):
    # Live run 2026-08-03: lanes passed --lane with a trailing quote
    # (generic_exp_7'). Sanitization keeps one identity so evidence still
    # attributes.
    task = make_slots_task(tmp_path, gpu=1)
    held = grab_as(task, "lane7'", "o/lda-lane7")["ticket"]
    bank(task, 0.83369, "o/lda-lane7")
    kernel_slots.release(task, held)
    ledger = kernel_slots.read_ledger(os.path.join(task, ".kernel_slots.json"))
    assert kernel_slots.lane_best_public(task, ledger, "lane7'") == 0.83369
    assert kernel_slots.lane_best_public(task, ledger, "lane7") == 0.83369


def grab(task, pool="gpu", kind="push", lane="lane", priority=None,
         waiter_id=None, now=None):
    """One poll_once step — the atomic unit acquire_blocking loops on."""
    return kernel_slots.poll_once(
        task, pool, kind, "owner/kernel-a", lane,
        priority or kernel_slots.DEFAULT_PRIORITY[kind],
        waiter_id or f"w-{lane}", now if now is not None else time.time())


def test_kernel_slots_gates_pushes_only(tmp_path):
    # The account limit counts INTERACTIVE sessions, which pushes consume.
    # Submissions score on Kaggle's backend (contest 1: five concurrent,
    # zero rejections) so "score" is no longer a ticket kind at all.
    task = make_slots_task(tmp_path)
    assert kernel_slots.KINDS == ("push",)
    assert grab(task, kind="push", lane="a")["ticket"]
    assert grab(task, kind="push", lane="b")["ticket"]
    assert grab(task, kind="push", lane="c")["ticket"] is None
    # One queue PER POOL: a full GPU pool must not block the CPU pool.
    assert grab(task, pool="cpu", lane="d")["ticket"]
    with pytest.raises(ValueError, match="kind"):
        kernel_slots.acquire_blocking(task, "gpu", "score", "o/k", "lane")


def test_kernel_slots_priority_queue_orders_grants(tmp_path):
    # ship > run > reroll, FIFO within a tier — a freed slot goes to the
    # highest tier, not to whoever happens to poll first.
    task = make_slots_task(tmp_path, gpu=1)
    held = grab(task, lane="holder")["ticket"]
    t0 = time.time()
    assert grab(task, lane="早", priority="run", waiter_id="w-run",
                now=t0)["ticket"] is None
    assert grab(task, lane="ship", priority="ship",
                waiter_id="w-ship", now=t0 + 1)["ticket"] is None
    kernel_slots.release(task, held)
    # The earlier-arrived run waiter polls first but must NOT jump the queue.
    assert grab(task, lane="早", priority="run", waiter_id="w-run",
                now=t0 + 2)["ticket"] is None
    assert grab(task, lane="ship", priority="ship",
                waiter_id="w-ship", now=t0 + 3)["ticket"]
    # With the slot retaken, the run waiter keeps queueing.
    assert grab(task, lane="早", priority="run", waiter_id="w-run",
                now=t0 + 4)["ticket"] is None


def test_kernel_slots_grants_top_k_and_prunes_dead_waiters(tmp_path):
    task = make_slots_task(tmp_path)
    t0 = time.time()
    held = [grab(task, lane=f"h{i}", waiter_id=f"w-h{i}")["ticket"]
            for i in range(2)]
    # Three lanes queue on the full pool; the first then dies mid-wait (its
    # heartbeat goes stale) and must not hold a place in line.
    assert grab(task, lane="dead", waiter_id="w-dead", now=t0 - 120)["ticket"] is None
    assert grab(task, lane="b", waiter_id="w-b", now=t0)["ticket"] is None
    assert grab(task, lane="c", waiter_id="w-c", now=t0 + 1)["ticket"] is None
    for ticket in held:
        kernel_slots.release(task, ticket)
    # Two slots free -> BOTH fresh waiters grant (rank < free), regardless of
    # poll order — a slow-polling head cannot strand the second slot — and
    # the dead waiter's stale entry blocks neither.
    assert grab(task, lane="c", waiter_id="w-c", now=t0 + 2)["ticket"]
    assert grab(task, lane="b", waiter_id="w-b", now=t0 + 3)["ticket"]


def test_kernel_slots_reap_releases_only_kaggle_confirmed_dead(tmp_path):
    # TTL alone must NOT reclaim: a dead lane's kernel keeps RUNNING on
    # Kaggle, and blind reclaim over-granted the pool (run 5's ticket-holding
    # lanes still hit the session cap). Truth comes from Kaggle.
    task = make_slots_task(tmp_path)
    running = grab(task, kind="push", lane="zombie")["ticket"]
    kernel_slots.poll_once(task, "gpu", "push", "owner/kernel-b", "done",
                           "run", "w-done", time.time())
    ledger_path = os.path.join(task, ".kernel_slots.json")
    ledger = json.loads(open(ledger_path).read())
    for entry in ledger["tickets"]["gpu"]:
        entry["acquired"] = time.time() - 9999
    open(ledger_path, "w").write(json.dumps(ledger))

    statuses = {"owner/kernel-a": "running", "owner/kernel-b": "complete"}
    released = kernel_slots.maybe_reap(
        task, time.time(),
        kernel_status_fn=lambda ref, timeout: statuses[ref])
    assert running not in released        # kernel still running -> keep it
    assert len(released) == 1             # terminal kernel's ticket freed

    # Rate limit: an immediate second reap must not hammer Kaggle.
    assert kernel_slots.maybe_reap(
        task, time.time(),
        kernel_status_fn=lambda ref, timeout: "complete") == []
    # Past the interval, the terminal kernel's ticket is released too.
    assert kernel_slots.maybe_reap(
        task, time.time() + 61,
        kernel_status_fn=lambda ref, timeout: "complete") == [running]
    assert kernel_slots.status(task)["gpu"]["in_use"] == 0


def test_kernel_slots_fails_loud_without_its_config(tmp_path):
    with pytest.raises(FileNotFoundError, match="kernel_slots_config"):
        grab(str(tmp_path))


def test_classify_submit_output_reads_text_not_exit_codes():
    # Verified live 2026-08-02: the kaggle CLI exits 0 even on a rejected
    # submission, so the output text is the only signal.
    assert classify_submit_output("", "403 Client Error: Forbidden for url: "
                                  ".../CreateCodeSubmission") == "rejected-403"
    assert classify_submit_output("400 Client Error: Bad Request", "") == "rejected-400"
    assert classify_submit_output("", "") == "accepted"
    assert classify_submit_output("Successfully submitted", "") == "accepted"


def test_kernels_run_since_treats_not_found_as_empty(tmp_path):
    # A fresh account with zero kernels: the CLI exits 0 with literal
    # "Not found" instead of JSON. That is the empty state, not corruption —
    # a zero-push run's harvest must see [] rather than crash on json.loads.
    fake = tmp_path / "kaggle"
    fake.write_text("#!/bin/sh\necho 'Not found'\n")
    fake.chmod(0o755)
    assert kernels_run_since(str(fake), "2026-08-04T00:00:00", 50, 30) == []


def test_harvest_ranks_never_scored_kernels_first(tmp_path):
    # Run 5 submitted two already-scored kernels (alphabetical order) while
    # two unscored ones bounced off the full pool and were lost. The ledger
    # the submission procedure writes is what makes a banked score visible.
    ledger = tmp_path / "submissions.json"
    ledger.write_text(json.dumps({"submissions": [
        {"kernel_ref": "owner/scored-a", "public_score": 0.85952, "status": "complete"},
        {"file": "out.csv", "public_score": 0.84514, "status": "complete"},
        {"kernel_ref": "owner/pending-d", "public_score": None, "status": "pending"},
    ]}))
    banked = banked_kernel_refs(str(ledger))
    assert banked == {"owner/scored-a"}
    refs = ["owner/scored-a", "owner/unscored-b", "owner/unscored-c"]
    assert rank_harvest_candidates(refs, banked) == [
        "owner/unscored-b", "owner/unscored-c", "owner/scored-a"]
    assert banked_kernel_refs(str(tmp_path / "nowhere.json")) == set()


def test_preflight_prompt_carries_brief_verbatim_and_full():
    # The brief is organizer instruction text — it goes into the authoring
    # session whole (Rule 6), with the spec appended after it.
    brief = ("Solve the Kaggle competition some-comp.\n"
             "Follow your system instructions to guide you on how to solve this.\n"
             'Do not violate the competition rules, especially those in "X".')
    prompt = build_prompt(brief, "/t", "/t/dataset", "/t/dataset/statement.md",
                          "/t/RULES.md")
    assert brief in prompt
    assert "TASK BRIEF" in prompt
    assert prompt.index(brief) < prompt.index("preflight agent")


def test_preflight_validate_root_is_fail_loud(tmp_path):
    task = tmp_path / "task"
    ds = task / "dataset"
    ds.mkdir(parents=True)
    # empty root: statement missing
    with pytest.raises(SystemExit, match="statement.md missing"):
        validate_root(str(task))
    (ds / "statement.md").write_text("# Task")
    # statement alone: no data
    with pytest.raises(SystemExit, match="no competition data"):
        validate_root(str(task))
    (ds / "train.csv").write_text("id,y\n1,0\n")
    # data but no kaggle.json
    with pytest.raises(SystemExit, match="kaggle.json missing"):
        validate_root(str(task))
    (task / "kaggle.json").write_text(json.dumps({"competition": ""}))
    with pytest.raises(SystemExit, match="no competition slug"):
        validate_root(str(task))
    (task / "kaggle.json").write_text(json.dumps({"competition": "some-comp"}))
    with pytest.raises(SystemExit, match="higher_is_better"):
        validate_root(str(task))
    (task / "kaggle.json").write_text(json.dumps({"competition": "some-comp", "higher_is_better": True}))
    assert validate_root(str(task)) == "some-comp"


def test_preflight_spec_owns_scaffolding_and_brief_authority():
    spec = open(SPEC_PATH, encoding="utf-8").read()
    assert "Scaffolding you do first" in spec
    assert "competitions download" in spec
    assert '"higher_is_better": true|false' in spec
    assert "the brief is the authoritative copy" in spec
    assert "Starter Prompt" in spec
    # A task-published per-kernel time cap (contest 1: 600s) must be hunted for
    # and carried as a value; a spec trim dropping this loses the constraint.
    assert "Kernel run-time cap: the task's own stated limit is the authority" \
        in spec.replace("**", "")


def test_kaggle_config_minimal_knobs():
    """The benchmark's file is an override over the packaged config: the
    engine's settings at the top level, the runner's own under `benchmark`."""
    with open(CONFIG_PATH) as f:
        config = yaml.safe_load(f)
    benchmark = config["benchmark"]
    assert "kaggle" not in benchmark  # slug comes from the run root, not config
    assert "contest_economics" not in benchmark
    assert "knowledge_bank_dir" not in benchmark  # the book is served as experience, not staged
    assert config["budget"] == {"min_iteration_seconds": 900}
    # Zero harvest carve-out (user-set 2026-08-05): lanes own in-window
    # shipping; the campaign runs to the wall and the post-window harvest
    # is a no-op.
    assert benchmark["session_budget"]["harvest_window_minutes"] == 0
    assert benchmark["final_eval"]["harvest_budget_seconds"] == 0
    # Contest 5 (2026-08-06): the provider's safety classifier killed both
    # lanes' codex sessions on an adversarial task; a crash now retries once
    # on a second model instead of forfeiting the lane's remaining time.
    params = config["search_strategy"]["params"]
    assert params["implementation"]["fallback_model"] == "gpt-5.5"


# ---------------------------------------------------------------------------
# The Brief, the contest root, the procedure and the evaluation
# ---------------------------------------------------------------------------

COMPUTE = {"has_gpu": True, "gpu_name": "NVIDIA A100-SXM4-40GB, 40960 MiB", "num_cpus": 12, "mem_gb": 85}
LIMITS = {"gpu": 2, "cpu": 5, "ttl_seconds": 600, "reap_interval_seconds": 60, "verify_timeout_seconds": 120, "aging_seconds": 900}


def test_the_brief_is_the_statement_plus_the_campaigns_facts_and_the_rules(tmp_path):
    rules = open(RULES_PATH, encoding="utf-8").read()
    brief = build_brief(
        statement="# Practice task\n\nPredict the label of every test row.\n", competition="ioai-practice-1",
        higher_is_better=False, dataset_dir=tmp_path / "dataset", artifacts_dir=tmp_path / "artifacts",
        deadline_utc="2026-10-29T18:00:00+00:00", ledger_path=tmp_path / "contest_root" / "submissions.json",
        shared_root=tmp_path / "contest_root", pool_limits=LIMITS, rules_text=rules,
        shared_cache_dir=tmp_path / "shared", compute=COMPUTE,
    )
    objective = brief.objective
    assert objective.startswith("# Practice task")
    assert "`ioai-practice-1`" in objective and "2026-10-29T18:00:00+00:00" in objective
    assert PROCEDURE in objective and str(tmp_path / "contest_root" / "submissions.json") in objective
    assert f"python3 {tmp_path / 'contest_root' / 'kernel_slots.py'}" in objective
    assert "2 GPU and 5 CPU" in objective and "NVIDIA A100" in objective
    assert brief.measured_by.startswith("the public leaderboard score") and "lower is better" in brief.measured_by
    assert "pending submission is not yet a score" in brief.measured_by
    assert "## The organizers' binding rules" in objective and "cuda:0" in objective and "is 50 per task" in objective
    assert any("pinned at `kapso_datasets/RULES.md`" in rule for rule in brief.rules)
    assert brief.baseline is None
    for banned in ("TEN submit-and-learn rounds", "worth ZERO", "knowledge_bank", "SKIP", "STEAL"):
        assert banned not in objective, banned
    assert Brief.parse(brief.render()) == brief


def test_the_contest_root_carries_the_harness_conventions(tmp_path):
    task = tmp_path / "task"
    task.mkdir()
    shutil.copy2(RULES_PATH, task / "RULES.md")                          # the preflight's pinned copy
    (task / CONTEST_ROOT).mkdir()
    (task / CONTEST_ROOT / kernel_slots.LEDGER_NAME).write_text("{}")   # a stale ticket ledger goes
    root = stage_contest_root(str(task), "ioai-practice-1", True, "2026-10-29T10:00:00+00:00", LIMITS)
    assert root == str(task / CONTEST_ROOT)
    descriptor = json.loads((task / CONTEST_ROOT / "contest.json").read_text())
    assert descriptor == {
        "competition": "ioai-practice-1", "ledger": str(task / CONTEST_ROOT / LEDGER), "procedure": PROCEDURE,
        "higher_is_better": True, "window_start": "2026-10-29T10:00:00+00:00", "shared_root": root,
    }
    assert json.loads((task / CONTEST_ROOT / kernel_slots.CONFIG_NAME).read_text()) == LIMITS
    assert not (task / CONTEST_ROOT / kernel_slots.LEDGER_NAME).exists()
    for name in ("submit.py", "kernel_slots.py", "RULES.md"):
        assert (task / CONTEST_ROOT / name).is_file()
    assert "cuda:0" in (task / CONTEST_ROOT / "RULES.md").read_text()


def fake_kaggle(directory: Path, body: str) -> dict:
    """A `kaggle` on PATH that prints `body`: the environment for a subprocess."""
    directory.mkdir(parents=True, exist_ok=True)
    binary = directory / "kaggle"
    binary.write_text("#!/bin/sh\n" + body + "\n")
    binary.chmod(0o755)
    return {**os.environ, "PATH": f"{directory}:{os.environ['PATH']}"}


def candidate_repo(tmp_path, higher_is_better=False, window_start="2026-10-29T10:00:00+00:00"):
    """A session clone as the engine lays it out: the data with the
    descriptor, the provided evaluation, a kernel folder."""
    repo = tmp_path / "repo"
    shared_root = tmp_path / "contest_root"
    shared_root.mkdir()
    (repo / "kapso_datasets").mkdir(parents=True)
    shutil.copy2(SUBMIT_PATH, repo / "kapso_datasets" / "submit.py")
    (repo / "kapso_datasets" / "contest.json").write_text(json.dumps({
        "competition": "ioai-practice-1", "ledger": str(shared_root / LEDGER), "procedure": PROCEDURE,
        "higher_is_better": higher_is_better, "window_start": window_start, "shared_root": str(shared_root),
    }))
    (repo / "kapso_evaluation").mkdir()
    shutil.copy2(EVALUATION_SUITE / "evaluate.py", repo / "kapso_evaluation" / "evaluate.py")
    (repo / "kernel").mkdir()
    (repo / "kernel" / "kernel-metadata.json").write_text(json.dumps({"id": "me/kernel-a", "code_file": "script.py"}))
    (repo / "kernel" / "script.py").write_text("print('model')\n")
    return repo, shared_root / LEDGER, shared_root


def run_in(repo: Path, command: list, env: dict) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, *command], cwd=str(repo), env=env, capture_output=True, text=True)


def test_the_procedure_submits_and_records_the_entry_by_content(tmp_path):
    repo, ledger, _shared = candidate_repo(tmp_path)
    env = fake_kaggle(tmp_path / "bin", "echo 'Successfully submitted to ioai-practice-1'")
    done = run_in(repo, ["kapso_datasets/submit.py", "--kernel", "me/kernel-a", "--version", "3", "-m", "blend local=0.91"], env)
    assert done.returncode == 0, done.stderr
    (entry,) = json.loads(ledger.read_text())["submissions"]
    assert entry["competition"] == "ioai-practice-1" and entry["kernel_ref"] == "me/kernel-a" and entry["version"] == 3
    assert entry["submission_id"].startswith("kapso-") and entry["message"] == f"blend local=0.91 [{entry['submission_id']}]"
    assert entry["kernel_sha256"] == hashlib.sha256(b"print('model')\n").hexdigest()
    assert entry["status"] == "pending" and entry["verdict"] == "accepted" and entry["public_score"] is None
    # A file upload records the file's hash; a rejection is recorded and exits non-zero.
    (repo / "out.csv").write_text("id,y\n1,0\n")
    rejected = fake_kaggle(tmp_path / "bin403", "echo '403 Client Error: Forbidden for url: .../CreateSubmission' >&2")
    done = run_in(repo, ["kapso_datasets/submit.py", "--file", "out.csv", "-m", "upload local=0.5"], rejected)
    assert done.returncode == 2
    entries = json.loads(ledger.read_text())["submissions"]
    assert len(entries) == 2 and entries[1]["file"] == "out.csv" and entries[1]["status"] == "rejected"
    assert entries[1]["verdict"] == "rejected-403" and entries[1]["file_sha256"] == hashlib.sha256(b"id,y\n1,0\n").hexdigest()


def write_ledger(ledger: Path, entries: list) -> None:
    ledger.parent.mkdir(parents=True, exist_ok=True)
    ledger.write_text(json.dumps({"submissions": entries}))


def mine(**overrides) -> dict:
    entry = {
        "competition": "ioai-practice-1", "submission_id": "kapso-aa11", "message": "blend local=0.91 [kapso-aa11]",
        "submitted_at": "2026-10-29T11:00:00+00:00", "status": "pending", "public_score": None, "ref": None,
        "kernel_ref": "me/kernel-a", "version": 3, "code_file": "kernel/script.py",
        "kernel_sha256": hashlib.sha256(b"print('model')\n").hexdigest(), "verdict": "accepted", "output": "",
    }
    entry.update(overrides)
    return entry


OTHER = mine(submission_id="kapso-bb22", message="other [kapso-bb22]", kernel_sha256="0" * 64, status="complete", public_score=0.99)


class TestProvidedEvaluation:
    def evaluate(self, repo, env):
        return run_in(repo, ["kapso_evaluation/evaluate.py"], env)

    def test_missing_when_no_submission_of_this_candidate_is_recorded(self, tmp_path):
        repo, ledger, _shared = candidate_repo(tmp_path)
        env = fake_kaggle(tmp_path / "bin", "echo '[]'")
        assert self.evaluate(repo, env).returncode == 11
        write_ledger(ledger, [OTHER])
        done = self.evaluate(repo, env)
        assert done.returncode == 11 and "no submission of this candidate" in done.stdout

    def test_a_scored_submission_is_refreshed_attributed_and_oriented(self, tmp_path):
        repo, ledger, shared = candidate_repo(tmp_path, higher_is_better=False)
        write_ledger(ledger, [OTHER, mine()])
        rows = json.dumps([{"ref": 777, "date": "2026-10-29 11:05:00", "status": "complete", "publicScore": "0.42",
                            "description": "blend local=0.91 [kapso-aa11]"}])
        env = fake_kaggle(tmp_path / "bin", f"echo 'Next Page Token = x'; echo '{rows}'")
        done = self.evaluate(repo, env)
        assert done.returncode == 0, done.stdout + done.stderr
        line = [line for line in done.stdout.splitlines() if line.startswith("KAPSO_EVAL_MANIFEST")][-1]
        result = json.loads(line.split(" ", 1)[1])
        assert result == {"score": -0.42, "raw_score": 0.42, "higher_is_better": False, "submission_id": "kapso-aa11",
                          "ref": 777, "submitted_at": "2026-10-29T11:00:00+00:00"}
        refreshed = json.loads(ledger.read_text())["submissions"][1]
        assert refreshed["status"] == "complete" and refreshed["public_score"] == 0.42 and refreshed["ref"] == 777
        assert (shared / "best_score.log").read_text().startswith("0.42 2026-10-29T11:00:00+00:00 me/kernel-a blend")

    def test_pending_rejected_and_out_of_window_are_distinct_outcomes(self, tmp_path):
        repo, ledger, _shared = candidate_repo(tmp_path)
        env = fake_kaggle(tmp_path / "bin", "echo '[]'")
        write_ledger(ledger, [mine()])
        done = self.evaluate(repo, env)
        assert done.returncode == 12 and "pending" in done.stdout
        write_ledger(ledger, [mine(status="rejected", verdict="rejected-403", output="403 Client Error")])
        done = self.evaluate(repo, env)
        assert done.returncode == 13 and "403 Client Error" in done.stdout
        errored = json.dumps([{"ref": 1, "status": "error", "errorDescription": "Evaluation exception",
                               "publicScore": "", "description": "blend local=0.91 [kapso-aa11]"}])
        write_ledger(ledger, [mine()])
        done = self.evaluate(repo, fake_kaggle(tmp_path / "binerr", f"echo '{errored}'"))
        assert done.returncode == 13 and "Evaluation exception" in done.stdout
        write_ledger(ledger, [mine(status="complete", public_score=0.5, submitted_at="2026-10-29T09:00:00+00:00")])
        assert self.evaluate(repo, env).returncode == 14

    def test_the_latest_of_this_candidates_submissions_is_reported(self, tmp_path):
        repo, ledger, _shared = candidate_repo(tmp_path, higher_is_better=True)
        write_ledger(ledger, [
            mine(status="complete", public_score=0.7, submitted_at="2026-10-29T11:00:00+00:00"),
            mine(submission_id="kapso-cc33", status="complete", public_score=0.6, submitted_at="2026-10-29T12:00:00+00:00"),
        ])
        done = self.evaluate(repo, fake_kaggle(tmp_path / "bin", "echo '[]'"))
        assert done.returncode == 0 and '"raw_score": 0.6' in done.stdout and '"submission_id": "kapso-cc33"' in done.stdout


def test_kernel_folders_are_found_anywhere_under_the_task_dir(tmp_path):
    task = tmp_path / "task"
    for folder in ("kapso_campaign/sessions/lane0/kernel", "contest_root/.git/kernel", "kapso_campaign/kernel"):
        (task / folder).mkdir(parents=True)
        (task / folder / "kernel-metadata.json").write_text(json.dumps({"id": "me/k", "code_file": "script.py"}))
    found = kernel_metadata_dirs(str(task))
    assert found == [str(task / "kapso_campaign" / "kernel"), str(task / "kapso_campaign" / "sessions" / "lane0" / "kernel")]
