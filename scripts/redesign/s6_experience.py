"""S6 of the semantic suite (docs/plans/redesign/wp9-semantic-suite.md,
change 9): experience pays, and the record shows why.

Two builds of the churn fixture at the same seed repository, data,
evaluator, config, models and machine type, at the same tiny budget (a
tiny budget delivers little: WP1/WP4/WP6/WP7 delivered 0.845, 0.847,
0.851 and nothing twice; the spread is recorded with the result):

- build one is served nothing and writes to an isolated bank home;
- its campaign is learned (mining, the exam, the update crew's commit),
  banking at least one card in a scope the second build is served;
- build two is served that bank by its head.

Both timelines are sampled at the engine config's heartbeat cadence; the
comparison reads the incumbent's score at each grid point (the anytime
series), the gap per point (build two minus build one), the bank's cards
the second build read and the judge found load-bearing, and the lessons
cited. The bar is the design's: a non-negative gap at every checkpoint
both define and at least one cited lesson, with both builds scoring at
least one observation. A rerun is a second record, never a choice.

The learn's grader roles need Codex, so on a fresh machine the learn runs
on the development box over the fetched build-one campaign (advisory for
smoothness, exact for its product: the bank's commit) and the bank
reaches the machine for build two as a bare remote loaded by reference.

    python3 s6_experience.py --clone <clone> --out <dir> [--learn-model <m>] [--steps a,b] [--advisory <reason>]
"""

import argparse
import hashlib
import json
import math
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent))
import plugin_proof  # noqa: E402
import status_timeline  # noqa: E402
from plugin_proof import SUITE, ClaudeHost, CodexHost, Context, UserMode, codex_session_note, effective_config, learning_on, project_config, record_step, shell_step, status_of, wait_for  # noqa: E402
from status_timeline import heartbeat_seconds  # noqa: E402

BUDGET = SUITE["builds"]["s6"]
# The spread of this budget across the packages, recorded beside the pair
# so one pair is read as a sample, not a verdict (structural provenance).
SPREAD = "WP1/WP4/WP6/WP7 delivered 0.845, 0.847, 0.851 and nothing twice at this budget"
STEP_NAMES = ["build-one", "learn-build-one", "build-two", "review-two", "comparison"]


# --------------------------------------------------------- the pure core
def best_score(row: Dict[str, Any]) -> Optional[float]:
    """The incumbent's score stored in a timeline row, or None."""
    best = (row.get("stored") or {}).get("best")
    if isinstance(best, dict) and isinstance(best.get("score"), (int, float)):
        return float(best["score"])
    if isinstance(best, (int, float)):
        return float(best)
    return None


def last_sample_seconds(timeline: Sequence[Dict[str, Any]]) -> float:
    """Seconds from a timeline's first sample to its last (0 when empty)."""
    rows = [row for row in timeline if row.get("ts")]
    if not rows:
        return 0.0
    return (datetime.fromisoformat(rows[-1]["ts"]) - datetime.fromisoformat(rows[0]["ts"])).total_seconds()


def anytime_series(timeline: Sequence[Dict[str, Any]], cadence: float, horizon: Optional[float] = None) -> List[Tuple[float, Optional[float]]]:
    """The incumbent's best score at each grid point k*cadence from the
    first sample to the horizon, the running max of the scores seen by
    then (None until the first score). The grid's last point is at or
    past the last sample, so a score landing in the final partial
    interval is on it; a horizon past the last sample (the other build
    still running) carries the incumbent forward — a finished build's
    delivered score stands for the rest of the budget."""
    rows = [row for row in timeline if row.get("ts")]
    if not rows:
        return []
    start = datetime.fromisoformat(rows[0]["ts"])
    elapsed = [( (datetime.fromisoformat(row["ts"]) - start).total_seconds(), best_score(row)) for row in rows]
    reach = max(elapsed[-1][0], horizon or 0.0)
    points = math.ceil(reach / cadence - 1e-9) + 1
    series = []
    for step in range(points):
        point = step * cadence
        seen = [score for when, score in elapsed if when <= point + 1e-6 and score is not None]
        series.append((point, max(seen) if seen else None))
    return series


