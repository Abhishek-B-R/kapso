"""The Codex half of the plugin's trigger suite (docs/plans/redesign/
wp7-plugin.md, change 9): the cases `claude plugin eval` reads under
plugin/evals, each run through `codex exec --json` in a bare project
whose `.agents/skills` holds the plugin's skills; the skills the session
loaded read from the stream (the command that read a `SKILL.md`) and
from the session's rollout (the `<skill>` message an explicit `$name`
invocation injects); the cases' Skill graders applied to what was
loaded. Explicit cases are Claude Code's `/kapso:<cmd>` and are skipped:
Codex's explicit form is `$kapso-<skill>`, proven in the host facts.

A Codex session loads a skill by reading its file, and reads several as
references (the build skill sends it to the evaluation skill, the
harness skill to the operating one), so a near miss that read the skill
under test beside the expected one routed right: its refusal grader
passes when the expected skill was loaded too, and the report names the
first skill read, the routing decision as Claude Code's Skill tool shows
it. A case with no expected skill stays strict.

    scripts/redesign/plugin_round.sh codex-triggers [--tag main] [--case 'build-*'] [--runs 2] [-j 4]
    python3 scripts/redesign/codex_triggers.py --regrade <out-dir>    # the rule again over a run's results

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
SUITE_PATH = ROOT / "tests" / "semantic" / "suite.json"
DEFAULT_SANDBOX = json.loads(SUITE_PATH.read_text(encoding="utf-8"))["triggers"]["codex_sandbox"]
SKILL_FILE = re.compile(r"skills/([\w-]+)/SKILL\.md")
SKILL_TAG = re.compile(r"<skill>\s*<name>([\w-]+)</name>")
SKIPPED_KIND = "explicit"
# A session whose sandbox never came up: codex's bwrap sandbox fails on a
# machine without user-namespace networking ("bwrap: loopback: Failed
# RTM_NEWADDR: Operation not permitted"), and the session announces the
# skill it means to read and cannot read it. That is the machine's failure,
# never a trigger miss; it is classified as such from the session's own
# words (s2-codex-5: 123 of 138 failed runs said it).
SANDBOX_FAILURE = re.compile(r"bwrap: [^\n\"\\]*")


def sandbox_failure(stream_file: Path) -> Optional[str]:
    """The sandbox failure a run reported, from its stderr and its stream
    (the host repeats bwrap's line in its message), or None."""
    for path in (stream_file.with_suffix(".err"), stream_file):
        if path.is_file():
            match = SANDBOX_FAILURE.search(path.read_text(encoding="utf-8", errors="replace"))
            if match:
                return match.group(0).strip()
    return None


def probe_sandbox(sandbox: str, out: Path) -> None:
    """One session under the chosen sandbox before the suite runs: a
    sandbox that cannot start fails every run the same way, so the suite
    stops here with the fix named rather than grading a hundred broken runs."""
    project = out / "work" / "sandbox-probe"
    project.mkdir(parents=True, exist_ok=True)
    probe = subprocess.run(["timeout", "180", "codex", "exec", "--json", "--skip-git-repo-check", "--sandbox", sandbox, "-C", str(project), "reply with the word ok"],
                           capture_output=True, text=True, cwd=str(project))
    failure = SANDBOX_FAILURE.search(probe.stderr + probe.stdout)
    if failure:
        raise RuntimeError(f"codex's {sandbox} sandbox does not start on this machine ({failure.group(0).strip()}); run with --sandbox danger-full-access and say so in the record")


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
            item = record["item"]
            # A load is a read that succeeded: a command that names the
            # file without reading it (an `echo`), or that failed, is none.
            inner = re.sub(r"^/bin/\w+ -lc ['\"]", "", item["command"]).lstrip()
            if item.get("exit_code", 0) != 0 or inner.startswith("echo"):
                continue
            for name in SKILL_FILE.findall(item["command"]):
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


def grade(graders: Sequence[Dict[str, Any]], loaded: Sequence[str], started: bool = True) -> List[Dict[str, Any]]:
    """Each Skill grader over the loaded skills, as `claude plugin eval`
    applies it to the Skill tool's JSON input: the count of loads whose
    `{"skill": "<name>"}` matches `input_match`, between min and max. A
    refusal (max 0) fails when the forbidden skill was the first read (the
    session routed to it); a later read beside the expected skill passes,
    marked `read_after` (Codex reads skills as references). A run that
    never started fails every grader: no evidence is not a pass."""
    matches = lambda grader, name: bool(re.search(grader["input_match"], json.dumps({"skill": name})))
    counts = {grader["name"]: sum(1 for name in loaded if matches(grader, name)) for grader in graders}
    expected_loaded = any(counts[g["name"]] >= g["min"] for g in graders if g["max"] != 0)
    results = []
    for grader in graders:
        count = counts[grader["name"]]
        if grader["max"] == 0:
            first = bool(loaded) and matches(grader, loaded[0])
            passed = started and (count == 0 or (expected_loaded and not first))
            results.append({"name": grader["name"], "count": count, "passed": passed, "read_after": passed and count > 0})
        else:
            passed = started and count >= grader["min"] and (grader["max"] is None or count <= grader["max"])
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


def run_case(case: Dict[str, Any], run: int, out: Path, model: str, effort: str, timeout: int, sandbox: str) -> Dict[str, Any]:
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
            ["timeout", str(timeout), "codex", "exec", "--json", "--skip-git-repo-check", "--sandbox", sandbox, "-C", str(project),
             "-m", model, "-c", f'model_reasoning_effort="{effort}"', case["prompt"]],
            stdout=stream, stderr=err, text=True, cwd=str(project),
        )
    lines = stream_file.read_text(encoding="utf-8").splitlines()
    begun = any('"thread.started"' in line for line in lines)
    loaded = loaded_skills(lines, rollout_lines(thread_id(lines))) if begun else []
    graders = grade(case["graders"], loaded, begun)
    environment = sandbox_failure(stream_file)
    return {
        "case": case["name"], "run": run, "exit": completed.returncode, "seconds": round(time.monotonic() - started, 1),
        "started": begun, "loaded": loaded, "graders": graders, "environment": environment,
        "passed": environment is None and all(g["passed"] for g in graders),
    }


