---
name: cpp-performance
description: "How a contest program spends its time limit: input and output, the margin, exact operation counts, compiler pragmas, light random numbers, no allocation in loops, caching and memoisation, the precompute step, and the time-limit ladder. Use when writing or speeding up the solution, and whenever a run exceeds the time limit."
---
# Performance under a time limit

## The budget

- The algorithm's time is the limit minus input and output minus a margin;
  a program that reads and writes large inputs spends real time on them,
  so budget them explicitly and keep a margin of a tenth or so of the
  limit, never less than the measured io time.
- Count operations exactly from the largest inputs the constraints allow
  and convert to seconds at the machine's measured rate (a simple
  operation per a few nanoseconds on the judge; measure, do not assume):
  round nothing down. The budget is a number of seconds per step, and the
  steps' budgets add up to the whole.
- Make the program time-aware: it reads the clock and stops itself before
  the limit, and it uses the time that remains; an unspent second is
  score left on the table.

## The code

- Fast input and output (buffered reads, no synchronised streams, manual
  parsing when the input is large).
- Compiler optimisation pragmas and the build line the task gives; the
  fastest operation and structure for every hot path (arrays over maps,
  integer over floating point where exact, bitsets where they fit).
- A light random generator (a xorshift, not the library's heavy engines)
  in the inner loop.
- No allocation inside loops: preallocate, reuse buffers, keep the working
  set small and contiguous.
- Caching, memoisation and precomputation for anything evaluated more
  than once; delta updates for scores and legality.
- A precompute step, when the task allows a separate one, generates
  tables the solution embeds; it runs within the time the task gives it,
  and the solution never depends on it running at judge time.

## When a run exceeds the limit

Climb the ladder in this order, and no step is skipped: understand the
complexity of every part; a more efficient algorithm or data structure;
the bottlenecks, with caching, memoisation or precomputation; and only
then the parameters, relaxed gently to the highest values that fit. A
good solution that timed out because it was implemented badly is fixed,
not pruned.
