---
name: cv-protocol
description: "How a change is accepted and how a score is read: the official validation number as the selection signal and never the tuning target, the clustered bootstrap gate on internal resampling, folds grouped by the repeated unit, the metric per slice, the windowed reading when the data's horizon is near, the public-versus-internal calibration gap, and the out-of-fold predictions a fitted blend needs. Use before accepting or rejecting any change, when reading an evaluation, and when judging candidates."
---
# Cross-validation protocol

## What the validation number is for

The task's validation split is one finite sample; the hidden test is
another, and the two can differ. The official validation number is the
selection signal and your feedback, not a tuning target: no hyperparameter
search, feature or blend selection, early stopping or design pruning is
driven by it. Tune and gate on internal resampling of the training period
whose splits mirror how test differs from train; treat validation
differences inside noise as ties, broken toward the simpler, more
regularised, more resampling-stable design; and never resubmit near-copies
of the validation-best candidate to polish decimals.

## The gate

Bootstrap the internal metric with the correct clustering unit (resample
whole entities or origins, not rows, when rows within a group are
correlated) and keep a change at roughly one clustered standard error of
paired improvement, or when the paired bootstrap's probability of
improvement is clearly above even. Never a round-number bar: on a mature
design it rejects every honest step, or exceeds what the resampling can
resolve and becomes impassable. Re-measure the full suite occasionally to
confirm small accepted gains compound. When two tests disagree, trust the
one whose resampling unit matches the data's correlation structure.

## Folds

Group the folds by whatever unit repeats across rows (an entity, a
document, a patient, a speaker, an image source, a near-duplicate
cluster) when the task predicts unseen units: a fold that splits a
repeated unit measures memorisation. When the task predicts later
observations of known units (its test rows belong to entities the
training rows hold), the unit recurs across folds by design and the
split is by time instead.
Forward-chaining folds for anything that expands the training set across
time (label replay at earlier cutoffs), and a feature or model is judged
on folds it never saw; a replayed training row whose label window closes
after a fold's origin does not belong in that fold's training set.

## Read by slice

Report the metric per slice beside the aggregate: by the entity's history
depth and recency, by the conditions the task's segments suggest, by class
frequency. A flat aggregate can hide a large move on one slice and the
opposite on another; selection sees only what is reported.

## When the data's horizon is near

When the test origin sits at or near the last timestamps the data covers,
a single flat validation origin can mislead: candidates that fit such a
window have transferred worse. Examine label completeness and the shift
across time, score candidates across temporal sub-windows of validation
under test-identical truncation, choose the windows that represent the
test population, and report the flat and the windowed reading together;
when they disagree, say why before choosing. If the task's evaluator
changes mid-campaign, rescore the comparable candidates on the new ruler
rather than mixing readings.

## The public measurement

When the task has a second, smaller public measurement (a leaderboard's
public split), the gap between it and the internal estimate is the
calibration signal; a candidate chosen on the public number is chosen on
the smaller sample. Record the gap per submission and price later
estimates with it.

## What every family leaves behind

Training-period out-of-fold predictions and the validation and test
prediction vectors, saved with the attempt in the shared artifact
directory keyed by content and version. A fitted blend (the ensembling
skill) can only select among families that shipped them; a fixed blend
evaluated on its own folds does not need them.
