# Use binned outcome profiles to test a compact nonlinear basis when a regularized linear model underfits.

**Rule:** Use binned outcome profiles to test a compact nonlinear basis when a regularized linear model underfits a low-dimensional tabular target; build it only when cross-fold profiles repeat and the basis beats a budget-matched flexible reference beyond resampling noise, then send that model to the locked holdout. If the shapes or gain do not repeat, keep the flexible learner. This works because explicit smooth bends, thresholds, reversals, and sparse interactions avoid spending tree splits on smooth approximation and noise rejection.

## Is this your situation?

- A regularized linear classifier is materially behind the required validation score, while only a modest number of features appear predictive.
- Numeric label-rate plots show bends, steps, reversals, or saturation that raw linear terms cannot represent.
- An additive smoother improves the baseline but paired slices or residual plots still show one or two concentrated interactions.
- A tree ensemble is the default next step, but the choice between more capacity and a compact functional-form repair has not been tested on identical folds and a declared compute budget.

## What to do

1. Freeze identical stratified folds. Declare a small compute budget for each candidate. Score the current linear model, a budget-matched tree ensemble, and an additive smoother on those folds. Save out-of-fold predictions so every later comparison uses the same rows and metric.
2. Within each training fold, plot label rates and counts over quantile bins for numeric features. Add paired slices only for feature pairs suggested by domain logic or residual structure. Ignore apparent shapes supported by very small bins or shapes that change direction across folds.
3. Translate stable shapes into the smallest basis that expresses them. Use a hinge for a slope change, an indicator for a step, a linear term plus a tail indicator for a reversal, a spline or decay term for a smooth bend, and one product term for a localized interaction.
4. Fit thresholds and shape constants by cross-validation without reading generator code or holdout labels. Keep preprocessing fold-local. If a source file already reveals the functional form, record that form as a prior hypothesis rather than calling the result independent discovery.
5. Compare the regularized basis model with the frozen flexible reference. All profiles repeat and the basis wins beyond resampling noise? -> refit the basis on all training rows and send it to a locked holdout. Any profile is unstable or the win disappears? -> keep the flexible model and retain the plots as diagnostics.
6. If an additive model remains behind and paired slices show a stable interaction, add only that interaction and repeat the comparison. If the gain vanishes across folds, remove the interaction and route the unchanged additive model to the final comparison.

## Why believe this

Trees approximate smooth effects with staircases and can spend many splits screening noise. An additive smoother represents bends efficiently but misses interactions. A small explicit basis removes both costs when training-fold profiles expose the relevant geometry. Observed in our run, a supplied basis led one hand-set slow-learning-rate boosting configuration by about 1.9 AUC points in shared cross-validation, while targeted interactions recovered about 0.8 points for an additive smoother. Later binned training-row tables displayed the pre-specified shapes; they confirmed the basis but did not derive it. The selected model then cleared the locked evaluation. The comparison is an upper bound on blind discovery value because the basis family matched a readable generator and the boosting reference was not searched.

**Confidence:** promising — supported in 1 campaign on 1 synthetic churn dataset (0 outcome verdicts, 1 measured scope edge); no counter-evidence; untested in independent campaigns, other datasets, and serving.

