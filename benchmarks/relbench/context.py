"""The RelBench task's facts, as the Brief the runner hands build().

Everything here is the task's own: its definition with the label-generating
code, the label statistics, the schema, the regime and the per-tick
invocation contract, the prediction contract, the data-access rules, the
compute and the paths. Nothing here says how to solve the task: that is the
harness's (src/kapso/harness/bundled/predictive-modelling), and a Brief
carries no standing guidance.
"""

from __future__ import annotations

import inspect
import textwrap
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd

from kapso.handles import Brief

from benchmarks.common import compute_facts, resources
from benchmarks.relbench.task_specs import (
    AUTOCOMPLETE_BINARY,
    DATASET_NOTES,
    ENTITY_BINARY,
    TaskSpec,
    coerce_boolean_target,
)

LEADERBOARD = "https://star-project.stanford.edu/relbench/leaderboard/"
VOID_COMMAND = 'python kapso_evaluation/grader.py --void run_XXXX --reason "<what was wrong>"'


# ---------------------------------------------------------------------------
# The facts
# ---------------------------------------------------------------------------

def describe_database(db, dataset) -> str:
    """Every table with its keys, time column, relationships and every column
    (nothing is clipped: the model reads the whole schema)."""
    lines: List[str] = [
        f"Database time range: {db.min_timestamp} .. {db.max_timestamp} | "
        f"val cutoff V = {dataset.val_timestamp} | test cutoff T = {dataset.test_timestamp}",
        "",
    ]
    for name, table in sorted(db.table_dict.items()):
        df = table.df
        fkeys = ", ".join(f"{c}->{t}" for c, t in table.fkey_col_to_pkey_table.items()) or "none"
        lines.append(
            f"### table `{name}` — {len(df):,} rows | pkey: {table.pkey_col} | "
            f"time_col: {table.time_col} | fkeys: {fkeys}"
        )
        columns = []
        for col in df.columns:
            null_pct = float(df[col].isna().mean()) * 100
            bit = f"{col}:{df[col].dtype}"
            if null_pct >= 1:
                bit += f"({null_pct:.0f}% null)"
            columns.append(bit)
        lines.append("  columns: " + ", ".join(columns))
    return "\n".join(lines)


def label_statistics(spec: TaskSpec, train_df: pd.DataFrame, val_df: pd.DataFrame) -> str:
    lines = []
    for split, df in (("train", train_df), ("val", val_df)):
        if spec.is_recommendation:
            sizes = df[spec.dst_entity_col].map(len)
            lines.append(
                f"- {split}: {len(df):,} rows | ground-truth list size "
                f"mean={sizes.mean():.2f} median={sizes.median():.0f} max={sizes.max()}"
            )
        elif spec.family in (ENTITY_BINARY, AUTOCOMPLETE_BINARY):
            pos = float((df[spec.target_col] == 1).mean())
            lines.append(f"- {split}: {len(df):,} rows | positive rate = {pos:.4f}")
        elif spec.is_multiclass:
            top = df[spec.target_col].value_counts(normalize=True).head(5)
            top_str = ", ".join(f"{int(k)}:{v:.2%}" for k, v in top.items())
            lines.append(
                f"- {split}: {len(df):,} rows | {spec.num_classes} classes | top classes: {top_str}"
            )
        else:
            t = df[spec.target_col]
            lines.append(
                f"- {split}: {len(df):,} rows | target min={t.min():.3g} "
                f"q25={t.quantile(0.25):.3g} median={t.median():.3g} "
                f"q75={t.quantile(0.75):.3g} max={t.max():.3g} mean={t.mean():.3g} "
                f"std={t.std():.5g}"
            )
    return "\n".join(lines)


def nmae_divisor(spec: TaskSpec, train_df: pd.DataFrame) -> Optional[float]:
    """The published boards quote a regression task's error as NMAE =
    MAE / std(train targets); None when the task's metric is not MAE."""
    if spec.primary_metric != "mae":
        return None
    return float(train_df[spec.target_col].std())


