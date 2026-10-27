"""The author test (docs/plans/redesign/wp9-semantic-suite.md, change 11;
WP2's S3 made runnable): a model author with only the authoring guide,
the reference and the trading example writes a harness for a new domain
in a scratch directory, logging every guess as one line, and may not run
`kapso`. The driver runs `check`; the judge classifies each guess and
reviews the harness against the guide's rules. Two rounds: the structural
gaps and contradictions of round one are written into the guide (this
package owns those pages), and a fresh author runs round two. The bar is
zero structural gaps in round two and a green `check`.

    python3 author_test.py --clone <clone> --out <dir> [--host claude_code] [--round round-1] [--advisory <reason>]
    python3 author_test.py --out <dir> --grade        # classify the guesses on the judge's route

The guess grammar, one per line of the author's `GUESSES.md`:

    GUESS: <what it guessed> | <where it looked> | <what it chose>
"""

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence

sys.path.insert(0, str(Path(__file__).resolve().parent))
import plugin_proof  # noqa: E402
from plugin_proof import SUITE, ClaudeHost, CodexHost, record_step, shell_step  # noqa: E402
from s1_cold_engineer import CLAUDE_COLD, CODEX_COLD  # noqa: E402
import judge as judge_module  # noqa: E402

GUESS_PATTERN = re.compile(r"^GUESS:\s*(?P<what>.+?)\s*\|\s*(?P<where>.+?)\s*\|\s*(?P<chose>.+?)\s*$")
CLASSES = ("structural_gap", "contradiction", "domain_decision", "already_in_guide")
GUIDE_PAGES = ["docs/harnesses/write.mdx", "docs/harnesses/index.mdx", "docs/reference/harness.mdx", "docs/harnesses/example-trading.mdx"]
EXAMPLE = "examples/harnesses/trading"
STEP_NAMES = ["round-1", "guide-fixes", "round-2"]
BRIEF = """You are a domain author writing a Kapso harness for a new domain, `pipeline-dbt`: dbt data pipelines (models, sources, tests, incremental builds, a warehouse the project runs against, CI that runs the project). You have never seen Kapso before; you know dbt well.

Read, in this order, and nothing else in the repository:

{pages}
{example}/  (every file under it: the worked example)

Then write the harness into the directory {out}/pipeline-dbt ({out} is your working directory; create the directory). Give it a manifest, instructions pages (guardrails and at least setup, implementation and verification), at least two skills each with its SKILL.md (one with a script beside it), at least one delegate under agents/, an mcp.json with at least one stdio server whose script under servers/ may be a stub that imports mcp and defines one tool, at least two hooks under hooks/ each with its hook.json and script, and requirements.txt. It must pass `kapso harness check` as the guide describes it; follow the guide's conventions exactly where it states one.

Every time the guide, the reference or the example left something undecided that you had to guess, write one line in {out}/GUESSES.md in exactly this grammar:

    GUESS: <what you guessed and what you chose> | <where in the guide you looked> | <the shape or value you settled on>

Be honest and complete: a guess you later confirmed in the example still counts if the guide itself did not say it. Do not read any other file in the repository, do not run kapso, do not install anything, do not modify anything outside {out}. When you are done, reply with the file list of {out}/pipeline-dbt and the number of lines in {out}/GUESSES.md.
"""
CLASSIFY = """You are grading the guess log of an author who wrote a Kapso harness with only the authoring guide below. Classify each guess as exactly one of:

- "structural_gap": a field, file, key, convention or host behaviour the engine or `kapso harness check` would reject if guessed wrong, which the guide does not state.
- "contradiction": the guide says two things that cannot both hold.
- "domain_decision": a choice about the author's own domain (dbt), not about Kapso, that no guide could make for them.
- "already_in_guide": the guide already states it; the author did not find it.

Reply with exactly one JSON object: {{"classifications": [{{"index": <1-based int>, "class": "<one of the four>", "why": "<one sentence in plain prose that cites the guide by file and section, never by pasting code, and uses no double-quote characters, so the JSON stays valid>"}}, ...]}}, one entry per guess, in order.

=== THE GUIDE ===
{guide}

=== THE GUESSES ===
{guesses}
"""


# ----------------------------------------------------------- the core
@dataclass
class Guess:
    index: int
    what: str
    where: str
    chose: str
    raw: str


def parse_guesses(text: str) -> List[Guess]:
    """Every `GUESS:` line in the grammar; a `GUESS:` line that does not
    match the grammar raises (Rule 2: a malformed line is not skipped)."""
    guesses = []
    index = 0
    for number, line in enumerate(text.splitlines(), 1):
        if not line.strip().startswith("GUESS:"):
            continue
        match = GUESS_PATTERN.match(line.strip())
        if not match:
            raise ValueError(f"GUESSES line {number} is not `GUESS: <what> | <where> | <chose>`: {line.strip()!r}")
        index += 1
        guesses.append(Guess(index, match["what"], match["where"], match["chose"], line.strip()))
    return guesses


