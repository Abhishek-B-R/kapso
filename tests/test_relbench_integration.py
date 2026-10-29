"""The RelBench integration: the Brief from the task's facts, the harness's
sanitizer on real data, the override file, the provided grader, the final
report over the archive's registered finals, and the grader's own labels.
Tests that need a populated relbench cache are skipped unless the cache
exists."""

import json
import os
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

# The relbench package is installed separately (pip install relbench); it is
# not a declared extra. Without it these skip rather than erroring at import.
pytest.importorskip("relbench")

from kapso.core.config import load_config, read_yaml
from kapso.execution.evaluation_archive import label_run_of_record
from kapso.handles import Brief
from kapso.harness import BUNDLED_ROOT
from benchmarks.common import stage_evaluation
from benchmarks.relbench import scoring
from benchmarks.relbench.context import build_brief
from benchmarks.relbench.task_specs import (
    ENTITY_REGRESSION,
    PRIMARY_METRIC_OVERRIDES,
    TaskSpec,
    coerce_boolean_target,
)

REPO_ROOT = Path(__file__).parents[1]
GENERIC_EVAL_DIR = REPO_ROOT / "benchmarks" / "relbench" / "data" / "generic_eval"
HARNESS = BUNDLED_ROOT / "predictive-modelling"
SANITIZER = HARNESS / "skills" / "sanitized-copy" / "scripts" / "sanitize.py"
RELBENCH_CACHE = Path(
    os.environ.get("RELBENCH_PRISTINE_CACHE_DIR", os.path.expanduser("~/.cache/relbench"))
)
needs_rel_f1 = pytest.mark.skipif(
    not (RELBENCH_CACHE / "rel-f1" / "db").exists(),
    reason="requires a populated rel-f1 relbench cache",
)


# ---------------------------------------------------------------------------
# The Brief
# ---------------------------------------------------------------------------

class FakeTable:
    def __init__(self, df, pkey, time_col, fkeys):
        self.df = df
        self.pkey_col = pkey
        self.time_col = time_col
        self.fkey_col_to_pkey_table = fkeys


class FakeDriverTask:
    """A relbench-shaped entity task: the Brief reads its docstring, its
    `make_table` source, its tables and its dataset's database."""

    entity_col = "driverId"
    entity_table = "drivers"
    time_col = "date"
    target_col = "position"

    def __init__(self, num_eval_timestamps: int):
        self.num_eval_timestamps = num_eval_timestamps
        wide = pd.DataFrame({f"c{i}": [1.0] for i in range(45)})
        wide["driverId"] = [1]
        db = SimpleNamespace(
            table_dict={
                "drivers": FakeTable(wide, "driverId", None, {}),
                "results": FakeTable(pd.DataFrame({"resultId": [1], "driverId": [1], "position": [None]}),
                                     "resultId", "date", {"driverId": "drivers"}),
            },
            min_timestamp="1950-05-13", max_timestamp="2009-11-01",
        )
        self.dataset = SimpleNamespace(get_db=lambda: db, val_timestamp="2005-01-01", test_timestamp="2010-01-01")
        ticks = pd.to_datetime(["2005-01-01", "2005-02-01", "2005-03-01"][:num_eval_timestamps])
        rows = len(ticks) * 4
        self.tables = {
            "train": pd.DataFrame({"date": pd.to_datetime(["2000-01-01"] * 8), "driverId": range(8), "position": [1.0, 2, 3, 4, 5, 6, 7, 8]}),
            "val": pd.DataFrame({"date": np.repeat(ticks, 4), "driverId": range(rows), "position": [3.0] * rows}),
            "test": pd.DataFrame({"date": np.repeat(ticks, 4), "driverId": range(rows)}),
        }

    def get_table(self, split, mask_input_cols=None):
        return SimpleNamespace(df=self.tables[split])

    def make_table(self, db, timestamps):
        """The driver's finishing position in the races of the window."""
        return db


def driver_spec(num_eval_timestamps: int = 1) -> TaskSpec:
    return TaskSpec(
        dataset_name="rel-f1", task_name="driver-position", family=ENTITY_REGRESSION,
        primary_metric="mae", maximize=False, full_timeout=7200, debug_timeout=900,
        entity_col="driverId", entity_table="drivers", time_col="date", target_col="position",
        timedelta_str="30 days", num_eval_timestamps=num_eval_timestamps, metrics=["mae", "r2"],
    )


COMPUTE = {"has_gpu": True, "gpu_name": "NVIDIA A100-SXM4-40GB, 40960 MiB", "num_cpus": 12, "mem_gb": 85}


