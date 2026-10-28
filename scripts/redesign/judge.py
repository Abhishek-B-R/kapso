"""The judge of the semantic suite (docs/plans/redesign/wp9-semantic-
suite.md, change 5): a standalone pass on the development box over a
fetched record directory. For a conversation rubric (S2) each conversation
step is rendered as the user's messages and each turn's final text with
numbered lines, judged in one model call, in two blind passes; the run's
score per dimension is the minimum over steps (the worst step binds); a
dimension whose passes straddle the bar gets a third, adjudicating pass.
For the other rubrics the driver writes the inputs (a reader's answers
with the fact sheet, an author's harness with its guess log) and names
them. The reply must be exactly one JSON object (a code fence around it
allowed) with exactly the rubric's dimensions, integer scores in the
scale, and evidence entries whose quote occurs at the line they name;
anything else is a judge failure with the raw reply kept, never a pass.
The vendor is Gemini on Vertex through LiteLLM, from the suite's one
home; `--preflight` makes one small call before any machine runs.

    python3 judge.py <record-dir> --rubric s2
    python3 judge.py <record-dir> --rubric s4 --inputs judge/reading-claude_code.md judge/reading-codex.md
    python3 judge.py --preflight
"""

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

import litellm

SUITE_PATH = Path(__file__).resolve().parent.parent.parent / "tests" / "semantic" / "suite.json"
RUBRICS = Path(__file__).resolve().parent.parent.parent / "tests" / "semantic" / "rubrics"
JUDGE_DIR = "judge"
CONTRACT = (
    "Reply with exactly one JSON object and nothing else (a ```json fence around it is allowed): "
    '{"scores": {"<dimension>": {"score": <integer in [{low}, {high}]>, "evidence": [{"where": "<file>:L<line>", "quote": "<the line\'s words, verbatim>"}]}}, "notes": "<optional>"}. '
    "One entry per dimension, every dimension of the rubric, no other. Each dimension's evidence list "
    "has at least one entry, and each entry names a line of the material below by its exact file and "
    "`L<line>` label and quotes words that occur on that line. A score with an empty evidence list, or "
    "evidence that does not quote the material, is not allowed."
)
FENCE = re.compile(r"^```(?:json)?\s*\n(.*?)\n```\s*$", re.S)


class JudgeFailure(Exception):
    """The judge's reply broke the contract: a judge failure, kept apart
    from a product failure, never a pass."""


def load_suite() -> dict:
    return json.loads(SUITE_PATH.read_text(encoding="utf-8"))


# ---------------------------------------------------------------- rendering
def final_texts(rows: Sequence[dict]) -> List[Dict[str, str]]:
    """The conversation a transcript holds: the user's messages (the proof's
    prompts and the persona's replies) and each turn's final text (the
    Claude Code `result` row, or the last Codex `agent_message` before the
    next prompt)."""
    turns: List[Dict[str, str]] = []
    pending: Optional[str] = None
    for row in rows:
        if "proof_prompt" in row:
            if pending is not None:
                turns.append({"role": "assistant", "text": pending})
                pending = None
            turns.append({"role": "user", "text": row["proof_prompt"]})
        elif "persona_reply" in row:
            if pending is not None:
                turns.append({"role": "assistant", "text": pending})
                pending = None
            turns.append({"role": "user", "text": row["persona_reply"]})
        elif row.get("type") == "result":
            turns.append({"role": "assistant", "text": row.get("result") or ""})
            pending = None
        elif row.get("type") == "item.completed" and (row.get("item") or {}).get("type") == "agent_message":
            pending = row["item"].get("text") or ""
    if pending is not None:
        turns.append({"role": "assistant", "text": pending})
    return turns


def render_step(name: str, rows: Sequence[dict]) -> str:
    """The step's conversation with numbered lines (`L<n>`), the file a
    judge cites."""
    lines = [f"# step {name}", ""]
    for turn in final_texts(rows):
        lines.append(f"[{turn['role']}]")
        lines.extend(turn["text"].splitlines() or [""])
        lines.append("")
    return "\n".join(f"L{number}: {line}" for number, line in enumerate(lines, 1)) + "\n"


def transcript_rows(path: Path) -> List[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.startswith("{")]


# ----------------------------------------------------------------- contract
def extract_json(reply: str) -> dict:
    text = reply.strip()
    match = FENCE.match(text)
    if match:
        text = match.group(1).strip()
    if not (text.startswith("{") and text.endswith("}")):
        raise JudgeFailure("the reply is not one JSON object")
    # Model output: a malformed object is a contract break (a judge
    # failure), not an uncaught crash that leaves a stale block.
    try:
        data = json.loads(text)
    except json.JSONDecodeError as error:
        raise JudgeFailure(f"the reply is not valid JSON: {error}") from error
    if not isinstance(data, dict):
        raise JudgeFailure("the reply's JSON is not an object")
    return data


