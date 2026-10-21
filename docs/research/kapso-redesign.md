# Kapso redesign: positioning and interfaces

*Started 2026-10-21. The positioning is settled first; the interface and
architecture changes follow from it. Companion to
`docs/plans/kapso-plugin-mental-model.md` (the module map) and
`docs/plans/hn-launch/discourse-study-2026-10.md` (what engineers feel).*

## 1. One-liner (settled 2026-10-21)

> Turn coding-agent output into verified outcomes, not review debt: plug in the harness for your domain, set the goal, every step traced.

Why this one: it opens on the engineer's own pain (tokens burned, a pile of
diffs to review), names the outcome (verified, not claimed), and carries the
two product facts in the shortest form: the harness is pluggable for a
domain, and every step is on record. It does not name a category, which is
deliberate: "applied research", "auto-research", "iteration engine",
"software factory" and "long-running agents" were all tried and rejected.

## 2. TL;DR (draft 2, to iterate; replaces the README's "What is Kapso?")

Coding agents burn tokens and hand back diffs you have to review. Kapso runs
them differently. You plug in a harness for your domain and set a goal; it
works the goal until it is met, measuring every attempt with an evaluation
the agents cannot touch and keeping every step on record. What comes back is
a verified outcome: the branch that met the goal, the evaluation that proved
it, deployed as running software.

A harness teaches Kapso one kind of work: how to propose, build, measure,
judge and deploy there, and the tools it needs. Harnesses ship for ML
models, data pipelines, GPU kernels, algorithm contests and agents; write
your own for anything with an evaluation.

It learns from experience, and the lessons carry their receipts: one rule
per card, the condition it applies under, the measured effect from each run
that tested it, a reliability score with its rationale.

## 3. Tags (draft, to iterate)

Verified outcomes · Pluggable harnesses · Every step traced · Learns from runs

## 4. Rules for every public sentence

- Words out: "with a number", "judge" (say evaluation), "trust",
  "applied research", "iteration engine", "long-running agents",
  "self-improving", "autonomous", "software factory", "team of agents",
  "always-on", "AI and data systems".
- Every number travels with who ran it, on what evaluator, and when.
- Learning stays "knows more after every run; measurably better is the
  experiment still running" until the A/B says otherwise.
- The engineer stays in charge: their goal, their evaluation when they have
  one, their merge.

## 5. The product shape the one-liner implies

- **Engine**: the loop (propose, build on a branch, measure, continue from
  the best until the goal is met or the budget runs out), the isolated and
  versioned evaluation, the trace, deployment, learning.
- **Harness**: a plug-in package for one kind of work: the handler (scoring
  direction, stop semantics, task context), per-module instructions
  (propose, build, judge, deploy, the entrance's evaluation templates),
  extra tools, default budgets and gates. Shipped harnesses are today's
  benchmarks and examples; anyone can write one (trading, science). The
  trust boundaries stay in the engine; a harness never reaches the
  evaluation guard, the budgets, the inbox or the checkpoint.
- **Experience**: what the engine knows. Learned itself (the lesson bank,
  evidence-priced) or through others (the hosted knowledge base, imported
  repositories and papers), with provenance shown.

Interface sketch from the whiteboard (to be designed in §7):

```python
kapso = Kapso()
kapso.load_harness("predictive-modelling")      # or a path, or a git URL
kapso.load_experience("mine")                   # the bank; or "leeroopedia", a repo, findings
solution = kapso.build(goal, evaluation=...)    # evolve becomes build
software = kapso.deploy(solution)
experience = kapso.learn(solution)
```

## 6. Open items

- The TL;DR: iterate until it reads right, then replace the README section
  and the PyPI summary.
- The tags: four, in the one-liner's order.
- The entrance when there is no evaluation (the engine proposes one, the
  judge checks it is fair): keep the three-case design from
  `docs/plans/kapso-plugin-user-flow.md` §4.
- The harness contract and the `load_harness` / `load_experience` /
  `build` / `deploy` / `learn` interface: design next, after the story.

## 7. Interface redesign

To be written once the story is locked.