class TestBrief:
    def brief(self, tmp_path, num_eval_timestamps=1, hosted="none"):
        task = FakeDriverTask(num_eval_timestamps)
        rolling_root = tmp_path / "rolling" if num_eval_timestamps > 1 else None
        return build_brief(task, driver_spec(num_eval_timestamps), tmp_path / "copy", rolling_root,
                           tmp_path / "shared", hosted, compute=COMPUTE)

    def test_the_objective_holds_the_tasks_facts_whole(self, tmp_path):
        """The task definition with its label-generating code, the label
        statistics, the schema with every column, the paths and the
        retraction command: facts, never clipped."""
        brief = self.brief(tmp_path)
        objective = brief.objective
        assert "## Task definition" in objective and "def make_table" in objective
        assert "The driver's finishing position" in objective
        assert "positive rate" not in objective and "median=" in objective
        assert "### table `drivers`" in objective and "c44:float64" in objective   # the 45th column, not clipped
        assert f"`{tmp_path / 'copy'}`" in objective and str(tmp_path / "shared") in objective
        assert "a frozen database, truncated at the test cutoff" in objective
        assert "--void run_XXXX" in brief.render()
        assert "NVIDIA A100" in objective and "~12 CPUs" in objective
        assert "Published-board units" in objective

    def test_measured_by_names_the_metric_its_direction_and_the_orientation(self, tmp_path):
        brief = self.brief(tmp_path)
        assert brief.measured_by.startswith("validation mae, lower is better")
        assert "negated, so that higher is better" in brief.measured_by
        assert "mae, r2" in brief.measured_by
        assert "divide a MAE by" in brief.target and brief.baseline.startswith("the seeded candidate")

    def test_the_rules_are_the_tasks_and_the_grant_is_the_configs(self, tmp_path):
        rules = self.brief(tmp_path).rules
        assert any("two-model contract" in rule for rule in rules)
        assert any("No hosted model API is granted" in rule for rule in rules)
        assert any("date <= t" in rule for rule in rules)
        assert not any("another tick's snapshot" in rule for rule in rules)
        granted = self.brief(tmp_path, hosted="openai").rules
        assert any("OPENAI_API_KEY" in rule for rule in granted)
        with pytest.raises(ValueError, match="hosted_model_api"):
            self.brief(tmp_path, hosted="anthropic")

    def test_a_rolling_task_carries_the_per_tick_invocation_contract(self, tmp_path):
        brief = self.brief(tmp_path, num_eval_timestamps=3)
        assert "## Per-row seed time" in brief.objective
        assert "6 invocations in all" in brief.objective and "(3 validation ticks, then 3 test ticks)" in brief.objective
        assert str(tmp_path / "rolling") in brief.objective
        assert any("another tick's snapshot" in rule for rule in brief.rules)

    def test_no_standing_guidance_rides_in_the_brief(self, tmp_path):
        """What the harness says (the practices, the validation discipline)
        is not the task's: the Brief carries none of it."""
        text = self.brief(tmp_path).render()
        for phrase in ("Feature engineering", "never use the official validation score",
                       "features_history", "practice"):
            assert phrase not in text, phrase

    def test_the_brief_survives_its_own_rendering(self, tmp_path):
        """The engine fingerprints the rendered text and a resume parses it
        back: a code block in the objective must round-trip."""
        brief = self.brief(tmp_path, num_eval_timestamps=3)
        assert Brief.parse(brief.render()) == brief


class TestMetricRouting:
    def test_v2_regression_tasks_optimize_r2(self):
        assert PRIMARY_METRIC_OVERRIDES["rel-trial/studies-enrollment"] == ("r2", True)
        assert PRIMARY_METRIC_OVERRIDES["rel-amazon/review-rating"] == ("r2", True)

    def test_the_regime_is_the_scans_word(self):
        assert driver_spec().regime == "frozen" and driver_spec(40).regime == "seed-time"
        autocomplete = TaskSpec(dataset_name="rel-salt", task_name="sales-group", family="autocomplete_multiclass_classification",
                                primary_metric="accuracy", maximize=True, full_timeout=1, debug_timeout=1)
        assert autocomplete.regime == "autocomplete"


# ---------------------------------------------------------------------------
# The sanitized copy, on real data
# ---------------------------------------------------------------------------

