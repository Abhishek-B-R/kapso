---
name: cv-protocol
description: "How a change is accepted and how a score is read: the clustered bootstrap gate, the metric per slice, forward-chaining folds, the windowed validation when the label window abuts the data horizon, and the out-of-fold predictions every family must leave behind. Use before accepting or rejecting any change, when reading an evaluation, and when judging candidates."
---
# Cross-validation protocol

## The gate

Bootstrap the validation metric with the correct clustering unit (resample
whole entities or origins, not rows, when rows within a group are
correlated). Keep a change at roughly one clustered standard error of paired
improvement, or when the paired bootstrap's probability of improvement is
about 0.8 or better. Never a round-number bar: it rejects every honest
per-step gain on a mature design, or exceeds what the validation can resolve
and becomes impassable. Re-measure the full suite occasionally to confirm
small accepted gains compound. When two tests disagree, trust the one whose
resampling unit matches the data's correlation structure.

## Read by slice

Report the metric per slice beside the aggregate: by the entity's history
depth and recency, by the conditions the task's segments suggest, by class
frequency. A flat aggregate can hide a large move on one slice and the
opposite on another; selection sees only what is reported.

## Folds

Forward-chaining folds for anything that expands the training set across
time (label replay at earlier cutoffs); a feature or model is judged on folds
it never saw.

## When the label window abuts the data horizon

When the test origin sits at or near the last timestamps the database
covers, a single flat validation origin is presumed dishonest: the better a
candidate fit such a window, the worse it transferred, across three measured
campaigns. From the first full evaluation, score every candidate across
temporal sub-windows of validation under test-identical truncation, gate
selection on the most-shifted window, and report both the flat and the
windowed reading. If the evaluation's ruler changes mid-campaign, the newer
reading is the honest one at once.

## What every family leaves behind

Training-period out-of-fold predictions and the validation and test
prediction vectors, saved with the attempt in the shared artifact directory
keyed by content and version. The final ensemble (the
relational-feature-practices skill's sixth practice) can only select among
families that shipped them.
