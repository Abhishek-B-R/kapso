---
name: ensembling
description: "How a final ensemble is built and judged: members chosen for decorrelation, the blend that fits the metric (a fitted meta-model, a mean on the metric's scale, a rank average for ranking metrics) measured against the plain combination, the out-of-fold predictions a fitted blend needs, the ensemble as its own candidate, and the end-of-budget stage. Use when combining models, in the last stage of the budget, and when judging a blended candidate."
---
# Ensembling

- Members are chosen for what they add: models that process the
  information differently (a boosted tree, a linear model, a neural
  model, a different backbone or pretraining), not near-copies at
  different seeds. The test is the pairwise correlation of their
  predictions on the folds: members that score within noise of each other
  and correlate weakly, by the campaign's own spread, are the ones a blend
  pays for.
- The blend fits the metric: a mean of probabilities or of values on the
  metric's own scale for probability and regression metrics (a rank
  average throws away calibration and units there); a rank average for
  ranking and ordering metrics; a fitted meta-model (logistic regression
  or ridge on the members' predictions, fast to train) measured against
  the plain combination on the folds. Keep what wins; a meta-model that
  does not beat its members and the plain combination is not kept.
  Weight a member up on the slice where the per-slice reading shows it
  pays.
- A fitted blend needs every member's cross-fitted (out-of-fold)
  predictions, so a member without them cannot join it; a fixed blend
  evaluated on its own folds needs only the members' predictions.
- The ensemble is submitted as its own candidate: final selection sees
  only candidates, and an ensemble that was never one cannot win.
- Near the end of the budget the work is this: list every archived
  candidate across all branches with its score and the correlations, build
  the blend, measure it, submit it. Heavy ensembles earlier spend budget
  that features would have paid better.
- A blend never rounds probabilities toward certainty to flatter a loss
  metric: a confident wrong answer costs more than the gain on the right
  ones. Calibrate on the metric's own scale instead.
