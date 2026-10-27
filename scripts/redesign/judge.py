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
    "One entry per dimension, every dimension of the rubric, no other. Each evidence entry names a line of the material below by its file and line label and quotes words that occur on that line."
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
    data = json.loads(text)
    if not isinstance(data, dict):
        raise JudgeFailure("the reply's JSON is not an object")
    return data


def validate(data: dict, dimensions: Sequence[str], scale: Sequence[int], root: Path) -> Dict[str, Dict[str, Any]]:
    """The scores against the rubric: exactly its dimensions, integers in
    the scale, evidence at the lines it names."""
    scores = data.get("scores")
    if not isinstance(scores, dict) or set(scores) != set(dimensions):
        raise JudgeFailure(f"the dimensions are {sorted(scores) if isinstance(scores, dict) else scores!r}, not {sorted(dimensions)}")
    low, high = scale
    for dimension, entry in scores.items():
        score = entry.get("score") if isinstance(entry, dict) else None
        if not isinstance(score, int) or isinstance(score, bool) or not low <= score <= high:
            raise JudgeFailure(f"{dimension}: the score {score!r} is not an integer in [{low}, {high}]")
        evidence = entry.get("evidence")
        if not isinstance(evidence, list):
            raise JudgeFailure(f"{dimension}: evidence is not a list")
        for item in evidence:
            where, quote = (item.get("where"), item.get("quote")) if isinstance(item, dict) else (None, None)
            if not isinstance(where, str) or not isinstance(quote, str) or ":L" not in where:
                raise JudgeFailure(f"{dimension}: an evidence entry lacks `where` as <file>:L<line> or `quote`")
            file, _, label = where.rpartition(":L")
            path = root / file
            if not path.is_file() or not label.isdigit():
                raise JudgeFailure(f"{dimension}: {where} names no line of a file under the record")
            lines = path.read_text(encoding="utf-8").splitlines()
            number = int(label)
            if not 1 <= number <= len(lines) or quote.strip() not in lines[number - 1]:
                raise JudgeFailure(f"{dimension}: the quote {quote!r} is not on {where}")
    return scores


# ------------------------------------------------------------------- calls
def ask(prompt: str, settings: dict) -> str:
    response = litellm.completion(
        model=settings["model"], messages=[{"role": "user", "content": prompt}],
        vertex_project=settings["vertex_project"], vertex_location=settings["vertex_location"],
    )
    return response.choices[0].message.content or ""


def judge_material(material: str, rubric_text: str, dimensions: Sequence[str], scale: Sequence[int], settings: dict, root: Path, archive: Path, label: str) -> Dict[str, Any]:
    """One judging call on one piece of material: the prompt and the raw
    reply archived, the scores validated."""
    contract = CONTRACT.replace("{low}", str(scale[0])).replace("{high}", str(scale[1]))
    prompt = f"{rubric_text}\n\n{contract}\n\nThe material:\n\n{material}"
    (archive / f"prompt-{label}.md").write_text(prompt, encoding="utf-8")
    reply = ask(prompt, settings)
    raw = archive / f"raw-{label}.txt"
    raw.write_text(reply, encoding="utf-8")
    return validate(extract_json(reply), dimensions, scale, root)


def aggregate(per_item: Dict[str, Dict[str, Dict[str, Any]]], dimensions: Sequence[str]) -> Dict[str, Dict[str, Any]]:
    """The run's score per dimension: the minimum over the items judged,
    with the worst item's evidence."""
    scores: Dict[str, Dict[str, Any]] = {}
    for dimension in dimensions:
        worst = min(per_item.items(), key=lambda pair: pair[1][dimension]["score"])
        scores[dimension] = {"score": worst[1][dimension]["score"], "evidence": worst[1][dimension]["evidence"], "worst": worst[0]}
    return scores


def judge_record(record_dir: Path, rubric: str, inputs: Optional[Sequence[str]], suite: dict) -> dict:
    """Judge a record in place: the conversation steps (rubric s2) or the
    named inputs; two passes, a third on a straddle; the record's `judge`
    block written, a failure recorded as such."""
    record_path = record_dir / "record.json"
    record = json.loads(record_path.read_text(encoding="utf-8"))
    spec = suite["tests"][record["test"]]["judge"]
    if spec is None or spec["rubric"] != rubric:
        raise ValueError(f"{record['test']} is judged by the rubric {spec and spec['rubric']!r}, not {rubric!r}")
    settings = suite["judge"]
    archive = record_dir / JUDGE_DIR
    archive.mkdir(exist_ok=True)
    rubric_text = (RUBRICS / f"{rubric}.md").read_text(encoding="utf-8")
    materials: Dict[str, str] = {}
    if inputs:
        for name in inputs:
            materials[Path(name).stem] = f"(file {name})\n" + "\n".join(f"L{n}: {line}" for n, line in enumerate((record_dir / name).read_text(encoding="utf-8").splitlines(), 1))
    else:
        for step in record["steps"]:
            if step.get("deferred") or step.get("kind", "conversation") != "conversation":
                continue
            transcript = record_dir / "transcripts" / f"{step['name']}.jsonl"
            if not transcript.is_file():
                continue
            rendered = archive / f"{step['name']}.rendered.md"
            rendered.write_text(render_step(step["name"], transcript_rows(transcript)), encoding="utf-8")
            materials[step["name"]] = f"(file {JUDGE_DIR}/{rendered.name})\n" + rendered.read_text(encoding="utf-8")
    block: Dict[str, Any] = {"vendor": settings["vendor"], "model": settings["model"], "route": "litellm vertex_ai", "rubric": rubric,
                             "passes": [], "adjudication": {}, "failure": None, "prompt_path": f"{JUDGE_DIR}/", "raw_paths": []}
    bar = spec["bar"]
    try_passes = settings["passes"]
    for number in range(1, try_passes + 1):
        per_item = {}
        for label, material in materials.items():
            try:
                per_item[label] = judge_material(material, rubric_text, spec["dimensions"], spec["scale"], settings, record_dir, archive, f"{label}-pass{number}")
            except JudgeFailure as failure:
                block["failure"] = f"pass {number}, {label}: {failure}"
                block["raw_paths"].append(f"{JUDGE_DIR}/raw-{label}-pass{number}.txt")
                record["judge"] = block
                record_path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
                return block
            block["raw_paths"].append(f"{JUDGE_DIR}/raw-{label}-pass{number}.txt")
        block["passes"].append({"scores": aggregate(per_item, spec["dimensions"]), "items": per_item})
    for dimension in spec["dimensions"]:
        scores = [p["scores"][dimension]["score"] for p in block["passes"]]
        if min(scores) < bar <= max(scores):
            worst = block["passes"][scores.index(min(scores))]["scores"][dimension]["worst"]
            try:
                third = judge_material(materials[worst], rubric_text, spec["dimensions"], spec["scale"], settings, record_dir, archive, f"{worst}-adjudication-{dimension}")
            except JudgeFailure as failure:
                block["failure"] = f"adjudication of {dimension} on {worst}: {failure}"
                break
            block["adjudication"][dimension] = {"score": third[dimension]["score"], "evidence": third[dimension]["evidence"], "item": worst}
    record["judge"] = block
    record_path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    return block


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
    for dimension, entry in block["passes"][0]["scores"].items():
        scores = [p["scores"][dimension]["score"] for p in block["passes"]]
        adjudicated = block["adjudication"].get(dimension, {}).get("score")
        print(f"{dimension}: {scores}" + (f" adjudicated {adjudicated}" if adjudicated is not None else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
