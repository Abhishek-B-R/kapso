# Feedback

Weigh beside the score, in the metric's direction:

- the score and the runtime against the baseline, the current best or the
  standings, per seed and overall; for an anytime search, headroom left
  unspent under the time limit is a finding;
- which family the candidate belongs to and whether that family is
  saturated with evidence (the heuristic-patterns skill names the
  families): a third annealer with new moves is not a new family;
- the category of cases where the candidate loses, never a single case,
  and as findings, not fixes: the next proposal decides the fix;
- a measured difference: one inside the repeated-run spread or the
  measured noise is a tie;
- where the task is scored on a leaderboard, the economics (the
  contest-economics skill): the time to a first strong score, the
  critical-path velocity (how fast the lane turns a round), the
  confirmation overhead (rounds spent re-measuring near-ties), the compute
  ledger (what each round cost against what it returned), and the
  calibration gap between the predicted and the public score;
- a blended candidate by the ensembling skill's rule: a blend that does
  not beat its members is not an ensemble;
- a stop as a decision only with the noise floor, the gap and the budget
  written down (the contest-economics skill's stopping rationale);
- the floor: a candidate worse than the baseline does not ship; on a
  leaderboard, a candidate the account's best already beats is spent on
  only when the economics say so (a harvest, a diverse member for a blend).
