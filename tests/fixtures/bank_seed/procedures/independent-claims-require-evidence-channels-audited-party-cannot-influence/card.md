# Independent claims require evidence channels the audited party cannot influence.

**Rule:** When reviewers assess train-only discovery, non-use of protected data, or independent score verification, approve the claim only after the relevant check is produced outside the audited party's control; require a blinded replay for discovery, an evaluation-engine access record for non-use, and a separately produced score for verification. If that evidence is missing, label the result provisional and request the missing check, because diffs, path searches, and self-declarations establish visible non-reference, not non-use or independence.

## Is this your situation?

- A result is described as discovered from training data alone, but the builder could read source code or documentation that reveals the generating structure.
- Protected evaluation data may be reachable through a mounted path, parent directory, copied file, credential, or helper program, and no engine access record covers the evaluation period.
- The evaluated party ran the scoring program and supplied the score that determines acceptance, promotion, payment, or a target-crossing decision.
- The available integrity evidence consists of repository diffs, source searches, repeated self-scoring, or declarations rather than a blinded replay or separately produced measurement.

## What to do

1. Write down the claim being reviewed: discovery from permitted data, non-use of protected data, or independent score verification. Identify the privileged artifacts, the evaluated process, the scoring process, and who controlled each credential and log during the relevant period.
2. Ask the evaluation-engine owner for the boundary record. The engine, not the model builder or reviewer, must make generator source, hidden labels, scoring secrets, and private outputs unreadable to the evaluated process and must log access from its account, container, parent directories, mounts, credentials, and helper processes.
3. For a score-verification claim, freeze the model, dependencies, prediction command, and input fingerprint. Request a score produced by an operator or service outside the evaluated party's control. Route its artifact fingerprint, evaluator fingerprint, input fingerprint, score, timestamp, and log location into the final evaluation record.
4. For a discovery claim after source exposure, request a replay by a builder who cannot see the source. Use the same permitted data and decision criterion, then check whether the same mechanism class emerges before attributing discovery to the data rather than to the privileged description.
5. For a non-use claim, accept only an engine-enforced access boundary plus its access record for the full evaluation period. Keep code diffs, path searches, and declarations as supporting diagnostics; do not promote them to proof that a reachable file was never read.
6. The relevant independently controlled check exists? -> attach it to the evaluation record and allow only the claim it establishes. The check is absent, an artifact remained reachable, or the evaluated party supplied the only score? -> label the result provisional and route it to a blinded replay or independent remeasurement before acceptance.

## Why believe this

Independence is about who could influence the evidence, not only what appears in a repository. A clean diff can show an unchanged evaluator, and a path search can show no obvious protected-data reference. Neither proves that another process produced the score or that a builder did not use a visible design. In our run, the judge called a self-reported score of about 0.851 independently verified and called the implementor's deterministic rerun independent, although the engine recorded no evaluation or verification and the judge did not rerun the scorer. The score cleared its target by only about 0.001 AUC, so provenance could change the acceptance claim. The ideator and implementor each declared that they did not open the external label copy; neither reported seeing the workspace copy. Separately, a generator-matched model family was presented as recoverable from training summaries after the generator source had already been read. These episodes support provisional labeling and an independent check, not an allegation of leakage.

**Confidence:** promising — supported in 1 campaign on 1 synthetic churn dataset (0 outcome verdicts, 2 measured scope edges); no counter-evidence; untested in independent campaigns, other datasets, and serving.

