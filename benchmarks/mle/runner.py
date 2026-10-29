#!/usr/bin/env python3
"""MLE-bench runner: one competition, one campaign on the facade's build().

    python -m benchmarks.mle.runner --competition <id> [-i N] [--workspace DIR] [--resume]
        [--harness REF] [--experience REFS] [--coding-agent CLI]
    python -m benchmarks.mle.runner --list [--lite]

The runner keeps the competition material and launches the engine: it
downloads and prepares the competition's public data under the archive root
(`benchmark.work_root` in config.yaml), stages the provided grader with the
competition's settings beside it, writes the Brief from the competition's
description and files, seeds the baseline candidate, and runs build() with
the bundled predictive-modelling harness (or the one --harness names) and
the experience --experience loads. After the campaign it grades the
delivered candidate's `final_submission.csv` once, officially, on the
private answers, and writes final_report.json.
"""

import argparse
import json
import shutil
import tarfile
import tempfile
import zipfile
from pathlib import Path
from typing import Dict, Optional

from dotenv import load_dotenv
from mlebench.data import download_and_prepare_dataset
from mlebench.grade import grade_csv
from mlebench.registry import registry

from kapso.core.config import read_yaml
from kapso.handles import Budget, Solution
from kapso.kapso import Kapso

from benchmarks.common import stage_evaluation, write_runtime_config
from benchmarks.mle.context import build_brief

load_dotenv()

BENCH_DIR = Path(__file__).resolve().parent
CONFIG_PATH = BENCH_DIR / "config.yaml"
DATA_DIR = BENCH_DIR / "data"
EVALUATION_SUITE = DATA_DIR / "generic_eval"
BASELINE = DATA_DIR / "generic_baseline" / "main.py"
BUNDLED_HARNESS = "predictive-modelling"
FINAL_REPORT = "final_report.json"
SUBMISSION = "final_submission.csv"


def list_competitions(lite_only: bool) -> None:
    competitions = registry.get_lite_competition_ids() if lite_only else registry.list_competition_ids()
    title = "MLE-bench lite competitions" if lite_only else "All MLE-bench competitions"
    print(f"\n{'=' * 60}\n{title} ({len(competitions)} total)\n{'=' * 60}")
    for competition_id in sorted(competitions):
        print(f"  • {competition_id}")
    print()


def extract_archives(data_dir: Path) -> None:
    """Every archive among the prepared files, extracted beside it once."""
    for archive in sorted(data_dir.iterdir()):
        if not archive.is_file():
            continue
        target = data_dir / archive.stem
        if zipfile.is_zipfile(archive):
            with zipfile.ZipFile(archive) as opened:
                members = opened.namelist()
                if members and not (target / members[0]).exists():
                    target.mkdir(exist_ok=True)
                    opened.extractall(target)
        elif tarfile.is_tarfile(archive):
            with tarfile.open(archive, "r:*") as opened:
                members = opened.getnames()
                if members and not (target / members[0]).exists():
                    target.mkdir(exist_ok=True)
                    opened.extractall(target)


def prepare_data(competition, data_dir: Path) -> Path:
    """The competition's public files under the archive root, archives extracted."""
    download_and_prepare_dataset(competition)
    data_dir.mkdir(parents=True, exist_ok=True)
    for item in sorted(competition.public_dir.glob("*")):
        destination = data_dir / item.name
        if destination.exists():
            continue
        if item.is_dir():
            shutil.copytree(item, destination)
        else:
            shutil.copy2(item, destination)
    extract_archives(data_dir)
    return data_dir


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


def seeded_baseline() -> str:
    directory = tempfile.mkdtemp(prefix="mle_baseline_")
    shutil.copy2(BASELINE, Path(directory) / "main.py")
    return directory


def final_report(work_dir: Path, competition, solution: Solution) -> Dict[str, object]:
    """The official grade on the private answers, once, on the delivered
    candidate's `final_submission.csv`; or the no-candidate report."""
    report: Dict[str, object] = {"competition_id": competition.id, "solution": solution_summary(solution)}
    submission = solution.campaign / SUBMISSION
    if solution.branch is None:
        report["error"] = "no candidate delivered"
    elif not submission.is_file():
        report["error"] = f"the delivered candidate has no {SUBMISSION} at the repository root"
    else:
        grade = grade_csv(submission, competition)
        report["private_evaluation"] = grade.to_dict()
    out = work_dir / FINAL_REPORT
    out.write_text(json.dumps(report, indent=2, default=str) + "\n")
    print(f"[mle] final report -> {out}")
    return report


