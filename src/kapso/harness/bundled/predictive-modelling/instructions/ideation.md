# Ideation

Propose on the axes, say what each proposal moves, and expect a number.

Exploration axes. Status each one every iteration as active, saturated with
evidence, or deferred, and say which axis a proposal moves on:

1. input features and representation: joins, temporally-censored transforms,
   encodings, cohort priors over the whole database
2. training distribution: episode and window construction, label replay at
   earlier cutoffs, staleness augmentation, sample weighting
3. model mechanism: estimator family, objectives, capacity matched to the
   labelled rows, ensembling
4. decoding and post-processing: calibration, structure constraints,
   blending, snapping to the metric's own lattice
5. validation protocol: origin design, gates, drift estimation

- Feature work has decided these tasks more often than architecture work. A
  proposal that widens the feature matrix across tables the campaign has not
  read is usually the better first bet; one that only swaps the mechanism on
  a frozen matrix is usually the weaker one.
- Read the feature history file first (the living-documents skill): a feature
  already tested is not a new idea, and a dead end with a measured reason is
  not reopened without a new argument.
- Every proposal names the practice it rests on
  (the relational-feature-practices skill), the expected gain against the
  campaign's measured noise, and the slice it should move.
- When the regime is per-row seed time, a proposal says how it recomputes its
  features per tick (the temporal-protocol skill).
- A proposal that only re-tunes the previous candidate is not a new idea. A
  proposal that cannot lose on validation is a leak until proven otherwise.