def gap_series(series_two: Sequence[Tuple[float, Optional[float]]], series_one: Sequence[Tuple[float, Optional[float]]]) -> List[Tuple[float, Optional[float]]]:
    """Build two minus build one over the COMMON budget horizon (the grid
    both builds reached), each build's incumbent carried forward by the
    anytime series. None where either build has no score yet at that
    point — a behind-interval, counted separately, never silently dropped
    into a happy minimum."""
    one = {round(point, 6): score for point, score in series_one}
    horizon = min(len(series_two), len(series_one))
    gaps = []
    for point, score_two in series_two[:horizon]:
        score_one = one.get(round(point, 6))
        gaps.append((point, (score_two - score_one) if score_two is not None and score_one is not None else None))
    return gaps


def behind_points(series_two: Sequence[Tuple[float, Optional[float]]], series_one: Sequence[Tuple[float, Optional[float]]]) -> int:
    """Points on the common horizon where build one has a score and build
    two does not: experience arriving late, which the gap must not hide."""
    one = {round(point, 6): score for point, score in series_one}
    horizon = min(len(series_two), len(series_one))
    return sum(1 for point, score_two in series_two[:horizon] if score_two is None and one.get(round(point, 6)) is not None)


def gap_min(gaps: Sequence[Tuple[float, Optional[float]]]) -> Optional[float]:
    defined = [value for _, value in gaps if value is not None]
    return min(defined) if defined else None


def scored_observations(trace: Dict[str, Any]) -> int:
    return sum(1 for attempt in trace.get("attempts", []) if attempt["evaluation"].get("score") is not None)


def served_and_used(trace: Dict[str, Any]) -> Dict[str, Any]:
    """From build two's trace: the bank sources served, the cards the
    sessions read and the judge found load-bearing, and the lessons cited
    (a lesson whose cards any session read or the judge found
    load-bearing)."""
    read: set = set()
    load_bearing: set = set()
    for attempt in trace.get("attempts", []):
        cards = attempt.get("cards") or {}
        read.update(cards.get("read") or [])
        load_bearing.update(cards.get("load_bearing") or [])
    lessons = trace.get("lessons") or []
    # A cited lesson is one the judge found LOAD-BEARING in an attempt
    # (actual use), not one merely read; reading alone does not pay.
    cited = [lesson for lesson in lessons if lesson.get("load_bearing_by")]
    read_only = [lesson for lesson in lessons if any(lesson.get("read_by", {}).values()) and not lesson.get("load_bearing_by")]
    return {
        "served_sources": [lesson["reference"] for lesson in lessons],
        "read": sorted(read),
        "load_bearing": sorted(load_bearing),
        "lessons": lessons,
        "cited": len(cited),
        "read_not_load_bearing": len(read_only),
    }


def review(served: Dict[str, Any], gaps: Sequence[Tuple[float, Optional[float]]], scored: Tuple[int, int]) -> str:
    lines = [
        "# S6 review: what the second build was served, and whether it paid",
        "",
        f"Served sources: {', '.join(served['served_sources']) or 'none'}.",
        f"Cards the sessions read: {', '.join(served['read']) or 'none'}.",
        f"Cards the judge found load-bearing: {', '.join(served['load_bearing']) or 'none'}.",
        f"Lessons cited (load-bearing in an attempt): {served['cited']} of {len(served['lessons'])}.",
        f"Scored observations: build one {scored[0]}, build two {scored[1]}.",
        f"Spread at this budget: {SPREAD}.",
        "",
        "Gap per checkpoint (build two minus build one, seconds → gap):",
    ]
    for point, value in gaps:
        lines.append(f"  {int(point):>6}s  {'—' if value is None else f'{value:+.4f}'}")
    minimum = gap_min(gaps)
    lines.append("")
    lines.append(f"Minimum gap where both define it: {'not established (no common scored point)' if minimum is None else f'{minimum:+.4f}'}.")
    return "\n".join(lines) + "\n"


