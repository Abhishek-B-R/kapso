You are reviewing a sub-plan before it is built: `docs/plans/redesign/wp10-docs-examples.md`, work package 10 (docs and examples) of the Kapso redesign. Read-only: change nothing.

Read, in this order:

1. `docs/plans/redesign/wp10-docs-examples.md`, whole.
2. The design it implements: `docs/plans/docs-and-examples-redesign.md`, whole (the principles, the navigation table, where today's pages go, the examples' shape and set, the checks, the migration table).
3. The master plan's row for WP10 and its status: `docs/plans/redesign/MASTER.md` (section 2's table, section 6's table), and the owner's decisions of 2026-10-29 at the end of `docs/plans/redesign/DECISIONS.md` (the release gate, the Saturday target).
4. The docs site as it stands: `docs.json` (the navigation), every page under `docs/` (skim each for what it covers; read `docs/learning/*.mdx`, `docs/evolve/*.mdx`, `docs/experience/*.mdx`, `docs/harnesses/*.mdx`, `docs/agent-access.mdx` and `docs/coding-agent-skills.mdx` closely, since the plan condenses, moves or merges them), `docs/reference/*.mdx`.
5. The examples as they stand: `examples/README.md`, each example's `README.md`, `kapso-brief.md` and `run.py`; `examples/harnesses/`.
6. The checks that exist: `scripts/check_snippets.py`, `scripts/check_docs_coverage.py`, `scripts/check_docs_geo.py`, `.github/workflows/docs.yml`; the words-out list in `docs/research/kapso-redesign.md`.
7. `CLAUDE.md`: the engineering rules.

Answer these, with findings rather than summaries:

1. Does the plan deliver the design? For each group and page the design names, say whether the plan creates it, keeps an existing page for it, condenses into it, or leaves it out — and whether what it leaves out (the four domain examples' harnesses) is the right thing to defer under the owner's Saturday target, or whether something cheaper and still faithful to the design is possible.
2. The condensations: Learn from six pages to two and How it works from fourteen to four. Reading the current pages, what would a reader lose? Name the sections that must survive (facts a user of the shipped verbs needs) and the ones that are internals a contributor reads once; say whether four and two are the right counts.
3. The redirects and the navigation test: is the plan's rule (every retired path redirects to the page that absorbed it; every page listed once; no page outside the navigation) complete, and what does Mintlify's `docs.json` actually support for redirects?
4. The lints: are the two rules as stated mechanical and fair (the words-out list from the research note; a number adjacent to a metric word without provenance in its paragraph; the benchmark tables' column as provenance)? Where would they false-positive on today's pages, and what should the allow-list be instead of a widening?
5. The examples: is `full-loop` as described buildable from today's `ml_model_development` in the day; is the README shape right; what of the four domain examples must the README say so that a reader is not misled.
6. The interface, ownership and the order of changes: anything missing, anything in the wrong package, any change that cannot be one commit with a test.
7. Time: the plan claims one day. Where is it optimistic, and what would you cut first if it slips?

Write numbered findings, each with a severity (P1: must change before building; P2: should change; P3: minor), the section of the plan, what is wrong, and the change you propose. Then a short list of what is sound. Do not change any file.