def validate(data: dict, dimensions: Sequence[str], scale: Sequence[int], root: Path, allowed: Sequence[str]) -> Dict[str, Dict[str, Any]]:
    """The scores against the rubric: exactly its dimensions, integers in
    the scale, at least one evidence entry per dimension, each quoting a
    line of one of the `allowed` material files (never another file)."""
    allowed_set = set(allowed)
    scores = data.get("scores")
    if not isinstance(scores, dict) or set(scores) != set(dimensions):
        raise JudgeFailure(f"the dimensions are {sorted(scores) if isinstance(scores, dict) else scores!r}, not {sorted(dimensions)}")
    low, high = scale
    for dimension, entry in scores.items():
        score = entry.get("score") if isinstance(entry, dict) else None
        if not isinstance(score, int) or isinstance(score, bool) or not low <= score <= high:
            raise JudgeFailure(f"{dimension}: the score {score!r} is not an integer in [{low}, {high}]")
        evidence = entry.get("evidence")
        if not isinstance(evidence, list) or not evidence:
            raise JudgeFailure(f"{dimension}: evidence is empty or not a list (a score needs a quote)")
        for item in evidence:
            where, quote = (item.get("where"), item.get("quote")) if isinstance(item, dict) else (None, None)
            if not isinstance(where, str) or not isinstance(quote, str) or not quote.strip() or ":L" not in where:
                raise JudgeFailure(f"{dimension}: an evidence entry lacks `where` as <file>:L<line> or a non-empty `quote`")
            file, _, label = where.rpartition(":L")
            if file not in allowed_set:
                raise JudgeFailure(f"{dimension}: {where} cites {file!r}, not the material ({sorted(allowed_set)})")
            path = root / file
            if not path.is_file() or not label.isdigit():
                raise JudgeFailure(f"{dimension}: {where} names no line of a file under the record")
            if not quote_on(path.read_text(encoding="utf-8").splitlines(), label, quote):
                raise JudgeFailure(f"{dimension}: the quote {quote!r} is not on {where}")
    return scores


def quote_on(lines: Sequence[str], label: str, quote: str) -> bool:
    """The quote starts on line `label` (1-based): on that line, or across
    it and the lines after it, whitespace folded — a judge quoting a
    sentence the rendering wrapped cites the line it starts on."""
    number = int(label)
    if not 1 <= number <= len(lines):
        return False
    def folded(text: str) -> str:
        # The text with its `L<n>: ` number, a leading bullet, heading or
        # quote mark, inline emphasis and code marks, and runs of whitespace
        # folded away — a judge quotes the words, not the markdown around
        # them, and drops a different mark each time (both sides fold alike).
        text = re.sub(r"^L\d+:\s?", "", text)
        text = re.sub(r"^(?:[-*+>]|\d+\.|#{1,6})\s+", "", text)
        return " ".join(re.sub(r"[*_`~]", "", text).split())
    wanted = folded(quote)
    first = folded(lines[number - 1])
    window = " ".join([first, *(folded(line) for line in lines[number:number + 3])])
    start = window.find(wanted) if wanted else -1
    return 0 <= start < len(first)   # it begins on the cited line, whatever it runs on to


# ------------------------------------------------------------------- calls
def ask(prompt: str, settings: dict) -> str:
    response = litellm.completion(
        model=settings["model"], messages=[{"role": "user", "content": prompt}],
        vertex_project=settings["vertex_project"], vertex_location=settings["vertex_location"],
    )
    return response.choices[0].message.content or ""


def judge_material(material: str, rubric_text: str, dimensions: Sequence[str], scale: Sequence[int], settings: dict, root: Path, archive: Path, label: str, allowed: Sequence[str]) -> Dict[str, Any]:
    """One judging call on one piece of material: the prompt and the raw
    reply archived (before validation, so a contract break keeps its
    evidence), the scores validated against the rubric and the material's
    own file (never another file)."""
    contract = CONTRACT.replace("{low}", str(scale[0])).replace("{high}", str(scale[1]))
    prompt = f"{rubric_text}\n\n{contract}\n\nThe material:\n\n{material}"
    (archive / f"prompt-{label}.md").write_text(prompt, encoding="utf-8")
    reply = ask(prompt, settings)
    (archive / f"raw-{label}.txt").write_text(reply, encoding="utf-8")
    data = extract_json(reply)
    # A quote that is not on its cited line, the reply otherwise in shape,
    # is the model's citation slip (two of ten judge runs on 2026-10-28
    # lost their whole report to one): one re-ask, archived beside the
    # first; a second slip fails loud in validate as before.
    if misquoted(data, root):
        reply = ask(prompt, settings)
        (archive / f"raw-{label}-retry.txt").write_text(reply, encoding="utf-8")
        data = extract_json(reply)
    return validate(data, dimensions, scale, root, allowed)


