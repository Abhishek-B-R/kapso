# Predictive-modelling guardrails (every module)

Read the task statement before anything else: the data and its shape, the
metric and its direction, the splits and their cutoffs, the prediction
contract, the compute, the directory it names for shared artifacts, and the
rules the task adds. The task's numbers win over anything written here.

## Standing rules

- The test set never trains. Test labels are read only by the evaluation.
  The official validation number is the selection signal and your feedback,
  not a tuning target: the whole chain that produces validation predictions
  (features, selectors, calibrators, thresholds, early stopping, stackers,
  blend weights) never saw validation labels; the test-predicting chain may
  refit on them (the two-model contract, the cv-protocol skill).
- Every feature for a row stamped at time t is computed from data before
  t, or at t where the task statement admits it (a seed time that includes
  its own stamp); a join past that boundary is a leak and voids the attempt.
- When the task statement says the data is a relational database with a
  temporal cutoff, work from the sanitized copy the statement names (the
  sanitized-copy skill says what one holds and builds it for a relational
  benchmark) and follow the temporal-protocol skill: the regime is the
  task's.
- Reads outside the task's data, the sanitized copy and the shared artifact
  directory are what the leakage-scan skill and the leakage-auditor
  delegate look for; the verification session voids on their evidence.
- Measure before you assume: the relational-feature-practices skill's
  practices are things to measure on this task, kept only where your own
  numbers agree.
- Features before architectures; the feature matrix is never finished; an
  ensemble of decorrelated finalists comes last; every accept-or-ship gate is
  calibrated to measured noise, never a round number (the cv-protocol skill).
- No web access in implementation and verification: the shell's fetchers
  and the native web tools are off there. What the task grants (a model
  hub, a hosted model API, external data under its leakage rule) is named
  in the task statement, fetched in setup, and used as it says.
- Keep the repository's stack and conventions; prefer duckdb to pandas for
  large joins and project columns early; print library versions once;
  suppress the noise in the logs, never the warnings that say a fit went
  wrong; a few small modules with `main.py` orchestrating.
