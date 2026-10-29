# Fixed-holdout sampling error limits decisions near a target.

**Rule:** When a fixed holdout result is near a decision target, use the metric's sampling standard error as the resolution limit for claims, forecasts, confirmation, and stopping; express each relevant margin in standard-error units, treat a training cross-validation score as the center of an uncertain forecast rather than a promised holdout margin, and use deterministic re-runs only to check execution. Continue modelling only when comparable-data evidence shows plausible recoverable gain large enough to change the decision; otherwise report the thin result and stop, because neither modelling nor repeated scoring of the same rows creates a new sample.

## Is this your situation?

- A frozen model is evaluated once on a finite holdout whose rows will remain fixed for the final decision.
- The observed score is close to an acceptance target, while its improvement over a baseline may be much larger.
- A cross-validation point estimate is being used to predict the exact final holdout margin or the direction of its sampling error.
- The team must choose among another deterministic evaluation, more model search, more independent evaluation data, or stopping.

## What to do

1. Freeze the model, predictions, evaluator, metric direction, holdout rows, and decision target. Estimate the holdout metric's sampling standard error with a suitable row-level bootstrap or an analytic estimator fixed before reading the result. For two models scored on the same rows, bootstrap their paired metric difference rather than treating their score errors as independent.
2. Compute every decision-relevant contrast in its own uncertainty units. Use result minus target for target crossing and result minus baseline for practical improvement. Report the observed contrast, its standard-error multiple, and a confidence interval or calibrated crossing probability when the decision requires inferential certainty. Keep a mechanical threshold pass separate from evidence that the result will generalize above that threshold.
3. Forecast the final holdout as a distribution, not as the training cross-validation point estimate. Center the forecast on an appropriately nested or repeated validation estimate, include uncertainty from model selection and validation, then include the holdout's sampling error. Do not assign the realized holdout error a direction in advance; finite-sample noise may move the score either way.
4. If execution could be nondeterministic, hash the model, inputs, predictions, and evaluator, then buy one cheap re-run on the same rows. Matching outputs confirm execution determinism only. Different outputs trigger an execution investigation. To reduce sampling uncertainty, add genuinely independent evaluation rows or authorize a new independent sample; repeated scoring or bootstrapping of the same rows does not add information.
5. Estimate remaining achievable modelling gain on comparable data. Use repeated outer validation, learning-curve saturation, or same-row comparisons across credible model families. If a trustworthy oracle is available, compare it with the candidate on the same rows. Treat the result as approximate when the oracle uses plug-in imputations or the candidate is the selected maximum of a search, because those estimators can bias the apparent gap in opposite directions. Never subtract a holdout score from a ceiling measured on training rows. When no oracle exists, use the strongest credible same-protocol candidate and the stability of recent gains as a conservative bound.
6. All credible same-population gain estimates are well below the holdout standard error and cannot change the operating decision? -> stop model search, record the thin target claim, and route the remaining budget to more independent evaluation data or deployment safeguards. Material recoverable gain remains? -> continue training-data search, but keep the locked holdout out of model selection. The model is adequate but target certainty is still required? -> enlarge or independently repeat the evaluation instead of tuning against the fixed draw.

## Why believe this

A finite holdout score is an estimate from one random draw. Its sampling error remains after the model is frozen, and scoring the same rows again repeats that draw rather than averaging it away. Cross-validation is another noisy estimator, so its point estimate can center a forecast but cannot promise the realized holdout margin or its direction. Headroom also has meaning only when the candidate and reference are measured on comparable data. In our run, the model beat the baseline by about 5 SE but only barely cleared the target. The pre-evaluation forecast explicitly named sampling as the residual risk; the target crossing held, and the final result landed roughly 1.2 SE below the forecast center, an ordinary draw under that forecast. The judge nevertheless assigned a downward direction to sampling noise and read an exact same-row re-run as protection from a one-draw fluke. The stop decision was sound in direction, but its same-row gain estimate remains approximate because it compares a plug-in oracle with a candidate selected by search.