def misquoted(data: dict, root: Path) -> bool:
    """True when some evidence entry's quote is not on the line it cites,
    with everything on the way there well formed; any other fault is left
    to validate, which names it."""
    scores = data.get("scores")
    if not isinstance(scores, dict):
        return False
    for entry in scores.values():
        evidence = entry.get("evidence") if isinstance(entry, dict) else None
        for item in evidence if isinstance(evidence, list) else []:
            where, quote = (item.get("where"), item.get("quote")) if isinstance(item, dict) else (None, None)
            if not isinstance(where, str) or not isinstance(quote, str) or ":L" not in where:
                return False
            file, _, label = where.rpartition(":L")
            path = root / file
            if not path.is_file() or not label.isdigit():
                return False
            if not quote_on(path.read_text(encoding="utf-8").splitlines(), label, quote):
                return True
    return False


def gather_materials(record_dir: Path, record: dict, inputs: Optional[Sequence[str]], archive: Path) -> Dict[str, Dict[str, str]]:
    """Each thing judged, as {label: {file, text}}: the named inputs, or
    every conversation step rendered with ALL of its transcripts (the step
    and its follow-ups, `<step>*.jsonl`), so the judge sees the whole
    exchange. A conversation step with no transcript raises (Rule 2: a
    broken record is not a smaller judged surface)."""
    materials: Dict[str, Dict[str, str]] = {}
    if inputs:
        for name in inputs:
            path = record_dir / name
            if not path.is_file():
                raise JudgeFailure(f"the input {name} does not exist under the record")
            numbered = "\n".join(f"L{n}: {line}" for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1))
            materials[Path(name).stem] = {"file": name, "text": f"(file {name})\n{numbered}"}
        return materials
    for step in record["steps"]:
        if step.get("deferred") or step.get("kind", "conversation") != "conversation":
            continue
        transcripts = sorted((record_dir / "transcripts").glob(f"{step['name']}*.jsonl"))
        if not transcripts and step.get("messages") == 0:
            # No exchange happened (a conversation step the host did not
            # run, recorded with zero messages): nothing to judge, not a
            # broken record.
            continue
        if not transcripts:
            raise JudgeFailure(f"the conversation step {step['name']} has no transcript to judge")
        rows: List[dict] = []
        for transcript in transcripts:
            rows.extend(transcript_rows(transcript))
        rendered = archive / f"{step['name']}.rendered.md"
        rendered.write_text(render_step(step["name"], rows), encoding="utf-8")
        file_label = f"{JUDGE_DIR}/{rendered.name}"
        materials[step["name"]] = {"file": file_label, "text": f"(file {file_label})\n" + rendered.read_text(encoding="utf-8")}
    return materials


def judge_record(record_dir: Path, rubric: str, inputs: Optional[Sequence[str]], suite: dict) -> dict:
    """Judge a record in place: the conversation steps (rubric s2) or the
    named inputs; `passes` blind passes, each straddling item adjudicated;
    the record's `judge` block written, a contract break recorded as a
    failure (never a pass). A pending non-passing block is written first,
    so a crash mid-judging never leaves a stale pass on disk."""
    record_path = record_dir / "record.json"
    record = json.loads(record_path.read_text(encoding="utf-8"))
    spec = suite["tests"][record["test"]]["judge"]
    if spec is None or spec["rubric"] != rubric:
        raise ValueError(f"{record['test']} is judged by the rubric {spec and spec['rubric']!r}, not {rubric!r}")
    settings = suite["judge"]
    archive = record_dir / JUDGE_DIR
    archive.mkdir(exist_ok=True)
    rubric_text = (RUBRICS / f"{rubric}.md").read_text(encoding="utf-8")
    dimensions, scale, bar = spec["dimensions"], spec["scale"], spec["bar"]
    block: Dict[str, Any] = {"vendor": settings["vendor"], "model": settings["model"], "route": "litellm vertex_ai", "rubric": rubric,
                             "passes": [], "adjudication": {}, "failure": "judging did not complete", "prompt_path": f"{JUDGE_DIR}/", "raw_paths": []}

    def persist() -> None:
        record["judge"] = block
        record_path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")

    persist()
    materials = gather_materials(record_dir, record, inputs, archive)
    if not materials:
        raise JudgeFailure("nothing to judge: the record has no judged material")
    for number in range(1, settings["passes"] + 1):
        items: Dict[str, Dict[str, Dict[str, Any]]] = {}
        for label, material in materials.items():
            block["raw_paths"].append(f"{JUDGE_DIR}/raw-{label}-pass{number}.txt")
            persist()
            items[label] = judge_material(material["text"], rubric_text, dimensions, scale, settings, record_dir, archive, f"{label}-pass{number}", [material["file"]])
        block["passes"].append({"items": items})
        persist()
    # Each straddling (dimension, item) gets an adjudicating pass; the
    # minimum over items then binds per dimension (report.py resolves it).
    for dimension in dimensions:
        for label, material in materials.items():
            scores = [block["passes"][number]["items"][label][dimension]["score"] for number in range(len(block["passes"]))]
            if min(scores) < bar <= max(scores):
                raw_label = f"{label}-adjudication-{dimension}"
                block["raw_paths"].append(f"{JUDGE_DIR}/raw-{raw_label}.txt")
                persist()
                third = judge_material(material["text"], rubric_text, dimensions, scale, settings, record_dir, archive, raw_label, [material["file"]])
                block["adjudication"][f"{dimension}|{label}"] = {"score": third[dimension]["score"], "evidence": third[dimension]["evidence"]}
    block["failure"] = None
    persist()
    return block


