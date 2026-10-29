# WP8: the harness ports

2026-10-29, v2 after the plan review (the same day). Owner: the redesign's
implementer. Branch `wp8-harness-ports` (off `redesign` at 5647528b, the
merge of WP9). Size: XL in the master, refined here to four to five days
of wall clock: the two harnesses and the runners first, then the four
reproduction arms in parallel on frozen harness versions; the hours table
at the end tracks it. The port mapping is `docs/research/harness-ports.md`;
the order of work and the done-when lines are
`docs/plans/initial-harnesses-plan.md` (P1 to P5); the semantic test is
S3 of `docs/plans/semantic-production-tests.md`. The package was parked
until the owner said go; the owner's go is the full-path timeline agreed
on 2026-10-28. The decisions this version takes that the owner may want to
revisit are listed under Review, first.

## Scope

Two bundled harnesses under `src/kapso/harness/bundled/`, loaded by name:
`predictive-modelling`, written from RelBench and then MLE-bench, and
`competitive-programming`, written from ALE-bench and then IOAI. Each is a
complete tree in the package's own grammar: pages, skills with their
scripts, a delegate, hooks, a requirements file; `kapso harness list` names
them; `check` is green with no warning. The four benchmark runners become
task material plus `build()` with the harness plus final scoring: the
handlers' problem-context prose retires into the pages and skills, and the
grader, the caches and the task's facts stay with the runner, every
retiring line placed or listed as dropped. The knowledge each benchmark
holds is onboarded where the design puts it: the RelBench bank served by
reference, the MLE graph's workflows as a skill, ALE's prose as a skill,
and the IOAI book, backed up and passed for provenance, converted to a
bank in the card grammar once the grammar admits reported evidence. The
cross-checks of the plan's P5 run before the full arms: the abstraction
scan as a gate test, the task swaps as short arms, and S3's author test on
`pipeline-dbt` again after the ports' guide fixes. One non-regression arm
per benchmark on the frozen harness versions, read against the recorded
populations preregistered below, is archived and recorded here; S3 joins
the semantic suite with its report.

