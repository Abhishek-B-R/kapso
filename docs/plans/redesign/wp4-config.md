# WP4: Config without modes

2026-10-26. Owner: the redesign's implementer, autonomously, the owner
checking the decisions. Branch `wp4-config` off `redesign` at `55a92430`.
Size: L (the config's shape touches every verb, the strategy's parameter
reading, four benchmark runners and the pages; the findings the earlier
packages left here add the budget's end and the judge's retry). Revised
after the cross-model review (the Review section).

## Scope

The config becomes two layers resolved by one function: the packaged
defaults and one override file, the packaged file being the schema an
override is checked against at every depth; `modes`, `default_mode` and
the `mode` argument go everywhere (the facade, the CLI, the orchestrator,
the preflight, the launch record, the checkpoint, the host session, the
ingest). The build's sessions are named by role over a table of hosts, so
`--coding-agent` sets the default host and a host is never asked for a
model it cannot serve. The retirements: `design_axes` (the planner names
the axes from the goal and the ideation page), `additional_context` and
`context` on `build()` with the generic handler's prose (the brief and the
engine's contract, each said once), the strategy presets file. The web
switches stay as the engine's capability boundary, one per role, and a
harness that forbids the web lists a hook. The benchmark configs become
override files and their runners lose `--mode`, with a smoke test each
through the runner's own path; `kapso doctor` prints the effective
config. And the findings the earlier packages left for this package: the
budget's end (finishing obligations protected, a launch predicate instead
of a floor, admission from the last round's duration, the reserve derived
from the obligations when not set), the judge's retry (the outcome
inspected first, the session resumed, its reason in the record, an
`unjudged` attempt when the budget cuts it), the judge's cards parser, the
attempt's commit in the record, the reconstruction reading the branch
before it concludes, the engine's own sessions in the record, the harness
directory protected from the file tools, the evaluation directory's rule
stated, the maintainer's default decided with its knobs in the config.

