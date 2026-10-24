# A build with no evaluator: fraud scoring

A fifteen-minute build on labelled transactions and a rule-based scorer,
with no evaluator anywhere. The brief states the protocol instead; the
campaign's first node builds the evaluator from it in `kapso_evaluation/`,
the judge checks that it is fair, and from then on it is registered and
protected like one you had written.

Recorded result: not recorded yet.

## What you get

- `repo/score.py`, three hand-written rules, replaced on a branch of its own
  inside `build/` by a model fitted on the 80 percent split.
- An evaluator the campaign wrote: `build/kapso_evaluation/evaluate.py`,
  following `Measured by` in the brief, registered in
  `build/.kapso/evaluation_registry.json` with provenance `maintainer_built`.
- `solution.evaluation`: the version and provenance the delivered score was
  measured under; `solution.score`, the precision-recall AUC on the held-out
  20 percent.

## Run it

```bash
python generate.py        # 20,000 labelled transactions, seeded, about 5 percent fraud
kapso doctor build
kapso build --brief kapso-brief.md --data data --repo repo --output build --detach
kapso watch build --follow
```

`python run.py` is the same build from Python.

## What to look at

- `kapso-brief.md`: `Measured by` is a protocol, not a path, and `Baseline`
  is `unknown`. The campaign's first measurement replaces the unknown.
- `build/kapso_evaluation/evaluate.py` after the first node: the split, the
  seed, the metric, exactly as the protocol said. Any later candidate that
  edits it is rejected.
- `build/.kapso/evaluation_registry.json`: one version, provenance
  `maintainer_built`.
- `solution.explain()`: the score line names the evaluator version.

## Change it

- The protocol: change the split, the seed or the metric in `Measured by`;
  the evaluator the campaign builds follows the new text.
- The target: `pr_auc above 0.50` is proposed with headroom (the shipped rules score 0.09 under the protocol, gradient boosting with no feature work 0.55, measured 2026-10-24 on the generated data); a target the
  data cannot reach ends in `max_iterations`.
- Bring your own evaluator instead: write it, pass it with `--evaluation`,
  and it is protected from the start; `Measured by` then names the file.
- The data: `generate.py` (seed 20261025) writes `data/transactions.csv`
  and `MANIFEST.json` with its hash.
