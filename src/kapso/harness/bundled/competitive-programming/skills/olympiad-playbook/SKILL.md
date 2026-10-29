---
name: olympiad-playbook
description: "The ten twists an olympiad-style machine-learning task comes with, the house move for each, and how to pull the matching cards from a served experience bank before proposing. Use in ideation when the task is a machine-learning problem under contest rules, before the first proposal."
---
# The olympiad playbook

An olympiad task is a plain prediction task with a twist, and the twist
decides the method. Read the statement, name its twist from the list,
then pull what a served bank holds for it: `bank_index` lists the cards,
and a card's title and tags name the twist its problem had; open the
matched cards with `bank_get_card` and read the idea and the code before
proposing. Nothing here names a past problem or a score: the bank does.

| Twist, from the statement | House move |
|---|---|
| **Adapt a provided checkpoint; old classes must keep scoring** | never fine-tune the trunk: closed-form or routed heads on frozen features (fine-tuning memorises and forgets) |
| **Labels absurdly scarce** (plenty of data, tens of labels or fewer) | mine the unlabelled structure (clustering, consistency training) and spend the few labels only to name what the structure found |
| **The output is a pairing or a permutation** between two sets | good embeddings plus a global assignment solve; greedy per-query picks lose the constrained points |
| **Count, box or locate things** | at olympiad data sizes, classical vision pre-structure (edges, contours, masks) feeding a small learner beats an end-to-end detector; check per-class or banded scoring quirks |
| **Per-pixel or per-cell output** | align the loss with the metric first (focal, class-weighted): it routinely beats architecture work; post-processing rarely pays |
| **A fixed model or system is the puzzle itself** (extract its secrets, recover its parameters, craft inputs for it) | read the system's mathematics first; the winners are usually exact or closed-form, not trained |
| **Steer a provided generative model** to mandated content | small targeted interventions (attention-only fine-tunes, latent arithmetic), never a full retrain |
| **The training data openly lies** (noisy labels, planted outliers, heavy imbalance, fakes) | model the corruption explicitly: two-model agreement for label noise, robust estimators for outliers, reweighting for imbalance |
| **Ordered signal in, structured signal out** (separate, reconstruct, tag, correct, transcribe) | encode the task's invariant into the input (cyclic time, synthetic corruptions, a permutation-invariant loss) rather than growing the model; mind explicit parameter and feature caps |
| **No twist: plain supervised, executed cleanly** | leak-free features, honest grouped validation, right-sized models; feature engineering and honest cross-validation beat architecture, and most winners are library-scale |

Two twists can apply at once (a scarce-label task over a fixed model);
name both and pull cards for both. A twist the list does not hold is a
finding for the harness: say so in the attempt notes.

After the twist: the task-type-playbooks skill gives the family for the
modality, the cv-protocol skill the validation that will not lie, and the
contest-economics skill when to ship it.
