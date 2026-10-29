"""The author test (docs/plans/redesign/wp9-semantic-suite.md, change 11;
WP2's S3 made runnable): a model author with only the authoring guide,
the reference and the trading example writes a harness for a new domain
in a scratch directory, logging every guess as one line, and may not run
`kapso`. The driver runs `check`; the judge classifies each guess and
reviews the harness against the guide's rules. One cold author per run, on
the guide as committed (the record pins its hash): the structural gaps and
contradictions it logs are written into the guide between runs (this
package owns those pages) and committed, and the next run's fresh author
is the design's round two. The bar is zero structural gaps and a green
`check`.

    python3 author_test.py --clone <clone> --out <dir> [--host claude_code] [--advisory <reason>]
    python3 author_test.py --out <dir> --clone <clone> --grade        # classify the guesses on the judge's route

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
from plugin_proof import SUITE, ClaudeHost, CodexHost, codex_session_note, record_step  # noqa: E402
from s1_cold_engineer import CLAUDE_COLD, CODEX_COLD  # noqa: E402
import judge as judge_module  # noqa: E402

GUESS_PATTERN = re.compile(r"^GUESS:\s*(?P<what>.+?)\s*\|\s*(?P<where>.+?)\s*\|\s*(?P<chose>.+?)\s*$")
CLASSES = ("structural_gap", "contradiction", "domain_decision", "already_in_guide")
GUIDE_PAGES = ["docs/harnesses/write.mdx", "docs/harnesses/index.mdx", "docs/reference/harness.mdx", "docs/harnesses/example-trading.mdx"]
EXAMPLE = "examples/harnesses/trading"
STEP_NAMES = ["write"]
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

- "structural_gap": a field, file, key, convention or host behaviour the engine or `kapso harness check` would reject if guessed wrong, which the guide does not state. The test is rejection: name the check rule or engine behaviour that a wrong guess would trip. A choice the guide leaves open that any reasonable value satisfies (a library or SDK pattern, a code style, a language version, an optional extra file) is not structural: it is a domain_decision, a choice that is the author's to make about their own domain or their own code.
- "contradiction": the guide says two things that cannot both hold.
- "domain_decision": a choice about the author's own domain (dbt), not about Kapso, that no guide could make for them; or a choice about the author's own code (a library, a style, a language version, an extra file) to which the engine accepts any reasonable answer.
- "already_in_guide": the guide already states it; the author did not find it.

Reply with exactly one JSON object: {{"classifications": [{{"index": <1-based int>, "class": "<one of the four>", "why": "<one sentence in plain prose that cites the guide by file and section, never by pasting code, and uses no double-quote characters, so the JSON stays valid; for a structural_gap it names the check rule or engine behaviour a wrong guess would trip>"}}, ...]}}, one entry per guess, in order.

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


def merge_classifications(first: Sequence[Dict[str, Any]], second: Sequence[Dict[str, Any]], third: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """The final class per guess from two blind passes and, for each guess
    whose passes disagree on the one thing the bar counts (structural or
    not), the adjudicating pass's class; a guess the passes agree on keeps
    the first pass's row. Every row carries both passes' classes, so a
    reader sees what was adjudicated."""
    adjudicated = {row["index"]: row for row in third}
    merged = []
    for one, two in zip(first, second):
        straddles = (one["class"] == "structural_gap") != (two["class"] == "structural_gap")
        if straddles and one["index"] not in adjudicated:
            raise judge_module.JudgeFailure(f"guess {one['index']} straddled the bar and the adjudication did not classify it")
        source = adjudicated[one["index"]] if straddles else one
        merged.append({**source, "passes": [one["class"], two["class"]], "adjudicated": straddles})
    return merged


def classify_twice(guesses: Sequence[Guess], guide: str, settings: dict, ask: Callable[[str, dict], str], raw_dir: Path) -> List[Dict[str, Any]]:
    """Two blind classifications and a third for the guesses that straddle
    the bar — the judge's rule, so one call's reading of one guess never
    decides the test's one hard bar on its own."""
    first = classify_guesses(guesses, guide, settings, ask=ask, raw_path=raw_dir / "classify-write-pass1.txt")
    second = classify_guesses(guesses, guide, settings, ask=ask, raw_path=raw_dir / "classify-write-pass2.txt")
    straddling = [guess for guess, one, two in zip(guesses, first, second) if (one["class"] == "structural_gap") != (two["class"] == "structural_gap")]
    third = classify_guesses(straddling, guide, settings, ask=ask, raw_path=raw_dir / "classify-write-adjudication.txt") if straddling else []
    return merge_classifications(first, second, third)


def structural_gaps(classified: Sequence[Dict[str, Any]]) -> int:
    return sum(1 for row in classified if row["class"] == "structural_gap")


