# Predictive-modelling guardrails (every module)

Read the task statement before anything else: the data and its shape, the
metric and its direction, the splits and their cutoffs, the prediction
contract, the compute, and the rules the task adds. The task's numbers win
over anything written here.

## Standing rules

- The test set never trains. Test labels are read only by the evaluation.
  Validation labels select models and train the test-predicting model only:
  the model that produces validation predictions never saw them (the
  two-model contract).
- Every feature for a row stamped at time t is computed from data stamped at
  or before t. A join that reaches past the row's own time is a leak, and a
  leak voids the attempt whatever it scores.
- When the task statement says the data is a relational database with a
  temporal cutoff, work from the sanitized copy under `prepared/` (the
  sanitize-cache skill builds it in setup) and follow the temporal-protocol
  skill: the regime, frozen database or per-row seed time, is the task's.
- Reads outside the prepared copy, the task's data reference and the shared
  artifact directory are what the leakage-scan skill and the leakage-auditor
  delegate look for; the verification session voids on their evidence.
- Measure before you assume. Every practice in the
  relational-feature-practices skill is a thing to measure on this task and
  keep only where your own numbers agree.
- Features before architectures; the feature matrix is never finished; an
  ensemble of decorrelated finalists comes last; every accept-or-ship gate is
  calibrated to measured noise, never a round number (the cv-protocol skill).
- No web fetches in implementation and verification. What the task grants
  (a model hub, a hosted model API, external data under its leakage rule) is
  named in the task statement and used as it says.
- Keep the repository's stack and conventions; prefer duckdb to pandas for
  large joins and project columns early; print library versions once;
  suppress progress bars; a few small modules with `main.py` orchestrating.
