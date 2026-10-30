# Bundled harnesses

A harness in this directory loads by name: `kapso build --harness <name>`,
`Kapso().load_harness("<name>")`, the brief's `Harness` line; `kapso harness
list` prints each one under `bundled` with what this machine lacks for it.
Each is a complete harness in the package's own grammar, written from the
benchmarks the engine was measured on (docs/research/harness-ports.md, the
ports of docs/plans/redesign/wp8-harness-ports.md), and holds no task: the
benchmark runners under `benchmarks/` supply the task material and launch a
build with the harness.

| Harness | Domain | Written from |
|---|---|---|
| `predictive-modelling` | structured prediction: a test set that never trains, cross-validation discipline, leakage as the failure that voids, features before architectures, ensembling last; relational databases with a temporal cutoff as the situation its skills name | RelBench (the measured practices, the temporal protocol, the leakage audit), then MLE-bench |
| `competitive-programming` | a scored contest under a clock: validity before score, an insurance submission early, the scorer's measurement over every claim, a submission ledger and a quota spent on purpose; heuristic-optimisation rounds and olympiad-style Kaggle tasks as the modalities its skills name | ALE-Bench (the scorer discipline, the heuristic toolbox), then the IOAI campaigns (the contest economics, the Kaggle flow, the olympiad playbook) |

The gate runs `check` over every directory here at the packaged page budget
and fails on a warning (`tests/test_bundled_harnesses.py`), and scans each
for a benchmark constant. The worked example for writing one lives under
`examples/harnesses/trading/`.
