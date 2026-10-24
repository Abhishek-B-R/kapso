"""Render one semantic run's record as its markdown report.

    python report.py <run.json> <budgets.json> <out.md>

The record's shape is in README.md. Budgets map a step name to the limits
from docs/plans/kapso-plugin-skills.md: `messages`, `questions`, `minutes`,
`longest_message_lines`; a step passes when every recorded value is at or
under its limit and the step completed.
"""

import json
import sys
from pathlib import Path

LIMIT_KEYS = ("messages", "questions", "minutes", "longest_message_lines")


def step_passes(step: dict, limits: dict) -> bool:
    if not step["completed"]:
        return False
    return all(step[key] <= limits[key] for key in LIMIT_KEYS if key in limits)


def render(record: dict, budgets: dict) -> str:
    lines = [
        f"# {record['test']} on {record['host']}",
        "",
        f"- machine: {record['machine']}",
        f"- package: {record['package']['version']} ({record['package']['wheel_sha256'][:12]})",
        f"- started: {record['started']}  finished: {record['finished']}",
        "",
        "| step | messages | questions | minutes | longest message | completed | verdict |",
        "|---|---|---|---|---|---|---|",
    ]
    verdicts = []
    for step in record["steps"]:
        limits = budgets.get(step["name"], {})
        passed = step_passes(step, limits)
        verdicts.append(passed)
        lines.append(
            f"| {step['name']} | {step['messages']} | {step['questions']} | {step['minutes']} "
            f"| {step['longest_message_lines']} lines | {'yes' if step['completed'] else 'no'} "
            f"| {'pass' if passed else 'FAIL'} |"
        )
    lines.append("")
    if record.get("judge"):
        lines.append("| dimension | score |")
        lines.append("|---|---|")
        for dimension, score in record["judge"].items():
            lines.append(f"| {dimension} | {score} |")
        lines.append("")
    lines.append("Transcripts:")
    lines.extend(f"- {path}" for path in record.get("transcripts", []))
    lines.append("")
    lines.append(f"Result: {'PASS' if all(verdicts) else 'FAIL'} ({sum(verdicts)}/{len(verdicts)} steps)")
    return "\n".join(lines) + "\n"


def main() -> None:
    record = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    budgets = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
    Path(sys.argv[3]).write_text(render(record, budgets), encoding="utf-8")


if __name__ == "__main__":
    main()
