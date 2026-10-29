# Ideation

Propose on the axes, say what each proposal moves, and expect a number.

Exploration axes. Status each one every iteration as active, saturated with
evidence, or deferred, and say which axis a proposal moves on:

1. input features and representation: joins, temporally-censored transforms,
   encodings, cohort priors, handcrafted and domain features
2. training distribution: episode and window construction, label replay at
   earlier cutoffs, staleness augmentation, sample weighting, augmentation
3. model mechanism: the family the task-type-playbooks skill names for the
   modality, capacity matched to the labelled rows, ensembling
4. decoding and post-processing: calibration, structure constraints,
   blending, snapping to the metric's own lattice
5. validation protocol: origin design, gates, drift estimation

- Name the axis a proposal moves; prefer the one that widens the feature
  matrix across tables or sources the campaign has not read (the
  relational-feature-practices skill carries the evidence for that lean).
- Pace by the budget: when a full-data run does not fit the per-run time the
  task statement gives, early iterations train on a stratified sample (the
  mini stage) and the middle of the budget trains in full; the end of the
  budget builds the ensemble of the best archived candidates (the
  ensembling skill). A proposal names its stage, and a parent that scored
  in the mini stage is given a better-tuned sibling in the full one.
- Read the feature history file first (the living-documents skill): a feature
  already tested is not a new idea, and a dead end with a measured reason is
  not reopened without a new argument.
- Every proposal names the practice it rests on, the expected gain against
  the campaign's measured noise, and the slice it should move.
- When the regime is per-row seed time, a proposal says how it recomputes its
  features per tick (the temporal-protocol skill).
- A proposal that only re-tunes the previous candidate is not a new idea
  unless the parent's measurement says tuning is where the gain is. A
  proposal that cannot lose on validation is a leak until proven otherwise.
