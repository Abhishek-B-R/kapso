# WP10: docs and examples

2026-10-29. Owner: the redesign's builder. Branch `wp10-docs-examples` off `redesign` after WP8 merges (its pages land on top of WP8's benchmark pages). Size: one day, the owner's Saturday target in view; the cross-model review of this plan runs while the first change is built.

## Scope

The docs site reads as `docs/plans/docs-and-examples-redesign.md` lays it out: the navigation organised by what the reader is doing, the pages each earlier package landed kept, the sections the design condenses condensed (Learn from six pages to two; How it works from fourteen to four), the bundled harnesses with a page each, the plugin's commands in the reference, every retired path redirected. The examples hold one shape and one table, the full loop restated as one example, and the public pages pass the design's two lints beside the drift check that exists.

**Not in scope.** The four domain examples' harnesses (`gpu-kernels`, `torch-performance`, `prompt-harness`, `agent-scaffold`): each is a domain harness under the owner's harness rule (an expert mental model from research, a review, a revision), days of work apiece, so those four examples stay as they run today, their README saying so, and their harnesses are a follow-up after the release (a decision in DECISIONS). The release itself (WP11). New engine behaviour of any kind. The S1 run of every example on a fresh machine (WP11's gate).

## Interface

### What this package exposes

- **The navigation** (`docs.json`): tab Documentation with the groups Start, Build, Harnesses, Experience, Deploy, Learn, How it works, Benchmarks; tab API Reference with Python API, CLI, Config, Brief format, Harness formats, Experience, Plugin commands. Every page path retired by a merge is in `docs.json`'s `redirects` to its new home, so a link that worked yesterday lands on the page that absorbed it.
- **The Learn group**: `docs/learn/what-learn-produces.mdx` (cards with receipts: the card, its reliability states, how a campaign becomes a lesson, serving as an introduction with the three tools) and `docs/learn/development-mode.mdx` (the pipeline's four stages, the graders' two layers and the gauntlet, the promotion gates and codify), condensed from today's six learning pages, whose paths redirect.
- **The How-it-works group**: `docs/how-it-works/engine-modules.mdx` (the orchestrator, the strategy, the handler, the sessions, the gates, repo memory, the budget: one page from overview, architecture, execution-flow, orchestrator, experiment-lifecycle, mcp-gates, repo-memory), `docs/how-it-works/evaluation-integrity.mdx` (today's page, moved), `docs/how-it-works/record-and-trace.mdx` (the campaign's record and `kapso trace`, from `build/trace` which stays as the Build page and links here), `docs/how-it-works/search.mdx` (strategies, parent selection, cost-aware selection, model routing and retries, the coding agents, the feedback generator: one page from six). The Evolve paths redirect; the Components subgroup goes.
- **The Harnesses group**: `docs/harnesses/bundled/predictive-modelling.mdx` and `docs/harnesses/bundled/competitive-programming.mdx` (what each ships, where it came from, the modules and skills, the hooks, how to run a task on it), placed between Use and Write.
- **The reference**: `docs/reference/plugin-commands.mdx` (the ten commands and the six skills, each with its one line and what it asks), listed in API Reference; `check_docs_coverage.py` learns the plugin commands as a surface (the file list under `plugin/commands/`).
- **The examples**: `examples/full-loop/` (today's `ml_model_development`, renamed; the README in the four sections; `run.py` the twelve-line build, review, learn, build again with experience, deploy); `examples/README.md` the one table with minutes and the one command per row, the four domain examples marked "runs today; its harness is a follow-up"; every example's README under eighty lines in the four sections.
- **The lints**: `scripts/check_claims.py`, two rules over the public pages (`docs/**/*.mdx`, `README.md`): a word of the words-out list (`docs/research/kapso-redesign.md`'s list, read from one data file `scripts/words_out.txt` the lint owns) outside a fenced block fails; a number adjacent to a metric word (AUROC, accuracy, F1, MAE, log loss, score, rank, MAP, NMAE, percent) with no provenance within its paragraph (a parenthesis or sentence naming who ran it, on what, when, or a link to a benchmark page that does) fails; the allow-list is the benchmark pages' own tables, which carry provenance in a column. Wired into `.github/workflows/docs.yml` beside the drift check.

### What this package consumes

WP1–WP8's pages as landed; the drift check (`scripts/check_snippets.py`), the coverage check and the GEO check as they run in CI; the examples as WP9 left them (short drivers, the semantic fixtures); the design document.

## Ownership

Edits: `docs/` (pages, `docs.json`), `examples/` (`full-loop`, the README, the four domain examples' READMEs), `scripts/check_claims.py`, `scripts/words_out.txt`, `scripts/check_docs_coverage.py`, `.github/workflows/docs.yml`, `tests/test_check_claims.py`, `tests/test_docs_navigation.py`. Reads, never edits: `src/` (the surface the coverage check reads), `tests/semantic/` (WP9's), `benchmarks/` (WP8's pages come from there).

## Changes

1. **The plan and its review**: this file; `scripts/redesign/review.sh` on a brief naming the design, the current navigation and the plan; the findings answered here before change 3 lands.
2. **The lints**: `scripts/check_claims.py` with `scripts/words_out.txt`, `tests/test_check_claims.py` (a fixture page per rule: the banned word in prose fails, in a fence passes; a bare metric number fails, one with provenance passes, a benchmark table row passes), the CI step. Run over the tree; every hit fixed on its page in the same commit.
3. **Learn condensed**: the two pages written from the six; `docs.json` group and redirects; `tests/test_docs_navigation.py` (every retired path redirects; every page in the navigation exists; no page outside the navigation).
4. **How it works condensed**: the four pages from the fourteen; the Components subgroup removed; redirects.
5. **The bundled harness pages** and the Harnesses group order; **Plugin commands** in the reference with the coverage check extended.
6. **Start and Experience named per the design**: `agent-access` merged into `coding-agent-skills` as "Kapso in your coding agent" with a redirect; the Experience pages' sidebar titles per the design (What experience is, Your bank, Leeroopedia and indexes, Provenance as a section of the first).
7. **The examples**: `full-loop` from `ml_model_development` (the rename in the examples' tests and the semantic fixtures' references), its README and driver; the examples table; the four domain READMEs' line.
8. **The docs checks green** (`mint validate`, `broken-links`, coverage, snippets, GEO, claims) and the gate; the pull-request review (cross-model), answered here; the merge into `redesign`.

## Tests

- Syntactic: `tests/test_check_claims.py` (the two rules on fixtures, the fence exemption, the provenance forms), `tests/test_docs_navigation.py` (the navigation's pages exist, every page is listed once, every retired path redirects to an existing page), the coverage check's plugin surface (a command file without its reference line fails).
- Proof run: the docs workflow's six checks green on the branch; a `mint dev` render of the new navigation read once by the builder.
- Semantic hooks: none new; S1 (WP11's gate) runs every example's driver, including `full-loop`, from the released wheel.

## Acceptance

- The navigation matches the design's two tabs and groups; every page the design names exists or is named here as deferred; every retired path redirects.
- Learn is two pages and How it works four, each under 250 lines, nothing of the retired pages lost that the design keeps (the condensation table in the Review section says where each section went).
- Both bundled harnesses have a page; the plugin's commands are in the reference and the coverage check knows them.
- `examples/README.md` is one table; `full-loop` runs under twelve lines; the four domain examples say what they are.
- The two lints run in CI and the tree passes them; the drift check still passes.
- The pull-request review answered; the gate green; the merge.

## Risks

- **Condensing loses a fact a reader needs.** Each retired page's sections are mapped in the Review table before deletion; the coverage check keeps the reference whole.
- **The lints false-positive on legitimate prose.** The provenance forms are listed and tested; a benchmark table carries provenance in a column and is allowed as such; a hit is fixed on the page, never by widening the allow-list without a note here.
- **Time.** One day; the review runs in parallel with change 2; the examples' four follow-ups are out of scope by decision.

## Review

(The cross-model review's findings and their answers; the condensation table.)
