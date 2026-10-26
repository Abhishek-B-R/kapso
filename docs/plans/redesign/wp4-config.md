# WP4: Config without modes

2026-10-26. Owner: the redesign's implementer, autonomously, the owner
checking the decisions. Branch `wp4-config` off `redesign` at `55a92430`.
Size: L (the config's shape touches every verb, the strategy's parameter
reading, four benchmark runners and the pages; the findings the earlier
packages left here add the budget's end and the judge's retry).

## Scope

The config becomes two layers resolved by one function: the packaged
defaults and one override file, unknown keys refused by name; `modes`,
`default_mode` and the `mode` argument go everywhere (the facade, the CLI,
the orchestrator, the preflight, the launch record, the checkpoint, the
host session, the ingest). The build's sessions are named by role over a
table of hosts, so `--coding-agent` routes every session and a host is
never asked for a model it cannot serve. The retirements: `design_axes`
(the planner names the axes from the goal and the ideation page),
`additional_context` and `context` on `build()`, the generic handler's
prose (the engine's task statement for every build), `implementation_web`
and the ideation `web_search` knob (a harness hook). The benchmark configs
become override files and their runners lose `--mode`, with a smoke test
each; `kapso doctor` prints the effective config. And the findings the
earlier packages left for this package: the budget's end (the finishing
sessions inside the reserve, admission from the last attempt's duration,
no session launched on the floor), the judge's retry (resumed, its reason
in the record, none after a deadline), the judge's cards parser, the
attempt's commit in the record, the reconstruction reading the branch
before it concludes, the engine's own sessions in the record, the harness
directory read-only to sessions, the evaluation directory's rule stated,
the maintainer's default decided.

**Not in scope.** The benchmarks' harness ports (WP8: this package
converts their configs and smoke-tests their runners; the handlers'
`get_problem_context` prose stays in the benchmark handlers until then).
`deploy(target=)` and the `deployment` block's shape (WP5; the block is
unchanged here). The plugin's skills reading the effective config (WP7;
this package tells it what changed). The learning crews' session specs
(`learning.*`, already `{cli, model, effort}`), the `inference` block and
the `learner` block, which keep their shape. A lighter ideation for small
briefs (WP1's finding): decided below as a measurement first, not a
change. The docs' new navigation (WP10; this package rewrites the pages it
changes).

## Interface

**Exposed.**

- **The resolver**, `kapso.core.config.load_config(config_path=None) ->
  dict`: the effective config, the packaged `src/kapso/config.yaml`
  deep-merged with the override file at `config_path` (nested mappings
  merge key by key; scalars and lists replace; `None` or the packaged path
  itself gives the packaged defaults alone). An override file whose
  top-level key the packaged file does not name is refused:
  `kapso-config.yaml: unknown key 'modes'; the keys are budget, deployment,
  …`. One top-level key is reserved and never read by the engine:
  `benchmark`, the runners' own settings. The specialised loaders go
  (`load_mode_config`, `load_platform_defaults`,
  `load_deployment_defaults`, `load_experience_defaults`,
  `load_harness_defaults`, `resolve_inference_config`): every consumer
  reads its block from the one dict. `deep_merge` stays as the merge.
  `overrides(config_path) -> list[str]`: the dotted paths the override
  file sets, for the doctor.
- **The packaged file's top-level keys**, the whole schema at the top
  level: `hosts`, `inference`, `preflight`, `gates`, `deployment`,
  `harness`, `experience`, `search_strategy`, `knowledge_search`,
  `learner`, `retry`, `models`, `budget`, `inbox`,
  `evaluation_maintainer`, `learning`, and the reserved `benchmark`.
  What `GENERIC` carried is top-level; what `defaults` carried is merged
  into its blocks (`search_strategy.params.cost`, `models.embedding`,
  `budget.checkpoint_heartbeat_seconds`, `retry.request_timeout_seconds`,
  `inbox`). `MINIMAL` is gone: a config that turns things off is an
  override file a person writes, and the configuration page shows one.
