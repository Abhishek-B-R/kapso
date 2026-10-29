# Implementation

Build the chosen idea on the branch and run the task's evaluation.

- Temporal discipline first: every feature for a row at t from data at or
  before t. The temporal-protocol skill has the pattern for each regime and
  the trap that makes a crippled model look its best on validation.
- Data comes from the prepared copy and the task's data reference, through
  the library's API as the relbench-api skill says. Never a path you fetched,
  never the library's own download; pretrained weights from the setup
  shortlist, and a load that fails is an error, not a fallback.
- Read the feature history file before writing a feature and append to it
  after every experiment; keep the table information file current (the
  living-documents skill).
- The program follows the eda-discipline skill: the exploration block, the
  error-analysis block, timers, a debug mode that runs the whole pipeline on
  a stratified sample, quiet logs. Run debug first, then the full evaluation
  once; a stage knob at the top of the code says whether this run trains on
  the mini sample or in full (the ideation page's pacing).
- Apply the relational-feature-practices skill as measurements, the
  task-type-playbooks skill's family for the modality, and the
  tabular-modeling skill's practices on a flat table: within-group
  normalisation, capacity matched to the rows, segment coverage,
  dormancy-proof signal, noise-calibrated gates, label replay, the text
  channel when the task grants a model API, the metric's own statistic, the
  label-determinism audit.
- Cache expensive artifacts (embeddings, feature matrices, per-model
  validation and test predictions) in the shared artifact directory, keyed by
  content and version; check before computing.
- Before launching the evaluation, run the leakage-scan skill's script on your
  diff. Fix every finding, or write in the attempt notes why it is safe. When
  the change touches joins, time handling or data access, also ask the
  leakage-auditor; its report is cheaper than a voided attempt.
- Finish with the cv-protocol skill's reading beside the score: the clustered
  standard error of the gain, the metric per slice, the windowed validation
  when the label window abuts the data horizon. Save each family's
  out-of-fold predictions with the attempt: the ensembling skill's blend can
  only select among families that shipped them.
