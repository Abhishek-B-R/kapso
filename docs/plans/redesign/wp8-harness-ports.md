# WP8: the harness ports

2026-10-29. Owner: the redesign's implementer. Branch `wp8-harness-ports`
(off `redesign` at 5647528b, the merge of WP9). Size: XL in the master,
refined here to three to four days of wall clock with the runs overlapping;
the hours table at the end tracks it. The port mapping is
`docs/research/harness-ports.md`; the order of work and the done-when lines
are `docs/plans/initial-harnesses-plan.md` (P1 to P5); the semantic test is
S3 of `docs/plans/semantic-production-tests.md`. The package was parked
until the owner said go; the owner's go is the full-path timeline agreed on
2026-10-28.

## Scope

Two bundled harnesses under `src/kapso/harness/bundled/`, loaded by name:
`predictive-modelling`, written from RelBench and then MLE-bench, and
`competitive-programming`, written from ALE-bench and then IOAI. Each is a
complete tree in the package's own grammar: pages, skills with their
scripts, a delegate, hooks, a server where the port plan names one, a
requirements file; `kapso harness list` names them; `check` is green with
no warning. The four benchmark runners become task material plus `build()`
with the harness plus final scoring: the handlers' problem-context prose
retires into the pages and skills, and the grader, the raw cache and the
task's facts stay with the runner. The knowledge each benchmark holds is
onboarded where the design puts it: the RelBench bank served by reference,
the MLE graph's workflows as a skill, ALE's prose as a skill, and the IOAI
book, backed up and passed for provenance, converted to a bank in the card
grammar and served by path. The cross-checks of the plan's P5 run at the
end: the abstraction scan as a gate test, the task swaps, and S3's author
test on `pipeline-dbt` again after the ports' guide fixes. One
non-regression run per benchmark, at its recorded budget and model, is
archived and recorded here; S3 joins the semantic suite with its report.

