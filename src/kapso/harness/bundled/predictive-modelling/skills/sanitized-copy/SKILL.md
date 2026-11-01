---
name: sanitized-copy
description: "What the sanitized, read-only copy of a time-cut relational database holds (every table truncated at the test cutoff, the target and the columns it derives from physically absent, the test rows reduced to key and seed time, per-tick snapshots for the rolling regime, a marker that records what was done) and the script that builds one for a relational benchmark dataset. Use in setup, before anything reads the data: to verify the copy the task names, or to build one when the task provides none."
---
# The sanitized copy

The copy is the only database a candidate reads. Its contract, in terms of
any relational database:

- a forecasting or recommendation task: no row dated after the test cutoff
  in any table (the pristine data holds rows after it, from which future
  labels could be rebuilt); the training and validation task tables kept
  with their labels; the test table reduced to the entity id and the seed
  time (and the source id for a recommendation task);
- a post-cutoff-row task (autocomplete): the database keeps its rows after
  the cutoff, the target column is blanked there, and the columns the task
  names as the target's sources are dropped from the stored tables, so a
  direct file read sees no more than the library's masked view;
- the rolling regime: one snapshot per evaluation tick, each a database
  truncated at the tick, a training table of every label window closed by
  the tick with labels recomputed from the snapshot itself, a test table of
  that tick's rows, an empty schema-correct validation table (so a loader
  never regenerates one), and the rows' positions in the task's official
  test table, for whatever evaluation assembles per-tick predictions;
- every file a real copy, never a link into the source; the whole tree
  read-only; a `SANITIZED.json` marker naming the dataset, the task, the
  regime, the source and one report: per table its kept and pristine row
  counts, the columns removed, the rows blanked, the test table's columns,
  and under the rolling regime the snapshot and tick counts. Copy the
  report into the domain statement.

A copy the task provides is verified against this contract in setup; a
copy built by hand for any other database meets it the same way.

## The script, for a relational benchmark dataset

```
python3 $KAPSO_HARNESS_ROOT/skills/sanitized-copy/scripts/sanitize.py \
    --dataset <name> --task <name> --source <library cache> --out <copy> [--rolling]
```

It needs the relbench package (the task's library, not a harness
requirement) and a dataset and task the library registers; run it in a
fresh interpreter, since the library caches tables in memory. It opens
the dataset and the task from the source with both cache directories
bound to it (the library's own cache variable does not matter), builds
the contract above, and refuses an output directory that is not empty, a
source that is itself a sanitized copy, a source missing a task table, an
output inside the source, and a rolling build of a task with one
evaluation timestamp or of a recommendation task.

Read-only means the files cannot be replaced or edited by an ordinary
write; it is a guard against a slip, not a security boundary. The
leakage-scan skill and the verification session are what catch a read the
copy does not allow.
