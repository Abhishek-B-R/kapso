**WP8 needs revision before building.** It captures most of the port’s structure, but weakens the agreed acceptance criteria and leaves several executable contracts unresolved. I made no changes. Bundled harness files and tests appeared concurrently during the review; those new files are outside this review.

References to changes and sections below mean [WP8](/home/ubuntu/kapso/.claude/worktrees/kapso-plugin/docs/plans/redesign/wp8-harness-ports.md).

1. **P1 — P1 / changes 3–7: the RelBench reproduction is not tied to the recorded experiment.**  
   The plan builds the expected predictive pages, skills, hooks, runner and bank reference. However, it calls 600 minutes and the current Codex override the **“recorded budget … and model”** for the 82.1 result. The accompanying baseline [README](/home/ubuntu/kapso/.claude/worktrees/kapso-plugin/benchmarks/relbench/claude_code_baseline/README.md:4) describes a four-hour comparison. The current override does not establish the historical launch configuration.

   `rel-trial/study-outcome` is a reasonable representative task, but retrieve its actual launch record, hardware, model routes, bank head, evaluator and budget before declaring the reproduction. Otherwise this is a new experiment. Also reconcile the promised **“eight practices”** with today’s eleven numbered practices in `context.py`; use an explicit disposition for every source section so later additions are not silently dropped.

2. **P1 — P2 / changes 8–10: establishing a baseline replaces the done-when line.**  
   The plan builds MLE additions, workflow references, a runner and a grader. It changes “reproduces its recorded result” into **“the run records the baseline … a valid graded score.”** That is not non-regression. `spooky-author-identification` being the handler’s default does not establish that it is the right recorded lite task.

   Recover a task-level result and its conditions, including the published MLE submission referenced by the benchmark README. If unavailable, the owner must explicitly amend P2 and S3. Missing mapped work also includes `predict-endpoint`, or an explicit WP5 handoff, and a recorded check that adding MLE required no RelBench-shaped change beyond the narrowly permitted page sentence and guide correction.

3. **P1 — P3 / changes 11–13: the claimed absence of an ALE baseline is false.**  
   **“No ALE result is recorded in the tree”** contradicts [ALE’s README](/home/ubuntu/kapso/.claude/worktrees/kapso-plugin/benchmarks/ale/README.md:12): `ahc008` has Kapso **1221**, versus ALE Agent **1189**. P3 requires a recorded **rating-level** result, not merely a valid public score.

   Keep `ahc008` if its launch conditions can be recovered. Specify the private evaluation, rank-to-rating calculation and comparison against 1221 under matching conditions. Missing historical configuration is a retrieval requirement, not grounds for silently lowering the bar.

4. **P1 — P4 / changes 14–17: the IOAI task, comparison and several mapped additions are missing.**  
   **“One practice task from the override file’s list”** is not executable: that override contains no practice-task list. Acceptance further changes “at or above the recorded cold start” into **“valid scores at the budget.”**

   Name the task, historical run and exact comparison conditions. The recorded IOAI runs include materially different lane counts, seeds and harvest conditions; they are not interchangeable baselines. Add the mapping’s missing copied ML skill directories, IOAI ideation axes, and learning scope by twist and modality. The current contest tree contains none of the explicitly required copies from `predictive-modelling`.

5. **P2 — P5 / changes 18–21: the timing and gate integration change without a recorded decision.**  
   P5 calls for cross-checks after P2 and after P4, with the shipped-harness scan run by `check`. WP8 defers them until the end and says **“check does not change … (a decision below)”**, but supplies no such decision.

   Keeping structural `check` domain-agnostic is sensible. Record that architectural change in the upstream plan/DECISIONS and specify the mandatory release gate that replaces it. Run the predictive checks after MLE and the contest checks after IOAI. After fixing a swap finding, rerun the swap: **“or each edit a recorded finding fixed”** is not yet evidence of zero edits on the final revision.

