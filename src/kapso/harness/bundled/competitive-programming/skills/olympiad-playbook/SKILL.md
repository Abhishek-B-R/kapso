---
name: olympiad-playbook
description: "The ten twists an olympiad-style machine-learning task comes with, the house move to measure first for each with its condition, and how to pull the matching cards from a served experience bank when the campaign has one. Use in ideation when the task is a machine-learning problem under contest rules, before the first proposal."
---
# The olympiad playbook

An olympiad task is a plain prediction task with a twist, and the twist
decides the method. Read the statement and name its twist from the list.
When the campaign serves an experience bank (the session's tools show its
index and card tools), pull what it holds for the twist: the index lists
the cards, and a card's title and tags name the twist its problem had;
open the matched cards and read the idea and the code before proposing.
Without a bank the table below is the starting point on its own. Nothing
here names a past problem or a score: the bank does.

| Twist, from the statement | House move, to measure first |
|---|---|
| **Adapt a provided checkpoint; old classes must keep scoring** | fine-tuning the trunk forgets the old classes unless they are replayed: start from closed-form or routed heads on frozen features, and let a fine-tune earn its place against that on the old classes' score |
| **Labels absurdly scarce** (plenty of data, tens of labels or fewer) | mine the unlabelled structure (clustering, consistency training) and spend the few labels to name what the structure found; a supervised baseline on the few labels is the control |
| **The output is a pairing or a permutation** between two sets | good embeddings plus a global assignment; greedy per-query picks lose the constrained points, so measure the assignment against them |
| **Count, box or locate things** | at olympiad data sizes, classical vision pre-structure (edges, contours, masks) feeding a small learner is the first thing to measure; an end-to-end detector when the data allows it; check per-class or banded scoring quirks |
| **Per-pixel or per-cell output** | align the loss with the metric first (focal, class-weighted), which usually beats architecture work; post-processing is measured after that, on the metric |
| **A fixed model or system is the puzzle itself** (extract its secrets, recover its parameters, craft inputs for it) | read the system's mathematics first; an exact or closed-form solution is the first candidate, a trained one the fallback |
| **Steer a provided generative model** to mandated content | small targeted interventions (attention-only fine-tunes, latent arithmetic) before a full retrain, which costs the most and is measured last |
| **The training data openly lies** (noisy labels, planted outliers, heavy imbalance, fakes) | model the corruption explicitly: two-model agreement for label noise, robust estimators for outliers, reweighting for imbalance |
| **Ordered signal in, structured signal out** (separate, reconstruct, tag, correct, transcribe) | encode the task's invariant into the input (cyclic time, synthetic corruptions, a permutation-invariant loss) before growing the model; mind explicit parameter and feature caps |
| **No twist: plain supervised, executed cleanly** | leak-free features, honest grouped validation, right-sized models; feature engineering and honest cross-validation beat architecture, and a bigger model earns its place by measurement |

Two twists can apply at once (a scarce-label task over a fixed model);
name both and pull cards for both. A twist the list does not hold is a
finding for the harness: say so in the attempt notes.

After the twist: the task-type-playbooks skill gives the family for the
modality, the cv-protocol skill the validation that will not lie, and the
contest-economics skill when to ship it.
