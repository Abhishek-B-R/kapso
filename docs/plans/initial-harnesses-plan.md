# The two initial harnesses: plan

2026-10-24. The port mapping is `docs/research/harness-ports.md`; this is
the order of work, what each step takes from where, and what proves it
done. The harnesses are `predictive-modelling` (RelBench, MLE-bench) and
`competitive-programming` (ALE-bench, IOAI). They start after build steps
1 to 3 of `docs/research/redesign-status.md` exist: `build`, the harness
package with staging and `check`, and `load_experience`.

## Order

RelBench first, because it has the most written domain material and the
only learned bank, so one port exercises pages, skills, hooks, a delegate,
prepared resources and experience together. MLE-bench second, into the same
harness, as the first test that the abstraction holds. ALE third, the
smaller contest port. IOAI fourth, with its server and its bank.

## P1. `predictive-modelling` from RelBench

| Part | Written from |
|---|---|
| `guardrails.md` | the data-access rules and iteration protocol in `benchmarks/relbench/context.py`; the test set never trains; no row after its seed time |
| `setup.md` | the sanitized cache as `prepared/cache`; the regime (frozen-db or seed-time) from `EVALUATION_PROTOCOL.md` into the statement |
| `ideation.md` | the five axes verbatim from the config's `design_axes` |
| `implementation.md` | `FEATURE_ENGINEERING_NOTE`, the modelling practices, the rolling contract |
| `verification.md` | the static audit, the `upto_test_timestamp` trap, validation that looks fine while test is stripped |
| `feedback.md` | the per-axis frontier; ship nothing below the reproduced champion |
| `learning.md` | scope by dataset, task and temporal regime |
| skills | `sanitize-cache` (script from `sandbox.py`), `temporal-protocol`, `relational-feature-practices` (the eight practices), `relbench-api`, `torch-frame`, `living-documents`, `leakage-scan` (script from the audit greps), `cv-protocol` |
| delegate | `leakage-auditor` |
| hooks | `protect-prepared`, `deny-web-fetch` on implementation and verification |

The runner becomes task selection plus `kapso build --harness
predictive-modelling` plus final scoring; the grader, the starter kit's
contract and the raw cache stay with it. The RelBench bank is added as an
experience source by reference.

Done when: `check` is green with no warnings; one banked RelBench task
reproduces its recorded score within noise at the same budget and model;
the abstraction scan (section P5) finds no RelBench constant in the
harness; the bank loads and the trace shows its cards served.

## P2. MLE-bench into the same harness

| Part | Written from |
|---|---|
| `setup.md` additions | profile the data; fetch candidate models and datasets from the hub in setup; the statement records task type, metric, splits, data size, compute |
| `ideation.md` and `implementation.md` additions | the three stages by budget progress; stratified subsample first; epoch times printed; heavy ensembles last |
| `feedback.md` addition | stage-aware scoring |
| skills | `task-type-playbooks` (one reference per workflow in `benchmarks/mle/data/kg_data.json`, code examples kept), `hf-model-fetch`, `ensembling`, `tabular-modeling` |

The tip sheet in `kg_data.json` is reviewed line by line; what contradicts
the guardrails is dropped. The MLE runner becomes a thin entry point.

Done when: one lite competition reproduces its recorded result; the MLE
port required no RelBench-shaped change to the harness, or the change was
a page sentence and the guide gained the rule that would have prevented it.

## P3. `competitive-programming` from ALE-bench

| Part | Written from |
|---|---|
| `guardrails.md` | the official scorer is the score; the time limit is the task's; a failing seed fails |
| `setup.md` | build the task root: statement, local scorer, test cases, baseline |
| `ideation.md` | axes: algorithm family, state representation, neighbourhood and move design, time allocation, multi-strategy by input condition |
| `implementation.md` | the efficiency rules from the handler's domain knowledge |
| `verification.md` | the scorer on every seed, the time limit, the baseline |
| skills | `heuristic-patterns` (the handler's prose, sectioned), `cpp-performance`, `scorer-cli` |
| delegate | `score-auditor` |
| hooks | `require-scorer-run` (Stop) |

Done when: one AHC problem reproduces its recorded rating-level result at
the same budget; `check` green; no problem constant in the harness.

## P4. IOAI into the same harness

| Part | Written from |
|---|---|
| `guardrails.md` additions | `RULES.md`: the statement's quota, the report docstring, the leaderboard as arbiter |
| `setup.md` addition | the preflight from `preflight_spec.md`: URL or starter prompt to data, `kaggle.json` and a complete statement |
| `implementation.md` additions | the insurance submission, the time-allocation plan, confirm-gain discipline, harvest before the end |
| `verification.md` addition | the kernel audit; CV inflation against the public score |
| `feedback.md` additions | time-to-first-strong-score, critical-path velocity, confirmation overhead, the ceiling proof |
| skills | `kaggle-cli` (from `KAGGLE_CLI.md`), `contest-preflight`, `contest-economics` (handler plus `RUN_FINDINGS.md`), `olympiad-playbook` (the book index's router) |
| delegate | `submission-auditor` |
| server | `kernel-slots` from `kernel_slots.py` |
| hooks | `deny-shell-submit`, `require-insurance` (Stop on implementation) |

Before the bank: back up `benchmarks/kaggle/knowledge_bank/` and its
reserve from the `ioai-2025` worktree (they exist nowhere else), then the
provenance pass; then `kapso experience add --dir ... --name ioai-book`.

Done when: one practice task reproduces a public score at or above the
recorded cold start at the same budget, with zero shell-level submits in
the trace; the bank serves through the playbook skill.

## P5. Cross-checks, run after P2 and after P4

- **Abstraction scan**: a script that fails on any benchmark constant in a
  harness: dataset and task names, metric values, quotas, deadlines, paths
  outside the harness's own conventions. Run by `check` for shipped
  harnesses.
- **Task swap**: a task from the domain that the benchmark does not
  contain, run without a harness edit: a Kaggle tabular competition for
  `predictive-modelling`, a second AHC problem and an IOAI 2025 task for
  `competitive-programming`. An edit needed to run is a finding against
  the harness or the guide, recorded and fixed.
- **Third-domain author test** (the guideline's test, defined in
  `semantic-production-tests.md` S3): an author with only the guide, the
  design and the trading example writes a harness for data pipelines.

## What it costs

RelBench and MLE need the GPU boxes the benchmarks already use; ALE needs
the Docker scorer; IOAI needs the Kaggle account and one practice
competition. One reproduction run per benchmark, at the benchmark's own
budget, is the price of each "done when" line.
