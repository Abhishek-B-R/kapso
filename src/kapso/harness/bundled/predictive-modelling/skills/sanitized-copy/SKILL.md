---
name: sanitized-copy
description: "Build the sanitized, read-only copy of a relational benchmark database for one task: tables truncated at the test cutoff, the target and the columns it derives from removed from the stored files, the test table reduced to entity and seed time; per-tick snapshots for the rolling regime; a marker that says what was done. Use before anything reads the data, when the task provides no sanitized copy; needs the relbench package the task's data reference names."
---
# Sanitize the cache

```
python3 $KAPSO_HARNESS_ROOT/skills/sanitized-copy/scripts/sanitize.py \
    --dataset <name> --task <name> --source <library cache> --out <copy>
```

The script needs the relational benchmark library the task's data
reference names (relbench); it is the task's library, not a harness
requirement. It opens the dataset and the task from the source cache with
both cache directories bound to it (the library's own cache variable does
not matter), and writes a copy whose files are real copies, never links
into the source:

- a forecasting or recommendation task: no row dated after the test cutoff
  in any table; the training and validation task tables kept with their
  labels; the test table reduced to the entity id and the seed time (and
  the source id for a recommendation task);
- an autocomplete task: the database keeps its rows after the cutoff (the
  test rows must be predictable); the target column is blanked after the
  cutoff, and the columns the task names as removed (the ones the target
  derives from) are dropped from the stored tables, so a direct file read
  sees no more than the library's masked view.

With `--rolling`, one snapshot per evaluation tick under the output
directory: tables truncated at the tick, a training table of every window
closed by the tick with labels recomputed from the snapshot itself, a test
table of that tick's rows, an empty schema-correct validation table, and
the rows' positions for the grader's assembly. The temporal-protocol skill
says when a task needs it.

The whole tree is made read-only and a `SANITIZED.json` marker records
the dataset, the task, the regime, the source and the report: every table
with its pristine and kept row counts, the columns removed, the rows
blanked, the test table's columns. Copy the report into the domain
statement. The script refuses an output directory that is not empty, a
source that is itself a sanitized copy, a source missing a task table, and
an output inside the source.

Read-only means the files cannot be replaced or edited by an ordinary
write; it is a guard against a slip, not a security boundary. The
leakage-scan skill and the verification session are what catch a read the
copy does not allow.