6. **P1 — Harness/task split / change 4: the sanitizer is legitimate domain machinery, but the proposed extraction is incomplete.**  
   RelBench’s API in `sanitize-cache` is explicitly allowed by the mapping. An API-specific skill is not automatically benchmark task material. What must stay outside the harness is the selected dataset/task, cutoffs, target columns, raw cache, private labels and selected protocol parameters.

   The implementation is in `sandbox.py`, not the handler, and currently imports `benchmarks.relbench.task_specs`, reads environment configuration and uses a copy fallback. Copying it would retain benchmark coupling and violate repository rules. More seriously, the proposed fixture assumes **“rows after the cutoff gone”** universally: autocomplete preserves future rows while blanking targets; recommendation and rolling snapshots have different contracts.

   Define a parameterized, standalone sanitizer covering those regimes. Decide whether the runner or setup owns sanitized-cache creation; the plan currently assigns it to both. Test the actual leakage boundaries, row alignment and per-tick isolation.

7. **P1 — Harness/task split / change 4: `leakage-scan` changes advisory evidence into unconditional rejection.**  
   The proposed **“exit 1 on any”** hit changes `_audit_patterns` semantics. Existing `verify:` patterns deliberately flag legal train-plus-validation refitting for review. `mask_input_cols=False` is not universally illegal, and `upto_test_timestamp=False` must be interpreted against the rolling/autocomplete contract.

   The concrete cache paths, archive locations and label-bearing columns are task resources; the general leakage rules and API hazards belong in the skill. Parameterize the former, retain advisory versus disqualifying findings, and make the scan regime-aware. A diff-only scan also cannot replace the final full-candidate audit. Avoid maintaining divergent copies of the rules in the runner and skill.

8. **P2 — Harness/task split / change 4: the two trading hooks are not both “the same program.”**  
   `protect-prepared` is largely reusable, provided it is mounted after setup. `deny-web-fetch` tells the agent that **“all market data comes from the market-data server”** and to **“Use get_bars.”** That is trading-domain material incorrectly imported into predictive modelling.

   Rewrite the reason around prepared task resources and specify module placement. Its matcher only blocks shell commands using `curl`, `wget` or `aria2c`; it does not reproduce the entire `implementation_web: false` policy or stop native search and arbitrary Python downloads. Preserve the host-level web setting where required, and describe the hook’s actual protection accurately.

9. **P1 — Harness/task split / change 8: reviewing only the MLE tip sheet leaves contradictions and task examples in the shipped skill.**  
   **“The code examples kept; the tip sheet reviewed line by line”** is insufficient. Other nodes say never cross-validate transformers, never average ensemble outputs, cap tree features at 200, and round probabilities such as 0.98 to 1 when optimizing loss. Code examples load named datasets such as IMDB and Iris; one evaluates on their test split.

   Review all workflows, concepts and examples. Keep domain model names and conditional techniques; replace named example datasets with task-supplied inputs and make validation instructions agree with the harness. Historical or arbitrary thresholds need justification and an appropriate configuration home. The acceptance phrase **“no … model … choice”** should also match the actual rule: domain model choices are allowed; choices of models for Kapso’s agents are not.

10. **P1 — Harness/task split / change 14: copying IOAI documents wholesale imports task rules and engine settings.**  
    **“`RUN_FINDINGS.md`’s thirteen issues as rules”** would include launcher branch selection, authentication setup, lane allocation, provider-pool limits, timeout allocation, checkpoint handling and process cleanup. These are runner/engine concerns. The source now also contains I-14, so the stated inventory is stale.

    Likewise, IOAI’s quota defaults, permitted GPU shape, external-model/data restrictions and package restrictions are contest/task material. `KAGGLE_CLI.md` contains concrete examples such as `titanic`, `test_scenarios.pkl`, a fixed version, and a duplicated push command. It also contradicts `RULES.md` about whether submissions require tickets.

    Produce a source-to-destination inventory: reusable CLI mechanics and contest economics into skills; task restrictions into the statement; account limits and engine controls into runner configuration; historical incidents into evidence or documentation. Resolve contradictory source instructions before porting them.

