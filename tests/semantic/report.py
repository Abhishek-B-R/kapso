"""Render one semantic run's record as its markdown report.

    python report.py <run.json> <budgets.json> <out.md>

The record's shape is in README.md. Budgets map a step name to the limits
from docs/plans/kapso-plugin-skills.md: `messages`, `questions`, `minutes`,
`longest_message_lines`; a step passes when it completed, every recorded
value is at or under its limit, every artifact it names exists (relative
to the record's directory), and the budgets file knows the step: a step
without limits fails, so a round cannot add a step the budgets never
bound. A deferred step (`deferred` set to the reason) is reported and
neither passes nor fails.
"""

import json
import sys
from pathlib import Path
from typing import Dict, List, Optional

LIMIT_KEYS = ("messages", "questions", "minutes", "longest_message_lines")


def missing_artifacts(step: dict, root: Path) -> List[str]:
    return [artifact for artifact in step.get("artifacts", []) if not (root / artifact).exists()]


def step_passes(step: dict, limits: Optional[dict], root: Path) -> bool:
    if not limits or not step["completed"] or missing_artifacts(step, root):
        return False
    return all(step[key] <= limits[key] for key in LIMIT_KEYS if key in limits)


def render(record: dict, budgets: Dict[str, dict], root: Path) -> str:
    lines = [
        f"# {record['test']} on {record['host']}",
        "",
        f"- machine: {record['machine']}",
        f"- package: {record['package']['version']} ({record['package']['wheel_sha256'][:12]})",
        f"- started: {record['started']}  finished: {record['finished']}",
        "",
        "| step | messages | questions | minutes | longest message | completed | artifacts | verdict |",
        "|---|---|---|---|---|---|---|---|",
    ]
    verdicts = []
    for step in record["steps"]:
        if step.get("deferred"):
            lines.append(f"| {step['name']} | - | - | - | - | - | - | deferred: {step['deferred']} |")
            continue
        limits = budgets.get(step["name"])
        missing = missing_artifacts(step, root)
        passed = step_passes(step, limits, root)
        verdicts.append(passed)
        verdict = "pass" if passed else ("FAIL (no budget)" if not limits else "FAIL")
        artifacts = f"{len(step.get('artifacts', [])) - len(missing)}/{len(step.get('artifacts', []))}" + (f" missing {', '.join(missing)}" if missing else "")
        lines.append(
            f"| {step['name']} | {step['messages']} | {step['questions']} | {step['minutes']} "
            f"| {step['longest_message_lines']} lines | {'yes' if step['completed'] else 'no'} | {artifacts} | {verdict} |"
        )
    lines.append("")
    if record.get("judge"):
        lines.append("| dimension | score |")
        lines.append("|---|---|")
        for dimension, score in record["judge"].items():
            lines.append(f"| {dimension} | {score} |")
        lines.append("")
    if record.get("notes"):
        lines.append("Notes:")
        lines.extend(f"- {note}" for note in record["notes"])
        lines.append("")
    lines.append("Transcripts:")
    lines.extend(f"- {path}" for path in record.get("transcripts", []))
    lines.append("")
    lines.append(f"Result: {'PASS' if all(verdicts) else 'FAIL'} ({sum(verdicts)}/{len(verdicts)} steps)")
    return "\n".join(lines) + "\n"


def main() -> None:
    record_path = Path(sys.argv[1])
    record = json.loads(record_path.read_text(encoding="utf-8"))
    budgets = {name: limits for name, limits in json.loads(Path(sys.argv[2]).read_text(encoding="utf-8")).items() if name != "_"}
    Path(sys.argv[3]).write_text(render(record, budgets, record_path.parent), encoding="utf-8")


if __name__ == "__main__":
    main()