def contradictions(classified: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [row for row in classified if row["class"] == "contradiction"]


def run_metrics(record: Dict[str, Any]) -> Dict[str, Any]:
    metrics = next((step["metrics"] for step in record["steps"] if step["name"] == "write"), {})
    return {
        "structural_gaps": metrics.get("structural_gaps"),
        "contradictions": metrics.get("contradictions"),
        "check_green": 1 if metrics.get("check_green") else (0 if "check_green" in metrics else None),
    }


# ---------------------------------------------------------------- driver
class Author:
    def __init__(self, args: argparse.Namespace):
        self.args = args
        self.clone = Path(args.clone).resolve()
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

    def step_write(self) -> Dict[str, Any]:
        name = "write"
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
        # The guide the author read, archived so a later grade classifies
        # against it (the pin is its hash), never against a changed one.
        artifacts.append(self.artifact("guide.md", guide_text(self.clone)))
        # An author with no guess to log is a complete run (a guide that
        # left nothing undecided is the goal), never a failed one.
        step = record_step(name, [turn], check.returncode == 0 and bool(files), artifacts,
                           [f"{len(guesses)} guesses; check exited {check.returncode}; {len(files)} files", "the author did not run kapso (the guide forbids it); the driver runs check"])
        step["metrics"] = {"guesses": len(guesses), "check_green": check.returncode == 0, "files": len(files), "structural_gaps": None, "contradictions": None}
        return step


def grade(record: Dict[str, Any], out: Path, clone: Path, settings: dict, ask: Optional[Callable[[str, dict], str]] = None) -> Dict[str, Any]:
    """Classify the write step's guesses on the judge's route, twice with an
    adjudication, the counts into the record's metrics. The guide classified
    against is the one the author read: the run's archived `guide.md` when
    it wrote one, else the clone's pages, and either must hash to the run's
    pin — a grade under a later guide is a different experiment, and raises."""
    steps = [step for step in record["steps"] if step["name"] == "write"]
    if not steps:
        raise RuntimeError("the record has no write step to grade")
    step = steps[0]
    archived = out / "artifacts" / "guide.md"
    guide = archived.read_text(encoding="utf-8") if archived.is_file() else guide_text(clone)
    pinned, actual = record["pins"]["guide_sha256"], hashlib.sha256(guide.encode("utf-8")).hexdigest()
    if actual != pinned:
        raise RuntimeError(f"the guide to grade against hashes to {actual[:12]}, not the run's pin {pinned[:12]}: grade against the guide the author read (check that commit out), never a later one")
    guesses_md = out / "artifacts" / "write-guesses.md"
    guesses = parse_guesses(guesses_md.read_text(encoding="utf-8")) if guesses_md.is_file() else []
    classified = classify_twice(guesses, guide, settings, ask or judge_module.ask, out / judge_module.JUDGE_DIR)
    step["classification"] = classified
    step["metrics"]["structural_gaps"] = structural_gaps(classified)
    step["metrics"]["contradictions"] = len(contradictions(classified))
    (out / "artifacts" / "write-classification.json").write_text(json.dumps(classified, indent=2), encoding="utf-8")
    record["metrics"] = run_metrics(record)
    return record


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--clone", default=None)
    parser.add_argument("--out", required=True)
    parser.add_argument("--host", default="claude_code", choices=["claude_code", "codex"])
    parser.add_argument("--machine", default=os.uname().nodename)
    parser.add_argument("--advisory", default=None)
    parser.add_argument("--grade", action="store_true")
    args = parser.parse_args(argv)
    if args.clone is None:
        parser.error("--clone is the checkout whose guide the author reads (and the grade classifies against)")
    driver = Author(args)
    record_file = driver.out / "record.json"
    started = datetime.now(timezone.utc)
    record = json.loads(record_file.read_text()) if record_file.exists() else {
        "test": "author", "host": args.host, "machine": args.machine, "run_id": f"author-{args.host}-{started.strftime('%Y%m%dT%H%M%SZ')}", "advisory": args.advisory,
        "package": {"version": subprocess.run(["kapso", "--version"], capture_output=True, text=True).stdout.strip().split()[-1], "wheel_sha256": "-"},
        "pins": {"suite_sha256": hashlib.sha256(plugin_proof.SUITE_PATH.read_bytes()).hexdigest(), "pages": GUIDE_PAGES, "example": EXAMPLE,
                 "guide_sha256": hashlib.sha256(guide_text(driver.clone).encode("utf-8")).hexdigest()},
        "user": {"kind": "scripted", "card": None, "interventions": ["the author holds only the guide pages, the reference and the trading example; it may not run kapso; the driver runs check and classifies the guesses"], "events": [], "pushback": None},
        "started": started.isoformat(timespec="seconds"), "finished": None, "steps": [], "metrics": {}, "notes": [note for note in [codex_session_note()] if note], "transcripts": [],
    }
    if args.grade:
        record = grade(record, driver.out, driver.clone, SUITE["judge"])
        record_file.write_text(json.dumps(record, indent=1) + "\n", encoding="utf-8")
        print(json.dumps(record["metrics"]))
        return 0
    for name in STEP_NAMES:
        print(f"== {name}", flush=True)
        step = driver.step_write()
        record["steps"] = [existing for existing in record["steps"] if existing["name"] != name] + [step]
        record["finished"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
        record["transcripts"] = sorted(f"transcripts/{path.name}" for path in (driver.out / "transcripts").glob("*.jsonl"))
        record_file.write_text(json.dumps(record, indent=1) + "\n", encoding="utf-8")
        print(json.dumps({key: value for key, value in step.items() if key not in ("notes", "classification")}), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
