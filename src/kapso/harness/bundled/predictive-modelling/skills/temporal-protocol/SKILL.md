---
name: temporal-protocol
description: "The two temporal regimes of a time-cut prediction task (frozen database, per-row seed time), what a per-tick snapshot holds under the rolling regime, and the one call that silently cripples a rolling model. Use when the task statement names a temporal cutoff, in setup to record the regime and in implementation and verification to apply it."
---
# Temporal protocol

Both regimes forbid a row from seeing data stamped after its own seed time.
They differ in what the database handed to the model contains.

## Frozen database

The database is truncated at the task's test cutoff; every test row, even
one dated after the cutoff, is answered from that frozen snapshot. This is
what a library's default loader does and what reference baselines do. When
every test seed time sits at the cutoff (span zero), the two regimes
coincide and nothing here needs deciding.

## Per-row seed time (rolling)

The database is full; each row is anchored at its own timestamp and may use
everything strictly before it. Published entries on a task whose test rows
roll past the cutoff were set in this regime. An evaluation under it hands
the program one snapshot per tick (the task statement says how it invokes
the program and where each tick's predictions go), and each snapshot holds
only data dated at or before its tick: tables truncated at the tick; a
training table of every label window already closed by the tick, fully
labelled; a test table of that tick's rows, inputs only; a validation table
present but empty by design, so per-tick tuning splits come from the
training table.

- Do not re-truncate a snapshot. Loading the database "up to the test
  timestamp" clamps every tick back to the static cutoff and throws away the
  history between the cutoff and the tick, which on a rolling task is most of
  the evidence. Load the snapshot whole (the relbench-api skill names the
  argument) or read its tables directly.
- Your own measurements will not catch that mistake: validation ticks fall
  before the cutoff and lose nothing, while every test tick is stripped, so
  the crippled model looks its best on validation. If per-tick history stops
  growing at a fixed date, suspect this first.
- Later ticks see more history, since earlier windows' outcomes are closed
  results by then: recompute features per tick, and retrain per tick when it
  pays. Snapshots grow monotonically, so an earlier origin's expensive
  artifacts are reusable verbatim; cache them in the shared artifact
  directory keyed by origin.
- The debug mode must finish a tick in seconds (subsample origins and trees):
  one run covers every tick.
- Never look for other ticks' snapshots or their root: each invocation
  legally sees its own snapshot only, and reaching outside it is a finding.

## In setup

Record in the domain statement which regime the task runs under, the span of
the test seed times past the cutoff, and, for the rolling regime, the number
of ticks and the snapshot's contents in the words above.
