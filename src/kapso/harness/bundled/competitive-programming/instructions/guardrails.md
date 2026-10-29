# Competitive-programming guardrails (every module)

Read the task statement before anything else: the problem and its
constraints, the input distribution, the time and memory limits, the
scorer or the leaderboard and its units, the submission form and modality,
the quota and the deadline when the contest sets them, the organizers'
rules. The task's numbers win over anything written here.

## Standing rules

- The official scorer or leaderboard is the score. Nothing else measures a
  solution; a self-reported number is a claim until the scorer says it.
- A solution that fails one case fails: a wrong answer or a time-limit
  exceeded on any seed scores zero for that seed, and a seed at zero is an
  invalid solution, whatever the others scored.
- The time limit is the task's. Budget input and output, a safety margin,
  and the algorithm's own time inside it; count operations exactly from
  the largest inputs the constraints allow; spend the time that remains.
- The statement's quota is the authority on how many submissions there
  are, and it is shared by every lane on the account; every submission's
  code opens with a self-contained report (the approach, the model or
  features, the training recipe, how inference produces the output); the
  account's whole history on the task is fair inspiration.
- Ship early, then improve: a valid scoring solution first, within the
  first attempts, then the algorithm. The task root's submission procedure
  is the only way a submission is made (it records what was spent).
- Handle the constraints directly. No naive fallback that bypasses an
  error to produce something; when a fallback is needed, a decent one,
  said in the attempt notes.
- Measure before you believe: the heuristic-patterns skill's families and
  the olympiad-playbook skill's house moves are starting points to run on
  every seed, not rankings to assume.
- Keep the repository's language, build line and layout as the task gives
  them; no library, model or data the task's rules forbid; no
  machine-learned component where the time limit cannot afford it.