def solve_competition(args) -> dict:
    settings = read_yaml(str(CONFIG_PATH))["benchmark"]
    competition = registry.get_competition(args.competition)
    work_dir = (Path(settings["work_root"]) / competition.id).resolve()
    work_dir.mkdir(parents=True, exist_ok=True)
    print(f"\n{'=' * 60}\nSolving: {competition.id}\n{'=' * 60}")
    print(f"  Archive root: {work_dir}")

    data_dir = prepare_data(competition, work_dir / "data")
    higher_is_better = not competition.grader.is_lower_better
    floors = settings["floor_scores"]
    floor_score = float(floors["higher_is_better"] if higher_is_better else floors["lower_is_better"])
    timeouts = settings["timeouts"]
    evaluation_dir = stage_evaluation(EVALUATION_SUITE, work_dir, {
        "competition_id": competition.id,
        "higher_is_better": higher_is_better,
        "data_dir": str(data_dir),
        "full_timeout": int(timeouts["full"]),
        "debug_timeout": int(timeouts["debug"]),
        "floor_score": floor_score,
    })
    shared_cache_dir = work_dir / "shared_cache"
    shared_cache_dir.mkdir(exist_ok=True)
    brief = build_brief(
        competition, data_dir, higher_is_better, int(timeouts["debug"]), int(timeouts["full"]),
        floor_score, list(settings["forbidden_packages"]), shared_cache_dir,
    )

    kapso = Kapso(config=str(write_runtime_config(CONFIG_PATH, shared_cache_dir, work_dir)))
    kapso.load_harness(args.harness or BUNDLED_HARNESS)
    for reference in (args.experience or "").split(","):
        if reference.strip():
            kapso.load_experience(reference.strip())
    solution = kapso.build(
        brief,
        evaluation=str(evaluation_dir),
        repo=None if args.resume else seeded_baseline(),
        output=args.workspace,
        budget=Budget(experiments=args.iterations),
        resume=args.resume,
        coding_agent=args.coding_agent,
    )

    print("\n" + "=" * 60 + "\nFinal Evaluation (the private answers, once)\n" + "=" * 60)
    report = final_report(work_dir, competition, solution)
    print(json.dumps(report, indent=2, default=str))
    return report


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run Kapso on an MLE-bench competition",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("-c", "--competition", type=str, help="Competition ID (e.g. spooky-author-identification)")
    parser.add_argument("-i", "--iterations", type=int, default=None, help="Budget.experiments (the config's when absent)")
    parser.add_argument("-d", "--coding-agent", type=str, default=None, help="The host every session runs on (the config's when absent)")
    parser.add_argument("--workspace", type=str, default=None, help="The campaign directory (output=); needed to resume")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--harness", type=str, default=None, help=f"A harness reference (default: the bundled {BUNDLED_HARNESS})")
    parser.add_argument("--experience", type=str, default=None,
                        help="Comma-separated sources to serve: mine, a bank path or git reference, an index name")
    parser.add_argument("--list", action="store_true", help="List all competitions")
    parser.add_argument("--lite", action="store_true", help="List the lite competitions")
    args = parser.parse_args()

    if args.list or args.lite:
        list_competitions(lite_only=args.lite)
        return
    if not args.competition:
        parser.error("--competition is required unless --list or --lite is given")
    if args.competition not in registry.list_competition_ids():
        parser.error(f"unknown competition {args.competition!r}; --list prints the registry")

    report = solve_competition(args)
    print("\n" + "=" * 60 + "\nCOMPLETED\n" + "=" * 60)
    print(f"Competition: {report['competition_id']}")
    print(f"Private evaluation: {report.get('private_evaluation', report.get('error'))}")
    print(f"Delivered: {report['solution']}")


if __name__ == "__main__":
    main()