11. **P1 — Interface / `kernel-slots`: runtime quota and ledger access are valid, but the path and authority contract is absent.**  
    A generic account-session server may read task-supplied quota data and maintain runtime state. That does not put a budget or engine field *inside the harness*. The problem is **“the ledger under the campaign root”**: staged servers run in session directories, not the campaign root, and no campaign-root argument or discovery contract is specified.

    Define how the runner supplies the shared state location and authoritative limits. Setup may materialize validated quota data under `prepared/`; it must not invent account capacity. Keep the mutable ledger outside read-only prepared resources. Specify account-wide locking across processes/campaigns, cancellation, stale-ticket verification and resume behavior. Reconcile blocking acquisition with MCP call timeouts. A single-process fixture ledger cannot establish these properties.

12. **P1 — Change 14 / submission hooks: the permitted submission route is undefined.**  
    `deny-shell-submit` rejects `kaggle competitions submit` and names **“the skill’s procedure”**, but the copied CLI procedure itself uses that shell command. `kernel-slots` currently allocates push tickets; it is not the missing submission API.

    Define a trusted submission operation that captures the immutable kernel version or file hash, response and score identity. Specify whether the runner’s harvest uses that same operation and what “zero shell-level submits” counts. Also make `require-scorer-run` and `require-insurance` conditional on task modality; otherwise ALE can be blocked for having no Kaggle submission, and IOAI for having no local seed results.

13. **P1 — Runner interface / changes 6, 9, 12, 15: `Brief` prose does not replace handler behavior.**  
    [`Kapso.build()`](/home/ubuntu/kapso/.claude/worktrees/kapso-plugin/src/kapso/kapso.py:1368) constructs `GenericProblemHandler`. That handler always maximizes. Writing metric direction into `Brief.measured_by` does not change the engine’s ordering. MLE, RelBench and ALE all support lower-is-better tasks.

    Other lost contracts include RelBench’s `finalize_run_selection` and IOAI’s `honor_agent_stop=False` and reserve behavior. Archive inference can infer a last run, but cannot recreate a validity decision that the old callback never recorded. IOAI’s configured zero reserve also cannot simply become `Budget(reserve_minutes=0)`: that handle rejects zero.

    Specify supported facade/config mechanisms for each behavior, or obtain a WP1/WP4 interface change. If grades are normalized to a maximizing score, retain and report the raw benchmark metric explicitly. Do not hide engine controls in harness fields.

14. **P1 — Runner interface / task statements: the proposed `Brief` contents are too loosely specified.**  
    A `Brief` can carry the full task statement; its objective is not clipped. The short list **“objective … metric … baseline … rules … budget”** is not a sufficient preservation contract.

    RelBench must retain schema and relationships, timestamp semantics, label SQL, label statistics, prediction shapes/order/dtypes, starter helpers, validation-versus-test refit rules, rolling protocol, resource paths, retraction instructions and champion artifact access. MLE needs the complete competition constraints, submission schema, debug/full contract and runtime limits. ALE needs statement, examples, constraints, scorer invocation, case sets and aggregation. IOAI needs the organizer prompt, modality, permitted resources, account/competition identity, quota and absolute deadline.

    Split mixed builders such as `_resources` and `_prediction_contract` into facts and standing guidance. Reusable preflight instructions, training-stage guidance, submission-loop economics, leakage methodology and generic data-access advice must not remain embedded in runners merely because their surrounding functions also produce task facts.

