"""The Codex half of the plugin's trigger suite (docs/plans/redesign/
wp7-plugin.md, change 9): the cases `claude plugin eval` reads under
plugin/evals, each run through `codex exec --json` in a bare project
whose `.agents/skills` holds the plugin's skills; the skills the session
loaded read from the stream (the command that read a `SKILL.md`) and
from the session's rollout (the `<skill>` message an explicit `$name`
invocation injects); the cases' Skill graders applied to what was
loaded. Explicit cases are Claude Code's `/kapso:<cmd>` and are skipped:
Codex's explicit form is `$kapso-<skill>`, proven in the host facts.

    scripts/redesign/plugin_round.sh codex-triggers [--tag main] [--case 'build-*'] [--runs 2] [-j 4]

A stream or rollout line of a shape this module does not know raises:
the fixture tests/fixtures/codex_trigger_events.jsonl pins the shapes.
"""

import argparse
import fnmatch
import json
import re
import shutil
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence

from kapso.core.front_matter import read_front_matter

ROOT = Path(__file__).resolve().parent.parent.parent
PLUGIN = ROOT / "plugin"
EVALS = PLUGIN / "evals"
ROLLOUTS = Path.home() / ".codex" / "sessions"
SKILL_FILE = re.compile(r"skills/([\w-]+)/SKILL\.md")
SKILL_TAG = re.compile(r"<skill>\s*<name>([\w-]+)</name>")
SKIPPED_KIND = "explicit"


def cases(evals: Path = EVALS, tag: Optional[str] = None, pattern: Optional[str] = None) -> List[Dict[str, Any]]:
    """The cases under the eval directory: name, tags, prompt and the
    Skill graders (tool_used on Skill with min, max and input_match)."""
    found = []
    for prompt_file in sorted(evals.glob("*/prompt.md")):
        data, body = read_front_matter(prompt_file)
        name = data.get("name", prompt_file.parent.name)
        tags = list(data.get("tags", []))
        if tag is not None and tag not in tags:
            continue
        if pattern is not None and not fnmatch.fnmatch(name, pattern):
            continue
        graders = []
        for grader_file in sorted((prompt_file.parent / "graders").glob("*.md")):
            grader, _ = read_front_matter(grader_file)
            if grader["type"] == "tool_used" and grader["tool"] == "Skill":
                graders.append({"name": grader_file.stem, "input_match": grader["input_match"],
                                "min": grader.get("min", 1), "max": grader.get("max")})
        found.append({"name": name, "tags": tags, "prompt": body.strip(), "graders": graders})
    return found


def loaded_skills(stream: Iterable[str], rollout: Iterable[str]) -> List[str]:
    """The skills a session loaded, in order, once each: from the
    stream, every completed command that read a `skills/<name>/SKILL.md`;
    from the rollout, every user message that begins with the `<skill>`
    block an explicit invocation injects."""
    loaded: List[str] = []

    def note(name: str) -> None:
        if name not in loaded:
            loaded.append(name)

    for line in stream:
        record = json.loads(line)
        if record["type"] == "item.completed" and record["item"]["type"] == "command_execution":
            for name in SKILL_FILE.findall(record["item"]["command"]):
                note(name)
    for line in rollout:
        record = json.loads(line)
        payload = record["payload"]
        if payload.get("type") == "message" and payload["role"] == "user":
            for part in payload["content"]:
                if part["type"] == "input_text" and part["text"].lstrip().startswith("<skill>"):
                    note(SKILL_TAG.search(part["text"]).group(1))
    return loaded


def thread_id(stream: Iterable[str]) -> str:
    for line in stream:
        record = json.loads(line)
        if record["type"] == "thread.started":
            return record["thread_id"]
    raise ValueError("no thread.started event in the stream")


def grade(graders: Sequence[Dict[str, Any]], loaded: Sequence[str]) -> List[Dict[str, Any]]:
    """Each Skill grader over the loaded skills, as `claude plugin eval`
    applies it to the Skill tool's JSON input: the count of loads whose
    `{"skill": "<name>"}` matches `input_match`, between min and max."""
    results = []
    for grader in graders:
        count = sum(1 for name in loaded if re.search(grader["input_match"], json.dumps({"skill": name})))
        passed = count >= grader["min"] and (grader["max"] is None or count <= grader["max"])
        results.append({"name": grader["name"], "count": count, "passed": passed})
    return results


