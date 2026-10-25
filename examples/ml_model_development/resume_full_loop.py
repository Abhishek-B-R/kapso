"""Resume the full-loop E2E from a sandbox whose experience stage
completed (run_full_loop.py, learn-facade-integration.md Phase 2).

Usage:
  PYTHONPATH=src:. python examples/ml_model_development/resume_full_loop.py \
      learning/e2e-facade/<stamp> [--from build1|learn]

`--from learn` reuses a completed build1 by learning from its campaign
DIRECTORY (learn()'s path dispatch) — no Solution needed, so a
crashed later stage never costs a good campaign.

Validates the completed stage's artifacts, loads the index it made (the
pages already live in the stores; loading never ingests), wipes any
partial campaign, then runs build1 -> learn -> build2 and the
loop-closure check into the SAME sandbox.
"""

import json
import shutil
import sys
import os
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "src"))

from kapso.kapso import Kapso
from kapso.handles import Budget

from examples.ml_model_development.run_full_loop import (
    BUILD_BUDGET_MINUTES,
    BUILD_MAX_ITERATIONS,
    GOAL,
    served,
    stage,
)


def main() -> None:
    sandbox = Path(sys.argv[1]).resolve()
    start_at = "build1"
    if "--from" in sys.argv:
        start_at = sys.argv[sys.argv.index("--from") + 1]
    if start_at not in ("build1", "learn"):
        raise ValueError("--from must be build1 or learn")
    status_path = sandbox / "stage_status.json"
    status = json.loads(status_path.read_text())
    if status["experience"]["state"] != "done":
        raise RuntimeError(
            "resume requires the experience stage done; run run_full_loop.py instead"
        )
    index_name = status["experience"]["index_name"]
    print(f"Resuming E2E in sandbox: {sandbox}", flush=True)

    kapso = Kapso(config=str(sandbox / "config.e2e.yaml"))

    # The index the research made is loaded, never re-ingested: loading
    # reads its record and connects to the stores it was built on.
    corpus = kapso.load_experience(index_name)
    if corpus.head != status["experience"]["index_id"]:
        raise RuntimeError(
            f"the index {index_name} is {corpus.head} now, {status['experience']['index_id']} "
            "when the run made it — the sandbox was re-ingested; start a new run"
        )
    (sandbox / "memory-1b-resumed.txt").write_text(kapso.memory.explain())

    # A partial campaign from the interrupted run cannot be resumed at this
    # layer (the driver owns whole stages) — wipe and redo cleanly.
    keep = {"campaign1"} if start_at == "learn" else set()
    for partial in ("campaign1", "campaign2"):
        if partial in keep:
            continue
        if (sandbox / partial).exists() and status.get(
            f"build{partial[-1]}", {}
        ).get("state") != "done":
            shutil.rmtree(sandbox / partial)
            print(f"  wiped partial {partial}", flush=True)

    workdir = sandbox / "task"

    # --- 2. build #1: served the corpus ---
    sol1 = None
    if start_at == "learn":
        if status.get("build1", {}).get("state") != "done":
            raise RuntimeError("--from learn requires a completed build1")
        print("  reusing completed build1 (campaign1)", flush=True)
    else:
        if status.get("build1", {}).get("state") == "done":
            # Redo: a completed-but-unusable stage (e.g. a budget-starved
            # campaign) is re-run from scratch into a fresh campaign dir.
            # The durable stage (the experience) is never redone.
            print("  build1 was done — redoing it (fresh campaign)", flush=True)
            if (sandbox / "campaign1").exists():
                shutil.rmtree(sandbox / "campaign1")
        stage(status_path, "build1", "running")
        sol1 = kapso.build(
            GOAL,
            repo=str(workdir),
            output=str(sandbox / "campaign1"),
            budget=Budget(experiments=BUILD_MAX_ITERATIONS, minutes=BUILD_BUDGET_MINUTES),
        )
        (sandbox / "solution1.txt").write_text(sol1.explain())
        stage(status_path, "build1", "done",
              score=sol1.score, goal_achieved=sol1.goal_achieved, served=served(sol1))

    # --- 3. learn ---
    stage(status_path, "learn", "running")
    lesson = kapso.learn(
        sol1 if sol1 is not None else str(sandbox / "campaign1")
    )
    (sandbox / "lesson.txt").write_text(lesson.explain())
    (sandbox / "memory-2-after-lesson.txt").write_text(kapso.memory.explain())
    stage(status_path, "learn", "done",
          trajectory=lesson.trajectory_id, admitted=lesson.admitted,
          head_before=lesson.bank_head_before,
          head_after=lesson.bank_head_after,
          cards_created=lesson.cards_created,
          cards_updated=lesson.cards_updated)

    # --- 4. build #2: served the corpus and the bank ---
    stage(status_path, "build2", "running")
    kapso.load_experience("mine")
    sol2 = kapso.build(
        GOAL,
        repo=str(workdir),
        output=str(sandbox / "campaign2"),
        budget=Budget(experiments=BUILD_MAX_ITERATIONS, minutes=BUILD_BUDGET_MINUTES),
    )
    (sandbox / "solution2.txt").write_text(sol2.explain())
    (sandbox / "memory-3-final.txt").write_text(kapso.memory.explain())
    stage(status_path, "build2", "done",
          score=sol2.score, goal_achieved=sol2.goal_achieved, served=served(sol2))

    served2 = served(sol2).get("mine")
    if served2 != lesson.bank_head_after:
        raise RuntimeError(
            f"LOOP NOT CLOSED: build2 served mine at {served2}, lesson produced "
            f"{lesson.bank_head_after}"
        )
    stage(status_path, "loop", "closed",
          served_head_build2=served2, admitted=lesson.admitted)
    print(f"\nFULL_LOOP_COMPLETE sandbox={sandbox}", flush=True)


if __name__ == "__main__":
    main()