15. **P1 — Evaluation directories / MLE: external answers are compatible with the contract, but the search metric changes.**  
    **“Answers … outside the workspace”** is expressly supported by the evaluation documentation. It is not, by itself, a blocker or a security boundary.

    The substantive change is making MLE’s official grader the in-loop measurement. Today the handler returns the candidate’s `<score>` as the search score, while official grading also affects medal tracking. Replacing that with repeated official hold-out scores changes optimization and comparability.

    Decide the intended protocol: development validation for search with official final grading, or an explicitly approved repeated-grading benchmark. Specify answer access, the candidate entry point, timeout, submission validation, stale-output removal, failure exits, metric direction, final-line output and `result.json`. The final report must grade the delivered candidate, not whichever submission file remains in a shared directory.

16. **P2 — Evaluation directories / ALE: a Docker-backed grader is feasible, but “fixture scorer output” tests too little.**  
    Calling the official Docker scorer from `evaluate.py` can satisfy the contract. The plan does not specify image/version, mounts, compiler mode, case selection, repeated evaluations, failure aggregation or public-score-to-private-rating separation.

    Preserve the intended aggregation in today’s handler, including its repeated public evaluation, rather than silently replacing it with one pass. Run a small real scorer invocation in validation; parsing a canned output only tests parsing. Keep private cases and Elo computation runner-side.

17. **P1 — Evaluation directories / IOAI: a lane’s running best is not an evaluator for a candidate.**  
    **“The lane’s best public score since the campaign’s start”** can assign an earlier candidate’s score to later code, including a candidate that never submitted. Concurrent lanes, delayed scores and harvest submissions make this worse. Fingerprinting the reader does not protect the mutable ledger or establish submission identity.

    Evaluate a specific candidate’s recorded submission: competition, lane/session, candidate commit or artifact hash, kernel reference/version or uploaded-file hash, submission ID, timestamps and terminal status. Define pending, missing, rejected and out-of-window outcomes. Sessions can perform submissions, but the evaluator must verify the candidate-to-submission association. Campaign-best scoring belongs in the final campaign report.

18. **P1 — Runner rewrites / changes 6 and 15: “follows” and “stay” conceal substantial migration work.**  
    **“`campaign.py` follows”** and **“the harvest and the organizers’ trace export stay”** do not specify preservation.

    Explicitly cover fresh output versus resume; initial repository seeding; experiment limits; shared-cache paths and permissions; runtime config; pinned harness/bank identities; absolute deadlines including preflight; lane-specific GPU assignments; report paths; and the new location of serving records. `Solution.branch` and `commit` can be absent, so final grading needs an explicit no-candidate path.

    Preserve RelBench’s validation selection, selected test evaluation once, then audit. Preserve IOAI’s harvest deduplication, version selection and submission window. Its existing final audit can miss lane-specific kernel locations. I found no organizers’ export implementation in the named IOAI runner to simply retain: identify its source and output contract. A durable clock alone also does not make spot recovery work without durable workspace, cache, ledger and checkpoint restoration.

19. **P1 — IOAI bank / Interface and change 16: the representation changes from curated reference material to measured lessons without an evidence policy.**  
    The mapping proposed an ingested index. WP8 instead proposes a bank, automatically **“active for the sure-gold tier”**, with **“the rationale naming the tier.”** That is a material change: external banks are presented as “measured by others”; indexes as “reported by others.”

    The actual book mixes reproduced solutions, author claims, mirror-only methods and answer keys. A public score establishes neither reusable scope nor reliability of a general claim. `candidate` cards also serve, so assigning weaker entries that state does not quarantine them.

    Decide with WP3 how external evidence is represented. Distinguish reproduced, independently corroborated and merely claimed results; describe the score’s protocol and limitations; separate runnable procedures from insights or reference-only material. A tier can inform a rationale, but cannot replace one. Do not fabricate Kapso trajectories or harness coordinates.