**Not in scope.** New leaderboard results or campaigns across tasks (one
task per benchmark). Learning from these runs or re-learning the RelBench
bank (the learn verb is WP3's, exercised by S6). Publishing the IOAI bank
or any entry whose licence is unknown: the provenance table gives the
owner the decision, and nothing of the book is pushed anywhere by this
package. A deployment module on either harness: WP5's bundled targets
cover deployment, and the port mapping's `predict-endpoint` row is dropped
(a user's own harness may add one). The organizers' trace export of the
IOAI contest, which lives on the `worktree-ioai-2025` branch and not here.
The docs' navigation and catalogue (WP10): this package writes the bundled
README, each harness's README, and the sentences the existing pages need.
The release (WP11). The live UI (by decision).

## Interface

### What this package exposes

**Two bundled names.** `kapso build --harness predictive-modelling`,
`kapso.load_harness("competitive-programming")`, the brief's `Harness`
line, `kapso harness check|export <name>`; `kapso harness list` prints both
under `bundled` with what each needs on this machine. The names resolve
through WP2's `parse_reference` as they are: a directory under the
package's `bundled/` holding a manifest.

**The trees.**

```text
predictive-modelling/  (0.3.2)              competitive-programming/  (0.3.1)
├── harness.yaml                            ├── harness.yaml
├── requirements.txt  (the scripts' own)    ├── (no environment file: the hooks are stdlib)
├── instructions/  guardrails setup         ├── instructions/  guardrails setup
│   ideation implementation                 │   ideation implementation
│   verification feedback learning          │   verification feedback learning
├── skills/  (twelve)                       ├── skills/  (thirteen; six shared with the other)
│   cv-protocol  eda-discipline             │   contest-economics  contest-preflight
│   ensembling  hf-model-fetch              │   cpp-performance  cv-protocol
│   leakage-scan (scripts/scan.py)          │   eda-discipline  ensembling
│   living-documents                        │   heuristic-patterns  hf-model-fetch
│   relational-feature-practices (eleven)   │   kaggle-cli  olympiad-playbook
│   relbench-api (tensor frames folded in)  │   scorer-cli  tabular-modeling
│   sanitized-copy (scripts/sanitize.py)    │   task-type-playbooks
│   tabular-modeling  task-type-playbooks   ├── agents/ score-auditor
│   temporal-protocol                       │           submission-auditor
├── agents/ leakage-auditor                 └── hooks/ require-scorer-run
└── hooks/ protect-prepared  deny-web-fetch            deny-shell-submit
           deny-web                                    require-insurance
```

No server on either harness: the Kaggle session-pool ticket office stays
the runner's path-invoked CLI (below). The page budget (forty lines) is the
binding constraint on the skill count: a skill that cannot earn a sentence
on its module's page is folded into another. Both harnesses start at
`0.1.0` with the first benchmark and go to `0.2.0` with the second; every
later edit bumps the version; the versions the arms run on are pinned in
this plan before the arms launch.

**What the scripts need.** `requirements.txt` lists what the harness's own
scripts need on every task (pandas, numpy, pyarrow). The sanitizer needs
the relational benchmark library the task's data reference names; the
skill says so, and the library is not a harness requirement, so a build on
a flat-table task is not refused for a library it never uses.

**The runners.** Each keeps its line and its task material and launches
the facade with the full mapping of today's flags:

```text
python -m benchmarks.relbench.runner -s rel-trial -t study-outcome [-i N] [--workspace DIR] [--resume] [--time-budget-hours H] [--harness REF] [--experience REFS] [--coding-agent CLI] [--rebuild-cache]
python -m benchmarks.mle.runner --competition spooky-author-identification [-i N] [--workspace DIR] [--resume] [--harness REF] [--experience REFS] [--coding-agent CLI]
python -m benchmarks.ale.runner --problem ahc008 [-i N] [--workspace DIR] [--resume] [--harness REF] [--experience REFS] [--coding-agent CLI]
python -m benchmarks.ioai2026.runner --root RUN_ROOT --hours H [--iterations N] [--resume] [--node-expansion K] [--harness REF] [--experience REFS] [--coding-agent CLI]
```

| Today | On `build()` |
|---|---|
| `-i` / `--iterations` | `Budget.experiments` |
| `--workspace` / `--root` | `output=` (the campaign directory) |
| `--resume` | `resume=True` (the checkpoint's fingerprint checked by the engine) |
| `--time-budget-hours`, `--hours` | `Budget.minutes`, with the reserve from the override file |
| the seeded trivial baseline (`generic_baseline/main.py`) | `repo=` (the maintainer's calibration needs a runnable candidate) |
| `--target-val`, `--knowledge-file` | deleted; the no-stop rule becomes the config key below |
| `--no-kg` | deleted with the knowledge graph (`task-type-playbooks` carries it) |
| `--coding-agent` | `coding_agent=` |
| the handler's problem context | the `Brief` and the task's data directory (the preservation list below) |
| `--harness`, `--experience` | `load_harness`, `load_experience`; the default harness is the benchmark's bundled one |

`--harness` takes any reference, so the task swaps need no runner edit for
the harness; the runner edits each swap does need are pre-listed in change
17. The `benchmark:` block of each override file keeps the runner's own
keys (WP4); the engine never reads it; the literals the handlers carried
(`RUN_COUNTS`, the concurrency cap, the runtime limits, the timeout tiers,
the output caps, the lite problems' contestant counts, the session-pool
sizes) move into that block, read at the call site. The runners read no
environment variable; their imports sit at the top (they are the modules
that may import the heavy optional libraries); no try/except.

**What the Brief preserves.** A `Brief` carries the whole task statement
in its objective, never clipped; the runner writes it from the task's
facts, and nothing in it is standing guidance (that is the harness's).
Per benchmark, the objective holds:

- RelBench: the task definition with the label-generating code, the label
  statistics, the schema with keys, time columns and relationships, the
  timestamp semantics and regime (frozen database or per-row seed time,
  with the per-tick invocation contract when rolling), the prediction
  contract (shapes, order, dtypes, the two-model rule, the files and
  where), the sanitized copy's absolute path and the starter kit's
  helpers, the shared artifact directory's path, the compute, the
  retraction command, the reproduced champion's location and validation
  score when one is seeded (the `Baseline` field), the published entries
  (`Target`), and the task rules (`Rules`: never a published solution to
  this task; external data only under a zero-leakage argument; what hosted
  model API is granted, if any; the library traps that are the task's own).
- MLE: the competition's description and data layout, the submission
  schema and sample, the held-out protocol (a stratified ten percent of
  training held back and never trained on, its score the search's signal),
  the debug and full contract with the runtime limits, the forbidden
  packages, the compute.
- ALE: the statement with examples and constraints, the scorer's
  invocation in the task root, the case sets, the aggregation (the average
  over the public evaluations), the time limit, the baseline.
- IOAI: the organizer's prompt and the preflight's statement, the
  modality, the permitted resources and the organizers' rules
  (`RULES.md`'s content, as task rules), the account and competition
  identity, the quota, the absolute deadline, the submission procedure the
  task root provides and the session-pool discipline.

The mixed builders (`_resources`, `_prediction_contract`, the iteration
protocol) are split: facts to the Brief, standing guidance to the pages
and skills, each line placed or listed as dropped in the change's commit.

**The evaluation directories.** The engine optimises one `score`, higher
is better (`GenericProblemHandler.maximize_scoring` is fixed `True`), so
every grader emits an oriented score and writes the raw metric and its
direction into `evaluation_output` beside it; the Brief's `Measured by`
says both; the runner's final report prints the raw metric. Each grader
reads a committed `task.json` beside it (dataset, task, metric, timeouts,
the sanitized copy's path, the rolling root), so the directory is
self-describing and fingerprintable and the RelBench grader's environment
contract is deleted. Per benchmark:

- RelBench: `data/generic_eval` as today, validation scoring over the
  sanitized copy, the per-tick cascade under the rolling regime.
- MLE: the candidate run under the runtime limit; the score is the
  candidate's own held-out score (the protocol the task states); the
  official grade on the private answers stays in the runner's final
  evaluation, once, on the delivered candidate.
- ALE: the official scorer (the `ale_bench` session's public evaluation,
  through Docker) over the public cases, averaged over the configured
  evaluation count; the private evaluation and the rank-to-rating
  computation stay in the runner.
- IOAI: the candidate's own recorded submission, read from the ledger the
  task's submission procedure writes: competition, kernel reference and
  version or file hash, submission id, timestamps, terminal status, score;
  pending, missing, rejected and out-of-window outcomes are distinct
  results (a pending score is an error, not a zero); the campaign's best
  belongs to the final report.

Every grader is tested against the contract of `docs/build/evaluation.mdx`
on a fixture: one command, the score on the last line, `result.json`,
non-zero on a malformed submission.

**The engine seams the runners need (interface requests).** Three handler
behaviours the benchmarks relied on have no equivalent on `build()`:

- the judge's stop vote (`honor_agent_stop`): an open-ended task runs to
  its budget; this becomes the config key
  `search_strategy.params.honor_agent_stop` (default `true`), read by the
  orchestrator, set `false` in the four override files; the handler
  attribute goes (WP4 owns the budget's end; WP1 the handler);
- the archive's labelling (`finalize_run_selection`): the generic feedback
  flow calls the engine's own `evaluation_archive.finalize_session_run`
  on the registered archive root it already knows, so a judged-invalid or
  integrity-flagged run is stamped `invalid` without a handler callback
  (WP1's file); the runner's final evaluation then selects among the
  archive's `final` runs and the `Solution`'s delivered candidate, and
  says when there is no candidate;
- the insured reserve (`deliverable_ready_reserve_seconds`): dropped with
  the IOAI handler; the engine's derived and bounded reserve (WP4)
  applies.

Each is one small edit in another package's file; the owner's go is asked
below, and the edits are made in this package once given, with the
handler attributes deleted (rule 7).

**The sanitized cache.** One implementation, the harness skill's
`scripts/sanitize.py` (standalone: arguments only, imports at the top, no
environment read, the autocomplete, recommendation and rolling shapes, a
non-empty output refused), run by the RelBench runner before launch into
the task's cache directory, reused across campaigns under a version
marker, and named in the Brief as an absolute read-only path. The setup
session does not build it (prepared resources are not integrity-verified
and the setup budget is minutes); it verifies the copy the statement
names (row counts against the cutoff, the test table's columns, the tree
read-only) and records the regime. A user's own relational task runs the
same script by hand or in setup when its data fits the budget.

**The leakage scan.** One rule table, in the skill's `scripts/scan.py`:
violations and advisory findings, regime-aware, a `--diff` mode on added
lines and a `--tree` mode over a candidate's files. The runner's final
audit calls the harness's script in tree mode over the delivered
candidate, so the handler's own table is deleted.

**The Kaggle session pool.** `kernel_slots.py` stays the runner's
path-invoked CLI: blocking acquisition is its contract, its pool sizes
live in the override file's `benchmark.session_budget.kernel_slots`, and
the runner passes the ledger's absolute path and the limits when it
stages the task root. The harness's `kaggle-cli` skill names the
discipline (claim a ticket before a push when the task names a pool) and
no number. The task root also provides a submission procedure the
runner writes: it records the immutable kernel version or file hash, the
response, the submission id and the score in the ledger the evaluator
reads; `deny-shell-submit` denies a raw `kaggle competitions submit` in
the shell and names that procedure; `require-insurance` and
`require-scorer-run` are conditional on what the task root provides (a
submission ledger; a seed list) and pass when it is absent, so neither
harness blocks the other's modality.

**The IOAI book as a bank.** The card grammar's evidence entries describe
what a campaign did with a claim (a learner run, a trajectory, a line
reference, a usage, an effect); a curated winner's solution has none of
these, only a public score at a source. The conversion therefore waits
for one honest extension of the grammar, requested from the learning
package's owner: a `reported` evidence source (`{url, author, licence,
score, protocol}`) with its own verdict `reported`, outside the executed
verdicts and the reliability promotion rules, so a converted card is born
`candidate`, serves with the provenance line "reported by others", and
never prices as our measurement. With it, `benchmarks/ioai2026/book_to_bank.py
--book DIR --provenance provenance.json --out DIR --verdicts ...` writes a
bank repository: `git init -b main`, `index.md`, `insights/index.md`,
`procedures/index.md`, `sightings.md`, `log.md`, one procedure card per
entry at `procedures/<uid>/card.md` with the solution files under
`procedures/<uid>/code/` (the payload path the retriever serves) and no
other markdown under `procedures/`, the format-v2 ledger with `type`,
`scope: domain`, `representation: code`, `evidence` (the reported entry),
`reliability.{state: candidate, rationale, plain}`, `log` of length one,
`probe`, `supersedes`, `contradicts`, `provenance.version: 1`; the body's
rule paragraph from `idea.md`. The test is `Bank(out).conformance_findings()
== []` plus a real load and card retrieval through the serving layer. Two
runs: the shareable bank (verdicts shippable-with-attribution and ours)
and the local-only bank (the rest), both at `~/banks/` and in the backup
bucket; a remote is the owner's call. For the IOAI arm the served bank
excludes the entry of the arm's own task (a decision below). The
provenance table gains the columns the review asked for (stated licence
or "unstated"; a use verdict and a publish verdict; third-party payloads
under `solution/`; our-reimplementation with the bright line "no copied
code, idea only, cited") in a second pass over the saved `provenance.json`.
Without the grammar extension, the fallback is (c): convert only the
entries we reproduced ourselves with a trajectory, and keep the rest as
the local book.

**The abstraction scan.** `benchmarks/harness_scan.py` (benchmark tooling,
not a core module): `scan(root, vocabulary) -> list[Finding]` over the
pages and the `SKILL.md` bodies outside fenced code (not scripts, not
`requirements.txt`, not the manifest); a finding is the file, the line and
the word. The vocabulary is dependency-free: RelBench's task and dataset
names from `task_specs.py`, ALE's problem lists moved into
`benchmarks/ale/problems.py` (no `ale_bench` import), MLE's competition
ids and IOAI's practice slugs as committed data files with a separate,
skipped-when-absent test that each still matches its registry, plus the
benchmark and library names (`relbench`, `mle-bench`, `ale-bench`, `ahc`,
`kaggle`, the library's environment variables) with a decision per word on
whether it is permitted domain vocabulary on a skill (the library's API
is) or a constant on a page (never). The number rule is "a number
adjacent to a quota, deadline, score or hardware word", with an allow-list
of statistical thresholds and version strings. The gate test
`tests/test_bundled_abstraction.py` runs unconditionally and fails on a
hit; a zero-hit result is evidence, not proof, and the Codex review of
each harness reads for the rest. `check` does not change (a decision in
DECISIONS); `docs/harnesses/write.mdx` says the scan exists and is ours.

**S3 in the suite.** `tests/semantic/suite.json` gains `s3` in a shape
`report.py` can render: the steps are the four arms, the scan and the
four swaps, with no host dimension (each a machine run), each with its
bars (the preregistered band or baseline, zero scan hits, zero harness
edits); `scripts/redesign/s3_ports.py --rederive` reads the archives and
renders `tests/semantic/reports/s3-1.md`; the author test stays its own
`author` entry and is re-run. The verdict is the runner's exit status as
for every test.

**The archive of an arm** (one file per run under
`scripts/redesign/runs/s3-<benchmark>-<n>/`, ignored by git, linked from
the record, copied to the artifacts bucket): the wheel's hash and the
branch commit, the harness name, version and hash, the resolved config
and the override file, the model routes, the machine kind and zone, the
task, data and evaluator identities, the bank's head and provenance, the
clocks and budgets, every candidate's commit and outputs, the raw scoring
and audit evidence, the submissions and versions, the serving and pull
logs, the session streams, the delegates' reports, the hook decisions,
the failures, the token and cost records, the baseline and band used.
`--rederive` recomputes the verdict from these without live state.

**The benchmark machine.** `scripts/redesign/benchmark_machine.sh` with
three kinds: `gpu` (a spot `a2-highgpu-1g`, one A100 40 GB), `gpu4` (a
spot `a2-highgpu-4g`, four A100 40 GB: the shape the RelBench lanes
recorded; within the project's 64 preemptible A100 quota) and `cpu` (an
`e2-standard-8` with Docker); the driver-bearing image; the wheel and the
benchmark tree at this commit in one venv with the benchmark's stack; the
secrets as the fresh machine pushes them, the Kaggle credential over ssh
stdin for the MLE and IOAI arms; the run archived; the machine deleted.
One machine per arm, fresh for the full arm (a smoke arm's state is not
inherited).

### What this package consumes

WP2's harness package (the bundled root, `check`, staging per host, the
task statement, verification, `KAPSO_HARNESS_ROOT`, `${PLUGIN_ROOT}`); WP3's
experience (a bank by path or git reference, the serving, the pull log);
WP4's config (override files, the reserved `benchmark:` block); WP1's
handles (`Brief`, `Budget`, `Solution`, `load_harness`, `build()`); WP6's
record (the trace that shows the harness at work); WP9's runner shape
(`fresh_machine.sh`, the author test driver, the suite and the report);
the learning package's card grammar (`src/kapso/learning/bank.py`), for
the one extension requested above.

## Ownership

Edits: `src/kapso/harness/bundled/` (the two trees and the README),
`benchmarks/` (the four runners, handlers, override files and READMEs;
`relbench/context.py`, `relbench/campaign.py`, `relbench/scoring.py`;
`relbench/sandbox.py` deleted into the skill's script and
`relbench/handler.py` into `scoring.py`; `ale/problems.py`; `harness_scan.py` and
the vocabulary files; `ioai2026/book_to_bank.py`, `ioai2026/PROVENANCE.md`;
`ioai2026/past_learning/` deleted), the tests under `tests/`
(`test_bundled_harnesses.py`, `test_bundled_hooks.py`,
`test_bundled_scripts.py`, `test_bundled_abstraction.py`,
`test_benchmark_runners.py`, the RelBench and IOAI tests,
`test_book_to_bank.py`; `test_past_learning_tasks.py` deleted),
`scripts/redesign/benchmark_machine.sh`, `benchmark_machine_install.sh`,
`s3_ports.py` and the README (WP9's directory, merged; noted here),
`tests/semantic/suite.json` (the `s3` entry, in WP9's shape),
`tests/semantic/reports/s3-*.md`, `tests/semantic/README.md` (the S3
section), `docs/harnesses/use.mdx`, `docs/harnesses/write.mdx` (the scan's
existence; the rules the author test re-run teaches),
`docs/reference/harness.mdx` (the bundled sentences),
`docs/plans/redesign/{MASTER,DECISIONS}.md`, this plan.

Interface requests, each one small edit in another package's file, made
here once the owner says go: `src/kapso/core/config.yaml` and
`src/kapso/execution/orchestrator.py` (the `honor_agent_stop` key; WP4,
WP1); `src/kapso/execution/search_strategies/generic/feedback_flow.py` (the
archive labelling without a handler callback; WP1);
`src/kapso/environment/handlers/base.py` (the three attributes deleted;
WP1); `src/kapso/learning/bank.py` and `bank_invariants.py` (the reported
evidence source and verdict; the learning package).

Reads, never edits: `src/kapso/harness/*.py` (WP2), `src/kapso/experience/`
(WP3), `src/kapso/kapso.py` and `handles.py` (WP1), `plugin/` (WP7),
`examples/harnesses/trading/` (the model; two hook programs copied with
the domain's own refusal reason).

## Changes

Each one a commit with its test; the suite green at each. The harnesses
are finished, reviewed and frozen before any full arm runs; the scan and
the swaps run before the arms; a post-arm fix that changes a harness
either re-runs the arm or the record names the version it ran on and why
that is still evidence.

1. **MASTER's rows and this plan.** WP9's row says merged by pull request
   #165; WP8's row says in progress with the ownership corrected to
   `src/kapso/harness/bundled/` and `benchmarks/`; the decisions below in
   DECISIONS; the plan review's findings answered under Review.
2. **The bundled root under test** (done: `tests/test_bundled_harnesses.py`):
   every directory under the bundled root passes `check` with zero
   failures and zero warnings at the packaged page budget, resolves by its
   bare name, and `kapso harness list` prints it under `bundled`.
3. **`predictive-modelling` 0.1.0, the pages, from RelBench** (drafted):
   the seven pages from `context.py`'s notes and `EVALUATION_PROTOCOL.md`,
   each under forty lines; the task's numbers in the task statement; the
   data-access rules that are task rules (the integrity rule, external
   data, the hosted-API grant, the library traps) left to the Brief, the
   domain-general ones on guardrails; the rolling regime's semantics and
   trap on the skill, the per-tick invocation contract left to the
   statement.
4. **Its skills, delegate and hooks** (drafted): `sanitized-copy` with the
   standalone `scripts/sanitize.py` (run on the local pristine cache for
   `rel-trial/study-outcome`: tables truncated, the test table reduced to
   entity and seed time, the tree read-only, a second run refused),
   `temporal-protocol`, `relational-feature-practices` (the eleven
   practices, the credential and budget lines of practice 8 rewritten as
   "when the task grants a hosted model API"), `relbench-api` (the tensor
   frame material folded in: no `torch-frame` skill, there is no written
   material for one), `living-documents` (the shared artifact directory
   named by the task statement, not by variable), `leakage-scan` with
   `scripts/scan.py` (violations and advisory findings, regime-aware,
   diff and tree modes), `cv-protocol`; `agents/leakage-auditor.md`;
   `hooks/protect-prepared` and `hooks/deny-web-fetch` with the domain's
   refusal reason; `requirements.txt` without the benchmark library.
   Tests (done): both hooks on both hosts' event shapes, allow and deny;
   the scan with one hit per rule, advisory alone passing, the regime
   switch, line numbers through context lines, removed lines not read.
5. **MLE-bench into the harness, 0.2.0.** The pages' additions (setup:
   profile the data, search the hub for candidate models and datasets in
   setup, record task type, metric, splits, data size and compute in the
   domain statement; ideation and implementation: the three stages as a
   pacing rule by the budget progress the evaluation output's budget
   notes report, the stratified subsample first, the hard-coded stage
   knob, epoch times printed, heavy ensembles last; feedback: stage-aware
   scoring), the skills `task-type-playbooks` (every workflow, concept and
   code example of `kg_data.json` reviewed with a disposition per node:
   named example datasets replaced by the task's inputs, validation advice
   that contradicts the guardrails dropped, arbitrary thresholds dropped,
   the tip sheet's "avoid cross-validation" dropped; the list under
   Review), `hf-model-fetch` (prose: how to search the hub for the task
   type and what to record; the handler's fetch was a model's web search,
   not a script), `ensembling`, `tabular-modeling`, `eda-discipline` (the
   EDA block at the start and the error-analysis block at the end,
   per-fold prints, the prediction distribution, feature importances as a
   leakage probe), and the installed-API traps from `_resources` on
   `tabular-modeling`. The page budget decides what folds.
6. **The independent review of `predictive-modelling` 0.2.0** (Codex
   `gpt-6-astra`, xhigh, read-only) against the demo harnesses' rubric
   (domain-general, abstracted, the benchmark's bias in one place) with
   the checklist "every line of the retiring prose is placed or listed as
   dropped", then the revision and the version bump; the abstraction scan
   run on it; recorded under Review.
7. **`competitive-programming` 0.1.0 from ALE-bench.** Pages (guardrails:
   the official scorer is the score, the time limit is the task's, a
   failing seed fails; setup: read the task root the statement names
   (statement, scorer, cases, baseline; the runner writes it); ideation:
   algorithm family, state representation, neighbourhood and move design,
   time allocation, multi-strategy by input condition, every proposal
   with an expected score and a first-strong-score time; implementation:
   the efficiency rules, the time-limit ladder (complexity first,
   bottlenecks, then parameters at the highest that fits), the io-time
   budgeting, the precompute pattern with its cap, "do not prune a good
   idea over a few failed implementations"; verification: the scorer on
   every seed, the time limit, the baseline; feedback: score and runtime
   against the baseline, which family is saturated; learning: scope by
   problem and algorithm family), the skills `heuristic-patterns` (the
   handler's domain knowledge, sectioned), `cpp-performance` (the pragma
   and data-structure tips, the precompute pattern), `scorer-cli` (how to
   run the scorer the task root provides and read its output),
   `agents/score-auditor.md`, `hooks/require-scorer-run` (Stop on
   implementation: no finish without a scorer run over every seed of the
   task root's seed list; passes when the root has no list). Tests: the
   hook on both hosts' shapes with and without the list and the results;
   `check` green.
8. **IOAI into the harness, 0.2.0**, from a source-to-destination inventory
   written first (every section of `RULES.md`, `KAGGLE_CLI.md`,
   `preflight_spec.md`, `RUN_FINDINGS.md` I-1 to I-14 and the handler's
   prose placed as: a skill's mechanics, a page's rule, the Brief's task
   rule, the runner's configuration, or dropped as a historical incident;
   the contradiction between the CLI guide and the rules on tickets
   resolved before porting): guardrails additions (the statement's quota
   is the authority, the report docstring on every submission, the
   leaderboard as arbiter, the account's history as fair inspiration);
   setup: read the task root the runner's preflight wrote; implementation:
   the insurance submission, the time-allocation plan before the first
   kernel, confirm-gain discipline, the harvest before the end, the
   cross-lane board protocol (skip, steal, complement, ensemble) and the
   late-budget priority rule; verification: the kernel audit's rules and
   CV inflation against the public score; feedback: time to first strong
   score, critical-path velocity, confirmation overhead, the GPU ledger,
   the ceiling proof with the noise-floor argument; ideation: the axes
   (model family, data use, transduction on the unlabelled evaluation set,
   time allocation); learning: scope by the statement's twist and
   modality; the skills `kaggle-cli` (the CLI mechanics with the guide's
   examples generalised, no named competition or file), `contest-preflight`
   (what a complete statement holds, for a user's own task),
   `contest-economics`, `olympiad-playbook` (the ten twists and how to
   pull the served bank's cards for a twist; the scan is the test that it
   names no problem and no score); `agents/submission-auditor.md`;
   `hooks/deny-shell-submit`, `hooks/require-insurance` (conditional on
   the task root's ledger). Tests: both hooks on both hosts' shapes, with
   and without the ledger.
9. **The independent review of `competitive-programming` 0.2.0** and its
   revision; the scan run on it.
10. **The engine seams**, once the owner says go: the `honor_agent_stop`
    config key read by the orchestrator and set in the four override
    files; the archive labelling in the generic feedback flow through the
    engine's own `finalize_session_run`; the three handler attributes
    deleted. Tests: a stop vote under the key off does not end a campaign
    (the orchestrator's existing stop test extended); a judged-invalid run
    is stamped `invalid` in the archive without a handler.
11. **The RelBench runner on `build()`.** The Brief from the task spec
    (the preservation list), the per-task grader directory with
    `task.json` (the environment contract deleted), the oriented score,
    the sanitized copy built by the runner with the harness's script and
    reused by version marker, `--harness` defaulting to the bundled name,
    `--experience` as today, the full flag mapping; `RelBenchHandler`
    reduced to the runner's own scoring: the caches, `final_evaluate`
    (the archive's `final` runs and the delivered candidate; test once;
    the harness's scan in tree mode as the audit) and the no-candidate
    path; `get_problem_context`, `apply_bank_intro`, the notes, the axes,
    the audit table and `sandbox.py` deleted; `context.py` keeps the
    task-side builders split into facts; `campaign.py`'s invocation
    mapped flag by flag. The runner's own rules: no environment reads,
    imports at the top, the literals into the `benchmark:` block, the
    exception handling gone with the rewrite. Tests: the runner's solve
    path with the provider boundary mocked and the real facade (the roles,
    the deadlines, the reserve, the harness in the launch record, the
    evaluation directory's contract on a fixture, a lower-is-better task's
    oriented score sorting correctly, no candidate delivered).
    Done (2026-10-29): `scoring.py` replaces the handler class (the
    sanitized copy and the per-tick snapshots through the harness's
    script, reused under a marker of the task and the script's hash; the
    staged evaluation with `task.json`; the final report over the
    archive's finals with the winner's test metrics once, the harness's
    scan over its code and the build's delivery beside it);
    `context.py` builds the Brief from the facts, every schema column
    listed (rule 6); the champion seeding is deleted with the handler
    (`claims/` was retired to the bucket); `--initial-repo`, `--no-kg`,
    `--target-val` and `--knowledge-file` are gone; the starter kit and
    the baseline read the task from `kapso_evaluation/task.json` and the
    copy from the run's `RELBENCH_CACHE_DIR` (a tick's snapshot under the
    rolling regime); the pristine cache is the library's own
    (`get_relbench_cache_dir`); `campaign.py` is budget-bound only. The
    real-data test of the sanitizer found its report's row counts at zero
    (a `columns=[]` parquet read has no rows): the counts now come from
    the parquet metadata.
12. **The MLE runner on `build()`.** The grader directory per competition
    (the held-out score as the search signal; the official grade once in
    the runner's final evaluation), `data=` the prepared competition data,
    the handler's prose retired with the same rules; the budget progress
    the stage rule reads verified in the smoke arm (the evaluation
    output's budget notes), or raised to WP4/WP6 as a finding. Tests as
    for RelBench, with `mlebench` skipped when absent.
    Done (2026-10-29): `data/generic_eval/grader.py` runs the candidate
    (the debug mode as the gate, then the full mode), validates
    `final_submission.csv` with the competition's validator and reads the
    held-out `<score>`, oriented; the maintainer registers it (the
    override file enables the maintainer, as RelBench's does) and its
    calibration runs the seeded baseline, which writes the sample
    submission and reports the floor score of the override file's
    `benchmark.floor_scores`; `context.py` builds the Brief from the
    competition's published description, the prepared data's layout, the
    contract, the held-out protocol, the caps and the forbidden packages
    (the LLM cleaning of the description and the hub search are gone: the
    description rides verbatim, the harness's `hf-model-fetch` skill
    searches the hub in setup); the data stays by absolute path under the
    archive root, not as `data=` (the engine tracks `kapso_datasets/` in
    the workspace's git and copies it per session, which a dataset of
    gigabytes cannot bear: a decision in DECISIONS); the knowledge graph
    file and the handler are deleted; `benchmarks/common.py` holds what
    the runners share (the runtime file, the staged evaluation, the
    compute, a directory's layout). The stage rule's budget notes are
    left to the smoke arm (change 19).
13. **The ALE runner on `build()`.** The task root it writes (statement,
    the scorer wrapper over the `ale_bench` session, the seeds, the
    baseline) as `data=`, the grader over the public cases averaged over
    the configured count, the private evaluation and the rating in the
    runner's final evaluation in the benchmark's own units (final rank,
    rank percentage, performance), `maximize` derived from the problem's
    metadata rather than the lite dictionary, the prose retired. Tests as
    above; one real scorer invocation in the smoke arm.
    Done (2026-10-29): `data/generic_eval/grader.py` opens the
    benchmark's own session and judges `main.cpp` on the public cases,
    `fast` once and `full` over `benchmark.runs`, the mean total oriented
    and the floor for a submission with a failed case (the all-or-nothing
    rule, now the task's: in the Brief and the manifest, not the
    harness); its `--scores results/scores.json` mode is the candidates'
    scorer procedure, writing the per-seed file the harness's scorer-cli
    skill describes and the finish hook accepts; the task root is the
    public seed list (`kapso_datasets/seeds.txt`); the seeded baseline
    prints the example output and takes the floor, so the maintainer's
    calibration has a runnable candidate; `maximize` from the problem's
    `score_type`; the contestants from the standings' length; the lite
    roster in `problems.py` without the library; the private evaluation
    and the rating in the runner's final report in the contest's units.
    The runner's per-campaign session is gone: every grader run opens
    its own session (the resource limits of the library's session are
    not the campaign's budget), which the smoke arm times.
14. **The IOAI runner on `build()`.** The preflight stays and writes the
    task root (statement, `RULES.md`'s content as task rules, the
    submission procedure, the ledger path, the session-pool limits from
    the config), the Brief from it, the evaluator over the candidate's own
    recorded submission, `kernel_slots.py` as the CLI it is, the harvest
    with its deduplication and window kept, `run_final_eval` kept, the
    handler's prose retired, `knowledge_bank_dir` deleted from the config;
    `past_learning/` and its test deleted (superseded by `learn()`). Tests:
    `test_ioai2026_benchmark.py` moved to the new shape; the evaluator on
    a fixture ledger with pending, missing, rejected and scored entries;
    exact candidate-to-submission attribution.
    Done (2026-10-29): the runner stages a contest root beside the
    preflight's task (`task/contest_root/`: `contest.json` with the
    competition, the ledger's absolute path, the procedure, the metric's
    direction, the window start and the shared root; `submit.py`;
    `kernel_slots.py` with its limits; `RULES.md` pinned) and passes it as
    `data=`, so every session's `kapso_datasets/` carries the harness's
    conventions while the ledger and the ticket office's state stay in
    the shared root; `submit.py` submits through the CLI and records the
    entry with a token in the message and the kernel source's hash (or
    the file's), which is the attribution: the provided evaluation
    (`data/generic_eval/evaluate.py`, run by the sessions, no maintainer:
    a leaderboard has no calibration run) refreshes pending entries from
    the submissions list by token, matches the candidate's kernel or file
    by hash, and reports scored, pending (exit 12), rejected (13), out of
    window (14) and missing (11) as distinct outcomes, banking a newly
    scored entry in the shared `best_score.log` the ticket office reads;
    the preflight's `kaggle.json` gains the metric's direction; the Brief
    is the statement plus the campaign's facts, with the organizers'
    rules as a section of the objective (a Rules item cannot hold a
    bulleted document: the grammar would split it); the handler, the
    knowledge bank staging (`knowledge_bank_dir`), the CLI playbook
    staging and `past_learning/` with its tests are deleted; the harvest,
    `run_final_eval` and the audit are kept, the audit over every kernel
    folder found under the task.
15. **The IOAI book as a bank**, once the grammar extension lands (or the
    fallback): `book_to_bank.py`, the two banks, the second provenance
    pass with the added columns, `PROVENANCE.md` committed. Tests: the
    fixture book converts into a bank with `conformance_findings() == []`,
    loads through `load_experience` by path, and serves a card with its
    code payload; a corrupt provenance row raises; the local-only entry is
    absent from the shareable bank.
    Done (2026-10-29): the grammar extension landed in the learning
    package (`bank.py`: the `reported` verdict with its five source
    fields checked by conformance, `Card.reported_only`;
    `bank_invariants.py`: admission refuses it as a learner's;
    `retriever.py`: the evidence trail renders the source and every
    read of a reported-only card carries the "reported by others"
    line). `book_to_bank.py` writes the bank whole after every check (a
    corrupt row, an uncovered entry, an unknown tier or status, markdown
    in a payload refuse before a byte is written): the card's title from
    the book's router line, the rule from the idea page's lead
    paragraph, the task page as the situation, the idea's remainder and
    the payload as what to do, the provenance and verification as why,
    the confidence line in sync with `reliability.plain`; the status and
    best-known score from the idea page's own `status:`/`best:` lines
    (INDEX.md writes `?` where the page carries the review's verdict).
    The two banks: `~/banks/ioai-shareable` (47 cards: 43
    shippable-with-attribution + 4 ours; 46 code, 1 text — the survey)
    and `~/banks/ioai-local-only` (21 cards: 13 local-only + 8 excluded;
    19 code, 2 text — the theory rounds), both conformance-clean,
    loadable by path, their tarballs and checksums beside the book's
    backup and in the bucket. The second pass's table (`PROVENANCE.md`
    beside the runner, 162 rows: the stated licence, use, publish, the
    third-party payload, our files; the first pass's rules reading,
    open questions and appendix carried) reads shareable 102,
    local-only 60 over both sets. For the record: the body contract's
    floors are unmet on 19 cards' rules (the book's one-line leads) and
    9 cards' what-to-do (a one-paragraph idea), which the seeder's
    rewrite queue owns; no artifact-reference pattern hits; the loaded
    bank's intro line still says "measured by others" for a bank read
    by path — the card line says what its evidence is (DECISIONS).
16. **The abstraction scan**: `benchmarks/harness_scan.py`, the
    dependency-free vocabularies, the gate test that never skips, run over
    both harnesses; the hits fixed at the source (and at changes 6 and 9).
    Done (2026-10-29): `scan(root, vocabulary)` over `instructions/*.md`,
    `agents/*.md` and `skills/*/SKILL.md` outside fenced code, the
    harness's own names (skills, hooks, agents, files) blanked before a
    word is read; the vocabulary (146 words) from `task_specs.py`
    (datasets, size tiers, the override tasks), `ale/problems.py`,
    `mle/data/competitions.json` (82 ids, 22 lite) and
    `ioai2026/data/competitions.json` (the practice slug and the book's
    twelve mirrors), plus the named benchmarks and libraries with a
    decision each: `relbench` and its cache variable skill-only, the
    benchmark names never, the platforms (kaggle, atcoder) not words. The
    number rule: a number within two tokens of a quota, deadline, score or
    hardware word, an ordered list's marker skipped, version strings and
    statistical thresholds allowed. `tests/test_bundled_abstraction.py`
    runs over every bundled harness and pins the rules on a fixture;
    `tests/test_benchmark_vocabularies.py` checks each data file against
    its registry and skips when the registry is absent (the mlebench and
    relbench registries, ale_bench's roster, Kaggle's listing with the
    account's credentials). The first run found three hits: two sentences
    on predictive-modelling's pages naming the data library (rephrased to
    name the skill, 0.3.2) and one false positive (a list marker beside
    "submission", the rule fixed); competitive-programming was clean.
    `check` is unchanged (DECISIONS); `docs/harnesses/write.mdx` says the
    scan exists and is ours.
    Found on the way: the repository's `data/` ignore rule had left changes
    12–14's provided suites and baselines untracked (the tests passed only
    where they were written); `!benchmarks/*/data/` re-includes them,
    committed apart as 6f8bb2fb.
17. **The task swaps**, before the full arms, each a short arm with its
    exact task and the runner edit it is known to need, pre-listed so a
    runner edit is not mistaken for a harness finding: a second RelBench
    task with a maximised metric and span zero (`rel-event/user-attendance`
    in the frozen regime); `ahc011`, inside the lite list only because the
    runner's metadata source is the dictionary until change 13 derives it;
    a Kaggle tabular competition through the IOAI preflight with
    `--harness predictive-modelling` (runner edit: the organizers' rules are
    the IOAI task's, so the preflight takes a rules file per task); an
    IOAI 2025 practice competition through the IOAI runner. The bar is
    zero harness edits; a harness edit needed is a finding, fixed at the
    source, and the swap runs again. The two Kaggle swaps run in series on
    the one account with their quota cost recorded.
18. **The versions frozen.** Both harnesses' versions and hashes pinned
    here; the archive of every arm carries them.
    Done (2026-10-29), the tree as committed after change 16; the swaps
    and the arms run on these, and an edit to either harness after this
    point is a finding that re-pins the row:

    | Harness | Version | Hash (the whole directory) |
    |---|---|---|
    | `predictive-modelling` | 0.3.2 | `f38e6e5a43a6a8208d0f81989883a5611372da9aa53c0917d5856d8c6f76d1f3` |
    | `competitive-programming` | 0.3.1 | `1241d8cc1d821226584a7d6b95f2dfa5e6e514efed35da5f926b90b5e9256183` (re-pinned after the review's finding 9: 0.3.0, `f061926e76c62ff909893a02bd9218708c5965bac705d857be949ac40870dfd1`, ran the arms and the swaps and differs by one line of the kaggle-cli skill; DECISIONS, 2026-10-29) |
19. **The smoke arms, then the full arms**, one machine per arm, the band
    or baseline preregistered under Acceptance, the archives copied to the
    bucket: RelBench on `gpu4` (twelve hours, the four lanes the recorded
    campaigns used, cold); MLE on `gpu` (twenty-four hours, the recorded
    budget); ALE on `cpu`; IOAI on `gpu` (two hours, one lane, the
    recorded cold-start shape). Recorded: the score against its
    population, pages in the prompts, skills opened, the delegate's
    reports, the hooks fired, the cards served and cited, the cost and the
    hours, the token spend per provider.
    Amended 2026-10-29 by the owner (DECISIONS): the arms are quick runs
    in parallel on distinct logins — RelBench three hours on one A100
    with the four lanes, MLE three hours, ALE three hours, IOAI two
    hours — each record stating its budget beside the recorded one; the
    acceptance reads "at the arm's budget". Standing 2026-10-29 under
    Acceptance: three steps run, three running, one deferred.
20. **S3 in the suite** and the author test again: the `s3` entry and
    `s3_ports.py --rederive`, `tests/semantic/reports/s3-1.md`; the author
    test re-run on both hosts after the guide fixes with the driver's
    prompt excluding the bundled harnesses (its condition is the guide,
    the design and the trading example only), the guess log classified
    and recorded here. Done 2026-10-29 for the record (`d7fce019`, the
    `s3` entry and `s3_ports.py`; `reports/s3-1.md` re-derived with the
    deferred steps visible); the author test's re-run is owed after the
    arms.
21. **The docs' sentences.** `docs/harnesses/use.mdx` names the two bundled
    harnesses; `docs/harnesses/write.mdx` says the scan exists and what
    `check` leaves to it; the reference's bundled-name row shows a real
    name; each harness's README says what it ships and where it came from.
    Done 2026-10-29 (`9af07766`; the reference's row fixed after the
    review's finding 6).
22. **The pull-request review.** Cross-model, the findings fixed or
    answered here; the status rows. Done 2026-10-29 for the Claude half
    (twenty-two findings, the table under Review); the Codex half after
    the arms, whose machines hold the login.

## Tests

- **Syntactic.** `tests/test_bundled_harnesses.py` (check green at the
  packaged budget, listed, resolved), `tests/test_bundled_hooks.py` (every
  bundled hook on both hosts' event shapes, allow and deny; the manifest
  lists each where its rule applies), `tests/test_bundled_scripts.py` (the
  scan's rules, modes and regimes; the sanitizer's refusals and the
  boolean target coercion; the sanitizer's data boundary on the real
  task recorded from the local run, since a fixture dataset would need the
  library's registry), `tests/test_bundled_abstraction.py` (a planted task
  name, a planted number beside a quota word and a planted foreign path
  each one finding; the shipped trees clean; the test never skips),
  `tests/test_benchmark_runners.py` kept at the provider boundary (the real
  facade and orchestration plumbing: the roles, deadlines, reserve, the
  harness and evaluation directory in the launch record, the oriented
  score of a lower-is-better task, no candidate delivered, a resume's
  fingerprint), one evaluation-directory contract test per benchmark on a
  fixture, the IOAI evaluator's attribution cases, `tests/test_book_to_bank.py`
  (conformance clean, real load and card payload, corrupt input raises),
  the engine seams' two tests. Each pins a contract a user or a run would
  hit; none exercises a mock alone.
- **Proof run.** The four arms (change 19) with the archive contract
  above, the records in this plan: the score and its population, the
  harness at work in the trace, the cards served, the cost, the hours and
  the tokens.
- **Semantic hooks.** S3 complete: the four arms against their
  preregistered populations, the scan at zero hits, the four swaps at zero
  harness edits, the author test at zero structural guesses;
  `tests/semantic/reports/s3-1.md`.

## Acceptance

- `kapso harness list` names `predictive-modelling` and
  `competitive-programming`; `kapso harness check` on each reports zero
  failures and zero warnings (so every page is within the budget and
  every skill is named on its module's page) and the needs per module.
- No evaluator, dataset, goal, budget, credential, engine field, or choice
  of model or runner for Kapso's own agents in either harness (domain
  model names are allowed); the scan at zero hits on the frozen versions;
  the Codex reviews' scores recorded with the revisions that answered
  them; every line of the retiring prose placed or listed as dropped.
- Each benchmark runner launches `build()` with its harness and the record
  carries the harness; the handlers hold no domain prose; `sandbox.py`,
  the audit table, the knowledge-graph flag, `past_learning/` and the
  three handler attributes are gone; the runners read no environment
  variable and carry no try/except.
- The four arms recorded on the frozen versions, each against the
  population preregistered here:
  - RelBench `rel-trial/study-outcome`: the recorded population is the
    thirteen campaign lanes of 2026-07-31 to 08-14 (4×A100 boxes; eleven at
    a twelve-hour cap, two at six; test AUROC mean 0.775, sd 0.021, best
    0.821, the headline); the comparison population is the eleven
    twelve-hour lanes (mean 0.780, sd 0.020); the bar is a test AUROC at
    or above mean minus two standard deviations (0.741) with the number
    reported beside the band; at or above the best is noted, not required.
    The arm differs from the population in being cold (no seeded champion)
    and in the hosted-API grant (none: the project's OpenAI keys are
    exhausted), and the record says so.
  - MLE `spooky-author-identification`: the recorded population is the
    three runs of the official submission (Gemini-3-Pro-Preview, 24 h, one
    H100; log loss 0.247, 0.230, 0.284; silver, silver, bronze; medal
    thresholds gold 0.165, silver 0.270, bronze 0.294, median 0.419); the
    bar is a valid graded log loss at or below the bronze threshold at the
    same budget, reported beside the three, with the model routes named
    (today's, not the recorded model, which is no longer served).
  - ALE `ahc008`: the recorded result is one observation (Kapso 1221 against
    ALE Agent 1189, final ratings 1909 against 1879) with no launch record
    in the tree or any bucket; no band can be estimated from one
    observation; the bar is a rating at or above 1189 at the handler's
    recorded evaluation shape, reported beside 1221.
  - IOAI: the recorded practice task's competition (`timed-deps-12`) is no
    longer reachable, so the arm runs on the open `radar-ioai-2025` practice
    competition at the recorded cold-start shape (one lane, two hours) with
    the shareable bank served minus the task's own entry; the bar is a
    valid public score above the competition's median with zero shell
    submits and the pulled cards named; it establishes a baseline and the
    record says so.
  Every arm: pages in the prompts, skills staged, the delegate's reports,
  hooks mounted and, where the host reports them (Claude Code; Codex
  reports none, so the ledger's token on every submission is the hook's
  evidence there), fired; the cards served; the MLE port required no
  RelBench-shaped change to the harness, or the change was a page sentence
  and the guide gained the rule. The MLE in-loop score is the candidate's
  own hold-out number, which the verifier and the final private grade
  check and nothing in the loop computes (DECISIONS, 2026-10-29).
- The task swaps at zero harness edits after any fix, the runner edits
  listed; the Kaggle swap's quota cost recorded.
- **Standing, 2026-10-29 19:15Z** (the record `tests/semantic/reports/s3-1.md`,
  re-derived from `scripts/redesign/runs/s3-1/arms.json`, names each step
  as run or deferred; a required step deferred fails the run, which the
  merge rests on only as far as the steps below say):
  - `scan`: zero hits over both trees, live at re-derivation.
  - `swap-relbench` (`s3-relbench-swap-1`, rel-event/user-attendance, two
    hours): ran clean, zero harness edits, one experiment delivered, test
    MAE 0.2298 (val 0.2385); the leakage scan's one advisory finding kept.
  - `swap-kaggle` (`s3-kaggle-swap-1`, spooky-author-identification through
    the IOAI preflight and runner under predictive-modelling, two hours):
    ran clean, four ledger submissions, best public log loss 0.30161, two
    experiments, no shell submit.
  - `arm-ioai` (`s3-ioai-1`): the tooling established, the score a replay
    of the account's own earlier kernel, no candidate delivered; the
    step's bar now includes a delivered candidate and the arm fails it.
    The owner accepts this standing for the release (2026-10-29): the
    record keeps the failing bar and the release notes say what was and
    was not measured.
  - `swap-ale` (`s3-ale-swap-ahc011-1`): the campaign ended at 18:10Z; the
    final report (the private cases) was computing at the time of writing.
  - `arm-mle` (`s3-mle-4`, three hours on one A100, 19:48Z): a valid graded
    log loss of 0.2271 on the private answers, silver, at the recorded
    population's best (0.230, 0.247, 0.284) and under the bronze bar
    (0.294); two experiments, the delivered candidate the second; the
    first attempt died on the evaluator the setup session wrote.
  - `arm-ale` (`s3-ale-2`) and `arm-relbench` (`s3-relbench-3`): running,
    their earlier attempts having died on the two engine faults recorded
    under What the arms found (the RelBench arm twice: the stream split,
    then the run folder on a wheel that predated its fix); recorded as
    they land, before the merge.
  - `swap-ioai`: dropped from the release's required steps by the owner
    (2026-10-29: no Kaggle account will be set up; the open practice
    competitions need their rules accepted in a browser); the step
    definition stays for a later run.
  - The author test's re-run on both hosts: owed; it waits for the arms,
    since a fresh machine's copy of the Codex login would refresh the
    token the arms' machines hold.
- The author test at zero structural guesses on both hosts after the
  guide fixes, with the bundled harnesses excluded from its inputs.
- The IOAI bank: two verified copies of the backup, a verdict per entry
  with both the use and the publish reading, the shareable bank clean on
  conformance and loadable, the local-only bank apart, the arm's own task
  excluded, nothing of the book in the harness beyond the ten twists.
- The gate green at every merge; the docs checks; MASTER's row; the
  pull-request review answered.

## Risks

- **The recorded configurations are not reproducible as they were.** The
  RelBench lanes were warm (a champion seeded from earlier lanes) and the
  MLE model is gone; the bars above are preregistered against the
  recorded populations with the differences named. A miss outside the
  band reopens the port; a miss explained by a named difference is
  recorded as such and the owner decides.
- **Cost and the token gates.** Machine hours: RelBench 12 h plus a 2 h
  smoke on `gpu4` (spot, about $5 an hour), MLE 24 h plus 2 h on `gpu`,
  IOAI 2 h plus 1 h on `gpu`, ALE on `cpu`, four one-hour swaps, the
  author test's two arms on the fresh machine: about $200 of machines at
  spot prices. Tokens: every arm's ideation runs a Claude member and a
  Claude lens planner, so the Claude Max bucket (the token rule's TOKEN3,
  then token-5) is on the critical path of the overlapping arms; the
  Codex roles run on the device-auth session; the arms take the gate in
  the order RelBench, MLE, IOAI, ALE and a bucket over its weekly cap
  waits. The per-arm token estimate is read from the recorded lanes'
  cost records and written beside the hours before launch.
- **GPU availability and preemption.** Spot A100s in us-central1; the
  machine script tries the zones; a preemption deletes the machine, so
  the archive is fetched as the arm goes and the engine's checkpoint
  allows a resume on a new machine with the harness hash checked.
- **The Kaggle side.** One account, its session limits and the practice
  competition's quota bound the IOAI arm and the two Kaggle swaps, which
  run in series.
- **The grammar extension.** If the learning package's owner declines the
  reported evidence kind, the fallback converts only our own reproduced
  entries and the IOAI arm is served fewer cards; the record says which.
- **Time.** Four to five days; the hours table shows slippage as it
  happens.

## Review

### The plan review (cross-model, 2026-10-29)

`scripts/redesign/review.sh` over the brief at
`scripts/redesign/runs/wp8-plan-review/brief.md`: Codex `gpt-6-astra` at
xhigh (31 findings) and Claude `claude-opus-5` (39 findings), both
read-only, recorded as `codex.md` and `claude.md` beside the brief. Every
finding is answered below; the plan above is the revision. The owner's
decisions the review surfaced, taken here on the implementer's
recommendation and reversible on the owner's word:

1. **The reproduction bars** (Codex 1–4, 23–25; Claude 23–27): the recorded
   configurations are retrieved and preregistered under Acceptance; the
   RelBench arm runs at the recorded lane shape on a four-GPU box, cold;
   the MLE arm at the recorded budget with today's model routes; the ALE
   arm against the one recorded observation without a band; the IOAI arm
   on an open competition as a baseline.
2. **The IOAI book's representation** (Codex 19–20; Claude 16–17): a bank
   with a `reported` evidence kind requested from the learning package,
   the fallback being our own reproduced entries only.
3. **Prior-solution exposure** (Codex 21): the served bank excludes the
   arm's own task; the organizers' rules do not forbid the book, the
   licences decide what ships.
4. **The engine seams** (Codex 13; Claude 11–12): the oriented score needs
   no engine change; the stop key, the archive labelling and the dropped
   reserve are three small edits in WP1's and WP4's files, requested here.
5. **Spend**: about $200 of spot machines and the Claude Max bucket's
   weekly headroom, taken in the order above.

| # | Reviewer, severity | Finding | Answer |
|---|---|---|---|
| C1 | Codex P1 | The RelBench reproduction is not tied to the recorded experiment; "eight practices" is stale | The thirteen lane archives retrieved (`gs://leeroo-kapso-relbench-artifacts/runs/rel-trial--study-outcome/`): 4×A100, 12 h, the model routes, a seeded champion; the band preregistered under Acceptance; eleven practices everywhere |
| C2 | Codex P1 | MLE: a baseline replaces the done-when line; the published submission not consulted | The submission's three runs read (PR openai/mle-bench#107, the LFS reports): the bar is the bronze threshold at the recorded budget, the model difference named; `predict-endpoint` dropped with the deployment module (Scope); the "no RelBench-shaped change" clause restored |
| C3 | Codex P1 | "No ALE result" is false: ahc008 Kapso 1221 | Corrected: the bar is at or above 1189 beside 1221 in the benchmark's units; no launch record exists, said as such |
| C4 | Codex P1 | IOAI: no practice-task list; the bar lowered; mapped additions missing | The recorded competition is unreachable (403), so the arm is a baseline on `radar-ioai-2025` at the recorded cold-start shape; the ideation axes, the learning scope and the copied ML skills (`cv-protocol`, `ensembling`, `tabular-modeling` by directory copy, as the port mapping says) added to change 8 |
| C5 | Codex P2 | P5's timing and the `check` integration changed without a decision | The decision is in DECISIONS (2026-10-29); the scan runs at changes 6, 9 and 16; a swap runs again after its fix |
| C6 | Codex P1 | The sanitizer extraction is incomplete; two owners | One standalone script in the skill (written and run on the real task), the runner its one caller; the autocomplete, recommendation and rolling shapes covered |
| C7 | Codex P1 | The scan turns advisory evidence into rejection; regime; diff-only; two copies | Advisory and violation kept, regime-aware, a tree mode for the final audit, one table (the handler's deleted) |
| C8 | Codex P2 | The trading hooks are not both the same program | `deny-web-fetch` rewritten with the domain's reason; what it catches said in its docstring; the engine's web switch stays the boundary |
| C9 | Codex P1 | Only the tip sheet reviewed; named datasets in examples | Every node reviewed with a disposition list (change 5); the acceptance phrase corrected to Kapso's own agents |
| C10 | Codex P1 | Copying IOAI documents imports task rules and engine settings; I-14; contradictions | A source-to-destination inventory first (change 8); `RULES.md` to the Brief; the account limits to the config; incidents dropped or kept as evidence; the ticket contradiction resolved |
| C11 | Codex P1 | `kernel-slots` as a server has no path or authority contract | Not a server: the runner's CLI with the config's limits and an absolute ledger path |
| C12 | Codex P1 | The permitted submission route is undefined; hooks block the other modality | The task root's submission procedure writes the ledger; the hooks name it and are conditional on what the root provides |
| C13 | Codex P1 | `Brief` prose does not replace handler behaviour (direction, stop, selection, reserve) | The oriented score with the raw metric beside; the three seams requested (Interface) |
| C14 | Codex P1 | The Brief's contents too loosely specified | The preservation list per benchmark (Interface) |
| C15 | Codex P1 | MLE's search metric changes | The held-out score stays the search signal; the official grade once |
| C16 | Codex P2 | ALE's grader under-specified; a canned output tests parsing | The scorer wrapper, the count from the config, the private side runner-side; one real invocation in the smoke arm |
| C17 | Codex P1 | A lane's running best is not a candidate's evaluator | The candidate's own recorded submission with its outcomes (Interface) |
| C18 | Codex P1 | "follows" and "stay" conceal migration work | The flag mapping and the preservation list; the no-candidate path; the organizers' export is not on this branch (Scope) |
| C19 | Codex P1 | The bank changes the representation without an evidence policy | The `reported` evidence kind, cards born `candidate`, "reported by others"; the fallback |
| C20 | Codex P1 | "Every card field" does not make a loadable bank | The exact file set, the `code/` payload, the conformance test and a real load (Interface, change 15) |
| C21 | Codex P2 | The verdicts need more dimensions; back up before conversion | The second provenance pass's columns; the backup done first (two verified copies) |
| C22 | Codex P2 | The scan's heuristics incomplete and overbroad | The scope, the vocabularies, the number rule and allow-list; zero hits is evidence, not proof |
| C23 | Codex P1 | The hardware contradicts the launch configuration; budgets undefined | `gpu4` for RelBench; the budgets per arm and the cost line (Risks) |
| C24 | Codex P2 | The comparison rule needs preregistration; smoke arms inherit state | Preregistered populations; one fresh machine per arm |
| C25 | Codex P1 | Early reproductions do not validate the final harnesses | Reordered: harnesses frozen before the arms; the swaps before the full arms |
| C26 | Codex P2 | The archive contract is thin | The archive contract (Interface) |
| C27 | Codex P1 | None of the swaps is specified for the zero-edit bar | Exact tasks and the known runner edits pre-listed; the bar is zero harness edits |
| C28 | Codex P2 | The author test's inputs must stay controlled | The driver's exclusion of the bundled harnesses; fresh context; both hosts |
| C29 | Codex P1 | Copying implementations imports known violations; the hub fetch is not a script | The scripts rewritten (done for two); `hf-model-fetch` is prose; the runners' rules in change 11 |
| C30 | Codex P1 | `build()`-mocked tests weaken coverage | The provider boundary stays the mock; the missing tests added |
| C31 | Codex P2 | Ownership unreconciled; the status row | The scan is benchmark tooling; the interface requests listed; the RelBench bank inspected at change 11 (a real load); the row says in progress |
| L1 | Claude P1 | Two sanitizers, two rule tables | One each (C6, C7) |
| L2 | Claude P1 | The sanitized cache cannot be both `prepared/` and the runner's | The runner builds it with the harness's script; setup verifies |
| L3 | Claude P1 | `kernel-slots` blocking, the ledger's path, the limits' source | The CLI with the config's limits (C11) |
| L4 | Claude P1 | `requirements.txt` pins the benchmark library | Removed; the skill names the task's library |
| L5 | Claude P1 | ALE's task root has no owner; no scorer CLI exists | The runner writes it with a scorer wrapper; the hook reads the root's seed list |
| L6 | Claude P1 | MLE's in-loop grade would optimise against the private answers | The held-out score (C15) |
| L7 | Claude P1 | Items in a harness the design excludes | Each resolved: the rolling invocation contract to the statement, the task rules to the Brief, practice 8's credential line rewritten, the shared directory named by the statement, the quota file gone, the twists tested by the scan, the library skills named as the bias in the Codex rubric |
| L8 | Claude P2 | Domain knowledge left to die with the handlers | The TLE ladder, io budgeting, precompute, the EDA discipline, the API traps and the board protocol each given a home (changes 5, 7, 8) |
| L9 | Claude P2 | The plan contradicts itself on task rules | Split as the tree does (change 3) |
| L10 | Claude P3 | "Copied" is not what was built | Reworded: the same program shape with the domain's reason |
| L11 | Claude P1 | The metric's direction has no home | The oriented score (C13) |
| L12 | Claude P1 | Four handler behaviours lose their home | The three seams requested; the stop key in the override files |
| L13 | Claude P1 | Nothing exports the grader's environment variables | `task.json`; the contract deleted |
| L14 | Claude P2 | Flags the rewrite drops | The mapping table |
| L15 | Claude P2 | Dynamic per-round signals become static | The evaluation output's budget notes, verified in the smoke arm or raised |
| L16 | Claude P1 | The evidence block does not admit third-party evidence | The `reported` kind requested; the fallback |
| L17 | Claude P2 | The conversion's file list is short | The exact set and the conformance test |
| L18 | Claude P2 | The provenance reading misses four questions | The second pass's columns |
| L19 | Claude P1 | The scan's vocabulary needs imports the gate lacks | Dependency-free vocabularies; the gate never skips |
| L20 | Claude P1 | The fixed rules too lax and too blunt; scope unstated | The scope, the number rule, the allow-list, the names |
| L21 | Claude P2 | The foreign-path rule collides with the harness's content | The shared directory is a convention named by the statement; `results/` added; the library variables stay a hit on pages |
| L22 | clean | `check` stays domain-agnostic | `write.mdx` says the scan exists (change 21) |
| L23 | Claude P1 | The noise band has no source in the tree | The lane archives; preregistered |
| L24 | Claude P1 | The machine contradicts the recorded configurations | `gpu4`; one lane for IOAI, the recorded cold-start shape |
| L25 | Claude P2 | No cost per arm; the token gates missing | Risks |
| L26 | Claude P2 | The bars drift from the done-when lines | Restored under Acceptance |
| L27 | clean | The smoke-arm rule and the baseline reading | kept |
| L28 | Claude P1 | Each swap needs an edit the zero-edit bar will hit | The bar is zero harness edits; the runner edits pre-listed; `maximize` derived |
| L29 | Claude P2 | The author test exists; do not duplicate its entry | The `author` entry re-run; `s3` holds the arms, the scan and the swaps |
| L30 | Claude P2 | CLAUDE.md compliance of the rewritten runners | Listed per runner change |
| L31 | Claude P2 | Which tests earn their place | The provider boundary stays; the missing tests added (Tests) |
| L32 | Claude P3 | Paths that do not exist | The flat `tests/` layout; MASTER's ownership corrected |
| L33 | Claude P1 | The cross-checks run after the arms | Reordered (C25) |
| L34 | Claude P2 | Ownership: the scan, `bank.py`, `past_learning/` | Benchmark tooling; the request; deleted |
| L35 | Claude P2 | Three IOAI specifics | The task named; the runner's preflight stays, the page reads the root; `RULES.md` to the Brief; `knowledge_bank_dir` deleted |
| L36 | Claude P3 | The organizers' export is not on this branch | Out of scope (Scope) |
| L37 | Claude P3 | The page budget binds the skill count | Said (Interface) |
| L38 | Claude P3 | Eleven practices | Corrected |
| L39 | Claude P2 | The deployment module dropped silently | Said (Scope) |

What both reviews found clean is kept: the two-harness split and the
names, `--harness` on every runner with the swaps routed through the
existing runners, the book as a bank rather than an index, nothing of the
book pushed, the smoke-arm rule, one archive per run, the Codex review per
port before the arms, `check` domain-agnostic, the started tree's
discipline.

### Change 5: the MLE graph's dispositions (2026-10-29)

Every node of `benchmarks/mle/data/kg_data.json` (34 workflows, 8
concepts, 8 code examples, the tip sheet) was read and placed:

- **Kept, as conditional practice** in `task-type-playbooks`: the text
  classification families and their conditions, token classification, the
  tabular factors, the image factors and the ensemble-by-condition ladder,
  image-to-image, audio models and features, video and volumes, detection
  and segmentation; the tip sheet's early stopping, the modality with the
  most value, a model per modality, and the meta-model rule; the
  pretrained-weights-or-fail rule; augmentation after the split.
- **Kept, names only** in `references/hub-inventory.md`: the 24 hub
  inventories by task type (speech, time series, graphs, question
  answering, translation, summarisation, generation, ranking, similarity,
  pose, depth and the rest), with the caveat that an inventory ages and
  the hub is searched in setup.
- **Kept as reference code** under `references/code/` with the named
  example datasets replaced by the task's inputs (the IMDB load and its
  test split; the iris frame and its synthetic category).
- **Reworded**: "never cross-validate transformers" became resampling at
  the budget's price; "never simple averaging" became a fitted blend
  measured against the rank average (the relational practices blend by
  rank average); the fixed thresholds (five hundred thousand rows, two
  hundred features, fifty epochs, two hundred parameters, ten billion
  parameters, five gigabytes) became their conditions.
- **Dropped**: the tip sheet's "avoid out-of-fold validation, cross
  validation and heavy folding" (contradicts the guardrails and the
  cv-protocol skill); "never use LightGBM unless sparse" (arbitrary; the
  relational practices use it); "round probabilities toward certainty
  when the metric is a loss" (a confident wrong answer costs more than
  the gain; the ensembling skill says the opposite); "a model under two
  hundred parameters" (a typo-grade claim); the handler's "forbidden
  packages" line (task material, the Brief's); the stage percentages'
  sampling formula (the task's data size decides, said on the ideation
  page as a pacing rule).

### The harness reviews (changes 6 and 9, 2026-10-29)

`scripts/redesign/review.sh` over each harness at 0.2.0, read-only, both
reviewers: `scripts/redesign/runs/wp8-harness-review-pm/` (predictive-modelling:
Codex 28 findings, scores 2/3/2; Claude 33 findings, scores 3/4/4) and
`scripts/redesign/runs/wp8-harness-review-cp/` (competitive-programming:
Codex 23 findings, scores 2/3/2; Claude 18 findings, scores 4/4/4). The
revisions land in two commits each: the scripts, manifest and tests first,
the pages and skills second, with every finding answered in the table
below as it is closed.

**A repository trap the first commit hit.** `.gitignore` ignores every
directory named `*cache*/`, so the skill `sanitize-cache` was never tracked
although `check` and the gate test saw it on disk; it is renamed
`sanitized-copy` (a skill's name must not match an ignore pattern; the
gate test now also asserts every bundled file is tracked).

**Closed in the first commit (predictive-modelling):** the sanitizer binds
the task's cache directory as well as the dataset's (Codex 1), drops an
autocomplete task's removed columns from the stored tables (Codex 2),
copies files instead of hardlinking them (Codex 3), refuses a sanitized
source, reports every table and the removed columns in a `SANITIZED.json`
marker, and states its library prerequisite (Codex 27); the scan reports
every matching rule on a line, flags the loader's default under per-row
seed time, scans only the candidate's files in tree mode and fails loud on
a missing root or a file that is not text (Codex 5, 6); `protect-prepared`
is off setup (Codex 18); the zero-inflated median is the mixture's median
(Codex 16); the grader reads `task.json` beside itself and emits the
oriented score with the raw metric (Codex 13 of the plan review).

**Closed in the second commit (predictive-modelling 0.3.0): the pages and
the skills.** Every finding of both reviews by id (C = Codex, L = Claude),
with where it went:

| Id | Finding | Disposition |
|---|---|---|
| C1 | P1: `--source` does not bind the task-table cache | first commit: `open_from` replaces both registry cache directories; the three split files are required before anything is written |
| C2 | P1: an autocomplete task's removed columns stay in the stored tables | first commit: dropped from the stored tables and reported |
| C3 | P1: writable hardlinks into the pristine cache | first commit: real copies |
| C4 | P1: `relbench-api` assumes cache wiring the harness never supplies | the skill rewritten: bind explicitly, through the registries' `cache_dir` in code or the variable exported to the copy in the shell; the task statement names the copy and the evaluation binds the program's run |
| C5 | P1: the scanner's classification (the default load, a multiline call, first match wins) | first commit: every matching rule per line, `default-load` under per-row seed time; a call split over lines is named as the scan's limit, which is why verification also reads the code |
| C6 | P1: tree mode scans the staged tooling, passes a missing root, replaces bad bytes | first commit: the staged directories excluded, a missing root refused, a file that is not text refused; this commit adds virtual environments, installed packages and `.kapso` to the exclusions (L26) |
| C7 | P1: an explanatory sentence as the validity boundary; diff-only verification | the verification page rewritten: the whole candidate in tree mode, the auditor establishes the data flow over the diff and the inherited code, a safety sentence is evidence to assess, an unresolved check is named and never passed |
| C8 | P1: the full validation-chain safeguard lost | guardrails: the whole chain (features, selectors, calibrators, thresholds, early stopping, stackers, weights) never saw validation labels; `cv-protocol`: the official number is not a tuning target, a replayed row whose window closes after a fold's origin stays out of that fold; the auditor checks the chain |
| C9 | P1: label determinism legal from timestamps alone | practice 11: point-in-time availability, permitted-column provenance and target lineage before any such feature is kept; a published bar is a reason to audit, not evidence; the sibling method is a hypothesis |
| C10 | P2: the evaluator's invocation contract inside `temporal-protocol` | the regime fixes only what a snapshot holds and which training rows it offers; the invocation shape, the snapshot's further contents, where predictions go and the seed instant's inclusion are read from the task statement |
| C11 | P2: autocomplete missing from the protocol; the API skill contradicts the scan | the third regime (a post-cutoff row with a blanked target) in `temporal-protocol`; `relbench-api` gives the loader argument per regime and the scan's rule under each |
| C12 | P2: flat tables and users' own databases routed unconditionally | every page routes by situation ("when the data is a relational database with a temporal cutoff", "when that reference is a relbench dataset"); the sanitized copy is a contract with the script as its relbench implementation (L30); the scan's shape-neutral rules serve a flat task with the auditor as its gate (L17); a proposal names the practice it rests on, from any skill |
| C13 | P2: a budget fraction, dated bins, empirical cutoffs, campaign memories, "hours" | the stage follows from whether a full-data run fits the per-run time; recency binned on the task's time scale; "below 0.95" is "weakly, by the campaign's own spread"; the panel sized to its measured agreement; fine-tuning eligible when the forward folds can resolve its gain; the anecdotes and the simulation share removed; "when a fine-tune costs hours of the budget" |
| C14 | P2: the preferences spread and duplicated | one owner per policy: the gate, the folds and the slice reading in `cv-protocol`, the blend in `ensembling`, the evidence in `relational-feature-practices` citing both; the pages keep one-line consequences naming the skill; feedback weighs a wider matrix against the complexity it costs |
| C15 | P2: rank averaging prescribed where it changes the prediction's meaning; OOF for every blend | `ensembling`: the blend fits the metric (a mean on the metric's scale, a rank average for ranking metrics, a fitted meta-model measured against the plain combination); out-of-fold predictions required for a fitted blend only |
| C16 | P2: the MAE hurdle recipe | first commit: the mixture's median |
| C17 | P2: a drift diagnostic as an automatic scoring override | `cv-protocol`: examine completeness and shift, choose the windows that represent the test population, report both readings and say why when they disagree, rescore comparable candidates when the task's evaluator changes |
| C18 | P2: setup mounts the hook that refuses its own output | first commit: `protect-prepared` off setup |
| C19 | P2: the web rule and the model-fetch workflow disagree | setup downloads the pinned weights under `prepared/models/` and records each local path; implementation loads from it; the native web tools are denied by the new `deny-web` hook (L27); both hooks' reasons name the domain's rule |
| C20 | P2: hub access treated as permission to train on companion data | `hf-model-fetch`: the three permissions are separate questions; companion data screened for overlap, near-duplicates, the temporal cutoff and the licence; the size by measured memory; revisions pinned |
| C21 | P2: softened absolutes that remain absolutes | `task-type-playbooks`: TF-IDF earns a seat to measure, all layers by default, progressive resizing as the design to measure against several sizes, epochs decided by early stopping, dimensionality a measurement; `tabular-modeling`: the GPU histogram when the card is free; the pretrained-weight rule applies to the chosen backbone |
| C22 | P2: the reference code keeps task assumptions and contradicts its skill | the eight examples rewritten: the task's parameters named at the top (paths, class count, metric, the pinned model path, the split's caveat), early stopping on the validation loss in the transformer and tree examples, truncation delimited as the example's scope with the chunking rule cited, the vectoriser fitted on training rows only |
| C23 | P2: EDA suppresses warnings and overgeneralises the sample | `eda-discipline`: the noise off and the warnings on; the blocks grow when evidence warrants; the sample inside the split, group and time boundaries, stratified or range-spanning; install quietly |
| C24 | P2: living-document persistence assumed | `living-documents`: the directory the task statement names (`$KAPSO_SHARED_CACHE_DIR` in a Kapso campaign), created only when absent, every entry headed by its task and version, one append per entry |
| C25 | P2: useful retiring prose omitted | feedback: a provided baseline is reproduced under the current data before it is trusted; verification: the published bar converted to the metric's units; `cv-protocol` and the auditor: folds grouped by the repeated unit; ideation: re-tuning is an idea when the parent's measurement says tuning is where the gain is; practice 8: the rows covered are logged |
| C26 | P2: "every graph node placed" unsupported by the inventory | the pose weights beside the keypoint models, the speech recogniser and the 3D route placed; the test stubs, the fork-only section and the single-language forks dropped; the retrieval model labelled as retrieval; the plan's count corrected to 24 inventories |
| C27 | P2: the sanitizer advertises refusals and reporting it lacks | first commit: the marker, the sanitized-source refusal, every table reported, the prerequisite stated; this commit: one report shape and the rolling refusals (L23, L24, L25) |
| C28 | P3: the AST's input confused | the audio section: each checkpoint's processor turns the waveform into what the model consumes; the sampling rate and preprocessing from the checkpoint |
| L1 | P1: the shared artifact directory named six times, defined nowhere | `living-documents` names it (`$KAPSO_SHARED_CACHE_DIR` in a Kapso campaign, the directory the task statement names for shared artifacts); the guardrails read it from the task statement; the runner's brief names it (change 11) |
| L2 | P1: validation is one finite sample and not a tuning target | the first section of `cv-protocol` and the first guardrail |
| L3 | P2: a runner-private variable and directory in the scan's rules | the rule is written against the sanitizer's own naming: a sibling `(val|test)_NNN_` snapshot path or a `..` out of the snapshot |
| L4 | P2: an evaluator's assembly file in the sanitizer | kept, named for what it is: the rows' positions in the task's official test table, for whatever evaluation assembles per-tick predictions |
| L5 | P2: `relbench-api` asserts an environment fact, and the scan punishes the fix | in code the registries' `cache_dir` binds the copy with no variable at all; the variable is exported in the shell, which the scan does not read; an assignment of it in code stays the violation |
| L6 | P2: split leakage other than temporal | `cv-protocol` folds by the repeated unit; the auditor's list; setup profiles the unit and the domain statement records it |
| L7 | P2: the calibration gap to the public measurement | `cv-protocol`, feedback and implementation's reading |
| L8 | P3: early stopping on the loss; the pose names; the published bar's units | the playbook's standing rule; the inventory; verification step 3 and the domain statement's units |
| L9 | P2: implementation routes every task through the library | conditional on the data reference being a relbench dataset |
| L10 | P2: verification's checklist in one benchmark's vocabulary | step 1 conditional on a relational benchmark database; step 2, the auditor, is the gate for any other shape |
| L11 | P3: ideation restates the lean | one line naming the axis and citing the skill for the evidence |
| L12 | P3: the stage rule referenced, never stated | ideation: the stage follows from whether a full-data run fits the per-run time the task gives; setup records it |
| L13 | P3: recency bins assume a multi-year database | terciles of the recency distribution on the task's time scale |
| L14 | P2: trees on the CPU as an absolute | `tabular-modeling`: the networks get a contended card; otherwise measure the GPU histogram |
| L15 | P3: gradual unfreezing recommended over full fine-tuning | all layers by default; unfreezing worth measuring on a small set; full freezing not |
| L16 | P3: test fixtures and forks in the inventory | dropped |
| L17 | P2: the scan is a silent pass on a flat task | the shape-neutral rules (a test label read, a fit on train and test together, a validation fit as an advisory); the rest is the auditor's, and the skill says so |
| L18 | P2: autocomplete as a regime the protocol does not define | the third regime, named the same on the CLI and in the domain statement |
| L19 | P3: the validation-fit spelling; tree mode's description | the pattern widened to the common spellings; the skill names the exclusions |
| L20 | P3: the gate, the OOF rule and the blend rule in three places | one owner each; the practices skill cites them |
| L21 | P3: installation output forbidden, installation never prescribed | "install what is missing at the top of the program, quietly" |
| L22 | P2: the weights can never be loaded | setup downloads them under `prepared/models/`; implementation loads from the pinned path |
| L23 | P3: a `getattr` fallback that cannot fire | `task.num_eval_timestamps` |
| L24 | P3: three report shapes under one key | one shape: `tables` of `{rows, pristine_rows}`, `removed_columns`, `blanked`, `test_table`, `snapshots` |
| L25 | P3: a rolling recommendation task crashes | refused with the reason, before anything is written |
| L26 | P3: tree mode reads a vendored library | `.kapso`, the virtual environments, `site-packages` and `node_modules` excluded |
| L27 | P2: the stated web rule is not the enforced one | `hooks/deny-web` (PreToolUse on `WebSearch|WebFetch`) on implementation and verification |
| L28 | P3: the refusal names a convention this harness lacks | it names the shared artifact directory |
| L29 | P3: the delegate cites a page it is not staged with | "Check this list" |
| L30 | P2: a user's own database cannot use the script | the copy's contract in library-free terms; the script as its implementation for a relbench dataset; setup verifies or builds by the contract |
| L31 | P2: the Kaggle gap (L17, L9, L6, L7) | closed by those |
| L32 | P3: `kapso deploy` has nothing to run | the description says the domain stops at the candidate; deployment is the engine's bundled targets |
| L33 | P3: two provenance phrases a user cannot resolve | "from a hand-written knowledge graph of past competitions" |

**Closed in change 9 (competitive-programming 0.3.0).** Every finding of
both reviews by id (K = Codex, M = Claude), with where it went:

| Id | Finding | Disposition |
|---|---|---|
| K1 | P1: setup asks for work the engine forbids (running the scorer, downloading into the data directory) | setup learns the scorer from its help and documentation and reads the baseline's recorded scores; the preflight is a pre-build activity and in setup judges the root; the data directory is not changed in setup; prepared models go under `prepared/models/` |
| K2 | P1: a zero score as a universal invalidity contract | validity from the scorer's status and the task's rule for a failed case, on the guardrails, in `scorer-cli`, in the score-auditor and on the verification page; the all-or-nothing rule belongs to the task statement (the ALE runner's Brief, change 13) |
| K3 | P1: a user's own competition has no permitted submission route | the descriptor convention (`kapso_datasets/contest.json`: `competition`, `ledger`, `procedure`); the shell denial fires only where a procedure is named; without one the command submits and the session records the entry in the shape `kaggle-cli` gives; setup checks the procedure runs |
| K4 | P1: corrupt hook inputs fail open | explicit shape checks block with a reason; a file that is not JSON fails loud, and hook.json's launcher line (`\|\| exit 2`) turns that into the hosts' blocking exit; a test runs the launcher on a corrupt file |
| K5 | P2: the gates' evidence is shallow | finite numbers (no booleans), a non-negative spread and runtime, a status from the scorer's set, a build line, a positive run count, the solution named and unchanged since the file was written; ledger entries for this competition with a submission id; the verifier remains the gate |
| K6 | P2: `stop_hook_active` ignored | honoured by both Stop hooks; every reason says how to finish an attempt that cannot comply; a test over the flag |
| K7 | P2: root discovery and conventions | the root is the nearest statement with a data directory beside it; `seeds.txt` and `contest.json` documented in `scorer-cli`, `kaggle-cli`, `contest-preflight` and the setup page; an empty seed list and a relative ledger path block as an incomplete root |
| K8 | P2: the shell denial misses spellings and rejects text | the pattern takes a path to the binary, the alias, a line continuation and the Python API's call; described as an accidental-bypass guard; the quota lives in the procedure and the verifier |
| K9 | P2: modality and benchmark bias spread across the pages | setup records the modality; every leaderboard-only and scorer-only rule on the pages carries its condition; an anytime search spends the remaining time and an exact method returns; the length bound is the task's |
| K10 | P2: comparisons assume maximisation and add a delivery goal | "worse than, in the metric's direction"; validity, improvement and the floor distinguished; the account's best is a spend question, not a delivery requirement |
| K11 | P2: the preflight's rule hierarchy and the lost prompts | the organizers say what binds and the statement pins the binding document; every constraint quoted or pinned; starter and continuation prompts verbatim; the cap binds the scoring re-run; the skill's trigger is a contest scored on a site |
| K12 | P2: contradictory and stale CLI claims | only a push takes a session; the CPU-pool claim dropped; the terminal states named; "read the text" replaces the exit-code claim; the CLI line stated with `-h` as the fallback reading |
| K13 | P2: status and output not tied to the version | status, output, audit and submission name the version (`<owner>/<slug>/<version>`), one output directory per version |
| K14 | P2: the row count as the quota counter | the quota's unit and window from the statement; the ledger plus the whole paginated list, the site's allowance where shown, the procedure's reservation where it exists |
| K15 | P2: the loop, the stop and the harvest disagree | "When the work ends": the deadline or session gate, the spent quota, or the written stopping rationale; the harvest scoped to this campaign's kernels, this competition, the quota and the window, before the campaign's last round |
| K16 | P2: ceilings not established | the triage is a diagnostic; the stopping rationale is a rationale, not a proof; "sub-point" is "inside the noise floor" |
| K17 | P2: differing measurements as invalidity | a reproducibility protocol (the same build and inputs, the scorer's seeds fixed, repeated runs); a difference beyond the spread is a finding; a CV/public gap is investigated; void only on a false report, a broken rule, or the task's own all-or-nothing rule |
| K18 | P2: the submission auditor assumes a kernel | the brief branches by modality and checks only what the task establishes; label leakage, validation leakage and permitted transduction separated |
| K19 | P2: house moves as prohibitions | every move carries its condition and what to measure first; the alternative earns its place by measurement |
| K20 | P2: the copied skills' dependencies | `hf-model-fetch` and `tabular-modeling` copied too (six shared skills); `cv-protocol` and `ensembling` no longer cite the relational skill; the playbook's rules were made conditional in change 6 |
| K21 | P2: past-run memories | the lost result and the double-digit inflation are rules now: the insurance's margin, and a naive fold on grouped data overstates the public score |
| K22 | P3: the inventory's losses | the toolbox restored (proximal methods, Frank-Wolfe, trust-region, augmented Lagrangian, ADMM, Nelder-Mead, the ellipsoid method, firefly and bat), Monte-Carlo tree search named; "findings, not fixes" on the feedback page and in the auditor; the bank first and the web second on the ideation page (M13); the standings, the pull, the token's locations, the submit flags and the `--sandbox` warning in `kaggle-cli`; the daily cap and the cancelled run in its table; the continuation prompts and the cap on the re-run in the preflight |
| K23 | P3: the numpy requirement | the environment file dropped; the task's tools are checked in setup |
| M1 | P1: `stop_hook_active` | K6 |
| M2 | P1: the submission route | K3 |
| M3 | P2: the hooks' conventions named nowhere | K7 |
| M4 | P2: the scoring re-run and the session | K12 |
| M5 | P2: script-only as a Kaggle fact | a kernel is a script or a notebook; the task's rules decide; fixed at creation |
| M6 | P2: both modalities' rules unconditional | K9 |
| M7 | P2: a zero seed as a void | K2 |
| M8 | P2: repeated runs for a randomised solution | `scorer-cli`: repeated runs per seed, the mean and the spread recorded, a difference inside the spread is not one; the domain statement records the run count; the hook and the auditor read the spread |
| M9 | P2: the daily cap | the quota's window in `contest-economics` and `kaggle-cli`; the failure row restored |
| M10 | P2: the numpy requirement | K23 |
| M11 | P2: tracebacks fail open | K4 |
| M12 | P2: the bank pull unconditional, engine tool names | conditional on a served bank; "its index and card tools" |
| M13 | P2: "where to look outside" missing | the ideation page's source order: the summary and the board, the bank, then the web when the module's web is on |
| M14 | P3: the results file's location | at the attempt's root, in the skill and the hook |
| M15 | P3: the deny is bypassable; the pages oversell the gates | the pattern widened; the hooks described as mistake catchers; the pages say the finish asks once and the verifier reproduces |
| M16 | P3: two missing commands; "the board" is two things | the standings and the pull in the table; "the standings" and "the account's submissions list" named apart; the two token locations named |
| M17 | P3: `cv-protocol` on a heuristic attempt | the implementation page scopes it to a trained model; a heuristic solution's noise is the repeated-run spread |
| M18 | P3: house moves as absolutes | K19 |

**Change 8's inventory (IOAI into competitive-programming), for the record:**

| Source | Destination |
|---|---|
| `RULES.md`: the quota's authority, the report docstring, the account's history as inspiration | guardrails (standing rules) |
| `RULES.md`: no outside models or data, one GPU, the machine shape, no internet, a script only, the fixed package list and its pins, the session limits' numbers | the Brief's task rules and the runner's configuration (the pool sizes); the submission-auditor checks a kernel against the task's rules |
| `RULES.md`: the ticket office's protocol | the kaggle-cli skill (the discipline, no numbers); the office itself stays the runner's CLI |
| `KAGGLE_CLI.md` §0–§11: the modality, the pages, the download, the kernel folder and metadata, the push, the poll, the output, the submission, the score, the failures table | the kaggle-cli skill, with the named competition, the named data file, the fixed version number and the duplicated push line removed; the submission goes through the task root's procedure (the guide's "submissions need no ticket" against the rules' "take a score ticket" resolved by that procedure owning the pool) |
| `KAGGLE_CLI.md`: the copy-paste template with a token in it | dropped (a credential value in a page) |
| `preflight_spec.md`: the scaffolding, the hard boundary, the fidelity rules, where the rules win, the statement's sections | the contest-preflight skill (for a user's own task; the runner's preflight stays the runner's, and the setup page reads the root it wrote) |
| the handler's bank paragraph (the book as the first search priority, its tiers and layout) | the olympiad-playbook skill: the ten twists and the house moves, and how to pull a served bank's cards; the book itself is experience, not harness |
| the handler's loop (submit-and-learn rounds, the calibration gap, the time gate, "an idle clock is the one unacceptable outcome") | the contest-economics skill |
| the handler's board protocol (skip, steal, complement, ensemble) and the late-budget priority rule | the contest-economics skill and the ideation page |
| the handler's public-versus-private warning and "report the local score in the message" | the contest-economics skill |
| the handler's score tags and `result.json` line, the task and dataset paths, the time remaining, the competition slug, the rules path, the skill path, `best_score.log` | the Brief and the runner (task facts and engine fields) |
| `RUN_FINDINGS.md` I-7 (the lost first submission, the harvest, the triage by prediction rate), I-12 (validation inflation), I-14 (the reserve) | the contest-economics skill (insurance first, the harvest, triage, validation inflation; the reserve is the engine's) |
| `RUN_FINDINGS.md` I-1 to I-6, I-8 to I-11, I-13, the environment notes (lane collapse, the ideation split, the pool cap, the box setup, the `.env`, the checkpoint, orphaned GPU processes, the runner's default, the session pool's three consumers, zone exhaustion, per-model rate limits, the Bedrock trio) | dropped as runner and infrastructure incidents; their fixes live in the runner and the machine scripts |
| the port mapping's `kernel-slots` server | not a server: the runner's CLI (a decision in DECISIONS) |
| the port mapping's copied ML skills | `task-type-playbooks`, `cv-protocol`, `ensembling`, `eda-discipline` copied by directory, with a gate test that each copy is identical to its source |

### The pull-request review (Claude half, 2026-10-29)

`scripts/redesign/runs/wp8-pr-review/brief.md` on `1801fccf`, the Claude
reviewer only (the Codex login the arms' machines carry must not be
refreshed from the development box while they run). Twenty-two findings
(two P1, eight P2, twelve P3), answered in two commits: A (`690e8277`,
the code) and B (this one: the record, the pages, the plan).

| # | Finding | Disposition |
|---|---|---|
| 1 | P1: the scan imported RelBench's names through a module that imports the library, so the gate errored at collection on CI | the names are committed data (`benchmarks/relbench/data/datasets.json`, from the registry); the vocabulary test holds the file to the registry and to the runner's maps under its skip (A) |
| 2 | P1: three of nine S3 steps recorded while the Acceptance read as if all ran | the record re-derived with the deferred steps visible; the Acceptance carries the standing per step; MASTER's row says what the merge rests on (B) |
| 3 | P2: a live submission ledgered as rejected on a bare 400/403 in the output | the classifier reads the CLI's phrases; anything unconfirmed is pending, settled from the list; the harvest probe treats pending as made (A) |
| 4 | P2: the sanitizer's skip took the leakage scan's tests with it | the sanitizer tests in their own module (A) |
| 5 | P2: the MLE in-loop score is self-reported and unverifiable in the loop | the owner's call, recorded in DECISIONS; the Acceptance says what checks it (B) |
| 6 | P2: the reference's bundled-name example resolves to nothing | `predictive-modelling` (B) |
| 7 | P2: the retired handler seams in three pages; the names gate not extended | the sentences and rows removed; `min_iteration_seconds_insured`, `deliverable_ready_reserve_seconds`, `problem_handler.honor_agent_stop`, `use_knowledge_graph`, `fetch_huggingface_models`, `--no-kg` in the gate; `finalize_run_selection` is live code and the three knowledge flags appear in tests' negative assertions, so they stay out (B) |
| 8 | P2: PROVENANCE.md names open questions it never defines | it does, in the first pass's sections it carries at its end; the preamble now points there and defines the bank and reserve sets, in the file and its renderer (B) |
| 9 | P2: the Kaggle skill's pages line wrong for the installed CLI | fixed; competitive-programming 0.3.1, the frozen row re-pinned with the note (A, B) |
| 10 | P2: a local import in `benchmarks/common.py` | at the top (A) |
| 11 | P3: the plan's trees stale | redrawn as committed (B) |
| 12 | P3: two decision entries on the scan's home, the earlier unmarked | marked superseded (B) |
| 13 | P3: the S3 step budgets pre-amendment | re-pinned to the arms' budgets (B) |
| 14 | P3: "skills opened" and hooks fired on a Codex arm | `skills_staged`, `hooks_mounted` beside `hooks_fired`; the Acceptance says what a Codex arm evidences (B) |
| 15 | P3: the IOAI arm delivered nothing and its audit was empty | both in the note; a delivered candidate is part of the step's bar (B) |
| 16 | P3: the RelBench brief's schema heading | qualified: the library's database, what the copy keeps (B) |
| 17 | P3: the scan skips the manifest and the references; own names blanked before the number rule | both scanned; the number rule reads the raw line (A) |
| 18 | P3: a try/finally around the IOAI build | removed (A) |
| 19 | P3: `LITE_PROBLEMS` is the reported ten | `REPORTED_PROBLEMS`, the `--lite` label (A) |
| 20 | P3: an earlier launch's ledger satisfies the insurance gate | the ledger starts afresh at staging; the gate wants a non-rejected entry (A) |
| 21 | P3: the suite file reformatted whole in the S3 commit | said in the pull request's body |
| 22 | P3: the IOAI runner's experiment cap hard-coded | `run_defaults.iterations` (A) |

Clean, per the reviewer: the two harnesses as domain harnesses, the
engine facts the pages assert, the hooks, the runners, the bank
extension, the two engine fixes, the tests, the docs sentences.

### What the arms found in the engine (2026-10-29)

- **A separator inside an event's text cut the event** (`s3-relbench-1`,
  died in its first ideation at 16:48Z): a Codex web-search title held a
  U+2028 line separator; the session record split the stream with
  `str.splitlines`, which cuts there, and raised on the half-line. Fixed:
  `stream_lines` splits on the newline alone, every stream reader uses it,
  and a cut line is one without its newline (DECISIONS.md, 2026-10-29).
  The arms relaunched from the rebuilt wheel as `s3-relbench-2` and
  `s3-mle-4`; the arms already running carry the old wheel and are
  relaunched if the same cut kills one.
- **The ALE smoke died at the final report** (`s3-ale-smoke-1`, 17:29Z): the
  runner read the contestants off `session.standings`, and the pinned
  ALE-Bench (1.6.1) makes that property raise ("Accessing standings is not
  allowed"). Fixed: the loader's standings, which the runner already held
  for the brief, are threaded into `final_report`; `--final-eval-only`
  reports on the solution a workspace holds, so a runner that dies after
  its campaign is finished by hand (`scratchpad` `ale_finish.sh`). Test:
  the final-eval-only path enters no facade.
- **The ALE quick arm died inside its campaign** (`s3-ale-1`, ahc008, about
  17:55Z, 1.5 h in): the implementation session added
  `output_data_generic_exp_1/` to the repository's `.gitignore` beside its
  own `results/` and `*.scores.json`, and the engine's commit of its run
  folder at the session's close (`ExperimentSession.commit_folder`) failed
  on the ignore rule, which killed the campaign before a solution was
  delivered. Fixed: the run folder is added by force, since it is the
  engine's record and a candidate's ignore rules do not apply to it
  (DECISIONS.md, 2026-10-29). Relaunched as `s3-ale-2` from the rebuilt
  wheel.
- **The IOAI quick arm's score is a replay** (`s3-ioai-1`, timed-deps, one
  lane, two hours, the bank served minus the task's own entry): the agent
  found the Kaggle account's own August kernel for the competition on the
  account, "stole the proven kernel", pushed once (public 1.00000 at
  16:52Z, out-of-fold 0.7802) and stopped at 17:35Z with the budget
  exhausted after one experiment. No shell submit (the ledger's token is
  on the submission), the preflight, the contest root, the ledger, the
  hooks and the runner all ran on the harness; but the bar "above the
  median" is met by a replay, not a cold start, and the record says so. A
  clean reading needs a Kaggle account that never entered the competition,
  or the radar practice competition with its rules accepted in a browser,
  which only the owner can do. The campaign delivered no candidate
  (`branch: null`, the budget exhausted after one experiment) and the
  static audit found no kernel folder under the task directory
  (`audit: {}`); the step's bar includes a delivered candidate since the
  review, and this arm fails it.
- **The Kaggle swap ran clean** (`s3-kaggle-swap-1`, spooky-author-identification
  through the IOAI preflight and runner under the predictive-modelling
  harness, two hours): four submissions through the ledger, best public
  log loss 0.30161 at 17:00Z, two experiments, no harness edit.
- **The MLE quick arm died in the maintainer's calibration** (`s3-mle-1`,
  16:33Z, eight minutes in): the calibration run exited 2 with `existing
  evaluator snapshot is corrupt`. The line is printed by
  `kapso_evaluation/kapso_eval.py`, which the evaluation-setup session
  wrote for this campaign: it snapshots the evaluation directory under the
  archive root by a fingerprint of the tree and refuses a snapshot whose
  fingerprint no longer matches, and a snapshot that has been run once
  carries its own bytecode cache. Not engine code, and not the harness's
  prose either (the smoke on the same task, `s3-mle-smoke-2`, wrote an
  evaluator without a snapshot); one run's evidence, kept here for the
  harness review rather than patched. The relaunch (`s3-mle-4`) is the
  second reading.

## Hours

| Change | Estimate | Cost | As run |
|---|---|---|---|
| 1–4 the plan v2, the bundled root, predictive-modelling 0.1.0 | 6 h | | 5 h so far |
| 5–6 MLE into the harness, the review | 5 h | the review's tokens | |
| 7–9 competitive-programming from ALE and IOAI, the reviews | 8 h | the reviews' tokens | |
| 10 the engine seams | 2 h | | |
| 11–14 the four runners on `build()` | 10 h | | |
| 15 the book as a bank, the second provenance pass | 4 h | a subagent's tokens | |
| 16–17 the scan, the swaps | 4 h + four one-hour arms | about $15 | |
| 18–19 the arms | 2 h of launching + the wall clock (RelBench 14 h on `gpu4`, MLE 26 h on `gpu`, IOAI 3 h, ALE 4 h, overlapping) | about $180 of spot machines; the Claude Max bucket | |
| 20–22 S3, the author test, the docs, the PR review | 5 h + two author arms | | |