@needs_rel_f1
class TestSanitizerOnRealData:
    def test_forecasting_copy_is_leak_free(self, tmp_path):
        """The harness's sanitizer, as the runner invokes it: the test table
        reduced to key and seed time, the database truncated at the cutoff,
        the tree read-only, the marker's report."""
        dest = tmp_path / "copy"
        subprocess.run(
            [sys.executable, str(SANITIZER), "--dataset", "rel-f1", "--task", "driver-position",
             "--source", str(RELBENCH_CACHE), "--out", str(dest)],
            check=True, capture_output=True,
        )
        test_df = pd.read_parquet(dest / "rel-f1" / "tasks" / "driver-position" / "test.parquet")
        assert "position" not in test_df.columns
        races = pd.read_parquet(dest / "rel-f1" / "db" / "races.parquet")
        assert str(races["date"].max()) < "2010-01-02"
        assert not os.access(dest / "rel-f1" / "db" / "races.parquet", os.W_OK)
        marker = json.loads((dest / scoring.SANITIZED_MARKER).read_text())
        assert marker["dataset"] == "rel-f1" and marker["report"]["tables"]["races"]["rows"] <= marker["report"]["tables"]["races"]["pristine_rows"]

    def test_the_copy_is_reused_under_its_marker_and_rebuilt_on_demand(self, tmp_path, monkeypatch):
        """The runner builds the copy once per task and script; a changed
        script or --rebuild-cache builds it again."""
        calls = []
        real_run = scoring.subprocess.run

        def counting_run(command, **kwargs):
            calls.append(command)
            return real_run(command, **kwargs)

        monkeypatch.setattr(scoring.subprocess, "run", counting_run)
        out = tmp_path / "sanitized_cache"
        first = scoring.ensure_sanitized_copy(SANITIZER, RELBENCH_CACHE, "rel-f1", "driver-position", out, rolling=False, rebuild=False)
        again = scoring.ensure_sanitized_copy(SANITIZER, RELBENCH_CACHE, "rel-f1", "driver-position", out, rolling=False, rebuild=False)
        assert first == again == out and len(calls) == 1
        scoring.ensure_sanitized_copy(SANITIZER, RELBENCH_CACHE, "rel-f1", "driver-position", out, rolling=False, rebuild=True)
        assert len(calls) == 2 and (out / scoring.SANITIZED_MARKER).is_file()


class TestRepoMemoryMcpMount:
    """Finding 9: sessions mount the repo-memory MCP gate for MCP-capable agents."""

    def _config(self, agent_type="claude_code", agent_specific=None):
        from kapso.execution.coding_agents.base import CodingAgentConfig

        return CodingAgentConfig(
            agent_type=agent_type, model="m", debug_model="m",
            agent_specific=agent_specific if agent_specific is not None else {},
        )

    def test_claude_code_gets_gate_mounted(self, tmp_path):
        from kapso.execution.experiment_workspace.experiment_session import (
            ExperimentSession,
        )

        config = self._config()
        mounted = ExperimentSession._mount_repo_memory_mcp(config, str(tmp_path))
        assert mounted is True
        servers = config.agent_specific["mcp_servers"]
        (server_conf,) = servers.values()
        assert server_conf["env"]["REPO_MEMORY_ROOT"] == str(tmp_path)
        tools = config.agent_specific["allowed_tools"]
        assert "Bash" in tools
        assert any("get_repo_memory_section" in t for t in tools)
        assert any("get_repo_memory_summary" in t for t in tools)

    def test_preset_mcp_servers_passthrough(self, tmp_path):
        from kapso.execution.experiment_workspace.experiment_session import (
            ExperimentSession,
        )

        preset = {"mcp_servers": {"custom": {"command": "x"}}}
        config = self._config(agent_specific=dict(preset))
        mounted = ExperimentSession._mount_repo_memory_mcp(config, str(tmp_path))
        assert mounted is True
        assert config.agent_specific["mcp_servers"] == preset["mcp_servers"]
        assert "allowed_tools" not in config.agent_specific

    def test_non_mcp_agent_untouched(self, tmp_path):
        from kapso.execution.experiment_workspace.experiment_session import (
            ExperimentSession,
        )

        config = self._config(agent_type="aider")
        mounted = ExperimentSession._mount_repo_memory_mcp(config, str(tmp_path))
        assert mounted is False
        assert "mcp_servers" not in config.agent_specific


class TestOverrideFile:
    def test_the_override_resolves_over_the_packaged_config(self):
        """The benchmark's file is an override (docs/plans/redesign/
        wp4-config.md): what it leaves unset rides along from the
        packaged defaults, what it sets is the campaign's; the runner's own
        keys sit in the `benchmark:` block the engine never reads."""
        path = REPO_ROOT / "benchmarks/relbench/config.yaml"
        override = read_yaml(path)
        cfg = load_config(str(path))
        params = cfg["search_strategy"]["params"]
        assert params["parent_policy"] == "best"   # the packaged default
        # Codex deployment (2026-07-26): implementation, verification, the
        # maintainer and the judge all run on the codex CLI — the default
        # host, so none of them names a cli of its own; the selector too.
        assert params["host"] == "codex"
        assert cfg["evaluation_maintainer"]["enabled"] is True
        assert "cli" not in override["evaluation_maintainer"]
        assert "cli" not in override["search_strategy"]["params"]["judge"]
        assert params["ideation"]["selector"]["cli"] == "codex"
        # The temporal-leakage protocol: no live web in implementation.
        assert params["implementation"]["web"] is False
        assert "models" not in override
        # K=4 expansion (user-directed 2026-07-29): four GPU-pinned lanes,
        # 10h budget, 5h session caps; threads sized for the on-demand
        # a2-highgpu-4g fallback (48 vCPU -> 11/lane).
        assert params["node_expansion_value"] == 4
        lanes = params["expansion_lane_env"]
        assert len(lanes) == 4
        assert all(lane["OMP_NUM_THREADS"] == "11" for lane in lanes)
        assert [lane["CUDA_VISIBLE_DEVICES"] for lane in lanes] == ["0", "1", "2", "3"]
        assert params["implementation"]["timeout"] == 18000
        assert cfg["budget"]["minutes"] == 600
        benchmark = override["benchmark"]
        assert benchmark["work_root"] == "tmp/relbench" and params["registered_evaluation_archive_glob"] == "tmp/relbench/*/runs"
        assert benchmark["timeouts"]["small"] == {"full": 7200, "debug": 900}
        assert benchmark["hosted_model_api"] == "none"


