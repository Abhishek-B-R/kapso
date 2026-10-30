---
name: scorer-cli
description: "How to run the official scorer the task root provides on every seed of its list, repeated for a randomised solution, read its output, and write the results file at the attempt's root that the harness's finish hook and the verifier read (score, spread and runtime per seed, the status the scorer reported, the build line, the solution it scored). Use before finishing an attempt, in setup to learn the scorer, and in verification to reproduce an attempt's scores."
---
# The scorer

The task root the task statement names holds the problem's scorer (or the
procedure that reaches the official one), the seed list and the baseline.
The seed list is `kapso_datasets/seeds.txt` in the task's data directory,
one seed per line; the task statement gives the scorer's invocation, and
the domain statement records what setup learned about its output, its
units, its direction and the status it reports per case. Without a seed
list the task is not scored by seeds here, and the finish hook has no
opinion.

## Running it

Run the scorer on every seed of the list, with the build line the task
gives, in the foreground (a run started in the background dies with the
session and scores nothing). A randomised solution (annealing, random
search, any search seeded by the clock) is a noisy measurement: score it
over repeated runs per seed, the scorer's own seeds fixed where the task
allows, and record the mean as the score and the spread (the standard
deviation, or the range for few runs) beside it; a difference inside the
spread is not a difference, and the number of runs is the domain
statement's. A deterministic solution runs once.

## The results file

Write `results/scores.json` at the attempt's root (the directory the
session starts in):

```json
{
  "build": "the compile line used",
  "solution": "src/main.cpp",
  "runs": 4,
  "seeds": {
    "0001": {"score": 123456.0, "spread": 310.0, "runtime_ms": 1870, "status": "ok"},
    "0002": {"score": 0.0, "spread": 0.0, "runtime_ms": 2010, "status": "time-limit"}
  }
}
```

`solution` is the file the scorer scored, relative to the attempt's root;
`runs` the runs per seed (1 for a deterministic solution). Every seed of
the list appears with a finite numeric `score`, a `spread`, a
non-negative `runtime_ms` (the maximum over the runs) and a `status` the
scorer reported (`ok`, `wrong-answer`, `time-limit`, `runtime-error`).
The require-scorer-run hook asks once, at the finish, for a file of this
shape written after the solution's last change; it is a mistake catcher,
not the gate: the verifier reproduces the file seed by seed under the same
protocol, so a number the scorer did not produce is a finding there.

## Reading it

A seed whose status is not `ok` is a failed case; what it costs the
submission is the task's scoring rule, read in the statement (a sum over
seeds keeps the others, an all-or-nothing rule does not). The maximum
runtime against the limit with the margin says how much headroom is left;
the spread says what a difference must exceed; the scores across seeds
say which categories of inputs the solution loses on, which is what the
score-auditor reads.
