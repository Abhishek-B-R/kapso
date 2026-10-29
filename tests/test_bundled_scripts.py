"""The bundled harnesses' scripts on constructed inputs
(docs/plans/redesign/wp8-harness-ports.md, change 4): the leakage scan
reports one finding per rule, in diff mode on the added lines and in tree
mode over a directory, exits 1 on a violation and 0 on advisory findings
alone, and applies the regime's rule; the sanitizer refuses what it must
and coerces a text boolean target."""

import importlib.util
import json
import subprocess
import sys

import pytest

from kapso.harness import BUNDLED_ROOT

SKILLS = BUNDLED_ROOT / "predictive-modelling" / "skills"
SCAN = SKILLS / "leakage-scan" / "scripts" / "scan.py"
SANITIZE = SKILLS / "sanitize-cache" / "scripts" / "sanitize.py"


def diff_of(*lines, file="main.py"):
    body = "\n".join(f"+{line}" for line in lines)
    return f"--- a/{file}\n+++ b/{file}\n@@ -0,0 +1,{len(lines)} @@\n{body}\n"


def run_scan(regime, *, diff=None, tree=None):
    argv = [sys.executable, str(SCAN), "--regime", regime] + (["--diff"] if diff is not None else ["--tree", str(tree)])
    completed = subprocess.run(argv, input=diff or "", capture_output=True, text=True)
    return completed.returncode, [json.loads(line) for line in completed.stdout.splitlines()]


VIOLATIONS = [
    ("unmasked-test-table", "test = task.get_table('test', mask_input_cols=False)"),
    ("removed-columns", "cols = db.table_dict['users'].removed_cols"),
    ("cache-location", "os.environ['RELBENCH_CACHE_DIR'] = '/tmp/mine'"),
    ("outside-snapshot", "root = os.environ['RELBENCH_ROLLING_ROOT']"),
    ("task-stats", "print(task.stats())"),
    ("download", "dataset = get_dataset(name, download=True)"),
    ("direct-fetch", "url = 'https://relbench.stanford.edu/data/rel-x.zip'"),
    ("private-builder", "table = task._get_table('test')"),
    ("pristine-cache", "path = Path.home() / '.cache/relbench'"),
]


@pytest.mark.parametrize("rule,line", VIOLATIONS, ids=[rule for rule, _ in VIOLATIONS])
def test_each_violation_is_one_finding_that_fails_the_scan(rule, line):
    code, findings = run_scan("frozen", diff=diff_of("import os", line))
    assert code == 1
    assert [(f["rule"], f["line"], f["advisory"]) for f in findings] == [(rule, 2, False)]
    assert findings[0]["file"] == "main.py" and findings[0]["text"] == line


def test_advisory_findings_alone_pass_with_the_verify_prefix():
    code, findings = run_scan("frozen", diff=diff_of(
        "train = task.get_table('train', mask_input_cols=False)",
        "X = np.concatenate([train_x, val_x])",
        "model.fit(X_val, val_y)",
    ))
    assert code == 0
    assert [f["rule"] for f in findings] == ["unmasked-table", "train-val-mixing", "fit-on-validation"]
    assert all(f["advisory"] and f["concern"].startswith("verify: ") for f in findings)


def test_a_clean_diff_has_no_findings_and_removed_lines_are_not_read():
    diff = "--- a/main.py\n+++ b/main.py\n@@ -1,2 +1,2 @@\n-x = task._get_table('test')\n+x = task.get_table('val')\n y = 1\n"
    assert run_scan("seed-time", diff=diff) == (0, [])


def test_the_regime_decides_which_truncation_argument_is_the_violation():
    truncated = diff_of("db = dataset.get_db(upto_test_timestamp=True)")
    untruncated = diff_of("db = dataset.get_db(upto_test_timestamp=False)")
    assert run_scan("seed-time", diff=truncated)[0] == 1 and run_scan("frozen", diff=truncated)[0] == 0
    assert run_scan("frozen", diff=untruncated)[0] == 1 and run_scan("seed-time", diff=untruncated)[0] == 0
    assert run_scan("autocomplete", diff=untruncated) == (0, []) and run_scan("autocomplete", diff=truncated) == (0, [])


def test_line_numbers_follow_the_hunk_through_context_lines():
    diff = (
        "--- a/features.py\n+++ b/features.py\n@@ -10,3 +10,5 @@\n context\n+a = 1\n context\n"
        "+table = task._get_table('x')\n+b = 2\n"
    )
    code, findings = run_scan("frozen", diff=diff)
    assert code == 1 and [(f["file"], f["line"]) for f in findings] == [("features.py", 13)]


def test_tree_mode_scans_every_python_file_whole(tmp_path):
    (tmp_path / "main.py").write_text("import os\nx = 1\n")
    (tmp_path / "features").mkdir()
    (tmp_path / "features" / "build.py").write_text("a = 1\ntable = task._get_table('x')\n")
    (tmp_path / "notes.md").write_text("task._get_table('x') in prose is not code\n")
    code, findings = run_scan("frozen", tree=tmp_path)
    assert code == 1 and [(f["file"], f["line"], f["rule"]) for f in findings] == [("features/build.py", 2, "private-builder")]


def sanitizer():
    spec = importlib.util.spec_from_file_location("sanitize", SANITIZE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


pytest.importorskip("relbench")


def test_the_sanitizer_refuses_a_missing_cache_a_full_output_and_an_output_inside_the_source(tmp_path, monkeypatch):
    module = sanitizer()
    source = tmp_path / "cache"
    (source / "rel-x" / "db").mkdir(parents=True)
    full = tmp_path / "out"
    full.mkdir()
    (full / "stale").write_text("x")
    for argv, message in (
        (["--dataset", "rel-y", "--task", "t", "--source", str(source), "--out", str(tmp_path / "o1")], "no pristine cache"),
        (["--dataset", "rel-x", "--task", "t", "--source", str(source), "--out", str(full)], "is not empty"),
        (["--dataset", "rel-x", "--task", "t", "--source", str(source), "--out", str(source / "inner")], "must not be inside"),
    ):
        monkeypatch.setattr(sys, "argv", ["sanitize.py", *argv])
        with pytest.raises(SystemExit) as caught:
            module.main()
        assert message in str(caught.value)


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