**Not in scope.** The benchmarks' harness ports (WP8: this package
converts their configs and smoke-tests their runners; the handlers'
`get_problem_context` prose stays in the benchmark handlers until then,
and their constructors are edited here). `deploy(target=)` and the
`deployment` block's shape (WP5; the block is unchanged here, read
through the resolver). The plugin's skills reading the effective config
(WP7; this package tells it what changed). The learning crews' session
specs (`learning.*`, already `{cli, model, effort}`), the `inference`
block and the `learner` block, which keep their shape. A lighter ideation
for small briefs (WP1's finding): a measurement first, not a change. The
docs' new navigation (WP10; this package rewrites the pages it changes).
Moving the judge into a worktree (WP2's Q2.9): declined, the judge reads
the campaign and the diff it is handed. Codex-side isolation from a
user's own `config.toml` servers: Codex hooks need the user config (WP2's
host fact), so a build session on Codex carries them; a finding for WP7.

## Interface

**Exposed.**

- **The resolver**, `kapso.core.config.load_config(config_path=None) ->
  dict`: the effective config, the packaged `src/kapso/config.yaml`
  deep-merged with the override file at `config_path` (nested mappings
  merge key by key; scalars and lists replace; `None` or the packaged path
  itself gives the packaged defaults alone). **The packaged file is the
  schema**: at every depth, a mapping in the override may name only the
  keys the packaged mapping names at that path, refused by name
  (`kapso-config.yaml: budget: unknown key minute; the keys are
  experiments, minutes, …`), except under the open namespaces (`hosts`,
  `inference.roles`, `gates`, `knowledge_search.params`,
  `search_strategy.params.session_env_defaults`, `benchmark`, and the
  items of lists); a host entry's keys are `model`, `effort` and the
  adapter's own settings named in `agents.yaml`. One top-level key is
  reserved and never read by the engine: `benchmark`, a benchmark
  runner's own settings. `read_yaml(path)` reads a file that is not a
  config (the agents registry, a harness manifest). The specialised
  loaders go (`load_mode_config`, `load_platform_defaults`,
  `load_deployment_defaults`, `load_experience_defaults`,
  `load_harness_defaults`, `resolve_inference_config`): every consumer
  reads its block from the one dict; the experience settings derived
  from four blocks are `kapso.experience.experience_settings(config)`.
  `deep_merge` stays as the merge. `override_paths(config_path) ->
  list[str]`: the dotted paths the override file sets, for the doctor.
  The blocks with validators of their own keep them and gain the ones
  this package adds: the roles and their specs (types included), the
  budget, the maintainer, the fidelity block, the ensemble's time split,
  the policy enums (`gate_failure_policy`, `parent_policy`). What the walk
  cannot catch, and is left: a wrong value where a free string is allowed
  (a model name, a role name under `inference.roles`).
- **The packaged file's top-level keys**: `hosts`, `inference`,
  `preflight`, `gates`, `deployment`, `harness`, `experience`,
  `search_strategy`, `knowledge_search`, `learner`, `retry`, `models`,
  `budget`, `inbox`, `evaluation_maintainer`, `learning`, and the reserved
  `benchmark`. What `GENERIC` carried is top-level; what `defaults`
  carried is merged into its blocks. `MINIMAL` is gone: a config that
  turns things off is an override file a person writes, and the
  configuration page shows one. `strategies.yaml` and the strategy
  factory's presets go: the config's `search_strategy.params` is the one
  home of the strategy's parameters.
- **The hosts table and the roles.**

  ```yaml
  hosts:                       # the coding-agent CLIs a build may run on, and what each is asked for
    claude_code: {model: claude-opus-5, auth_mode: oauth}
    codex:       {model: gpt-5.6-sol, effort: xhigh}
  search_strategy:
    type: generic
    params:
      host: claude_code        # the default host: every role without a cli of its own runs here with the host's model
      ideation:                # a role: cli, model, effort, timeout (seconds; none = the budget's clamp alone), web
        gates: [research, experiment_history, repo_memory]
        candidates_per_member: 1
        web: true              # the native web tools; a harness that forbids the web on a module lists a hook
        # ensemble: [{cli, model?, effort?, lens?}, …], selector: {cli, model?, effort?},
        # lens_planner: {cli, model?, effort?, timeout}, ensemble_time_split: {…}
      implementation:
        gates: [research, repo_memory]
        web: true
        # fallback_model: a second model tried once when the session crashes
      judge: {}
      gate_failure_policy: warn
      parent_policy: best
      node_expansion_value: 1
      …
  ```

  A host entry is `model` plus the adapter's own settings (`auth_mode`
  for Claude Code, `base_url` and `auth_token_env` for the OSS adapter,
  `vertex_project` and friends for Vertex), the keys `agents.yaml` names
  under the adapter's `settings`; `effort` applies to every host.
  `agents.yaml` keeps the adapters' registry, their structural
  `agent_specific` defaults and, new, `serves` (`claude`, `openai` or
  `any`: the model family the adapter can be asked for) and `settings`;
  it holds no model name (the config's hosts table is the one home, Rule
  1), so `CodingAgentFactory.build_config` requires a model. A role
  resolves as: its `cli`, else `params.host`; its `model`, else the host
  entry's; its `effort`, else the host entry's; the host entry's other
  keys as the session's settings. A role naming a host the table lacks is
  refused: `search_strategy.params.judge.cli: gemini is not in hosts; add
  hosts.gemini: {model: …}`. The precedence of a build session's agent
  settings: `agents.yaml`'s structural defaults, then the host entry's
  settings, then the role's own keys, then the staging's merge (so the
  structural defaults reach build sessions, WP2's finding). The
  verification session runs on the implementation role (as WP2 made it),
  the harness setup session and the difficulties reconstruction too; the
  judge is the harness's `feedback` module and WP6's `feedback/<branch>`
  label, no new module. The lens planner, the ensemble members and the
  selector are specs of their own under `ideation`, whose `model` may be
  left to the host's; a member's `base_url` and `auth_token_env` move to
  the OSS host's entry. Single-session ideation is the ensemble machinery
  with one member, the ideation role (one session, one candidate, no
  selector): the separate Claude-only path goes, so ideation runs on the
  host it names. The former `coding_agent` and `feedback_generator`
  blocks and the flat `idea_generation_model`, `implementation_model`,
  `implementation_cli`, `auth_mode`, `effort`, `ideation_timeout`,
  `implementation_timeout`, `ideation_gates`, `implementation_gates`,
  `ideation_ensemble`, `ideation_selector`, `ideation_lens_planner`,
  `ideation_candidates_per_member`, `ensemble_time_split`,
  `implementation_fallback_model`, `web_search` and `implementation_web`
  parameters go. `evaluation_maintainer` names its session the same way
  (`cli`, `model`, `effort`, `timeout`, the host's where unset).
  `kapso.core.roles.resolve_role(hosts, params, role) -> SessionRole(cli,
  model, effort, timeout, web, settings)` is the one resolver, in `core`
  because the preflight calls it; the preflight's `SessionSpec` stays
  what a requirement row is built from (a cli, a model, an origin), and
  `build_session_specs` maps the resolved roles, members, selector,
  planner and maintainer to it, so `kapso doctor build` names the
  sessions a build will run from the same resolution. `hosts` is not a
  session source: a host no role names is not asked for.
- **`--coding-agent <cli>`** on `kapso build` and `build(coding_agent=)`
  set `search_strategy.params.host` for the campaign: the default host
  for every role without a `cli` of its own, with that host's model.
  Recorded in the launch record as `host` and fingerprinted by the
  checkpoint. The benchmark runners' flag means the same.
- **The preflight pairs a host with its model** from the adapter's
  `serves`: `claude` (`claude_code`) serves `claude-*` models and nothing
  else, `openai` (`codex`) everything but them, `any` (the OSS, Vertex and
  other adapters) is not checked statically. One row per distinct pair
  (`codex is asked for claude-opus-5`, failed with the keys that ask and
  the fix); the live tier (`--models`) stays the real probe.
- **The strategy's parameters are a known set**: `search_strategy.params`
  and each role block are validated against the names the generic
  strategy reads, listed in `kapso.core.roles` (the engine's own
  parameters, threaded at launch, are a second set a file may not set).
  The packaged file carries every default the strategy once held as a
  literal (`gate_failure_policy`, `parent_policy`, `node_expansion_value`,
  the gate lists, `candidates_per_member`, the repo memory's policy and
  retries), and the strategy reads its parameters without literal
  defaults; tests that construct it directly take
  `tests/strategy_support.generic_params(**overrides)`.
- **The web.** `ideation.web` and `implementation.web` (true by default)
  are the engine's permission boundary: on Claude Code the two native
  tools leave the allow-list and go on `--disallowedTools`; on Codex
  `--search` is not passed (the Codex ideation runner's `web_search`
  included); the selector and the lens planner follow `ideation.web`. A
  harness whose protocol forbids the web on a module lists a hook there
  (the domain rule, per module); the trading example gains `deny-web` on
  `implementation` (`PreToolUse` on `WebSearch|WebFetch` and on the
  shell's `curl`/`wget`, and on Codex's web search where its hooks see
  it, verified in the proof run). RelBench keeps `implementation.web:
  false` and the past-learning runner both roles off (their protocols);
  the research inference role keeps its own `web_search`.
- **The budget block**, in the `Budget` handle's words:

  ```yaml
  budget:
    experiments: 10            # the experiment cap when the brief and the call name none
    minutes: null              # the wall clock, none = unbounded
    usd: null                  # the model spend, best effort
    reserve_minutes: null      # kept out of the search for finishing; null = derived from the obligations (below)
    min_iteration_seconds: 60  # the static admission floor (seconds; the minutes above are the person's words)
    min_iteration_seconds_insured: null
    min_agent_timeout_seconds: 60   # below this no session is launched
    checkpoint_heartbeat_seconds: 60
    fidelity: {…}
  ```

  `DEFAULT_MAX_ITERATIONS` leaves the facade for `budget.experiments`;
  `time_budget_minutes`, `cost_budget_usd` and
  `finalization_reserve_minutes` are renamed; `BudgetSpec.resolve` reads
  the new names. The engine's seconds stay internal.
- **The budget's end.** Two classes of session. A *search* session
  (setup, ideation and its members, the lens planner, the selector,
  implementation) is clamped against the searchable remainder, the budget
  less the reserve. A *finishing* session completes an attempt (the
  candidate's evaluation run, verification, the judge, the difficulties
  reconstruction): it is clamped against the whole remainder less the
  obligations that follow it, each protected at its floor
  (`min_agent_timeout_seconds`): after the evaluation run, verification
  when the harness verifies, then the judge, then the delivery's
  protected slice (the fidelity policy's measurement slice when fidelity
  is active, as the escrow protects it today; the final checkout
  otherwise, seconds). Unused time flows to the next obligation. The
  maintainer bridge keeps its bounded overrun. **The launch predicate**:
  `BudgetSnapshot.room(obligations_seconds, finishing) -> Optional[float]`
  is the time a session of that class may take (None when unbudgeted); a
  session is launched only when its room is None or at least the floor,
  and its deadline is the smaller of its configured timeout and its room,
  never raised to the floor (an unbudgeted campaign keeps its configured
  timeouts). A session not launched says why: verification `unverified`
  with the reason, the judge `unjudged`, the reconstruction skipped.
  **The `unjudged` attempt**: `SearchNode.unjudged` (empty when judged,
  else the reason: `the budget left no time for the judge`, `the judge's
  session ended at the budget's deadline`, `no tags after a retry`); the
  attempt keeps its score, is not a parent, is never delivered (as WP2's
  `unverified`), and the trace shows it. **Admission**: an ordinary round
  is admitted when the searchable remainder covers the larger of
  `min_iteration_seconds` and the last completed round's duration (no
  history: the floor alone, the exhaustion and affordability checks
  before it as today); an insured campaign (the handler reports a
  deliverable) uses `min_iteration_seconds_insured` alone, the handler
  vouching for its endgame; the fidelity policy's reserved full-size
  attempt keeps its own gate after ordinary admission fails. A round's
  duration is the wall time from its ideation's start to its last lane's
  judgment, recorded on the checkpoint (`round_seconds`) so a resume uses
  the restored history; a continuation of a suspended node is not a new
  round. The stop: `stopped_reason: budget_exhausted` with `stop_detail`
  `attempt_would_not_fit` (admission) or `finishing_cut` (a finishing
  session not launched or cut), two new members of the checkpoint's
  closed set, and the prose (`the remaining 8 min would not cover an
  attempt (the last took 14 min)`) in the status file's note, the log and
  the trace. **The reserve**: `budget.reserve_minutes` set wins, bounded
  by a quarter of the budget (a structural bound, so a short budget keeps
  its search); `null`, the packaged default, derives it each round from
  the obligations: the harness's `verification_minutes` when it verifies,
  the judge's last observed duration (cold start: the floor), the
  delivery's protected slice. The trace's budget line says which budget
  won when the brief and the launch both named one, and the effective
  reserve.
- **The judge's retry.** The invocation's outcome is inspected before its
  output: a first run that ended at its deadline (`deadline_exceeded`
  without `completed_before_kill`) is not retried, the attempt is
  `unjudged` with the deadline reason; a complete answer with no tags
  resumes the judge's own session with the nudge (`agent.resume(
  cli_session_id, RETRY_PROMPT, timeout_seconds=room, reason="tags
  missing")`, both hosts) under a re-computed room, a missing session
  handle raising as a wiring bug; a retry cut at its deadline is
  `unjudged` with the deadline reason, two runs recorded, the second's
  entry `retry_reason: tags missing` and `exit: timeout`; a retry still
  without tags is `unjudged` with `no tags after a retry` (the fabricated
  valid result goes). The reason reaches the run entry through
  `start_run(..., reason=)` before the launch, so an invocation that
  raises still records it (one optional key added to WP6's run entry,
  `retry_reason`; the trace prints it on the run's line; the trace's
  schema is 2). The Claude adapter counts a resumed session's spend as the
  delta of the host's cumulative figure, not the figure twice (host totals
  1.0 then 1.4 give 1.4). The cards parser treats `none`, `false`, `null`
  and an empty tag as no card, and the prompt asks for `none`.
- **The attempt's commit.** `SearchNode.commit`, the branch head when the
  attempt is evaluated (null for an attempt never evaluated: suspended,
  rejected before evaluation); in the checkpoint, the trace's attempt
  block (`commit`) and its text line.
- **The problem text.** The generic handler keeps `problem_description`,
  `eval_dir` and `data_dir` and renders the brief with the two reference
  lines (where the evaluation and the data live) and nothing else; the
  evaluation contract is rendered once, in the implementation prompt, in
  three forms: a provided suite (run it, never edit it,
  `kapso_evaluation/result.json`), a registered one (the maintainer's
  contract, as today), none (build your own under `kapso_evaluation/`);
  the provided case no longer gets the build-your-own text. `build(
  context=)`, `build(additional_context=)` and
  `ProblemHandler(additional_context=)` go; the five benchmark handlers'
  constructors are edited (ALE's domain prose moves into its own
  `get_problem_context`), their prose staying until WP8. The task
  statement stays a harness build's file (without a harness nothing
  mounts or names it; the brief in the prompts is the one problem text).
- **The axes are the planner's.** The lens planner's first plan names
  the design axes of the solution space it derived from the goal and the
  ideation page (an `<axes>` tag, a numbered list), stored in
  `lens_plan.json` and every history record (keep and revise included)
  and validated on reload; the replanner receives the axes it named and
  statuses each before it revises them, so a revision cannot erase an
  unexplored dimension unstatused; the judge's prompt renders the plan's
  axes when a plan exists and otherwise omits the axis-frontier duty
  (nobody consumes it without a planner). `DESIGN_AXES_DEFAULT` goes;
  RelBench's five axes move into its handler's context until WP8.