20. **P1 — IOAI bank / change 16: “every card field” does not establish a loadable, conformant bank.**  
    Concrete requirements are missing:

    - Path loading requires a Git repository whose **`main` commit** contains `index.md`, `insights/` and `procedures/`. Empty directories are not committed.
    - Section indexes, the body-plus-trailing-ledger grammar, required body sections, confidence text, valid evidence verdicts, and version/log consistency need validation.
    - The serving layer advertises procedure payloads under `code/`; **“solution files beside”** the card does not provide that expected location.
    - Copying `problem.md`, `idea.md` or README files below `procedures/` triggers the current card-layout invariant.
    - Learning evidence admission expects a resolvable trajectory/reference and justified outcome evidence. A public URL and score alone do not satisfy it.

    Distinguish load rejection, serving behavior and learning conformance: serving does not run the entire learning gate. Test real loading and card retrieval, plus the agreed conformance path. `scope: domain` means broadly eligible, not “only olympiad tasks”; express applicability honestly, remembering external references serve all scopes.

21. **P2 — IOAI bank / provenance and backup: the split is sensible, but verdicts need more dimensions.**  
    A source’s stated licence and organizer rules are appropriate starting evidence. They do not alone establish ownership of every copied notebook, model, dataset or embedded asset. An `ours` reimplementation can still contain third-party material.

    Record source URL/revision, author, licence evidence, attribution requirements, component dependencies, modifications, and separate decisions about local use, redistribution and eligibility for the target contest. Unknown rights should not become “shippable” by inference. “Local-only” also needs a clear backup/access policy.

    Back up and verify **both the primary book and reserve before conversion work**, as P4 requires; name inventory hashes and a restore check. Pin the provenance input and converted bank commit. Define whether same-task prior solutions are permitted in the reproduction and whether “cold start” still accurately describes that arm.

22. **P2 — Abstraction scan / Interface and change 18: the proposed heuristics are both incomplete and overbroad.**  
    Registries catch known IDs, not the design’s full class of benchmark constants. They miss historical task names, book-only entries, account handles, target columns, task filenames, dates, hardware limits and constants embedded in scripts or references. “IOAI’s practice uids” also needs an actual source.

    **“A decimal that reads as a score, quota or deadline”** is not an implementable rule. It misses integer quotas, textual deadlines, percentages and scientific notation; broad matching flags legitimate probability bounds, learning rates, versions and algorithm examples.

    The bundled trees will also contain legitimate library/model identifiers, `/kaggle/input`, `/kaggle/working`, CLI paths and leakage patterns that name forbidden paths. Specify file coverage, token boundaries, contextual rules and narrow reviewed exceptions. Combine deterministic known-constant checks with source review; do not claim a zero-hit result proves abstraction.

23. **P1 — Benchmark machine and Hours: the hardware contradicts the launch configuration, and the budgets are not defined.**  
    The proposed **one H100 or one A100** does not satisfy RelBench’s four GPU-pinned lanes or IOAI’s default eight GPU-pinned lanes. Reducing lanes changes the experiment. MLE’s eight-hour candidate runtime and implementation-session ceiling are not a campaign budget; ALE’s session ceiling likewise does not define a four-hour arm.

    The available arithmetic is:

    | Arm | What is actually specified | Cost implication |
    |---|---|---|
    | RelBench | 2-hour smoke + 10-hour full | 12 machine-hours; 48 GPU-hours if the four-GPU configuration is retained |
    | MLE | Table says 9 hours; campaign cap absent | 9 machine-hours is an estimate, not a bound |
    | ALE | Table says 4 hours; campaign cap absent | CPU/Docker hours are not yet bounded |
    | IOAI | Default full window is 2 hours; table says 3 | Smoke allowance is unstated; local GPU and Kaggle execution costs are separate |
    | Swaps | Four one-hour arms | Four additional machine-hours, plus any separately excluded preparation |
    | Author test | Two host runs | Additional author/judge usage and machine time |

    The four table entries total **28 machine-hours**, or **32 including swaps**, before author runs, provisioning, retries and reruns. No per-arm token estimate or cap is provided. Obtain measured input/output/cached usage by role and lane from comparable traces; include setup, research, verification, judging and reviews. Wall time alone cannot yield token cost.

