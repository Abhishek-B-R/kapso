# WP10: docs and examples

2026-10-29. Owner: the redesign's builder. Branch `wp10-docs-examples`, branched from WP8's tip (its pages sit on WP8's benchmark pages) and rebased onto `redesign` when WP8 merges; built in the same worktree by switching branches at each commit. Size: two days (the review priced the first estimate three short; the cut below brings it to two), the owner's Saturday target in view.

## Scope

The docs site reads as `docs/plans/docs-and-examples-redesign.md` lays it out: the navigation organised by what the reader is doing, the pages each earlier package landed kept, Learn condensed from six pages to two, How it works kept as its fifteen pages with a truth pass and a flat group (the condensation deferred past the release: the review's cut order, and the design's own principle that a section ships when its verbs do), the bundled harnesses with a page each, every retired path redirected without chains, the benchmark pages' numbers with their provenance. The examples hold one shape and one table under the design's names, the full loop restated as one example, every driver checked, and the public pages, the README and the examples' READMEs pass the design's two lints beside the drift check that exists.

**Not in scope.** The four domain examples' harnesses (`gpu-kernels`, `torch-performance`, `prompt-harness`, `agent-scaffold`): each is a domain harness under the owner's harness rule (an expert mental model from research, a review, a revision), days of work apiece, so those four examples run as they do today under the design's names, their README saying so and that their evaluator still sits inside `repo/`, and their harnesses are a follow-up after the release (DECISIONS). The How-it-works condensation (fifteen pages to four), deferred past the release with its must-survive list recorded in the Review (finding 8). A `plugin-commands` reference page: the plugin page's two tables are the one copy, and the coverage check reads them. A recorded result for `full-loop` (one live run of two builds, a learn and a deploy; the README says "not recorded yet" until it exists). The release itself (WP11). New engine behaviour of any kind.

## Interface

### What this package exposes

- **The navigation** (`docs.json`): tab Documentation with the groups Start, Build, Harnesses, Experience, Deploy, Learn, How it works, Benchmarks; tab API Reference with Python API, CLI, Config, Brief format, Harness formats, Experience, Plugin commands. Every page path retired by a merge is in `docs.json`'s `redirects` to its new home, so a link that worked yesterday lands on the page that absorbed it.
- **The Learn group**: `docs/learn/what-learn-produces.mdx` (cards with receipts: the card, its reliability states, how a campaign becomes a lesson, serving as an introduction with the three tools) and `docs/learn/development-mode.mdx` (the pipeline's four stages, the graders' two layers and the gauntlet, the promotion gates and codify), condensed from today's six learning pages, whose paths redirect.
- **The How-it-works group**: today's fifteen `docs/evolve/*` pages, in one flat group, after a truth pass (the CLI package named as it is, the resolved config in place of a mode layer, no "both shipped modes", no compatibility paragraph). `build/trace` stays in Build. The condensation to four pages is deferred (Not in scope).
- **The Harnesses group**: `docs/harnesses/bundled/predictive-modelling.mdx` and `docs/harnesses/bundled/competitive-programming.mdx` (what each ships, where it came from, the modules and skills, the hooks, how to run a task on it), placed between Use and Write.
- **The reference**: no new page; `check_docs_coverage.py` learns the plugin commands as a surface (the file list under `plugin/commands/`) and reads them off `docs/coding-agent-skills.mdx`'s table, the one copy.
- **The examples**: `examples/full-loop/` (today's `ml_model_development`, renamed; the README in the four sections saying "not recorded yet"; `run.py` the twelve-line build, review, learn, build again with experience, deploy; `run_full_loop.py`, `resume_full_loop.py`, `run_cli_inference_smoke.py` and `e2e/` deleted with their rows in `tests/test_config_resolution.py` and `.gitignore`); the four domain examples renamed to the design's names (`gpu-kernels`, `torch-performance`, `prompt-harness`, `agent-scaffold`); `examples/README.md` the one table with minutes, the one command and whether a result is recorded per row, `pipeline-dbt` in it, the four domain examples marked "runs today; its evaluator sits inside repo/; its harness is a follow-up"; `tests/test_examples_drivers.py`: every `examples/*/run.py` compiles, holds at most twelve lines of code, and names only flags and keywords the CLI and the API expose.
- **The lints**: `scripts/check_claims.py`, two rules over the public pages (`docs/**/*.mdx`, `README.md`, `examples/*/README.md`): a phrase of the words-out list (`scripts/words_out.txt`, from `docs/research/kapso-redesign.md`'s rules for every public sentence) in prose fails — the list in two sections, phrases out everywhere and phrases out on the front pages only (`judge` and `trust`, which are also the engine's role and a host's trust line that the inner pages must name); prose is everything outside code fences and inline code, and a `text` or `md` fence is prose; a result (two or more decimals, or a percentage) beside a metric word with no provenance in its paragraph fails, provenance being a word naming who ran it, on what or when, a row of a table whose header names its source, or a target marked expected or not measured; headings are not prose and a one-decimal threshold is a rule, not a result. Wired into `.github/workflows/docs.yml` beside the drift check, with the workflow triggering on every file the checks guard.

### What this package consumes

WP1–WP8's pages as landed; the drift check (`scripts/check_snippets.py`), the coverage check and the GEO check as they run in CI; the examples as WP9 left them (short drivers, the semantic fixtures); the design document.

## Ownership

Edits: `docs/` (pages, `docs.json`, `docs/README.md`), `README.md`, `examples/` (`full-loop`, the four renames, the README, the READMEs), `scripts/check_claims.py`, `scripts/words_out.txt`, `scripts/check_docs_coverage.py`, `.github/workflows/docs.yml`, `.gitignore` (the retired drivers' rows), `tests/test_check_claims.py`, `tests/test_docs_navigation.py`, `tests/test_examples_drivers.py`, `tests/test_config_resolution.py` (WP4's three `e2e/config.*.yaml` rows, retired with the drivers), `plugin/skills/kapso/SKILL.md` (one link), `pyproject.toml` (the project URLs, with WP11's release). Reads, never edits: `src/` (the surface the coverage check reads), `tests/semantic/` (WP9's), `benchmarks/` (WP8's pages come from there).

## Changes

1. **The plan and its review**: this file; `scripts/redesign/review.sh` on a brief naming the design, the current navigation and the plan; the findings answered here. Done 2026-10-29: the Claude half (27 findings, below); the Codex half waits for a login with quota.
2. **The lints**: `scripts/check_claims.py` with `scripts/words_out.txt`, `tests/test_check_claims.py`, the CI step; every hit fixed on its page. Done 2026-10-29 (`aa75483c`, refined in change 4's commit after the review): eleven hits, the front pages' one-liner and the README's heading among them (the owner may veto the wording).
3. **Learn condensed**: the two pages from the six; `docs.json` and redirects; `tests/test_docs_navigation.py`; every link rewritten. Done 2026-10-29 (`6d8e07b5`).
4. **How it works kept, with a truth pass**: the stale lines corrected, the Components subgroup flattened, the links outside the docs pages rewritten; the lint's refinements and the workflow's triggers ride with it. Done 2026-10-29.
5. **The bundled harness pages** and the Harnesses group order. Done 2026-10-29: `docs/harnesses/bundled/predictive-modelling.mdx` and `competitive-programming.mdx` (what each ships from its manifest and its live `check` line, where it came from, the per-module table, the skills, the delegates, the hooks, the environment, how to run a task on it with the runners' lines), placed between Use and Write; the overview's cards and the use page link to them; `docs/README.md`'s Pages section regenerated from `docs.json` (it had kept three retired groups and lacked three live ones).
6. **The coverage check's plugin surface** (`plugin/commands/` read off the plugin page's table). Done 2026-10-29: `plugin_commands()` lists the command files, each must appear as `/kapso:<name>` on `docs/coding-agent-skills.mdx`; the check's run is its test, as for the other two surfaces.
7. **Start and Experience named per the design**: `agent-access` merged into `coding-agent-skills` as "Kapso in your coding agent" with a redirect, keeping the docs MCP server lines per host and the `llms.txt` rendition; the Experience pages' sidebar titles per the design. Done 2026-10-29: the plugin page is "Kapso in your coding agent" with the docs server's three install lines and the Markdown rendition as a section, `agent-access` deleted behind a redirect (the navigation test pins it), the README's link moved; the Experience sidebar reads What experience is, Your bank on a build, Leeroopedia and indexes, Share a bank, with a Provenance section on the overview.
8. **The benchmark pages' provenance**: one paragraph per table saying who ran it, on what and when, from WP8's records.
9. **The examples**: `full-loop` from `ml_model_development` with its old drivers deleted, the four renames, the table, `tests/test_examples_drivers.py`.
10. **The docs checks green** (`mint validate`, `broken-links`, coverage, snippets, GEO, claims) and the gate; the pull-request review (cross-model), answered here; the rebase onto `redesign` once WP8 merges; the merge.

## Tests

- Syntactic: `tests/test_check_claims.py` (the two rules on fixtures, the fence rules, the provenance forms, the shipped pages clean), `tests/test_docs_navigation.py` (the navigation's pages exist, every page is listed once, every redirect lands on a page that exists without chaining, the retired paths redirect), `tests/test_examples_drivers.py` (every driver compiles, is twelve lines or fewer, names real flags), the coverage check's plugin surface (a command file without its line on the plugin page fails).
- Proof run: the docs workflow's six checks green on the branch; a `mint dev` render of the navigation read once by the builder.
- Semantic hooks: none new. S1 runs its six tasks on the fixtures the suite names (churn, fraud, empty-wish, trading, pipeline-dbt), not every example; the drivers' check above is what WP10 owns for the rest.

## Acceptance

- The navigation matches the design's two tabs and groups; every page the design names exists or is named here as deferred; every redirect lands on a page that exists.
- Learn is two pages, each under 250 lines, every H2 of the six retired pages placed or dropped with a reason (the table in the Review); How it works is the fifteen pages with the stale lines corrected.
- Both bundled harnesses have a page; the coverage check knows the plugin's commands.
- `examples/README.md` is one table under the design's names; `full-loop` runs under twelve lines and says its result is not recorded; the four domain examples say what they are; every driver passes the drivers' check.
- The benchmark pages' tables carry their provenance.
- The two lints run in CI and the tree passes them; the drift check still passes.
- The pull-request review answered; the gate green; the merge.

## Risks

- **Condensing loses a fact a reader needs.** Each retired page's sections are mapped in the Review table before deletion; the coverage check keeps the reference whole.
- **The lints false-positive on legitimate prose.** The provenance forms are listed and tested; a benchmark table carries provenance in a column and is allowed as such; a hit is fixed on the page, never by widening the allow-list without a note here.
- **Time.** One day; the review runs in parallel with change 2; the examples' four follow-ups are out of scope by decision.

## Review

### The plan review (2026-10-29)

`scripts/redesign/review.sh` on `scripts/redesign/runs/wp10-plan-review/brief.md`: the Claude half (opus-5) returned 27 findings; the Codex half did not run (the development box's Codex login hit its usage limit until 2026-11-04; it runs when a login with quota exists). Every finding by id, with its disposition:

| Id | Finding | Disposition |
|---|---|---|
| 1 | P1: `external-evaluation.mdx` missing from the 14→4 list | moot: the condensation is deferred (26); the page stays in the flat group |
| 2 | P1: nobody owns the benchmark pages' provenance | change 8: one paragraph per table from WP8's records |
| 3 | P2: `mcp-gates`' user section would land in a contributor page | moot (26); noted for the condensation when it comes |
| 4 | P2: the Experience mapping unstated | change 7 names it: `index` "What experience is" (Provenance a section of it), `use` "Your bank on a build", `add` "Leeroopedia and indexes", `share` "Share a bank"; no path changes |
| 5 | P3: two unstated deviations (the reference listed once; `build/trace` kept) | recorded here as deliberate |
| 6 | P2: rename the four domain examples to the design's names; `pipeline-dbt` has no row | change 9 does both |
| 7 | P1: a rewrite priced as a merge; the sources are stale | the condensation is deferred (26); the four stale lines corrected in change 4; every sentence carried into the Learn pages was verified against the tree |
| 8 | P1: name the must-survive facts before deleting | recorded for the deferred condensation: `auth_mode`'s four values and the Bedrock rules, the `oss_claude_code`/`vertex_claude_code` setups, the `openai_compatible` section and its cost warning, the agent table, the XML result-tag contract, the cost estimator contract, the external-evaluation callback contract, the `kapso-mcp` table, the two failure policies — destinations `reference/configuration.mdx`, `reference/kapso-api.mdx`, `reference/cli.mdx`, `build/evaluation.mdx` |
| 9 | P2: thirty-seven links in surviving pages, the mirror, the README, pyproject, the plugin's skill | the Learn links rewritten on nine pages, the mirror and the skill (changes 3, 4); the Evolve links stay live (26); the navigation test gains the shipped files' links in change 9; pyproject's URLs with WP11 |
| 10 | P1: existing redirects pointing at pages this package deletes | the test asserts every destination resolves and no redirect chains; the one such redirect re-pointed (change 3) |
| 11 | P2: redirects cannot carry a fragment | no link used an anchor into the retired Learn pages; the rule stands for the deferred condensation |
| 12 | P3: phrase the listing clause by `.mintignore` | the test reads the tree; `.mintignore` excludes nothing today |
| 13 | P1: `judge` 96 times; the list is positioning copy | the list in two sections: everywhere, and the front pages only for `judge` and `trust` (change 2) |
| 14 | P1: the first run needs the owner's one-liner | the builder's own wording was vetoed by the direction document: the owner pointed at `docs/research/kapso-redesign.md` (2026-10-29, "use that doc as the direction for updating the docs and story telling"); its one-liner is the README's heading and the PyPI summary, its TL;DR is What is Kapso on the README and `docs/index.mdx`, adapted only where the lint or a fact forced it: "judge" left out of the module list (a front-page word out), the harness list cut to the two that ship plus the examples' trading harness, "ready to deploy" for "deployed" (deploy is its own verb) |
| 15 | P2: a `text` fence is prose | done (change 4): text and md fences are prose for the words-out rule |
| 16 | P1: the table allow-list is false of today's pages | the rule reads a table's header for its source column and the paragraph's provenance words; change 8 fixes the IOAI page from WP8's record |
| 17 | P2: the examples' READMEs in rule 2's scope | done (change 4), with "expected" and "not measured" markers allowed |
| 18 | P2: the workflow's triggers | done (change 4): both lists widened |
| 19 | P2: `full-loop` has no recorded result inside the day; the old drivers' fate | the README says "not recorded yet"; the drivers, `e2e/`, their test rows and the ignore line go (change 9) |
| 20 | P1: S1 does not run every example | the Tests line corrected; `tests/test_examples_drivers.py` is the cheap check WP10 owns |
| 21 | P3: three things the README must say of the four | change 9 says all three |
| 22 | P2: files edited but not listed | Ownership lists them; `test_no_evolve_left.py`'s docstring stays with the deferred condensation |
| 23 | P3: lint before deleting | the lint ran before the Learn deletion and again after; the order is harmless with the test over the tree |
| 24 | P3: changes 5 and 6 bundle two things; the merge must keep the MCP server lines | split (changes 5, 6, 7); change 7 keeps them |
| 25 | P2: `plugin-commands` would duplicate the plugin page | dropped; the coverage check reads the plugin page (change 6) |
| 26 | P1: one day is three short | the cut taken: the condensation deferred, `record-and-trace` not written; two days |
| 27 | P2: built on WP8's branch | moved to `wp10-docs-examples` before the second commit |

### Decisions taken (How it works ships as it is, with a truth pass; the plugin page is the one copy of its commands; the four domain examples are renamed, not re-harnessed; 2026-10-29)

The design condenses fifteen How-it-works pages into four. The plan
review priced that as a rewrite of stale prose (a day with a per-claim
verification pass) and named it first in the cut order; under the owner's
Saturday target it is deferred past the release, with the must-survive
facts and their destinations recorded in the sub-plan's review for the
day it is done. What ships now is a truth pass: the lines that named a
retired CLI module, a mode layer, "both shipped modes" and a
compatibility rule are corrected, and the group is one flat list. The
design's `plugin-commands` reference would have been a second copy of
the plugin page's two tables with nothing to keep them equal, so the
plugin page stays the one copy and the coverage check reads it. The
four domain examples take the design's names so the examples table and
the tree agree, and keep their harnessless shape until their harnesses
are written under the harness rule.

### The Learn condensation table

| Retired page | H2 | Destination |
|---|---|---|
| overview | Why measured experience · What a lesson looks like · How a campaign becomes a lesson · Grading before learning · Serving | what-learn-produces (the same sections) |
| bank | What is on a card · Reliability states · Retirement is one-way · Contradictions | what-learn-produces, What a card is |
| bank | Repository layout | development-mode, The bank repository |
| bank | Creating and sharing · Reading the bank yourself | what-learn-produces, Where the bank lives |
| serving | What happens at launch · The three tools · What the frame does filter · Contradictions · Probe offers · Why an introduction | what-learn-produces, How the next campaign reads it |
| pipeline | The frame does the mechanics · Import · Mine · Grade · Update · Running the whole chain | development-mode, the first two sections |
| graders | The two layers · Who sees what · Two modes · The split manifest · The scorecard · The gauntlet | development-mode, How a bank is graded |
| development | The development run · The promotion gates · Codify | development-mode, the last two sections |