def card_named(answer: str, card: str) -> bool:
    """Whether a review names a card: by its slug, or by its title's words
    (the slug's words in order, at least the first five), case folded."""
    text = " ".join(answer.lower().replace("-", " ").replace("_", " ").split())
    slug = card.rsplit("/", 1)[-1].removesuffix(".md").lower()
    words = [word for word in slug.replace("_", "-").split("-") if word]
    if not words:
        return False
    if " ".join(words) in text:
        return True
    head = " ".join(words[:5])
    return len(words) >= 5 and head in text


def delivered_score(trace: Dict[str, Any]) -> Optional[float]:
    """The delivered branch's score, resolved to its attempt's evaluation
    (the `delivered` object holds a branch and a commit, no score)."""
    delivered = trace.get("delivered") or {}
    branch = delivered.get("branch")
    for attempt in trace.get("attempts", []):
        if attempt.get("branch") == branch:
            return attempt["evaluation"].get("score")
    return None


def comparison_metrics(trace_one: Dict[str, Any], trace_two: Dict[str, Any], gaps: Sequence[Tuple[float, Optional[float]]], served: Dict[str, Any], behind: int = 0) -> Dict[str, Any]:
    scored = (scored_observations(trace_one), scored_observations(trace_two))
    return {
        "gap_min": gap_min(gaps),
        "behind_points": behind,
        "lessons_cited": served["cited"],
        "scored_observations_min": min(scored),
        "scored_observations": {"build_one": scored[0], "build_two": scored[1]},
        "delivered": {"build_one": delivered_score(trace_one), "build_two": delivered_score(trace_two)},
    }


def run_metrics(record: Dict[str, Any]) -> Dict[str, Any]:
    comparison = next((step for step in record["steps"] if step["name"] == "comparison"), None)
    review = next((step for step in record["steps"] if step["name"] == "review-two"), None)
    if not comparison or not comparison.get("metrics"):
        return {}
    source = comparison["metrics"]
    metrics = {key: source.get(key) for key in ("gap_min", "lessons_cited", "scored_observations_min")}
    metrics["review_names_served_cards"] = (review or {}).get("metrics", {}).get("review_names_served_cards")
    return metrics


# ------------------------------------------------------------ the bank
def bank_head_and_cards(bank: Path) -> Dict[str, Any]:
    """A bank home (a bare repo): its head and its cards, counted from the
    tree (an insight is `insights/<name>.md` but not the index; a procedure
    is `procedures/<name>/card.md`)."""
    if not bank.exists():
        return {"head": None, "cards": [], "count": 0}
    head = subprocess.run(["git", "-C", str(bank), "rev-parse", "HEAD"], capture_output=True, text=True)
    tree = subprocess.run(["git", "-C", str(bank), "ls-tree", "-r", "--name-only", "HEAD"], capture_output=True, text=True)
    if head.returncode != 0 or tree.returncode != 0:
        return {"head": None, "cards": [], "count": 0}
    cards = [path for path in tree.stdout.splitlines()
             if (path.startswith("insights/") and path.endswith(".md") and path != "insights/index.md")
             or (path.startswith("procedures/") and path.endswith("/card.md"))]
    return {"head": head.stdout.strip(), "cards": sorted(cards), "count": len(cards)}