def report(results: List[Dict[str, Any]], skipped: List[str]) -> str:
    by_case: Dict[str, List[Dict[str, Any]]] = {}
    for result in results:
        by_case.setdefault(result["case"], []).append(result)
    lines = ["| case | runs | passed | first read | loaded | read after | sandbox failures |", "|---|---|---|---|---|---|---|"]
    failed, read_after, environment = 0, 0, 0
    for name, runs in by_case.items():
        passed = sum(1 for r in runs if r["passed"])
        failed += passed < len(runs)
        loaded = sorted({skill for r in runs for skill in r["loaded"]})
        first = sorted({r["loaded"][0] for r in runs if r["loaded"]})
        later = sum(1 for r in runs for g in r["graders"] if g.get("read_after"))
        read_after += later > 0
        broken = sum(1 for r in runs if r.get("environment"))
        environment += broken
        lines.append(f"| {name} | {len(runs)} | {passed}/{len(runs)} | {', '.join(first) or '(none)'} | {', '.join(loaded) or '(none)'} | {later} | {broken} |")
    lines.append("")
    lines.append(f"{len(by_case) - failed} of {len(by_case)} cases passed every run; "
                 f"{read_after} case(s) read a forbidden skill after the expected one (a pass under the host's rule, a first read would have failed); "
                 f"{environment} run(s) failed in the sandbox before any skill could be read (the machine's failure, not established, never a miss); "
                 f"{len(skipped)} explicit case(s) skipped (Codex's explicit form is `$kapso-<skill>`).")
    return "\n".join(lines)


def regrade(out: Path) -> int:
    """The rule again over a run's results: the loads are the evidence,
    the graders and the verdicts are rewritten in place, the report too."""
    document = json.loads((out / "results.json").read_text(encoding="utf-8"))
    graders = {case["name"]: case["graders"] for case in cases(tag=document["tag"])}
    for result in document["results"]:
        result["graders"] = grade(graders[result["case"]], result["loaded"], result.get("started", True))
        result["environment"] = sandbox_failure(out / "streams" / f"{result['case']}-{result['run']}.jsonl")
        result["passed"] = result["environment"] is None and all(g["passed"] for g in result["graders"])
    (out / "results.json").write_text(json.dumps(document, indent=1) + "\n", encoding="utf-8")
    text = report(document["results"], document["skipped"])
    (out / "REPORT.md").write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0 if all(r["passed"] for r in document["results"]) else 1


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--tag", default="main")
    parser.add_argument("--case", default=None, help="a glob on case names")
    parser.add_argument("--runs", type=int, default=2)
    parser.add_argument("--model", default="gpt-6-astra")
    parser.add_argument("--effort", default="medium")
    parser.add_argument("--timeout", type=int, default=600, help="seconds per run; a run that overstays ends with exit 124 and counts as it stands")
    parser.add_argument("--sandbox", default=DEFAULT_SANDBOX, help="codex's sandbox for the sessions (the suite's triggers.codex_sandbox); a machine whose bwrap cannot start needs danger-full-access, said in the record")
    parser.add_argument("-j", "--jobs", type=int, default=2)
    parser.add_argument("--out", default=None)
    parser.add_argument("--regrade", default=None, help="a run's output directory: grade its results again, run nothing")
    args = parser.parse_args(argv)
    if args.regrade:
        return regrade(Path(args.regrade))
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    selected = cases(tag=args.tag, pattern=args.case)
    skipped = [case["name"] for case in selected if SKIPPED_KIND in case["tags"]]
    selected = [case for case in selected if SKIPPED_KIND not in case["tags"]]
    jobs = [(case, run) for case in selected for run in range(1, args.runs + 1)]
    probe_sandbox(args.sandbox, out)
    with ThreadPoolExecutor(max_workers=args.jobs) as pool:
        results = list(pool.map(lambda job: run_case(job[0], job[1], out, args.model, args.effort, args.timeout, args.sandbox), jobs))
    (out / "results.json").write_text(json.dumps({
        "model": args.model, "effort": args.effort, "runs": args.runs, "tag": args.tag, "sandbox": args.sandbox,
        "skipped": skipped, "results": results,
    }, indent=1) + "\n", encoding="utf-8")
    text = report(results, skipped)
    print(text)
    return 0 if all(r["passed"] for r in results) else 1


if __name__ == "__main__":
    sys.exit(main())