24. **P2 — Risks / noise and smoke arms: the comparison rule needs preregistration.**  
    **“The campaign’s run-to-run spread”** is usable only for comparable runs. Different models, budgets, lanes, seeded champions or post-deadline harvests do not form a noise estimate. Repeated scores for the same IOAI kernel are evidence of scoring variation, but not automatically the campaign-to-campaign band.

    State the metric units, band estimator, comparison population and response to missing records before running. If only one historical observation exists, acknowledge that a run-to-run band cannot be estimated from it.

    Smoke-before-full is sound, but **“a tenth of the cost”** contradicts RelBench’s two-hour versus ten-hour arms. Define the other smokes. Reset mutable state between arms, and account for quota and account-history effects; otherwise the full arm inherits smoke work and changes the reproduction.

25. **P1 — Changes 7, 10, 13, 17 / sequencing: early reproductions do not validate the final harnesses.**  
    RelBench runs against predictive `0.1.0`, then MLE changes it to `0.2.0`. ALE likewise runs before IOAI changes the contest harness. Those early results cannot prove non-regression on the shipped versions. Editing a tree underneath a running campaign can also trip harness hash checks.

    Split preparation, launch and collection into an explicit dependency graph. Freeze and pin final trees before acceptance runs; treat earlier runs as development evidence or budget their reruns. Move bank backup/provenance earlier. Identify the separate machines and shared account/provider limits that permit overlap. As written, **“each one a commit … suite green at each”** with blocking reproduction steps does not establish the parallel schedule assumed by the hours table.

26. **P2 — S3/report / change 21: the archive contract is too thin for reproducible verdicts.**  
    **“One file per run”** is fine if it means a complete archive, but its contents and durable destination need definition. Archive source/wheel hashes; resolved configuration and overrides; model routes; hardware; task/data/evaluator identities; harness tree/hash; bank head and provenance; clocks and budgets; candidate commits and outputs; raw scoring and audit evidence; submissions/versions; serving and pull logs; session streams; delegate reports; hook decisions; failures; and token/cost records.

    Preserve the selected baseline and noise-band evidence, swap edit logs, and author inputs/guesses/judgments too. `--rederive` should recompute pass/fail from those artifacts without live leaderboard state. An ignored local archive that disappears with the machine is not sufficient.

27. **P1 — Task swaps / change 19: none of the four swaps is specified enough for the zero-edit bar.**  
    Naming a category is insufficient. Each needs an exact task, input acquisition, rules, evaluator, baseline, resource envelope, command and success artifact.

    | Swap | Most likely required change |
    |---|---|
    | Different RelBench dataset | Missing task registration/metadata, schema assumptions, target coercion, or a different temporal regime; select a task that exercises a real distinction |
    | Kaggle tabular through IOAI preflight | Preflight currently installs IOAI2026 rules; ordinary Kaggle resource rules and file submissions need task-specific handling |
    | AHC outside lite | Handler initialization indexes `LITE_PROBLEMS_INFO`; direction and contestant/rating metadata need a general source |
    | IOAI 2025 | Correct year/task rules, available submission endpoint, quota and resource permissions; a closed historical task needs an explicitly accepted evaluation route |

    Separate runner preparation from measured harness edits. The present claim **“any reference is accepted, so the task swaps need no runner edit”** does not follow: accepting `--harness` fixes none of these task-adapter limitations. Run again after fixes to establish zero edits.

28. **P2 — Author test / change 20: this is S3’s third part, but its inputs must remain controlled.**  
    Re-running `pipeline-dbt` is **not a proxy**: S3 explicitly names that domain. Reusing the existing driver is appropriate.

    Specify a fresh author context, final guide revision, exact allowed design/example inputs, both host runs, complete guess logs and independent classification. The driver currently supplies public guide/reference pages; record how these satisfy S3’s “guide, design and trading example” input rather than silently omitting part of it. Preserve the distinction between structural gaps and legitimate domain choices. Reusing an already-authored harness or prior answers would invalidate the completeness test.

