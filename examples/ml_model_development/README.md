# ML model development: Spaceship Titanic

A 45-minute build that takes `repo/train.py` from a DummyClassifier at
about 0.50 accuracy toward the brief's 0.78 on the Kaggle Spaceship Titanic
data, with the repository's own `evaluate.py` as the judge. This example is
also the reference for Kapso's full loop (research, learn_knowledge, build,
learn, build again), in `run_full_loop.py`.

Recorded result: not recorded yet.

## What you get

- `repo/train.py`, whose `train_model()` and `predict_with_model()` keep
  their signatures and get new bodies: features, a model, hyperparameters,
  on a branch of its own inside `build/`.
- A score from `repo/evaluate.py --data-dir ./data --seed 0`: accuracy on a
  90/10 train/validation split of `train.csv`.
- `build/.kapso/solution.json`, the record, read back by `Solution.open("build")`.

## Run it

```bash
pip install pandas numpy scikit-learn xgboost lightgbm catboost
kaggle competitions download -c spaceship-titanic && unzip spaceship-titanic.zip -d repo/data/
kapso doctor build
kapso build --brief kapso-brief.md --repo repo --output build --detach
kapso watch build --follow
```

Without the Kaggle CLI, download `train.csv` and `test.csv` from
https://www.kaggle.com/competitions/spaceship-titanic/data into `repo/data/`.
`python run.py` is the same build from Python.

The full loop, which needs the knowledge-graph backends from
`scripts/start_infra.sh` and about five hours:

```bash
python run_full_loop.py
python resume_full_loop.py learning/e2e-facade/<stamp> --from learn   # re-enter a run at a stage
```

## What to look at

- `kapso-brief.md`: the rules say the two functions keep their signatures
  and `test.csv` is never fitted on; the judge holds every candidate to them.
- `solution.explain()`: the score, the stop reason, the cost.
- `cd build && python evaluate.py --data-dir ./data --seed 0`: re-measured by hand.

## Change it

- The target: `Target` in the brief.
- The budget: the brief's `Budget minutes=45 iterations=4`, or the command's
  `--budget-minutes` and `--iterations`, which win over it.
- Protect the evaluator from the start by moving `evaluate.py` into a
  directory of its own and passing it with `--evaluation`.
