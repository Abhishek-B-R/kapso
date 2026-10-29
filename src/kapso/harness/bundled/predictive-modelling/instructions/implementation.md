# Implementation

Build the chosen idea on the branch and run the task's evaluation.

- Temporal discipline first: every feature for a row at t from data before
  t. The temporal-protocol skill has the pattern for each regime and the
  trap that makes a crippled model look its best on validation.
- Data comes from the task's data reference and the sanitized copy, as the
  task statement describes them; when that reference is a database of the
  relbench-api skill's library, through its API as the skill says. Never a path you
  fetched, never the library's own download; pretrained weights from the
  setup shortlist's local paths, and a load that fails is an error, not a
  fallback.
- Read the feature history file before writing a feature and append to it
  after every experiment; keep the table information file current (the
  living-documents skill, in the shared artifact directory).
- The program follows the eda-discipline skill: the exploration block, the
  error-analysis block, timers, a debug mode that runs the whole pipeline on
  a sample taken within the task's split boundaries, quiet logs. Run debug
  first, then the full evaluation once; a stage knob at the top of the code
  says whether this run trains on the mini sample or in full.
- The practices are the relational-feature-practices skill's, measured, and
  the task-type-playbooks skill's family for the modality; a flat table
  follows the tabular-modeling skill. The text channel exists only when the
  task grants a model API; the metric's own statistic is always the target.
- Cache expensive artifacts (embeddings, feature matrices, per-model
  validation and test predictions) in the shared artifact directory, keyed by
  content and version; check before computing.
- Before launching the evaluation, run the leakage-scan skill's script on your
  diff. Fix every finding, or write in the attempt notes why it is safe. When
  the change touches joins, time handling, data access or the split, also
  ask the leakage-auditor; its report is cheaper than a voided attempt.
- Finish with the cv-protocol skill's reading beside the score: the gain
  against the clustered standard error on internal resampling, the metric
  per slice, the gap to any public measurement the task has. Save each
  family's out-of-fold predictions with the attempt in the shared artifact
  directory: the ensembling skill's fitted blend can only select among
  families that shipped them.
