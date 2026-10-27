I would fix the plan before building the suite. It covers the design’s headings, but several proposed checks could pass without proving the promised behavior.

This reviews [WP9](/home/ubuntu/kapso/.claude/worktrees/kapso-plugin/docs/plans/redesign/wp9-semantic-suite.md) at `e20e7395`. The checkout advanced during reading; findings below distinguish the newer learning fixes where relevant. I changed nothing.

1. **P1 — Changes 3–4; Acceptance: the report is not yet a semantic gate.**  
   The plan adds rendering for the persona and judge, but [report.py](/home/ubuntu/kapso/.claude/worktrees/kapso-plugin/tests/semantic/report.py:27) determines PASS from completed steps, budgets and artifact existence. Judge scores do not affect it; omitted steps are undetected; deferred steps disappear from the denominator; an empty run passes through `all([])`.  
   **Fix:** define each test’s required steps and semantic predicates, then make the report and runner exit status enforce them. Missing judgments, invalid judge output, incomplete runs and required deferrals must prevent a semantic PASS.

2. **P1 — Interface, S2; Changes 3: replacing answer policies does not complete S2.**  
   The design requires the whole round on both hosts, including learned lessons, harness improvement, deployment parity and a second engineer’s served build. The existing driver defers Codex learn/improve/share; the second engineer only loads and lists a bank; deployment completion checks a directory; the harness probe accepts either `done` or `failed`. Fraud’s generated evaluator is listed rather than contract-tested. WP9 does not explicitly replace these shortcuts.  
   **Fix:** specify artifact-backed completion predicates for all nine design steps, remove semantic deferrals, require the teammate’s independent install and build, verify deployment outputs against the evaluated solution, and require the interview’s silent-module questions to be resolved.

3. **P1 — Persona interface; Changes 2–3: the conversation can stop before the persona participates.**  
   [Context.converse](/home/ubuntu/kapso/.claude/worktrees/kapso-plugin/scripts/redesign/plugin_proof.py:220) stops whenever `turn.asked` is false. A persona therefore cannot challenge an unsupported result or complain about an omitted question—the exact behavior WP7’s harness interview needs tested. The proposed “reply’s first line” also discards multiline answers and violates CLAUDE.md’s prohibition on truncating messages entering another model.  
   **Fix:** offer every completed host turn to the persona, preserve its complete message, recognize only exact standalone `DONE`, and distinguish user satisfaction from artifact-verified completion. Turn/time exhaustion must produce an explicit incomplete result, not success.

4. **P2 — Personas; Risks, variance: the simulation needs a behavioral and reproducibility contract.**  
   Another vendor’s model is a useful interaction probe, but an imperfect engineer: it may patiently repair the product, invent repository knowledge, manufacture pushback, accept promises as results, or never say `DONE`. “Patience: 2” alone does not control these tendencies.  
   **Fix:** define question counting and patience scope, permitted knowledge, available actions, satisfaction criteria and abandonment. Isolate the persona from tools, hidden host reasoning and expected answers. Pin and archive models, effort/settings, CLI versions, prompts, card/README hashes and session policy. `S2` versus `S2-mechanical` distinguishes the broad modes, but `user` also needs explicit mode, persona identity and any scripted intervention. Define how both reruns affect acceptance; do not select the favorable one.

5. **P1 — Judge interface; Risks: the fallback vendor does not exist for S2.**  
   Claude and Codex already play the two sides. If Gemini is unavailable, there is no remaining vendor “that did not play either side.” Third-vendor-first is correct; the fallback is not executable as written. Project reachability also does not establish that the exact model, bridge, credentials and structured-output path work.  
   **Fix:** preflight that complete judge route before expensive runs. Specify either another independent provider, an explicitly disclosed weaker fallback, or an ungraded result that blocks acceptance. Record the model provider separately from the CLI used to reach it.