# ---------------------------------------------------------------------------
# The provided grader, on real data
# ---------------------------------------------------------------------------

@needs_rel_f1
class TestProvidedGrader:
    def _repo(self, tmp_path):
        root = tmp_path / "candidate"
        (root / "kapso_evaluation").mkdir(parents=True)
        for f in GENERIC_EVAL_DIR.glob("*"):
            (root / "kapso_evaluation" / f.name).write_bytes(f.read_bytes())
        (root / "main.py").write_text(
            "import json, os, numpy as np\n"
            "from relbench.tasks import get_task\n"
            "task = json.load(open('kapso_evaluation/task.json'))\n"
            "t = get_task(task['dataset'], task['task'], download=False)\n"
            "n_val = len(t.get_table('val'))\n"
            "n_test = len(t.get_table('test'))\n"
            "out = os.environ['KAPSO_RUN_DATA_DIR']\n"
            "np.save(f'{out}/val_predictions.npy', np.full(n_val, 13.0))\n"
            "np.save(f'{out}/test_predictions.npy', np.full(n_test, 13.0))\n"
            "print('fixture candidate done, debug=' + str('--debug' in __import__('sys').argv))\n"
        )
        # The task's settings travel with the grader, in the evaluation directory.
        (root / "kapso_evaluation" / "task.json").write_text(json.dumps({
            "dataset": "rel-f1", "task": "driver-position", "primary_metric": "mae",
            "higher_is_better": False, "work_dir": str(tmp_path / "work"),
            "full_timeout": 300, "debug_timeout": 300, "cache_dir": str(RELBENCH_CACHE),
            "rolling_root": None,
        }))
        env = os.environ.copy()
        env.pop("RELBENCH_CACHE_DIR", None)

        def run(fidelity):
            return subprocess.run(
                [sys.executable, "kapso_evaluation/grader.py", "--fidelity", fidelity,
                 "--fraction", "1.0", "--seed", "1337"],
                cwd=root, env=env, capture_output=True, text=True, timeout=300,
            )
        return root, tmp_path / "work", run

    def test_fast_scores_without_archiving(self, tmp_path):
        _root, work, run = self._repo(tmp_path)
        proc = run("fast")
        assert proc.returncode == 0, proc.stdout[-2000:]
        manifest = json.loads(proc.stdout.strip().splitlines()[-1].split(" ", 1)[1])
        assert manifest["fidelity"] == "fast" and manifest["raw_score"] > 0
        # The engine maximises: a lower-is-better metric travels negated, the raw value beside it.
        assert manifest["score"] == -manifest["raw_score"] and manifest["higher_is_better"] is False
        assert not (work / "runs").exists()

    def test_full_archives_with_code_snapshot(self, tmp_path):
        _root, work, run = self._repo(tmp_path)
        proc = run("full")
        assert proc.returncode == 0, proc.stdout[-2000:]
        manifest = json.loads(proc.stdout.strip().splitlines()[-1].split(" ", 1)[1])
        run_dir = work / "runs" / "run_0001"
        metrics = json.loads((run_dir / "private/metrics.json").read_text())
        assert abs(metrics["val"]["mae"] - manifest["raw_score"]) < 1e-9
        assert metrics["test"] == {}
        assert (run_dir / "test_predictions.npy").exists()
        assert (run_dir / "code" / "main.py").exists()
        assert not (run_dir / "code" / "kapso_evaluation").exists()
        # Governance contract: the archive is stamped with the evaluator that
        # produced it, and that evaluator's tree is snapshotted under the id.
        label = json.loads((run_dir / "private/selection.json").read_text())
        assert label["evaluator_id"] == manifest["evaluator_id"]
        snapshot = work / "evaluators" / manifest["evaluator_id"]
        assert (snapshot / "grader.py").exists()
        assert (snapshot / "kapso_eval_archive.py").exists()

    def test_rescore_reproduces_the_archived_score(self, tmp_path):
        """run <-> --rescore agreement on the real grader and real data: the
        recomputation from stored predictions must equal the archive-time
        score bit-for-bit, because final selection treats any disagreement
        as tampering and refuses to ship."""
        root, work, run = self._repo(tmp_path)
        proc = run("full")
        assert proc.returncode == 0, proc.stdout[-2000:]
        archived = json.loads(
            proc.stdout.strip().splitlines()[-1].split(" ", 1)[1]
        )
        rescore = subprocess.run(
            [sys.executable, "kapso_evaluation/grader.py",
             "--rescore", str(work / "runs" / "run_0001")],
            cwd=root, capture_output=True, text=True, timeout=300,
        )
        assert rescore.returncode == 0, rescore.stdout[-2000:]
        payload = json.loads(
            rescore.stdout.strip().splitlines()[-1].split(" ", 1)[1]
        )
        assert payload["mode"] == "rescore"
        assert payload["run"] == "run_0001"
        assert payload["score"] == archived["score"]
        assert payload["evaluator_id"] == archived["evaluator_id"]
        assert payload["metrics"]["mae"] == archived["raw_score"]
        assert payload["score"] == -payload["metrics"]["mae"]