**Confidence:** promising — supported in 1 campaign on 1 synthetic churn dataset (0 outcome verdicts, 2 measured scope edges); no counter-evidence; untested in independent campaigns, other datasets, and serving.

---
```yaml
type: procedure
tags: [holdout-evaluation, sampling-error, forecasting, stopping, uncertainty]
timestamp: 2026-10-28T12:19:24Z
scope: [harness:none]
scope_conditions: >-
  Applies when a frozen model is evaluated on one fixed finite holdout and its
  reported margin or plausible remaining modelling gain is comparable to the
  holdout metric's sampling standard error.
evidence:
  - source:
      learner_run: lr_20261028T121924
      trajectory: s6-campaign-one/20261028T113149_facade
      ref: campaign.log#L12-L19
      card_version: 1
    verdict: spawn
    usage: >-
      Never served (the bank was empty); observed independently in the
      post-campaign judge's result narrative.
    effect: >-
      The result was +0.053 over the 0.797 baseline, about 5.2 bootstrap SE,
      but only +0.0008 over the 0.85 target, about 0.08 SE. These simultaneous
      measured margins show that claim strength depends on distance in
      holdout-SE units and found
      [fixed-holdout-sampling-error-limits-decisions-near-target].
  - source:
      learner_run: lr_20261028T121924
      trajectory: s6-campaign-one/20261028T113149_facade
      ref: mined/it-1/flow-1.md#L104-L116
      card_version: 1
    verdict: exercise
    usage: >-
      Never served (the bank was empty); this is the pre-evaluation half of
      the forecast-and-outcome episode, not a separate scope edge.
    effect: >-
      The proposal used a 0.0101 holdout SE, projected +0.013 over the target
      as about 1.3 SE, explicitly named sampling as the honest residual risk,
      and contrasted that forecast with a weaker model where the coin flip was
      genuine. This exercises, rather than contradicts, the distributional
      forecast branch.
  - source:
      learner_run: lr_20261028T121924
      trajectory: s6-campaign-one/20261028T113149_facade
      ref: campaign.log#L19
      card_version: 1
    verdict: refine
    usage: >-
      Never served (the bank was empty); this is the same forecast-and-outcome
      episode as entry 2, not a separate measurement or scope edge.
    effect: >-
      The judge observed a 0.8508 holdout below the 0.8631 train-CV estimate
      and said the drop went in the direction sampling noise predicts. A
      fixed holdout draw has no predicted error direction, so this explicit
      misreading earns the refine and the procedure's directionless-forecast
      warning.
  - source:
      learner_run: lr_20261028T121924
      trajectory: s6-campaign-one/20261028T113149_facade
      ref: campaign.log#L12-L26
      card_version: 1
    verdict: exercise
    usage: >-
      Never served (the bank was empty); this repeats the same fixed-holdout
      measurement as entry 1 and is not a separate instance or scope edge.
    effect: >-
      A second evaluation on the same 3000 rows reproduced 0.8508 exactly,
      and the judge called it “a second independent full run” and concluded
      “the number is not a one-draw fluke.” The report priced it at about 24
      seconds against 29 minutes of unused budget. Because the rows and
      deterministic path did not change, the cheap check exercised execution
      repeatability but did not reduce sampling uncertainty.
  - source:
      learner_run: lr_20261028T121924
      trajectory: s6-campaign-one/20261028T113149_facade
      ref: campaign.log#L19-L31
      card_version: 1
    verdict: refine
    usage: >-
      Never served (the bank was empty); this is the stop analysis of the same
      campaign outcome, not an independent measurement or scope edge.
    effect: >-
      The judge cited the 0.8636 train-row ceiling and the 0.8508 holdout score
      as ~0.013 of headroom inside the noise floor, while the report separately
      gave 0.8631 for train CV. The mixed-population subtraction is not model
      headroom; this earns the refine to require comparable rows, while these
      rounded figures alone do not establish a precise same-row gap.
  - source:
      learner_run: lr_20261028T121924
      trajectory: s6-campaign-one/20261028T113149_facade
      ref: .kapso/ideation/iter1/claude_code_claude-opus-5.stream.txt#L35-L36
      card_version: 1
    verdict: exercise
    usage: >-
      Never served (the bank was empty); this code-and-output read qualifies
      entry 5's stop analysis and is not a separate measurement or scope edge.
    effect: >-
      The reported 0.8636 train ceiling came from the known generative logit
      after median-filling one missing input and zero-filling another. That
      makes it a plug-in oracle estimate rather than a directly measured
      ceiling, so it can understate remaining headroom.
  - source:
      learner_run: lr_20261028T121924
      trajectory: s6-campaign-one/20261028T113149_facade
      ref: predict.py#L145-L189
      card_version: 1
    verdict: exercise
    usage: >-
      Never served (the bank was empty); this implementation read qualifies
      entry 5's stop analysis and is not a separate measurement or scope edge.
    effect: >-
      The champion estimate was the maximum from a multi-pass coordinate
      search scored as a mean of per-fold AUCs on one fixed split. Selection
      can bias that estimate upward, so its gap to the plug-in oracle is an
      approximate bound, not measured recoverable headroom.
reliability:
  state: candidate
  validity: 0.50
  boundary: 0.60
  coverage: 1.00
  score: 0.65
  rationale: >-
    Validity is anchored at 0.50 because the ledger contains 0 confirm, 0
    weaken, and 0 refute outcome verdicts; the reduced-weight founding spawn
    cannot self-confirm, and the exercise entries add no validity. Boundary
    starts at 0.40 and adds 0.10 for each of two distinct measured refines:
    one holds the directionless fixed-holdout forecast boundary and one
    requires headroom to use comparable populations. The forecast/outcome,
    deterministic-rerun, oracle-read, and implementation-read echoes are
    collapsed into their underlying episodes, and there is no unresolved
    contradicts edge, giving 0.60. Coverage is 1.00 because the ledger's 1
    distinct synthetic churn dataset covers 1 of 1 dataset families the bank
    has seen for this domain and scope. Participation is weighted as one
    campaign on one dataset: repeated scoring and related reads are not
    independent instances; zero cards were served, so no serving outcome or
    zero-uptake cap applies. The overall score is 0.65 =
    round(0.50*0.50 + 0.25*0.60 + 0.25*1.00), and one campaign cannot meet
    the two-campaign activation gate, so state remains candidate. What would
    most change the score is an outcome verdict from an independent campaign
    on a different dataset, especially confirm-grade serving uptake.
  plain: promising — supported in 1 campaign on 1 synthetic churn dataset (0 outcome verdicts, 2 measured scope edges); no counter-evidence; untested in independent campaigns, other datasets, and serving.
provenance: {version: 2}
log:
  - version: 1
    date: 2026-10-28
    commit: lr_20261028T121924
    change: >-
      Spawned a candidate procedure for using fixed-holdout sampling error to
      qualify near-target claims, forecast final results, interpret re-runs,
      and stop only from comparable-data headroom.
  - version: 2
    date: 2026-10-28
    commit: lr_20261028T121924
    change: >-
      reassessed: scored the no-outcome ledger at its neutral validity anchor,
      credited two distinct measured scope edges after collapsing echoes, and
      retained candidate state because all participation comes from one
      campaign.
supersedes: null
contradicts: []
probe: >-
  Before the next locked evaluation, record a validation-based distribution
  for the holdout score and a comparable-data bound on remaining model gain;
  then check whether the realized holdout margin falls inside the forecast and
  whether the predeclared stop branch chooses the same budget allocation.
representation: text
```
