# The redesign: master implementation plan

2026-10-24. The *what* is `docs/research/redesign-status.md`; this is the
*how*: the work packages, their dependencies, the tests each one carries
and the tests that wait for the end, the branch and release shape, and the
method every package follows. Each package gets a sub-plan in this
directory, written from `TEMPLATE.md` when the package is next, reviewed,
and only then built. `wp1-build.md` is the first and the model.

## 1. The shape of the work

**One integration branch, one release.** The redesign renames `evolve` to
`build`, retires modes and `serving.enabled`, and replaces `SolutionResult`.
Landed piecemeal on `main`, which releases often and pushes every commit,
that would break released users every week. So: an integration branch
`redesign`, cut from today's `kapso-plugin` branch; one branch per work
package merged into it by pull request with the gate green; `main` merged
into `redesign` weekly to absorb fixes; and `redesign` merged into `main`
once, as the release, when the full semantic suite passes on a fresh
machine. No compatibility shims at any point (CLAUDE.md rule 7); the
release notes carry the rename.

**Disjoint ownership so packages run in parallel.** The facade
(`src/kapso/kapso.py`, 1,933 lines) and the CLI (`src/kapso/cli.py`, 1,330
lines) would be touched by six packages. WP0 splits the CLI into one module
per verb and moves the handles out of the facade, so that after it each
package owns files no other package edits. The ownership column below is
the rule; a package that needs a file it does not own asks, in its
sub-plan, for an interface from the owner.

**Plan the next step in detail, the rest to its interfaces.** Sub-plans
for packages two steps ahead would be rewritten; what the master fixes
now is each package's scope, the interface it exposes, what it depends on
and what proves it done.

## 2. Work packages

| WP | Name | Scope in one line | Owns | Depends on | Size |
|---|---|---|---|---|---|
| 0 | Foundations | the `redesign` branch; the CLI split into `src/kapso/cli/<verb>.py` and the handles module; the fresh-machine provisioning script; the semantic suite's skeleton | `src/kapso/cli/`, `scripts/redesign/`, `tests/semantic/` skeleton | none | S |
| 1 | `build` | `Brief`, `Budget`, `Solution`, `Software`, `Experience`; `Kapso.build()` replacing `evolve()`; `kapso build`; `Solution.open`; the rename in code, tests and skills | `src/kapso/handles.py`, the build section of the facade, `src/kapso/cli/build.py`, `skills/` | 0 | M |
| 2 | Harness package | reference grammar and store; `check`; content hash in the record; staging per module (pages, skills, servers, delegates, merged hooks); prepared resources; prerequisite refusal; `kapso harness new\|check\|list\|add\|update\|remove\|export`; `--harness` on the three verbs | `src/kapso/harness/`, `src/kapso/cli/harness.py`, the staging seams in sessions and prompt assembly | 1 | L |
| 3 | Experience | reference grammar and homes; `load_experience`, `add_experience`; `kapso experience add\|list\|share`; provenance intro; scope rule; `serving.enabled` removed; `kapso bank`, `learn init-bank`, `learn_knowledge`, `research`, `index_kg` retired into it | `src/kapso/experience/`, `src/kapso/cli/experience.py`, the serving layer | 1, 2 (scope) | M |
| 4 | Config without modes | packaged defaults plus one override file; `modes` and the `mode` argument gone; `design_axes` deleted with the planner reading the ideation page and the goal; `additional_context` and handler prose retired; `implementation_web` a hook; benchmark configs as override files; `doctor` prints the effective config | `src/kapso/core/config.py`, `config.yaml`, strategy parameter reading, `benchmarks/*/config.yaml` | 2 | M |
| 5 | Deploy | the `target` argument with the config default; the five bundled targets as skills with their scripts | `src/kapso/deployment/`, `src/kapso/cli/deploy.py` | 2 | M |
| 6 | Observability | `kapso trace` text and `--json`; `doctor --json`; the registry's liveness filter; the harness in the status header; hook decisions, delegate reports and verification evidence in the record from both CLIs' transcripts | `src/kapso/cli/trace.py`, `doctor.py`, `watch.py`, the record writers | 1, 2 | M |
| 7 | Plugin | the `plugin/` tree, manifests, launcher, marketplace files; the commands; the six skills with sidecars; session-start brief; delegation tools; skill lab re-run; the authoring interview | `plugin/`, `.claude-plugin/`, `.agents/plugins/` | 1, 2, 3, 6 | L |
| 8 | Harness ports | `predictive-modelling` from RelBench then MLE; `competitive-programming` from ALE then IOAI; banks; cross-checks (per `initial-harnesses-plan.md`; parked until the owner says go) | `src/kapso/harnesses/`, `benchmarks/` runners | 2, 3, 4 | XL |
| 9 | Semantic suite | fixtures (the examples), persona cards, the simulated-user driver, the judge, the report; S1 to S6; GCP provisioning | `tests/semantic/`, `scripts/redesign/` | 0; each S on its WP | M, spread |
| 10 | Docs and examples | the new navigation and pages; examples as tasks on harnesses; the drift check and the two lints (per `docs-and-examples-redesign.md`) | `docs/`, `docs.json`, `examples/`, `scripts/` | each section on its WP | L, spread |
| 11 | Release | version, changelog and release notes, PyPI, the docs site, the marketplace tag; the full semantic suite as the gate | | all | S |

