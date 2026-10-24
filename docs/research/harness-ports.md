# Porting the benchmarks to two harnesses, and the knowledge they already hold

2026-10-24. Companion to `harness-design.md` and `onboarding.md`. Two
harnesses cover the four benchmarks: `predictive-modelling` for MLE-bench
and RelBench, `competitive-programming` for ALE-bench and IOAI. This note
says what each benchmark contributes to its harness, what stays with the
benchmark's runner as task material, and where each benchmark's knowledge
lives today, found by reading the tree and the worktrees on this machine.

## 0. The split

A harness is a domain; a benchmark is a set of tasks in it. Two benchmarks
share a harness when the standing rules, the skills and the checks are the
same and only the tasks differ. That holds for both pairs:

| Harness | Benchmarks | What they share | What differs, and lives in the task |
|---|---|---|---|
| `predictive-modelling` | MLE-bench, RelBench | a test set that never trains, cross-validation discipline, leakage as the failure that voids, subsample early then full, ensembling late, features before architectures | the data shape (a flat Kaggle dataset; a relational database with a temporal cutoff), the evaluator (the MLE grader; the RelBench protocol per task), the compute |
| `competitive-programming` | ALE-bench, IOAI | an official scorer or leaderboard as the only truth, a timed budget, a submission quota, ship-early-then-improve, a report with every submission | the problem kind (heuristic optimisation on AtCoder; ML tasks on Kaggle), the submission mechanic (a local scorer; a kernel push and a submit) |

The situations one benchmark has and the other lacks are skills the page
names by situation: "when the statement says the data is a relational
database with a temporal cutoff, build the sanitized cache in setup and
follow the temporal-protocol skill". A skill costs nothing on the tasks
that never trigger it.

## 1. predictive-modelling

### What each benchmark contributes

| Part | From MLE-bench | From RelBench |
|---|---|---|
| guardrails | test set and submission always full; the statement's metric is the metric | no row dated after its seed time is ever visible to a feature; the protocol per task decides what the database contains |
| setup page | profile the data, fetch candidate models and datasets from the hub, write the statement with task type, metric, splits, data size, compute | build the sanitized cache (`sandbox.py`: truncate at the test timestamp, strip the label-bearing columns), return it as `prepared/cache`; write the regime (frozen-db or seed-time) into the statement from `EVALUATION_PROTOCOL.md` |
| ideation page | the three stages by budget progress (mini, full, final ensembling) as a pacing rule | the five axes verbatim: features and representation, training distribution, model mechanism, decoding and post-processing, validation protocol |
| implementation page | stratified subsample first, hard-coded STAGE knob, print epoch times, heavy ensembles only at the end | features before architecture, the feature matrix is never finished, group-relative features, capacity matched to labelled rows, per-tick retraining under the rolling contract |
| verification page | the test split never read outside the grader; CV-versus-public gap as the calibration problem | the static audit for reads outside the cache, the `upto_test_timestamp` trap, validation that looks fine while test is stripped |
| feedback page | stage-aware scoring: do not prune a mini-stage candidate against a full one | the per-axis frontier; ship nothing below the reproduced champion |
| learning page | scope by task type and data modality | scope by dataset, task and temporal regime |
| skills | `task-type-playbooks` (from `kg_data.json`, one reference per workflow), `hf-model-fetch`, `cv-protocol`, `ensembling`, `tabular-modeling` | `sanitize-cache` (with the script), `temporal-protocol` (the two regimes and the rolling contract), `relational-feature-practices` (the eight measured practices), `relbench-api`, `torch-frame`, `living-documents` (table information and feature history files) |
| delegates | `leakage-auditor` | the same auditor, briefed on temporal leakage |
| servers | none; the hub is reached in setup | none |
| hooks | `protect-prepared` (the split is read-only), `deny-web-fetch` on implementation and verification (the hub is for setup) | the same two; the web denial is RelBench's `implementation_web: false` rule made a hook |
| deployment | `predict-endpoint` | none needed |

### What stays with the runner

Task selection, the data download and the raw cache, the grader and the
evaluation directory (`data/generic_eval/grader.py`, the starter kit's
`CONTRACT.md` folded into the task statement), the leaderboard comparison,
the GPU lane pinning and timeouts (engine config). The runner becomes
`kapso build --harness predictive-modelling` plus task selection and final
scoring, as the interface draft said.

### Knowledge found

