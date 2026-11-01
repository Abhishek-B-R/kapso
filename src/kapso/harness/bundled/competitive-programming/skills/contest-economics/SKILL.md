---
name: contest-economics
description: "How a leaderboard contest's budget is spent: the insurance submission, the round trip, predicting a score before spending one, the calibration gap, the shared board's protocol (skip, steal, complement, ensemble), the quota's unit and window, the late-budget priority rule, the scoped harvest, the validation inflation that mis-ranks, the pre-submission triage, and the stopping rationale. Use when deciding whether to submit, what to submit next, how to read the board, and when the work ends."
---
# Contest economics

## The loop

A lane runs submit-and-learn rounds until the remaining time cannot fit a
full round trip (build, push, run, submit, score): implement an idea,
validate locally, write down the public score you predict, submit once it
clears the return bar; wait for the score and bank it; the score minus
the prediction is your calibration gap, and it prices every later
estimate; study the gap, every sibling submission and the account's
whole history on this competition; propose the best successor the
evidence supports; go again. A failed or under-target round is material,
not a stop.

## When the work ends

Three conditions end it, all from the task: the deadline or the session
gate the statement sets closes; the quota is spent; or the stopping
rationale below is written and accepted. A round that succeeded or an
idea that looks hard to beat ends nothing; an idle clock, and above all a
lane with zero submissions, is the one unacceptable outcome.

## Insurance first

A valid scoring submission within the first fraction of the budget: a
lane that pushes its first kernel minutes before the deadline scores
nothing, since a run, a scoring re-run and a rejection all take time the
margin must hold. The insurance pays for everything after it; improve
from there.

## Time allocation

Write the time-allocation plan before the first kernel: the round trip's
length (a push, the run, the scoring re-run), the number of rounds that
fit, the margin the last submission needs for its run and scoring.
Confirm a mid-run score only when the expected gain pays for the round
trip: a confirmation of a near-tie buys certainty at the price of an
untried idea.

## The shared board

Every lane submits through one account, so the account's submissions
list is the team's memory and the standings are the field. Before each
experiment read both and act in this order: **skip** an idea a sibling
already scored; **steal** the components behind results stronger than
yours (pull the kernel; a proven feature, schedule or head is free
progress); **complement** when your plan lands within noise of a
sibling's, by switching to the variant most different from the board's
leaders (another family, feature view or objective); **ensemble** once
the board holds two or more diverse strong models and single-model gains
fall inside the noise floor: a blend of their probabilities is usually
the cheapest points left. Every submission message names the idea and
the local score, so the team's calibration stays computable.

## The quota

The statement gives the quota's unit (submissions, or kernel versions)
and its window (the whole task, or a day that resets): the plan is per
window. The count is the ledger plus the account's submissions list, read
before every spend (the list is paginated: read it whole), and the site's
own remaining-allowance figure where it shows one; where the task root's
procedure reserves the spend, it is the counter. Past most of the window's
budget, prioritise spends your calibration says can beat the current
best submitted score, mapping local scores to public estimates through
the gaps already banked. A priority, not a stop: budget unspent at the
window's end is thrown away, so keep submitting the best available
candidates to the end; what to avoid is re-measuring a variant the board
has already answered.

## The harvest

A pushed kernel lives on the site and survives the machine: any completed
version that was never submitted is still submittable later. Before the
campaign's last round, harvest every completed version of this campaign's
kernels for this competition that was never submitted and still fits the
quota and the submission window (list the kernels, check each version's
status, validate its output, submit it, record it); versions are
numbered per kernel from one.

## Validation inflation

Local validation runs optimistic. On grouped or session-structured data a
naive random fold overstates the public score, often by a wide margin:
use grouped, session-aware validation (the cv-protocol skill), and treat
a public gain your own validation cannot explain with suspicion rather
than celebration. The public score is feedback, not the prize: the final
ranking is the private split, so prefer moves that improve the model over
moves that fit the public split's quirks.

## Triage before spending

Compare a candidate's file with references of known score before spending
a submission: a prediction rate or class share that differs sharply from
every reference is a diagnostic to resolve first (a bug, a shifted
threshold, a wrong id space), not a bound on the score; a candidate whose
output fails the format or the sanity assertions is ruled out for free.

## The stopping rationale

A stop is a decision when three things are written down: the noise floor
of the metric (repeated scores of the same kernel differ), the gap to the
best, and the budget left; together they say whether a further spend is
likely to change the rank, and the argument is read by the feedback
session. It is a rationale, not a proof: another method may still
improve, and the rationale says why the lane will not find it in the
time left. A stop without the argument is a lane idling.
