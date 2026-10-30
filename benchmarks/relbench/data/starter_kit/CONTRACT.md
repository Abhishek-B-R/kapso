# Evaluation contract

The evaluation runs your program from the repository root, in two modes:

    python main.py --debug     # must finish fast; validates the pipeline end-to-end
    python main.py             # full training run

After each run it loads, validates, and officially scores:

    $KAPSO_RUN_DATA_DIR/val_predictions.npy
    $KAPSO_RUN_DATA_DIR/test_predictions.npy

Rules:

1. Under the standard regime both files must exist after EVERY run (debug
   included), with rows aligned positionally to `task.get_table("val")` /
   `task.get_table("test")`. Under the rolling regime (the Brief says when;
   the snapshot's `val.parquet` is empty) an invocation writes
   `test_predictions.npy` for the snapshot it is handed, in order, and no
   `val_predictions.npy`: the evaluation assembles the ticks.
   Val predictions must be OUT-OF-SAMPLE: produced by a model that never saw
   val labels in training. Training on train+val is allowed only for the
   model that produces test predictions (the two-model contract).
2. Shapes/dtypes — binary: float (N,) probabilities in [0,1]; regression: float (N,);
   multiclass: float (N, C) scores; recommendation: int (N, K) ranked distinct
   destination ids in [0, num_dst).
3. Your search score is the official VALIDATION primary metric, computed by the
   evaluation. Test metrics are computed privately; you never see them.
4. Data access: the sanitized copy the evaluation binds your run to through
   `RELBENCH_CACHE_DIR` (under the rolling regime, that tick's snapshot); the
   task's names are in `kapso_evaluation/task.json`; `kapso_datasets/common.py`
   loads it correctly. The copy is read-only and complete, test labels are
   physically absent, and `download=True` is never passed. Do not probe for
   what the copy does not hold.
5. You may run `python kapso_datasets/check_predictions.py` yourself after writing
   predictions to pre-validate shapes before the evaluation does; it reads the
   regime from the task's settings and checks what that regime asks for.
6. Session lifetime: your session exists only while you are actively working —
   the moment you stop responding it ends and every process it started is
   killed; no completion notification can ever reach you. Run evaluations and
   long builds in the FOREGROUND, blocking (re-issue foreground waits if a
   single call hits its timeout cap); never background them and end your turn
   "to wait". A backgrounded run dies with the session and scores nothing.