---
```yaml
type: procedure
tags: [evaluation-integrity, provenance, access-control, audit, reproducibility]
timestamp: 2026-10-28T12:19:24Z
scope: [harness:none]
scope_conditions: >-
  Applies when model builders or reviewers must substantiate train-only
  discovery, non-use of protected evaluation data, or independent score
  verification while privileged artifacts or scoring channels may be reachable
  by the evaluated process.
evidence:
  - source:
      learner_run: lr_20261028T121924
      trajectory: s6-campaign-one/20261028T113149_facade
      ref: campaign.log#L12-L19
      card_version: 1
    verdict: spawn
    usage: >-
      Never served (the bank was empty); the post-campaign review compared the
      judge's written integrity verdict with the checks the verdict named.
    effect: >-
      The judge called the repeated evaluator execution "a second independent
      full run" and wrote "Integrity verified independently," grounding that
      conclusion in an evaluator diff and path grep while accepting a 0.8508
      score only +0.0008, about 0.08 SE, above the target. This explicit verdict
      on a decision-critical score and its inspection-only rationale finds
      [independent-claims-require-evidence-channels-audited-party-cannot-influence].
  - source:
      learner_run: lr_20261028T121924
      trajectory: s6-campaign-one/20261028T113149_facade
      ref: mined/it-1/flow-1.md#L299-L312
      card_version: 1
    verdict: exercise
    usage: >-
      Never served (the bank was empty); this provenance record describes the
      same measurement as evidence entry 1, not a separate instance or scope
      edge, and supplies only the control details for that judge acceptance.
    effect: >-
      The score provenance was provided, the node output contained the
      implementor's two in-session evaluator runs, the engine recorded no
      evaluation attempt or verification, and the judge read the committed
      result without running the evaluator. Because the accepted score lacked
      a separately controlled remeasurement, this same event exercises the
      card's provisional-label branch without adding another instance.
  - source:
      learner_run: lr_20261028T121924
      trajectory: s6-campaign-one/20261028T113149_facade
      ref: mined/operations.md#L69-L119
      card_version: 1
    verdict: refine
    usage: >-
      Never served (the bank was empty); the post-campaign exposure audit
      inspected label reachability and the checks used to support non-use.
    effect: >-
      Evaluation labels were reachable through an external path and a
      gitignored workspace copy, while the protected path named in the brief
      did not exist. The audit found only the evaluator's scoring reads and no
      other session command reading either copy, but it also established that
      diffs and path searches cannot detect an unrecorded read. This refines the
      card from demonstrated leakage to unverifiable non-use when labels remain
      reachable.
  - source:
      learner_run: lr_20261028T121924
      trajectory: s6-campaign-one/20261028T113149_facade
      ref: mined/operations.md#L120-L141
      card_version: 1
    verdict: refine
    usage: >-
      Never served (the bank was empty); the post-campaign attribution audit
      inspected what the ideation process knew before its train-data analysis.
    effect: >-
      The ideator read the visible generator, stated that it knew the exact
      data-generating process, hard-coded that process to measure the ceiling,
      and later presented constant recovery inside the same family. This prior
      source access refines the recovery result to estimability inside a
      supplied family rather than independent discovery of that family.
reliability:
  state: candidate
  validity: 0.50
  boundary: 0.60
  coverage: 1.00
  score: 0.65
  rationale: >-
    Validity is anchored at 0.50 because the ledger contains 0 confirm, 0
    weaken, and 0 refute outcome verdicts; the reduced-weight founding spawn
    cannot self-confirm, and the exercise entry adds no validity. Boundary
    starts at 0.40 and adds 0.10 for each of two distinct measured refines:
    the reachability audit bounds non-use to unverifiable when labels remain
    reachable, and the source-exposure audit bounds recovery to estimability
    inside a supplied family rather than blinded discovery. The provenance
    exercise is collapsed with the founding judge acceptance, and there is no
    unresolved contradicts edge, giving 0.60. Coverage is 1.00 because the
    ledger's 1 distinct synthetic churn dataset covers 1 of 1 dataset families
    the bank has seen for this domain and scope. Participation is weighted as
    one campaign on one dataset: the founding acceptance and its control
    record are one instance, not two; zero cards were served, so no serving
    outcome or zero-uptake cap applies. The overall score is 0.65 =
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
      Spawned a candidate procedure for reviewers to withhold independent
      discovery, non-use, or score-verification claims until the engine or a
      blinded recheck supplies evidence outside the audited party's control.
  - version: 2
    date: 2026-10-28
    commit: lr_20261028T121924
    change: >-
      reassessed: scored the no-outcome ledger at its neutral validity anchor,
      credited two distinct audit-defined scope edges, and retained candidate
      state because all participation comes from one campaign.
supersedes: null
contradicts: []
probe: >-
  In the next evaluation, run one frozen artifact under a separate account that
  cannot read generator source or evaluation labels, capture access-denial logs
  and a score attestation, and compare that independently produced score with
  the evaluated party's submitted result.
representation: text
```