29. **P1 — Proposed scripts, server, graders and runners / CLAUDE.md: copying implementations imports known violations.**  
    The sanitizer contains environment reads, local imports and a try/except fallback. Legacy benchmark code also contains exception handling, prompt truncation and duplicated operational defaults. **“The handler’s hub fetch”** is actually an LLM/web-search operation, not a ready-made download script; copying it would drag agent orchestration into a domain script.

    Require explicit argument/config inputs, top-level imports in isolated optional-dependency modules, propagated errors, and SDK-owned credential access. Single-source quotas, timeouts, polling, runtime limits and paths; derive staged task configuration from that source. Treat the documented harness path ABI separately from inventing new environment configuration.

    Move reusable behavior rather than retaining parallel old/new implementations. Delete superseded handler prose and legacy learning paths, and migrate their callers. Scripts inside skills and grader directories are appropriate; copying their current code unchanged is not.

30. **P1 — Tests: the proposed runner tests weaken existing coverage while claiming otherwise.**  
    **“None exercises a mock alone”** overstates what `build()`-mocked solve tests prove. Such tests can usefully verify argument assembly, but cannot establish config resolution, staging, integrity, resume, serving or final delivery. Today’s runner tests already construct substantially more real machinery.

    Keep provider calls stubbed while exercising the real facade and orchestration plumbing. The sanitizer’s data-boundary tests, both-host hook tests, actual grading fixtures and bank conversion tests earn their place. Expand them where contracts are tricky: minimizing metrics; no successful candidate; stale results; evaluator tampering; preserved resume state; concurrent slot acquisition/cancellation; exact submission attribution; conditional hooks; real bank loading/card payload retrieval; and corrupt provenance/ledger inputs.

    A fixture ALE output tests parsing, not Docker execution. A successful IOAI card pull tests availability, not evidence conformance. Add a wheel-installed bundled export/staging check so scripts and resources are verified outside the checkout.

31. **P2 — Ownership and unresolved decisions: the plan declares ownership it has not reconciled.**  
    `src/kapso/harness/abstraction.py` is a new public-core module in WP2’s territory. WP9’s directories being **“merged; noted here”** does not itself settle ownership of new drivers and semantic-suite changes. Override changes touch WP4’s contract; deployment and documentation require WP5/WP10 coordination. WP3 also anticipates obsolete family-scoped banks being re-learned, while WP8 explicitly excludes re-learning the RelBench bank.

    Record these interface agreements before implementation. Prefer benchmark/release tooling for a benchmark-specific scanner unless WP2 accepts a general core API. Inspect and pin the actual RelBench bank rather than assuming “external sources serve all” resolves every grammar issue.

    The owner should decide acceptance-bar changes, historical comparison runs, bank-versus-index semantics, permitted prior-solution exposure, resource/token expenditure and any engine-interface expansion. The implementer should decide extraction details within those settled contracts. Also change step 1’s **“WP8’s row says built on this branch”** to an in-progress status until its proof exists.

What came out clean:

- Two complete bundled trees, situational skills and no harness composition match the design.
- RelBench API use in a sanitizer skill, domain model names, and a runtime quota-reading server are not inherently violations of “Never in a harness.”
- External-answer MLE grading and Docker-backed ALE grading are compatible with the evaluation-directory architecture.
- Keeping ordinary `check` domain-agnostic is a sound choice once the replacement gate is explicitly agreed.
- Separating shareable and local-only material, pinning experience, and withholding publication are sensible.
- `pipeline-dbt` on both hosts is the intended author test, and archiving traces for a re-derived S3 report is the right approach.