# ---------------------------------------------------------------------------
# The final report over the archive
# ---------------------------------------------------------------------------

def _driver_position(tmp_path):
    """The real task from the pristine cache, the spec, and an archive root."""
    from relbench.tasks import get_task

    os.environ["RELBENCH_CACHE_DIR"] = str(RELBENCH_CACHE)
    task = get_task("rel-f1", "driver-position", download=False)
    spec = TaskSpec(
        dataset_name="rel-f1", task_name="driver-position", family=ENTITY_REGRESSION,
        primary_metric="mae", maximize=False, full_timeout=300, debug_timeout=300,
        entity_col="driverId", entity_table="drivers", time_col="date", target_col="position",
        num_eval_timestamps=40, metrics=["mae"],
    )
    (tmp_path / "runs").mkdir()
    return tmp_path, task, spec


# The maintainer-built entrypoint is a thin forwarder onto the provided
# grader — this is the wrapper shape the registered contract expects, and
# using it here proves forwarding covers --rescore.
FORWARDING_WRAPPER = (
    "import subprocess\n"
    "import sys\n"
    "from pathlib import Path\n"
    "raise SystemExit(subprocess.call(\n"
    "    [sys.executable, str(Path(__file__).resolve().parent / 'grader.py'),\n"
    "     *sys.argv[1:]]))\n"
)

DELIVERED = {"campaign": "/w", "branch": "generic_exp_2", "commit": "abc123", "score": -2.7,
             "stopped_reason": "budget_exhausted", "experiments": 3, "cost_usd": 1.5, "harness": "predictive-modelling"}


def _governed_head(work_dir):
    """Stage the evaluation as the runner does (the provided suite plus the
    task's settings) with the maintainer's wrapper, snapshot it, and return
    its fingerprint and the directory."""
    from kapso.execution import evaluation_archive_sandbox as sandbox

    source = stage_evaluation(GENERIC_EVAL_DIR, work_dir, {
        "dataset": "rel-f1", "task": "driver-position", "primary_metric": "mae",
        "higher_is_better": False, "work_dir": str(work_dir), "full_timeout": 300,
        "debug_timeout": 300, "cache_dir": str(RELBENCH_CACHE), "rolling_root": None,
    })
    (source / "kapso_eval.py").write_text(FORWARDING_WRAPPER)
    head = sandbox.fingerprint_tree(source)
    sandbox.snapshot_evaluator_tree(work_dir, source, head)
    return head, source


def _archive_run(runs_dir, name, val_pred, test_pred, status, session="exp_A",
                 forged_val=None, head="", score=None, code="print('candidate')\n"):
    """One archived run as the governed grader would record it: predictions,
    label with evaluator stamp, metrics.json, the code snapshot, and the
    archive-time manifest line the rescore tripwire cross-checks."""
    run_dir = runs_dir / name
    (run_dir / "private").mkdir(parents=True)
    (run_dir / "code").mkdir()
    (run_dir / "code" / "main.py").write_text(code)
    np.save(run_dir / "val_predictions.npy", val_pred)
    np.save(run_dir / "test_predictions.npy", test_pred)
    (run_dir / "private/selection.json").write_text(
        json.dumps({"status": status, "session": session, "by": "test",
                    "evaluator_id": head})
    )
    (run_dir / "private/metrics.json").write_text(
        json.dumps({"val": forged_val or {"mae": 999.0}, "test": {}})
    )
    if score is not None:
        # The manifest's score is oriented for the engine (higher is better):
        # this task's metric is an error, so the raw value travels negated.
        line = {"fidelity": "full", "fraction": 1.0, "seed": 1337,
                "items": int(len(val_pred)), "total_items": int(len(val_pred)),
                "score": -score, "raw_score": score, "higher_is_better": False,
                "run": name, "session": session}
        (run_dir / "manifest.txt").write_text(
            "KAPSO_EVAL_MANIFEST " + json.dumps(line) + "\n"
        )
    return run_dir