def task_definition(task, spec: TaskSpec) -> str:
    doc = inspect.getdoc(type(task)) or ""
    lines = [f"Task `{spec.dataset_name}/{spec.task_name}` — family: {spec.family}."]
    if doc:
        lines.append(f"Official description: {doc}")
    if spec.is_recommendation:
        lines.append(
            f"For each seed row (source `{spec.src_entity_col}` from table "
            f"`{spec.src_entity_table}`, seed time in `{spec.time_col}`), predict the "
            f"ranked top-{spec.eval_k} destination `{spec.dst_entity_col}` ids from table "
            f"`{spec.dst_entity_table}` ({spec.num_dst_nodes:,} candidate ids, integer "
            f"indices 0..{spec.num_dst_nodes - 1}) that the source will interact with in "
            f"(t, t + {spec.timedelta_str}]."
        )
    elif spec.is_autocomplete:
        lines.append(
            f"A row of table `{spec.entity_table}` identified by `{spec.entity_col}` at "
            f"time `{spec.time_col}` is being entered; predict its `{spec.target_col}` "
            "column from the relational context. The target column has been removed "
            "from the database you can access."
        )
        if spec.removed_columns:
            lines.append(
                "Also removed for leakage prevention (do not attempt to reconstruct): "
                + ", ".join(spec.removed_columns)
            )
    else:
        lines.append(
            f"For each seed row (entity `{spec.entity_col}` from table "
            f"`{spec.entity_table}`, seed time in `{spec.time_col}`), predict "
            f"`{spec.target_col}` over the window (t, t + {spec.timedelta_str}]."
        )
    if spec.rolling:
        lines.append(
            f"This task uses {spec.num_eval_timestamps} consecutive evaluation windows "
            "per split (multiple seed timestamps in val/test)."
        )
    if not spec.is_autocomplete:
        # The label-generating code is public task definition, and the most
        # useful fact for feature work and for replaying labels at earlier cutoffs.
        source = textwrap.dedent(inspect.getsource(type(task).make_table))
        lines.append(
            "The label-generating code (`make_table`), the task's definition:\n```python\n"
            + source
            + "\n```"
        )
    return "\n".join(lines)


def prediction_contract(spec: TaskSpec, n_val: int, n_test: int) -> str:
    shape_val = spec.expected_pred_shape(n_val)
    shape_test = spec.expected_pred_shape(n_test)
    if spec.is_recommendation:
        dtype_line = (
            "dtype: integer destination ids in [0, "
            f"{spec.num_dst_nodes}), ranked best-first, distinct within each row"
        )
    elif spec.is_multiclass:
        dtype_line = "dtype: float scores, one column per class (higher = more likely)"
    elif spec.family in (ENTITY_BINARY, AUTOCOMPLETE_BINARY):
        dtype_line = "dtype: float probabilities in [0, 1]"
    else:
        dtype_line = "dtype: float predictions on the original target scale"
    return (
        "Your program `main.py` runs from the repository root, in two modes, and on\n"
        "every run writes into the directory the variable `KAPSO_RUN_DATA_DIR` names:\n"
        f"- `val_predictions.npy`: shape {shape_val}, row i aligned with row i of\n"
        "  `task.get_table(\"val\")` in its original order;\n"
        f"- `test_predictions.npy`: shape {shape_test}, aligned with `task.get_table(\"test\")`;\n"
        f"- {dtype_line}; saved with `np.save`; never reorder, drop or deduplicate\n"
        "  task-table rows;\n"
        "- `metrics.json` beside them is optional (self-measured diagnostics).\n"
        "The evaluation computes the official metrics itself from these files.\n"
        f"Run modes: `python main.py --debug` must finish within {spec.debug_timeout // 60}\n"
        "minutes; it is a pipeline-correctness gate, not a mini training run (subsample,\n"
        "truncate, skip what full mode rebuilds, as long as the whole pipeline runs end\n"
        "to end and both full-shape files are written; constant predictions for the\n"
        "rows it skips are fine), and exceeding the cap kills the run unscored.\n"
        f"`python main.py` (full mode) must finish within {spec.full_timeout / 3600:.1f} hours\n"
        "including every embedding and feature computation."
    )


