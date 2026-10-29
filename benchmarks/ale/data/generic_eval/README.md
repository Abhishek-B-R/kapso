# ALE-Bench provided evaluation suite (for the Evaluation Maintainer)

`grader.py` is the complete, immutable scoring pipeline. The registered
entrypoint (`kapso_eval.py`) must be a thin delegator:

```python
# kapso_eval.py --fidelity fast|full --fraction F --seed S
# -> exec: python kapso_evaluation/grader.py --fidelity <f> --fraction <F> --seed <S>
```

`grader.py` already does everything the entrypoint contract requires: it
compiles and judges the candidate's `main.cpp` through the benchmark's own
Docker judge on every public case, averages the total over the configured
runs, and prints the final `KAPSO_EVAL_MANIFEST` line with the score. Do not
reimplement any of it.

## Fidelity semantics

The evaluation cost is the judge's runs over the public cases:

- `--fidelity fast` → one run over every public case.
- `--fidelity full` → the task's configured number of runs; the score is
  the mean total.
- `--fraction`/`--seed` are echoed into the manifest for grant validation.

The candidates also run `grader.py --scores results/scores.json` themselves,
as the harness's scorer procedure, which writes the per-seed results file and
no manifest.

## Configuration

The task's settings travel with the grader: `task.json` beside it, written
by the runner (the problem, the score's direction, the runs, the judge's
workers, the floor score). The suite needs Python with `ale_bench` installed
and Docker available.

## Hard rules

- Score of record = the manifest's `score` = the mean total over the public
  cases, oriented so that higher is better (`raw_score` is the total as the
  contest counts it). A submission with a case not accepted, or scored zero,
  takes the floor: the contest's all-or-nothing rule.
- The private cases and the rating are never computed here: the runner
  computes them once, after the campaign.