@needs_rel_f1
class TestFinalReport:
    """Selection-eligibility labels (user-directed 2026-07-31, after the
    user-ignore incident: the final evaluation shipped a self-disqualified
    leaky intermediate). Pool = registered finals stamped with the HEAD
    evaluator; ranking values are recomputed from stored predictions by the
    head evaluator's own --rescore, never read from metrics.json; the
    winner's test metrics are computed once and its code scanned by the
    harness."""

    def report(self, work_dir, task, spec, source, solution=DELIVERED):
        return scoring.final_report(work_dir, source, task, spec, HARNESS, solution)

    def test_the_report_ignores_pending_and_voided_runs(self, tmp_path):
        work_dir, task, spec = _driver_position(tmp_path)
        head, source = _governed_head(work_dir)
        runs = work_dir / "runs"
        n_val = len(task.get_table("val"))
        n_test = len(task.get_table("test"))
        val_y = task.get_table("val", mask_input_cols=False).df[
            task.target_col].to_numpy(dtype=float)
        expected = float(np.abs(val_y - 11.0).mean())

        # Superseded intermediate with a FORGED perfect metrics.json val and
        # genuinely best predictions — must not be selectable.
        _archive_run(runs, "run_0001", val_y.copy(), np.full(n_test, 11.0), "superseded",
                     forged_val={"mae": 0.0001}, head=head, score=0.0)
        # Registered final: mediocre but real.
        _archive_run(runs, "run_0002", np.full(n_val, 11.0), np.full(n_test, 11.0), "final", head=head, score=expected)
        # Self-voided run with perfect predictions — excluded.
        _archive_run(runs, "run_0003", val_y.copy(), np.full(n_test, 11.0), "self-voided", head=head, score=0.0)

        report = self.report(work_dir, task, spec, source)
        assert report["run"] == "run_0002"
        # Val in the report is the head evaluator's recomputation from the
        # stored predictions, not the (forged-able) metrics.json.
        assert abs(report["val_metrics"]["mae"] - expected) < 1e-9
        assert report["test_metrics"]["mae"] > 0
        assert report["head_evaluator_id"] == head
        assert set(report["scored"]) == {"run_0002"}
        assert report["audit"]["clean"] is True and report["audit"]["regime"] == "seed-time"
        assert report["solution"] == DELIVERED
        assert json.loads((work_dir / scoring.FINAL_REPORT).read_text())["run"] == "run_0002"
        # The winner's test metrics are written back, once.
        assert json.loads((runs / "run_0002" / "private" / "metrics.json").read_text())["test"]["mae"] == report["test_metrics"]["mae"]

    def test_the_harness_scan_reports_a_leak_in_the_winners_code(self, tmp_path):
        work_dir, task, spec = _driver_position(tmp_path)
        head, source = _governed_head(work_dir)
        n_val = len(task.get_table("val")); n_test = len(task.get_table("test"))
        val_y = task.get_table("val", mask_input_cols=False).df[task.target_col].to_numpy(dtype=float)
        _archive_run(work_dir / "runs", "run_0001", np.full(n_val, 11.0), np.full(n_test, 11.0), "final",
                     head=head, score=float(np.abs(val_y - 11.0).mean()),
                     code="t = task.get_table('test', mask_input_cols=False)\n")
        audit = self.report(work_dir, task, spec, source)["audit"]
        assert audit["clean"] is False
        assert any(finding["file"] == "main.py" for finding in audit["findings"])

    def test_session_finals_are_inferred_when_the_hook_never_fired(self, tmp_path):
        """The manifest of record is printed by the maintainer-owned wrapper and
        may carry no run/session identity, so the hook can silently never fire
        (observed live: every run left 'pending' -> the final evaluation errored
        and a completed task recorded as failed). selection.json always records
        the session, so the archive derives each session's last run as its final."""
        work_dir, task, spec = _driver_position(tmp_path)
        head, source = _governed_head(work_dir)
        runs = work_dir / "runs"
        n_val = len(task.get_table("val")); n_test = len(task.get_table("test"))
        val_y = task.get_table("val", mask_input_cols=False).df[task.target_col].to_numpy(dtype=float)
        mae_of = lambda c: float(np.abs(val_y - c).mean())
        # session A: two runs, the later one is the final; session B: one run
        _archive_run(runs, "run_0001", np.full(n_val, 20.0), np.full(n_test, 20.0), "pending", session="exp_A", head=head, score=mae_of(20.0))
        _archive_run(runs, "run_0002", np.full(n_val, 11.0), np.full(n_test, 11.0), "pending", session="exp_A", head=head, score=mae_of(11.0))
        _archive_run(runs, "run_0003", np.full(n_val, 30.0), np.full(n_test, 30.0), "pending", session="exp_B", head=head, score=mae_of(30.0))
        report = self.report(work_dir, task, spec, source)
        status = lambda n: json.loads((runs / n / "private/selection.json").read_text())["status"]
        assert status("run_0001") == "superseded"
        assert status("run_0002") == "final"
        assert status("run_0003") == "final"
        # of the two finals, the oriented score (negated error) picks run_0002
        assert report["run"] == "run_0002"
        assert abs(report["val_metrics"]["mae"] - mae_of(11.0)) < 1e-9

    def test_final_under_a_superseded_evaluator_is_excluded(self, tmp_path):
        """The archive-level mirror of the in-loop None-projection rule: a
        final measured under a superseded evaluator never re-ranks against
        head runs, even with the best raw score on the board."""
        work_dir, task, spec = _driver_position(tmp_path)
        head, source = _governed_head(work_dir)
        runs = work_dir / "runs"
        n_val = len(task.get_table("val")); n_test = len(task.get_table("test"))
        val_y = task.get_table("val", mask_input_cols=False).df[task.target_col].to_numpy(dtype=float)
        mae_of = lambda c: float(np.abs(val_y - c).mean())
        _archive_run(runs, "run_0001", val_y.copy(), np.full(n_test, 11.0), "final", session="exp_A", head="superseded-evaluator", score=0.0)
        _archive_run(runs, "run_0002", np.full(n_val, 11.0), np.full(n_test, 11.0), "final", session="exp_B", head=head, score=mae_of(11.0))
        report = self.report(work_dir, task, spec, source)
        assert report["run"] == "run_0002"
        assert "run_0001" in report["excluded"]
        assert "never re-ranked across rulers" in report["excluded"]["run_0001"]

    def test_edited_archive_score_fails_loud(self, tmp_path):
        """A forged manifest score disagrees with its own recomputation —
        final selection refuses to ship rather than resolving silently."""
        work_dir, task, spec = _driver_position(tmp_path)
        head, source = _governed_head(work_dir)
        n_val = len(task.get_table("val")); n_test = len(task.get_table("test"))
        _archive_run(work_dir / "runs", "run_0001", np.full(n_val, 11.0), np.full(n_test, 11.0), "final", head=head, score=0.0001)
        with pytest.raises(ValueError, match="does not match its recomputation"):
            self.report(work_dir, task, spec, source)

    def test_no_eligible_run_is_the_documented_error_with_the_delivery_beside_it(self, tmp_path):
        """Nothing final under the head: the report says there is no candidate
        and still records what the build delivered (here: nothing)."""
        work_dir, task, spec = _driver_position(tmp_path)
        head, source = _governed_head(work_dir)
        n_val = len(task.get_table("val")); n_test = len(task.get_table("test"))
        _archive_run(work_dir / "runs", "run_0001", np.full(n_val, 11.0), np.full(n_test, 11.0), "self-voided", session="exp_A", head=head)
        _archive_run(work_dir / "runs", "run_0002", np.full(n_val, 11.0), np.full(n_test, 11.0), "invalid", session="exp_A", head=head)
        nothing = {**DELIVERED, "branch": None, "commit": None, "score": None}
        report = self.report(work_dir, task, spec, source, solution=nothing)
        assert report["run"] is None and "no candidate" in report["error"] and report["solution"]["branch"] is None
        status = lambda n: json.loads((work_dir / "runs" / n / "private/selection.json").read_text())["status"]
        assert status("run_0001") == "self-voided" and status("run_0002") == "invalid"

    def test_missing_label_raises(self, tmp_path):
        work_dir, task, spec = _driver_position(tmp_path)
        _head, source = _governed_head(work_dir)
        run_dir = work_dir / "runs" / "run_0001"
        (run_dir / "private").mkdir(parents=True)
        (run_dir / "private/metrics.json").write_text(json.dumps({"val": {"mae": 1.0}, "test": {}}))
        with pytest.raises(FileNotFoundError):
            self.report(work_dir, task, spec, source)

    def test_finalize_stamps_final_and_supersedes_session_siblings(self, tmp_path):
        work_dir, task, _spec = _driver_position(tmp_path)
        runs = work_dir / "runs"
        n_val = len(task.get_table("val")); n_test = len(task.get_table("test"))
        for name, session in (("run_0001", "exp_A"), ("run_0002", "exp_A"), ("run_0003", "exp_B")):
            _archive_run(runs, name, np.full(n_val, 11.0), np.full(n_test, 11.0), "pending", session=session)
        label_run_of_record(str(runs), {"fidelity": "full", "run": "run_0002", "session": "exp_A"}, True)
        status = lambda n: json.loads((runs / n / "private/selection.json").read_text())["status"]
        assert status("run_0002") == "final"
        assert status("run_0001") == "superseded"
        assert status("run_0003") == "pending"  # other session untouched

    def test_finalize_respects_self_voided_and_judge_veto(self, tmp_path):
        work_dir, task, _spec = _driver_position(tmp_path)
        runs = work_dir / "runs"
        n_val = len(task.get_table("val")); n_test = len(task.get_table("test"))
        _archive_run(runs, "run_0001", np.full(n_val, 11.0), np.full(n_test, 11.0), "self-voided")
        label_run_of_record(str(runs), {"fidelity": "full", "run": "run_0001", "session": "exp_A"}, True)
        rec = json.loads((runs / "run_0001/private/selection.json").read_text())
        assert rec["status"] == "self-voided"  # retraction outranks promotion

        _archive_run(runs, "run_0002", np.full(n_val, 11.0), np.full(n_test, 11.0), "pending")
        label_run_of_record(str(runs), {"fidelity": "full", "run": "run_0002", "session": "exp_A"}, False)
        rec2 = json.loads((runs / "run_0002/private/selection.json").read_text())
        assert rec2["status"] == "invalid"

    def test_fast_manifest_is_a_noop(self, tmp_path):
        work_dir, _task, _spec = _driver_position(tmp_path)
        label_run_of_record(str(work_dir / "runs"), {"fidelity": "fast", "run": "", "session": "exp_A"}, True)


