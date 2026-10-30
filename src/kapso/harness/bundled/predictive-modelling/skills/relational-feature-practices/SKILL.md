---
name: relational-feature-practices
description: "Eleven practices for relational and tabular prediction that measured positive when ablated on tasks of this shape, each stated as a thing to measure on the task at hand and keep only where its own numbers agree: within-group normalisation, capacity matched to the labelled rows, segment coverage, history-free signal for a dormant population, the noise-calibrated gate, the decorrelated ensemble, label replay at earlier cutoffs, the hosted-model text channel, task-adaptive fine-tuning, the metric's own statistic, and the label-determinism audit. Use when proposing or building features, choosing capacity, gating a change, building the final ensemble, or deciding what to do with text columns."
---
# Relational feature practices

Feature engineering has been the highest-value direction on tasks of this
shape. Representation work over the database (new joins across tables,
temporally-censored transforms, cohort-level priors, interaction and trend
encodings) has decided them more often than the model has, and the
recurring failure has been freezing the feature matrix once an early
champion emerged and swapping model mechanisms while never re-widening it.
Two standing leanings follow, guidance rather than constraints: consider
every table (an unread table is usually unexplored signal; when you set
one aside, record the measured reason in the feature history), and lean
features over architecture. Each practice below is a measurement to make,
not an assumption to carry. The procedures they rely on (the gate, the
folds, the reading by slice, the blend) are the cv-protocol and ensembling
skills'; this skill holds the evidence and cites them.

## 1. Normalise features within the competing set

Whenever several prediction rows share a natural grouping key (the same
seed timestamp, session, parent entity, auction or batch), so that the
rows are in effect scored against one another: beside each informative
raw feature add its within-group rank, percentile and z-score, and the gap
to the group's leading value. An absolute value cannot distinguish "strong
in a weak group" from "strong overall", and the label often encodes
exactly that relative standing. The gain has held across model families
(linear, shallow trees, boosted ensembles), which is what makes it the
first thing to measure rather than a one-off.

## 2. Match capacity to the labelled rows; make complexity earn its place

When labelled training rows number in the low thousands or fewer, score a
strongly regularised or plainly linear model against the richer ensemble
instead of assuming more capacity wins: with few rows the extra capacity
fits sample noise, and a compact linear design has beaten far larger
ensembles and hand-engineered blends on such tasks. Wide matrices and
stacked models are worth building; each added layer is kept only where it
measurably beats the simpler version. Read every such comparison by slice
as well as in aggregate (the cv-protocol skill): a change that looks flat
overall can move one slice by a large margin and another the opposite way.

## 3. Segment coverage: measure it before you model

Split the evaluation rows by how much pre-cutoff history the target entity
has (none, sparse, rich) and report per segment: its share of training,
validation and prediction-era origins; its label rate; your metric on it.
Two failures hide in the aggregate: a segment whose share grows from
validation to the prediction period makes validation overstate
history-derived features; and any feature that reaches the row through
the entity's own past events is null by construction for zero-history
entities, so a model can score well overall while coin-flipping that whole
segment. If a material segment scores near chance: build features that do
not route through the entity's own history (the entity's own attributes,
the attributes of the items or context in the row, cohort aggregates
through shared non-history keys such as device, location, category or
demographics, system-level activity at the origin); match the training
mix to the prediction-era mix with per-row weights, or fit a router plus
segment-specific models; and judge candidates on the segment-weighted
metric. Adopt each step only where the gated forward-fold test agrees.

## 4. When the population is dormant, ego-features go empty

Report the metric by entity-history recency and depth, binned on the
task's own time scale (terciles of the recency distribution are enough;
event counts none, a few, many). If most evaluation entities are long
inactive, features built solely from the entity's own past (counts,
recencies, rates) are near-empty exactly where the evaluation mass is.
Invest in signal that survives dormancy: as-of-cutoff aggregates over
related entities (the activity and outcomes of neighbours through foreign
keys), graph-derived scalars computed at the cutoff (degree,
co-participation counts, community statistics), attribute-cohort
baselines, and the content or text state of the entity's artefacts,
placed in the main model's feature set (a separate weak graph model
blended at the end is not a substitute for neighbourhood features the
strong model can split on). Go deeper than one hop: propagate the
label-generating activity itself through the relation graph, as-of-cutoff
counts and outcome rates of the one- and two-hop neighbourhood over the
same interaction table that defines the label, with quantiles taken
within the arrival batch, plus the row's arrival context (how many
prediction rows arrived together for the same origin and that batch's
aggregate reach). Where an entity-entity relation exists, a low-rank
factorisation of its adjacency and community-level empirical-Bayes
outcome rates are the history-free signals to measure first. Separately,
before finalising, compute pairwise prediction correlations among the
surviving candidates: two that score within noise of each other and
correlate weakly, by the campaign's own spread, are a blend waiting to
happen (practice 6, the ensembling skill); gate it like any change.

