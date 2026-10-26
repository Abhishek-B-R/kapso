# ML model development: Spaceship Titanic

A 45-minute build that takes `repo/train.py` from a DummyClassifier at
about 0.50 accuracy toward the brief's 0.78 on the Kaggle Spaceship Titanic
data, with the repository's own `evaluate.py` as the judge. This example is
also the reference for Kapso's full loop (a question researched and ingested
into an index, a build served it, a lesson learned, a build served the index
and the bank), in `run_full_loop.py`.

Recorded result: not recorded yet.

## What you get

- `repo/train.py`, whose `train_model()` and `predict_with_model()` keep
  their signatures and get new bodies: features, a model, hyperparameters,
  on a branch of its own inside `campaign/`.
- A score from `repo/evaluate.py --data-dir ./data --seed 0`: accuracy on a
  90/10 train/validation split of `train.csv`.
- `campaign/.kapso/solution.json`, the record, read back by `Solution.open("campaign")`.

## Run it

```bash
pip install pandas numpy scikit-learn xgboost lightgbm catboost
kaggle competitions download -c spaceship-titanic && unzip spaceship-titanic.zip -d repo/data/
kapso doctor build
kapso build --brief kapso-brief.md --repo repo --output campaign --detach
kapso watch campaign --follow
```

Without the Kaggle CLI, download `train.csv` and `test.csv` from
https://www.kaggle.com/competitions/spaceship-titanic/data into `repo/data/`.
`python run.py` is the same build from Python, into the same `campaign/`
directory: run one or the other.

The full loop, which needs the stores an index is held in (Weaviate and
Neo4j from `scripts/start_infra.sh`), `OPENAI_API_KEY` in `.env` for the
embeddings, and about five hours:

```bash
python run_full_loop.py
python resume_full_loop.py learning/e2e-facade/<stamp> --from learn   # re-enter a run at a stage
```

The same loop from the shell: `kapso experience add --research "..." --name spaceship`,
`kapso build --experience spaceship ...`, `kapso learn campaign`, then
`kapso build --experience spaceship,mine ...`.

## What to look at

- `kapso-brief.md`: the rules say the two functions keep their signatures
  and `test.csv` is never fitted on; the judge holds every candidate to them.
- `solution.explain()`: the score, the stop reason, the cost.
- `cd campaign && python evaluate.py --data-dir ./data --seed 0`: re-measured by hand.
- `kapso trace campaign`: every attempt with its sessions and runs, its
  score and the judge's words, what was rejected and why, what it cost.

## Change it

- The target: `Target` in the brief.
- The budget: the brief's `Budget minutes=45 experiments=4`, or the command's
  `--budget-minutes` and `--budget-experiments`, which win over it.
- Protect the evaluator from the start by moving `evaluate.py` into a
  directory of its own and passing it with `--evaluation`.
