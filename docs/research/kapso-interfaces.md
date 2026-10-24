# Kapso interfaces: harness, experience, build, deploy, learn

*Design draft 1, 2026-10-21. Companion to `kapso-redesign.md` (the story) and
`docs/plans/kapso-plugin-mental-model.md` (the current module map). Written
to the one-liner: plug in the harness for your domain, set the goal, every
step traced. Rule 7 applies: the new design lands directly, no shims.*

## 1. What the interface has to make true

1. A harness is a package for one kind of work; you plug one in, ours or
   yours, and the engine behaves as a specialist in that domain.
2. You set a goal; you may bring an evaluation, or the engine proposes one.
   Either way the evaluation is isolated from the builder and versioned.
3. What comes back is a verified outcome: the branch that met the goal, the
   evaluation that proved it, deployable as running software.
4. Every step is on record and readable afterwards.
5. The engine learns from experience, its own and others', and serves it
   with provenance.

Non-goals for this round: the inner loop's mechanics (the generic strategy,
the judge, the maintainer, budgets, the inbox stay as they are), hosting,
the live terminal UI.

## 2. Nouns and verbs

Three nouns: the **engine** (the loop, the guarded and versioned evaluation,
the trace, deployment, learning), a **harness** (what teaches the engine a
domain), **experience** (what the engine knows: learned itself or through
others). Three verbs: `build`, `deploy`, `learn`. Two loaders:
`load_harness`, `load_experience`.

```python
from kapso import Kapso, Budget

kapso = Kapso(config="kapso-config.yaml")              # optional; packaged config otherwise
kapso.load_harness("predictive-modelling")             # bundled name, a path, or a git URL
kapso.load_experience("mine")                          # the lesson bank
kapso.load_experience("leeroopedia")                   # hosted, learned through others
kapso.load_experience(repo="https://github.com/org/x") # imported into the knowledge graph

solution = kapso.build(
    "Raise the data-quality score of warehouse/orders_clean.parquet above 0.95 "
    "with row retention at or above 0.98; dq/ must not be modified.",
    evaluation="dq",                 # provided: protected and versioned; omit and the engine proposes one
    data="data",
    repo=".",
    output="../orders-dq-campaign",
    budget=Budget(minutes=60, iterations=10),
)
solution.branch, solution.score, solution.evaluation.version, solution.trace
software = kapso.deploy(solution, target="docker")
experience = kapso.learn(solution)                     # cards with receipts, banked
```

| Today | New | Note |
|---|---|---|
| `evolve(goal, eval_dir, data_dir, initial_repo, output_path, mode, coding_agent, …)` | `build(goal, evaluation, data, repo, output, budget, …)` | one verb, plain argument names |
| `mode` (GENERIC, MINIMAL, benchmark modes) | `load_harness(...)` | the harness carries the domain knobs; modes are retired (§7) |
| `Kapso(kg_index=…, bank=…)` | `load_experience(...)` | sources, not file paths |
| `research()`, `learn_knowledge()`, `index_kg()` | `load_experience(research=…)`, `load_experience(repo=…)`, internal indexing | experience learned through others; §4 |
| `learning.serving.enabled` | loading experience is the switch | no second flag |
| `SolutionResult` | `Solution` | the verified outcome, with `.evaluation` and `.trace` |
| CLI `evolve`, `research`, `index_kg`, `bank` | `build`, `experience`, `harness` | `deploy`, `learn`, `watch`, `inbox`, `doctor` stay |

## 3. The harness contract

*Superseded on 2026-10-23 by `harness-design.md`: a harness is instruction
pages, skills, delegates, tool servers and hooks, listed per module in
`harness.yaml`, with no handler, no prompts of the engine's phases and no
engine knobs. Section 7's "harness defaults" fall with it: the harness and
the engine config never share a key. The text below is kept as the record
of the first draft.*

A harness is a directory. Bundled ones live in the package; yours live in
your repository or in a git repository of their own.

```text
<harness>/
├── harness.yaml        identity, family, requirements, defaults
├── handler.py          the evaluation contract: a ProblemHandler subclass
├── prompts/
│   ├── entrance.md     how to propose an evaluation and a target in this domain
│   ├── propose.md      lenses, design axes, what to consult first
│   ├── build.md        implementation rules and environment
│   ├── judge.md        domain-specific validity checks (leakage, contracts)
│   └── deploy.md       what "running" means here (service, batch job, pipeline)
├── tools/              extra MCP gates, each with required env and guidance
├── evaluators/         evaluation templates the entrance can instantiate
└── README.md
```

`harness.yaml`:

```yaml
name: predictive-modelling
version: 1.0.0
family: predictive-modelling        # the bank's task family for scope and serving
description: Kaggle-style tabular, vision and text modelling from raw data to a scored submission
requires:                           # surfaced by doctor; never installed silently
  binaries: []
  env: []
  python: ["xgboost", "lightgbm"]
defaults:                           # the per-domain knobs the strategy reads today
  gates: {propose: [research, experiment_history, repo_memory, bank], build: [research, repo_memory, bank]}
  parent_policy: best
  node_expansion_value: 1
  timeouts: {propose_minutes: 15, build_minutes: 60}
  design_axes: [...]
  budget: {minutes: 120, iterations: 10}
  effort: xhigh
evaluation:
  fidelity: {fast: {fraction: 0.1}, full: {fraction: 1.0}}
  templates: [holdout-metric]        # names under evaluators/
deploy:
  targets: [local, docker, modal]
  interface: predict                 # or batch, pipeline
```

**What a harness may do.** Extend the probabilistic parts: the prompts of
every phase, extra tools, the handler's problem context and scoring
direction, fidelity profiles, evaluation templates, deployment hints,
default budgets and gates. It may ship Python modules (a sandbox, a
submission loop, a data cache) and the handler may use them.

**What a harness may not do.** Touch the engine's guards: the evaluation
fingerprint and its verification, the evaluator registry and transitions,
budgets as hard stops, the inbox, the checkpoint, the trace. It may not pin
models or credentials: the user's config names models; a harness may set
`effort` and timeouts as defaults only.

**Precedence.** Packaged defaults, then the harness defaults, then the user's
config file, then call arguments. Today's `modes[<mode>]` layer is replaced
by the harness layer, and a user config is a plain override layer, which
also removes the "a config copy's `defaults:` is ignored" trap.

**Loading.** `load_harness(ref)` resolves a bundled name, a local path, or a
git URL (cached under `~/.kapso/harnesses/<slug>@<rev>`). Loading validates
the schema, imports the handler, checks every named prompt and tool exists,
and records `{name, version, content_hash}`; the hash goes into the run
checkpoint (a resume with a changed harness is refused by name) and into the
trajectory manifest (a lesson knows which harness produced it). Without a
load, the `generic` harness is active, which is today's GENERIC mode.

**Shipped harnesses, promoted from what exists.**

| Harness | From | Carries |
|---|---|---|
| `generic` | mode GENERIC | the default |
| `predictive-modelling` | benchmarks/mle, examples/ml_model_development | MLE handler, data preparation, stage-aware context |
| `relational-prediction` | benchmarks/relbench | sanitized cache, task specs, leakage audit, lane GPU pinning |
| `algorithm-contest` | benchmarks/ale | Docker scorer, contest heuristics |
| `ai-olympiad` | benchmarks/ioai2026 | submission loop, kernel slots, preflight |
| `gpu-kernels` | examples/cuda_optimization | profiler judge, numerical tolerance |
| `torch-performance` | examples/pytorch_optimization | wall-clock and memory judge |
| `prompt-harness` | examples/prompt_engineering | prompt and decoding search |
| `agent-scaffold` | examples/agentic_scaffold | agents improving agents |
| `data-pipelines` | new, from the data-quality flow | check suites, retention rules, batch deploy |