def rollout_lines(thread: str, wait_seconds: float = 10.0) -> List[str]:
    """The session's rollout file, named by its thread id; written by the
    time the stream ends, read again for a few seconds in case the host
    is still flushing it."""
    deadline = time.monotonic() + wait_seconds
    while True:
        matches = list(ROLLOUTS.glob(f"**/rollout-*-{thread}.jsonl"))
        if matches:
            return matches[0].read_text(encoding="utf-8").splitlines()
        if time.monotonic() > deadline:
            raise FileNotFoundError(f"no rollout for thread {thread} under {ROLLOUTS}")
        time.sleep(0.5)


def run_case(case: Dict[str, Any], run: int, out: Path, model: str, effort: str, timeout: int) -> Dict[str, Any]:
    project = out / "work" / f"{case['name']}-{run}"
    if project.exists():
        shutil.rmtree(project)
    shutil.copytree(PLUGIN / "skills", project / ".agents" / "skills")
    stream_file = out / "streams" / f"{case['name']}-{run}.jsonl"
    stream_file.parent.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    # The deadline is the `timeout` command's, so a run that overstays ends
    # with exit 124 and its stream so far, and the suite goes on.
    with open(stream_file, "w", encoding="utf-8") as stream, open(stream_file.with_suffix(".err"), "w", encoding="utf-8") as err:
        completed = subprocess.run(
            ["timeout", str(timeout), "codex", "exec", "--json", "--skip-git-repo-check", "--sandbox", "read-only", "-C", str(project),
             "-m", model, "-c", f'model_reasoning_effort="{effort}"', case["prompt"]],
            stdout=stream, stderr=err, text=True, cwd=str(project),
        )
    lines = stream_file.read_text(encoding="utf-8").splitlines()
    loaded = loaded_skills(lines, rollout_lines(thread_id(lines))) if any('"thread.started"' in line for line in lines) else []
    graders = grade(case["graders"], loaded)
    return {
        "case": case["name"], "run": run, "exit": completed.returncode, "seconds": round(time.monotonic() - started, 1),
        "loaded": loaded, "graders": graders, "passed": all(g["passed"] for g in graders),
    }


def report(results: List[Dict[str, Any]], skipped: List[str]) -> str:
    by_case: Dict[str, List[Dict[str, Any]]] = {}
    for result in results:
        by_case.setdefault(result["case"], []).append(result)
    lines = ["| case | runs | passed | loaded |", "|---|---|---|---|"]
    failed = 0
    for name, runs in by_case.items():
        passed = sum(1 for r in runs if r["passed"])
        failed += passed < len(runs)
        loaded = sorted({skill for r in runs for skill in r["loaded"]})
        lines.append(f"| {name} | {len(runs)} | {passed}/{len(runs)} | {', '.join(loaded) or '(none)'} |")
    lines.append("")
    lines.append(f"{len(by_case) - failed} of {len(by_case)} cases passed every run; "
                 f"{len(skipped)} explicit case(s) skipped (Codex's explicit form is `$kapso-<skill>`).")
    return "\n".join(lines)


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--tag", default="main")
    parser.add_argument("--case", default=None, help="a glob on case names")
    parser.add_argument("--runs", type=int, default=2)
    parser.add_argument("--model", default="gpt-6-astra")
    parser.add_argument("--effort", default="medium")
    parser.add_argument("--timeout", type=int, default=600, help="seconds per run; a run that overstays ends with exit 124 and counts as it stands")
    parser.add_argument("-j", "--jobs", type=int, default=2)
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    selected = cases(tag=args.tag, pattern=args.case)
    skipped = [case["name"] for case in selected if SKIPPED_KIND in case["tags"]]
    selected = [case for case in selected if SKIPPED_KIND not in case["tags"]]
    jobs = [(case, run) for case in selected for run in range(1, args.runs + 1)]
    with ThreadPoolExecutor(max_workers=args.jobs) as pool:
        results = list(pool.map(lambda job: run_case(job[0], job[1], out, args.model, args.effort, args.timeout), jobs))
    (out / "results.json").write_text(json.dumps({
        "model": args.model, "effort": args.effort, "runs": args.runs, "tag": args.tag,
        "skipped": skipped, "results": results,
    }, indent=1) + "\n", encoding="utf-8")
    text = report(results, skipped)
    print(text)
    return 0 if all(r["passed"] for r in results) else 1


if __name__ == "__main__":
    sys.exit(main())
