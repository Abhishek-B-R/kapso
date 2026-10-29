---
name: ensembling
description: "How a final ensemble is built and judged: members chosen for decorrelation, out-of-fold predictions for every member, a fitted meta-model measured against the simple average, the ensemble as its own candidate, and the end-of-budget stage. Use when combining models, in the last stage of the budget, and when judging a blended candidate."
---
# Ensembling

- Members are chosen for what they add: models that process the
  information differently (a boosted tree, a linear model, a neural
  model, a different backbone or pretraining), not near-copies at
  different seeds. The relational-feature-practices skill's sixth practice
  gives the test: pairwise prediction rank-correlation among finalists,
  and a blend of the decorrelated ones.
- Every member ships training-period out-of-fold predictions and its
  validation and test predictions; a member without them cannot join.
- Blend two ways and measure both on forward folds: a fitted meta-model
  (logistic regression or ridge on the members' predictions, fast to
  train) and the plain rank-average. Keep the one that wins on your
  folds; a meta-model that does not beat its members and the average is
  not kept. Weight a member up on the slice where the per-slice reading
  shows it pays.
- The ensemble is submitted as its own candidate: final selection sees
  only candidates, and an ensemble that was never one cannot win.
- Near the end of the budget the work is this: list every archived
  candidate across all branches with its validation score and the
  correlations, build the blend, measure it, submit it. Heavy ensembles
  earlier spend budget that features would have paid better.
- A blend never rounds probabilities toward certainty to flatter a loss
  metric: a confident wrong answer costs more than the gain on the right
  ones. Calibrate on the metric's own scale instead.
