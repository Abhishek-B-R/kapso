"""The verification verdict: what a harness's verification session writes
for one attempt, what the engine reads back, and how the judge and the
delivery read it. Design: docs/research/harness-design.md section 4; the
plan: docs/plans/redesign/wp2-harness.md ("Verification").

    {"verdict": "valid" | "void", "summary": "...",
     "findings": [{"rule": "...", "evidence": "strategy/signal.py:4 ..."}]}

A session that writes none leaves the attempt `unverified`: its score
stands, it stays a parent, it is never delivered while the harness has
verification. A malformed verdict raises (CLAUDE.md rule 2).
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from kapso.harness.load import HarnessError

VALID = "valid"
VOID = "void"
UNVERIFIED = "unverified"
VERDICT_FILE = "verdict.json"
VERIFICATION_DIR = Path(".kapso") / "verification"


def verification_dir(campaign_dir: Path, branch: str) -> Path:
    return Path(campaign_dir) / VERIFICATION_DIR / branch


def unverified(reason: str) -> Dict[str, Any]:
    return {"verdict": UNVERIFIED, "summary": reason, "findings": []}


def read_verdict(path: Path) -> Dict[str, Any]:
    """The verdict a session wrote, or `unverified` when the file is
    absent; a file that is not the contract raises naming the problem."""
    if not path.is_file():
        return unverified("the verification session wrote no verdict")
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise HarnessError(f"{path}: the verdict must be an object")
    verdict = data.get("verdict")
    if verdict not in (VALID, VOID):
        raise HarnessError(f"{path}: verdict must be \"{VALID}\" or \"{VOID}\", not {verdict!r}")
    summary = data.get("summary")
    if not isinstance(summary, str) or not summary.strip():
        raise HarnessError(f"{path}: summary must be a non-empty string")
    findings = data.get("findings", [])
    if not isinstance(findings, list):
        raise HarnessError(f"{path}: findings must be a list")
    clean: List[Dict[str, str]] = []
    for finding in findings:
        if (
            not isinstance(finding, dict)
            or not isinstance(finding.get("rule"), str)
            or not isinstance(finding.get("evidence"), str)
        ):
            raise HarnessError(f"{path}: each finding is {{\"rule\": ..., \"evidence\": ...}}")
        clean.append({"rule": finding["rule"], "evidence": finding["evidence"]})
    if verdict == VOID and not clean:
        raise HarnessError(f"{path}: a void verdict needs at least one finding with evidence")
    return {"verdict": verdict, "summary": summary.strip(), "findings": clean}


def is_void(verification: Optional[Dict[str, Any]]) -> bool:
    return verification is not None and verification["verdict"] == VOID


def is_deliverable(verification: Optional[Dict[str, Any]]) -> bool:
    """Delivered: an attempt with no harness verdict, or a valid one. A
    void is never delivered, and neither is an attempt the harness's
    session did not verify."""
    return verification is None or verification["verdict"] == VALID


def render_verification(verification: Optional[Dict[str, Any]]) -> str:
    """The judge's block for an attempt the harness verified; "" without."""
    if verification is None:
        return ""
    lines = ["## Harness verification of this attempt", "", f"Verdict: {verification['verdict']}",
             f"Summary: {verification['summary']}"]
    if verification["findings"]:
        lines.append("Findings:")
        lines += [f"- {finding['rule']}: {finding['evidence']}" for finding in verification["findings"]]
    if verification["verdict"] == VOID:
        lines += ["", "A void verdict means this attempt is invalid whatever its score: say so in "
                      "your feedback and report the evaluation as not valid."]
    elif verification["verdict"] == UNVERIFIED:
        lines += ["", "The harness could not verify this attempt (no verdict was written): judge it on "
                      "its evidence, and say that verification is missing."]
    return "\n".join(lines) + "\n"
