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


def test_the_gap_is_build_two_minus_build_one_per_common_point():
    one = [(0.0, None), (60.0, 0.80), (120.0, 0.82)]
    two = [(0.0, None), (60.0, 0.83), (120.0, 0.88)]
    gaps = s6.gap_series(two, one)
    assert gaps[0] == (0.0, None)
    assert abs(gaps[1][1] - 0.03) < 1e-9 and abs(gaps[2][1] - 0.06) < 1e-9
    assert s6.gap_min(gaps) is not None and abs(s6.gap_min(gaps) - 0.03) < 1e-9
    assert s6.gap_min([(0.0, None)]) is None
    # A point build one has not reached is not a gap (build two is ahead on the grid).
    ahead = s6.gap_series([(0.0, 0.8), (60.0, 0.9)], [(0.0, 0.7)])
    assert abs(ahead[0][1] - 0.1) < 1e-9 and ahead[1] == (60.0, None)


def test_served_and_used_reads_the_cards_and_lessons_from_a_trace():
    empty = s6.served_and_used(TRACE)
    assert empty["read"] == [] and empty["load_bearing"] == [] and empty["cited"] == 0, "the cold churn trace served nothing"
    served = {
        "lessons": [
            {"reference": "mine:all", "read_by": {"generic_exp_0": ["card-a"]}, "load_bearing_by": {"1": ["card-a"]}},
            {"reference": "leeroopedia", "read_by": {}, "load_bearing_by": {}},
        ],
        "attempts": [{"cards": {"read": ["card-a", "card-b"], "load_bearing": ["card-a"]}},
                     {"cards": {"read": ["card-b"], "load_bearing": []}}],
    }
    used = s6.served_and_used(served)
    assert used["read"] == ["card-a", "card-b"] and used["load_bearing"] == ["card-a"]
    assert used["cited"] == 1 and used["served_sources"] == ["mine:all", "leeroopedia"]


def test_the_run_metrics_aggregate_the_comparison_and_no_observation_is_honest():
    trace_one = {"attempts": [{"evaluation": {"score": 0.80}}], "delivered": {"score": 0.80}}
    trace_two = {"attempts": [{"evaluation": {"score": 0.86}}, {"evaluation": {"score": None}}], "delivered": {"score": 0.86}}
    gaps = [(0.0, None), (60.0, 0.04), (120.0, 0.06)]
    served = s6.served_and_used({"lessons": [{"reference": "mine:all", "read_by": {"s": ["c"]}, "load_bearing_by": {}}], "attempts": [{"cards": {"read": ["c"], "load_bearing": []}}]})
    metrics = s6.comparison_metrics(trace_one, trace_two, gaps, served)
    assert metrics["gap_min"] == 0.04 and metrics["lessons_cited"] == 1 and metrics["scored_observations_min"] == 1
    record = {"steps": [{"name": "comparison", "metrics": metrics}], "metrics": {}}
    assert s6.run_metrics(record) == {"gap_min": 0.04, "lessons_cited": 1, "scored_observations_min": 1}
    # A build that scored nothing: the minimum is zero, the pair not established.
    none_two = {"attempts": [{"evaluation": {"score": None}}], "delivered": None}
    assert s6.comparison_metrics(trace_one, none_two, gaps, served)["scored_observations_min"] == 0


def test_the_steps_and_bars_match_the_suite():
    assert s6.STEP_NAMES == s6.SUITE["tests"]["S6"]["required_steps"]["claude_code"]
    assert set(s6.SUITE["tests"]["S6"]["bars"]) == {"gap_min", "lessons_cited", "scored_observations_min"}
    assert s6.SUITE["steps"]["learn-build-one"]["kind"] == "build"