def resolve_items(block: dict, dimensions: Sequence[str], bar: int) -> Dict[str, Dict[str, Optional[int]]]:
    """Each judged item's resolved score per dimension: a straddling item's
    adjudication deciding, else the minimum over passes; None when a pass
    did not score it. The one way to read a block per item (S4 grades each
    reader this way); `resolve` collapses it to the worst item."""
    passes = block.get("passes", [])
    adjudication = block.get("adjudication", {})
    labels = sorted({label for a_pass in passes for label in a_pass.get("items", {})})
    resolved: Dict[str, Dict[str, Optional[int]]] = {}
    for label in labels:
        resolved[label] = {}
        for dimension in dimensions:
            scores = [a_pass.get("items", {}).get(label, {}).get(dimension, {}).get("score") for a_pass in passes]
            if any(score is None for score in scores):
                resolved[label][dimension] = None
                continue
            straddled = min(scores) < bar <= max(scores)
            adjudicated = adjudication.get(f"{dimension}|{label}", {}).get("score")
            resolved[label][dimension] = adjudicated if straddled and adjudicated is not None else min(scores)
    return resolved


def resolve(block: dict, dimensions: Sequence[str], bar: int) -> Dict[str, Optional[int]]:
    """The final score per dimension: the minimum over the judged items of
    each item's resolved score (the worst item binds). None when no item is
    fully scored, so a broken block never silently passes. report.py and S1
    read a block this way."""
    items = resolve_items(block, dimensions, bar)
    finals: Dict[str, Optional[int]] = {}
    for dimension in dimensions:
        values = [items[label][dimension] for label in items if items[label][dimension] is not None]
        finals[dimension] = min(values) if values and len(values) == len(items) else None
    return finals


def preflight(suite: dict) -> str:
    settings = suite["judge"]
    reply = ask('Reply with exactly one JSON object: {"ok": true}', settings)
    data = extract_json(reply)
    if data.get("ok") is not True:
        raise JudgeFailure(f"the route answered {reply[:200]!r}")
    return f"the judge's route answers: {settings['model']} via litellm vertex_ai"


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("record_dir", nargs="?", help="the fetched record's directory (record.json, transcripts/, artifacts/)")
    parser.add_argument("--rubric", choices=["s2", "s4", "s1", "author"], help="the rubric under tests/semantic/rubrics/")
    parser.add_argument("--inputs", nargs="*", default=None, help="files under the record directory to judge instead of the conversation steps")
    parser.add_argument("--preflight", action="store_true", help="one small call on the route, before any machine runs")
    args = parser.parse_args(argv)
    suite = load_suite()
    if args.preflight:
        print(preflight(suite))
        return 0
    if not args.record_dir or not args.rubric:
        parser.error("a record directory and --rubric, or --preflight")
    block = judge_record(Path(args.record_dir).resolve(), args.rubric, args.inputs, suite)
    if block["failure"]:
        print(f"judge failure: {block['failure']}")
        return 2
    for label, dimensions in block["passes"][0]["items"].items():
        for dimension in dimensions:
            scores = [p["items"][label][dimension]["score"] for p in block["passes"]]
            adjudicated = block["adjudication"].get(f"{dimension}|{label}", {}).get("score")
            print(f"{label} / {dimension}: {scores}" + (f" adjudicated {adjudicated}" if adjudicated is not None else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