- **The hosts table and the roles.**

  ```yaml
  hosts:                       # the coding-agent CLIs a build may run on, and what each is asked for
    claude_code: {model: claude-opus-5, auth_mode: oauth}
    codex:       {model: gpt-5.6-sol, effort: xhigh}
  search_strategy:
    type: generic
    params:
      host: claude_code        # every session runs here with the host's model unless its role says otherwise
      ideation:                # a role: cli, model, effort, timeout (seconds; none = no deadline) override the host's
        gates: [research, experiment_history, repo_memory]
        candidates_per_member: 3
        # ensemble: [{cli, model?, effort?, lens?}, …], selector: {cli, model?, effort?},
        # lens_planner: {cli, model?, effort?, timeout}, ensemble_time_split: {…}
      implementation:
        gates: [research, repo_memory]
        # fallback_model: a second model tried once when the session crashes
      judge: {}
      gate_failure_policy: warn
      parent_policy: best
      node_expansion_value: 1
      …
  ```

  A host entry is `model` plus whatever the adapter takes as its own
  settings (`auth_mode`, `effort`, `vertex_project`, …); `agents.yaml`
  keeps the adapters' registry and their structural defaults and loses
  `default_model` and `default_debug_model` (the config is the one home
  of a model name, Rule 1), so `CodingAgentFactory.build_config` requires
  a model. A role resolves as: its `cli`, else `params.host`; its `model`,
  else the host entry's; its `effort`, else the host entry's; the host
  entry's other keys as the session's agent settings. A role naming a
  host the table lacks is refused: `search_strategy.params.judge.cli:
  gemini is not in hosts; add hosts.gemini: {model: …}`. The verification
  session runs on the implementation role (as WP2 made it), the harness
  setup session and the difficulties reconstruction too; the lens
  planner, the ensemble members and the selector are specs of their own
  under `ideation` whose `model` may now be left to the host's. The
  former `coding_agent` and `feedback_generator` blocks and the flat
  `idea_generation_model`, `implementation_model`, `implementation_cli`,
  `auth_mode`, `effort`, `ideation_timeout`, `implementation_timeout`,
  `ideation_gates`, `implementation_gates`, `ideation_ensemble`,
  `ideation_selector`, `ideation_lens_planner`,
  `ideation_candidates_per_member`, `ensemble_time_split`,
  `implementation_fallback_model`, `web_search` and `implementation_web`
  parameters go. `evaluation_maintainer` names its session the same way
  (`cli`, `model`, `effort`; `null` when off).
  `kapso.execution.search_strategies.generic.roles.resolve_role(config,
  role) -> SessionRole(cli, model, effort, timeout, settings)` is the one
  resolver, and the preflight derives the build's session specs from it,
  so `kapso doctor build` names exactly the sessions a build will run.
- **`--coding-agent <cli>`** on `kapso build` and `build(coding_agent=)`
  set `search_strategy.params.host` for the campaign: every role without
  its own `cli` runs there with that host's model. Recorded in the launch
  record and fingerprinted by the checkpoint as today. The benchmark
  runners' flag means the same.
