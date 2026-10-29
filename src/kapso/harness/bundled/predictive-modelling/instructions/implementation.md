# Implementation

Build the chosen idea on the branch and run the task's evaluation.

- Temporal discipline first: every feature for a row at t from data at or
  before t. The temporal-protocol skill has the pattern for each regime and
  the trap that makes a crippled model look its best on validation.
- Data comes from the prepared copy and the task's data reference, through
  the library's API as the relbench-api skill says. Never a path you fetched,
  never the library's own download.
- Read the feature history file before writing a feature and append to it
  after every experiment; keep the table information file current (the
  living-documents skill).
- Develop on a subsample (one origin, a fraction of the entities) until the
  pipeline is correct end to end, then run the full evaluation once. Print
  library versions and timings. Fix an API mismatch; never abandon the
  approach for it.
- Apply the relational-feature-practices skill as measurements: within-group
  normalisation, capacity matched to the labelled rows, segment coverage,
  dormancy-proof signal, noise-calibrated gates, the decorrelated ensemble as
  its own candidate, label replay at earlier cutoffs, the text channel when
  the task grants a model API, the metric's own statistic, the
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
  out-of-fold predictions with the attempt; a family without them cannot
  join the final ensemble.