6. **P2 — Judge contract; Changes 4: valid JSON and real quotations are insufficient.**  
   JSON-or-fail is appropriate and compatible with CLAUDE.md. However, `{}` is valid JSON; scores can have wrong types or ranges; required dimensions can be absent. A quotation can exist yet fail to support the conclusion—or merely quote the reader’s own false claim. Requiring every quotation to occur in transcripts also excludes legitimate artifact evidence.  
   **Fix:** validate exact required dimensions, types, ranges and evidence locations. Evidence should identify artifact/transcript, location and supported claim. Freeze the design’s five S2 dimensions verbatim. Separate judge failure from product failure, retain raw output, and allow neither to become a PASS.

7. **P1 — S1 interface: the six tasks lack executable prerequisites.**  
   The six intentions are clear, but “the churn fixture and nothing else” cannot supply all of them. The no-evaluator task needs a defined variant or the fraud fixture. Deploy and learn need a completed campaign; resume needs a deliberately interrupted, resumable checkpoint. Most concretely, [the bundled harness directory](/home/ubuntu/kapso/.claude/worktrees/kapso-plugin/src/kapso/harness/bundled/README.md) contains no harness: loading a bundled harness by name cannot succeed before WP8.  
   **Fix:** write a six-row task specification with exact input fixture, prerequisites and success evidence. Decide whether the harness task uses a pinned repository/path reference now or remains explicitly blocked on a bundled name. Do not silently substitute one for the other.

8. **P1 — S1 interface; runner: a fresh session is not a cold sandbox.**  
   The clone’s `docs/` includes plans, research, prior findings and expected behavior, beyond the public documentation. A new host session can still inherit plugins, MCP servers, instructions, memories and banks. The fresh installer also installs Kapso as a `uv tool`, which does not establish that the engineer’s `python3` can import it.  
   **Fix:** provide a plugin-free profile and fresh task workspace containing an allowlisted public-doc snapshot, fixture and required artifacts. Exclude the development checkout and previous answers. Install the wheel into the Python environment actually used by the Python arm, and verify both import and CLI provenance.

9. **P2 — S1 baseline: “released wheel and its docs” needs an immutable definition.**  
   This is a useful retrospective comparison, but it is not MASTER’s original pre-WP1 `main` baseline. Unpinned released docs may move, describe another version, or lack redesigned capabilities. Giving the released package redesign instructions would measure a mismatch rather than usability.  
   **Fix:** pin wheel/version/hash, corresponding documentation revision and fixture dependencies. Give version-neutral task goals and let each documentation set supply its own calls. Report unsupported capabilities explicitly and predeclare denominator treatment. Label the result a retrospective baseline.

10. **P1 — S1 metrics and rubric: “first try” and the design’s brevity tests are missing definitions.**  
    A Python script can contain several API calls and block until completion; a detached CLI command can return a receipt immediately. A receipt, deployment invocation or second session entry alone does not prove equivalent success. Counting every errored tool call also penalizes harmless searches and help inspection. The plan does not explicitly enforce the design’s twelve-line Python flow, six-command CLI flow or undocumented-requirement question.  
    **Fix:** define a task-solving attempt, relevant failed invocation, next corrective invocation, launch timestamp and terminal success separately. Preserve tool results and exit status, not merely tool names/inputs. Specify line/command counting and include all three design judgments alongside verb comprehension.

11. **P1 — S4 interface; Changes 6: the answer key remains partly circular.**  
    The design asks whether a fresh reader can establish six answers from the record. Comparing that reader with another model reading `trace --json` risks grading agreement with the same rendering. `solution.json` and trace JSON alone cannot settle every “why,” rejection distinction, missing-cost qualification or merge risk. WP7’s labels-in-history finding demonstrates why “safe to merge” is not equivalent to “valid winner.”  
    **Fix:** prepare an independently checked fact sheet from checkpoints, verdicts, evaluator evidence, session records, delivered commit/diff/history and cost coverage. Use records containing actual voids/rejections and partial or missing evidence. Accept “not established” where appropriate; never require invented certainty. Keep the answer key hidden from readers and assign the design’s later human reading to a named milestone.

