# Implementation

Build the chosen idea on the branch, score it, and leave the evidence.

- Time awareness first: the time limit minus input and output minus a
  margin is the algorithm's budget; an anytime search reads the clock and
  uses what is left. On a leaderboard task, the time-allocation plan comes
  before the first kernel: the round trip's length, the rounds that fit,
  the margin the last submission needs (the contest-economics skill).
- The cpp-performance skill's rules for a compiled solution: fast input and
  output, pragmas, light random numbers, no allocation in loops, caching,
  a precompute step when the task allows one. On a time-limit failure,
  climb its ladder in order; a good solution implemented badly is not
  pruned for it (the heuristic-patterns skill says how each family is
  pushed further).
- A machine-learning task follows the task-type-playbooks skill's family
  (a flat table, the tabular-modeling skill), the olympiad-playbook skill's
  house move for the twist, the cv-protocol skill's grouped, honest
  validation (for a trained model only: a heuristic solution has no folds,
  and its noise is the repeated-run spread), the eda-discipline skill's
  printed evidence, and the ensembling skill when the board holds diverse
  strong models; the kaggle-cli skill is the mechanics of a kernel.
- Where the task ships a scorer and a seed list: run the scorer-cli skill's
  procedure on every seed before finishing, repeated runs for a randomised
  solution, and write its results file at the attempt's root; the finish
  asks for it once, and the verifier reproduces it.
- Where the task is scored on a leaderboard: ship the insurance within the
  first rounds, then improve; confirm a mid-run score only when the
  expected gain pays for the round trip; submit through the procedure the
  task root names, which records the submission in the ledger (without
  one, record it yourself, the kaggle-cli skill); before the end, harvest
  every completed version that was never submitted. The finish asks once
  for a first submission in the ledger.
- When the scores move in a way you cannot explain, ask the score-auditor
  with the results; before spending a submission, ask the
  submission-auditor with the kernel or the file: a voided submission
  costs the quota.
- When runtime allows, add algorithms to the best solution rather than
  replacing it; the solution's length is bounded only where the task says.
