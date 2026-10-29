"""Stop hook on implementation: no finish without a scorer run over every seed.

The seed list is the task's, `kapso_datasets/seeds.txt` in the task root
(the data directory beside the nearest task statement at or above the
session's directory that has one); the results file is the harness's
convention (`results/scores.json` at the attempt's root, the scorer-cli
skill). A task root without a seed list means the task is not scored by
seeds here (a leaderboard contest, say), and the hook has no opinion.

The hook asks once: when the event says the session is already continuing
because of a stop hook, it stays silent, so a session whose scorer is
broken is not trapped. It is a mistake catcher, not the gate: it checks
the file's shape and that it was written after the solution's last change;
the verifier reproduces the numbers. A results file that is not JSON makes
the hook fail loud, and the launcher line in hook.json turns that failure
into a blocking exit (code 2), so a corrupt file never passes as a finish.
"""
import json
import math
import sys
from pathlib import Path

TASK_STATEMENT = "kapso_task.md"
DATA_DIR = "kapso_datasets"
SEED_LIST = "seeds.txt"
RESULTS = Path("results") / "scores.json"
STATUSES = ("ok", "wrong-answer", "time-limit", "runtime-error")


def task_root(start: Path):
    """The data directory beside the nearest task statement at or above `start` that has one, or None."""
    for directory in (start, *start.parents):
        if (directory / TASK_STATEMENT).is_file() and (directory / DATA_DIR).is_dir():
            return directory / DATA_DIR
    return None


def block(reason: str) -> None:
    print(json.dumps({"decision": "block", "reason": reason}))


def finite_number(value) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def seed_problem(entry) -> str:
    """Why a seed's entry is not a scorer result, or an empty string."""
    if entry is None:
        return "missing"
    if not isinstance(entry, dict):
        return "not a mapping"
    if not finite_number(entry.get("score")):
        return "no finite numeric score"
    if not finite_number(entry.get("spread")) or entry["spread"] < 0:
        return "no non-negative spread"
    if not finite_number(entry.get("runtime_ms")) or entry["runtime_ms"] < 0:
        return "no non-negative runtime_ms"
    if entry.get("status") not in STATUSES:
        return f"status not one of {', '.join(STATUSES)}"
    return ""


def main() -> None:
    event = json.load(sys.stdin)
    if isinstance(event, dict) and event.get("stop_hook_active"):
        sys.exit(0)
    root = task_root(Path.cwd().resolve())
    if root is None or not (root / SEED_LIST).is_file():
        sys.exit(0)
    seeds = [line.strip() for line in (root / SEED_LIST).read_text().splitlines() if line.strip()]
    if not seeds:
        block(f"{root / SEED_LIST} lists no seed: the task root is incomplete. Say so in the attempt notes and finish.")
        return
    if not RESULTS.is_file():
        block(f"No scorer run recorded: {RESULTS} is missing. Run the scorer on every seed of {root / SEED_LIST} and "
              "write the results file the scorer-cli skill describes before finishing; if the scorer cannot run, say "
              "so in the attempt notes and finish.")
        return
    results = json.loads(RESULTS.read_text())  # a corrupt results/scores.json fails loud here
    if not isinstance(results, dict) or not isinstance(results.get("seeds"), dict):
        block(f"{RESULTS} has no `seeds` mapping; write it as the scorer-cli skill describes.")
        return
    for key in ("build", "solution"):
        if not isinstance(results.get(key), str) or not results[key]:
            block(f"{RESULTS} names no `{key}`; write the build line and the solution file as the scorer-cli skill describes.")
            return
    if not isinstance(results.get("runs"), int) or isinstance(results["runs"], bool) or results["runs"] < 1:
        block(f"{RESULTS} has no positive integer `runs` (the runs per seed; 1 for a deterministic solution).")
        return
    solution = Path(results["solution"])
    if not solution.is_file():
        block(f"{RESULTS} names the solution {solution}, which does not exist at the attempt's root.")
        return
    if solution.stat().st_mtime > RESULTS.stat().st_mtime:
        block(f"{solution} changed after {RESULTS} was written: run the scorer again on the solution as it is now.")
        return
    problems = [f"{seed} ({why})" for seed in seeds if (why := seed_problem(results["seeds"].get(seed)))]
    if problems:
        block(f"The scorer has not run on every seed: {', '.join(problems)} in {RESULTS}. Run the scorer-cli skill's "
              "procedure on every seed before finishing.")
        return
    sys.exit(0)


if __name__ == "__main__":
    main()
