# Decisions taken during the implementation, for the owner to check

Started 2026-10-24. The owner asked for the implementation to run
autonomously and for any architecture or design decision that was not
discussed to be written here so it can be checked later. Newest first.
Each entry: what was decided, why, what the alternative was, and where it
shows.

## 2026-10-26, WP4 (taken while building)

**The judge says "its deadline"; the strategy says whose.** The
generator does not know whether the deadline that cut the judge was the
budget's room or the role's own timeout, so its reason reads `the
judge's session ended at its deadline`; the strategy, which computed
the deadline, rewrites it to `the budget's deadline` and reports the
finishing cut only when the budget set it. Why: a judge cut by its own
configured timeout with an hour of budget left is not a budget's end,
and stopping the campaign on it would be wrong. The plan's wording is
kept for the case it described. Shows in `feedback_generator.py`,
`strategy.py`.

**No verdict is a field of the result, not an exception.**
`FeedbackResult.unjudged` carries the reason (no tags after a retry,
the deadline, no room for a retry); the flow sets `SearchNode.unjudged`
from it and skips the verdict. The one exception kept is the missing
session handle, a wiring bug. Alternative rejected: raising for every
unjudged outcome, which would turn a budget's end into a failed
campaign.

**The launch predicate guards the lane's sessions; ideation's inner
sessions take the room they have.** The implementation, the evaluation
run, the verification, the judge and the reconstruction each check
their room against the floor before launching and record why when
refused. The ensemble members, the selector and the lens planner start
inside an admitted round (admission already covered the floor and the
last round), so they are clamped to their room without a launch check:
a selector that finds less than the floor runs with what remains and is
cut at it, recorded as timed out, rather than skipped with a second
mechanism inside the ideation module. Why: one predicate at the five
sites where a skip has a record to land in; the ideation sub-sessions'
case is an edge of an edge (a round admitted with barely the floor).
Shows in `strategy.py` (`_room`, `_clamped_timeout`,
`_finishing_deadline`), `budget.py`.

**The obligations are counted at the floor, not at their configured
timeouts.** A finishing session's room is the remainder less one floor
per session still to run (the evaluation run in cost mode, the
verification when the harness verifies, the judge) plus the delivery's
slice. Why: the plan says each is "protected at its floor"; counting
configured timeouts (ten minutes of verification, say) would hand the
end of a campaign to the reserve and starve the attempt in flight. The
derived reserve is the other side: there the verification's configured
minutes and the judge's observed duration count in full, so the
searchable window is cut for the real finishing cost while a session
already running is only asked to leave its successors their floors.

**The round's duration lives in the strategy's state.** `round_seconds`
is a key of `strategy_state` (written by `dump_state`, read strictly by
`load_state`), not a field of the checkpoint dataclass: the strategy
measures and consumes it, and the checkpoint carries the state whole.
The schema stays 6.

**The escrowed attempt's end is `attempt_would_not_fit`.** After the
fidelity policy's reserved full-size run, the campaign stops with the
admission detail (no further attempt fits) rather than a third detail:
the closed set has two new members, as planned.

**The delivery's slice without a fidelity measurement is thirty
seconds.** The final checkout and the records; a structural constant
(`DELIVERY_SECONDS`), not a knob, like the quarter bound on a set
reserve (`RESERVE_FRACTION_BOUND`).

**`deny-web` is the implementation module's; `deny-web-fetch` stays
everywhere.** The trading example already denied the shell's fetchers
(`curl`, `wget`, `aria2c`) on every module; the plan's `deny-web` is a
second hook, on the native web tools (`WebSearch|WebFetch`), listed on
implementation alone: ideation's web research is the example's intent
(the engine's `ideation.web` default), the implementation's web is the
leak the protocol forbids. Why two hooks: two rules, two reasons, each
placed where it applies by the manifest. Alternative rejected: folding
both into one hook on every module, which would take the web from
ideation. Codex's native web search is not a tool call its hooks see;
the engine's switch is the boundary there, and the page says so.

**The axes live in one tag, status included.** The planner's first plan
names the axes in an `<axes>` block (a list numbered from 1); a revision
restates every one in the same block as `N. <axis> — <status>`, and the
record keeps those lines as the axes, so the judge and the next
replanner read the latest status beside each axis; a keep puts its
statuses in its paragraph and carries the axes along. Why: one grammar
to parse and one field in the record, and the status is what the judge's
frontier report builds on. Alternatives rejected: a separate
`<axis_status>` tag and an `axis_statuses` field (two things to keep in
step, no reader that wanted them apart); statuses required on a keep
(a terse keep would be discarded for a formality). Shows in
`lens_planning.py`, the two planner prompts, `axis_frontier.md`.

**Single-session ideation keeps the ensemble's candidate hygiene.** The
plain path is the ensemble machinery with one member, so a candidate
under the degenerate floor (eighty characters, or forty of content) is
dropped and the fallback solution is implemented, where the old Claude-
only path took any output as the plan. Why: one machinery, one rule; a
plan that short is a skeleton on any host, and the fallback keeps the
round alive. Shows in `ideation.py`; the direct-construction tests give
their fake agents plan-sized outputs.

**A host the table does not name is a config error, named by where the
host is set.** `search_strategy.params.host (what --coding-agent sets):
gemini is not in hosts (the hosts are claude_code, codex); add
hosts.gemini: {model: …} to the config to use it`, a `ValueError` from
the resolver before the preflight, like every other config refusal; a
role's own `cli` is named as that role's key. The harness staging's
"no staging" refusal is unreachable through the facade now: the hosts
table is checked against the adapter registry, and every registered
adapter stages. Alternative rejected: a preflight row (the preflight
checks the machine against the config; a config that names nothing the
engine knows is not a machine fact).

**An open namespace exists in the schema, empty.** `knowledge_search.
params: {}` is in the packaged file: the walk allows any key under an
open namespace, but the namespace's own key must be one the packaged
mapping names, so an override could not set it until the packaged file
carried it. The readers take `["params"]`, not `.get`. The rule holds
for every open namespace: `hosts`, `inference.roles`, `gates`,
`session_env_defaults` all exist in the packaged file.

**A mapping in the packaged file is a mapping in an override.** The walk
refuses a scalar where the packaged value is a mapping (`inference:
nonsense` → `must be a mapping, got str`) instead of letting the merge
replace the block and the reader die later. Shows in `config.py`.

**The launch record's `config_path` is `None` for the packaged
defaults, however they were named.** `is_packaged()` (the resolver's
own test, exported) decides it at record and resume time, so a resume
from another install — a different site-packages path for the same
packaged file — compares equal, as the old `_launch_config_path` made
it. Shows in `kapso.py`.

**The trace fixture generator writes the launch record at the current
schema.** The archives predate the record without `mode`; the generator
reconstructs the record (schema 2, no `mode`) as it already
reconstructs the checkpoint's and the solution record's schemas, and the
three fixtures were regenerated from their archives (the golden texts
unchanged). The handle's words (`experiments`, `minutes`, `usd`,
`reserve_minutes`, `host`) come with change 5.

## 2026-10-26, WP4 (planned; taken while writing the sub-plan)

