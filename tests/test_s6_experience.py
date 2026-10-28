"""S6's core (docs/plans/redesign/wp9-semantic-suite.md, change 9): the
anytime series is the running best on a cadence grid (None until the
first score); the gap is build two minus build one per common point
(None where either is missing); the served-and-used reading lifts the
cards read and load-bearing and the lessons cited from a real trace; the
bank's cards are counted from the tree; the run metrics aggregate the
comparison; a build that scored nothing makes the pair "no observation"."""

import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts" / "redesign"))
spec = importlib.util.spec_from_file_location("s6_experience", ROOT / "scripts" / "redesign" / "s6_experience.py")
s6 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(s6)
TRACE = json.loads((ROOT / "tests" / "fixtures" / "semantic_transcripts" / "churn-trace.json").read_text())


def _row(seconds, score):
    stored = {"state": "running", "best": {"score": score} if score is not None else None}
    return {"ts": f"2026-10-27T10:{seconds // 60:02d}:{seconds % 60:02d}+00:00", "stored": stored}


def test_the_anytime_series_is_the_running_best_on_the_grid():
    timeline = [_row(0, None), _row(60, None), _row(120, 0.80), _row(180, 0.79), _row(240, 0.85)]
    series = s6.anytime_series(timeline, 60.0)
    assert [point for point, _ in series] == [0.0, 60.0, 120.0, 180.0, 240.0]
    assert [score for _, score in series] == [None, None, 0.80, 0.80, 0.85], "running max, None until the first score"
    assert s6.anytime_series([], 60.0) == []
    # s6-claude-5 (2026-10-28): the delivered score landed in the final
    # partial interval and fell off a grid cut at the last whole cadence;
    # the grid reaches the last sample, and a horizon past it (the other
    # build still running) carries the incumbent forward.
    terminal = timeline + [_row(250, 0.86)]
    assert s6.anytime_series(terminal, 60.0)[-1] == (300.0, 0.86)
    assert s6.last_sample_seconds(terminal) == 250.0 and s6.last_sample_seconds([]) == 0.0
    carried = s6.anytime_series(terminal, 60.0, horizon=420.0)
    assert [point for point, _ in carried][-3:] == [300.0, 360.0, 420.0] and [score for _, score in carried][-3:] == [0.86, 0.86, 0.86]


def test_the_gap_is_build_two_minus_build_one_per_common_point():
    one = [(0.0, None), (60.0, 0.80), (120.0, 0.82)]
    two = [(0.0, None), (60.0, 0.83), (120.0, 0.88)]
    gaps = s6.gap_series(two, one)
    assert gaps[0] == (0.0, None)
    assert abs(gaps[1][1] - 0.03) < 1e-9 and abs(gaps[2][1] - 0.06) < 1e-9
    assert s6.gap_min(gaps) is not None and abs(s6.gap_min(gaps) - 0.03) < 1e-9
    assert s6.gap_min([(0.0, None)]) is None
    # The common horizon: build two ran one point further, so that point is
    # not compared; and build two running behind build one is counted.
    ahead = s6.gap_series([(0.0, 0.8), (60.0, 0.9)], [(0.0, 0.7)])
    assert len(ahead) == 1 and abs(ahead[0][1] - 0.1) < 1e-9
    behind = s6.gap_series([(0.0, None), (60.0, 0.9)], [(0.0, 0.7), (60.0, 0.8)])
    assert behind[0] == (0.0, None) and s6.behind_points([(0.0, None), (60.0, 0.9)], [(0.0, 0.7), (60.0, 0.8)]) == 1


def test_served_and_used_counts_load_bearing_as_cited_not_mere_reading():
    empty = s6.served_and_used(TRACE)
    assert empty["read"] == [] and empty["load_bearing"] == [] and empty["cited"] == 0, "the cold churn trace served nothing"
    served = {
        "lessons": [
            {"reference": "mine:all", "read_by": {"generic_exp_0": ["card-a"]}, "load_bearing_by": {"1": ["card-a"]}},
            {"reference": "leeroopedia", "read_by": {"generic_exp_0": ["card-c"]}, "load_bearing_by": {}},
        ],
        "attempts": [{"cards": {"read": ["card-a", "card-b"], "load_bearing": ["card-a"]}},
                     {"cards": {"read": ["card-b"], "load_bearing": []}}],
    }
    used = s6.served_and_used(served)
    assert used["read"] == ["card-a", "card-b"] and used["load_bearing"] == ["card-a"]
    # Only the load-bearing lesson is cited; the read-only one is reported apart.
    assert used["cited"] == 1 and used["read_not_load_bearing"] == 1 and used["served_sources"] == ["mine:all", "leeroopedia"]


def test_the_run_metrics_aggregate_the_comparison_and_delivered_is_resolved_to_its_attempt():
    trace_one = {"attempts": [{"branch": "b1", "evaluation": {"score": 0.80}}], "delivered": {"branch": "b1", "commit": "abc"}}
    trace_two = {"attempts": [{"branch": "b2", "evaluation": {"score": 0.86}}, {"branch": "b3", "evaluation": {"score": None}}], "delivered": {"branch": "b2", "commit": "def"}}
    gaps = [(0.0, None), (60.0, 0.04), (120.0, 0.06)]
    served = s6.served_and_used({"lessons": [{"reference": "mine:all", "read_by": {"s": ["c"]}, "load_bearing_by": {"1": ["c"]}}], "attempts": [{"cards": {"read": ["c"], "load_bearing": ["c"]}}]})
    metrics = s6.comparison_metrics(trace_one, trace_two, gaps, served, behind=2)
    assert metrics["gap_min"] == 0.04 and metrics["lessons_cited"] == 1 and metrics["scored_observations_min"] == 1 and metrics["behind_points"] == 2
    # The delivered score is resolved from the delivered branch's attempt, not a `score` field.
    assert metrics["delivered"] == {"build_one": 0.80, "build_two": 0.86}
    record = {"steps": [{"name": "comparison", "metrics": metrics}], "metrics": {}}
    assert s6.run_metrics(record) == {"gap_min": 0.04, "lessons_cited": 1, "scored_observations_min": 1}
    none_two = {"attempts": [{"branch": "b", "evaluation": {"score": None}}], "delivered": None}
    assert s6.comparison_metrics(trace_one, none_two, gaps, served)["scored_observations_min"] == 0


def test_the_steps_and_bars_match_the_suite():
    assert s6.STEP_NAMES == s6.SUITE["tests"]["S6"]["required_steps"]["claude_code"]
    # gap_min is reported, not a hard bar (the budget makes its sign noise); the gate is use and an observation.
    assert set(s6.SUITE["tests"]["S6"]["bars"]) == {"lessons_cited", "scored_observations_min"}
    assert s6.SUITE["steps"]["learn-build-one"]["kind"] == "build"