- **The engine's own sessions in the record.** The difficulties
  reconstruction is staged like every session (`difficulties/<branch>`,
  the trace's label grammar extended), on the implementation role's host,
  and its prompt reads the branch (`git log` and `git diff --stat` against
  the parent) before it concludes what was lost. The build-time inference
  sessions (the repo-memory bootstrap, the commit messages) are recorded
  under `.kapso/sessions/engine/<role>/<n>/` through the adapters' record
  path (the inference client takes the campaign's record root; the
  inference block keeps its shape). The empty-workspace initialisation
  session and `ExperimentWorkspace.with_default_config` are deleted
  (unreachable from the facade). Every build session on Claude Code
  mounts only the servers the engine stages (`strict_mcp_config`) and
  keeps its MCP config under its own session directory (an adapter edit),
  so ensemble members no longer share one.
- **The harness directory is protected from the file tools.** The staging
  merges the engine's own `protect-harness` hook first into every
  session's hooks file whenever a harness is staged, user hooks or none
  (`PreToolUse` on the file tools and the patch headers on both hosts, as
  the trading example's `protect-prepared`; its script's path is the
  package's, not `${PLUGIN_ROOT}`), denying a write under the harness
  root with the reason; the staged record lists it; a shell write is not
  caught here, the hash check at the next staging catches it (WP2's
  decision: a hook is not a boundary). The setup session's guidance says
  to fix the environment, never the harness, and to report a harness that
  needs a change in its statement; the staging's refusal of a changed
  harness names the change and the way out. On Codex a hooks file implies
  `--dangerously-bypass-hook-trust`, so every Codex session with a harness
  carries it.
- **The evaluation directory's rule**, stated: for a provided suite every
  file of the manifest is protected and a new file is rejected when it is
  source (`PROTECTED_SUFFIXES`) or executable, data and reports being
  allowed (`result.json`, predictions, a profile), the leftover
  `result.json` refused at launch; an agent-generated, unregistered
  evaluator is the candidate's to write; a registered one is the
  maintainer's. `result.json` stays where it is. In
  `docs/build/evaluation.mdx` and the governance document.
- **`kapso doctor`**: the first line names the layers, `config: packaged
  defaults + /path/kapso-config.yaml (overrides: search_strategy.params.host,
  hosts.codex.model)`; `--show-config` prints the effective config as YAML
  and exits; `--json` carries `config` (the effective config, WP6's
  reserved key) and `overrides` (the dotted paths).
- **The maintainer is off by default**, its knobs in the config:
  `evaluation_maintainer: {enabled: false, cli: null, model: null, effort:
  null, timeout: null, subsample_seed, calibration_fraction,
  calibration_timeout_seconds, fast_variant_threshold_minutes,
  overhead_factor, max_change_requests, transition_freeze_fraction,
  protected_data_paths}`; the seven literals leave the orchestrator; a
  person turns it on with `enabled: true`.
- **The checkpoint's fingerprint** is the blocks a build reads: `hosts`,
  `search_strategy` (the host override included), `inference`, `retry`,
  `models`, `inbox`, `evaluation_maintainer`; never `budget`, `benchmark`,
  `learning`, `experience`, `gates`, `deployment`, `preflight`, `harness`
  (the harness identity has its own check). The checkpoint schema is 6.
- **The launch record** (schema 2) speaks the handle's words:
  `experiments`, `minutes`, `usd`, `reserve_minutes`, `host`; `mode`,
  `context` and `additional_context` go; the three committed trace
  fixtures are regenerated by the generator, which learns the new keys.
- **The benchmark configs** are override files: the engine's settings at
  the top level in the new shape (the roles, `budget`, `inbox`, `retry`),
  the runner's own under `benchmark:` (`run_defaults`, `knowledge_bank_dir`,
  `session_budget`, `final_eval`, the IOAI preflight's session spec,
  `fetch_huggingface_models`, `use_knowledge_graph`, the past-learning
  harvest); the secondary modes (`MINIMAL`, `FAST_DEBUG`) are deleted. The
  runners drop `--mode` (the RelBench campaign driver too), write their
  run-shaped settings as the merge of their own file and the shaping
  (`ideation.timeout`, `implementation.timeout`, the shared cache, the
  bank serving) to `.kapso_runtime/config.yaml` and pass it as
  `config_path`; the IOAI preflight reads `benchmark.preflight`.

**Consumed.** WP1's `Budget` handle and launch record; WP2's staging
(`stage_harness_for`, `StagedHarness.merged_agent_specific`,
`merge_hooks`, `harness.settings`) and the verdict's `is_deliverable`;
WP3's experience settings (folded into the resolver's dict, the derived
keys computed in the experience package); WP6's session record
(`start_run`, `run_entry`, extended by `retry_reason`), trace
(`attempts[].commit`, `attempts[].unjudged`, the run line, the label
grammar, schema 2) and `doctor --json` (`config` filled). Frozen once
reviewed; a change afterwards is a note here and a line to WP5 (`hosts`
is there for `deployment` when it wants it), WP7 (`--coding-agent` is the
default host; `doctor --show-config`; no `-m`), WP8 (override files with
`benchmark:`; the web rules as hooks when the benchmarks are ported; the
handlers' prose) and WP9 (S1's number). This package supersedes the
interfaces document's precedence paragraph (section 3) and "7. The config
file after this": there is no harness config layer (harness-design
sections 9 and 10), and the blocks it said to keep are reshaped here.

## Ownership

