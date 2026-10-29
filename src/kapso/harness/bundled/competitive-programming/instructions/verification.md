# Verification

Check that the attempt's score is the scorer's or the board's and that it
holds within the rules. The verdict is valid or void, with evidence.

1. Where the task ships a scorer and a seed list: run the scorer-cli
   skill's procedure yourself on every seed, under the protocol the domain
   statement records (the same build line and inputs; the scorer's seeds
   fixed where the task allows; repeated runs for a randomised solution),
   and compare with the attempt's results file seed by seed. A difference
   beyond the recorded spread, or a number the scorer never produced, is a
   finding. Where the task is scored on a leaderboard: read the attempt's
   submission in the ledger and the account's submissions list (the
   kaggle-cli skill): the public score is the measurement, and a pending
   submission is not yet a score.
2. Check the limits and the rules the task sets: the maximum runtime
   against the time limit with the margin, the memory, the build line; the
   kernel's hardware, packages, internet and outside resources where the
   organizers' rules fix them; the output's format against the sample.
3. Compare in the metric's direction against the baseline or the standings'
   best: worse than the baseline is valid but unfinished; say so. Read the
   local validation against the public score: a gap is investigated
   (distribution shift, sampling noise, a leak the cv-protocol skill's
   grouped folds would have caught), never a verdict by itself.
4. Ask the score-auditor with the results across seeds, or the
   submission-auditor with the kernel or the file: they name the category
   of cases where the solution loses, and what would void it.
5. Void when a reported score is not the scorer's or the board's, when a
   rule of the task is broken, or when the task's own scoring rule says a
   failed case invalidates the submission; otherwise valid, with the
   summary naming the scores, the headroom, the failed cases and the
   category findings.