class TestBooleanTargetCoercion:
    """Some relbench task tables store a boolean target as text ('t'/'f') —
    rel-trial studies-has_dmc, eligibilities-adult, eligibilities-child.
    relbench's own metrics then raise `pos_label=1 is not a valid label`, which
    killed the calibration run and failed the whole task live. Every consumer
    must see 0/1."""

    def test_text_boolean_target_becomes_int(self):
        table = SimpleNamespace(df=pd.DataFrame({"target": ["t", "f", "T", "F"]}))
        coerce_boolean_target(table, "target")
        assert table.df["target"].tolist() == [1, 0, 1, 0]
        assert str(table.df["target"].dtype) == "int64"

    def test_numeric_target_untouched(self):
        table = SimpleNamespace(df=pd.DataFrame({"target": [0.0, 1.0]}))
        coerce_boolean_target(table, "target")
        assert table.df["target"].tolist() == [0.0, 1.0]

    def test_unexpected_strings_raise(self):
        table = SimpleNamespace(df=pd.DataFrame({"target": ["t", "maybe"]}))
        with pytest.raises(ValueError, match="non-boolean strings"):
            coerce_boolean_target(table, "target")

    def test_a_recommendation_task_has_no_target_and_passes_through(self):
        """A RecommendationTask carries src/dst entity columns and no scalar
        target: the final scoring reaches for `task.target_col`, which is
        None there, and must not raise (observed live on
        rel-ratebeer/user-place-liked at cache-build time)."""
        table = SimpleNamespace(df=pd.DataFrame({"dst": [[1, 2]]}))
        assert coerce_boolean_target(table, None) is table