- **The preflight pairs a host with its model** before any session runs:
  `claude_code` serves `claude-*` models and nothing else, `codex` serves
  everything but `claude-*`; a role whose model its host cannot serve is a
  failed row naming the key (`hosts.codex.model`, or the role's own) and
  the fix. The live tier (`--models`) stays the real probe.
- **The strategy's parameters are a known set**: `search_strategy.params`
  is validated against the names the generic strategy reads (listed in
  one place beside the reads); an unknown name is refused by name. The
  packaged file carries every default the strategy once held as a literal
  (`gate_failure_policy`, `parent_policy`, `node_expansion_value`, the
  gate lists, `candidates_per_member`), and the strategy reads its
  parameters without literal defaults; tests that construct it directly
  take `tests/strategy_support.generic_params(**overrides)`, the packaged
  parameters with overrides.
- **The budget block**, in the `Budget` handle's words:

  ```yaml
  budget:
    experiments: 10            # the experiment cap when the brief and the call name none
    minutes: null              # the wall clock, none = unbounded
    usd: null                  # the model spend, best effort
    reserve_minutes: 10        # kept out of the search for finishing: the last attempt's verification and judgment, and the delivery
    min_iteration_seconds: 60  # the static admission floor
    min_agent_timeout_seconds: 60
    checkpoint_heartbeat_seconds: 60
    fidelity: {…}
  ```

  `DEFAULT_MAX_ITERATIONS` leaves the facade for `budget.experiments`;
  `time_budget_minutes`, `cost_budget_usd` and
  `finalization_reserve_minutes` are renamed; `BudgetSpec.resolve` reads
  the new names. The engine's seconds stay internal.
- **The budget's end.** The implementation session is clamped against
  the searchable remainder (the budget less the reserve), as today. The
  sessions that finish an attempt, verification and the judge, are
  clamped against the whole remainder: they may spend the reserve, which
  is what it is for. A session whose clamp would be the floor
  (`min_agent_timeout_seconds`) is not launched: the attempt records what
  is missing by name (`verification: unverified, no time left`; the judge:
  `evaluation_valid: false`, feedback `the budget left no time for the
  judge`), and the campaign stops with `budget_exhausted` and a detail
  naming it. An iteration is admitted only when the searchable remainder
  covers the larger of `min_iteration_seconds` and the last completed
  iteration's own duration (the first iteration is always admitted); the
  stop detail says `the remaining 8 min would not cover an attempt (the
  last took 14 min)`. The trace's budget line says which budget won when
  the brief and the launch both named one.
- **The judge's retry.** When the judge's answer carries no tags, the
  retry resumes the judge's own session with the nudge
  (`agent.resume(cli_session_id, RETRY_PROMPT)`, both hosts), and the run
  entry of that invocation carries `retry: "tags missing"` (one optional
  key added to WP6's run entry; the trace prints it on the run's line).
  A judge invocation that ended at its deadline is not retried: the
  attempt is rejected with `the judge's session ended at the budget's
  deadline`. The cards parser treats `none`, `false`, `null` and an empty
  tag as no card, and the prompt asks for `none`.
- **The attempt's commit.** `SearchNode.commit`, the branch head when the
  attempt is evaluated; in the checkpoint, the trace's attempt block
  (`commit`) and its text line.
- **The task statement for every build.** `kapso_task.md` is written for
  every campaign, harness or not: the brief whole, the budget, the
  evaluation and data references, the domain statement (the setup
  session's, when a harness has one) and the prepared resources. The
  generic handler keeps `problem_description`, `eval_dir` and `data_dir`
  and renders the brief with the two reference lines and nothing else; the
  evaluation contract (`kapso_evaluation/result.json`, no interactive
  output) lives in the implementation prompt, once. `build(context=)`,
  `build(additional_context=)` and `ProblemHandler(additional_context=)`
  go; the launch record drops both keys and its schema version is 2.
- **The web is a host capability, and a harness that forbids it lists a
  hook.** Implementation and ideation sessions get the live web on both
  hosts (Claude Code's `WebSearch` and `WebFetch`, Codex's `--search`).
  A domain whose protocol forbids it lists a `deny-web` hook on the
  module; the trading example gains one on `implementation`
  (`PreToolUse` on `WebSearch|WebFetch` and on the shell's `curl`/`wget`,
  and on Codex's web search where its hooks see it, verified in the proof
  run). The `--disallowedTools` path for the web goes with the knob.
- **The axes are the planner's.** The lens planner's first plan names
  the design axes of the solution space it derived from the goal and the
  ideation page (an `<axes>` tag, a numbered list), stored in
  `lens_plan.json` and the history; the replanner receives the axes it
  named and may revise them under the same contract (every axis
  statused); the judge's prompt renders the plan's axes when a plan
  exists and otherwise asks the judge to name the axes it sees in the
  goal and the domain guidance. `DESIGN_AXES_DEFAULT` (five ML axes in
  engine code) goes.
- **The engine's own sessions in the record.** The difficulties
  reconstruction is staged like every session (`difficulties/<branch>`,
  the implementation role's host) and its prompt reads the branch (`git
  log` and `git diff --stat` against the parent) before it concludes what
  was lost. The empty-workspace initialisation session (a model call to
  write an empty `main()`) is deleted: the workspace writes the file.
  Every build session mounts only the servers the engine stages
  (`strict_mcp_config`), and each session's Claude MCP config lives under
  its own session directory, so ensemble members no longer share one.
- **The harness directory is read-only to sessions.** The staging merges
  the engine's own `protect-harness` hook first into every session's
  hooks file when a harness is staged (`PreToolUse` on the file tools on
  both hosts, as the trading example's `protect-prepared`), denying a
  write under the harness root with the reason; the setup session's
  guidance says to fix the environment, never the harness, and to report
  a harness that needs a change in its statement; the staging's refusal
  of a changed harness names the change and the way out.
- **The evaluation directory's rule**, stated: a candidate may leave data
  and reports under `kapso_evaluation/` (`result.json`, predictions, a
  profile); code or an executable added there is a tamper and is rejected
  by name (what `verify_evaluation_tree` already does with
  `PROTECTED_SUFFIXES` and the executable bit). `result.json` stays where
  it is. In `docs/build/evaluation.mdx` and the governance document.
- **`kapso doctor`**: the first line names the layers, `config: packaged
  defaults + /path/kapso-config.yaml (overrides: search_strategy.params.host,
  hosts.codex.model)`; `--show-config` prints the effective config as YAML
  and exits; `--json` carries `config` (the effective config, WP6's
  reserved key) and `overrides` (the dotted paths).
- **The maintainer is off by default**: `evaluation_maintainer: null` in
  the packaged file with the page saying what turning it on does.
- **The benchmark configs** are override files: the primary mode's blocks
  at the top level in the new shape, the runner's own settings under
  `benchmark:`; the secondary modes (`MINIMAL`, `FAST_DEBUG`) are deleted.
  The runners drop `--mode`, write their run-shaped settings as an
  override file over their own (`.kapso_runtime/config.yaml` as today, now
  an override file) and pass it as `config_path`.

**Consumed.** WP1's `Budget` handle and launch record; WP2's staging
(`stage_harness_for`, `StagedHarness.merged_agent_specific`,
`merge_hooks`, `harness.settings`) and task statement; WP3's experience
settings (folded into the resolver's dict, the derived keys computed in
the experience package); WP6's session record (`run_entry`, extended by
`retry`), trace (`attempts[].commit`, the run line) and `doctor --json`
(`config` filled). Frozen once reviewed; a change afterwards is a note
here and a line to WP5 (`hosts` is there for `deployment` when it wants
it), WP7 (`--coding-agent` is the host; `doctor --show-config`; no `-m`),
WP8 (override files with `benchmark:`; the web rules as hooks; the
handlers' prose) and WP9 (S1's number).

## Ownership

Edits: `src/kapso/core/config.py`, `src/kapso/config.yaml`,
`src/kapso/core/preflight.py`, `src/kapso/core/cli_inference.py`,
`src/kapso/cli/{build,doctor,watch,inbox}.py`, `src/kapso/kapso.py` (the
constructor, `build()`'s arguments, the launch record, the context),
`src/kapso/execution/{orchestrator,budget,inbox,run_checkpoint}.py`,
`src/kapso/execution/search_strategies/base.py` (`commit`),
`src/kapso/execution/search_strategies/generic/*` (the parameter reading,
`roles.py` new, the prompts, the judge, the reconstruction, the planner),
`src/kapso/execution/coding_agents/{factory.py,agents.yaml}`,
`src/kapso/execution/coding_agents/session_record.py` (`retry`),
`src/kapso/execution/trace.py` (the commit, the retry, the budget line),
`src/kapso/execution/experiment_workspace/*` (the initialisation),
`src/kapso/environment/handlers/{base,generic}.py`,
`src/kapso/harness/{staging,task_statement}.py` and the engine hook under
`src/kapso/harness/engine_hooks/`, `src/kapso/gated_mcp/host_session.py`,
`src/kapso/experience/ingest.py` and the experience settings,
`src/kapso/knowledge_base/learners/defaults.py`, `benchmarks/*/config.yaml`
and `benchmarks/*/runner.py` (and `relbench/campaign.py`,
`ioai2026/past_learning/`), `examples/ml_model_development/e2e/`,
`examples/harnesses/trading/` (the `deny-web` hook), the docs named in
change 12, `skills/*/kapso/SKILL.md` (the lines that say `-m`), `tests/`.

Reads, never edits: the harness manifest and `check` (WP2; the manifest
gains no key), the experience store and grammar (WP3), the deployment
package (WP5), the plugin (WP7), `tests/semantic/` (WP9), the learning
crews' prompts and configs (`learning.*`).

## Changes

1. **The config as two layers, modes gone.** `load_config` resolves the
   effective config; the unknown-key refusal and the reserved `benchmark`
   key; `overrides()`; the specialised loaders deleted and their callers
   reading the dict (the facade's constructor, the orchestrator, the
   preflight's `_mode_block` gone, the doctor, `watch`, `inbox`, the host
   session, the ingest, the learner defaults, the inference layering, the
   experience settings computed in `kapso.experience` from the dict, the
   harness settings read from `config["harness"]`). The packaged file
   rewritten: `GENERIC`'s blocks at the top level, `defaults` merged in,
   `MINIMAL` deleted, the budget block in the handle's words with
   `experiments: 10`, `evaluation_maintainer: null`. The `mode` argument
   leaves `build()`, `kapso build` (`-m`), `OrchestratorAgent`, the
   preflight's context, the launch record (`RESUME_FROM_RECORD`,
   `FINGERPRINTED_LAUNCH_KEYS`) and the checkpoint's fingerprint (`mode`
   and `mode_config` become `config`, the effective config less `budget`;
   the checkpoint schema is 6). Tests: `test_config_resolution.py` (the
   merge, the refusal with the key list, the reserved key, the packaged
   file resolves alone and with an empty override, the override wins,
   lists replace, `overrides()`), the migrated tests
   (`test_config_layering.py` deleted; `test_preflight.py`,
   `test_cli_doctor.py`, `test_cli_build.py`, `test_run_checkpoint.py`,
   `test_inbox_*.py`, `harness_support.py`, `handles_support.py` and the
   rest read the new paths).
2. **The hosts table and the roles.** `hosts` and `params.host`; the
   role blocks; `roles.py` with `resolve_role` and the known-parameter
   set; the strategy reads every session's spec through it (ideation,
   members, selector, lens planner, implementation and its fallback,
   verification, the setup session, the reconstruction, the judge built
   from the `judge` role by the orchestrator); `coding_agent` and
   `feedback_generator` blocks gone; `--coding-agent` sets the host;
   `agents.yaml` loses the model defaults and `build_config` requires a
   model; the preflight's build specs come from `resolve_role` and the
   cli-model pairing row; the maintainer's block in the same words.
   Tests: `test_session_roles.py` (the precedence host → role, the
   missing host refused, the flag routes every role, each engine session
   asks the resolver, the pairing row), `test_preflight.py` extended.
3. **The parameters single-sourced.** Every literal default into the
   packaged file; the strategy requires its keys; unknown parameters
   refused; `tests/strategy_support.generic_params`. Tests: the
   refusal, the packaged parameters all known, the support helper used
   by the direct-construction tests.
4. **The axes are the planner's.** The `<axes>` tag in both planner
   prompts and the plan file; the replanner's contract over the plan's
   axes; the judge's prompt rendering the plan's axes or asking for them;
   `design_axes` and `DESIGN_AXES_DEFAULT` deleted; the RelBench config's
   axes move into its handler's problem context until WP8. Tests:
   `test_lens_planner.py` rewritten (the plan carries axes, the replanner
   receives them, a plan without axes is refused), `test_feedback_generator.py`
   (the prompt with and without a plan), `test_relbench_integration.py`.
5. **The task statement for every build; the context gone.**
   `_write_task_statement` for every campaign; the generic handler's
   prose and `additional_context` deleted; the evaluation contract in the
   implementation prompt once; `build(context=, additional_context=)`
   gone; the launch record schema 2; the trace fixtures regenerated.
   Tests: `test_task_statement.py` (a build without a harness has the
   file; the handler's context is the brief and the references), the
   facade and record tests migrated.
6. **The web as a hook.** `implementation_web`, `web_search` and the
   disallowed-tools path deleted; the implementation and ideation sessions
   get the web on both hosts; the trading example's `deny-web` hook on
   implementation; the harness reference's recipe. Tests:
   `test_implementation_web.py` deleted and its helpers moved to
   `tests/implementation_support.py`; `test_harness_hooks.py` (the hook
   denies the three tools with the reason).
7. **The budget's end.** The finishing sessions' clamp; no session on the
   floor; admission from the last iteration's duration; the stop detail;
   the trace's budget line. Tests: `test_budget_end.py` (each rule with a
   stubbed clock: the verification and the judge get the reserve, a
   floored session is not launched and the attempt says why, admission
   refuses with the detail, the first iteration is always admitted).
8. **The judge.** The retry resumed with `retry` in the run entry; no
   retry after a deadline; the cards parser; `SearchNode.commit` in the
   checkpoint and the trace. Tests: `test_judge_retry.py`,
   `test_feedback_generator.py` (the parser), `test_trace.py` (the commit
   and the retry on the goldens).
9. **The engine's own sessions.** The reconstruction staged, recorded and
   reading the branch; the initialisation session deleted;
   `strict_mcp_config` on every build session; the MCP config per session
   directory. Tests: `test_engine_sessions.py` (the reconstruction has a
   record and its prompt names the branch; two members have two config
   directories; the workspace initialises with no agent).
10. **The harness directory read-only.** The engine hook under
    `src/kapso/harness/engine_hooks/protect_harness/`, merged first by
    the staging on both hosts; the setup guidance line; the refusal's
    message. Tests: `test_protect_harness.py` (the merged file's first
    entry, the script's decision on both hosts' event shapes, the
    message).
11. **The benchmarks and the examples.** The four override files and the
    past-learning one, `benchmark:` for the runners' keys; the runners
    without `--mode`, their runtime config an override file; the e2e
    example's two files. Tests: `test_benchmark_configs.py` (each file
    resolves through the resolver with no unknown key; each runner's
    runtime config resolves; the orchestrator constructs from each with
    the provider boundary stubbed, as `harness_support.real_orchestrator`
    does).
12. **The doctor and the pages.** The config line, `--show-config`, the
    JSON keys; `docs/reference/configuration.mdx` rewritten (the two
    layers, an override file, the hosts and roles, the budget block, the
    unknown-key refusal, `--show-config`); `cli.mdx` (the build's rows,
    the doctor's flag), `kapso-api.mdx` (the signature), `docs/build/
    resume-and-budgets.mdx` (the reserve and the budget's end),
    `docs/build/evaluation.mdx` and `docs/research/evaluation-governance.md`
    (the directory's rule), `docs/reference/harness.mdx` (the engine
    hook, the web recipe), the `docs/evolve/*.mdx` snippets, the
    benchmark pages, the examples' READMEs, the skills' lines;
    `test_no_retired_names.py` extended with the names this package
    retires; the docs coverage check. Tests: `test_cli_doctor.py`.
13. **The proof run, S1's number, the findings, the master's row.**

## Tests

- Syntactic: the files named per change above. Goldens: the trace's
  fixtures regenerated for the record's new keys (`commit`, `retry`, the
  launch record v2), `kapso doctor --json` on the packaged config.
  Negative cases: an unknown top-level key, an unknown parameter, a role
  on a missing host, a model its host cannot serve, a plan without axes, a
  stale file with `modes`.
- Proof run, on a fresh machine from the wheel: (a) the churn example,
  no harness, `--coding-agent codex` on the packaged config, forty-five
  minutes: the trace shows every session on Codex with the host's model,
  and the minutes to the first candidate and to delivery are S1's numbers;
  (b) the trading example with `--harness` and an override file naming
  `host: codex` and `judge: {cli: claude_code}`, forty minutes and the
  default reserve: the last attempt verified and judged inside the
  reserve, no session on the floor, the stop detail at the budget's end,
  the `deny-web` hook's denial in the trace on Claude and the host-facts
  canary on Codex, the `protect-harness` hook's denial from a scripted
  write under the harness root; (c) a stale config with `modes:` refused
  at launch by name, `kapso doctor --show-config` and `--json` archived;
  (d) the four benchmark runners' smoke on the development box (no
  benchmark data on the fresh machine). Archived under
  `scripts/redesign/runs/wp4/`, one file per run.
- Semantic hooks: S1's time-to-first-candidate and time-to-delivery on
  (a), recorded here; S4's reading of (b)'s trace by Codex and Claude Code
  on one question, why the campaign stopped and whether the last attempt
  was finished, graded against the record.

## Acceptance

- `src/kapso/config.yaml` has no `modes` or `default_mode`;
  `load_config()` with no path returns it, and with an override file
  returns the merge; `grep -rn "load_mode_config\|modes\[" src tests` is
  empty; `test_no_retired_names.py` lists the retired names.
- `kapso build --config x.yaml` where `x.yaml` names `modes:` fails
  before any session with the unknown-key message naming the keys.
- `kapso build --coding-agent codex` runs every session on Codex with
  `hosts.codex.model`; the trace's sessions say so; `kapso doctor build`
  lists the same sessions and refuses a `claude-*` model on Codex by key.
- A direct `GenericSearch(...)` with a parameter the strategy does not
  read raises naming it; the strategy has no `self.params.get(key,
  literal)` left.
- The lens plan file carries `axes`; the judge's prompt renders them; no
  `design_axes` anywhere.
- A build without a harness has `kapso_task.md`; `build()` has no
  `context` or `additional_context`; the generic handler's context is the
  brief and the references.
- A campaign at its time budget on the proof run shows, in its trace,
  verification and judgment of its last attempt inside the reserve and a
  stop detail naming the budget's end, with no run killed on the floor.
- A judge whose first run had no tags shows two runs in one session, the
  second's entry `retry: tags missing`; a judge cut by the deadline shows
  one run and the attempt's rejection names the deadline.
- Every attempt in the trace has a `commit`; the reconstruction's session
  has a record; `.claude_mcp` directories are per session.
- A write under the harness root from a session is denied with the
  reason on both hosts; the setup prompt carries the line.
- The four benchmark override files and the runners' runtime files
  resolve; the runners have no `--mode`.
- `kapso doctor` prints the config line; `--show-config` prints YAML;
  `--json` has `config` and `overrides`.
- The pages named in change 12 say what the code does; the docs coverage
  check and `mint validate` pass; the gate is green at every commit.

## Risks

- The parameter rename touches many tests and the two benchmark configs
  that set most parameters: the table in the Interface is the migration
  map, and `test_no_retired_names.py` catches a leftover.
- Codex's hooks may not see its native web search: verified on the
  fresh machine; if they do not, the `deny-web` hook still catches
  `curl`/`wget`, the page says what the hook covers on each host, and the
  finding goes to WP8 with the RelBench port.
- Admission from the last iteration's duration can stop a campaign that
  would have fit a shorter attempt: the detail says why, the static floor
  still applies, and a person who wants the attempt sets a bigger budget.
- Resuming the judge's session on Codex depends on `codex exec resume`,
  which the adapter already does for the inbox; a host that cannot resume
  fails loud rather than starting a fresh session.
- Refusing unknown top-level keys refuses files written before this
  package: pre-release, no shim (Rule 7); the message lists the keys.
- The default reserve of ten minutes shortens the search of a short
  build: the proof run's numbers decide whether it stays; the budget page
  says how to lower it.

## Review

The cross-model review of this plan (`scripts/redesign/review.sh`) and
the answers, then the owner's go.
