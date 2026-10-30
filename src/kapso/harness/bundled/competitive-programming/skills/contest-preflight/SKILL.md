---
name: contest-preflight
description: "What a complete, self-contained task root for a leaderboard contest holds, so a solver never has to visit the contest's site: the problem, the organizers' starter and continuation prompts verbatim, the binding rules pinned beside the statement, the scoring formula, the data as it actually is on disk, the submission modality and format, the contest descriptor and the ledger. Use before the build, when a task arrives as a competition URL or an organizers' brief and no task root exists yet; in setup, to judge whether the root the build was given is complete."
---
# Preflight: from a brief to a task root

The task root is the one artifact everything downstream reads: the task
statement, the data directory beside it (`kapso_datasets/`), the
descriptor and the ledger. When the task arrives as a competition URL or
an organizers' starter prompt and no root exists, build it before the
build, from the actual files, not the page prose alone; the data directory
is pinned once the build starts, and setup changes nothing in it. A
local-scorer problem's root is the problem statement, the scorer, the seed
list and the baseline, as the scorer-cli skill says; this skill is for a
contest scored on a site.

## Scaffolding

Identify the competition the brief names; download its data with the
authenticated CLI into the data directory (a rules-acceptance error means
the account has not joined the competition: stop and say exactly that);
write the descriptor `kapso_datasets/contest.json` (`competition`, the
absolute path of the `ledger` the submissions are recorded in, and the
`procedure` that submits and records when one exists; the kaggle-cli skill
has the shapes). Treat the brief as organizer instruction, every line of
it, and quote it in the statement's prompt section; when the organizers
publish a starter prompt and continuation prompts (pages addressed to the
solver), find every one and quote each verbatim, in order; when a page
names another as binding, read that one and fold its constraints in.

## The hard boundary

The statement describes the task only. Nothing about how to solve it (no
solution, notebook, write-up, forum discussion or hint) enters the
statement. The dataset files are read-only truth: never modified, added
to or deleted.

## Fidelity

The statement is the sole task context the solver receives: complete
enough to execute the whole task from it alone, and concise (every line
earns its place). Quote the metric formula and the compute limit verbatim;
summarise the rest. Never invent a value: what the pages do not state is
written as not stated. Ground the data and submission sections in the real
files: names, columns, row counts, label ranges, what is not available
locally (a hidden test set scored only on the site).

## Which rules bind

The organizers say what binds: a rules document they publish as current
beats the competition's descriptive pages where the two disagree, and the
statement names the binding document and pins a copy beside itself, so
every session can read it. Every binding constraint reaches the solver
either quoted in the statement or in the pinned copy; nothing binding is
left on the site. The task's own published values (its submission limit
and window, its report requirements, its per-run cap, which binds the
scoring re-run too) are quoted as values, never as commands.

## The statement's sections, in order

1. A title and a one-line objective.
2. The problem: what is predicted, the setting, any provided starting
   point (a checkpoint, its architecture, what it was trained on); then
   the organizers' prompts, verbatim, when they published any.
3. The task rules: external data and models, a must-reuse rule, single
   model or single pass requirements, the compute and time limits, the
   submission quota with its unit and window, and the per-run cap, as
   values; the binding document's name and its pinned path.
4. The scoring: the exact metric and its aggregation, as a formula, with
   what each term is computed over, and the direction.
5. The data: every file and directory present, its role and shape; what
   is not local.
6. The submission: the modality first (code competition or file upload),
   then the exact file (name, columns, header, row order, id space) from
   the sample submission; every attachment the starter declares; the
   descriptor and the ledger by path; no CLI mechanics, which belong to
   the kaggle-cli skill.

End with a short note: the modality, the metric in one line, the values
not found on the pages.