Sizes: S under a week, M one to two weeks, L two to three weeks, XL
longer and GPU-bound. Estimates, not commitments; each sub-plan refines
its own.

## 3. Dependencies and tracks

```
WP0 ─ WP1 ─┬─ WP2 ─┬─ WP3 ──────┐
           │       ├─ WP4       ├─ WP7 ─┐
           │       ├─ WP5       │       ├─ WP11
           ├─ WP6 ─┴────────────┘       │
           │                            │
           └─ WP9 (S1 at 1, author test at 2, S4/S5 at 6, S2 at 7, S6 at 3+8, S3 at 8)
           └─ WP10 (Start/Build at 1, Harnesses at 2, Experience at 3, Deploy/trace at 5+6, plugin page at 7)
WP8 ─ after 2, 3, 4; parked
```

The spine is WP0 then WP1, serial: everything records against a
`Solution`. After WP1 four tracks run in parallel: **A** WP2 then WP5 (and
WP8 when unparked); **B** WP3, whose grammar and homes start beside WP2
and whose scope rule waits for WP2's manifest; **C** WP6, then WP4 once
WP2's pages exist; **D** WP9 and WP10, which start on day one with their
skeletons and grow one section per landed package. WP7 starts when A, B
and C have delivered their first interfaces and finishes last before the
release. The critical path is WP0, WP1, WP2, WP7, S2, WP11; WP2 and WP7
are the long poles.

## 4. Tests: what each package carries, what waits for the end

**Syntactic, every package.** Unit tests for each new module; contract
tests for each schema and grammar (negative cases included: unknown key,
unresolved reference, secret literal, malformed hook); integration tests
with the provider boundary mocked, asserting the shapes a module produces;
goldens for staged trees, rendered traces and records. They join the
curated gate, which stays green at every merge, with the CI invocation
unchanged. No live-provider test inside the gate.

**Proof run, every package.** One live run at a tiny budget on the fresh
machine, exercising the package end to end: the churn fixture for WP1, the
trading example on both CLIs for WP2 (where the two unverified Codex
facts, MCP tool naming in hook matchers and `stop_hook_active`, get
settled), a served card for WP3, a deploy for WP5, a trace for WP6, the
plugin round for WP7. Its campaign directory is archived, one file per
run, and linked from the sub-plan.

**Semantic, early where it can be.** S1 on today's `main` before WP1
starts, as the baseline the redesign is measured against; S1 again after
WP1 and WP10's Start and Build pages; the guide's author test when WP2's
`check` exists; S4 and S5 when WP6 lands; S2 one scenario step per skill
as WP7 lands them; S6 when WP3 serves and a second build exists.

**Semantic, in full, at the end.** The release gate is S1 to S6 complete,
both hosts, on a fresh machine, from the wheel that will be released; S3's
non-regression runs with WP8 when it is unparked. Anything that fails there
reopens its package.

**Reviews.** Every sub-plan and every pull request gets a cross-model
review before merge (the house practice: Codex at high effort), with the
findings answered in the plan or the PR. Four checkpoints with the owner:
after WP1 (the handle shapes become final and the interface document is
rewritten), mid-WP2 (host facts verified), after WP7 (the plugin on both
hosts), and before the release.

## 5. The method, per package

1. Write the sub-plan from `TEMPLATE.md`: scope and non-scope, the
   interface it exposes and consumes, file ownership, the change list,
   the tests, the proof run, acceptance, risks, estimate. Review it. The
   owner says go.
2. Build on a worktree branch off `redesign`; commit per change with its
   tests and docs; the gate green locally before every push.
3. Run the proof run on the fresh machine; archive it.
4. Run the package's semantic hooks; record the numbers in the sub-plan.
5. Land the package's section of the docs and examples (WP10's slice).
6. Pull request into `redesign` with the review; merge when green.
7. Update the status table in this file.

## 6. Status

| WP | Sub-plan | State |
|---|---|---|
| 0 | to write | |
| 1 | `wp1-build.md` | planned |
| 2 to 11 | to write when next | |

## 7. Risks

| Risk | Mitigation |
|---|---|
| the rename breaks released users | one release from the integration branch, release notes with the mapping, no piecemeal landing |
| Codex hook facts unverified (MCP matcher names, `stop_hook_active`) | settled in WP2's proof run; the staging layer rewrites matchers per host if needed |
| the facade and CLI as merge hot spots | WP0's split and the ownership column; interfaces frozen in sub-plans before parallel work |
| benchmark configs and runners break when modes go | WP4 converts them with a runner smoke test per benchmark; WP8 is the full reproduction |
| model-token limits throttle proof and semantic runs | the token gates already in use (probe the CLI per model before launching; the 7-day rule) |
| the IOAI bank's provenance | WP8, after the backup and the licence pass; local source only until then |
| scope creep toward the live UI | out of the first release by decision; the master lists no package for it |
| estimates | each sub-plan refines its own; the status table shows slippage early |
