---
name: relbench-api
description: "How to read a relational benchmark database and its task tables through the relbench library from a sanitized copy: binding the library to the copy, the loader's truncation argument per regime, the task-table masks, the private builders and the calls that probe for stripped labels, and the modelling stack the library ships with. Use when the task's data reference is a relbench dataset, in setup and in every implementation."
---
# The relbench API on a sanitized copy

The library reads its cache from the directory its cache variable names.
Bind it to the sanitized copy the task statement names, explicitly: the
evaluation sets the variable for your program's run, and in your own
shell you export it to the copy before you run anything; in code, the
registries let you construct the dataset and the task with `cache_dir`
pointing at the copy, which needs no variable at all. Never point the
variable or the argument anywhere else: a read from the library's own
cache is a read of the pristine files, which the leakage scan flags.
Open the dataset and the task with `download=False`: the copy is
complete for the task and read-only, and a download reaches for the
pristine files.

## Loading the database

`dataset.get_db(upto_test_timestamp=...)` is the regime's switch:

- `True` (the library's default) truncates at the dataset's test timestamp:
  the frozen regime. On a frozen copy the truncation changes nothing, so
  pass the default; `False` asks for rows the copy does not hold, and the
  scan reports it under this regime.
- `False` returns everything the copy holds. Under per-row seed time the
  copy handed to a tick is already the correct view, so load it whole;
  truncating it is the trap the temporal-protocol skill describes. Under
  the post-cutoff-row regime the copy keeps its later rows by design, and
  `False` is the required load.

Say in the attempt notes which one you passed and why; the scan reads the
regime from the domain statement and asks the same question.

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
