"""The Claude Code half's report: the `--json` document `claude plugin
eval` wrote, rendered per skill and kind against the bar (every case at
the threshold, no cross-skill false positive).

    python3 scripts/redesign/trigger_report.py <triggers.json>
"""

import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List

CASE_NAME = re.compile(r"^(?P<skill>[a-z]+)-(?P<kind>[eicn])(?P<index>\d+)$|^holdout-(?P<holdout>\d+)$")
KINDS = {"e": "explicit", "i": "implicit", "c": "confusion", "n": "none"}


def rows(document: Dict[str, Any]) -> List[Dict[str, Any]]:
    found = []
    for case in document["cases"]:
        match = CASE_NAME.match(case["name"])
        if match is None:
            raise ValueError(f"case name outside the suite's grammar: {case['name']}")
        skill = "holdout" if match.group("holdout") else match.group("skill")
        kind = "holdout" if match.group("holdout") else KINDS[match.group("kind")]
        runs = case["arms"]["with"]
        found.append({
            "name": case["name"], "skill": skill, "kind": kind,
            "score": case["aggregates"]["score"], "runs": len(runs),
            "errors": [run["error"] for run in runs if run.get("error")],
        })
    return found


def render(document: Dict[str, Any]) -> str:
    table = rows(document)
    lines = [
        f"Claude Code {document.get('claudeVersion', '?')}: {document['aggregates']['casesPassed']} of "
        f"{document['aggregates']['casesTotal']} cases at the threshold; mean score "
        f"{document['aggregates']['overallScore']:.2f}; ${document.get('costUsd', 0):.2f}; "
        f"{document.get('durationSeconds', 0):.0f}s" + ("; PARTIAL: " + str(document.get("partialReason")) if document.get("partial") else ""),
        "",
        "| skill | kind | cases | perfect | below |",
        "|---|---|---|---|---|",
    ]
    groups: Dict[tuple, List[Dict[str, Any]]] = {}
    for row in table:
        groups.setdefault((row["skill"], row["kind"]), []).append(row)
    for (skill, kind), members in sorted(groups.items()):
        perfect = [m for m in members if m["score"] >= 1.0]
        below = [m["name"] for m in members if m["score"] < 1.0]
        lines.append(f"| {skill} | {kind} | {len(members)} | {len(perfect)} | {', '.join(below) or '-'} |")
    errors = [(row["name"], error) for row in table for error in row["errors"]]
    if errors:
        lines += ["", "Run errors:"] + [f"- {name}: {error}" for name, error in errors]
    return "\n".join(lines)


if __name__ == "__main__":
    print(render(json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))))