**Not in scope.** New leaderboard results or campaigns across tasks (one
task per benchmark reproduces; the campaign runners keep working but are
not re-run). Learning from these runs or re-learning the RelBench bank (the
learn verb is WP3's, exercised by S6). Publishing the IOAI bank or any entry
whose licence is unknown: the provenance table gives the owner the
decision, and nothing of the book is pushed anywhere by this package. The
docs' navigation and catalogue (WP10): this package writes the bundled
README, each harness's README, and the sentences the existing pages need
to name the bundled harnesses. The release (WP11). The live UI (out of the
first release by decision).

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
predictive-modelling/                    competitive-programming/
├── harness.yaml                         ├── harness.yaml
├── requirements.txt                     ├── requirements.txt
├── instructions/                        ├── instructions/
│   guardrails setup ideation            │   guardrails setup ideation
│   implementation verification          │   implementation verification
│   feedback learning                    │   feedback learning
├── skills/                              ├── skills/
│   sanitize-cache (scripts/sanitize.py) │   heuristic-patterns
│   temporal-protocol                    │   cpp-performance
│   relational-feature-practices         │   scorer-cli
│   relbench-api  torch-frame            │   kaggle-cli
│   living-documents                     │   contest-preflight
│   leakage-scan (scripts/scan.py)       │   contest-economics
│   cv-protocol                          │   olympiad-playbook
│   task-type-playbooks                  ├── agents/
│   hf-model-fetch (scripts/fetch.py)    │   score-auditor.md
│   ensembling  tabular-modeling         │   submission-auditor.md
├── agents/leakage-auditor.md            ├── mcp.json  (kernel-slots)
├── hooks/                               ├── servers/kernel_slots.py
│   protect-prepared  deny-web-fetch     └── hooks/
└── (no servers)                             require-scorer-run  deny-shell-submit
                                             require-insurance
```

The port mapping per part (page or attachment, and the file it is written
from) is the table in `docs/research/harness-ports.md`; the per-step table
in `docs/plans/initial-harnesses-plan.md` names the source files. Both
harnesses start at `0.1.0` with the first benchmark and go to `0.2.0` with
the second; every later edit bumps the version.

**The runners.** Each keeps its line and its task material and launches
the facade:

```text
python -m benchmarks.relbench.runner -s rel-trial -t study-outcome [--harness REF] [--experience REFS] [--time-budget-hours H] [--coding-agent CLI]
python -m benchmarks.mle.runner --competition spooky-author-identification [--harness REF] [--experience REFS] [--coding-agent CLI]
python -m benchmarks.ale.runner --problem ahc008 [--harness REF] [--experience REFS] [--coding-agent CLI]
python -m benchmarks.ioai2026.runner --root RUN_ROOT --hours H [--harness REF] [--experience REFS] [--coding-agent CLI]
```

`--harness` defaults to the benchmark's bundled harness; any reference is
accepted, so the task swaps need no runner edit. A runner composes a `Brief`
from the task (objective; measured by: the metric and its direction;
baseline: the published entry; rules: the task's own numbers and access
rules; budget: the recorded one), passes `evaluation=` the benchmark's
grader directory and `data=` the task's data, loads the harness, calls
`build()`, then scores the delivered candidate once the benchmark's way
(RelBench's test table; MLE-bench's grader; ALE's private cases; the
leaderboard) and prints the report as today. The `benchmark:` block of each
override file keeps the runner's own keys (WP4); the engine never reads it.

**The evaluation directories.** RelBench's `data/generic_eval` as today
(validation scoring over the sanitized cache). MLE: a grader directory the
runner writes per competition, which runs the candidate under the runtime
limit and grades it with MLE-bench's grader against answers that live
outside the workspace. ALE: a grader that runs the candidate through the
Docker scorer over the public cases, every seed, and reports the score and
the time limit. IOAI: the leaderboard reader over the campaign's submission
ledger, the lane's best public score since the campaign's start. Each is
copied to `kapso_evaluation/` and integrity-protected by the engine; a
candidate that edits it is rejected (WP1).

**The abstraction scan.** `src/kapso/harness/abstraction.py`:
`scan(root: Path, vocabulary: Iterable[str]) -> list[Finding]`, a finding
being the file, the line and the word; the words are a benchmark's task
and dataset names, competition ids and problem ids read from the
benchmarks' own registries (RelBench's `task_specs`, ALE's problem lists,
MLE's competition registry, IOAI's practice uids), plus two fixed rules: a
decimal that reads as a score, quota or deadline on a page, and a path
outside the harness's conventions (`${PLUGIN_ROOT}`, `$KAPSO_HARNESS_ROOT`,
`prepared/`, the task statement). The gate test
`tests/harness/test_bundled_abstraction.py` runs it over both bundled
harnesses and fails on a hit. `check` does not change: it is domain-agnostic
and a user's harness is not our benchmark's (a decision below).

**The IOAI book as a bank.** `benchmarks/ioai2026/book_to_bank.py --book
DIR --provenance provenance.json --out DIR --verdicts shippable-with-attribution,ours`
writes a bank repository in the card grammar (`index.md`, `insights/`,
`procedures/<uid>/card.md` with the solution files beside it, `log.md`):
one procedure card per entry whose verdict is listed, `scope: domain`,
`reliability.state` `active` for the sure-gold tier and `candidate` for the
rest, the evidence block naming the public score and its source, the
rationale naming the tier, the provenance block naming the author and the
licence. A second run with `--verdicts local-only` writes the bank that
stays on this machine. The shareable bank's home is `~/banks/ioai-book.git`
plus the backup bucket; a remote is the owner's call. The campaign loads it
with `--experience ~/banks/ioai-book.git`; the harness's `olympiad-playbook`
skill says how to pull the matching cards for a statement's twist and
carries no problem name and no score. The provenance table
(`benchmarks/ioai2026/PROVENANCE.md`) is committed as the record of the
pass.

**S3 in the suite.** `tests/semantic/suite.json` gains `s3`: the four
non-regression runs with their recorded bars, the scan, the four task
swaps and the author test; `scripts/redesign/s3_ports.py --rederive` reads
the archived runs and renders `tests/semantic/reports/s3-1.md` through
`tests/semantic/report.py`; the verdict is the runner's exit status as for
every test.

**The benchmark machine.** `scripts/redesign/benchmark_machine.sh`, the
fresh-machine script's shape with a GPU: a spot `a3-highgpu-1g` (one H100)
or `a2-highgpu-1g` (one A100) in the credit project's zones, a
driver-bearing image, the wheel, the benchmark's requirements, the tokens
from the project's secrets, the run archived one file per run and the
machine deleted. ALE runs on a CPU machine with Docker.

### What this package consumes

WP2's harness package (the bundled root, `check`, staging per host, the
task statement, verification, `KAPSO_HARNESS_ROOT`, `${PLUGIN_ROOT}`); WP3's
experience (a bank by path or git reference, the serving, the pull log);
WP4's config (override files, the reserved `benchmark:` block); WP1's
handles (`Brief`, `Budget`, `Solution`, `load_harness`, `build()`); WP6's
record (the trace that shows the harness at work); WP9's runner shape
(`fresh_machine.sh`, the author test driver, the suite and the report).

## Ownership

Edits: `src/kapso/harness/bundled/` (the two trees and the README),
`src/kapso/harness/abstraction.py` (new), `benchmarks/` (the four runners,
handlers, override files and READMEs; `relbench/context.py`,
`relbench/campaign.py`; `ioai2026/book_to_bank.py`, `ioai2026/PROVENANCE.md`),
`tests/harness/test_bundled*.py` (new), `tests/test_benchmark_runners.py`,
`tests/test_relbench_*.py`, `tests/test_ioai2026_benchmark.py`,
`scripts/redesign/benchmark_machine.sh` and `scripts/redesign/s3_ports.py`
(WP9's directory, merged; noted here), `tests/semantic/suite.json` (the `s3`
entry), `tests/semantic/reports/s3-*.md`, `tests/semantic/README.md` (the
S3 section), `docs/harnesses/use.mdx` and `docs/reference/harness.mdx`
(the bundled sentences), `docs/harnesses/write.mdx` (the rules the author
test re-run teaches), `docs/plans/redesign/{MASTER,DECISIONS}.md`, this
plan.

Reads, never edits: `src/kapso/harness/*.py` other than the new module
(WP2: a needed change is recorded here as a finding first),
`src/kapso/experience/` (WP3), `src/kapso/kapso.py` and `handles.py` (WP1),
`src/kapso/core/config.py` and `config.yaml` (WP4), `plugin/` (WP7),
`examples/harnesses/trading/` (the model, copied from where two hooks are
the same program).

## Changes

Each one a commit with its test; the suite green at each.

1. **MASTER's rows and this plan.** WP9's row says merged by pull request
   #165 (merge 5647528b); WP8's row says built on this branch; the
   decisions below in DECISIONS.
2. **The bundled root under test.** `tests/harness/test_bundled.py`: every
   directory under the bundled root passes `check` with zero failures and
   zero warnings at the packaged `page_warning_lines`, `parse_reference`
   resolves its name as `bundled`, `kapso harness list` prints it under
   `bundled` with its needs. The bundled README rewritten for what ships.
   Proves: a port that ships broken is caught by the gate, not by a user.
3. **`predictive-modelling` 0.1.0, the pages, from RelBench.** Seven pages
   from `benchmarks/relbench/context.py` (the data-access rules and the
   iteration protocol into guardrails; the five design axes into ideation;
   `FEATURE_ENGINEERING_NOTE`, the eight practices and the rolling contract
   into implementation; the audit's rules into verification; the
   per-axis frontier and the reproduced-champion rule into feedback; the
   temporal regimes from `EVALUATION_PROTOCOL.md` into setup and learning),
   each under forty lines, the manifest listing the modules. The task's
   numbers (metric, splits, seed times, the prediction contract) stay in
   the task statement: a page says "the task statement" where the handler
   said a value.
4. **Its skills, delegate and hooks.** `sanitize-cache` with
   `scripts/sanitize.py` (the handler's `build_sanitized_cache` as a CLI
   taking dataset, task, source cache and output; relbench's API, no
   constant), `temporal-protocol` (the two regimes and the rolling
   contract), `relational-feature-practices` (the eight measured
   practices), `relbench-api`, `torch-frame`, `living-documents` (the table
   information and feature-history templates), `leakage-scan` with
   `scripts/scan.py` (the handler's `_audit_patterns` over a diff, a finding
   per hit, exit 1 on any), `cv-protocol`; `agents/leakage-auditor.md`
   briefed on temporal leakage; `hooks/protect-prepared` and
   `hooks/deny-web-fetch` (the trading example's programs, copied). Tests:
   the two hook scripts on both hosts' event shapes; the scan on a
   constructed diff with one hit per rule and a clean one; the sanitizer on
   a three-table fixture (rows after the cutoff gone, label columns gone,
   the test table reduced to entity and seed time).
5. **The independent review of the harness.** Codex (`gpt-6-astra`, xhigh,
   read-only) against the rubric the demo harnesses were reviewed on
   (domain-general, abstracted, the benchmark's bias in one place), then
   the revision and the version bump; recorded under Review.
6. **The RelBench runner on `build()`.** The `Brief` from the task spec
   (`_task_definition`, `_prediction_contract`, `_resources`, the label
   stats, the regime), `evaluation=data/generic_eval`, `data=` the starter
   kit, `--harness` defaulting to the bundled name, `--experience` as
   today; `RelBenchHandler` keeps the raw and sanitized caches, the shared
   cache, `final_evaluate` (test once, then the audit) and loses
   `get_problem_context`, `apply_bank_intro`, the notes and the axes;
   `context.py` keeps the task-side builders only; `campaign.py` follows.
   Tests: the solve path with `build()` mocked (the brief carries the task's
   facts and no note's sentence; the harness is the loaded one; the
   evaluation directory is the grader's), `test_relbench_integration.py`
   and `test_relbench_champion_seed.py` moved to the new shape.
7. **The RelBench reproduction.** `rel-trial/study-outcome` (classification,
   AUROC; Kapso's recorded 82.1 against the baseline study's 75.16) at the
   recorded budget (`budget.minutes: 600`, reserve 15) and model (the
   override file's Codex `gpt-5.6-sol` at xhigh), the RelBench bank served
   by reference (`Leeroo-AI/kapso-bank-relbench`). A two-hour smoke arm
   first, on the same machine type, to catch a harness fault before the
   full arm. Recorded: the score against the band the task's records give
   (the campaign's run-to-run spread for the task; the record names it),
   pages in the prompts, skills opened, the delegate's reports, the hooks
   fired, the cards served and cited, the cost and the hours.
8. **MLE-bench into the harness, 0.2.0.** The pages' additions (setup:
   profile the data, fetch candidate models and datasets from the hub,
   record task type, metric, splits, data size and compute in the domain
   statement; ideation and implementation: the three stages as a pacing
   rule by budget progress, the stratified subsample first, the hard-coded
   stage knob, epoch times printed, heavy ensembles last; feedback:
   stage-aware scoring), the skills `task-type-playbooks` (one reference
   per workflow node of `kg_data.json`, the code examples kept; the tip
   sheet reviewed line by line with the dropped lines listed under Review),
   `hf-model-fetch` with `scripts/fetch.py` (the handler's hub fetch),
   `ensembling`, `tabular-modeling`. The Codex review again, on the delta.
9. **The MLE runner on `build()`.** The grader directory written per
   competition (the candidate run under the runtime limit, MLE-bench's
   grader on answers outside the workspace), `data=` the prepared
   competition data, the handler's prose retired (`_set_problem_context`,
   `_generate_problem_context`, the stages, the hub text). Tests: the solve
   path with `build()` mocked; the grader script on a fixture submission.
10. **The MLE reproduction.** One lite competition
    (`spooky-author-identification`, the handler's default) at the
    benchmark's budget (the override file's session ceilings and the eight
    hour runtime limit) and model. The tree records no MLE result: the run
    records the baseline, and the bar is a valid graded score at the
    budget, said as such.
11. **`competitive-programming` 0.1.0 from ALE-bench.** Pages (guardrails:
    the official scorer is the score, the time limit is the task's, a
    failing seed fails; setup: the task root with statement, scorer, cases
    and baseline; ideation: algorithm family, state representation,
    neighbourhood and move design, time allocation, multi-strategy by input
    condition, every proposal with an expected score and a
    first-strong-score time; implementation: the efficiency rules;
    verification: the scorer on every seed, the time limit, the baseline;
    feedback: score and runtime against the baseline, which family is
    saturated; learning: scope by problem and algorithm family), the
    skills `heuristic-patterns` (the handler's `_get_domain_knowledge`,
    sectioned), `cpp-performance`, `scorer-cli` (how to run the scorer the
    task root provides and read its output), `agents/score-auditor.md`,
    `hooks/require-scorer-run` (Stop on implementation: no finish without
    a scorer run over every seed in the attempt's results). Tests: the hook
    on both hosts' shapes with and without the results file; `check` green.
    The Codex review.
12. **The ALE runner on `build()`.** The grader over the public cases
    through the Docker scorer, `final_evaluate` on the private cases kept,
    the prose retired. Tests: the solve path with `build()` mocked; the
    grader on a fixture scorer output.
13. **The ALE reproduction.** `ahc008` (the handler's default, in the lite
    list) at the benchmark's budget and model. No ALE result is recorded in
    the tree: the run records the baseline, the bar is a valid score over
    every seed at the budget.
14. **IOAI into the harness, 0.2.0.** Guardrails additions from `RULES.md`
    (the statement's quota is the authority, the report docstring on every
    submission, the leaderboard as arbiter, the account's history as fair
    inspiration); setup: the preflight from `preflight_spec.md` (URL or
    starter prompt to data, `kaggle.json` and a complete statement with
    quota, deadline, modality and compute); implementation: the insurance
    submission, the time-allocation plan before the first kernel,
    confirm-gain discipline, the harvest before the end; verification: the
    kernel audit (`audit_kernel`'s rules) and CV inflation against the
    public score; feedback: time to first strong score, critical-path
    velocity, confirmation overhead, the GPU ledger, the ceiling proof with
    the noise-floor argument; the skills `kaggle-cli` (from
    `KAGGLE_CLI.md`'s eleven sections), `contest-preflight`,
    `contest-economics` (the handler's economics and `RUN_FINDINGS.md`'s
    thirteen issues as rules), `olympiad-playbook` (the ten twists of the
    book's router and how to pull the served bank's cards for a twist; no
    problem name, no score); `agents/submission-auditor.md`; the server
    `kernel-slots` from `kernel_slots.py` (FastMCP, the ledger under the
    campaign root, the limits from the statement's quota file the setup
    session writes under `prepared/`); `hooks/deny-shell-submit`
    (PreToolUse on the shell: `kaggle competitions submit` typed in the
    shell is denied with the skill's procedure named) and
    `hooks/require-insurance` (Stop on implementation: no finish before
    the first submission is in the ledger). Tests: the server's tools on a
    fixture ledger; both hooks on both hosts' shapes. The Codex review.
15. **The IOAI runner on `build()`.** The preflight stays and writes the
    task root; the `Brief` from its statement; the evaluation is the
    leaderboard reader over the ledger; the handler's `get_problem_context`
    retired; `run_final_eval`, the harvest and the organizers' trace export
    stay. Tests: `test_ioai2026_benchmark.py` moved to the new shape; the
    reader on a fixture ledger.
16. **The IOAI book as a bank.** `book_to_bank.py` with the provenance
    table's verdicts; the shareable and the local-only banks built under
    `~/banks/` and copied to the backup bucket beside the tarballs;
    `PROVENANCE.md` committed. Test: a three-entry fixture book (one
    shippable, one ours, one local-only) converts into the right bank with
    every card field the grammar names, `index.md` listing the cards, the
    solution files under `procedures/<uid>/`, and the local-only entry
    absent from the shareable bank.
17. **The IOAI reproduction.** One practice task from the override file's
    list with the shareable bank served, at the recorded budget and model;
    zero shell-level submits in the trace; the cards pulled through the
    playbook skill named in the pull log.
18. **The abstraction scan.** The module, the gate test over both
    harnesses with the vocabularies read from the benchmarks' registries,
    the hits fixed at the source.
19. **The task swaps.** A different RelBench dataset through the RelBench
    runner; a Kaggle tabular competition through the IOAI runner's
    preflight with `--harness predictive-modelling`; an AHC problem outside
    the lite list through the ALE runner; an IOAI 2025 task through the
    IOAI runner. Short arms (an hour each): the question is whether the
    task runs with no harness edit. An edit needed is a finding against the
    harness or the guide, recorded and fixed at the source.
20. **The author test again.** `author_test.py` on `pipeline-dbt`, both
    hosts, after the guide gains the rules the ports taught (the clause in
    P2's done-when); the guide fixes under `docs/harnesses/write.mdx`.
21. **S3 in the suite.** The `s3` entry in `suite.json`, `s3_ports.py
    --rederive` over the archives, `tests/semantic/reports/s3-1.md`, the
    README's section.
22. **The docs' sentences.** `docs/harnesses/use.mdx` names the two bundled
    harnesses and what each is for; the reference's bundled-name row shows
    a real name; each harness's README says what it ships and where it
    came from.
23. **The pull-request review.** Cross-model, the findings fixed or
    answered here; the status rows.

## Tests

- **Syntactic.** `tests/harness/test_bundled.py` (check green, listed,
  resolved); `tests/harness/test_bundled_abstraction.py` (the scan: a
  planted task name, a planted score and a planted foreign path are each
  one finding; the shipped trees are clean); `tests/harness/test_bundled_hooks.py`
  (every bundled hook on both hosts' event shapes, allow and deny);
  `tests/harness/test_bundled_scripts.py` (the sanitizer, the scan, the
  fetch, the kernel-slots server on fixtures); `tests/test_benchmark_runners.py`
  (each runner's solve path with `build()` mocked: the brief's facts, the
  harness, the evaluation directory, no domain prose); the moved RelBench
  and IOAI tests; `tests/test_book_to_bank.py` (the conversion on the
  fixture book). Each pins a contract a user would hit; none exercises a
  mock alone.
- **Proof run.** The four reproductions (changes 7, 10, 13, 17), each on
  a benchmark machine, archived one file per run under
  `scripts/redesign/runs/s3-<benchmark>-<n>/` (ignored by git, linked from
  the records below), the record in this plan: the score and the band, the
  harness at work in the trace, the cards served, the cost and the hours.
- **Semantic hooks.** S3 complete: non-regression on all four, the scan at
  zero hits, the four swaps at zero edits, the author test at zero
  structural guesses; `tests/semantic/reports/s3-1.md`.

## Acceptance

- `kapso harness list` names `predictive-modelling` and
  `competitive-programming`; `kapso harness check` on each reports zero
  failures and zero warnings and the needs per module.
- No page over forty lines; every skill named on its module's page; no
  evaluator, dataset, goal, budget, credential, model or runner choice, or
  engine field in either harness; the scan at zero hits; the Codex review's
  scores recorded with the revision that answered them.
- Each benchmark runner launches `build()` with its harness and the record
  carries the harness; the handlers and `context.py` hold no domain prose
  (the notes' names are gone from `benchmarks/`).
- Four reproductions recorded: RelBench within its band or above with the
  bank's cards served; MLE, ALE and IOAI with valid scores at the budget
  (the first two as new baselines, said as such), IOAI with zero shell
  submits and the book's cards pulled; every trace showing pages, skills,
  the delegate's reports and hooks fired.
- The task swaps at zero edits, or each edit a recorded finding fixed at
  the source.
- The author test at zero structural guesses on both hosts after the
  guide fixes.
- The IOAI bank: two verified copies of the backup, a verdict per entry in
  `PROVENANCE.md`, the shareable bank holding only shippable and our own
  entries, the local-only bank apart, nothing of the book in the harness
  beyond the ten twists.
- The gate green at every merge; the docs checks; MASTER's row; the
  pull-request review answered.

## Risks

- **One run per task is noisy.** A miss inside the task's recorded spread
  is not a regression; a miss outside it reopens the port. The record
  names the spread it used. The smoke arm before each full arm catches a
  harness fault at a tenth of the cost.
- **GPU availability and preemption.** Spot H100s and A100s in the credit
  project's zones; the machine script tries the zones in turn; RelBench's
  durable-clock checkpoint survives a preemption and resumes with the
  harness hash checked.
- **The Kaggle side.** A practice competition's quota and the account's
  session limits bound the IOAI arm; the server's ledger holds them; the
  arm is recorded as run, quota included.
- **No recorded MLE or ALE result in the tree.** Said in the record: the
  runs establish the baselines; the non-regression claim for those two is
  "a valid score at the budget", not "within noise of a number the tree
  does not hold".
- **The bank conversion's grammar.** The frame's conformance rules run at
  learn time; a bank read by reference is checked for its layout. The
  conversion writes every field the grammar names anyway, and the IOAI arm
  proves the cards serve (the pull log names them).
- **The harness server's task root.** `kernel-slots` reads the ledger
  under the campaign and the quota from the file the setup session writes
  under `prepared/`; settled in change 14 with a test on the staged shape.
- **Time.** Three to four days with the runs overlapping; the hours table
  shows slippage as it happens.

## Review

The plan review (cross-model, before building) and the pull-request
review, with each finding answered, are recorded here as they land. The
owner's go for the package is the full-path timeline of 2026-10-28.

## Hours

| Change | Estimate | As run |
|---|---|---|
| 1–2 rows, the bundled root under test | 1 h | |
| 3–5 predictive-modelling from RelBench, reviewed | 6 h | |
| 6–7 the RelBench runner and reproduction | 3 h + the run (12 h wall) | |
| 8–10 MLE into the harness, runner, reproduction | 4 h + the run (9 h wall) | |
| 11–13 competitive-programming from ALE, runner, reproduction | 5 h + the run (4 h wall) | |
| 14–17 IOAI into the harness, runner, bank, reproduction | 8 h + the run (3 h wall) | |
| 18–19 the scan and the swaps | 3 h + four short arms | |
| 20–21 the author test again, S3 in the suite | 3 h + two arms | |
| 22–23 the docs' sentences, the PR review | 4 h | |
