You are reviewing a sub-plan before it is built: `docs/plans/redesign/wp9-semantic-suite.md`, work package 9 (the semantic suite) of the Kapso redesign. Read-only: change nothing.

Read, in this order:

1. `docs/plans/redesign/wp9-semantic-suite.md`, whole.
2. `docs/plans/semantic-production-tests.md` (the design the plan implements) and `docs/plans/redesign/MASTER.md` sections 3 to 5 (the order, the tests per package, the method), and the WP9 entries at the end of the WP7 block in `docs/plans/redesign/DECISIONS.md`.
3. What the suite already has: `tests/semantic/README.md`, `tests/semantic/report.py`, `tests/semantic/budgets.json`, `tests/semantic/personas/ml-engineer.yaml`, `scripts/redesign/plugin_proof.py` (the hosts, the steps, the record shape, the scripted policies), `scripts/redesign/fresh_machine.sh`, `scripts/redesign/README.md`.
4. What the round before it found: `docs/plans/redesign/wp7-plugin.md`, the Proof run, the Findings for later packages and the Pull-request review (the learn's two fail-loud cases, the budgets at the rubric's caps, the Codex arm's limits, the harness interview, the inbox proof, the empty bank).
5. The engine the suite reads: `src/kapso/learning/mining.py` (`_split_frontmatter`, the repair round), the exam's crew runner under `src/kapso/learning/`, `src/kapso/cli/trace.py` and `src/kapso/cli/watch.py` (`--json`), `src/kapso/experience/` (the serving, the pull log), `examples/churn-first-build`, `examples/trading`, `examples/README.md`, the authoring guide the author test gives its author (`docs/` pages on harness authoring).
6. `CLAUDE.md`: the engineering rules (no try/except, no configuration from environment variables, imports at the top, no compatibility shims, config values single-sourced, minimalism, every test earns its place).

Answer these, with findings rather than summaries:

1. Does the plan implement the design? For each of S1, S2, S4, S5, S6 and the author test: what the design asks, what the plan builds, what is missing or changed without saying so. Is parking S3's first two parts with WP8 right, and is the author test's placement here right?
2. The simulated user: is a persona through the other vendor's CLI a sound engineer stand-in (what will it get wrong: patience, pushing back, saying `DONE` too early or never), and what does the plan need to pin so two runs are comparable? Is the record shape enough to tell a persona run from a scripted one later?
3. The judge: is the vendor order right, is the JSON-or-fail contract right, are the rubrics the design's, and what prevents the judge from grading its own reading rather than the facts (S4 especially)?
4. S1: are the six tasks and their success predicates specifiable from the design and the public docs; what does "first try" mean for a Python call versus a CLI line; is the baseline on the released package meaningful given the released docs; what is a cold engineer's sandbox here (a plugin-free host session with the docs directory)?
5. S5: are the five injections injectable as described (the shim for a provider limit, the tmpfs for a full disk, the evaluator crash and killed session from WP6, the missing key from S2); what would each prove or fail to prove; is "at most two user messages" measurable?
6. S6: is the anytime comparison sound at a tiny budget (noise, the first build's variance); what must the learn complete to make it meaningful; are the learn repairs in scope rightly or do they belong to a learning package pull request?
7. The dbt fixture and the author test: is a dbt-on-DuckDB fixture small enough and the evaluator contract satisfiable; is the guess log a usable measure; what does "zero structural guesses" require of the guide?
8. The runner over the fresh machine: cost and hours per test; what runs on the development box and whether that is honest; the Codex key quota; what must be archived.
9. CLAUDE.md compliance of what the plan proposes (the shim, the judge's JSON contract, the drivers' structure), and the tests: which proposed tests earn their place, which only exercise mocks.
10. Anything the plan should decide now and has not.

Write numbered findings, each with a severity (P1: fix the plan before building; P2: should fix; P3: minor), the section, what is wrong, and the fix you propose. Then a short list of what came out clean. Do not change any file.
