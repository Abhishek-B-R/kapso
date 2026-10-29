# Ideation

Propose as a contestant plans a contest: what to ship first, what to try
next, what each idea should score and when.

Exploration axes. Status each one every iteration as active, saturated with
evidence, or deferred, and say which axis a proposal moves on:

1. algorithm family: annealing, beam or random search, tree search, random
   simulation, colony methods, exact or dynamic programming where the
   constraints allow (the heuristic-patterns skill is the catalogue)
2. state representation: what the search moves over, and what encoding
   makes a move cheap and a legality check free
3. neighbourhood and move design: small and large moves, feasibility kept
   or repaired, regret when the problem is tight
4. time allocation: between phases, between strategies, between search and
   final polish, all of it spent
5. multi-strategy by input condition: a different solution per input size
   or shape, precomputed answers where the inputs are fixed

- Every proposal states its family, its expected score against the baseline
  and the current best, and when it first reaches a strong score; an idea
  that cannot say what it would score is not ready.
- Beyond improving the ideas in the experiment summary, propose ideas that
  are not in it: diverse variations of algorithms and structures, crazy
  ones included. An idea is not dropped because a few implementations of
  it failed; a good idea implemented badly looks like a bad idea.
- When runtime allows, propose adding an algorithm to the best solution
  rather than replacing it; several annealers or strategies under one time
  budget often beat one.
- A proposal names the condition of the inputs under which it should lose.
