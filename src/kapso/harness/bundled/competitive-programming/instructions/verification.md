# Verification

Check that the attempt's score is the scorer's or the board's and that it
holds within the rules. The verdict is valid or void, with evidence.

1. Run the scorer-cli skill's procedure yourself on every seed of the task
   root; compare with the attempt's results file seed by seed. A score the
   attempt reports that the scorer does not reproduce is a finding. On a
   leaderboard task, read the attempt's submission in the ledger and the
   board (the kaggle-cli skill): the public score is the measurement, and
   a submission that is pending is not yet a score.
2. Check the limits and the rules: the maximum runtime against the time
   limit with the margin, the memory, the build line; the kernel's
   hardware, packages, internet and outside resources against the
   organizers' rules; the output's format against the sample.
3. Compare against the baseline or the board's best: below it is valid but
   unfinished; say so. Read the local validation against the public score:
   an inflation the cv-protocol skill's grouped folds would have caught is
   evidence of a leak.
4. Ask the score-auditor with the results across seeds, or the
   submission-auditor with the kernel: they name the category of cases
   where the solution loses, and what would void it.
5. Void when a seed fails, a reported score is not the scorer's, or a rule
   is broken; otherwise valid, with the summary naming the scores, the
   headroom and the category findings.