def rolling_contract(spec: TaskSpec, rolling_root: Path, n_val_ticks: int, n_test_ticks: int) -> str:
    return (
        "The test seed times roll past the database's cutoff, so the evaluation runs\n"
        f"your program once per tick, {n_val_ticks + n_test_ticks} invocations in all\n"
        f"({n_val_ticks} validation ticks, then {n_test_ticks} test ticks), each with\n"
        "`RELBENCH_CACHE_DIR` bound to that tick's snapshot: the database truncated at the\n"
        "tick, `train.parquet` holding every label window already closed by the tick\n"
        "(fully labelled), `test.parquet` holding that tick's rows (inputs only), and an\n"
        "empty, schema-correct `val.parquet`. Each invocation writes\n"
        "`test_predictions.npy` for the snapshot's test rows, in order, and no\n"
        "`val_predictions.npy`: the evaluation assembles the ticks into the official\n"
        "order. The caps cover all invocations together: the full cap for `main.py`,\n"
        f"the debug cap for `main.py --debug` over every tick. The snapshots live under\n"
        f"`{rolling_root}`, and an invocation is handed its own through the variable."
    )


def data_access_rules(spec: TaskSpec, hosted_model_api: str) -> List[str]:
    if hosted_model_api == "openai":
        hosted = (
            "A hosted model API is granted: OpenAI's, with the key in the campaign's .env "
            "(OPENAI_API_KEY), for feature extraction and anything else that helps."
        )
    elif hosted_model_api == "none":
        hosted = "No hosted model API is granted: a model you call runs on this machine."
    else:
        raise ValueError(f"benchmark.hosted_model_api must be 'openai' or 'none', got {hosted_model_api!r}")
    if spec.is_autocomplete:
        copy_rule = (
            "The database keeps rows after the test cutoff T (the test rows must be "
            "predictable); the target column is blanked after T and the columns it derives "
            "from are removed. Do not recover them."
        )
    else:
        copy_rule = (
            "The sanitized copy is truncated at the test cutoff T: rows after T do not "
            "exist in it."
        )
    exposed = "src id" if spec.is_recommendation else "entity id"
    rules = [
        "Never look up this task's published solution: the task may derive from a public "
        "competition, so no winning write-up, leaderboard code, answer key or feature recipe "
        "tuned to it; general methods, domain background and library usage are fine.",
        "Pretrained models may be downloaded and used in any way that helps (fine-tune, "
        "distil, extract features).",
        hosted,
        "External datasets are allowed under one condition: zero leakage into the test "
        "windows, and any leakage voids the experiment. Test labels are public real-world "
        "history, so truncate any source covering this database's domain at the cutoff "
        "before features touch it, and document each source with its provenance and the "
        "leak-free argument in changes.log.",
        "Synthetic data you generate yourself is legal.",
        copy_rule,
        f"Temporal censoring is yours: every feature and join for a seed row at time t uses "
        f"only rows with {spec.time_col} <= t.",
        "Validation labels serve model selection, and training only for the model that "
        "produces the test predictions, never for the one producing the validation "
        "predictions (the two-model contract): the chain that produces validation "
        "predictions (the model, calibrators, thresholds, feature selectors, early "
        "stopping, stackers, blend weights) never saw validation labels; when one pipeline "
        "refits on train+validation for test, the validation predictions stay the pre-refit "
        "model's.",
        f"Test rows expose only ({spec.time_col}, {exposed}). Never call task.stats(), never "
        "read a table's removed_cols, never pass mask_input_cols=False on the test split, "
        "never pass download=True: the copy is complete and read-only.",
        "Every full evaluation is archived and competes in final selection. An archived "
        "evaluation you later find invalid (leakage fixed after it ran) is voided "
        f"explicitly: `{VOID_COMMAND}`; an unvoided invalid run can be selected over your "
        "corrected work on its inflated score.",
    ]
    if spec.rolling:
        rules.append(
            "Under the rolling evaluation an invocation reads only the snapshot it is "
            "handed; reaching for another tick's snapshot or the rolling root is a leak."
        )
    return rules


# ---------------------------------------------------------------------------
# The Brief
# ---------------------------------------------------------------------------

