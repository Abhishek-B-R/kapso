"""Re-derive the plugin round's records (WP7) into the record's second
shape (docs/plans/redesign/wp9-semantic-suite.md, change 2): a `kind` on
every step from the suite's entry, `user` scripted, `pins` from the
package, a `run_id`, and `advisory` on the development box's record. Run
once; the reports are rendered again by report.py.

    python3 scripts/redesign/rederive_records.py
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
SUITE = json.loads((ROOT / "tests" / "semantic" / "suite.json").read_text(encoding="utf-8"))
RECORDS = {
    "claude_code": None,
    "claude_code_first": None,
    "codex": "the Codex half ran on the development box under the owner's own Codex login, by the owner's decision (WP7)",
}


def rederive(path: Path, advisory) -> None:
    record = json.loads(path.read_text(encoding="utf-8"))
    for step in record["steps"]:
        if step.get("deferred"):
            continue
        step["kind"] = SUITE["steps"][step["name"]]["kind"]
    record["run_id"] = f"{record['test']}-{record['host']}-{record['started'].replace(':', '').replace('-', '').replace('+0000', 'Z')}"
    record["user"] = {"kind": "scripted", "card": None, "interventions": [
        "the key written where the request's fix line says before the person says so (inbox)",
        "the fixture written for the criteria steps (build-data-only, build-empty-wish)",
        "the harness's module answers from the driver's policy (harness-new)",
    ]}
    record["pins"] = {"wheel_sha256": record["package"]["wheel_sha256"]}
    record["advisory"] = advisory
    path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    print("re-derived", path)


def main() -> None:
    for name, advisory in RECORDS.items():
        rederive(ROOT / "scripts" / "redesign" / "runs" / "wp7" / name / "record.json", advisory)


if __name__ == "__main__":
    main()
