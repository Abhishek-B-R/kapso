---
name: contest-economics
description: "How a timed contest's budget is spent: the insurance submission, the round trip, predicting a score before spending one, the calibration gap, the shared board's protocol (skip, steal, complement, ensemble), the late-budget priority rule, the harvest, the validation inflation that mis-ranks, and the pre-submission triage that costs nothing. Use when deciding whether to submit, what to submit next, and how to read the board."
---
# Contest economics

## The loop

A lane runs submit-and-learn rounds until the remaining time cannot fit a
full round trip (build, push, run, submit, score): implement an idea,
validate locally, write down the public score you predict, submit once it
clears the return bar; wait for the score and bank it; the score minus the
prediction is your calibration gap, and it prices every later estimate;
study the gap, every sibling submission and the account's whole history
on this competition; propose the best successor the evidence supports;
go again. A failed or under-target round is material, not a stop. The
session ends when the time gate closes, never because a round succeeded
or looks hard to beat; an idle clock, and above all zero submissions, is
the one unacceptable outcome.

## Insurance first

A valid scoring submission within the first fraction of the budget: the
best result of a campaign has been lost because its lane pushed its first
kernel minutes before the deadline and never submitted. The insurance
pays for everything after it; improve from there.

## Time allocation

Write the time-allocation plan before the first kernel: the round trip's
length (a push, the run, the scoring re-run), the number of rounds that
fit, the margin the last submission needs for its run and scoring. Confirm
a mid-run score only when the expected gain pays for the round trip: a
confirmation of a near-tie buys certainty at the price of an untried
idea.

## The shared board

Every lane submits through one account, so the board is the team's memory.
Before each experiment read it (scores and idea messages) and act in this
order: **skip** an idea a sibling already scored; **steal** the components
behind results stronger than yours (pull the kernel; a proven feature,
schedule or head is free progress); **complement** when your plan lands
within noise of a sibling's, by switching to the variant most different
from the board's leaders (another family, feature view or objective);
**ensemble** once the board holds two or more diverse strong models and
single-model gains go sub-point: a blend of their probabilities is usually
the cheapest points left. Every submission message names the idea and the
local score, so the team's calibration stays computable.

## The shared budget

The task's spend limit covers every lane together, and the board's row
count is the live counter: count it before every spend. Past most of the
budget, prioritise spends your calibration says can beat the current best
submitted score, mapping local scores to public estimates through the
gaps already banked. A priority, not a stop: budget unspent at the
deadline is thrown away, so keep submitting the best available candidates
to the end; what to avoid is re-measuring a variant the board has already
answered.

## The harvest

A pushed kernel lives on the site and survives the machine: any completed
version that was never submitted is still submittable later. Before the
end, and after it, harvest every completed version (list the kernels,
check the status, validate the output, submit the version) rather than
losing it; versions are numbered per kernel from one.

## Validation inflation

Local validation runs optimistic. On grouped or session-structured data a
naive random fold has overstated the public score by a double-digit
margin on more than one contest: use grouped, session-aware validation,
and treat a public gain your own validation cannot explain with suspicion
rather than celebration. The public score is feedback, not the prize: the
final ranking is the private split, so prefer moves that improve the
model over moves that fit the public split's quirks.

## Triage before spending

Sanity-check a candidate's file against a reference of known score before
spending a submission: a prediction-rate or class-share that differs
sharply from the references is a ceiling you can compute, and a candidate
under the ceiling is ruled out for free.

## The ceiling proof

Stop improving when the ceiling is proven: the noise floor of the metric
(repeated scores of the same kernel differ), the gap to the best, and the
budget left say whether a further spend can change the rank; a stop with
the argument written is a decision, a stop without one is a lane idling.