## 5. Calibrate every accept-or-ship gate to measured noise, never a round number

The procedure is the cv-protocol skill's: bootstrap the internal metric
with the correct clustering unit and set the acceptance bar from the
measured standard error. The evidence for it: a pre-picked bar fails two
ways at once. On a mature design the honest per-step gain is often a
fraction of such a bar, so every real improvement is rejected as a tie
and the search converges to re-shipping its incumbent; and when the bar
exceeds what the standard error can resolve, the gate is not strict but
impassable, and hours of genuine positive results are discarded. If two
of your own significance tests disagree, trust the one whose resampling
unit matches the data's correlation structure; do not pick the one that
supports rejecting. If a gate-selected weight or capacity lands on the
edge of its grid, the grid is wrong: extend it and re-select before
freezing.

## 6. Build an explicit ensemble candidate from the campaign's decorrelated finalists

Near the end of the budget, list every archived candidate across all
branches of the search, not only your own lineage, with its score and
pairwise prediction correlation. Finalists that sit within a couple of
clustered standard errors of the leader and correlate weakly, by the
campaign's own spread of pairwise correlations, are the blend's members;
the blend's form, its fitting and its out-of-fold requirement are the
ensembling skill's. The evidence: argmax selection among near-tied
decorrelated finalists discards the one improvement that is reliable in
expectation, and blending only within your own lineage captures almost
none of it, since siblings correlate highly and cross-branch finalists do
not. The ensemble is submitted as its own candidate: final selection only
ever sees candidates.

## 7. When labelled rows are scarce, replay the label query at earlier cutoffs

The training table's timestamps are usually a thin sample of the
timestamps at which the label is well defined. Regenerate training rows
at additional earlier cutoffs under exactly the same leakage discipline
(features strictly before the cutoff, labels from the window after it),
multiplying the labelled set several-fold; when rows are scarce this
expansion is usually the largest single gain available. Judge it on
forward-chaining folds it never saw, and keep a replayed row out of any
fold whose origin its label window closes after (the cv-protocol skill).
For groups that stay sparse after expansion, borrow strength rather than
abandoning them: hierarchical or empirical-Bayes shrinkage of group rates
toward the parent population, kept as first-class features. Never let a
stacker learn a sparse-slice weight from a validation set dominated by
the rich slice: a stacker that drives the sparse expert to zero is usually
miscalibrated on that slice, not proof the expert is worthless (calibrate
per slice, practice 5).

## 8. Text columns: measure an LLM-extracted feature block; a local encoder is not that measurement

When the task statement grants a hosted model API and the schema has text
columns:

- First action: a single-row live probe that round-trips one call through
  your schema parser. Build the pipeline only on a passed probe; a channel
  wired but never executed is the failure mode of this practice.
- Write the prompt as a domain-expert reviewer and ask for judgments
  (adequacy, ambition, difficulty, risk, coherence), not descriptions. Two
  rules: never ask for anything a join or a regex over the structured
  columns can recover (the model is a noisier copy of the database there;
  a facts-restating schema measures near chance with no incremental delta;
  audit the schema against the tables first); and pass the complete
  document plus the row's structured fields rendered as context, since the
  model's unique value is judging interactions between text and numbers.
  Window long documents into several complete calls; a truncated document
  measures the truncation. "Do not predict the label" means the recorded
  label; judgment dimensions are the point.
- Outputs need not be numeric: closed-vocabulary labels (joinable,
  group-by-able), normalised short phrases and one-sentence judgments
  (embed or cluster downstream), and micro-summaries are all valid
  targets. Prefer the most constrained modality that captures the signal;
  anchor numeric scales to the corpus so scores compare across documents;
  return an explicit insufficient-evidence marker instead of a fabricated
  midpoint.
- Before gating the block, regress each extracted dimension on the
  existing no-LLM feature matrix out of fold: a high R-squared means that
  dimension is a copy of features you already have; drop it or keep its
  residual. Treat the prompt and schema as a gated variable: run two or
  three variants through the same forward gates and keep the winner.
- Cache every response in the shared artifact directory keyed by model,
  prompt version and content hash, so the extraction is paid once per
  campaign and later candidates and re-runs read it for free. Log the
  rows covered: a channel that scored a sample is measured on the sample.
- When the corpus is large relative to the hosted throughput, serve a fast
  open instruct model locally as the extraction engine for full coverage
  and validate it against a hosted-scored panel sized so its agreement
  with the local scorer is measured above noise: keep the local scorer
  where the two agree; the panel is the quality gate, not a teacher.
