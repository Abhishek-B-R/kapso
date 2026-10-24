# Fixture: churn-with-evaluator

A tabular churn task with an evaluator present. The first fixture of the
semantic suite, and WP1's proof run: a build on it at a five-minute budget
must produce a `Solution`. The shipped logistic regression scores 0.797 AUC
(bootstrap standard error 0.010, `baseline.json`); a gradient-boosting
model with no feature work scores 0.832, so an attempt that finds the
thresholds and the interaction in the data has room to show it.

## What is in it

```
generate.py          deterministic data (seed 20261024): 10,000 training rows, 3,000 holdout rows, 16 features
repo/                the starting repository: predict.py (logistic regression) and its README
evaluation/          evaluate.py, the evaluator Kapso protects; private_dir.txt is written by generate.py
baseline.py          records baseline.json: the shipped model's score, repeats, bootstrap standard error
baseline.json        the recorded baseline, committed
kapso-brief.md       the brief a build takes: objective, the evaluator, the baseline, the target, the rules, a five-minute budget
MANIFEST.json        row counts, positive rates and sha256 of every generated file
data/, private/      generated, never committed
```

## Build on it

```
python generate.py
kapso build --brief kapso-brief.md --evaluation evaluation --data data --repo repo --output ../churn-build
python -c "from kapso import Solution; print(Solution.open('../churn-build').explain())"
```

## Regenerate

```
python generate.py && python baseline.py
```

Both are byte-identical on any machine with the same NumPy and pandas; the
hashes in `MANIFEST.json` say whether they are.

## The evaluator contract

- Invocation: `python kapso_evaluation/evaluate.py` from the workspace root,
  where `predict.py` and `kapso_datasets/` live. The engine copies
  `evaluation/` to `kapso_evaluation/` and `data/` to `kapso_datasets/`.
- The candidate's interface: `python predict.py --data kapso_datasets --out
  predictions.csv`, writing `id,churn_probability` for every holdout id.
- Metric: ROC AUC on the private labels, higher is better, printed as the
  last line `auc: 0.8412`, and written to `kapso_evaluation/result.json` in
  the shape the engine reads (`evaluation_script_path`, `evaluation_output`,
  `score`).
- Exit codes: 0 scored; 2 predictions missing or malformed, reason printed;
  3 `predict.py` failed, its last lines printed; a timeout raises.
- `--fast`: the first 600 holdout rows, a smoke check, not comparable with a
  full score.
- Deterministic: the same predictions file always scores the same; the
  baseline model is deterministic too, so repeats are identical and the
  noise figure is the bootstrap standard error in `baseline.json`.
- Sizing: one train-and-evaluate cycle runs in seconds on a 4-vCPU machine,
  so a five-minute build fits several attempts and the ten-minute semantic
  round fits more.

## What is sealed and what is not

The labels live under `private/`, outside the two directories the engine
copies into a workspace, and the evaluator reaches them by the absolute path
in `private_dir.txt`. Nothing stops a process in the workspace from reading
that path today: sealing the hold-out is the engine's job (evaluation
integrity and permissions, build steps 2 and 6), and the suite's tamper
checks test it then. Until then this fixture measures the flow, not the
boundary.