12. **P1 — S5 provider limit: the shim’s injection point and protocol are unspecified.**  
    A PATH wrapper failing its first N invocations can hit preflight, the conversational host, or the persona instead of a campaign session. It cannot interrupt a real CLI process already executing. Copying error prose alone may miss the exit code, stream event and output-file behavior the adapter actually consumes.  
    **Fix:** arm a captured failure protocol for a named campaign invocation after a recorded phase barrier; pass unrelated CLI calls through. Pin stdout, stderr, exit status, applicable files and recovery behavior. This proves handling of that simulated adapter failure, not real provider throttling or backoff. The wrapper is fault injection, not a forbidden compatibility shim.

13. **P1 — S5 evaluator crash and killed session: “WP6’s” repeats an acknowledged coverage gap.**  
    [WP6’s proof](/home/ubuntu/kapso/.claude/worktrees/kapso-plugin/docs/plans/redesign/wp6-observability.md:739) says the implementer consumed the one-shot evaluator crash before the engine’s evaluation reached it. Its killed-session case terminated an implementation CLI and the campaign continued; it did not demonstrate restarting a killed campaign writer.  
    **Fix:** target the engine-owned evaluator invocation and prove that invocation failed. Define precisely which process the killed-session scenario terminates. Keep automatic session recovery separate from user-requested campaign resume, and require subsequent valid work with the prior checkpoint preserved.

14. **P1 — S5 missing key; S2 inbox: the known false recovery is still inherited.**  
    WP7 supplied a placeholder key, withdrew the enrichment requirement and resumed into immediate budget exhaustion. WP9 refers back to that pause without specifying the promised fixture service and successful continuation.  
    **Fix:** provide a local service that rejects requests without the key and succeeds after it is installed. Retain the original task requirement, reserve time for continued work, and verify the resumed attempt actually uses the service. Choose a runtime failure path; a missing manifest-declared prerequisite may be refused before any session launches.

15. **P1 — S5 full disk and heartbeat: the proposed observation can fail on the same filesystem.**  
    A small tmpfs is a reasonable ENOSPC experiment, but mounting it over an existing campaign hides the campaign, while starting full prevents initialization. Once full, the status writer cannot create its temporary file there either. Moreover, [watch’s JSON path](/home/ubuntu/kapso/.claude/worktrees/kapso-plugin/src/kapso/cli/watch.py:87) prints stored data; DEAD/STALLED are computed by the reader, with staleness currently requiring three missed heartbeats.  
    **Fix:** mount before launch, fill only after a checkpoint, reserve an independently writable observer/log destination, and record the actual failing write and errno. Specify what “truthful within one heartbeat” means for stored state versus observed liveness. Free space and verify resume; route any required engine change to its owner.

16. **P2 — S5 expectations: message counts and preservation can pass vacuously.**  
    Existing `messages` means assistant turns, whereas S5 requires at most two **user** messages. The plan does not define the interaction window or whether scripted repairs count. Comparing two empty banks proves nothing. The design’s tampering check, explicitly folded into S5 as well as S3, is absent.  
    **Fix:** record user-role events from first failure presentation through verified recovery, including operator interventions. Define which scenarios legitimately have no inbox request. Seed a valid bank and compare its commit/content before and after. Add a named evaluator-tampering case, and state the current limitation on preventing hold-out reads.

17. **P1 — S6 comparison: the criterion is copied faithfully, but the measurement is not specified.**  
    The engine overwrites `status.json`; it does not provide the assumed complete “status histories.” Unequal attempt numbers are not equal-time checkpoints. Tiny builds can produce no scores, and WP7 showed that sixty minutes may yield one attempt or none. One stochastic pair cannot establish that learning caused improvement. The fixture’s bootstrap SE is not a measure of build-to-build search variance.  
    **Fix:** capture a timestamped timeline, preferably through `on_status`, and define a common elapsed-budget grid, valid incumbent scores and missing-data behavior. Require scored observations in both runs. Pin seed repository, data, evaluator, models, configuration and machine conditions. Keep the strict design bar as an observed-pair result unless the design is explicitly amended; report reruns and uncertainty without selecting a favorable pair.

