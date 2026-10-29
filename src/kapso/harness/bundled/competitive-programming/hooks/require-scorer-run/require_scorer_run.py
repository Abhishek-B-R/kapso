"""Stop hook on implementation: no finish without a scorer run over every seed.

The seed list is the task's, read from the task root (`kapso_datasets/`
beside the task statement, the engine's copy of the data directory the
build was given, found from the session's directory upward); the results
file is the harness's convention (`results/scores.json`, the scorer-cli
skill). A task root without a seed list means the task is not scored by
seeds here (a leaderboard contest, say), and the hook has no opinion.

Both hosts send the Stop event on stdin; a decision is `{"decision":
"block", "reason": ...}`; exit 0 with nothing printed lets the session
end.
"""
import json
import sys
from pathlib import Path

TASK_STATEMENT = "kapso_task.md"
DATA_DIR = "kapso_datasets"
SEED_LIST = "seeds.txt"
RESULTS = Path("results") / "scores.json"


def task_root(start: Path):
    """The data directory beside the nearest task statement at or above `start`, or None."""
    for directory in (start, *start.parents):
        if (directory / TASK_STATEMENT).is_file():
            data = directory / DATA_DIR
            return data if data.is_dir() else None
    return None


def block(reason: str) -> None:
    print(json.dumps({"decision": "block", "reason": reason}))


def main() -> None:
    json.load(sys.stdin)
    root = task_root(Path.cwd().resolve())
    if root is None or not (root / SEED_LIST).is_file():
        sys.exit(0)
    seeds = [line.strip() for line in (root / SEED_LIST).read_text().splitlines() if line.strip()]
    if not RESULTS.is_file():
        block(f"No scorer run recorded: {RESULTS} is missing. Run the scorer on every seed of "
              f"{root / SEED_LIST} and write the results file the scorer-cli skill describes before finishing.")
        return
    results = json.loads(RESULTS.read_text())
    scored = results.get("seeds") if isinstance(results, dict) else None
    if not isinstance(scored, dict):
        block(f"{RESULTS} has no `seeds` mapping; write it as the scorer-cli skill describes.")
        return
    missing = [seed for seed in seeds if not isinstance(scored.get(seed), dict)
               or not isinstance(scored[seed].get("score"), (int, float))
               or not isinstance(scored[seed].get("runtime_ms"), (int, float))]
    if missing:
        block(f"The scorer has not run on every seed: {', '.join(missing)} missing a numeric score and runtime "
              f"in {RESULTS}. Run the scorer-cli skill's procedure on every seed before finishing.")
        return
    sys.exit(0)


if __name__ == "__main__":
    main()
