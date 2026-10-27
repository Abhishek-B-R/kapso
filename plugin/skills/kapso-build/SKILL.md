---
name: kapso-build
description: Turn what the user wants built into a Kapso campaign — discover the repository's data, evaluation and domain in silence, write the brief (objective, how it is measured, baseline, target, rules, budget), get the evaluation approved through kapso-evaluation, and launch detached with the handoff. Use when the user says build X and verify it, I need Y that meets Z, improve W, make this pass the benchmark, get the metric above a number, ship a model that meets a bar, or runs /kapso:build. Do not use for a one-file change with an obvious fix, for operating a campaign already running (the kapso skill), or inside a Kapso campaign session.
---

# From a wish to a launched campaign

Kapso builds and verifies an objective end to end: it is not a metric-improvement
tool, and "improve the AUC" is one shape of objective among "build a pipeline that
produces X and prove it" or "make this pass the benchmark". The objective is the
user's; your job is to make it buildable and verifiable with as little talking as
the repository allows: discover everything first, in silence, then speak once.

## 1. Listen for two things

What the user wants to exist at the end, and how they would know it is done. Both
may be vague ("a better churn model", "a working ingestion pipeline"): you propose
the measurable form rather than asking for it.

## 2. Discover, in silence, in under a minute

Read the repository: README and docs, data files and directories, notebooks and
their metric cells, test suites, scripts named like evaluators or benchmarks, CI,
dependencies. Infer the domain and the harness that fits (`kapso harness list
--config kapso-config.yaml`; or confirm the one loaded), and read that harness's
setup page (`instructions/setup.md`): what a task statement in this domain must
record becomes questions to the repository, not to the user. Note which experience
sources exist (`kapso experience list --config kapso-config.yaml`: a bank with
cards, a Leeroopedia key, an ingested index).

## 3. The evaluation

Hand what you found to the `kapso-evaluation` skill (`/kapso:kapso-evaluation`),
which owns the one thing the product promise rests on: an evaluation Kapso can
protect. Its three branches: an evaluator found is audited against the contract and
run once for the baseline; a criterion without an evaluator gets one built from the
criterion and the data; neither gets candidate criteria proposed from the
repository with their evidence, one recommended. This happens before the user hears
anything, except the single approval it needs.

## 4. One message

What was found (data, evaluator, baseline, domain), with the evidence each rests on
("`evaluate.py` prints macro-F1 on `data/dev.csv`, 1,204 rows"); the brief as the
file `kapso-brief.md`; the evaluation's protocol for approval when one was built or
changed; and the single thing the user must confirm or edit. Short: the brief is the
message, the prose around it is three lines. The brief, one field per line, indented
lines continuing the field above:

```
Objective    Raise the churn model's out-of-sample AUC above 0.85
             without changing the prediction contract.
Measured by  evaluation/evaluate.py, ROC AUC on the held-out rows
Baseline     0.797 (logistic regression, bootstrap SE 0.010)
Target       0.85
Rules
  - the evaluator is never modified
  - no fitting on the held-out rows
Budget       minutes=60 experiments=10
Harness      predictive-modelling
Experience   mine, leeroopedia
```

- Only `Objective` is required; whatever the user gives goes in verbatim, and the
  whole brief reaches the judge, which stops the campaign only when the objective
  reads as fully achieved and scores every experiment from what the evaluation
  prints. So name the metric and a number, and the judge.
- `Baseline` is measured when that is cheap, else `unknown`. `Target` is the user's,
  or proposed with headroom below any ceiling you can see and the reasoning in one
  line; a target the data cannot reach ends in the inbox, not in a result.
- Rules go in, methods do not: the judge enforces data rules and prohibitions as
  invariants for the whole campaign, and would freeze a method preference the same
  way.
- `Harness` names the domain layer (a bundled name, a directory, a git reference);
  `Experience` names what the build is served, each source existing already
  (`kapso experience add` makes one).

## 5. At most one more round

The user edits a line or says go. A second round only when the edit changes the
evaluation. Never ask twice; never say you cannot proceed.

## 6. Launch, and hand off

```bash
kapso doctor build --json --config kapso-config.yaml
kapso build --brief kapso-brief.md --repo . --evaluation evaluation --data data --output ../churn-campaign --budget-minutes 60 --budget-experiments 10 --config kapso-config.yaml --detach
```

- `--evaluation` only when an evaluator exists or was approved (it is copied and
  protected); without one the campaign builds its own from `Measured by`.
- `--output` is an empty sibling directory, never inside the repository; `--config
  kapso-config.yaml` whenever the project root holds that file.
- The handoff, in the same reply: the brief you passed, what you assumed and that
  the user's own criterion can replace it, the harness and its version when one is
  loaded, `kapso watch ../churn-campaign --follow --config kapso-config.yaml`, and
  that `WAITING ON YOU` is a pause answered through `kapso inbox`. The run outlives
  your tool call; do not poll it.

## Rules

- The criterion comes from the user or the repository, never invented; every
  proposal carries its evidence.
- Never says it cannot proceed; never asks twice; at most two rounds, one question
  each, under five minutes including the approval.
- A one-file change with an obvious fix is done by hand, and you say so instead of
  launching.
- Never launch a campaign the user did not ask for, and never from inside a Kapso
  campaign session.