18. **P1 — S6 prerequisites: “a learn between them” does not guarantee useful experience.**  
    A detached launch, completed mining or an existing nonempty bank is insufficient. The public learn chain includes harvest, mining, exam-before-lesson and the update crew’s bank commit. [Trace distinguishes](/home/ubuntu/kapso/.claude/worktrees/kapso-plugin/src/kapso/execution/trace.py:384) available cards, actual reads and cards judged load-bearing; these are different facts.  
    **Fix:** require the exact learn to complete with its exam and committed, validated lessons attributable to build one. Start with an isolated bank, pin its resulting head, verify eligibility under the second build’s harness coordinate, and show reads plus supported use and review citations. Start build two from the same seed repository, not the first winner, and exclude other runs’ lessons.

19. **P1 — Changes 1; Ownership: the learning repair is misdescribed and exceeds its named files.**  
    Before WP9, the exam runner already retried a missing artifact once. Adding that retry cannot explain or fix the observed failure without determining why both sessions produced nothing. The evidence grammar lives under `learning/crews/mining/`, outside the two claimed source files. Arbitrary YAML parse repair also needs a deliberate solution compatible with “no try/except.”  
    **Fix:** make this a bounded learning prerequisite: preserve session errors, diagnose the existing retry’s failure, and name the prompt file and exact repairable grammar. Broader behavior belongs in a learning-package PR. The newer `d47187a2` improves diagnostics and prevalidates the specific colon case; update the plan to describe that narrower implementation rather than promising repair of every unparsable document.

20. **P2 — dbt fixture: the scale is plausible; the evaluator contract is unfinished.**  
    Three sources and five models can be small enough, but “share of tests passing plus freshness” leaves the denominator, weighting, skipped tests, build failures and freshness clock undefined. Mutable project tests could make deleting tests improve the score. A seeded generator alone does not make time-dependent freshness deterministic.  
    **Fix:** pin dependencies, row counts and an evaluation clock; protect the authoritative test set; define one score formula and failure semantics. Require a clean database/build directory, deterministic results, malformed-submission diagnostics, final `name: value`, engine-shaped `result.json`, a marked non-comparable fast mode and measured sub-minute evaluation. Include the examples’ README sections, `run.py`, manifest and baseline contract.

21. **P1 — Author test; Ownership and Acceptance: guide repair is required but not owned.**  
    The design requires every structural gap to be fixed in the guide before a fresh rerun. WP9 demands this while assigning documentation fixes elsewhere and omitting the authoring-guide files from ownership. The “one-line exception” conflicts with the stricter ownership list.  
    **Fix:** explicitly own this WP10 slice or make guide fixes a blocking dependency with a defined rerun. Name the exact guide/design/example packet. WP2 already ran this author test and collected 66/65 guesses, so WP9 should verify those fixes and extend the test to the runnable fixture, rather than present it as an entirely new test.

22. **P2 — Author rubric and guess log: zero self-reported guesses is not a reliable completeness measure.**  
    An author may silently assume conventions or produce a minimal harness that avoids every difficult interface. Conversely, legitimate domain choices are not missing guide sentences. `check` can exit zero while reporting unmet prerequisites, and does not execute scripts. There are also guide distinctions to settle: the design says pages under forty lines, while the guide describes warnings above forty; the public write page’s manifest comment and prose disagree about directory naming.  
    **Fix:** define required domain behaviors and classify guesses as structural gaps, contradictions, domain decisions or information already documented. Require references to the supplied packet, independently audit unsupported structural choices, distinguish check failures/warnings/needs, and rerun a fresh author after guide corrections. The guide must document engine contracts and the freedom authors have—not prescribe every dbt design choice.

23. **P1 — Fresh-machine runner; Codex quota: the exception defeats the design’s isolation guarantee.**  
    Recording that S2 ran on the development box is honest disclosure, but does not make it fresh-machine evidence. The quota issue also affects Codex playing the persona for a Claude host, S1’s Codex engineer, readers/authors, and engine roles inside otherwise Claude runs. Moving only the Codex half of S2 does not solve the dependency.  
    **Fix:** preflight every role’s actual credential/model route and secure fresh-machine capacity, otherwise mark the affected run incomplete. Development-box runs can remain diagnostic. Judging fetched evidence on the development box is defensible only as an explicit postprocessing exception with an isolated evidence packet and no local-checkout access.

