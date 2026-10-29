# Implementation

Build the chosen idea on the branch, score it on every seed, and leave the
evidence.

- Time awareness first: the time limit minus input and output minus a
  margin is the algorithm's budget; make the code time-aware (it stops
  itself, it does not hope); count the operations of every step exactly
  and in seconds for the largest inputs; distribute the budget among the
  steps; spend what is left.
- The cpp-performance skill's rules: fast input and output, compiler
  pragmas where they help, light random numbers, no allocation in loops,
  the fastest structure for every hot operation, caching and memoisation,
  a precompute step when the task allows one, within the time it gives.
- Understand the statement completely before coding: wrong answers come
  from a constraint read once; a solution handles every condition
  inherently.
- On a time-limit failure, climb the ladder in order: understand the
  complexity; a more efficient algorithm or structure; the bottlenecks,
  with caching, memoisation or precomputation; and only then relax the
  parameters, gently, to the highest value that fits. A good solution
  implemented badly is not pruned for it.
- Run the scorer-cli skill's procedure on every seed before finishing and
  write the results file it describes: score and runtime per seed, the
  build line, the commit. A finish without a scorer run over every seed is
  refused; a seed at zero is a finish with a known invalid solution, said
  in the notes.
- When the scores move in a way you cannot explain, ask the score-auditor
  with the results: it reads the scorer's output across seeds and names the
  category of cases where the solution loses.
- When runtime allows, add algorithms to the best solution rather than
  replacing it (the heuristic-patterns skill says how each family is
  pushed further); there is no limit on the solution's length.
