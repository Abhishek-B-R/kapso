# Competitive-programming guardrails (every module)

Read the task statement before anything else: the problem and its
constraints, the input distribution, the time and memory limits, the
scorer and its units, the submission form, the quota and the deadline when
the contest sets them. The task's numbers win over anything written here.

## Standing rules

- The official scorer or leaderboard is the score. Nothing else measures a
  solution; a self-reported number is a claim until the scorer says it.
- A solution that fails one case fails: a wrong answer or a time-limit
  exceeded on any seed scores zero for that seed, and a seed at zero is an
  invalid solution, whatever the others scored.
- The time limit is the task's. Budget input and output, a safety margin,
  and the algorithm's own time inside it; count operations exactly, in
  seconds, from the largest inputs the constraints allow, and use the time
  that remains rather than leaving it unspent.
- Handle the constraints directly in the solution. No naive fallback that
  bypasses an error to produce something; when a fallback is needed, a
  decent one, and said in the attempt notes.
- Ship early, then improve: a valid scoring solution first, within the
  first attempts, then the algorithm. A report with every submission says
  what changed and what it scored.
- Measure before you believe: the heuristic-patterns skill's families are
  starting points to run on every seed with the scorer-cli skill, not
  rankings to assume; keep what the seeds' scores keep.
- Keep the repository's language, build line and layout as the task
  statement gives them; no library the task forbids, no machine-learned
  component where the time limit cannot afford its inference.
