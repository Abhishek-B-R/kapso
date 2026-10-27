# A pipeline: the retail warehouse on dbt

The third domain of the semantic suite (`docs/plans/semantic-production-tests.md`):
a dbt project on DuckDB whose three nightly exports carry the defects a real
export does, staging models that pass them through untouched, two marts the
dashboards read, and an evaluator that asserts the data contract. A build
makes the contract hold at the staging layer; a harness author reads this
repository to write a harness for pipelines (the author test of WP9).

Recorded result: not yet run as a build; the shipped project scores
`tests_passing: 0.1538` (two of thirteen assertions: the marts' columns and
the row count) in four seconds on the development box, 2026-10-27.

## What you get

- `repo/`, a dbt project: `models/sources.yml` reads the exports in place as
  CSV, `models/staging/` three views, `models/marts/` two tables,
  `models/schema.yml` and `tests/` the engineer's own tests, `profiles.yml`
  a development profile into `dev.duckdb` at the project root.
- `evaluation/evaluate.py`, the contract: builds the project with its own
  profile into `kapso_evaluation/warehouse.duckdb`, runs thirteen assertions
  with DuckDB directly, prints `tests_passing: <share>` last, writes
  `result.json`; `--fast` builds the staging layer alone (eight assertions,
  not comparable).
- `generate.py`, the exports: seeded, byte-identical, hashes in
  `MANIFEST.json`; 812 customer rows (12 exported twice, 5 without a
  country), 5,060 order rows (60 re-exported, 30 without a customer, 40 with
  one the export never had, 50 with status `unknown`, 26 negative amounts,
  202 lower-case currencies), 4,176 payment rows (40 captured twice, 2% off
  by cents, 1% off by more).

## Run it

```bash
pip install numpy pandas "duckdb==2.0.0" "dbt-core==1.12.6" "dbt-duckdb==1.11.1"   # the generator, the evaluator, the project; the versions the baseline was measured on
python generate.py        # the exports under data/, seeded
kapso doctor build
kapso build --brief kapso-brief.md --evaluation evaluation --data data --repo repo --output campaign --detach
kapso watch campaign --follow
```

`python run.py` is the same build from Python, into the same `campaign/`
directory: run one or the other.

`--data data` lands the exports under `kapso_datasets/` in the workspace; the
evaluator passes that directory to dbt as `data_dir`. To work on the project
by hand: `cd repo && dbt build --profiles-dir . --vars '{data_dir: ../data}'`.

## What to look at

- `kapso_evaluation/result.json` in the campaign's winning branch: each
  assertion with its violations.
- `kapso trace campaign`: the attempts, the hooks, the evaluator's output per
  attempt.
- The staging models on the winning branch: where each defect was handled,
  and whether rows were quarantined or silently dropped (the row-count
  assertion keeps 95% of the exported orders).

## Change it

- A fourth export (`refunds`) with its own defects: a model, a mart column,
  an assertion.
- A stricter reconciliation (a tenth of a percent) once the payments'
  cents are handled.
- A harness for pipelines, written from this repository with the authoring
  guide: the setup session pins the exports, a page per module names the
  staging rules, a hook denies an edit to `models/sources.yml`.
