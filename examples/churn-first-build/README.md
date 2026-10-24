# Your first build: churn, with an evaluator present

A ten-minute build that raises a churn model's out-of-sample ROC AUC from the
shipped logistic regression's 0.797 toward the brief's 0.85 target, and hands
back a `Solution`: the winning branch, its score under an evaluator the
campaign cannot edit, and the record of the whole campaign.

Recorded result: the first proof run of the `build` verb (2026-10-24, a
fresh `e2e-standard-4`, `evaluation/evaluate.py`, five minutes and two
experiments) is cited in `docs/plans/redesign/wp1-build.md`; a result on a
released package is not recorded yet.

## What you get

- `repo/predict.py`, the starting model, improved on a branch of its own
  inside `campaign/`, one branch per experiment.
- A score measured by `evaluation/evaluate.py`: ROC AUC on 3,000 held-out
  rows whose labels never enter the workspace.
- `campaign/.kapso/solution.json`, the record; `Solution.open("campaign")` reads
  it from any process, and `kapso deploy campaign` ships it.

## Run it

```bash
python generate.py        # the data: 10,000 training rows, 3,000 held out, seeded
kapso doctor build
kapso build --brief kapso-brief.md --evaluation evaluation --data data --repo repo --output campaign --detach
kapso watch campaign --follow
```

`python run.py` is the same build from Python, into the same `campaign/`
directory: run one or the other. It blocks until the build returns and
prints `solution.explain()`. `--evaluation evaluation` copies the directory
to `kapso_evaluation/` inside the campaign, which is why the brief names
it there.

## What to look at

- `kapso-brief.md`: the objective, how it is measured, the baseline, the
  target, the rules the judge enforces, the budget. Everything the campaign
  knows about the task is in it, and all of it reaches the judge.
- The summary block: `COMPLETED` with the score and the stop reason, or
  `WAITING ON YOU` with what to answer (`kapso inbox campaign`).
- `solution.explain()` and `solution.diff()`: the delivered candidate, its
  measurement, and its code against the seed.
- `git -C campaign branch`: every experiment, kept.

## Change it

- The target: edit `Target` and the objective. A target the data cannot
  reach ends in `max_iterations`, not in a result.
- The budget: the brief's `Budget minutes=10 experiments=4`, or
  `--budget-minutes` and `--budget-experiments` on the command, which win
  over it.
- The evaluator: `evaluation/evaluate.py` runs `python predict.py --data
  kapso_datasets --out predictions.csv`, scores the predictions against the
  private labels, prints `auc: 0.8412` as its last line, writes
  `kapso_evaluation/result.json`, exits 2 on malformed predictions and 3
  when `predict.py` fails; `--fast` scores 600 rows, a smoke check. Change
  the metric there and in `Measured by` together.
- The data: `generate.py` (seed 20261024) writes `data/`, `private/` and
  `MANIFEST.json` with the hash of every file; `baseline.py` records
  `baseline.json` (0.797, bootstrap standard error 0.010). A gradient
  boosting model with no feature work scores 0.832, so there is room.

The hold-out is not sealed by this example: the labels sit outside the two
directories the engine copies into the workspace, and nothing more. Sealing
is the engine's job (evaluation integrity and permissions); until then this
example measures the flow, not the boundary.