---
```yaml
type: procedure
tags: [tabular, functional-form, feature-engineering, model-selection, cross-validation]
timestamp: 2026-10-28T12:19:24Z
scope: [harness:none]
scope_conditions: >-
  Applies when a regularized linear classifier underfits a low-dimensional
  tabular binary target and training-only outcome profiles show stable smooth
  bends, thresholds, reversals, or sparse pairwise interactions.
evidence:
  - source:
      learner_run: lr_20261028T121924
      trajectory: s6-campaign-one/20261028T113149_facade
      ref: output_data_generic_exp_0/cv_report.json#L9-L60
      card_version: 1
    verdict: spawn
    usage: >-
      Never served (the bank was empty); the implementation recorded the
      train-only comparison and constant search.
    effect: >-
      With the nonlinear family fixed, coordinate search moved five-fold CV
      AUC from 0.8317 at a wrong starting point to 0.8631, and the final guard
      selected the compact basis over the shipped baseline at 0.7982. The
      measured recovery and explicit mechanism found
      [binned-outcome-profiles-test-basis-when-linear-model-underfits].
  - source:
      learner_run: lr_20261028T121924
      trajectory: s6-campaign-one/20261028T113149_facade
      ref: kapso_evaluation/eval_profile.md#L33-L57
      card_version: 1
    verdict: exercise
    usage: >-
      Never served (the bank was empty); the implementation later computed
      training-row tables as a confirmation pass after the basis was fixed.
    effect: >-
      Binned outcome tables on training rows reproduced a step, a reversal, a
      late upturn, and a localized pairwise interaction already represented by
      the pre-specified basis. These tables confirm that the procedure's shape
      trigger was visible in permitted training data. Although they did not
      derive the basis, their measured shapes exercise the procedure's
      confirmation trigger.
  - source:
      learner_run: lr_20261028T121924
      trajectory: s6-campaign-one/20261028T113149_facade
      ref: mined/it-1/flow-1.md#L56-L69
      card_version: 1
    verdict: exercise
    usage: >-
      Never served (the bank was empty); this ideation table used the same
      training rows and folds as the constant search and is not a separate
      independent measurement.
    effect: >-
      One hand-set slow-learning-rate histogram boosting configuration scored
      0.8437, the additive smoother scored 0.8463, the interaction-enhanced
      smoother scored 0.8539, and the compact basis scored 0.8629. This one
      table does not establish a tuning plateau because the boosting reference
      was not searched. Within that boundary, its shared-fold ordering
      exercises the functional-form repair and omitted-interaction branches.
  - source:
      learner_run: lr_20261028T121924
      trajectory: s6-campaign-one/20261028T113149_facade
      ref: mined/it-1/flow-1.md#L320-L336
      card_version: 1
    verdict: exercise
    usage: >-
      Never served (the bank was empty); the locked evaluation was measured
      after model choice, with the deterministic rerun treated as the same
      measurement.
    effect: >-
      The selected basis returned 0.8508 on the full protected evaluation after
      train-only selection. This successful locked evaluation exercises the
      procedure's output route without isolating the basis-versus-boosting gain
      on holdout rows.
  - source:
      learner_run: lr_20261028T121924
      trajectory: s6-campaign-one/20261028T113149_facade
      ref: mined/operations.md#L120-L141
      card_version: 1
    verdict: refine
    usage: >-
      Never served (the bank was empty); one post-campaign exposure audit
      compared the visible generator, the ideation sequence, and the shipped
      search to bound what the comparison can establish.
    effect: >-
      The ideator read a visible generator, hard-coded its logit before the
      binned tables, measured its 0.8636 ceiling, labelled the next probe for
      the data-generating basis, and printed the true constants beside the
      recovery exercise. This single scope edge refines the episode to later
      profile confirmation and constant estimability within a supplied family,
      not independent discovery of that family.
reliability:
  state: candidate
  validity: 0.50
  boundary: 0.50
  coverage: 1.00
  score: 0.63
  rationale: >-
    Validity is anchored at 0.50 because the ledger contains 0 confirm, 0
    weaken, and 0 refute outcome verdicts; the reduced-weight founding spawn
    cannot self-confirm, and the exercise entries add no validity. Boundary
    starts at 0.40 and adds 0.10 for the one distinct measured refine:
    readable-generator exposure bounds the mechanism to confirmation and
    constant estimation inside a supplied nonlinear family; echoed uses of
    that exposure are collapsed, and there is no unresolved contradicts edge,
    giving 0.50. Coverage is 1.00 because the ledger's 1 distinct synthetic
    churn dataset covers 1 of 1 dataset families the bank has seen for this
    domain and scope. Participation is weighted as one campaign on one
    dataset: shared rows, folds, reruns, and the founding restatement are not
    independent instances; zero cards were served, so no serving outcome or
    zero-uptake cap applies. The overall score is 0.63 =
    round(0.50*0.50 + 0.25*0.50 + 0.25*1.00), and one campaign cannot meet
    the two-campaign activation gate, so state remains candidate. What would
    most change the score is an outcome verdict from an independent campaign
    on a different dataset, especially confirm-grade serving uptake.
  plain: promising — supported in 1 campaign on 1 synthetic churn dataset (0 outcome verdicts, 1 measured scope edge); no counter-evidence; untested in independent campaigns, other datasets, and serving.
provenance: {version: 2}
log:
  - version: 1
    date: 2026-10-28
    commit: lr_20261028T121924
    change: >-
      Spawned a candidate procedure from the measured basis comparison and
      later profile confirmation, with readable-generator exposure and the
      unsearched boosting reference recorded as discovery boundaries.
  - version: 2
    date: 2026-10-28
    commit: lr_20261028T121924
    change: >-
      reassessed: scored the no-outcome ledger at its neutral validity anchor,
      credited one distinct generator-exposure scope edge, and retained
      candidate state because all participation comes from one campaign.
supersedes: null
contradicts: []
probe: >-
  On a new tabular classification task with no readable generator, freeze one
  flexible reference, derive basis terms only from training-fold profiles, tune
  them inside resampling, and test whether the basis improves a locked later
  holdout beyond its uncertainty.
representation: text
```
