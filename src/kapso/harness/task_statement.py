"""The task statement, `<campaign>/kapso_task.md`: what every session of a
build with a harness reads first. The engine owns and renders it: the
brief whole, the effective budget, the evaluation and data references,
the harness, the setup session's own domain statement (read from its
file), and the prepared resources. Untracked and ignored, copied into
every session directory by the staging. Design:
docs/research/harness-design.md section 3; the plan:
docs/plans/redesign/wp2-harness.md ("The task statement").
"""

from pathlib import Path
from typing import Any, Dict, Optional, Sequence

from kapso.harness.load import Harness
from kapso.harness.staging import PREPARED_DIR, TASK_STATEMENT_FILE

SETUP_DIR = Path(".kapso") / "harness_setup"
SETUP_STATEMENT_FILE = "statement.md"
_BUDGET_KEYS = ("minutes", "experiments", "usd", "reserve_minutes")


def setup_statement_path(campaign_dir: Path) -> Path:
    """Where the harness setup session writes its domain statement."""
    return Path(campaign_dir) / SETUP_DIR / SETUP_STATEMENT_FILE


def prepared_names(campaign_dir: Path) -> Sequence[str]:
    prepared = Path(campaign_dir) / PREPARED_DIR
    if not prepared.is_dir():
        return ()
    return tuple(sorted(p.name for p in prepared.iterdir() if p.is_dir()))


def compose_task_statement(
    *,
    brief_text: str,
    harness: Harness,
    budget: Dict[str, Any],
    evaluation_dir: Optional[str],
    data_dir: Optional[str],
    domain_statement: str,
    prepared: Sequence[str],
) -> str:
    budget_line = " ".join(
        f"{key}={budget[key] if budget.get(key) is not None else 'the config’s'}" for key in _BUDGET_KEYS
    )
    evaluation = (
        "`kapso_evaluation/`, provided by the person and protected: a candidate that modifies it is rejected."
        if evaluation_dir else
        "none provided: the campaign builds the evaluation from the brief's `Measured by` protocol into `kapso_evaluation/`."
    )
    data = (
        "`kapso_datasets/` at the campaign root, a copy of the data directory the build was given; "
        "read it there, never the original." if data_dir else "no data directory was provided."
    )
    statement = domain_statement.strip() or "(the setup session has not written one)"
    resources = "\n".join(f"- `{PREPARED_DIR}/{name}`" for name in prepared) or "(none yet)"
    return (
        "# Task statement\n\n"
        f"Written by Kapso for harness {harness.name} {harness.version}; every session reads it first. "
        "The brief's values win over anything a harness page says.\n\n"
        "## Brief\n\n"
        f"{brief_text.strip()}\n\n"
        "## Budget\n\n"
        f"{budget_line}\n\n"
        "## Evaluation\n\n"
        f"{evaluation}\n\n"
        "## Data\n\n"
        f"{data}\n\n"
        "## Domain statement\n\n"
        f"{statement}\n\n"
        "## Prepared resources\n\n"
        f"{resources}\n"
    )


def write_task_statement(
    campaign_dir: Path,
    *,
    brief_text: str,
    harness: Harness,
    budget: Dict[str, Any],
    evaluation_dir: Optional[str],
    data_dir: Optional[str],
) -> Path:
    """Render the statement from what the campaign holds now: the setup
    session's statement file when it exists, the prepared directories as
    they are. Called at launch and again after the setup session."""
    campaign_dir = Path(campaign_dir)
    setup_statement = setup_statement_path(campaign_dir)
    domain_statement = setup_statement.read_text(encoding="utf-8") if setup_statement.is_file() else ""
    text = compose_task_statement(
        brief_text=brief_text, harness=harness, budget=budget,
        evaluation_dir=evaluation_dir, data_dir=data_dir,
        domain_statement=domain_statement, prepared=prepared_names(campaign_dir),
    )
    path = campaign_dir / TASK_STATEMENT_FILE
    path.write_text(text, encoding="utf-8")
    return path
