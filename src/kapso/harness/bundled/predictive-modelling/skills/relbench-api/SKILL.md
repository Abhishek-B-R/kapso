---
name: relbench-api
description: "How to read a relational benchmark database and its task tables through the relbench library from a sanitized copy: the loader's truncation argument, the task-table masks, the private builders and the calls that probe for stripped labels, and the modelling stack the library ships with. Use when the task's data reference is a relbench dataset, in setup and in every implementation."
---
# The relbench API on a sanitized copy

The library reads its cache from the directory its cache variable names;
the prepared copy under `prepared/cache` is that directory for every
session. Open the dataset and the task with `download=False`: the copy is
complete for the task and read-only, and a download reaches for the
pristine files, which the leakage scan flags.

## Loading the database

`dataset.get_db(upto_test_timestamp=...)` decides the regime:

- `True` (the library's default) truncates at the dataset's test timestamp:
  the frozen-database regime;
- `False` returns everything the copy holds. Under the per-row seed-time
  regime the copy handed to a tick is already the correct view, so load it
  whole; truncating it is the trap the temporal-protocol skill describes.

Under the frozen regime the sanitized copy is already truncated, so the
argument changes nothing; say in the attempt notes which one you passed and
why, because the leakage scan reads the regime from the domain statement
and asks the same question.

## Task tables

`task.get_table(split)` returns the split with its input columns masked as
the evaluation expects: entity id, seed time, and for a recommendation task
the source id. Never pass `mask_input_cols=False` on the test split, never
read a table's `removed_cols`, never call `task.stats()` on the sanitized
copy, and never call a private builder (`_get_table`): each one probes for
labels the copy does not hold, and each is a finding. The training table
carries its labels; the validation table carries its labels for selection
and for the test-predicting model only (the two-model contract in the
guardrails).

## The modelling stack

`relbench[full]` brings pytorch-frame and torch-geometric with the library's
reference examples (a tabular model over a single table, a graph model over
the schema). They are starting points, not the method: on these tasks the
feature matrix over joined tables, fed to a boosted or linear model with
the relational-feature-practices skill applied, has decided more often than
the graph model. Prefer duckdb to pandas for the joins; project the columns
you need before materialising.
