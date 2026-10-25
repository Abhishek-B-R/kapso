"""Live smoke of the CLI-only inference conversion (design §7.7).

Scaled-down production loop — add_experience(research=) (the CLI
web-search session, then a small ingest) -> one short build served the
index (repo memory, commit messages, judge, embeddings on the converted
stack) — with per-stage wall-clock recorded so the timings can be
compared against the API-path baseline in
learning/e2e-facade/20260825T223634 (research 76s; build1 15m26s for
the full 45-min-budget run).

Run:  PYTHONPATH=src:. python examples/ml_model_development/run_cli_inference_smoke.py
"""

import json
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT))
sys.path.insert(0, str(_REPO_ROOT / "src"))

from kapso.kapso import Kapso
from kapso.handles import Budget
from examples.ml_model_development.e2e.generate_data import generate
from examples.ml_model_development.run_full_loop import GOAL, sandbox_config, served

# Smoke budgets: the point is exercising every converted seam through at
# least one full iteration (implementation -> evaluation -> judge ->
# commit), not reaching the example's target score. The example's
# reference E2E showed 20 minutes starves the FIRST implementation, so
# 25 gives one full iteration headroom without paying for a real run.
BUILD_BUDGET_MINUTES = 25
BUILD_MAX_ITERATIONS = 2

RESEARCH_QUESTION = (
    "For small tabular binary classification (~2000 rows, mixed "
    "numeric/categorical, missing values): the two highest-leverage "
    "modeling moves over a DummyClassifier baseline, with concrete "
    "sklearn-compatible choices."
)


def main() -> None:
    example_dir = _REPO_ROOT / "examples/ml_model_development"
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    sandbox = _REPO_ROOT / "learning" / "e2e-facade" / f"{stamp}-cli-smoke"
    sandbox.mkdir(parents=True)
    build = subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"], cwd=str(_REPO_ROOT),
        check=True, capture_output=True, text=True,
    ).stdout.strip()
    timings = {"build": build}
    timings_path = sandbox / "stage_timings.json"
    index_name = f"smoke-{stamp.lower()}"
    print(f"CLI smoke sandbox: {sandbox} (build {build})", flush=True)

    config_path = sandbox_config(sandbox)

    workdir = sandbox / "task"
    shutil.copytree(example_dir / "repo", workdir)
    train_df, test_df = generate(rows=2000, test_rows=500, seed=1337)
    (workdir / "data").mkdir()
    train_df.to_csv(workdir / "data" / "train.csv", index=False)
    test_df.to_csv(workdir / "data" / "test.csv", index=False)

    kapso = Kapso(config=str(config_path))
    kapso.add_experience("mine")

    def timed(name, fn):
        print(f"=== SMOKE STAGE {name}: running", flush=True)
        t0 = time.time()
        result = fn()
        timings[name] = round(time.time() - t0, 1)
        timings_path.write_text(json.dumps(timings, indent=1))
        print(f"=== SMOKE STAGE {name}: done in {timings[name]}s", flush=True)
        return result

    # --- 1. experience: the research session (codex --search), then a small ingest ---
    timed("experience", lambda: kapso.add_experience(research=RESEARCH_QUESTION, name=index_name))
    corpus = kapso.load_experience(index_name)
    if not corpus.cards:
        raise RuntimeError(f"the index {index_name} holds no pages")
    timings["experience_pages"] = corpus.cards
    timings_path.write_text(json.dumps(timings, indent=1))

    # --- 2. short build served the index: repo memory + commit messages + judge + embeddings ---
    sol = timed("build", lambda: kapso.build(
        GOAL,
        repo=str(workdir),
        output=str(sandbox / "campaign"),
        budget=Budget(experiments=BUILD_MAX_ITERATIONS, minutes=BUILD_BUDGET_MINUTES),
    ))
    (sandbox / "solution.txt").write_text(sol.explain())
    timings["build_score"] = sol.score
    timings["build_goal_achieved"] = sol.goal_achieved
    timings["build_served"] = served(sol)
    timings_path.write_text(json.dumps(timings, indent=1))
    print(f"\nCLI_SMOKE_COMPLETE sandbox={sandbox} timings={timings}",
          flush=True)


if __name__ == "__main__":
    main()