def guide_text(clone: Path) -> str:
    return "\n\n".join(f"=== {page} ===\n{(clone / page).read_text(encoding='utf-8')}" for page in GUIDE_PAGES)


def classify_guesses(guesses: Sequence[Guess], guide: str, settings: dict, ask: Optional[Callable[[str, dict], str]] = None, raw_path: Optional[Path] = None) -> List[Dict[str, Any]]:
    """Each guess classified on the judge's route; the reply is one object
    with one entry per guess, each class one of the four, or it raises. The
    raw reply is archived (when raw_path is given) before validation, so a
    contract break — a malformed reply — keeps its evidence, as the judge's
    own calls do."""
    ask = ask or judge_module.ask
    if not guesses:
        return []
    rendered = "\n".join(f"{guess.index}. {guess.raw}" for guess in guesses)
    reply = ask(CLASSIFY.replace("{guide}", guide).replace("{guesses}", rendered), settings)
    if raw_path is not None:
        raw_path.parent.mkdir(parents=True, exist_ok=True)
        raw_path.write_text(reply, encoding="utf-8")
    data = judge_module.extract_json(reply)
    rows = data.get("classifications")
    if not isinstance(rows, list) or len(rows) != len(guesses):
        raise judge_module.JudgeFailure(f"the classifier returned {len(rows) if isinstance(rows, list) else 'no'} entries for {len(guesses)} guesses")
    out = []
    for guess, row in zip(guesses, rows):
        if row.get("index") != guess.index or row.get("class") not in CLASSES or not isinstance(row.get("why"), str):
            raise judge_module.JudgeFailure(f"guess {guess.index}: a bad classification {row!r}")
        out.append({"index": guess.index, "guess": guess.raw, "class": row["class"], "why": row["why"]})
    return out


def structural_gaps(classified: Sequence[Dict[str, Any]]) -> int:
    return sum(1 for row in classified if row["class"] == "structural_gap")


