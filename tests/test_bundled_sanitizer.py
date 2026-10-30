"""The predictive-modelling harness's sanitized-copy script
(skills/sanitized-copy/scripts/sanitize.py): its refusals before any write,
the rolling build's limits, the text-boolean target. The script needs the
relbench library, so this module skips as a whole without it; the leakage
scan's tests, which need nothing, live in tests/test_bundled_scripts.py
(docs/plans/redesign/wp8-harness-ports.md, the review's finding 4)."""

import importlib.util
import sys

import pytest

from kapso.harness import BUNDLED_ROOT

SANITIZE = BUNDLED_ROOT / "predictive-modelling" / "skills" / "sanitized-copy" / "scripts" / "sanitize.py"

pytest.importorskip("relbench")


def sanitizer():
    spec = importlib.util.spec_from_file_location("sanitize", SANITIZE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module




def test_the_sanitizer_refuses_what_it_must_before_writing_anything(tmp_path, monkeypatch):
    module = sanitizer()
    source = tmp_path / "cache"
    (source / "rel-x" / "db").mkdir(parents=True)
    (source / "rel-x" / "tasks" / "t").mkdir(parents=True)
    for split in ("train", "val", "test"):
        (source / "rel-x" / "tasks" / "t" / f"{split}.parquet").write_bytes(b"")
    (source / "rel-x" / "tasks" / "u").mkdir()
    (source / "rel-x" / "tasks" / "u" / "train.parquet").write_bytes(b"")
    sanitized = tmp_path / "already"
    (sanitized / "rel-x" / "db").mkdir(parents=True)
    (sanitized / module.MARKER).write_text("{}")
    full = tmp_path / "out"
    full.mkdir()
    (full / "stale").write_text("x")
    for argv, message in (
        (["--dataset", "rel-y", "--task", "t", "--source", str(source), "--out", str(tmp_path / "o1")], "no pristine cache"),
        (["--dataset", "rel-x", "--task", "t", "--source", str(sanitized), "--out", str(tmp_path / "o2")], "is itself a sanitized copy"),
        (["--dataset", "rel-x", "--task", "u", "--source", str(source), "--out", str(tmp_path / "o3")], "pristine task table missing"),
        (["--dataset", "rel-x", "--task", "t", "--source", str(source), "--out", str(full)], "is not empty"),
        (["--dataset", "rel-x", "--task", "t", "--source", str(source), "--out", str(source / "inner")], "must not be inside"),
    ):
        monkeypatch.setattr(sys, "argv", ["sanitize.py", *argv])
        with pytest.raises(SystemExit) as caught:
            module.main()
        assert message in str(caught.value)


def test_the_rolling_build_refuses_a_recommendation_task_and_a_single_timestamp_task(tmp_path):
    """Both refusals come before any snapshot is written: a recommendation task
    has no entity column for the per-tick tables, and a task with one
    evaluation timestamp per split is the flat regime."""
    module = sanitizer()
    recommendation = module.RecommendationTask.__new__(module.RecommendationTask)
    with pytest.raises(SystemExit, match="recommendation task"):
        module.build_rolling(None, recommendation, "rel-x", "t", tmp_path)
    single = module.AutoCompleteTask.__new__(module.AutoCompleteTask)
    with pytest.raises(SystemExit, match="one evaluation timestamp"):
        module.build_rolling(None, single, "rel-x", "t", tmp_path)
    assert not any(tmp_path.iterdir())


def test_the_sanitizer_coerces_a_text_boolean_target_and_refuses_other_strings():
    pandas = pytest.importorskip("pandas")
    module = sanitizer()

    class Table:
        def __init__(self, frame):
            self.df = frame

    coerced = module.coerce_boolean_target(Table(pandas.DataFrame({"y": ["t", "F", "true"]})), "y")
    assert coerced.df["y"].tolist() == [1, 0, 1]
    with pytest.raises(ValueError, match="non-boolean strings"):
        module.coerce_boolean_target(Table(pandas.DataFrame({"y": ["t", "maybe"]})), "y")
    numeric = Table(pandas.DataFrame({"y": [0, 1]}))
    assert module.coerce_boolean_target(numeric, "y") is numeric