- Primary wiring: a per-fold supervised head over the judgments (plus
  sentence embeddings) producing out-of-fold-complete train, validation
  and test prediction vectors, entered as its own decorrelated finalist
  for practice 6; its errors decorrelate from history-derived channels
  because it reads the documents while they read the past. Secondary:
  per-event marks aggregated at several horizons where a model consumes
  sequences. Attributes dissolved as extra columns in a large matrix are
  the failure mode: a gate cannot see a small orthogonal lift among
  thousands of columns.
- A rejected zero-shot block is evidence about that block, not about the
  text. Before concluding the text carries no signal, test a supervised
  text channel (a head on the frozen judgments or embeddings against the
  labels), or escalate to practice 9. Zero-shot rejection followed by
  supervised success is the usual course on document-heavy tasks.
- When the label aggregates future outcomes of linked documents, score
  each document at its own level and aggregate predictions over the
  entity's cutoff-visible forward roster (the linked documents already
  registered at the cutoff whose outcomes land in the window), rather than
  only attaching document scores as historical entity aggregates, which
  the entity's own outcome-rate features absorb.

## 9. When a frozen text channel pays but a large text gap remains, fine-tune an open model on the task

A frozen channel compresses each document into a bounded schema or
embedding and discards most of what the text says about the label.
Escalate to task-adaptive fine-tuning when all hold: the documents are
rich enough that an expert reading them could know things your features
do not (shown by a positive frozen channel, or by a rejected zero-shot
block on a document-heavy corpus; zero-shot failure does not clear the
text); the documents are long, or a published bar set by a fine-tuned
language model sits far above your best; the labelled rows, after
practice 7's replay, are enough that a forward-fold measurement can
resolve the gain a fine-tune must show; and a GPU is there. Method: LoRA
or QLoRA on a small open instruction model scoring the label directly,
preferring a domain-pretrained variant when one exists and checking the
hub for the current strong small models and encoders (the hf-model-fetch
skill, in setup). Serialise into its input both the row's text and its
relational context rendered as text (history counts, cohort rates,
neighbour outcomes) so the model can learn their interaction. Multiply
sample efficiency by distilling hosted-model rationales on
training-period rows whose outcomes are history, and fine-tune on
rationale-then-verdict. Validate on forward folds under the same leakage
and two-model discipline as everything else, and enter the fine-tuned
scorer as one more decorrelated family, gated against the channel it
escalates from.

## 10. Optimise the metric you are scored on; for MAE-family metrics that means medians

When the evaluation is an absolute-error metric, L2-trained means target
the wrong statistic: train with L1 or median-quantile objectives and
predict conditional medians end to end, including through any target
transform (a log transform preserves the median, not the mean, so it pairs
with L1; use it for heavy-tailed targets). For zero-inflated counts, model
the mixture (a zero-probability classifier and a positive-part
distribution) and take the mixture's median, not a product of means: when
the zero probability is at least one half the median is zero; otherwise it
is the positive part's quantile at (0.5 minus the zero probability) over
(1 minus the zero probability). Gate the zero component like any family.
Calibrate per slice on the metric's own scale. When the label is a ratio
of future binary events over a small roster, it lives on a lattice: the
MAE-optimal prediction is the median of the predicted outcome
distribution, snapped to the achievable lattice, and the snap is a free,
measurable gain.

## 11. Run a label-determinism audit before deep modelling

Some labels are partially determined at the cutoff: the database already
holds rows that fix the outcome (posted results, registrations,
reservations, schedules, completed transactions). Before building anything
deep, probe every pre-cutoff table as a direct label source with cheap
single-join tests (join to the label rows, aggregate, measure the
standalone score on a sample). Three checks come before any such feature
is kept: point-in-time availability (the row held that value at the
cutoff; a snapshot taken later can carry outcomes revised afterwards, and
only the rows' own timestamps say so), permitted-column provenance (the
column is not one the task removes or names as the target's source; under
the post-cutoff-row regime a value recovered from a correlated column is
the leak the temporal-protocol skill names), and target lineage (the
feature is not the label under another name). Signal that passes all
three is legal: the rules forbid post-cutoff reads, not reading the
cutoff state well. A published method family far above the field is a
reason to run this audit, not evidence that such a source exists. Wire
such sources as covered-rows-direct plus model-fallback, with coverage
counts and per-slice scores logged. Part of the audit is label lineage
across the database's task family: when the label is a function of
per-document outcomes that a sibling task predicts directly, a
sibling-grade per-document predictor applied over the label's
cutoff-visible roster is a hypothesis to measure, and the sibling's proven
design a starting point.
