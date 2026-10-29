# Verification

Check that the attempt's score is the scorer's and that it holds on every
seed within the limits. The verdict is valid or void, with evidence.

1. Run the scorer-cli skill's procedure yourself on every seed of the task
   root; compare with the attempt's results file seed by seed. A score the
   attempt reports that the scorer does not reproduce is a finding.
2. Check the limits: the maximum runtime over the seeds against the time
   limit with the margin, the memory where the task limits it, the build
   line the task gives. A seed over the limit, or a seed at zero, is an
   invalid solution.
3. Compare against the baseline the task root provides and the current
   best: a solution below the baseline is valid but unfinished; say so.
4. Ask the score-auditor with the results across seeds: it names the
   category of cases where the solution loses and whether the loss is a
   bug (a constraint mishandled, an output format error) or the method.
5. Void when a seed fails or a reported score is not the scorer's;
   otherwise valid, with the summary naming the scores, the runtime
   headroom and the category findings.