24. **P2 — Runner; Risks, spend and hours: the schedule is not budgeted enough to execute safely.**  
    S1 is 48 sessions across two packages and hosts; the second persona’s role could double that. If all three build tasks complete in both interfaces, that is 24 builds before deploy/learn/resume. S2’s existing sixty-minute build and 150-minute learn allowance already total 3.5 hours before other work; S6 permits 4.5 hours for two such builds and a learn, exceeding the machine’s default four-hour deletion limit.  
    **Fix:** add a per-test matrix of calls, campaign budgets, waits, total deadline, expected model spend and machine-hours. Separate campaign, persona and judge spend; unknown Codex dollars are not zero. S4 should state which archived campaign it reuses. Provision the examples’ dependency venv, pin CLI versions, and define whether reused machines receive clean users/workspaces.

25. **P2 — Archives and reports: a record file is insufficient to reproduce the judgment.**  
    Campaign directories omit learning artifacts stored elsewhere; copied status snapshots omit timelines. Date/test/host filenames and the current `--from` replacement behavior can overwrite the first failure. WP7 already needed prose to explain mixed wheels and restored campaigns.  
    **Fix:** use immutable run/attempt IDs and archive the wheel hash, source/plugin/docs revisions, effective configuration, fixture manifests, role prompts/settings, both sides’ raw transcripts, tool results, injection timestamps, checkpoints, relevant Git history, deployment proofs, learn/exam/update outputs, bank heads, serving records/pull logs, judge input/output and verdict. Preserve failed runs and qualified reruns. Verify evidence is fetched before deletion, exclude credentials, and record cleanup even when judging fails.

26. **P2 — CLAUDE.md; proposed tests and driver structure: configuration ownership and meaningful checks need tightening.**  
    Models, retry counts, turn limits, timeouts, checkpoints and injection sizes need one configured source; the plan names no such home and excludes `config.yaml` from ownership. Reusing existing environment-variable switches and hardcoded driver constants would carry existing violations forward.  
    **Fix:** assign configuration ownership, keep imports at module scope, use explicit subprocess results, and share the small amount of host/record machinery the drivers actually need. Keep scripted and persona modes as distinct test purposes, without compatibility branches.

    The valuable proposed tests are malformed/schema-invalid judge output, complete-message preservation, real event parsing, artifact-backed success predicates, recovery timelines, missing-score handling, source/read/use attribution, learning failure paths and actual evaluator execution. Prompt/rubric rendering tests earn a place only when they protect a concrete contract. Mock-return passthroughs, mock call-count assertions and merely parsing a guess log do not establish semantic quality. Add real local subprocess tests for shim behavior and runner failure/cleanup.

27. **P3 — Scope, run matrix and cadence: several remaining decisions are implicit.**  
    S5/S6 host coverage, the second persona’s placement, the author test’s record identifier and rerun acceptance are unspecified. “Once here and once at WP11” also omits the design’s runs after skill/page/help/public-doc changes. MASTER’s diagram says S6 follows WP3+WP8, while its prose permits it once serving and a second build exist.  
    **Fix:** publish one required-run matrix, assign the human S4 follow-up, retain the documented change-triggered cadence, and reconcile the dependency diagram. A churn S6 smoke can proceed without WP8; full S3 coverage remains explicitly pending.

What came out clean:

- Parking S3’s benchmark non-regression and abstraction work with WP8 is correct. Keeping the guide author test in WP9 is also correct.
- Reusing the examples as fixtures, the trading example, and a generated README-only empty repository avoids duplicate fixtures.
- Another vendor’s persona and a third-vendor-first judge match the design, provided their limitations are recorded.
- Strict JSON failure, complete transcripts and unchanged rubric budget caps are sound choices.
- S6 appropriately reserves the stronger causal claim for the separate A/B work; this suite should report exactly what its observed pair proves.