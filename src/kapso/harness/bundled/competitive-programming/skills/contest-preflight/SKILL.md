---
name: contest-preflight
description: "What a complete, self-contained contest statement holds, so a solver never has to visit the contest's site: the problem, the organizers' starter prompt verbatim, the binding rules, the scoring formula, the data as it actually is on disk, the submission modality and format. Use when a task arrives as a URL or an organizer's brief and no task root exists yet, or to judge whether a task root is complete."
---
# Preflight: from a brief to a task root

The task root is the one artifact everything downstream reads. When the
task arrives as a competition URL or an organizers' starter prompt and no
root exists, build it before anything else, and build it from the actual
files, not the page prose alone.

## Scaffolding

Identify the competition the brief names; download its data with the
authenticated CLI into the dataset directory (a rules-acceptance error
means the account has not joined the competition: stop and say exactly
that); record the competition's identity beside the data. Treat the brief
as organizer instruction, every line of it, and quote it in the
statement's starter-prompt section; when it names another page as
binding, read that page and fold its constraints in.

## The hard boundary

The statement describes the task only. Nothing about how to solve it (no
solution, notebook, write-up, forum discussion or hint) enters the
statement. The dataset files are read-only truth: never modified, added
to or deleted.

## Fidelity

The statement is the sole task context the solver receives: complete
enough to execute the whole task from it alone, and concise (around a
hundred and fifty lines; every line earns its place). Quote the metric
formula and the compute limit verbatim; summarise the rest. Never invent a
value: what the pages do not state is written as not stated. Ground the
data and submission sections in the real files: names, columns, row
counts, label ranges, what is not available locally (a hidden test set
scored only on the site).

## Where the binding rules win

The organizers' current rules file beats the competition pages where they
disagree, except for the values the task itself publishes (its own
submission limit, its own report requirements, its own per-run time cap),
which the statement quotes as binding values, never as commands. The
statement does not restate what the rules file covers (hardware, no
internet, no outside models, the fixed package list); it covers the task.

## The statement's sections, in order

1. A title and a one-line objective.
2. The problem: what is predicted, the setting, any provided starting
   point (a checkpoint, its architecture, what it was trained on); then
   the starter prompt, verbatim, when the organizers published one.
3. The task rules: external data and models, a must-reuse rule, single
   model or single pass requirements, the compute and time limits, the
   submission quota and the per-run cap as values.
4. The scoring: the exact metric and its aggregation, as a formula, with
   what each term is computed over.
5. The data: every file and directory present, its role and shape; what
   is not local.
6. The submission: the modality first (code competition or file upload),
   then the exact file (name, columns, header, row order, id space) from
   the sample submission; every attachment the starter declares; no CLI
   mechanics, which belong to the kaggle-cli skill.

End with a short note: the modality, the metric in one line, the values
not found on the pages.
