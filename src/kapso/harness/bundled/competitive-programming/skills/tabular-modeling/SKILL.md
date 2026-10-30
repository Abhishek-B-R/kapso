---
name: tabular-modeling
description: "The practices for a flat prediction table: many features before any architecture, gradient-boosted trees as the default with their traps, distribution shift between train and test, dimensionality when features far outnumber rows, the GPU question, and the installed-library API mismatches that stop a run. Use when the task's data is tabular, and when a library call fails on its arguments."
---
# Tabular modelling

- Features first. Handcrafted, generated, aggregated, from other
  libraries, encoded from categories and dates and text: features that
  capture different information and together cover the signal decide
  tabular tasks more than the model does. Keep a feature history (what
  was tried, what it measured, what was kept) in the shared artifact
  directory and widen it every iteration.
- Gradient-boosted trees are the strongest default on a pure table; a
  linear or strongly regularised model is measured beside them when the
  labelled rows are few, and a neural model when the table meets text or
  images.
- Read the feature context against the test distribution: position,
  time and average-based features may differ at test time; represent the
  information behind them (an average per period instead of the period)
  rather than the raw index.
- When features far outnumber rows, measure a reduced or selected matrix
  against the full one before trusting either; a tree model on a very
  wide dense matrix is a candidate for selection, not a rule.
- When the networks and the trees compete for one card, measure which
  gains more per minute of it and give the card to that one; a boosting
  library's GPU histogram is usually worth it on a large table, measured
  once. Empty the GPU cache between runs; print library versions once at
  the start.
- API mismatches are fixed, never a reason to abandon the approach:
  recent LightGBM takes early stopping and logging as callbacks (the
  older keyword arguments raise); recent scikit-learn names its losses
  `absolute_error` and `squared_error`; CatBoost wants its categorical
  columns named; XGBoost's early stopping needs an evaluation set.
- Validate with the folds the data's structure demands (grouped,
  forward-chained, stratified) and gate on measured noise (the
  cv-protocol skill); a held-out share of the training data that nothing
  trains on, not even a hyperparameter, is the honest internal measurement
  when the task gives no validation split.