def contradictions(classified: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [row for row in classified if row["class"] == "contradiction"]


def run_metrics(record: Dict[str, Any]) -> Dict[str, Any]:
    rounds = {step["name"]: step for step in record["steps"] if step["name"] in ("round-1", "round-2")}
    two = rounds.get("round-2", {}).get("metrics", {})
    return {
        "structural_gaps_round1": rounds.get("round-1", {}).get("metrics", {}).get("structural_gaps"),
        "structural_gaps_round2": two.get("structural_gaps"),
        "check_green_round2": 1 if two.get("check_green") else (0 if "check_green" in two else None),
    }


# ---------------------------------------------------------------- driver
class Author:
    def __init__(self, args: argparse.Namespace):
        self.args = args
        self.clone = Path(args.clone).resolve() if args.clone else None
        self.out = Path(args.out).resolve()
        (self.out / "transcripts").mkdir(parents=True, exist_ok=True)
        (self.out / "artifacts").mkdir(parents=True, exist_ok=True)
        self.host = ClaudeHost(CLAUDE_COLD) if args.host == "claude_code" else CodexHost(CODEX_COLD)

    def artifact(self, name: str, text: str) -> str:
        (self.out / "artifacts" / name).write_text(text, encoding="utf-8")
        return f"artifacts/{name}"

    def brief(self, scratch: Path) -> str:
        return BRIEF.format(
            pages="\n".join(f"{number}. {self.clone / page}" for number, page in enumerate(GUIDE_PAGES, 1)),
            example=self.clone / EXAMPLE, out=scratch,
        )

    def step_round(self, name: str) -> Dict[str, Any]:
        scratch = self.out / "work" / name
        if scratch.exists():
            shutil.rmtree(scratch)
        scratch.mkdir(parents=True)
        transcript = self.out / "transcripts" / f"{name}.jsonl"
        turn = self.host.turn(scratch, self.brief(scratch), None, transcript)
        harness = scratch / "pipeline-dbt"
        guesses_file = scratch / "GUESSES.md"
        guesses = parse_guesses(guesses_file.read_text(encoding="utf-8")) if guesses_file.is_file() else []
        check = subprocess.run(["kapso", "harness", "check", str(harness)], capture_output=True, text=True)
        files = sorted(str(path.relative_to(harness)) for path in harness.rglob("*") if path.is_file()) if harness.is_dir() else []
        artifacts = [self.artifact(f"{name}-reply.txt", turn.text), self.artifact(f"{name}-check.txt", check.stdout + check.stderr),
                     self.artifact(f"{name}-files.txt", "\n".join(files)), self.artifact(f"{name}-guesses.md", guesses_file.read_text(encoding="utf-8") if guesses_file.is_file() else "")]
        # The harness copied under the record so the judge's author rubric
        # can read it (`judge.py --rubric author --inputs ...`).
        if harness.is_dir():
            review = self.out / "artifacts" / f"{name}-harness.md"
            review.write_text("\n\n".join(f"=== {path} ===\n{(harness / path).read_text(encoding='utf-8', errors='replace')}" for path in files if (harness / path).suffix in (".md", ".yaml", ".json", ".py", ".txt")), encoding="utf-8")
            artifacts.append(f"artifacts/{name}-harness.md")
        step = record_step(name, [turn], check.returncode == 0 and bool(files) and bool(guesses), artifacts,
                           [f"{len(guesses)} guesses; check exited {check.returncode}; {len(files)} files", "the author did not run kapso (the guide forbids it); the driver runs check"])
        step["metrics"] = {"guesses": len(guesses), "check_green": check.returncode == 0, "files": len(files), "structural_gaps": None}
        return step

    def step_guide_fixes(self) -> Dict[str, Any]:
        """The gaps and contradictions of round one are written into the
        guide between rounds (this package owns those pages); the step
        records what was fed into the fix and the guide's diff."""
        record = json.loads((self.out / "record.json").read_text())
        round_one = next((step for step in record["steps"] if step["name"] == "round-1"), None)
        classified = round_one.get("classification", []) if round_one else []
        gaps = [row for row in classified if row["class"] in ("structural_gap", "contradiction")]
        diff = subprocess.run(["git", "-C", str(self.clone), "diff", "--stat", "--", "docs/harnesses", "docs/reference/harness.mdx"], capture_output=True, text=True) if self.clone else None
        artifacts = [self.artifact("guide-fixes-inputs.json", json.dumps(gaps, indent=2))]
        if diff:
            artifacts.append(self.artifact("guide-fixes-diff.txt", diff.stdout))
        step = shell_step("guide-fixes", True, artifacts, 0.0,
                          [f"{len(gaps)} structural gaps and contradictions from round one fed into the guide; the pages this package owns: {', '.join(GUIDE_PAGES)}"])
        step["metrics"] = {"fixes_from_round1": len(gaps)}
        return step


def grade(record: Dict[str, Any], out: Path, clone: Path, settings: dict, ask: Optional[Callable[[str, dict], str]] = None) -> Dict[str, Any]:
    """Classify each round's guesses on the judge's route; the counts into
    the record's metrics."""
    guide = guide_text(clone)
    for step in record["steps"]:
        if step["name"] not in ("round-1", "round-2"):
            continue
        guesses_md = out / "artifacts" / f"{step['name']}-guesses.md"
        guesses = parse_guesses(guesses_md.read_text(encoding="utf-8")) if guesses_md.is_file() else []
        classified = classify_guesses(guesses, guide, settings, ask=ask, raw_path=out / judge_module.JUDGE_DIR / f"classify-{step['name']}.txt")
        step["classification"] = classified
        step["metrics"]["structural_gaps"] = structural_gaps(classified)
        (out / "artifacts" / f"{step['name']}-classification.json").write_text(json.dumps(classified, indent=2), encoding="utf-8")
    record["metrics"] = run_metrics(record)
    return record


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--clone", default=None)
    parser.add_argument("--out", required=True)
    parser.add_argument("--host", default="claude_code", choices=["claude_code", "codex"])
    parser.add_argument("--round", default=None, choices=STEP_NAMES)
    parser.add_argument("--machine", default=os.uname().nodename)
    parser.add_argument("--advisory", default=None)
    parser.add_argument("--grade", action="store_true")
    args = parser.parse_args(argv)
    driver = Author(args)
    record_file = driver.out / "record.json"
    started = datetime.now(timezone.utc)
    record = json.loads(record_file.read_text()) if record_file.exists() else {
        "test": "author", "host": args.host, "machine": args.machine, "run_id": f"author-{args.host}-{started.strftime('%Y%m%dT%H%M%SZ')}", "advisory": args.advisory,
        "package": {"version": subprocess.run(["kapso", "--version"], capture_output=True, text=True).stdout.strip().split()[-1], "wheel_sha256": "-"},
        "pins": {"suite_sha256": hashlib.sha256(plugin_proof.SUITE_PATH.read_bytes()).hexdigest(), "pages": GUIDE_PAGES, "example": EXAMPLE},
        "user": {"kind": "scripted", "card": None, "interventions": ["the author holds only the guide pages, the reference and the trading example; it may not run kapso; the driver runs check and classifies the guesses"], "events": [], "pushback": None},
        "started": started.isoformat(timespec="seconds"), "finished": None, "steps": [], "metrics": {}, "notes": [], "transcripts": [],
    }
    if args.grade:
        record = grade(record, driver.out, driver.clone, SUITE["judge"])
        record_file.write_text(json.dumps(record, indent=1) + "\n", encoding="utf-8")
        print(json.dumps(record["metrics"]))
        return 0
    selected = [args.round] if args.round else STEP_NAMES
    for name in selected:
        print(f"== {name}", flush=True)
        step = driver.step_guide_fixes() if name == "guide-fixes" else driver.step_round(name)
        record["steps"] = [existing for existing in record["steps"] if existing["name"] != name] + [step]
        record["finished"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
        record["transcripts"] = sorted(f"transcripts/{path.name}" for path in (driver.out / "transcripts").glob("*.jsonl"))
        record_file.write_text(json.dumps(record, indent=1) + "\n", encoding="utf-8")
        print(json.dumps({key: value for key, value in step.items() if key not in ("notes", "classification")}), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