| What | Where | Format and size | Status | Onboards as |
|---|---|---|---|---|
| the RelBench lesson bank, learned by the pipeline | `github.com/Leeroo-AI/kapso-bank-relbench` (private, last push 2026-08-22); local bare clone in the `relbench-learning` worktree at `data/kapso-bank.git` (branches `main`, `archive`; tags `lr_founding_20260818` through `lr_20260822T093928`); the founding seed at `data/.seed-founding` (10 insights, 3 procedures) and a review copy at `data/.review-bank` | the bank format: `index.md`, `insights/*.md`, `procedures/*/card.md`, `log.md`, `sightings.md` | real, measured, the only learned bank among the four | `load_experience("Leeroo-AI/kapso-bank-relbench")`; see section 3 on scope |
| the MLE knowledge graph | `benchmarks/mle/data/kg_data.json` | 51 nodes, 50 edges: 34 workflows by task type (text classification, tabular, image, audio, time series, graph ML, VQA, segmentation, ...), 8 concepts, 8 code examples, 1 "Kaggle competitions" tip sheet; 79 KB; loaded into Neo4j by the old wiki agent on request | hand-written, 2026 era, prescriptive | the workflows and code examples become `task-type-playbooks` with one reference file each; the tip sheet is reviewed line by line before any of it reaches a page (section 3) |
| RelBench domain notes | `benchmarks/relbench/context.py`: `FEATURE_ENGINEERING_NOTE`, `MODELLING_PRACTICE_NOTE` (eight practices), `ROLLING_CONTRACT_NOTE`, `CHAMPION_NOTE_TEMPLATE`, `LIVING_DOCUMENTS_NOTE`, `FEATURES_HISTORY_TEMPLATE`; `EVALUATION_PROTOCOL.md` | prose, about 500 lines | measured on past campaigns, the best-written domain material in the tree | pages and the four RelBench skills above; the champion note is the engine's artifact offer, not harness material |
| MLE handler prose | `benchmarks/mle/handler.py`: the stages, the hub fetch, the output rules | prose | in use | the setup and implementation pages |

## 2. competitive-programming

### What each benchmark contributes

