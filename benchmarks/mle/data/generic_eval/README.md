# MLE-bench provided evaluation suite (for the Evaluation Maintainer)

`grader.py` is the complete, immutable scoring pipeline. The registered
entrypoint (`kapso_eval.py`) must be a thin delegator:

```python
# kapso_eval.py --fidelity fast|full --fraction F --seed S
# -> exec: python kapso_evaluation/grader.py --fidelity <f> --fraction <F> --seed <S>
```

`grader.py` already does everything the entrypoint contract requires: runs
the candidate (`main.py`) in an isolated child process, validates the
`final_submission.csv` it writes at the repository root with the
competition's own validator, reads the held-out score the program reports
in `<score>` tags, and prints the final `KAPSO_EVAL_MANIFEST` line with the
score. Do not reimplement any of it.

## Fidelity semantics

The evaluation cost is the candidate's training run, not scoring items:

- `--fidelity fast` → `python main.py --debug`, the contract's cheap
  whole-pipeline mode, under the debug cap.
- `--fidelity full` → the debug run first, as the gate, then
  `python main.py` under the full cap.
- `--fraction`/`--seed` are echoed into the manifest for grant validation.

## Configuration

The task's settings travel with the grader: `task.json` beside it, written
by the runner (the competition, the metric's direction, the prepared data's
path, the caps, the floor score). The suite needs Python with `mlebench`
installed.

## Hard rules

- Score of record = the manifest's `score` = the held-out score the program
  reports, oriented so that higher is better (`raw_score` is the number
  reported). The official grade on the private answers is never computed
  here: the runner computes it once, after the campaign.
- Never import candidate modules into the scoring process; `grader.py`
  already isolates the candidate in a subprocess.