def build_brief(
    task,
    spec: TaskSpec,
    sanitized_copy: Path,
    rolling_root: Optional[Path],
    shared_cache_dir: Path,
    hosted_model_api: str,
    compute: Optional[Dict[str, object]] = None,
) -> Brief:
    """The whole task statement, from the task's own facts: never clipped,
    and nothing in it is guidance."""
    dataset = task.dataset
    train = coerce_boolean_target(task.get_table("train", mask_input_cols=False), spec.target_col)
    val = coerce_boolean_target(task.get_table("val", mask_input_cols=False), spec.target_col)
    test = task.get_table("test")
    db = dataset.get_db()
    compute = compute_facts() if compute is None else compute
    train_std = nmae_divisor(spec, train.df)

    if spec.is_autocomplete:
        regime = "a post-cutoff row with a blanked target: the database keeps its rows after the cutoff"
    elif spec.rolling:
        regime = f"per-row seed time (rolling): {spec.num_eval_timestamps} evaluation ticks per split"
    else:
        regime = "a frozen database, truncated at the test cutoff"
    label_lines = label_statistics(spec, train.df, val.df)
    if train_std is not None:
        label_lines += (
            f"\n- Published-board units: the leaderboard reports NMAE = MAE / std(train "
            f"targets) = MAE / {train_std:.5g}; the constant divisor leaves your MAE "
            "ordering unchanged."
        )
    sections = [
        f"# RelBench task {spec.dataset_name}/{spec.task_name}",
        "The relational deep learning benchmark (relbench.stanford.edu): the best possible "
        "test metric, selected on the official validation metric, with no form of test leakage.",
        DATASET_NOTES[spec.dataset_name],
        "\n## Task definition\n" + task_definition(task, spec),
        "\n## Label statistics\n" + label_lines,
        "\n## Database schema (the library's database: the sanitized copy keeps these tables with the "
        "columns the task definition lists as removed dropped, and truncated at the test cutoff in the "
        "frozen regime)\n" + describe_database(db, dataset),
        "\n## Data\n"
        f"The sanitized copy of the database and the task tables is at `{sanitized_copy}` "
        "(read-only; the evaluation binds your program's run to it through "
        "`RELBENCH_CACHE_DIR`, and `kapso_evaluation/task.json` names it with the task).\n"
        f"The temporal regime: {regime}.\n"
        f"The shared artifact directory, `KAPSO_SHARED_CACHE_DIR`, is `{shared_cache_dir}`: it "
        "persists across experiments and campaigns of this task.\n"
        "The starter kit in `kapso_datasets/`: `common.py` (loads the task from the copy the "
        "run is bound to and saves predictions per the contract), `check_predictions.py` "
        "(checks the prediction files' shapes), `CONTRACT.md`. Files under "
        "`kapso_evaluation/` are not modified.",
        "\n## Prediction contract\n" + prediction_contract(spec, len(val.df), len(test.df)),
    ]
    if spec.rolling:
        sections.append(
            "\n## Per-row seed time: the rolling evaluation\n"
            + rolling_contract(spec, rolling_root, int(val.df[spec.time_col].nunique()),
                               int(test.df[spec.time_col].nunique()))
        )
    sections.append("\n## Compute\n" + resources(compute))
    direction = "higher" if spec.maximize else "lower"
    orientation = "as it is" if spec.maximize else "negated, so that higher is better"
    measured_by = (
        f"validation {spec.primary_metric}, {direction} is better, computed by the evaluation "
        "in `kapso_evaluation/` from your prediction files on the official validation split; "
        f"the engine's score is that metric {orientation}, with the raw value beside it. "
        f"Every official metric is computed: {', '.join(spec.metrics)}. Test metrics are "
        "computed once after the campaign and never shown."
    )
    baseline = (
        "the seeded candidate `main.py`, which writes constant predictions (the training "
        "median for a regression, 0.5 for a binary label, the uniform vector for classes, "
        "the first K ids for a recommendation): its validation score is the floor, and "
        "nothing worse ships."
    )
    target = f"the published entries for this task on the RelBench leaderboard ({LEADERBOARD})"
    if train_std is not None:
        target += f"; regression boards quote NMAE, so divide a MAE by {train_std:.5g} before comparing"
    return Brief(
        objective="\n".join(sections),
        measured_by=measured_by,
        baseline=baseline,
        target=target,
        rules=data_access_rules(spec, hosted_model_api),
    )