**The build's sessions are roles over a hosts table.** The config gains
`hosts.<cli>: {model, …}` and `search_strategy.params.host`; ideation,
implementation and the judge are role blocks (`cli`, `model`, `effort`,
`timeout`) that default to the host and its model; `--coding-agent` sets
the host for the campaign. Why: the flag reached a field no session read
(WP2's and WP6's proof runs ran every session on Claude Code under
`--coding-agent codex`), a model the CLI could not serve was found at the
first session, and three blocks (`coding_agent`, `feedback_generator`,
the flat `*_model` parameters) named hosts and models with no rule
between them. Alternatives rejected: routing the flag to
`implementation_cli` alone (ideation and the judge stay elsewhere and the
model mismatch remains); deleting the flag (the plugin's build on the
host it runs in wants one word). The judge is a role under the strategy's
parameters, not a top-level block: it is the strategy's session, named
beside the sessions it judges. Shows in `config.yaml`,
`search_strategies/generic/roles.py`, the preflight.

**Unknown top-level keys are refused; `benchmark:` is reserved.** An
override file may name only the packaged file's top-level keys; the
runners' own settings live under `benchmark`, which the engine never
reads. Why: a mode leftover or a typo did nothing silently (the "a config
copy's `defaults:` is ignored" trap WP3 met), and the runners' keys
(`run_defaults`, `final_eval`, their own `preflight`) collide with the
engine's at the top level. Alternative rejected: a full nested schema;
the open mappings (env names, inference roles, hosts) would need a schema
language, while the blocks with validators (`budget`,
`evaluation_maintainer`, the ensemble members, the lens planner, and now
the strategy's parameters) keep refusing their unknown keys.

**`MINIMAL` is not shipped.** A config that turns things off is an
override file a person writes; the configuration page shows one.
Alternative rejected: a shipped `minimal.yaml`, a second shape to keep in
step with the first.

**The web stays a switch per role, the engine's boundary; a harness that
forbids the web lists a hook, the domain rule.** `ideation.web` and
`implementation.web` replace `web_search` and `implementation_web` with
one name and one meaning on both hosts: off, the two native tools leave
Claude Code's allow-list and go on `--disallowedTools`, and Codex is not
given `--search`; the selector and the lens planner follow ideation's.
The master's row said `implementation_web` becomes a hook; the review
showed the knob is the only binding denial Codex has (a hook may not see
its native search) and the only one a config without a harness has at
all, so the switch is kept as the engine's permission boundary and the
hook is the per-module domain rule a harness adds. The first draft
deleted both knobs; revised after the review.

**The axes are the planner's output.** The lens planner names the design
axes it derives from the goal and the ideation page in an `<axes>` tag;
the plan file carries them; the replanner statuses them; the judge's
prompt renders the plan's axes, or asks the judge to name the ones it
sees. Why: the harness design's section 9 recommends it, and the five ML
axes in `lens_planning.py` were domain prose in engine code. Alternative
rejected: an axes list in the harness's ideation page that the engine
parses, an engine-facing field in a page.

**The problem text is the brief; the evaluation contract is rendered once,
in the implementation prompt.** The generic handler renders the brief and
the two reference lines (where the evaluation and the data live) and
nothing else; the implementation prompt carries the contract in three
forms (a provided suite: run it, never edit it; a registered one: the
maintainer's; none: build your own). The first draft wrote the task
statement for every build; the review showed that without a harness
nothing mounts or names the file, so it stays a harness build's file.
Alternative rejected: keeping the handler's prose, two renderings of the
same facts that drifted (the handler said `result.json` may be created,
the prompt said where to write it, and the provided case got the
build-your-own text).

**The budget's end: finishing obligations protected, a launch predicate,
admission from the last round, the reserve derived.** A finishing session
(the candidate's evaluation run, verification, the judge, the
reconstruction) is clamped against the whole remainder less the
obligations after it, each at its floor, the delivery's protected slice
kept; a session is launched only when its room is at least the floor,
and a deadline is never raised to the floor; a judge or verification the
budget cuts leaves the attempt `unjudged` or `unverified` with the
reason, its score kept, never delivered; an ordinary round is admitted
when the searchable remainder covers the larger of the static floor and
the last completed round's duration (the insured campaign keeps its own
floor, the fidelity policy's reserved attempt its own gate); the reserve
is derived from the obligations when `budget.reserve_minutes` is unset
(the harness's verification minutes, the judge's observed duration, the
delivery's slice) and bounded by a quarter of the budget when set. Why:
every campaign of WP2's, WP3's and WP6's proof runs that reached its
budget ended on a verification cut at its clamped deadline and a judge on
the sixty-second floor, rejecting a scored attempt. The first draft gave
finishing sessions the whole remainder, floored the clamp and shipped a
ten-minute reserve; the review showed the judge starving after
verification, a reserve refusing short builds, the insured floor lost
and the fidelity slice unprotected. Alternatives rejected: raising
`min_iteration_seconds` (one number for every task), per-phase fractions
(the IOAI runner's recorded lesson: a phase sub-budget starved ideation),
marking a cut attempt invalid (the loss WP6 found, by another route).

**The judge's retry resumes its session, records its reason, and does not
follow a deadline.** Why: both S4 readers of WP6's proof run had to dig
the retry's reason out of the log, and a fresh session answered with none
of the context. A deadline-killed judge is the budget's end, not a
missing tag.

**`result.json` stays in the protected directory; code added there is
the tamper.** Moving the contract's output would break every evaluator
written so far; the integrity verifier already rejects added source and
executables, and what was missing was the rule stated in the pages.

**The maintainer is off by default, its knobs in the config.** It runs
its own calibration and registration sessions per build, and most builds
bring an evaluator or a harness verification; the packaged block carries
`enabled: false` and every knob the orchestrator held as a literal
(Rule 1; the first draft shipped `null` and left seven literals in code),
so a person turns it on with one key and sees what they are tuning.

**No lighter ideation for small briefs here.** An effort change is a
quality change nobody has measured; S1's time-to-first-candidate is
recorded on this package's proof run first, and the budget's end makes a
short campaign stop honestly rather than deliver a half-built attempt.

**The budget block speaks the handle's words.** `budget.minutes`,
`experiments`, `usd`, `reserve_minutes` replace `time_budget_minutes`,
`cost_budget_usd` and `finalization_reserve_minutes`, and the facade's
`DEFAULT_MAX_ITERATIONS` becomes `budget.experiments` (WP1 asked for the
literal to move with the block). One word per dimension across the brief,
the flags, the API and the config.

**`agents.yaml` loses its model defaults and gains `serves` and
`settings`; `build_config` requires a model.** The `default_model` lines
(`claude-opus-4-5` for Claude Code) duplicated the config's model and had
gone stale (Rule 1); the hosts table is the one home. `serves` names the
model family an adapter can be asked for (`claude`, `openai`, `any`), so
the preflight's pairing row is the adapter's fact and the OSS and Vertex
adapters, which run Claude Code with other models, are not refused;
`settings` names the keys a host entry may set for that adapter, so a
misspelled adapter setting is refused rather than ignored.

**The engine's `protect-harness` hook rides every staged session.** The
harness directory is the author's: WP3's proof lost a setup session's
minutes and dollars to a patched harness, and the identity check that
refused the campaign was right while the rule before it was missing.
Alternative rejected: staging the servers from a copy, whose `cwd` and
`${PLUGIN_ROOT}` paths would diverge from the author's tree while the
hash still moved.

**The empty-workspace initialisation session is deleted.** A model call
to write an empty `main()`, unreachable from the facade, which always
names a workspace; the workspace writes the file.

**`--config` stays explicit.** Nothing is read from the working directory
unnamed: the brief is named with `--brief`, and a stray
`kapso-config.yaml` applied silently is the class of surprise the
resolver exists to remove. The build's banner and the doctor's first line
name the layers.

**The strategy's parameters are a known set, every default in the
packaged file.** The gate-list literals WP3 flagged and every other
`params.get(key, literal)` move into `config.yaml`; the strategy reads
without defaults; a misspelled parameter is refused by name.

## 2026-10-25, WP6 (taken while building)

**A run's files are the host's account; the delivered files are the
diff's.** Both adapters took `files_changed` from a git status of the
session directory, which listed the engine's own `.kapso/` directories
for a judge session and nothing for a Codex implementation that had
committed its work (the proof run's Codex-hosted build delivered a
candidate whose trace said `files changed: none recorded`). The run
entry now carries what the host itself reported writing: the edit
tools' inputs on Claude Code, the `file_change` items on Codex,
relative to the session directory. A file written through a shell
command is not in that account, so the trace's delivered candidate
names the files its branch's diff touches (the checkpoint node's
`code_diff`), the ground truth of what the branch changed. Two facts,
two sources, neither a fallback for the other. Alternative rejected:
keeping the git status and filtering the engine's paths, which still
misses a committed change and still depends on when the status was
taken. Shows in `kapso.execution.coding_agents.transcripts` (`files`),
`session_record.record_run` and `kapso.execution.trace._delivered`.

**A launch is registered before its checks, and a receipt keeps it
listed.** The proof run's first launch died at the evaluation suite's
refusal before the campaign directory existed; `kapso watch campaign`
said `no status yet` (the receipt was read only once the directory
existed) and `kapso watch --all` knew nothing of it (the registry was
written after the orchestrator's construction, and its reader dropped
any path with no directory). Now a launch with an output directory is
registered as soon as the brief is read, before the evaluation refusal
and the preflight (a resume was registered by its launch; a build with
no output directory is registered once the orchestrator has made one);
the registry's reader keeps a path with a launch receipt beside it; and
the watch verb reads the receipt whether or not the directory exists.
A foreground launch that dies at a check leaves a registry line and
nothing else, which the listing skips. Alternative rejected: writing
the receipt into the registry's own line, which would make the registry
a second receipt. Shows in `Kapso.build`, `kapso.execution.inbox.
list_registered_campaigns` and `kapso.cli.watch`.

**The trace's JSON carries keys the plan did not list.** `sessions`
(top level): the session records that belong to no attempt, the harness
setup and a node still in flight, which the attempts' `sessions` cannot
hold and the failures section must still see. `branch`: the branch the
view was narrowed to, so `TraceView(data)` renders the narrowed text
again from the data alone. `header.status`: the status file's state,
phase and error, so a partial trace says why it is partial (running at a
phase, failed with its error, no status yet, or a record older than the
checkpoint). `attempts[].evaluation.output`: the evaluator's output, the
evidence of a rejection and of a crashed evaluator (S5's injection).
`lessons[].kind`: a hosted source renders differently from a bank (its
reads are not logged per card). `attempts[].cost_usd` and
`duration_seconds`: the node's own figures, "what it cost" per attempt.
After S4's first reading, two more: `header.cost.unpriced_runs`, the
Claude Code runs killed before their result event, whose spend the
total lacks (both readers worked it out from a `cost n/a` line), and
`attempts[].cards.listed`, the cards a session saw listed beside the
ones it read (`none (15 listed)` is not `none`). After the second,
`sessions[].hooks_staged`: a delivered block saying `hooks none fired
in its sessions` meant nothing when no hook was staged, and now says
so. After the pull-request review, `header.requests` (a campaign
waiting on the person renders `partial` with the count, as the listing
counts it alive), and the run entry's own keys beyond the sketch,
`cost_cumulative` (the host's figure the delta is taken from), `usage`
(the tokens, Codex's only figure) and `host_errors` (what the host
itself reported wrong), each on the trace page. Alternative rejected:
deriving each from the text's sections at the reader's end, which WP7's
skills would have to repeat. Shows in
`kapso.execution.trace` and `tests/test_trace.py`; WP7 reads the keys as
pinned there.

**The attempts come from the checkpoint's node history, not the
experiment history store.** The checkpoint's node carries the
verification, the load-bearing cards, the phase telemetry, the parent
branch and the evaluation output; the store (`experiment_history.json`)
is the gate's ranked view with fewer fields. A session's attempt is
found by the label grammar the staging uses (the branch for the
implementation, `verification/<branch>`, `feedback/<branch>`,
`ideation/iter<n>` for the n-th node), so no record has to name its
node. `complete` is decided by content, the record's `experiments_total`
against the checkpoint's `completed_iterations` with the status `done`,
not by file times, which an archive or a copy does not keep.

**The fixture generator reconstructs what the archives predate.** The
three archived proof runs were recorded before the run entries, the pull
log's session key and the current record schemas existed. The committed
generator (`tests/fixtures/trace/build_fixture.py`) rebuilds the session
records by splitting each Claude Code stream at its `result` events (a
trailing slice without one is a killed invocation, its error the
adapter's deadline text), times each run from the node's start and its
phases' durations, stamps each pull event with the session whose window
holds its time, lifts the records to the current schemas, blanks the
checkpoint's `agent_output` (the trace does not read it; the diffs it
does, for the delivered files, so they stay) and rebases the campaign's
own path to `/campaign`. The pull-request review found the generator
splitting a stream at its `result` events, a turn each: an invocation
begins at its `init` event (the hook events just before it are its own)
and holds every turn until the next; one that ended without a result
and was resumed is an `error` entry that says so, one killed at its
deadline a `timeout`. It is deterministic and the test proves it reproduces the
committed fixtures when the archives are on the machine. Alternative
rejected: hand-written fixtures, which could not carry a real delegate
report, a real void verdict or a real resumed session.

**A session staged again keeps its runs.** Re-staging the same label (a
phase re-run after a crash, a resume) used to rewrite the record with
`runs: []`, losing the entry the failed invocation had written in its
`finally`. The staging now keeps the entries already in the record at
that path, so the trace shows how the first invocation ended and that a
second one followed. Shows in `kapso.harness.staging.existing_runs`.

**The summary's label column is seventeen wide.** `Sessions failed:` is
the longest label; every pinned row in the docs and the tests moved two
columns. A shorter label (`Failures:`) would have read as failed
experiments.

## 2026-10-25, WP6 (planned; taken while revising the sub-plan after review)

**Every session has a record, and the adapters write its runs.** The
staging writes `session.json` for every staged session, harness or not
(WP2 wrote one only with a harness), and each adapter appends one run
entry per host invocation at the end of that invocation, in its own
`finally`, so a session that raises, resumes or retries is recorded as
it happened. Alternative rejected: a `finish(result)` call at every
site that runs a session, which has no result when the session raises
and misses the two Codex paths that bypass the adapters.

**`done` stays in `solve()`; the delivery runs inside it.** The facade
hands `solve()` a `finish` callable (the checkout and the record) that
runs inside the orchestrator's protected region before the terminal
publish, and the checkpoint completes after it. Alternative rejected:
publishing `done` from the facade after the record, which would strand
the five benchmark runners that call `solve()` directly and the tests
that pin `done` after it.

**A launch receipt beside the log.** `--detach` writes
`<campaign>.launch.json` with the child's pid and the log's path before
the child starts, so `kapso watch` can tell a campaign that is starting
from one that died before its status. Alternative rejected: a first
status frame written by the CLI, which the strategy constructor's own
`BuildStatus` would overwrite.

**The liveness rule is the view's.** A campaign is listed when
`OperationStatusView.alive is not False` (`starting` included, and a
machine without `/proc` judged by the heartbeat) or when it waits on
the person; the registry is written on every launch, inbox on or off;
the running learns and ingests are listed from `learning.status_dir`,
which takes `watch --all` off the observability design's deferred list.
`kapso inbox` keeps listing requests. `watch --tree` is retired: the
trace renders the attempts, and two renderers over one file would
drift.

**The trace prints evidence, not a merge verdict.** The six questions of
S4 are answered by a reader from the sections; the recommendation is
`kapso-review`'s, as its specification says. The verb keeps the master's
name, `kapso trace`, though WP1 retired `Solution.trace` because the
word promised a log: the trace renders the record and says so on its
page. The cost line carries its coverage (`claude_code` when any Codex
run exists), extending the status surface's time-only rule to a record
reader that already prints the campaign's cost.

**A refusal is read from the host's words, for now.** The Claude Code
adapter recognises the model's safeguard refusal by the result's text
(`API Error` and `safeguards flagged`), the shape the proof learns met;
the pull-request review asked for the structured signal WP3's finding
named (`model_refusal_no_fallback`), which is the API's error type
inside that same text, not a field of the result event. Until the host
exposes one, the words are the signal; a refusal worded otherwise would
be a failed turn with the words in its run entry, not a silent success,
since the digest keeps the result's text and the entry its error.

**The engine's errors print their message, on stderr.** For the
engine's own error classes the CLI prints the message alone (however
many lines, as the preflight's report is) and no traceback; any other
exception keeps its traceback. The CLI's own `Error:` refusals move
from stdout to stderr with them, so a script reading stdout sees
results only.

**The pull log carries the session.** The staging passes the session's
label to the bank gate's environment and every event records it, so
reads are attributed to the session that made them; an ask of WP3's
package, merged, taken here.

**The refusal is a result field and a config count.**
`CodingResult.refused` is set by the Claude Code adapter on the model's
safeguard refusal; the mining frame relaunches a refused lead
`learning.mining.refusal_relaunches` times (one) before any repair
round, and notes it through the learn status it is handed.

**`stopped_reason` and `requests` keep their names.** WP1 left the
rename open; both names are in the status file, the checkpoint and the
API, and a rename gains nothing.

## 2026-10-25, WP3 (taken after the sub-plan's review, while building)

**Scope is a filter again, on the harness coordinate.** The 2026-08
amendment made scope displayed information ("the index lists the whole
bank; the reading agent selects") because the `family:`/`dataset:`
coordinates were too fine: a card scoped to one dataset was useful on the
next. The coordinate is now the harness, which is the domain itself, so a
card measured under the predictive-modelling harness is noise in a
trading build. `mine` loaded at the default scope lists and reads only the
cards whose scope covers the coordinate (`domain`, or `harness:<name>`);
`mine:all` lifts that; a bank you read serves everything it holds;
quarantine is law under every scope. Alternative rejected: keep scope
displayed and delete the `scope` knob, which would have made the harness
coordinate decorative. Shows in `retriever.py` (the index and both reads
take the scope), the intro's count, `docs/experience/`.

**Loading never touches the network beyond a first fetch; `kapso
experience update` does.** The sub-plan had `mine` pull from its remote
on every load. Both reviewers showed what that does to a host session
(`kapso-mcp --experience mine` on a machine whose remote is unreachable
exits at every session start) and to a resume (the pin and the pull
compete). A load pins the local state; `update [ref]` pulls `mine`
fast-forward from its origin and re-fetches a bank you read at a moving
reference; `remove <ref>` deletes a clone or an index. A pinned commit
never moves; a campaign keeps its pin whatever `update` does later.
Alternative rejected: pull on load with a fallback to the local head when
the remote fails — a silent fallback (rule 2).

**`mine:all` is the lift's syntax everywhere.** `scope="all"` existed only
in Python; the CLI and the brief had no way to say it. `--experience
mine:all`, the brief's `Experience: mine:all`, `kapso-mcp --experience
mine:all` and `load_experience("mine:all")` are one form; `scope=` on
`load_experience` goes. A suffix on any other reference is refused by
name (a bank you read, the hosted gate and an index are always every
scope).

**The coordinate is the harness alone.** `build(serving_scope=)`, its
launch-record key and the `dataset` coordinate are retired with
`family:`; `KAPSO_TASK_HARNESS` is the one coordinate the gate reads.
Alternative rejected: keep `dataset` as a benchmark's extra coordinate —
a benchmark is a harness now (WP8), and a second coordinate would need
its own scope grammar, writer rule and tests for one caller.

**`none` is a reserved harness name.** `harness:none` is the coordinate of
a campaign with no harness, and WP2's name grammar allowed a harness
called `none`; `check` refuses the name. Alternative rejected: an
unnameable coordinate such as `harness:-`, which reads worse in a card.

**A card is identified by its source and its name; the citation grammar
stays `[card:name]`.** With two loaded banks holding one name, the gate
reads from the named source or the first that holds it and the pull log
records the source of every served row; the learning side credits a cited
name to the source the pull log shows it was read from, and reports a
name read from two sources as an ambiguity instead of guessing. The
evidence tool takes `source=` as the read does. Alternative rejected: a
qualified citation `[card:name@source]` — every prompt, parser and grader
that reads citations would change for the rare collision.

**One index per campaign.** The search gates hold one backend; two loaded
indexes are refused by name at planning. Alternative rejected: federated
search across indexes with result provenance, which no backend supports
today and which WP4 may revisit with the config.

**The loaded experience is campaign identity.** The references and their
scope enter the checkpoint's fingerprint; a resume loads the record's list
and re-pins each bank at the recorded head, and a resume that names a
different list is refused by name, as a changed harness is. Alternative
rejected: an operator dial like the budget — a campaign served a different
bank in its second half would be measuring two things.

**`kapso-mcp` serves the bundled gates only, by what is loaded and what
the directory holds.** `--gates` does not come back (the three
directory-driven gates turn themselves off with a reason; `kg` carries
write tools and never rode on a host); `--harness <ref>` gives the
session its coordinate, as a build has one; the intro rides as the MCP
server's `instructions`, so the session names its sources on connect;
`leeroopedia` loaded on the host prints the reminder to add it as the
host's own HTTP server; the session's staging directory is removed when
the server exits; a source that cannot be loaded stops the server with
the line that would fix it (no partial serving).

**The intro has its own slot.** `handler.additional_context` is frozen at
construction, so the intro appended after it never reached a session (WP2
recorded this). `{{experience_intro}}` is threaded into the ideation and
implementation prompts the way WP2 threads the harness guidance, and into
no other session; the test renders the prompts.

**Probe offers ride only your own bank.** A probe is a measurement you pay
for whose evidence lands in a bank you can write; a colleague's open
probes are not yours to run. The gate builds offers from `mine` alone.

**No `--experience` on `deploy` or `learn`.** Deploy's sessions mount no
gates at all (`deployment/selector`, `deployment/adapter`), so there is
nothing to serve; WP5 revisits when it adds staging. `learn` writes `mine`
whatever is loaded; `Kapso(bank=)` points `mine` elsewhere and is threaded
through every crew. The master plan's "on the three verbs" was the
harness interface's line.

**Team banks: `share` stays push-only.** Joining a team bank that already
has history, bare-repository synchronisation and divergence recovery are a
later package; `share` refuses a push the remote rejects, in git's words,
and the intro says "measured by you and your team" when `mine` has a
remote. Papers stay out the same way: no ingestor reads one; the
onboarding grammar marks `--paper` as not shipped, owner: the experience
package's second iteration.

**No `family:` knowledge anywhere.** The sub-plan had `kapso experience
list` mark a bank whose cards carry the retired coordinate; that needs
every card parsed on every `list` and keeps the old grammar alive in code
(rule 7). `list` is silent; a pre-release bank is re-learned.

**An index owns its namespace in both graph stores: a Weaviate collection
named after it and a Neo4j `corpus` property every node and query carry.**
The reviewers showed that two indexes holding a page of the same id
shared one Neo4j node, so adding a corpus changed what an earlier index's
"connected pages" returned. The graph backend now takes `corpus` as a
required parameter (the index's id), writes it on every node, matches on
it in every query and clears only its own nodes; the collection name is
`Kapso<Name><id>`, so a name removed and added again never meets its old
pages. The record's `backend_refs` carries both, which is how a loaded
index connects. Alternative rejected: one label per index, which needs
dynamic Cypher and gives nothing a property does not.

**`kapso learn <campaign>` is the verb's form; the learning system's own
commands move under `kapso learn dev`.** WP2 handed `kapso learn
<campaign> [--harness]` to this package. argparse cannot give one verb a
positional campaign beside nine subcommands (`import`, `mine`, `grade`,
`update`, `develop`, `codify`, `ingest`, `gauntlet`, `behave`): the
positional swallows the subcommand's name, or the subcommand parser
refuses the path. Those nine are the development regime's tools, for
people working on the learning system, so they live under `kapso learn
dev <command>` with the same flags, and the engineer's form is the plain
one. Alternative rejected: a subcommand named `campaign`, which is not
what the onboarding grammar and the docs promise.

**The learning crews are staged in full, and a harvest leaves the hosts'
staging directories out of a bundle.** The pages-only block the crews'
prompts carried is gone: the mining lead is staged at the bundle root like
any session (the learning module's skills, servers, delegates and hooks
beside the crew's own agent definitions and the contract), the update lead
in its run directory, and the update crew's `codex exec` workers in the
same directory in codex's format, `run-role.sh` exporting the harness's
variables and passing the staged servers, agent roles and hook trust, the
guidance read from a file beside the launcher. For a bundle to take a
staging and stay as harvested, the harvest leaves `.claude`, `.agents` and
`.codex` out at every level: they are the harness's files, recoverable from
the hash the manifest records, and the session records under
`.kapso/sessions`, which stay, say what each session ran with. The mining
crew owns those names at a bundle root for its session and refuses any
other occupant by name. Alternatives rejected: hiding a harvested `.claude`
for the session's length (the immutability check would have to learn the
hidden path, and the lead would see a directory the inventory does not
name); a symlinked view of the bundle for the session (the record and the
stream would land in the bundle through the links).

**A mining run has a directory of its own, `learning.mining.run_root`.**
Staging writes a session's record and stream under the campaign's
`.kapso/sessions`; a bundle takes no writes, so `stage_harness` takes a
`records_dir`, and a mining run's go to
`<run_root>/<trajectory>/.kapso/sessions/lead/`, an update run's to
`<run_dir>/.kapso/sessions/{lead,workers}/`, as every other crew keeps its
runs under `learning/`. The mined view itself stays in the bundle.

**The guidance names the task statement only when the campaign has one.**
A learning run's directory has none and an archived campaign has its
build's; a build writes the statement before its sessions, and the setup
session, which writes the domain statement the task statement is composed
from, has the path in its own prompt.

**A bare name is never a path.** The plan let a bare name that is a
directory be read in place, and the reviewers showed the trap: the
checkout an index was made from, beside the run, shadowed the index of
the same name, and the name could then neither be loaded nor removed. A
path is written as one (`./`, `../`, `/`, `~`) and must exist; a bare
name is a reserved name, a git shorthand or an index. The forms table is
corrected.

**A bank read by path is re-loaded from its recorded location, named as
the launch named it.** A resume or an inbox reply may run far from the
launch directory; the record's `resolved` is absolute, so that is what a
resume re-loads, and the source keeps the launch's spelling of its
reference so every record and the fingerprint agree. A reply rebuilds
the object with the bank the launch had (`Kapso(bank=)` is the record's
`mine` entry).

**A bank at a tag is pinned at the tag.** `bank_head` reads the commit a
bank is at (`HEAD`: `main` in a bare home, the checked-out revision in a
clone), not `main`, so `acme/kapso-bank@v1` records, counts and serves
the tag's commit. One clone directory per reference: the directory's
name carries a digest of the reference, so two references that read
alike as names never share a clone.

**An index pin holds at the build.** A handle that loaded index A while
the name was removed and ingested again as B before the build is refused
at the build, as a resume with a stale record is: a campaign is served
the index it loaded, never one that happens to carry the name now.

**Attribution starts at reading.** The exposure ladder carries three
rungs; a citation is credited to your bank when the card was opened from
it (`read` or `evidence-read`), a copy only listed by `bank_index` was
never read, and ambiguity means opened from both sources. A claim of
independence is refuted by any exposure, a listing included. An
unqualified `bank_get_card` with two banks goes to the first bank that
can serve the name under its scope, so what the index advertises a plain
read opens.

**The hindcast and the behaviour scenarios replay the surface a campaign
loading `mine` is served.** `compile_intro` moved to the serving module
and composes the same intro, for `mine` at its default scope under the
task's coordinate; the index they grade is rendered under that scope. A
card of another harness is not availability the grader can charge a
campaign with. The behaviour fixtures recorded with the earlier
coordinates stay exempt from the drift test and are re-recorded when WP8
ports the RelBench harness.

**A lesson that admits nothing moves nothing.** A crew that changed no
card, sighting or quarantine entry used to commit the rebuilt log alone,
so the bank's head moved and the lesson read as admitted. The frame now
commits, tags and pushes only when the bank's content changed; otherwise
the report carries one head before and after and `learn()` says the
lesson admitted nothing.

**`kapso experience add leeroopedia` probes the gate once.** The plan's
Interface promised it: the add sends the hosted server one MCP
`initialize` with the key on its URL and reports the server's name; a
refusal or an unreachable server stops the add with the status; an empty
`LEEROOPEDIA_API_KEY=` is no key. Loading stays a presence check. The
loaded source carries the URL and timeout of the config it came from,
and the sessions mount exactly those (`get_mcp_config(hosted=)`), never
the packaged address; a config gate list naming the hosted gate does not
mount it, since what is loaded is what is served and the records name it.

**A learn may run under a harness the build did not have.** `kapso learn
<campaign> --harness <ref>` on a campaign whose record names none loads
the harness for the crews (its learning module shapes their sessions)
while the lessons keep the build's own coordinate (`none`); a deploy
still runs as its build did.

**The hosts' staging names include the adapter's MCP directory.** The
Claude Code adapter writes `.claude_mcp/` beside a session; the frames
call the adapter's cleanup after the lead's session, and the harvest
leaves the directory out with the other staging directories.

**The research ingest's modes and depth are config.** `experience.
research_modes` and `experience.research_depth` replace two module
literals; the researcher's findings are unwrapped into the typed
sources the pipeline ingests.

**A `result.json` left in the evaluation directory is refused at
launch, not skipped.** (Taken during the proof run.) The evaluator
writes `kapso_evaluation/result.json` by contract, allowed as a new
runtime artifact; a copy an earlier run left at the root of the caller's
directory was protected with the suite, and the first evaluation changed
it and rejected every candidate. The launch now refuses the leftover by
name, with the way out in the message, at the facade's input check and
at the orchestrator's manifest. Alternative rejected: leaving the file
out of the manifest and the copy silently, which would split the
integrity rule ("every file in the suite is protected") with a special
case, reach the vendored archive sandbox and its byte-identical copies
in the benchmark suites, and still leave a stale result in the
workspace for a session to read. Whether the contract should move the
result out of the protected tree altogether is WP4's.

## 2026-10-25, WP2 (taken while building)

**A harness's Python requirements are checked against `python3` on PATH,
not the engine's interpreter.** The sub-plan said `importlib.metadata` in
the engine's process. The harness's servers, hooks and scripts run on the
`python3` the authoring guide tells the author to name, which is the
engine's interpreter only when Kapso is installed into an activated
environment; a `uv tool` install (the fresh machine, the install skill)
runs the engine in a venv of its own with no `pip`, so the fix line
`<sys.executable> -m pip install -r` could not even run there, and a user
who followed it would have installed into the interpreter nothing of the
harness uses. `check` now asks `python3` on PATH for its distributions in
a subprocess, reports its absence as a need of every module, and the fix
line is `python3 -m pip install -r <file>`. Alternative rejected: checking
both interpreters, which doubles the rows and still names the wrong one.

**A session that names no directory is refused, not staged into the
working directory.** Found by a test whose nodes had no directory and
left `.claude/` and `kapso_task.md` in the repository root; production
nodes always carry one. The guard sits after the no-harness path, which
writes nothing, so a build without a harness is untouched.

**The verification session runs on the implementation CLI, not the
judge's.** The sub-plan had it on the judge's host; the review pointed
out that a campaign whose attempts are implemented on Codex then had
its verification on Claude Code, so the Codex rows of the host table
(hooks, roles) were never exercised by the step that matters most.
The attempt's own host verifies it, with the implementation model.
Alternative rejected: a `verification_cli` knob, a knob nobody asked for.

**An `env` entry of a harness server names the variable it forwards, and
every `env` or `headers` value is one whole reference.** Claude Code
expands `${VAR}` wherever it sits and would accept
`"BROKER_API_KEY": "${MY_KEY}"` and `"Bearer ${TOKEN}"`; Codex forwards
variables by name and takes neither. Rather than translate per host (a
value on a command line, or a literal header), `check` refuses both
shapes and the guide says why. The `Bearer` prefix lives inside the
variable.

**A module's staging into a shared directory is exclusive.** Sessions at
the campaign root follow one another; the second used to find the
first's skills beside its own, which contradicted "nothing is inherited"
and the session's own record. Each staging removes the harness's skills,
hooks file and delegates that are not this module's. Alternative
rejected: a directory per session at the root, which moves the judge
and the maintainer out of the campaign root they read.

**A verification session that fails is said so, and no retry runs under
the budget's deadline.** The verdict's summary carries the session's
error (a kill, a crash) instead of "wrote no verdict", so the judge and
the record can tell a dead session from a silent one; a second session
is launched only when the first had its configured time, since the
budget's clamp would give the retry less still.

**A loaded harness is never attached to a campaign built without one.**
`deploy()` and `learn()` refuse it by name; a verb on a finished build
runs as the build did. Alternative rejected: silently adding the
deployment or learning module after the fact, which the Interface
forbids.

**The store's fetch record sits beside the clone.** Inside it, the record
changed the hash of a harness at a repository's root on every fetch and
overwrote an author's own `source.json`; two revisions whose names
sanitise to one directory are refused rather than served as each other.

## 2026-10-24, WP1 (after the third proof run)

**`solution.feedback` is the judge's words on the delivered candidate; the
last judgment only when nothing was delivered.** The third proof run
delivered node 0 (0.8474) and the record's feedback was node 1's failed
judgment ("the required tags were missing after a retry"), because
`build()` took `final_feedback` from the solve result. It now reads the
delivered node's feedback from the strategy, and `explain()` labels the
block `Feedback:` rather than `Last feedback:`. Alternative rejected:
carrying both, which doubles a field nobody asked for.

## 2026-10-24, WP2 (planned; taken while writing the sub-plan)

**The engine never installs a harness's requirements; it names what is
missing and the line that installs it.** The design says `build()`
"prepares the harness's requirements in the run's environment". A harness
can arrive by git URL, and an engine that runs `pip install -r` on whatever
it fetched is a supply-chain hole the engineer never agreed to. So
`check`, `harness add`, `doctor` and the refusal in `build()` report each
missing distribution with `pip install -r <path>`; the engineer runs it
once per machine. Alternative rejected: installing silently.

**Delegates are the hosts' own sub-agents on both CLIs, not engine-run
sessions behind a tool.** The design allowed either ("registered as
sub-agents, or run as their own session where the CLI has none"). Both
hosts have sub-agents: Claude Code takes `--agents` with the name,
description and prompt (verified: the model asks it by name and gets the
reply), and Codex's `multi_agent` is stable. Native agents inherit the
session's skills, servers and hooks for free and the host records their
transcripts; an engine-run session behind an MCP tool would sit inside a
tool call with the host's tool timeout around it. The one open point is
whether Codex takes named roles per invocation; the sub-plan carries the
fallback (spawn with the agent file's text as the first message).

**The task statement is an untracked file at the campaign root, copied
into every session directory; prepared resources are a real directory at
the root and a symlink everywhere else.** `kapso_evaluation/` is committed
to the workspace's main, which is why it reaches every clone; a task
statement committed that way would land in every candidate branch and in
the delivered code. Untracked and ignored, it reaches sessions the way
dropped data does (`_bring_dropped_data`), and the ideation worktree gets
a copy at staging. A snapshot under `prepared/` can be large, so one copy
at the root and a link per session; the `protect-prepared` hook is the
guard the harness chose, and the design says a hook is not a boundary.
Alternative rejected: committing both to main.

**A verification session that writes no verdict is run once more; still
nothing, and the attempt is `unverified`: it keeps its score and stays a
parent, is never delivered while the harness has verification, and the
judge is told.** The first draft left such an attempt valid; both
reviewers objected that an unchecked candidate could then be delivered on
a verifier timeout, which is the one outcome a verification promise must
exclude. A malformed verdict still raises (rule 2). Alternative rejected:
treating a missing verdict as void, which would discard good attempts on
a formatting slip, and treating it as valid, which would deliver them
unverified.

**Export moves to WP7.** An export has to carry `servers/`, the
requirements, the hook scripts and the delegates with their references
rewritten per host, and prove the result loads; that is host plugin
layout work, which WP7 owns, and nothing in a build needs it. The design's
surface line points at WP7.

**The recently-used list of local harnesses is dropped.** `list` shows
what is bundled and what is fetched; a local path is used by path. One
JSON file and a `forget` command were the price of one row of output.

**Delegates on Codex are named roles, verified, so the design's "own
session" fallback is not built.** `agents.<name>` with a description and
a config file whose developer instructions are the prompt; the role is
spawned by name and the host's sub-agent events carry it. One mechanism
per host, no runtime fallback.

**Prerequisites are scoped to the modules a verb runs.** The trading
harness's deployment-only broker server would otherwise refuse every
build on a laptop with no broker credential. A build refuses on the
requirements of setup, ideation, implementation, verification and
feedback and prints the rest as advisory; deploy and learn refuse on
their own module's.

**Setup and verification run only when the harness has content for them.**
A harness with no `setup.md` and no setup attachment gets no setup
session; the same for verification. The engine's deterministic parts
(the directory setup, the integrity check, the registered evaluation)
always run. A build with no harness is byte-for-byte today's behaviour;
nothing new runs for it. Alternative rejected: a setup session for every
build, which would add minutes to the first-build time WP1 already found
long.

**A loaded harness wins over the brief's `Harness` line, and a path in
that line resolves against the working directory.** The first is the rule
WP1 set for budgets (call arguments over the brief); the launch print
names the harness used so the override is visible. The second is what
every other path the CLI takes does; a brief that is run from its own
directory, as the examples say, can use a relative path. Alternative
rejected: resolving against the brief file's directory, which would make
`Brief` carry a base path and break `parse(render())`.

**Harness servers on Codex are mounted with `default_tools_approval_mode =
"approve"`.** The probe showed a stdio server's tool refused under a
read-only or workspace-write sandbox with no key and with `auto` ("MCP
tool call requires approval, but approval policy is never") and running
with `approve`. The shipped adapter uses `auto` for hosted gates; whether
that binds anywhere today is for the package that next touches a Codex
inference session (noted in the sub-plan).

**`export --format cursor` is dropped from WP2.** The design listed three
formats; Cursor's plugin layout is not verified from here and nobody has
asked for it. Two formats ship; a third is one function when wanted.

**The sub-plan was written before WP1's pull request was opened, on the
same branch.** The third WP1 proof run was in progress, and the plan does
not depend on its result; the planning document rides in WP1's PR as a
documentation commit, and WP2's code branch is cut from `redesign` after
the merge. Alternative rejected: idling for an hour.

## 2026-10-24, WP1 (planned; taken while revising the sub-plan after review)

**The brief has its own flag, `--brief`; `--goal-file` stays plain text.**
The design documents said `--goal-file kapso-brief.md`. A file that is not
a brief must not be guessed at (no silent fallback), and engineers do pass
plain problem statements by file today, so the two forms get two flags.
Alternative rejected: one flag that tries the brief grammar first.

**A solution's one path is `trace`.** `SolutionResult.code_path` and the
design's `Solution.trace` were the same directory: the workspace, checked
out at the delivered branch, with the record under `.kapso/`. One field,
named `trace`; deployment reads the code from it.

**`build()` writes `.kapso/solution.json` on every return, and `open()`
reads only that.** The alternative, reconstructing a solution from five
record files, needs rules for which file wins and has no durable
evaluation log to read. The facade already computes the delivered score,
the branch and the registry head at return; writing them is a few lines,
and a paused or budget-stopped campaign gets a record too.

**`Experience` is WP3's.** The design returns `Experience` from `learn()`;
today's `LessonResult` is that class. Renaming it belongs with the
experience work, not with `build`, so WP1 leaves `learn()` returning
`LessonResult` and only changes its parameter type.

**`kapso deploy` takes a solution, not a directory of code.** Today's
command constructs a result from any path. In the design `deploy` takes
the outcome of a build, so the command opens the record; deploying an
arbitrary directory is not a case of this verb. WP5 may add a `--repo`
form if a user needs it.

**`Kapso(config=...)`.** The constructor keyword follows the design; the
internal attribute keeps its name.

**A sentence goal is rendered as a brief too, so the engine always sees one
grammar.** `build("Raise AUC above 0.85")` renders `Objective    Raise AUC
above 0.85` into the goal text, the checkpoint fingerprints that, and a
resume parses it back; `kapso inbox` reads the objective's first line the
same way. Alternative rejected: passing a plain string through untouched,
which would have left the checkpoint holding two shapes and the resume
guessing which one it had.

**The brief keeps paragraphs and pasted indentation.** Blank lines between
two lines of the same field stay as paragraph breaks (elsewhere they are
nothing), and a field's continuation lines are dedented together, so a
pasted traceback or code block reaches the model with its relative
indentation. Rule 6 asked for the content whole; this is what "whole"
means for a multi-line objective. Alternative rejected: stripping every
continuation line, which flattens code.

**The `Solution` dropped three things the old result carried.**
`experiment_logs` (one line per node, re-derivable from the experiment
history and WP6's `kapso trace`), `resumed` (the checkpoint knows) and
`status_path` (always `trace/.kapso/status.json`). Each was a field nobody
acted on; rule 10.

**`final_report.json` carries flat keys instead of an opaque `metadata`
dictionary.** `learn()` writes `goal`, `succeeded`, `final_score`,
`stopped_reason`, `iterations`, `cumulative_iterations`, `cost_usd`. The
report's readers (the trajectory store, the mining crew) never read
`metadata` by key; they read the file as prose, so named keys serve them
better than a dump of the old dictionary.

**The first-build budget is forty-five minutes, because ideation alone
takes twelve to fourteen minutes on the shipped config.** The second proof
run's timeline (file mtimes and the status file on the fresh machine):
the campaign started 21:49:04, setup and repo memory were done by
21:49:08, the implementation session's folder appeared at 22:01:26, and
that session was killed at its 60-second floor at 22:04; the Python-flow
campaign launched at 22:07 was still in `ideation` at 22:21. So a
fifteen-minute campaign spends it all on the ideation session
(`claude-opus-5` with four gates) and the implementation gets the floor.
The first-build example and page now say three quarters of an hour and
the brief says `minutes=45 experiments=3`; the "ten minutes" the docs plan
promised is not true of the shipped config and is not claimed. A faster
profile for small briefs (a lighter ideation for a one-file task, fewer
lanes, or a quick mode) is a product question for WP4, the config
package, and is listed in the sub-plan's findings for later packages.

**The launch record is written on every fresh campaign, not only with the
inbox on, and it carries the brief.** A resume reads the launch's budget
and flags from it; with the inbox off there was no record, so a bare
resume dropped the brief's minutes and dollars (the pull-request review
found it). Registering the campaign in the inbox's registry stays
conditional on the inbox: that file is the inbox's. Alternative rejected:
keeping budgets only in the checkpoint, which does not hold them.

**`deploy()` refuses a solution with no candidate and a campaign directory
not checked out at the delivered commit.** Deployment copies the directory
as it is; after `git checkout main` for a look around, it would have
shipped the seed under the winning score. The refusal names the checkout
command. Alternative rejected: checking the commit out silently, which
moves a directory the person is working in.

**A bullet or a number at the start of an objective's line is text.** The
parser used to refuse a `- ` line under a text field so a misplaced rule
would not vanish into the objective; but goals carry bullet lists, and a
brief built in Python with one could not be read back. Text fields take
any text; `Rules` and `Experience` alone take items. Alternative rejected:
escaping bullets in the file, which no one would type.

**`solution.evaluator` is `None` with the shipped config, and the pages say
so.** The evaluation registry is written by the evaluation maintainer,
which runs only when a config has an `evaluation_maintainer` block;
`GENERIC` and `MINIMAL` have none. The pages describe the shipped
behaviour (a provided evaluator is protected by the integrity check; a
proposed one is judged, not registered) and name the block. Turning the
maintainer on by default is WP4's decision, with the config.

**No abbreviated flags on `kapso build`, `inbox` and `deploy`.** argparse
accepts `--det` for `--detach`; the detached child strips only the full
flag and would detach again, forever. `allow_abbrev=False` on the three
parsers whose flags a child re-reads. Alternative rejected: stripping
every prefix of `--detach`, which hides the trap instead of closing it.

**Fourteen public names changed after the naming review, two user-chosen
words did not.** Both reviewers (Codex gpt-6-astra at xhigh, Claude Code
opus-5) judged every public name of the build surface; the table in
`wp1-build.md` ("Naming review") lists each change and its reason. The
pattern: where the code's word and the word every person-facing string
used disagreed, the person-facing word won (`experiments` over
`iterations`); where one word was spent three ways, each thing got its own
(`evaluation` the directory, `evaluator` the stamp); where one directory had
five names, it got one (`campaign`). `Harness` and `Experience` stayed:
they are the owner's names for the two layers (2026-10-21, 2026-10-24),
and the reviewers' alternatives (`Domain`, `Lessons`) were judged on
cold-reader clarity alone. These renames touch the design document's
section 8 (`solution.trace` → `solution.campaign`,
`solution.evaluation.version` → `solution.evaluator.version`), which is why
they are here for the owner to check.

**The facade resolves every path it is given, and the workspace keeps its
directory absolute.** The first proof run on the fresh machine crashed at
the first session close: `--output ../churn-build` reached the experiment
workspace relative, the session clone ran `git add ../churn-build/...`
from its own directory, and git refused it as outside the repository. The
code is unchanged from `main`, so every relative `--output` whose session
left run data behind crashed before WP1 too; the fresh machine found it
because nothing from the development checkout masked it. `build()` now
resolves `output`, `evaluation`, `data` and a local `repo` (a URL is left
alone), and `ExperimentWorkspace` takes `os.path.abspath` of its directory,
so a direct caller is covered as well. Rule 7 applies: no second code path
for relative directories.

**A five-minute budget starves the implementation; the proof uses
fifteen.** The budget's `clamp_timeout` bounds every session by the time
left outside the reserve, with a 60-second floor, so a five-minute
campaign gives its first implementation about a minute, which the deadline
then kills. The example brief says ten minutes and four experiments; the
proof run passes `--budget-minutes 15 --iterations 2` on the command so
each session has room, which is also what the flags-win-over-the-brief
rule is for. The ten-minute claim on the first-build page stands for the
whole example on a machine with the libraries installed; it is measured by
the proof run and will be corrected if the run says otherwise.

**The examples are the semantic fixtures, under `examples/`.** The docs
plan said one source; the WP0 fixture lived under `tests/semantic/`. It
moved to `examples/churn-first-build/`, and `tests/semantic/README.md`
points at the examples. Alternative rejected: a copy under `tests/`, which
is the drift the plan forbids.

**The engine pages stay at their URLs, regrouped as "How it works".** The
docs plan retires the Evolve pages into condensed How-it-works pages. WP1
regroups them in the navigation and fixes their snippets, and leaves the
condensation to the packages that change their content (the config, the
record and the trace), so each page is rewritten once. Two pages did move
into Build (the inbox, resume and budgets), with redirects.

**The older examples keep their evaluator inside the repository until
WP2.** Moving each `evaluate.py` into a protected `evaluation/` directory
changes how it is invoked and needs each example run again; the harness
re-base in WP2 does that work once. Until then the brief's rule ("the
evaluator is never modified") is what protects it, as it did before.

**`Brief` is both the Python object and the file, one grammar.** The
interfaces document left open whether the brief is an API object or a
CLI-only file. `Brief.read` parses the file into the object and
`Brief.write` emits it, so the plugin, the CLI and a script hand the engine
the same thing, and `build()` renders the whole brief into the engine's
goal text. Alternative rejected: a file-only brief that the CLI flattens
to a goal string, which would leave Python users without the structure.

**Two names are left for later packages, on purpose.** `Experience` as
`learn()`'s return collides with `load_experience`'s source handle; WP3
settles it with the experience work. Whether a brief's `Harness` line or
a `load_harness()` call wins when both are given is WP2's, with the
loader. Neither is decided here.

## 2026-10-24, WP0

**Codex on the fresh machine logs in with an API key, Claude with the shared
OAuth token.** The fresh machine (`scripts/redesign/fresh_machine.sh`)
authenticates Codex with the `openai-api-key` secret from the benchmark
project's Secret Manager, via `codex login --with-api-key` over ssh stdin,
and Claude Code with the `claude-oauth-token-3` secret the campaigns already
use. Why: a copied ChatGPT session is single-holder; the copy that refreshes
on the machine revokes the development box's session, which runs the long
campaigns. A key is metered per token, revocable per machine and leaves no
shared state; a ten-minute proof run costs cents. Alternative rejected:
copying `~/.codex/auth.json` as the campaign waves do. Consequence: proof
runs and semantic runs that use Codex bill the OpenAI API account rather
than the ChatGPT plan; the Claude side still spends the shared weekly
window, so the token gate (probe the CLI per model before a long run)
applies to the fresh machine too.

**The CLI's top-level help keeps its hand-written epilog for now.** The
reviewers suggested replacing it with the parsers' own `help=` strings. WP0
keeps the text byte-identical (apart from trailing whitespace) because its
contract is "no behaviour change"; WP1 rewrites the help when `evolve`
becomes `build`.

**`deploy --interactive` stops on SIGINT through a signal handler instead
of `try/except KeyboardInterrupt`.** Same behaviour (the software is stopped
and the command exits 0); CLAUDE.md rule 2 forbids exception handling, and
WP0 chose to fix the violation in the move rather than carry it into a new
file. WP5 rewrites deploy anyway.

**The semantic fixture's hold-out is not sealed yet, and says so.** The
labels live outside the directories the engine copies into a workspace, but
a process in the workspace can read the absolute path the evaluator uses.
Sealing is the engine's job (evaluation integrity and permissions, build
steps 2 and 6); the fixture measures the flow until then, and its README
states it. Alternative rejected: a fixture-level trick (an encrypted labels
file, a separate evaluator process with its own credentials) that would
have to be undone when the engine seals hold-outs properly.

**The fixture's signal was reshaped for headroom.** The first generator
gave a logistic baseline of 0.742 AUC that a boosting model could not beat
(0.728). A fixture where nothing beats the baseline cannot show a build
working, so the label's logit gained thresholds, an interaction and a tenure
curve: logistic 0.797, boosting with no feature work 0.832. The persona and
the README carry the measured numbers, not round ones.