# ---------------------------------------------------------------- driver
class S6:
    def __init__(self, args: argparse.Namespace):
        self.args = args
        self.clone = Path(args.clone).resolve()
        self.out = Path(args.out).resolve()
        self.work = self.out / "work"
        self.work.mkdir(parents=True, exist_ok=True)
        # The host is the coding agent the campaigns' sessions run on
        # (`kapso build --coding-agent`) and the CLI the review runs in;
        # the learn's crews are the config's, on either host.
        self.host_name = args.host
        host = ClaudeHost() if args.host == "claude_code" else CodexHost()
        self.ctx = Context(host, self.clone, self.work, self.out, None, args.machine, learn_model=args.learn_model, user=UserMode("scripted", args.host))
        self.cadence = heartbeat_seconds() if args.cadence is None else args.cadence
        self.bank = self.out / "bank-one.git"
        self.samplers: Dict[str, subprocess.Popen] = {}

    def trace(self, campaign: Path) -> Dict[str, Any]:
        run = self.ctx.shell(f"kapso trace {campaign} --json", check=False)
        return json.loads(run.stdout) if run.returncode == 0 and run.stdout.strip() else {}

    def timeline(self, name: str) -> List[Dict[str, Any]]:
        path = self.out / "artifacts" / f"{name}-timeline.jsonl"
        return status_timeline.rows(path) if path.is_file() else []

    def _build(self, name: str, project: Path, campaign: Path, experience: Optional[str]) -> Dict[str, Any]:
        started = time.monotonic()
        if campaign.exists():
            self.ctx.shell(f"kapso build --output {campaign} --stop", check=False)
            shutil.rmtree(campaign, ignore_errors=True)
        served = f" --experience {experience}" if experience else ""
        self.ctx.shell(
            f"kapso build --brief kapso-brief.md --repo . --evaluation evaluation --data data --output {campaign}{served} "
            f"--budget-minutes {BUDGET['minutes']} --budget-experiments {BUDGET['experiments']} --config kapso-config.yaml "
            f"--coding-agent {self.host_name} --detach", cwd=project,
        )
        wait_for(lambda: status_of(campaign) is not None, 300, every=5)
        timeline = self.out / "artifacts" / f"{name}-timeline.jsonl"
        self.samplers[name] = subprocess.Popen([sys.executable, str(Path(__file__).parent / "status_timeline.py"), str(campaign), str(timeline), "--every", str(self.cadence), "--until-terminal"])
        wait_for(lambda: (status_of(campaign) or {}).get("state") in ("done", "failed"), BUDGET["minutes"] * 60 + 900, every=20)
        sampler = self.samplers.pop(name, None)
        if sampler:
            # The sampler exits by itself once it has written the terminal
            # row — the sample that carries the delivered score; it is only
            # killed when that row does not come within two cadences.
            wait_for(lambda: sampler.poll() is not None, int(self.cadence * 2) + 30, every=2)
            if sampler.poll() is None:
                sampler.terminate()
            sampler.wait()
        trace = self.trace(campaign)
        status = status_of(campaign) or {}
        artifacts = [self.ctx.artifact(f"{name}-status.json", json.dumps(status, indent=2)), self.ctx.artifact(f"{name}-trace.json", json.dumps(trace, indent=2)), f"artifacts/{name}-timeline.jsonl"]
        step = shell_step(name, status.get("state") == "done" and scored_observations(trace) >= 1, artifacts, (time.monotonic() - started) / 60,
                          [f"served: {experience or 'nothing'}", f"the campaign's sessions on {self.host_name}", f"scored observations: {scored_observations(trace)}", SPREAD], kind="build")
        step["metrics"] = {"scored_observations": scored_observations(trace), "delivered": delivered_score(trace)}
        return step

    def step_build_one(self) -> Dict[str, Any]:
        project = self.ctx.fixture("churn-first-build", "s6-build-one")
        # An isolated bank home, so the learn writes to a bank we own and read.
        project_config(project, {"learning": {"bank": {"local_path": str(self.bank)}}})
        self.ctx.state["s6_project_one"] = str(project)
        self.ctx.save()
        return self._build("build-one", project, self.work / "s6-campaign-one", None)

    def step_learn_build_one(self) -> Dict[str, Any]:
        started = time.monotonic()
        project = Path(self.ctx.state["s6_project_one"])
        campaign = self.work / "s6-campaign-one"
        notes = [f"the learn runs on the development box over build one's campaign{' (advisory for smoothness, exact for the bank commit)' if self.args.advisory else ''}"]
        if self.ctx.learn_model:
            config = effective_config(self.ctx, project)
            project_config(project, {"learning": learning_on(config["learning"], self.ctx.learn_model, "claude-fable-5")})
            notes.append(f"the learning crews ran on {self.ctx.learn_model} (--learn-model): the token's window for the shipped model was spent")
        learn = self.ctx.shell(f"kapso learn {campaign} --config kapso-config.yaml", cwd=project, check=False, timeout=SUITE["steps"]["learn-build-one"]["minutes"] * 60)
        bank = bank_head_and_cards(self.bank)
        self.ctx.state["s6_bank_head"] = bank["head"]
        self.ctx.save()
        artifacts = [self.ctx.artifact("learn-build-one.txt", learn.stdout + learn.stderr), self.ctx.artifact("bank-one.json", json.dumps(bank, indent=2))]
        step = shell_step("learn-build-one", learn.returncode == 0 and bank["count"] >= 1, artifacts, (time.monotonic() - started) / 60,
                          [*notes, f"the bank banked {bank['count']} card(s) at {bank['head']}"], kind="build")
        step["metrics"] = {"cards_banked": bank["count"], "bank_head": bank["head"]}
        return step

    def step_build_two(self) -> Dict[str, Any]:
        project = self.ctx.fixture("churn-first-build", "s6-build-two")
        project_config(project, {"learning": {"bank": {"local_path": str(self.out / "bank-two.git")}}})
        self.ctx.state["s6_project_two"] = str(project)
        self.ctx.save()
        return self._build("build-two", project, self.work / "s6-campaign-two", f"file://{self.bank}")

    def step_review_two(self) -> Dict[str, Any]:
        """The review skill on the host over build two: the host names the
        served cards the campaign used, from the record. The design's
        "named by the review" is this answer, checked against the trace's
        own reading — a card named here that the trace shows read or
        load-bearing — never the driver's own list."""
        started = time.monotonic()
        project = Path(self.ctx.state["s6_project_two"])
        campaign = self.work / "s6-campaign-two"
        served = served_and_used(self.trace(campaign))
        prompt = (f"Review the finished Kapso campaign at {campaign}: which experience cards was it served, which of them did its sessions use, "
                  "and did they pay? Name each card by its title or slug, in at most twenty lines.")
        turns = self.ctx.converse("review-two", project, prompt, lambda text, index: None, max_turns=1)
        answer = "\n".join(turn.text for turn in turns)
        named = sorted(card for card in set(served["read"]) | set(served["load_bearing"]) if card_named(answer, card))
        artifacts = [self.ctx.artifact("review-two.txt", answer)]
        step = record_step("review-two", turns, bool(named), artifacts,
                           [f"cards the review named, of those the trace shows read or load-bearing: {', '.join(named) or 'none'}"])
        step["metrics"] = {"review_names_served_cards": len(named)}
        return step

    def step_comparison(self) -> Dict[str, Any]:
        started = time.monotonic()
        trace_one = self.trace(self.work / "s6-campaign-one")
        trace_two = self.trace(self.work / "s6-campaign-two")
        # One grid for both: to the later build's last sample, the earlier
        # finisher's incumbent carried forward.
        horizon = max(last_sample_seconds(self.timeline("build-one")), last_sample_seconds(self.timeline("build-two")))
        series_one = anytime_series(self.timeline("build-one"), self.cadence, horizon)
        series_two = anytime_series(self.timeline("build-two"), self.cadence, horizon)
        gaps = gap_series(series_two, series_one)
        served = served_and_used(trace_two)
        metrics = comparison_metrics(trace_one, trace_two, gaps, served, behind=behind_points(series_two, series_one))
        scored = (metrics["scored_observations"]["build_one"], metrics["scored_observations"]["build_two"])
        (self.out / "judge").mkdir(exist_ok=True)
        text = review(served, gaps, scored) if min(scored) >= 1 else "# S6 review\n\nNo observation: a build scored nothing at this budget; the pair is not established. " + SPREAD + "\n"
        (self.out / "judge" / "comparison.md").write_text(text, encoding="utf-8")
        artifacts = [self.ctx.artifact("comparison.md", text),
                     self.ctx.artifact("series.json", json.dumps({"cadence_seconds": self.cadence, "build_one": series_one, "build_two": series_two, "gap": gaps}, indent=2)),
                     self.ctx.artifact("served.json", json.dumps(served, indent=2))]
        completed = min(scored) >= 1
        step = shell_step("comparison", completed, artifacts, (time.monotonic() - started) / 60,
                          ["an observed pair with the spread beside it; a non-negative gap at every common checkpoint and a cited lesson is the bar; both builds must score at least one observation", SPREAD], kind="shell")
        step["metrics"] = metrics
        return step


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--clone", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--learn-model", default=None, help="run the learning crews on this model (the token's window for the shipped one spent)")
    parser.add_argument("--cadence", type=float, default=None, help="the grid cadence; default: the engine config's budget.checkpoint_heartbeat_seconds")
    parser.add_argument("--host", default="claude_code", choices=["claude_code", "codex"], help="the coding agent the campaigns' sessions run on, and the CLI the review runs in")
    parser.add_argument("--machine", default=os.uname().nodename)
    parser.add_argument("--advisory", default=None)
    parser.add_argument("--steps", default=None)
    args = parser.parse_args(argv)
    driver = S6(args)
    record_file = driver.out / "record.json"
    started = datetime.now(timezone.utc)
    record = json.loads(record_file.read_text()) if record_file.exists() else {
        "test": "S6", "host": args.host, "machine": args.machine, "run_id": f"S6-{args.host}-{started.strftime('%Y%m%dT%H%M%SZ')}", "advisory": args.advisory,
        "package": {"version": subprocess.run(["kapso", "--version"], capture_output=True, text=True).stdout.strip().split()[-1], "wheel_sha256": "-"},
        "pins": {"suite_sha256": hashlib.sha256(plugin_proof.SUITE_PATH.read_bytes()).hexdigest(), "cadence_seconds": driver.cadence, "budget": BUDGET, "learn_model": args.learn_model},
        "user": {"kind": "scripted", "card": None, "interventions": ["both builds from the same seed, data, evaluator, config, models and machine; build one served nothing, build two served build one's banked experience"], "events": [], "pushback": None},
        "started": started.isoformat(timespec="seconds"), "finished": None, "steps": [], "metrics": {}, "notes": [SPREAD, *[note for note in [codex_session_note()] if note]], "transcripts": [],
    }
    steps = {"build-one": driver.step_build_one, "learn-build-one": driver.step_learn_build_one, "build-two": driver.step_build_two,
             "review-two": driver.step_review_two, "comparison": driver.step_comparison}
    assert list(steps) == STEP_NAMES
    selected = args.steps.split(",") if args.steps else list(STEP_NAMES)
    for name in selected:
        print(f"== {name}", flush=True)
        step = steps[name]()
        record["steps"] = [existing for existing in record["steps"] if existing["name"] != name] + [step]
        record["metrics"] = run_metrics(record)
        record["transcripts"] = sorted(f"transcripts/{path.name}" for path in (driver.out / "transcripts").glob("*.jsonl"))
        record["finished"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
        record_file.write_text(json.dumps(record, indent=1) + "\n", encoding="utf-8")
        print(json.dumps({key: value for key, value in step.items() if key != "notes"}), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
