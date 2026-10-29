---
name: heuristic-patterns
description: "The algorithm families that win timed optimisation contests (simulated annealing, beam and random search, tree search, random simulation, colony methods, exact methods where they fit), how each is pushed further, how parameters and strategies are chosen by input condition, and the diversity rule. Use when proposing or improving a solution's algorithm."
---
# Heuristic patterns

## The toolbox

Mathematical programming and convex methods (linear, nonlinear, quadratic
and sequential quadratic programming, simplex and interior point, Newton,
L-BFGS, conjugate gradient, subgradient and proximal methods, Frank-Wolfe,
trust-region and augmented-Lagrangian methods, ADMM, cutting planes, column
generation, Benders decomposition, the ellipsoid method); search structures
(k-d trees, hashing for duplicate states); exact and combinatorial methods
(dynamic programming, branch and bound, delta updates, knapsack, set cover,
the Hungarian algorithm, min-cost flow, max-flow families, spanning trees);
metaheuristics (genetic algorithms, differential evolution, CMA-ES,
simulated annealing, tabu search, particle swarm, ant colony, firefly and
bat methods, nested metaheuristics); direct search (Nelder-Mead, Powell,
pattern search). The families below are the ones that have decided
contests.

## Simulated annealing

The best approach when a good first solution exists and improves by
incremental, local changes; it almost always beats a simple greedy or a
plain local search. Push it further on four fronts:

- the state representation: how the encoding limits the search space or
  the convergence; an encoding that makes a move cheap and a legality
  check free is worth more than a better schedule;
- the neighbourhood: a balance of small and large moves; every valid
  solution reachable; moves that keep feasibility while reaching new
  regions; in tight problems, keep the last few steps and a regret
  mechanism;
- the budget: avoid recomputation in legality checks and scoring (delta
  updates), so the same time explores five or ten times more states;
- the scheme: adaptive and multi-phase annealing, annealing on the
  hyperparameters, several annealers with different seeds, states or
  neighbourhoods under one time budget when the limit allows.

## Beam search, random search, tree search

Think about the beam width and the evaluation function; balance diversity
and quality in the beam; stop bad branches fast and control time so more
candidates are tried; hash states to avoid duplicates; Monte-Carlo tree
search when the problem is a sequence of decisions with a rollout to
evaluate them; and keep asking how the same time could visit several times
more valuable states.

## Random simulation

In non-deterministic problems, random simulations are among the best
approaches, especially when the constraints allow deep rollouts. Combine
creative strategies with the simulation for longer horizons rather than a
few greedy steps; balance a few-step greedy move against long-horizon
maximisation by the problem; the heuristic scoring function is what makes
it work (consider both the mean and the spread of the rollouts, and run
enough of them to estimate well); avoid recomputation and stop bad
rollouts early so more of them fit.

## Ant colony optimisation

A population method for constructing global plans, effective when the
value of a solution lives in dependencies between its legs that a local
move cannot see.

## Parameters and configuration

Dynamic parameters that change with the situation avoid overfitting a
schedule and the local-optimum trap; the balance between diversity and
quality is tuned while searching, not fixed in advance; a parameter that
lands on the edge of its grid means the grid is wrong.

## Conditional solution generation

Combine approaches when it pays (several annealings or a multi-phase
version; several beam variants by condition); generate different solutions
for different input conditions (sizes, shapes, densities); precompute
answers for fixed or low-variance inputs, and hard-code them when the task
allows; keep multi-strategy solutions but drop the strategies that only
waste runtime. Some algorithms improve constantly with use (annealing,
random search) and may start cold: combine them with an efficient method
for the start rather than discarding them.

## Diversity

Beyond the ideas in the experiment summary, try out-of-the-box ones and
diverse combinations and modifications; vary algorithms and structures;
never drop an idea over a few failed implementations.