| Part | From ALE-bench | From IOAI |
|---|---|---|
| guardrails | the official scorer is the score; the time limit is the task's; a solution that fails one seed fails | `RULES.md`: the statement's quota is the authority (default 50), every submission opens with a self-contained report docstring, the leaderboard is the arbiter; the account's whole history is fair inspiration |
| setup page | build the task root: statement, local scorer, test cases, the baseline score | the preflight: from a URL or starter prompt to a downloaded dataset, `kaggle.json` and a complete statement nobody has to leave the repository to solve (`preflight_spec.md`), with quota, deadline, submission modality and compute in it |
| ideation page | axes: algorithm family, state representation, neighbourhood and move design, time allocation, multi-strategy by input condition; every proposal states expected score and the first-strong-score time | axes: model family, data use, transduction on the unlabelled evaluation set, time allocation; the statement's twist decides which playbook section applies |
| implementation page | avoid recomputation, light random, no allocation in loops; precompute or hard-code for fixed inputs; run several annealers under the time budget | an insurance submission within the first minutes, then improvement; a time-allocation plan written before the first kernel; confirm a mid-run score only when the expected gain earns it; harvest pushed-but-unsubmitted kernels before the end |
| verification page | run the scorer on every seed, check the time limit, compare against the baseline | audit the kernel for external resources and leakage; the submission's public score is the measurement; CV inflation against the public score is evidence |
| feedback page | score and runtime against the baseline; which family is saturated | time-to-first-strong-score, critical-path velocity, confirmation overhead, the counterfactual GPU ledger; stop when the ceiling is proven, with the noise-floor argument |
| learning page | scope by problem family and algorithm family | scope by the statement's twist (the book index's ten sections) and data modality |
| skills | `heuristic-patterns` (the handler's domain knowledge: annealing, beam and random search, random simulation, ant colony, parameters, conditional generation, implementation), `cpp-performance`, `scorer-cli` | `kaggle-cli` (from `KAGGLE_CLI.md`, the eleven sections), `contest-preflight`, `contest-economics`, `olympiad-playbook` (the book index's router, pointing at the ingested bank) |
| delegates | `score-auditor` (reads the scorer output across seeds) | `submission-auditor` (the kernel audit as judgment) |
| servers | none | `kernel-slots` (`kernel_slots.py`: the ticket office for the account's session limits; the credential-holding server) |
| hooks | `require-scorer-run` (Stop: no finish without a scorer run on all seeds) | `deny-shell-submit` (a `kaggle competitions submit` typed in the shell goes through the skill's procedure, not ad hoc), `require-insurance` (Stop in implementation: no finish without a first submission logged) |
| deployment | none | none |

IOAI's modelling content is predictive-modelling's. The contest harness
lists the ML skills it needs by copying their directories; `check` does not
mind, and a skill is a plain directory. Composing harnesses is not in the
design and is not needed for this.

### What stays with the runner

ALE: the problem set, the Docker scorer, the Elo computation. IOAI: the
competition list, the account, the organizers' prompts, the final scoring
against the leaderboard, `agent_traces_for_organizers`.

### Knowledge found

| What | Where | Format and size | Status | Onboards as |
|---|---|---|---|---|
| the IOAI knowledge bank, curated by hand | the `ioai-2025` worktree (branch `worktree-ioai-2025`), `benchmarks/kaggle/knowledge_bank/`: `INDEX.md` (tiers sure-gold, claimed-max, e1-active; status; best score), `book_index.md` (67 problems, a router by the statement's twist in ten sections), one directory per problem with `problem.md`, `idea.md` and `solution/` with runnable code; `knowledge_bank_reserve/` for weaker evidence | 333 files, 35 MB, plus 407 files, 44 MB in the reserve | **gitignored on purpose** ("local research material, never committed"), present only on this machine, used by the Kaggle handler as "first search priority" staged into the task root | an ingested index: `kapso experience add --dir <path> --name ioai-book`, then `load_experience("ioai-book")`; the router becomes the `olympiad-playbook` skill that tells the agent how to read the index. The directory needs a backup before anything else: it exists nowhere else |
| the past-task harvester | `benchmarks/ioai2026/past_learning/` (`harvest/extract_prompt.md`, `aggregate_prompt.md`, two prepared 2024 tasks) | prompts and data preparation | a hand-rolled learning loop for one target task | superseded by `learn()`; its `LEARNINGS.md` seed caches (`t1_seed_cache` through `t1_seed_v3`) lived on the GCP boxes and in a session scratchpad and are not on this machine |
| run findings and organizer answers | `benchmarks/kaggle/RUN_FINDINGS.md` (issues I-1 to I-13 with evidence and fixes), `discussions.md` (organizer Q&A), `K_RAMP_SPEC.md` | prose | on the `worktree-ioai-2025` branch | the economics and session-pool facts go into `contest-economics` and the `kernel-slots` skill |
| ALE domain knowledge | `benchmarks/ale/handler.py` `_get_domain_knowledge()`; `README.md` "Domain Knowledge" | about 60 lines of prose | in use | the `heuristic-patterns` skill, almost verbatim, split into sections |
| ALE experiment contexts | `benchmarks/ale/data/experiment_data/ahc00{2,5,6}_context.txt` | cleaned problem statements | task material | stays with the runner |

Nothing learned by the pipeline exists for ALE or IOAI. The bank at
`~/.kapso/bank.git` on this machine holds the facade end-to-end test's
`churn` lessons, not a benchmark's.

## 3. Open points

1. **Scope of an external bank.** The RelBench cards carry the task family
   `relbench`, and the harness they will serve is `predictive-modelling`.
   The rule in `onboarding.md` scopes `mine` to the loaded harness; a bank
   loaded by reference should serve everything it holds, because loading it
   was the choice. Recommended: scope applies to `mine` only.
2. **The MLE tip sheet contradicts the harness.** Its "Kaggle competitions"
   node says to avoid out-of-fold validation and heavy folding as time
   consuming. The predictive-modelling guardrails say cross-validation
   discipline is the rule. The workflows and code examples port; the tip
   sheet is reviewed line by line and most of it does not.
3. **The IOAI bank's provenance.** It holds winners' notebooks and
   reimplementations gathered from public contest archives, deliberately
   kept out of git. Before it becomes an index that ships to anyone, its
   licence per entry and the organizers' rules on prior solutions need a
   pass. Until then it is a local experience source for our own runs.
4. **Naming.** `competitive-programming` is the owner's name; IOAI is ML
   under contest rules rather than programming. The description carries
   both: "timed contests scored by an official scorer or leaderboard:
   heuristic optimisation and ML olympiad tasks".
5. **Order of porting.** RelBench first: it has the most written domain
   material and the only learned bank, so it exercises pages, skills,
   hooks and experience in one port. Then MLE into the same harness, then
   ALE as the smaller contest port, then IOAI with its server and bank.