The benchmark runners become thin entry points over their harness
(`expert-relbench` is `kapso build --harness relational-prediction ...` plus
the benchmark's own task selection and final scoring).

**Authoring.** `kapso harness new <name>` scaffolds the directory with the
generic prompts as a starting point; `kapso harness check <path>` loads it,
renders every prompt, runs the handler on a fixture and the evaluation
template on a sample, and reports; `kapso harness list` shows bundled and
cached ones.

## 4. Experience

One noun, two provenances, shown wherever it is served.

| Source | `load_experience(...)` | Provenance | Served through |
|---|---|---|---|
| my own runs | `"mine"` | measured by you | the bank gate, scope = the loaded harness's family |
| a team bank | `"team"` or a git URL | measured by your team | the same, after a pull |
| Leeroopedia | `"leeroopedia"` | reported by others, curated | the hosted gate |
| a repository or paper | `repo="…"`, `paper="…"` | reported by others, imported | the knowledge-graph gates, after ingestion |
| web research | `research="question"` | reported by others, fresh | as campaign context, and ingestible |

Rules: loading is the switch (no `serving.enabled`); the bank is pinned at
load for the whole run; the intro tells sessions what is loaded and with what
provenance; a harness may declare `experience: {serve: false}` in its
defaults for runs that must not be served (benchmarks under protocol).
Ingestion keeps its staging and its two containers; the `.index` file moves
under `~/.kapso/experience/` and is managed, not passed around.

`learn(solution)` returns an `Experience` handle (bank head, cards created
and updated, the report paths, `explain()`) and banks it under the harness's
family. The CLI: `kapso experience list | add <source> | share <git-url>`.

## 5. build

```python
build(
    goal: str | Brief,
    *,
    evaluation: str | None = None,   # a directory you own; None lets the engine propose one
    data: str | None = None,
    repo: str | None = None,         # path or git URL; None starts empty
    output: str | None = None,
    budget: Budget | None = None,    # minutes, iterations, dollars, finalization reserve
    resume: bool = False,
    on_status=None,
) -> Solution
```

**The goal.** A string, or a `Brief` (objective, measured_by, baseline,
target, rules, budget) which is also the `kapso-brief.md` file an engineer
edits; the CLI's `--goal-file` reads it. The entrance design in
`docs/plans/kapso-plugin-user-flow.md` §4 stands: an evaluation present is
protected; a criterion without an evaluation gets a proposed protocol from
the harness's templates; nothing at all gets candidate criteria with a
recommendation.

**The evaluation, three states, all visible in the trace.** *Provided*:
fingerprinted, verified per candidate, tampering throws the candidate out.
*Proposed*: built by the first node from the brief's protocol, checked for
fairness by the judge, then registered and protected like a provided one.
*Versioned*: the maintainer registers each version; a change request with
evidence may be accepted as a new version, after which every earlier result
is re-measured; no score crosses a version boundary.

**The outcome.** `Solution` carries `branch`, `score`, `succeeded`,
`evaluation` (version id, provenance, log path), `trace` (the campaign
directory), `explain()`, `diff()`. It is what `deploy` and `learn` take.

**The record.** Everything under `<output>/.kapso/`: the status file (from
setup on), the checkpoint, the experiment history, the evaluation archive
with evaluator versions, one branch per attempt with its verdict and log,
tool-call counts per node, the inbox and launch records, the serving record
and pull log. `kapso watch` reads it live; a new `kapso trace <campaign>`
renders it afterwards: the tree, each node's verdict and evaluation, the
evaluation versions, what was consulted, what was spent.

## 6. deploy and learn

`deploy(solution, target="auto" | "local" | "docker" | "modal" | "bentoml" |
"langgraph", env=None) -> Software` is unchanged in behaviour; the harness's
`prompts/deploy.md` and `deploy.interface` tell the adapter what running
means in that domain. `learn(solution, *, exam=True, push=None) ->
Experience` is unchanged in behaviour and banks under the harness family.

## 7. The config file after this

Keep: `inference`, `preflight`, `gates`, `deployment`, `coding_agent`,
`feedback_generator`, `learner`, `learning` (minus `serving.enabled`), and
the platform `defaults` (budget heartbeat, retry, inbox, `models.embedding`).
Remove: `modes`. The domain knobs the strategy reads today (`ideation_gates`,
`implementation_gates`, `parent_policy`, `node_expansion_value`,
`expansion_lane_env`, timeouts, `design_axes`, `ideation_ensemble`,
`ideation_lens_planner`, `session_env_defaults`, `env_strip`) move to
`harness.yaml` defaults, overridable in the user file under a `harness:`
key. MINIMAL becomes a config choice (knowledge off), not a harness.

## 8. Order of work

Each step lands with its tests and docs, suite green, no compatibility
layer kept.

1. `build` with `Brief`, `Budget` and `Solution`; `evolve` renamed in the
   facade, the CLI and the docs.
2. The harness package: schema, loader, validation, fingerprint; `generic`
   promoted from GENERIC; `kapso harness list | new | check`.
3. Benchmarks and examples promoted to harnesses one at a time; modes
   retired; runners rewired.
4. Experience: `load_experience`, the provenance intro, `research` and
   `learn_knowledge` folded in, the managed index, `kapso experience`.
5. `kapso trace`, `kapso doctor --json`, the registry liveness filter.

## 9. Open questions

1. Harness granularity: task family (as drafted) or finer, such as one per
   dataset family inside RelBench?
2. May a harness ship default models at all? Drafted as no: effort and
   timeouts only.
3. Experience scope: does a lesson learned under one harness ever serve
   another? Drafted as no, with an explicit `scope` to share.
4. Is `Brief` the goal object the API should expose, or a CLI-only file?
5. `research` as an experience source only, or also a standalone verb?
6. Harness distribution: git URLs with a local cache now; a marketplace
   later, in the plugin's shape.
7. The benchmark runners: keep their names as entry points, or fold them
   into `kapso build --harness`?
8. What `kapso trace` renders beyond `watch --tree`, and whether it also
   exports (JSON, a static page).
