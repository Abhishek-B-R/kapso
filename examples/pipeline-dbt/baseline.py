"""Score the shipped project in the engine's workspace layout and write
baseline.json: the number the brief and the README quote.

    python generate.py && python baseline.py
"""

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="pipeline-dbt-baseline-") as temp:
        workspace = Path(temp) / "ws"
        shutil.copytree(HERE / "repo", workspace)
        shutil.copytree(HERE / "data", workspace / "kapso_datasets")
        shutil.copytree(HERE / "evaluation", workspace / "kapso_evaluation", ignore=shutil.ignore_patterns("result.json", "warehouse.duckdb", "__pycache__"))
        run = subprocess.run([sys.executable, "kapso_evaluation/evaluate.py"], cwd=workspace, capture_output=True, text=True, check=True)
        result = json.loads((workspace / "kapso_evaluation" / "result.json").read_text(encoding="utf-8"))
    passed = sum(1 for assertion in result["assertions"] if assertion["passed"])
    (HERE / "baseline.json").write_text(json.dumps({
        "metric": "tests_passing",
        "score": result["score"],
        "assertions_passing": f"{passed}/{len(result['assertions'])}",
        "note": "the shipped staging models pass the exports through untouched; measured by evaluation/evaluate.py in the workspace layout",
    }, indent=2) + "\n", encoding="utf-8")
    print(run.stdout.strip().splitlines()[-1])
    print("baseline.json written")


if __name__ == "__main__":
    main()
