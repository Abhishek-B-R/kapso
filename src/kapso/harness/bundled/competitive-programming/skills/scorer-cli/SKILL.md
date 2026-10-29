---
name: scorer-cli
description: "How to run the official scorer the task root provides on every seed, read its output, and write the results file the harness's hook and the verifier read (score and runtime per seed, the build line, the commit). Use before finishing an attempt, in setup to learn the scorer, and in verification to reproduce an attempt's scores."
---
# The scorer

The task root the task statement names holds the problem's scorer (or the
procedure that reaches the official one), the seeds or cases to score on,
and the baseline. The task statement gives the invocation; the domain
statement records what setup learned about its output and units.

## Running it

Run the scorer on every seed in the task root's seed list, with the build
line the task gives, and record per seed the score and the runtime the
scorer reports. Run it in the foreground and wait: a run started in the
background dies with the session and scores nothing.

## The results file

Write `results/scores.json` beside the solution:

```json
{
  "build": "the compile line used",
  "commit": "the attempt's commit",
  "seeds": {
    "0001": {"score": 123456, "runtime_ms": 1870, "status": "ok"},
    "0002": {"score": 0, "runtime_ms": 2010, "status": "time-limit"}
  }
}
```

Every seed of the task root's list appears, with a numeric score, a
runtime and a status (`ok`, `wrong-answer`, `time-limit`, `runtime-error`).
The require-scorer-run hook refuses a finish while a listed seed is
missing; the verifier reproduces the file seed by seed, so a number the
scorer did not produce is a finding.

## Reading it

A seed at zero is an invalid solution for that seed; the maximum runtime
against the limit with the margin says how much headroom is left; the
spread across seeds says which categories of inputs the solution loses on,
which is what the score-auditor reads.