Edits: `src/kapso/core/{config,roles,preflight,cli_inference,agent_manifest,__init__}.py`,
`src/kapso/config.yaml`, `src/kapso/cli/{build,doctor,watch,inbox,experience,harness,learn}.py`,
`src/kapso/kapso.py` (the constructor, `build()`'s arguments, the launch
record, the context, the status heartbeat, deploy's block read),
`src/kapso/execution/{orchestrator,budget,inbox,run_checkpoint,cost_estimator,trace}.py`,
`src/kapso/execution/search_strategies/{base,factory,_template,__init__}.py`
(`strategies.yaml` deleted), `src/kapso/execution/search_strategies/generic/*`
(the parameter reading, the ideation unification, the prompts, the judge,
the reconstruction, the planner), `src/kapso/execution/coding_agents/{factory.py,agents.yaml,session_record.py}`
and the two adapters (`claude_code_agent.py`: the resumed session's
cost, the MCP config directory, the retry reason; `codex_agent.py`: the
retry reason), `src/kapso/execution/experiment_workspace/experiment_workspace.py`,
`src/kapso/environment/handlers/{base,generic}.py`,
`src/kapso/harness/staging.py` and the engine hook under
`src/kapso/harness/engine_hooks/`, `src/kapso/gated_mcp/{host_session,presets}.py`,
`src/kapso/experience/{ingest,sources,__init__}.py`,
`src/kapso/knowledge_base/learners/defaults.py`, `src/kapso/deployment/base.py`
(the one line that read the deleted loader), `benchmarks/*/config.yaml`,
`benchmarks/*/runner.py`, `benchmarks/*/handler.py` (the constructors),
`benchmarks/relbench/campaign.py`, `benchmarks/ioai2026/preflight.py`,
`benchmarks/ioai2026/past_learning/{config.yaml,runner.py,handler.py}`,
`examples/ml_model_development/e2e/` (the configs and the runner),
`examples/harnesses/trading/` (the `deny-web` hook), the docs named in
change 12 (`docs/research/kapso-interfaces.md` included),
`skills/*/kapso/SKILL.md` (the lines that say `-m`), `tests/`.

Reads, never edits: the harness manifest and `check` (WP2; the manifest
gains no key), the experience store and grammar (WP3), the deployment
package beyond the one line (WP5), the plugin (WP7), `tests/semantic/`
(WP9), the learning crews' prompts and configs (`learning.*`).

## Changes

1. **The config as two layers, modes gone.** `load_config` resolves the
   effective config; the walk against the packaged schema with the open
   namespaces; the reserved `benchmark` key; `read_yaml` for the registry;
   `override_paths()`; the specialised loaders deleted and every caller
   reading the dict (the inventory above); the packaged file rewritten
   (`GENERIC`'s blocks at the top level, `defaults` merged in, `MINIMAL`
   deleted, the budget block in the handle's words, the maintainer block
   with its knobs and `enabled: false`). The `mode` argument leaves
   `build()`, `kapso build` (`-m`), `OrchestratorAgent`, the preflight's
   context, the launch record and the checkpoint's fingerprint (narrowed
   to the build's blocks; schema 6). Tests: `test_config_resolution.py`
   (the merge, the refusal at depth with the key list, the open
   namespaces, the reserved key, the packaged file resolves alone and with
   an empty override, the override wins, lists replace, `override_paths`,
   the benchmark files resolve), the migrated tests
   (`test_config_layering.py` deleted; `test_preflight.py`,
   `test_cli_doctor.py`, `test_cli_build.py`, `test_run_checkpoint.py`
   (a `benchmark` edit does not change identity, a role's host does),
   `test_inbox_*.py`, `harness_support.py`, `handles_support.py`,
   `test_deployment_registry.py`, `test_observability.py`,
   `test_cli_harness.py`, `test_cli_experience.py`, `test_cli_inference.py`
   and the rest read the new paths).
2. **The hosts table and the roles.** `hosts` and `params.host`; the role
   blocks with `web`; `kapso.core.roles` with `resolve_role`, the specs'
   resolvers, the known-parameter sets and the enum checks; the strategy
   reads every session's spec through it; single ideation as an ensemble
   of one, the member, selector and planner sessions through the factory
   on their own hosts; the setup session, the verification, the
   reconstruction and the judge (built by the orchestrator from the
   `judge` role) likewise; `coding_agent` and `feedback_generator` blocks
   gone; `--coding-agent` sets the host; `agents.yaml` gains `serves` and
   `settings` and loses the model defaults, `build_config` requires a
   model, the build sessions' precedence (the structural defaults first);
   the preflight's build specs from the resolver and the pairing row; the
   maintainer's block in the same words. Tests: `test_session_roles.py`
   (the precedence host then role, the missing host refused, the flag
   routes every role without a cli, the pairing row, the known sets),
   `test_session_construction.py` (the `CodingAgentConfig` each
   construction site produces for a Claude host and a Codex host:
   `agent_type`, `model`, `effort`, `web`, the merged settings),
   `test_preflight.py` extended.
3. **The parameters single-sourced.** Every literal default into the
   packaged file; the strategy requires its keys; unknown parameters
   refused; `tests/strategy_support.generic_params`; the presets file and
   machinery deleted. Tests: the refusal, the packaged parameters all
   known, the support helper used by the direct-construction tests.
4. **The axes are the planner's.** The `<axes>` tag in both planner
   prompts, the plan file and every history record, validated on reload;
   the replanner's contract over the plan's axes; the judge's prompt
   rendering the plan's axes or omitting the duty; `design_axes` and
   `DESIGN_AXES_DEFAULT` deleted; RelBench's axes into its handler's
   context. Tests: `test_lens_planner.py` rewritten (the plan carries
   axes, a plan without axes is refused on reload, keep and revise carry
   them, the replanner statuses them), `test_feedback_generator.py` (the
   prompt with and without a plan), `test_relbench_integration.py`.
5. **The problem text; the context gone.** The generic handler's prose
   and `additional_context` deleted, the five benchmark constructors
   edited; the evaluation contract in the implementation prompt in its
   three forms; `build(context=, additional_context=)` gone; the launch
   record schema 2 in the handle's words; the fixture generator and the
   fixtures. Tests: `test_problem_text.py` (the handler's context is the
   brief and the references; the three contract forms; the provided case
   says run), the facade and record tests migrated.
6. **The web as the engine's boundary and a harness hook.** `web` per
   role on both hosts and the ideation runner; the trading example's
   `deny-web` hook on implementation; the harness reference's recipe.
   Tests: `test_web_boundary.py` (the allow-list, the disallowed tools and
   `--search` follow the role's `web` on every session path, the selector
   and the planner following ideation's), `test_harness_hooks.py` (the
   hook denies the three tools with the reason); the retired
   `test_implementation_web.py`'s helpers in `tests/implementation_support.py`.
7. **The budget's end.** The two session classes and the obligations;
   `BudgetSnapshot.room` and the launch predicate at every site; the
   `unjudged` attempt; admission from the last round's duration with the
   insured and reserved cases; `round_seconds` on the checkpoint; the
   derived reserve and the structural bound; the two stop details and
   the prose; the trace's budget line. Tests: `test_budget_end.py`
   through the real loop with a stubbed clock and stubbed sessions: the
   finishing sessions get the reserve less the obligations after them, a
   session without room is not launched and the attempt says why, the
   evaluation run inside the reserve, admission refuses with the detail,
   the first round with no history, the insured floor, the reserved
   full-size attempt, a resume using restored history, a continuation,
   K>1 lanes, an unbudgeted campaign keeping its configured timeouts,
   the derived reserve from a harness's minutes and an observed judge,
   the bound on a short budget, the maintainer bridge's overrun kept.
8. **The judge.** The outcome inspected first; the retry resumed under a
   re-computed room with `retry_reason` recorded before the launch; the
   `unjudged` outcomes; the adapters' `resume(..., reason=)` and
   `start_run(..., reason=)`; the resumed session's cost delta; the cards
   parser; `SearchNode.commit` in the checkpoint and the trace; the trace
   schema 2 with the label grammar. Tests: `test_judge_retry.py` (tagless
   then tagged; tagless then timeout; a first-run timeout not retried; no
   handle raises; the two run entries; the cost delta 1.0 then 1.4),
   `test_feedback_generator.py` (the parser), `test_trace.py` (the commit,
   the retry reason, `unjudged`, the difficulties label on the goldens).
9. **The engine's own sessions.** The reconstruction staged, recorded and
   reading the branch; the inference sessions recorded under
   `engine/<role>`; the initialisation path and `with_default_config`
   deleted; `strict_mcp_config` on every Claude build session; the MCP
   config per session directory. Tests: `test_engine_sessions.py` (the
   reconstruction has a record and its prompt names the branch; a
   bootstrap session has a record under `engine/repo_memory`; two members
   write two config directories and one's cleanup leaves the other's; the
   workspace initialises with no agent).
10. **The harness directory protected.** The engine hook under
    `src/kapso/harness/engine_hooks/protect_harness/`, merged first by
    the staging on both hosts whenever a harness is staged, in the
    staged record; the setup guidance line; the refusal's message.
    Tests: `test_protect_harness.py` (the merged file's first entry with
    or without user hooks, the record, the script's decision on both
    hosts' event shapes, a shell write passing the hook and failing the
    hash check, the message).
11. **The benchmarks and the examples.** The four override files and the
    past-learning one, `benchmark:` for the runners' keys; the runners
    without `--mode`, their runtime config the merge, the IOAI preflight,
    the campaign driver; the e2e example's three files. Tests:
    `test_benchmark_runners.py`: each runner's solve path entered with the
    provider boundary stubbed (the real resolver, factory, staging,
    orchestrator and record), asserting the resolved roles, the inbox,
    the reserve and the session deadlines equal the mode's former values
    (a snapshot), and the runtime file resolving.
12. **The doctor and the pages.** The config line, `--show-config`, the
    JSON keys; `docs/reference/configuration.mdx` rewritten (the two
    layers, an override file, the schema walk, the hosts and roles, the
    budget block, `--show-config`); `cli.mdx` (the build's rows, the
    doctor's flag), `kapso-api.mdx` (the signature), `docs/build/
    resume-and-budgets.mdx` (the reserve, the obligations, the budget's
    end, `unjudged`), `docs/build/evaluation.mdx` and
    `docs/research/evaluation-governance.md` (the directory's rule),
    `docs/reference/harness.mdx` (the engine hook, the web recipe, the
    Codex trust flag), `docs/research/kapso-interfaces.md` (the two
    superseded sections), the `docs/evolve/*.mdx` snippets, the benchmark
    pages, the examples' READMEs, the skills' lines;
    `test_no_retired_names.py` extended with the names this package
    retires (live identifiers and configuration, not history or negative
    tests); the docs coverage check. Tests: `test_cli_doctor.py`.
13. **The proof run, S1's number, the findings, the master's row** (the
    row names the ownership transfers and the size).

## Tests

- Syntactic: the files named per change above. Goldens: the trace's
  fixtures regenerated for the record's new keys and fresh fixtures from
  the proof run for the facts old archives cannot carry (`commit`,
  `retry_reason`, `unjudged`); `kapso doctor --json` on the packaged
  config. Negative cases: an unknown key at depth, an unknown parameter,
  a role on a missing host, a model its host cannot serve, a plan without
  axes, a stale file with `modes`, a wrong policy enum.
- Proof run, on a fresh machine from the wheel: (a) the churn example,
  no harness, `--coding-agent codex` on the packaged config, forty-five
  minutes: the trace shows every session on Codex with the host's model
  and the engine's sessions recorded, and the minutes to the first
  candidate and to delivery are S1's numbers; (b) the trading example
  with `--harness` and an override file naming `host: codex` and `judge:
  {cli: claude_code}`, forty minutes: the last attempt's verification and
  judgment inside the reserve with their rooms in the record, the
  `deny-web` hook's denial on the implementation session (run once more
  with `host: claude_code` for the Claude host), the `protect-harness`
  denial from a scripted file-tool write and the hash check catching a
  shell write; (c) a short churn build (twelve minutes, two cheap
  iterations) to force the admission refusal and its detail; (d) a stale
  config with `modes:` refused at launch by name, `kapso doctor
  --show-config` and `--json` archived; (e) the four benchmark runners'
  smoke on the development box; (f) `kapso-mcp` on the development box
  with the hosted gate on Codex, the approval mode checked (WP2's open
  row). Archived under `scripts/redesign/runs/wp4/`, one file per run.
- Semantic hooks: S1's time-to-first-candidate and time-to-delivery on
  (a), recorded here; S4's reading of (b)'s trace by Codex and Claude Code
  on one question, why the campaign stopped and whether the last attempt
  was finished, graded against the record.

## Acceptance

- `src/kapso/config.yaml` has no `modes` or `default_mode`;
  `load_config()` with no path returns it, and with an override file
  returns the merge; no live identifier or configuration under `src`,
  `tests`, `benchmarks`, `examples`, `skills` or the published docs names
  `load_mode_config`, `modes`, `default_mode`, `design_axes`,
  `implementation_web`, `additional_context`, `idea_generation_model`,
  `implementation_cli`, `feedback_generator:` or `coding_agent:` as a
  block (`test_no_retired_names.py`).
- `kapso build --config x.yaml` where `x.yaml` names `modes:` or
  `budget.minute:` fails before any session with the message naming the
  key and the keys allowed.
- `kapso build --coding-agent codex` runs every role without a cli of its
  own on Codex with `hosts.codex.model`; the trace's sessions say so;
  `kapso doctor build` lists the sessions the packaged config runs and,
  with an override file naming a `claude-*` model on Codex, fails the pair
  by key.
- A direct `GenericSearch(...)` with a parameter the strategy does not
  read raises naming it; the strategy has no `self.params.get(key,
  literal)` left.
- The lens plan file carries `axes`; the judge's prompt renders them with
  a plan and omits the duty without one; no `design_axes` identifier.
- `build()` has no `context` or `additional_context`; the generic
  handler's context is the brief and the references; the implementation
  prompt with a provided suite says to run it.
- `test_budget_end.py` shows, through the real loop with a stubbed clock,
  each rule of the budget's end; the proof run (c) shows an admission
  refusal with its detail in the trace, and (b) shows the last attempt's
  finishing sessions launched with rooms above the floor.
- A judge whose first run had no tags shows two runs in one session, the
  second's entry `retry_reason: tags missing`; a judge cut by the deadline
  shows one run and the attempt `unjudged` with the deadline reason.
- Every evaluated attempt in the trace has a `commit`; the reconstruction
  and the bootstrap sessions have records; two ensemble members have two
  MCP config directories and one's cleanup leaves the other's.
- A file-tool write under the harness root from a session is denied with
  the reason on both hosts; a shell write is caught by the hash check at
  the next staging; the setup prompt carries the line.
- The four benchmark override files and the runners' runtime files
  resolve; the runners have no `--mode`; each runner's smoke asserts the
  resolved roles, inbox, reserve and deadlines.
- `kapso doctor` prints the config line; `--show-config` prints YAML;
  `--json` has `config` and `overrides`.
- The docs coverage check and `mint validate` pass; the gate is green at
  every commit.

## Risks

- The parameter rename touches many tests and the two benchmark configs
  that set most parameters: the table in the Interface is the migration
  map, and `test_no_retired_names.py` catches a leftover.
- Codex's hooks may not see its native web search: the engine's `web`
  switch is the boundary on Codex regardless; the page says what the hook
  covers on each host.
- Admission from the last round's duration can stop a campaign that
  would have fit a shorter attempt: the detail says why, the static floor
  still applies, the insured case keeps its own floor, and a person who
  wants the attempt sets a bigger budget.
- The derived reserve is a cold start on the first round (the judge at
  its floor): the first attempt may still run its judge short; the second
  round knows better. The proof run (c) measures it.
- Resuming the judge's session on Codex depends on `codex exec resume`,
  which the adapter already does for the inbox; a host that cannot resume
  fails loud rather than starting a fresh session.
- Refusing unknown keys refuses files written before this package:
  pre-release, no shim (Rule 7); the message lists the keys.
- The schema walk takes the packaged file as the truth: a key the engine
  reads but the packaged file omits would be refused in an override; the
  packaged file carries every default (change 3), and
  `test_config_resolution.py` checks the strategy's set against it.

## Review

The cross-model review of the first plan (`scripts/redesign/review.sh`,
Codex `gpt-6-astra` at xhigh and Claude Code `claude-opus-5`, read-only,
2026-10-26; the outputs under `scripts/redesign/runs/wp4-plan-review/`).
Neither would build the first plan as written; both named the same three
things: the budget's end had no real mechanism, the retirements reached
code the plan declared out of scope, and the resolver's deletion missed
callers. Every finding and what the plan now says:

### Codex

| # | Finding | Answer |
|---|---|---|
| 1 | P1: the resolver breaks the agents registry read through `load_config` | `read_yaml` for files that are not configs; `agent_manifest.py` owned |
| 2 | P1: the loaders' callers missed (cost estimator, deployment base, the experience and harness CLIs, learn, `core/__init__`, the tests) | the inventory is in Ownership; `deployment/base.py`'s one line owned; the direct tests migrated |
| 3 | P1: finishing sessions sharing the whole remainder starve the judge after verification and eat the fidelity slice | rewritten: a finishing session is clamped against the remainder less the obligations after it, each at its floor, the delivery's protected slice kept; the bridge's overrun kept |
| 4 | P1: admission discards the insured floor and leaves resume and continuation undefined | the three cases written (ordinary, insured, the reserved attempt); the round's duration on the checkpoint; a resume uses history; a continuation is not a round |
| 5 | P1: a ten-minute reserve refuses short builds; the floor is the wrong predicate | the reserve derived from the obligations when unset, an explicit one bounded by a quarter of the budget; `room` as the launch predicate, no clamp raised to the floor, unbudgeted timeouts kept |
| 6 | P1: the retry's outcome contract (a timeout on either invocation, the fabricated valid result) | the outcome inspected first; the four outcomes written; the fabricated result gone; `unjudged` |
| 7 | P2: the reason must be in the recorder before the launch; a resumed session double-counts cost | `start_run(..., reason=)`; the Claude adapter's delta, tested 1.0 then 1.4 |
| 8 | P1: retiring the web switches removes the benchmarks' binding restriction | the switches stay as `web` per role, the engine's boundary; the harness hook is the domain rule; the inventory of paths in change 6 |
| 9 | P1: `ProblemHandler(additional_context=)` breaks the five handlers | their constructors owned and edited; ALE's prose into its context; the brief and the harness pages are where the material goes |
| 10 | P2: the session inventory and the build-time inference sessions | the inventory in the Interface; single ideation through the ensemble path; the inference sessions recorded under `engine/<role>` |
| 11 | P2: the pairing rule must be the adapter's, not a prefix on the host binary; OSS members' endpoints | `serves` per adapter in `agents.yaml`; a member's endpoint keys move to the OSS host's entry |
| 12 | P2: typos inside blocks survive | the packaged file is the schema at every depth, open namespaces listed; the enums checked |
| 13 | P2: the task file alone is not the single problem statement; the provided-suite instructions contradict | the task statement stays a harness file; the contract rendered once in three forms, the provided case saying run |
| 14 | P2: the evaluation rule's scope | stated for the three provenances; the manifest's files protected, additions by suffix and bit |
| 15 | P2: the hook is not read-only; the hooks file removal; the script root | the promise narrowed to the file tools; the hash check for the rest; the file written whenever a harness is staged; the package path |
| 16 | P2: the benchmark ownership map and runnable smokes | `budget` and `inbox` stay engine settings; the five runner keys under `benchmark`; the IOAI preflight; smokes through the runner's path with a snapshot |
| 17 | P2: the fingerprint reads runner-owned keys | narrowed to the build's blocks; tested |
| 18 | P2: MCP isolation needs the adapters and has no Codex mechanism | the Claude adapter owned; Codex declined in writing (hooks need the user config) |
| 19 | P2: the `difficulties` label, `commit`'s meaning, the fixture generator | the grammar extended; `commit` null when never evaluated; the generator learns the keys, fresh fixtures for the new facts |
| 20 | P2: the axes on reload, keep and revise, and without a planner | validated on reload; every history record carries them; statused before revised; the duty omitted without a planner |
| 21 | P2: the presets file is a second defaults layer; `agents.yaml`'s operational defaults | `strategies.yaml` and the presets deleted; the precedence of a build session's settings written |
| 22 | P2: the interfaces document conflicts | superseded in writing, edited in change 12 |
| 23 | P3: acceptance lines and proofs that cannot establish their claims | rewritten: the budget's end through the real loop; the deny-web hook on each host; the retired-name check scoped |
| 24 | P3: `judge` versus the `feedback` module; `SessionSpec` versus `SessionRole`; the default-host wording | said: the judge is the feedback module; the spec is a requirement's input, the role a session's; "default host" |

### Claude Code

| # | Finding | Answer |
|---|---|---|
| 1 | P1: an unjudged attempt as `evaluation_valid: false` re-creates the loss | the `unjudged` state: the score kept, not a parent, never delivered |
| 2 | P1: the stop detail cannot be a sentence | two enum members; the prose in the note, the log and the trace |
| 3 | P1: a ten-minute reserve refuses `minutes ≤ 10` | derived by default; an explicit reserve bounded by a quarter of the budget |
| 4 | P1: `load_config`'s non-config callers; the renamed constant's importers | `read_yaml`; the importers in Ownership |
| 5 | P1: the five handlers | owned and edited |
| 6 | P1: the web knobs were the only binding denial; no boundary without a harness | the `web` switches stay as the boundary; the hook is the domain rule |
| 7 | P1: callers in files not owned | Ownership names every one |
| 8 | P2: no mechanism for "no session on the floor" | `BudgetSnapshot.room` and the launch predicate at every site |
| 9 | P2: the insured floor | the insured case keeps its own floor; `min_iteration_seconds_insured` named in the block |
| 10 | P2: K>1 and a resume | the round's duration defined, on the checkpoint, restored on resume; no free pass |
| 11 | P2: the fidelity escrow | the reserved attempt keeps its gate; the measurement slice is a protected obligation |
| 12 | P2: the candidate evaluation clamped as search | a finishing session, inside the reserve |
| 13 | P2: the retry's deadline is the first call's number | re-computed room; a retry cut at its deadline is `unjudged` |
| 14 | P2: the reason's route into the entry; the trace schema | `start_run(..., reason=)`; trace schema 2 |
| 15 | P2: `hosts` read as sessions by the walker | the build's specs come from the resolver alone; said |
| 16 | P2: the gate rows go quiet | `_gate_requirements` reads the roles' gates |
| 17 | P2: `resolve_role` in the wrong package | `kapso.core.roles` |
| 18 | P2: the structural defaults never reach a build session | the precedence written: `agents.yaml`, the host, the role, the staging |
| 19 | P2: the `agents.yaml` claim | the registry held `default_model` per entry before this branch deleted them; the decision entry corrected |
| 20 | P2: the pairing rule wrong for the Claude-family hosts | `serves` per adapter |
| 21 | P2: the runner must write the merge; the flat timeouts | the merge; `ideation.timeout` and `implementation.timeout` |
| 22 | P2: the five runner keys; the smoke's assertions | listed; the snapshot |
| 23 | P2: the fingerprint widens to the whole file | narrowed to the build's blocks |
| 24 | P2: the record's vocabulary; the fingerprinted keys; the fixtures | the handle's words in v2; `host`; the generator |
| 25 | P2: the task statement has no reader without a harness | dropped: a harness file; the brief is the problem text |
| 26 | P2: the prompts' problem block | the brief and the two reference lines; the contract once, in three forms |
| 27 | P2: the judge invents axes without a planner | the duty omitted without a plan |
| 28 | P2: `evaluation_maintainer: null` leaves seven literals | the block with its knobs and `enabled: false` |
| 29 | P3: acceptance lines not checkable | rewritten |
| 30 | P3: the forty-minute run cannot prove admission | the short churn run (c) |
| 31 | P3: a mock-only test | `test_session_construction.py` asserts the configs produced |
| 32 | P3: typo classes still silent | the schema walk; the enums; what is left, said |
| 33 | P3: unlisted deletions | `strategies.yaml` and the presets in the Scope |
| 34 | P3: delete the initialisation path | deleted, with `with_default_config` |
| 35 | P3: names | `retry_reason`; `override_paths`; the units said in the block |
| 36 | P3: the engine hook's root; the Codex trust flag | the package path; said |
| 37 | P3: supersede the interfaces document | done in writing and in change 12 |
| 38 | P3: what goes beyond the row; the two open asks | the row will name the transfers and the size; Q2.9 declined; the hosted approval checked in proof (f) |

Built on these answers; the owner checks the decisions.

### Pull-request review

Both reviewers read pull request #159's diff against `redesign`, the
sub-plan with its proof run, the decisions, the six pages and the proof
evidence under `scripts/redesign/runs/wp4/` (`scripts/redesign/review.sh`,
brief and outputs in `scripts/redesign/runs/wp4-pr-review/`). Codex would
have held the merge on four P1s; Claude Code would have fixed one. Every
finding, with what was done; "fixed" names the commit after the review.

**Codex (gpt-6-astra, xhigh), sixteen findings.**

| Finding | Answer |
|---|---|
| P1 an unbudgeted Codex build crashes after starting ideation (`None` added to a float, the child left running) | fixed (`642f2fd4`): no deadline runs the turn to its end; the member's and the selector's deadlines are their shares bounded by their own timeouts |
| P1 an implementation not launched reaches the branch lookup (`BadName`) | fixed (`642f2fd4`): the lane returns the attempt with the reason, no branch, no diff; `unjudged` says the implementation was not launched; the round skips it after the barrier |
| P1 the judge's missing-handle error is caught by the flow and the candidate stays deliverable | fixed (`642f2fd4`): the flow's catch marks the attempt unjudged with the error; a judge session that fails to start (a quota, a login) is unjudged with its error at the generator; the raise stays for a completed turn with no handle |
| P1 `web: false` leaves Codex's cached search on | fixed (`642f2fd4`): the adapter and the raw ideation pass `web_search="disabled"` with the web off (the key's values verified against the CLI); the `web` row says so |
| P2 ideation deadlines raised to 60-second floors; the selector's minimum on the stale clamp | fixed (`642f2fd4`): the floors are gone, a share is never raised; the selector's share is bounded by the room read when it launches; a member's retry only inside a window with time left |
| P2 member and selector timeouts accepted and ignored | fixed (`642f2fd4`): each bounds its session's deadline |
| P2 the judge retry's budget flag from the first invocation only; "no room for a retry" bypasses the cut | fixed (`642f2fd4`): both invocations' rooms are remembered and the cut attributed from the one that was cut; a retry refused for want of room is a finishing cut |
| P2 a verification cut attributed by a timeout comparison | fixed (`642f2fd4`): the invocation's own outcome (killed at its deadline without completing) attributes the cut |
| P2 RelBench's `--experience` path writes `bank_serving` into a file the resolver refuses | fixed (`bed4c2c0`): threaded as the engine's own override, as the facade threads it; tested with a fake serving |
| P2 value shapes: `enabled: {typo: false}` accepted, `cli: [codex]` a TypeError, `model: false` inherits; the roles' refusals lack the file | fixed (`bed4c2c0`): the walk refuses a mapping where a value stood; a spec's `cli`, `model` and `effort` must be non-empty strings when set. The file: a build has one override file, so the key locates the line; `ConfigError`'s docstring says what the message carries |
| P2 `learner.*.agent_specific` not open; `inference.default` has no `agent_specific` | fixed (`bed4c2c0`): both learner maps and `inference.default.agent_specific` (new, empty) are open namespaces |
| P2 `hosts.gemini` accepted, then refused by the staging | fixed (`bed4c2c0`, `179df4cf`): the hosts a build runs on are the adapters with a staging, declared in the registry (`host`); `check_hosts` refuses the others with the four; the staging reads the same key. The earlier decision (every adapter stages) is reversed in the decisions |
| P2 the preflight asks for the ideation role's host under an ensemble | fixed (`bed4c2c0`): the row is skipped when members replace it |
| P2 the engine's inference sessions on Claude inherit the person's MCP servers | fixed (`179df4cf`): `strict_mcp_config` on the engine's Claude sessions; asserted |
| P2 the raw Codex ideation drops the env rules; the run entry records no deadline | fixed (`642f2fd4`): the strip and the defaults reach the raw call (asserted on member and selector); the run entry carries `deadline_seconds`. The gates: a Codex member mounts none by design, the member-prompt test pins it |
| P3 the trace omits the stop's explanation | fixed (`f4fb9154`): the `stopped` row carries the sentence from the status file's note (`stop_note` in the data); the three fixtures show it |

**Claude Code (claude-opus-5), thirteen findings.**

| Finding | Answer |
|---|---|
| HIGH a judge session that fails to start ends the campaign with a traceback | fixed (`642f2fd4`): unjudged with the session's error; tested |
| MEDIUM two concurrent engine sessions share one record | fixed (`179df4cf`): the number and the record are taken under the staging lock; eight threads tested |
| MEDIUM-LOW the replanner staged for `claude_code` whatever the planner's host | fixed (`642f2fd4`): staged for the planner's own host |
| MEDIUM-LOW the admission sentence never reaches the trace | fixed (`f4fb9154`) |
| LOW-MEDIUM a `~` config path fails as a bug | fixed (`bed4c2c0`): expanded once by the resolver; tested |
| LOW the roles' refusals do not name the file; `validate_config` not run for a runner's orchestrator | answered and fixed (`bed4c2c0`): the key locates the line in the one override file, the docstring says so; the orchestrator validates at construction, tested with a runner's file |
| LOW `-a claude_code` still demands a Codex login | said on the `-a` row (`bed4c2c0`): the engine's own sessions follow `inference.default`; an all-Claude run sets `inference.default.cli` |
| LOW `design_axes` missing from the guard | fixed (`6ee33d80`); the RelBench test spelling it renamed (the handler's own axes are its vocabulary) |
| LOW contracts no test pins | the round's value round-trips through the checkpoint (`6ee33d80`); K>1 lanes, a continuation and the maintainer's overrun stay in the findings |
| LOW leftovers: comments, pointers to a module that does not exist, the test shim, the function-local import | fixed (`642f2fd4`, `179df4cf`, `6ee33d80`) |
| LOW the budget's floors as literals | fixed (`50b2b9b9`): sourced from the packaged config |
| LOW the admission counts the finishing span twice | said on the page (`50b2b9b9`): the admission errs early by about one finishing span, never late; kept |
| LOW the reconstruction inherits the implementation's Stop hooks | left for the owner, in the findings |

**What the review did not change.** An unjudged attempt is never
delivered, the verifier keeps working after its verdict, the
reconstruction keeps its module's hooks: the owner's calls, in the
findings below.

## Proof run

**The fresh machine, `kapso-fresh-wp4`** (`e2-standard-4`, Ubuntu 24.04,
created 2026-10-26 13:52 UTC, deleted after 1.50 h, about $0.20;
`scripts/redesign/runs/wp4/`, one `run-N.log` per command, the campaigns
archived as `campaign-*.tgz`). The wheel built from the branch at
`7726831c`, reinstalled from `83f7398f` and `8dc91cde` as the findings
below were fixed (`wheel.sha256` lists the three); the two CLIs; the
campaign token from the secret store; Codex logged in with the API key
(`install.log`). The fixture: the trading and churn examples, the trading
harness and a copy of it for the shell-write check, three override files
(`trading-codex.yaml`: `host: codex`, `judge: {cli: claude_code}`;
`trading-claude.yaml`: `host: claude_code`; `stale-modes.yaml`: a
`default_mode` and a `modes` block), run-1 to run-3.

**What the machine could not run.** The API key behind the machine's
Codex login is over its quota (`Quota exceeded. Check your plan and
billing details`, every Codex session; run-5 to run-7): the first
launches of (a) and (b) died in their first session, and every later
build on the machine has its engine session on Codex (`inference.default`,
the repo memory) recorded failed under `OTHER SESSIONS` and `SESSIONS
FAILED`. The Codex-host builds ran on the development box instead, from
the branch's source, with the Claude judge on the same campaign token
(`scratchpad: devbox_wp4.sh`, the archives `campaign-devbox-{a,b}.tgz`);
the box's ChatGPT login answered a 429 at 14:00 and cleared by 14:12.

**(d) The doctor, the config line, the stale file** (run-3, run-4,
run-35). `kapso doctor build` on the packaged defaults prints `config:
packaged defaults`, the pairing rows (`claude_code is asked for
claude-opus-5`, `codex is asked for gpt-5.6-sol`), eight checks passed;
`--json` carries `overrides: []` and the effective config (`host:
claude_code`). With the override file: `config: packaged defaults +
/home/ubuntu/fixture/configs/trading-codex.yaml (overrides:
search_strategy.params.host, search_strategy.params.judge.cli)`;
`--show-config` prints the 296-line effective config, `host: codex` under
`params`. The stale file is refused by name at the doctor and at the
launch, before any session and with no campaign directory made:
`stale-modes.yaml: the top level: unknown keys default_mode, modes; the
keys are budget, deployment, evaluation_maintainer, experience, gates,
harness, hosts, inbox, inference, knowledge_search, learner, learning,
models, preflight, retry, search_strategy (and `benchmark`, a benchmark
runner's own)`. The first wheel printed it as a traceback, the resolver
raising a plain `ValueError` the CLI's error hook treats as a bug; fixed
on the branch (`15d0f07a`), and run-35 shows the one-line form.

**The hooks, scripted** (run-10): the engine's `protect-harness` script,
run as the hosts run it, denies a Claude Code `Write` under the harness
directory and a Codex `apply_patch` whose header names a harness file by
a relative path, each with the reason (`… is under the harness directory
(/home/ubuntu/fixture/examples/harnesses/trading), which is read-only in
every session: fix the environment or your own files, never the harness.
A harness that needs a change is reported in your final response, for its
author`), and passes a write elsewhere; the trading harness's `deny-web`
denies `WebSearch` with its reason. In the builds the implementation
sessions never tried the web, so the live hooks fired on `SessionStart`
only; the setup session's `protect-prepared` denied one write under
`prepared/` (`campaign-b.tgz`).

**(f) The hosted gate on Codex** (WP2's open row; on the development
box, `scratchpad: hosted_gate_check.sh`): a Codex session under
`--sandbox read-only` with Leeroopedia's server mounted as the adapter
mounts it. With `default_tools_approval_mode="auto"` the session listed
the eight tools and its `search_knowledge` call failed: `MCP tool call
requires approval, but approval policy is never`. With `"approve"` the
same call completed with the knowledge base's answer. The adapter now
writes `approve` for a hosted gate (`aace2f11`).

**(c) The churn example on the packaged host, twelve minutes, three
experiments** (run-9, run-14, run-15; `campaign-c12.tgz`; the fixture
`churn-unjudged`). One round: ideation 6.2 min, implementation 3.5 min,
the evaluation at 9.7 min (0.8454 on the provided evaluator), then the
judge launched with the 106 s the budget left (above the 60 s floor) and
cut at its deadline: the attempt `unjudged: the judge's session ended at
the budget's deadline`, the stop `budget_exhausted (finishing_cut)`,
nothing delivered. The trace's header: `budget 11.5 of 12.0 min, 1.5 min
reserved for finishing (the launch's over the brief's 45.0 min)`; the
attempt's line carries its commit (`generic_exp_0 @ 60cb08e3876d`). The
same build at eighteen minutes (run-17, run-22 to run-24;
`campaign-c.tgz`): the round took 16.8 min, the next was refused,
`budget_exhausted (attempt_would_not_fit)` with the note `the remaining
… would not cover an attempt (the last took 16.8 min)` in the status
file and the log, the attempt delivered at 0.8447 (`generic_exp_0 @
0c06e7466509`; first candidate 14.1 min, delivery 16.9 min).

**(b) The trading example with the harness on the Claude host, forty
minutes, two experiments** (run-8, run-25 to run-27; `campaign-b.tgz`).
One attempt reached the goal: Sharpe 2.2382 (baseline 0.14, target 1.0)
at minute 14.9, verified `valid` with no findings, judged `stop` at
minute 30.3; `goal_achieved`, `generic_exp_0 @ 1a102cc2c8dc` delivered.
The budget line: `30.3 of 40.0 min, 11.5 min reserved for finishing`, the
reserve derived from the harness's ten verification minutes, the judge's
floor and the delivery, unbounded as the plan had it; the verification
session wrote its verdict and kept working until its ten-minute cap
(`exit: timeout`, the verdict taken). The run entries carried no
deadline (a finding, fixed). The same build with the harness copy and a
shell write that never fired (run-28, run-31 to run-33;
`campaign-b2.tgz`, twenty minutes): one attempt scored 2.1312, verified
`valid`, the judge cut at the budget's deadline, `finishing_cut`, nothing
delivered: a second record of the unjudged attempt, with a harness.

**The hash check, live** (run-36, run-37, run-42, run-46 to run-48;
`campaign-b4.tgz`). A ten-minute build on the harness copy (run-36)
launched its setup session with a negative deadline (`exceeded its
-90.04s deadline`): the unbounded derived reserve (11.5 min) exceeded the
budget. Fixed on the branch (`8dc91cde`: the reserve bounded, the setup
session refused by the launch predicate with the reason) and the wheel
reinstalled. The build again at twenty minutes with a shell write to
`instructions/guardrails.md` of the harness copy during ideation
(`inject-harness.log`: `15:14:47 appended a line …`): the
implementation's staging refused it and the build failed with the
message, in the status file and the log: `the harness changed since
launch: trading 0.1.0 (cedac9605e0f) recorded, now db9ee558a39b (changed
instructions/guardrails.md); restore the recorded content (for instance
`git checkout` in /home/ubuntu/fixture/examples/harnesses/trading-b2) or
start a new campaign with a new --output`.

**(a) The churn example with `--coding-agent codex` on the packaged
config, forty-five minutes, three experiments**, on the development box
(`campaign-devbox-a.tgz`; the fixture `churn-codex`). Every session on
Codex with the host's model: `ideation/iter1/codex_gpt-5.6-sol`,
`generic_exp_0`, `feedback/generic_exp_0`, and the engine's own
`engine/repo_memory/1` (success, 1.8 min) under `OTHER SESSIONS`. One
round of 25.8 min, the ideation session alone 17.2 min (3.2M input
tokens), the candidate scored 0.849 against the 0.85 target, the next
round refused (`attempt_would_not_fit`), the attempt delivered
(`generic_exp_0 @ 9ee5956a1bf9`). S1's numbers on this run: first
candidate 22.2 min, delivery 26.9 min.

**(b) again with `host: codex` and the judge on Claude**, on the
development box (`campaign-devbox-b.tgz`; the fixture `trading-void`).
The setup, ideation, implementation and verification sessions on Codex,
the judge on Claude Code (`feedback/generic_exp_0 claude_code`): the
role-level `cli`. The attempt measured 2.4002 and was voided by the
verifier for a file added under `kapso_evaluation/`; the judge ran to
the end (`not valid, continue`), the next round was refused, nothing
delivered. The reserve: 17.2 min of 40, derived and unbounded, the
second instance of the finding above.

**S4's readings.** Two campaigns' records, read by Codex (gpt-6-astra,
xhigh) and Claude Code (opus-5) with the trace and the record alone, on
one question, why the campaign stopped and whether the last attempt was
finished (`scratchpad: s4_brief_wp4.md`); graded against the record in
`scripts/redesign/runs/wp4/s4/{b,devbox-b}/grading.md`. No claim either
reader made was wrong on either campaign. What they opened files for
became findings: the trace prints a null `stop_detail` as nothing (so a
reader cannot tell elided from null), gives durations and no wall clock,
does not reconcile a verification `timeout` with its `valid` verdict,
does not say where a derived reserve came from, hides the measured
figure behind `no score` on a voided attempt, prints `delegates
risk-reviewer stopped` without the reason, and keeps the admission
sentence in the status file and the log; and the record was missing the
campaign's first engine session (the repo-memory bootstrap) and the
deadline each run was launched with, both fixed on the branch.

**(e)** The four benchmark runners' smoke is `tests/test_benchmark_runners.py`,
on the development box under the gate.

**Semantic hooks.** S1 on (a): first candidate 22.2 min, delivery 26.9
min, on Codex; on the Claude host the eighteen-minute churn build gave
14.1 and 16.9. S4: the two readings above.

## Findings for later packages

Fixed on this branch during the proof run:

- **A config refusal printed as a traceback.** The resolver raised a plain
  `ValueError`, which the CLI's error hook treats as a bug; the refusal
  was right and unreadable. `ConfigError`, one line (`15d0f07a`).
- **WP2's open row: `auto` does not pre-approve a hosted gate on Codex.**
  The adapter writes `approve` for a hosted gate (`aace2f11`).
- **The record did not carry the deadline a run was launched with.** One
  key on the run entry, `deadline_seconds` (`83f7398f`).
- **The derived reserve had no bound and the setup session no launch
  predicate.** A ten-minute budget with a verifying harness derived 11.5
  minutes and launched the setup session with a negative deadline; the
  forty-minute builds kept 11.5 and 17.2 minutes out of the search. Both
  reserves take the quarter bound; the setup session is refused with the
  reason when its room is under the floor (`8dc91cde`).
- **The campaign's first engine session was unrecorded.** The repo-memory
  bootstrap runs in the strategy's constructor, before the orchestrator
  wired the recorder; the strategy wires it at the workspace's birth
  (`44e7fa6b`).
- **The judge's phase stayed `verification`** in the status file when a
  verification ran before it (`44e7fa6b`).

For the user's decision, or a later package:

- **An unjudged attempt with a score is not delivered.** Build (c) at
  twelve minutes: a candidate scored 0.8454 at minute 9.7, the judge cut
  at its deadline, `delivered: none succeeded`; build (b2): 2.1312,
  verified valid, the same end. By this package's rule (`unjudged` is
  never delivered, as `unverified` is not) a short budget that produced a
  scored candidate hands over nothing. A design question for the user:
  deliver the scored attempt with its `unjudged` flag, or keep the rule
  and have the summary say a scored candidate exists on its branch.
- **The verifier keeps working after its verdict.** Twice the verification
  session wrote `verdict.json` and ran on until its ten-minute cap
  (`exit: timeout`, 25–29 turns, $2.5). A session whose output file exists
  could be ended, or its page could say to stop (WP2's page, or the
  adapter).
- **What the trace should carry, from S4** (WP6's renderer): a voided
  attempt's measured figure beside the void (`no score` hides 2.4002); a
  word for a null `stop_detail` (the admission sentence and the finishing
  cut are on the `stopped` line since the pull-request review); the
  reserve's provenance (`derived` or `set`) on the
  budget line; a delegate's stop reason; wall-clock times, or the sessions'
  order; `cost $0.000 (Claude Code sessions only …)` on a campaign with no
  Claude session; `lens_planning` in the status file's phase list without
  a session.
- **Single-member Codex ideation is slow.** The churn build's ideation
  session on Codex took 17.2 min and 3.2M input tokens for one candidate,
  against 6–9 min on Claude; S1's numbers on Codex carry it. WP8's
  benchmark reproduction, or the ideation prompt for a single member.
- **The machine's Codex key is over its quota.** Every Codex session on the
  fresh machine failed; the Codex-host builds ran on the development box.
  The environment's, not the engine's; the record showed it by design.
- **The reconstruction inherits the implementation module's Stop hooks**
  (the pull-request review). Staged as the implementation module, it gets
  `require-results` on the trading harness, which blocks the read-only
  reconstruction once and tells it to run the backtest, on the attempt
  that produced no results; `stop_hook_active` keeps it to one turn. The
  way out is a staging without the module's hooks for the finishing
  sessions that write nothing; a design call for the owner.
- **Contracts no test pins** (the pull-request review): K>1 lanes at the
  budget's end, a continuation that is not a new round, the maintainer
  bridge's kept overrun. A resume from a restored `round_seconds` is
  pinned now; the rest for WP8's reproduction or a later package.

## Built

Branch `wp4-config` off `redesign` at `55a92430`, the commits below, each
with its tests and the gate green at every one (the last gate: 1,713
passed, 27 skipped, 2 deselected; the docs coverage check 43 commands and
methods, the snippet check 6 quoted files, `mint validate` passing). The
branch: 282 files, +9,991 −5,104.

| Commit | What landed |
|---|---|
| `b2939bec`, `f1513509`, `3ccd51d8` | the sub-plan, its planned decisions, its revision after the cross-model review |
| `1d630a17` | the config as two layers: the resolver with the packaged file as the schema, the hosts table and the three roles, `--coding-agent` as the host, the preflight's pairing, the strategy's known parameters, the benchmark override files, the fixtures regenerated (change 1) |
| `d0708cb1`, `41741786` | the design axes are the lens planner's (change 2) |
| `f0572115` | every build session's config through one precedence; `agents.yaml` without model defaults (change 3) |
| `59201c44` | the brief is the problem text; the launch record in the handle's words; the evaluation contract in three forms (change 4) |
| `748ac313`, `f6127849` | the web as the engine's boundary per role, and the trading harness's `deny-web` hook (change 6) |
| `e7c646d6`, `2ad2867e` | the budget's end: search and finishing rooms, the obligations, the derived reserve, admission from the last round, the two stop details, the unjudged attempt, the attempt's commit (change 7) |
| `cf6d9530`, `37a40138` | the judge's retry resumes its session by reason; the resumed session's cost; the cards parser (change 8) |
| `da8f75a2`, `a738820c` | the engine's own sessions in the record; the reconstruction staged and reading the branch; the initialisation session deleted (change 9) |
| `0a253651` | the harness directory protected: the engine's `protect-harness` hook first in every staged session; the changed harness refused by file name (change 10) |
| `a003953b` | the benchmark runners' paths, pinned to the former modes (change 11) |
| `7726831c` | the pages, the READMEs and the skills; the retired-name check extended; the doctor's config line and `--show-config` tested (change 12) |
| `15d0f07a` | the proof run's first finding: a config refusal is the engine's own error |
| `aace2f11` | WP2's open row closed: a hosted gate's tools pre-approved on Codex; the fixture generator keeps written runs |
| `83f7398f` | a run entry carries the deadline it was launched with |
| `8dc91cde` | the derived reserve bounded; the setup session follows the launch predicate |
| `44e7fa6b` | the engine recorder wired at the workspace's birth; the judge's phase after a verification |
| `a7a96478` | three trace fixtures from the proof run, with their tests |
| `807527b9`, `71975eea`, `36781f1c`, `512b3dd7` | the proof run's record (the section, the findings, this table, the master's row); the facade tests without the machine's preflight |
| `642f2fd4` | the pull-request review: the ideation rooms as shares bounded by their own timeouts; the judge's failures and an implementation not launched as unjudged attempts; the cuts attributed from the invocation that was cut; Codex's search disabled by config; the replanner on its own host |
| `bed4c2c0` | the review: the config's shapes (`~`, a mapping where a value stood, the adapters' own maps, a spec's strings); the hosts a build runs on declared in the registry; the orchestrator's own validation; the preflight under an ensemble; the RelBench serving as the engine's override; the `-a` row |
| `179df4cf` | the review: the engine's sessions take distinct records and mount only their own servers; the staging reads the hosts from the registry; the inference test's shim gone |
| `f4fb9154` | the review: the trace's `stopped` row carries the sentence the campaign stopped on |
| `50b2b9b9` | the review: the budget's floors from the packaged config; the admission's finishing span said |
| `6ee33d80` | the review: the retired-name guard knows `design_axes`; the checkpoint's round round-trips |
| the last commit | the review's answers (this section), the findings, the decisions |
