# Competitive-programming guardrails (every module)

Read the task statement before anything else: the problem and its
constraints, the input distribution, the time and memory limits, how it is
scored (an official scorer on a seed list, or a leaderboard) and the
metric's direction, the scoring rule for a failed case, the submission
form and quota when the contest sets them, the deadline, the organizers'
rules. The task's numbers win over anything written here.

## Standing rules

- The official scorer or the board is the score. Nothing else measures a
  solution; a self-reported number is a claim until the scorer says it, and
  the verifier reproduces it.
- A case the scorer reports as failed (a wrong answer, a time limit, a
  runtime error) is a failed case; what one failed case costs the whole
  submission is the task's scoring rule, read there, never assumed.
- The time limit is the task's: budget input and output, a margin, and the
  algorithm inside it, from the largest inputs the constraints allow. An
  anytime search spends the time that remains; an exact method returns
  when it is done.
- Where the task is scored on a leaderboard: the statement's quota is the
  authority on how many submissions there are and whether it resets; it is
  shared by every lane on the account; every submission is recorded in the
  ledger the task root names; a report at the top of the submitted code
  when the rules ask for one; the account's whole history on the task is
  fair inspiration.
- Ship early, then improve: a valid scoring solution within the first
  attempts, then the algorithm.
- Handle the constraints directly. No naive fallback that bypasses an
  error to produce something; when a fallback is needed, a decent one,
  said in the attempt notes.
- Measure before you believe: the heuristic-patterns skill's families and
  the olympiad-playbook skill's house moves are starting points to run on
  every seed, not rankings to assume; a randomised solution is measured
  over repeated runs (the scorer-cli skill).
- Keep the repository's language, build line and layout as the task gives
  them; no library, model or data the task's rules forbid; no
  machine-learned component where the time limit cannot afford it.