class TestGraderSelectionLabel:
    def test_void_run_stamps_and_rejects_cross_session(self, tmp_path, monkeypatch):
        import importlib.util
        spec = importlib.util.spec_from_file_location("relbench_grader", GENERIC_EVAL_DIR / "grader.py")
        grader = importlib.util.module_from_spec(spec)
        # Never drop a __pycache__ into the eval suite dir: the grader
        # snapshot/copy tests iterate that directory's entries.
        monkeypatch.setattr(sys, "dont_write_bytecode", True)
        spec.loader.exec_module(grader)

        monkeypatch.setattr(grader, "task_settings", lambda: {"work_dir": str(tmp_path)})
        own_session = grader._session_id()
        sel = tmp_path / "runs" / "run_0001" / "private"
        sel.mkdir(parents=True)
        (sel / "selection.json").write_text(json.dumps(
            {"status": "pending", "session": own_session, "by": "grader"}))
        grader.void_run("run_0001", "seed-day leakage")
        rec = json.loads((sel / "selection.json").read_text())
        assert rec["status"] == "self-voided"
        assert rec["reason"] == "seed-day leakage"

        (sel / "selection.json").write_text(json.dumps(
            {"status": "pending", "session": "someone-else", "by": "grader"}))
        # Refusals come from the vendored archive contract and raise loudly
        # (no exit-code translation layer): cross-session retraction and an
        # empty reason both fail the CLI with the cause in the traceback.
        with pytest.raises(PermissionError, match="belongs to session"):
            grader.void_run("run_0001", "not mine")
        with pytest.raises(ValueError, match="non-empty"):
            grader.void_run("run_0001", "   ")

    def test_strategy_hook_is_wired(self):
        import inspect

        from kapso.execution.search_strategies.generic import strategy as strat
        src = inspect.getsource(strat.GenericSearch)
        assert "_manifest_of_record" in src
        assert "label_run_of_record" in src

        from kapso.execution.evaluation_maintainer.maintainer import parse_manifest_line
        line = ('KAPSO_EVAL_MANIFEST {"fidelity": "full", "fraction": 1.0, '
                '"seed": 1, "items": 5, "total_items": 5, "score": 0.5, '
                '"run": "run_0007", "session": "generic_exp_3"}')
        parsed = parse_manifest_line(line)
        assert parsed["run"] == "run_0007"
        assert parsed["session"] == "generic_exp_3"
