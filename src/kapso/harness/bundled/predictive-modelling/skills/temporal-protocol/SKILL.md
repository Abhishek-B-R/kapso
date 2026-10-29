---
name: temporal-protocol
description: "The three temporal regimes of a time-cut prediction task (a frozen database, per-row seed time, a post-cutoff row with a blanked target), what each lets a row see, and the one load that silently cripples a rolling model while validation looks fine. Use when the task statement names a temporal cutoff, in setup to record the regime and in implementation and verification to apply it."
---
# Temporal protocol

A row with a seed time may use data stamped before that time; whether the
seed instant itself belongs to the past is the task's definition, and the
domain statement records it. The regimes differ in what the database
handed to the model contains.

## Frozen database

The database is truncated at the task's test cutoff; every test row, even
one dated after the cutoff, is answered from that frozen snapshot. This is
what a library's default loader does and what reference baselines do. When
every test seed time sits at the cutoff (span zero), the frozen and the
rolling regime coincide and nothing here needs deciding.

## Per-row seed time (rolling)

The database is full; each row is anchored at its own timestamp and may
use everything before it. Published entries on a task whose test rows roll
past the cutoff may have been set in this regime; the task statement says
which. An evaluation under it hands the program one snapshot per tick; how
it invokes the program, what the snapshot holds beyond the rule below, and
where each tick's predictions go are the task's contract, read there.
What the regime itself fixes: a snapshot holds only data dated before its
tick, and the training rows it offers are the label windows already
closed by the tick.

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
  pays; an earlier origin's expensive artifacts are reusable verbatim, so
  cache them in the shared artifact directory keyed by origin.
- Never look for other ticks' snapshots: each invocation legally sees its
  own, and reaching outside it is a finding.

## A post-cutoff row with a blanked target (autocomplete)

The row to predict is itself created after the cutoff, so the database
keeps its rows after the cutoff and the target column is blanked there,
together with the columns the target derives from. The loader must not
truncate (the untruncated load is the one this regime requires), and the
blanked columns are never reconstructed: a value recovered from a
correlated column is a leak, whatever its timestamp.

## In setup

Record in the domain statement which regime the task runs under, what the
seed instant counts as, the span of the test seed times past the cutoff,
and, for the rolling regime, the number of ticks and the snapshot's
contents as the task describes them.
