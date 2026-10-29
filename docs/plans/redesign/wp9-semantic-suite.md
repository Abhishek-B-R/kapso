# WP9: the semantic suite

2026-10-27, second version after the sub-plan's review (the first version
is `e20e7395`). Owner: the redesign's author. Branch `wp9-semantic-suite`
off `redesign` after WP7's merge (5cca2905). Size: L (MASTER's table said
M, spread; the row is corrected at merge): the suite is a release gate,
not a per-commit check, and every run costs hours and model spend.

## Scope

The semantic production tests of `docs/plans/semantic-production-tests.md`
made runnable, each with a gate the report computes, and run once each
where the machine's credentials allow: a simulated user from a persona
card driving the host turn by turn (the other vendor's CLI playing the
engineer, every host turn offered to it), a judge from a third vendor
grading rendered conversations and artifacts in two blind passes, S1 (the
cold engineer on the Python and CLI flow, with a retrospective baseline on
the released package), S2 proper (the plugin round with the persona and
the judge, both hosts, the second engineer's served build included), S4
(the trace read without the agent on a campaign that holds a void and a
rejection, judged against a hidden fact sheet), S5 (six injections with a
host session in the loop: a provider limit, an evaluator crash, a missing
key answered by a local service, a killed session and a killed writer, a
full disk, an evaluator tampered with), S6 (two seeded builds, the second
served the first's lessons, on a sampled timeline), and the author test's
second round on the `pipeline-dbt` fixture; one runner per test over the
fresh machine; one report per run under an immutable id. The learn's two
fail-loud cases the plugin round found are repaired as far as CLAUDE.md
allows (change 1, built), and the learn's real blocker on the fresh
machine is named: its grader roles run on Codex, and the machine's Codex
key has no credit.

**What WP7 deferred here**, each answered: the command-to-skill handover
read as the procedure (S2 measures it from the session's skill events);
the handoffs' tighter form (measured again under the twelve-line caps; a
finding for the skills, not rewritten here); the interview's silent
modules (the persona asks for the pages; measured); the inbox fixture
service and the continuation that uses it (S5's missing-key injection);
the review near misses' turn cap (the cases' `max_turns` raised to eight,
a knob in `plugin/evals`, allowed by the bounded exception below); the
second engineer's served build (S2's ninth step, a build at a tiny budget
on the teammate's own install); a staged card for the session brief (the
brief step runs after S6's learn has banked one, the bank served by
reference); the stop-then-resume continuation (S5's killed-writer case);
the machine's examples dependencies (the installer's venv).

**Not in scope.** S3's non-regression and abstraction parts (the harness
ports, WP8, parked until the owner says go). The release gate's full run
from the wheel to be released (WP11). The docs' pages for the suite beyond
`tests/semantic/README.md` and the authoring guide's fixes the author test
demands (both WP10 slices this package owns, named below). A skill, page
or verb the suite finds wanting is a finding here and a fix in its
package (MASTER: "anything that fails there reopens its package"), with
one bounded exception: a sentence in `plugin/skills/*/SKILL.md`,
`plugin/commands/*.md`, `plugin/evals/**` or `docs/**.mdx` that the suite
shows wrong, when one sentence settles it and the package is merged; never
engine code.

**The Codex login the machines run on.** The fresh machine's Codex API
key (`openai-api-key` in Secret Manager) answers the models listing and
refuses a response with `credit_balance_exhausted` (probed 2026-10-27
08:18 UTC), so every Codex role on a fresh machine — S1's Codex engineer,
S2's Codex host and the persona when Claude Code hosts, S4's Codex
reader, the author test's Codex author, the learn's grader roles — runs
on the owner's device-auth ChatGPT session instead: `fresh_machine.sh`
pushes its `auth.json` to each machine at install (and `plugin_proof`
copies it to the second engineer's Unix user), writes `~/.codex/SOURCE`
beside it, and every driver copies that line into its record's notes
(DECISIONS 2026-10-29; the runs before that mark were on the same
session, said in their records below). The arms therefore ran on fresh
machines, not on the development box; **advisory** is the development
box's mark alone (`--advisory`), and no run in this round carries it.
The cost of the path is the owner's: the session is a personal login
copied to throwaway VMs, and a refresh by any copy can revoke the
others (the Risks).

## Interface

**Exposed.**

- `tests/semantic/suite.json`, the one home of the suite's knobs and
  bars, read by every driver and by the renderer, echoed into each record:
  per test its `required_steps`, per step its budgets (`messages`,
  `questions`, `minutes`, `longest_message_lines`) and its metric bars
  (`first_try_min`, `wrong_calls_max`, `gap_min`, `structural_guesses_max`,
  `user_messages_max`), the judge's dimensions with their bar, the models
  and efforts of the user and the judge, the per-step turn cap, the
  persona's patience rule, the shim's count, the tmpfs size, the fixture
  manifests' expected hashes. The sampling cadence of a timeline is the
  engine config's `budget.checkpoint_heartbeat_seconds`, read through
  `load_config`, never copied. `budgets.json` folds into it and is deleted
  (Rule 7); `test_the_budgets_cover_every_step_of_the_round` becomes the
  check that every driver's step names are in `suite.json`.
- **The record, second shape** (`tests/semantic/README.md`): `test`, `host`,
  `machine`, `advisory` (true when an arm ran on the development box, with
  the reason), `run_id` (`<test>-<host>-<UTC stamp>`, immutable: a rerun
  is a new record, never a replacement), `pins` (what the driver pinned:
  `suite_sha256` always, `wheel_sha256` where a wheel was installed, and
  the test's own — the campaign read, the grid's cadence and the builds'
  budget, the guide's hash; the CLI versions are in the machine's install
  log under the run directory), `user`
  (`kind` scripted or persona, `card`, `card_sha256`, `vendor`, `model`,
  `effort`, `prompt_sha256`, `interventions`: the driver's out-of-band
  acts named per step), `steps` each with `name`, `kind` (`conversation`,
  `attempt`, `injection`, `build`, `reading`, `shell`), the conversation
  counts for a conversation, a `metrics` mapping for the others,
  `completed`, `artifacts`, `notes`, or `deferred` with the reason,
  `judge` (`vendor`, `model`, `route`, `passes`: two, each `scores`
  mapping a dimension to `{score, evidence: [{where, quote}]}`,
  `adjudication` when a dimension straddles the bar, `prompt_path`,
  `raw_paths`), `verdict` (computed by the renderer, below), `notes`,
  `transcripts`. WP7's three records are re-derived into this shape by a
  one-time script (`kind: conversation` on every step, `user: scripted`),
  their reports re-rendered; Rule 7 allows it, the Proof run of WP7 keeps
  its numbers.
- **The verdict** `report.py` computes and the runner's exit status
  carries: every `required_step` of the test present and `completed`
  (a deferred required step fails the run; `all([])` cannot pass because
  a test's required steps are never empty), every budget met, every
  metric bar met, the judge present where the test requires one with both
  passes' scores at or above the bar (a straddling dimension adjudicated
  by a third pass, else failed), no judge failure (a malformed reply is a
  judge failure, reported as such, never a pass), and the arm not
  advisory for a fresh-machine acceptance. The report renders each kind's
  table, the judge's two passes with their evidence, the pins, the
  interventions, the advisory flag first.
- `tests/semantic/personas/<name>.yaml`: `ml-engineer` (exists),
  `trading-author` (the harness interview's persona: knows the six module
  answers of the trading repository the scripted policy held), `second-
  engineer` (the teammate: terse, no context, wants a build served the
  shared bank), `data-engineer` (the author test's reader of the dbt
  fixture, not an S1 arm). A card carries `name`, `role`, `expertise`,
  `knows`, `wants`, `patience`, `answers`, `pushes_back_when`, and
  `planted` (one fact the card knows that the task view states wrongly,
  for the pushback check below).
- `scripts/redesign/simulated_user.py`: `next_message(card, task_dir,
  intent, history, host_message, vendor, settings) -> Reply`, the
  persona's next message from the other vendor's CLI (`codex exec` when
  the host is Claude Code, `claude -p` when the host is Codex; the vendor
  and model from `suite.json`), with `Reply(text, done, session, seconds)`:
  `done` only when the reply is `DONE` alone on its own; a non-zero exit,
  a timeout or an empty reply raises (a quota-refused persona is never a
  satisfied user). The prompt carries the card, the task view's README
  (never the example's), the step's intent, the whole history and the
  host's message, nothing clipped; the persona is told how many questions
  it has been asked against its `patience`, and is terse by the card's
  rule after it. The persona gets no tool, no hidden host reasoning, no
  expected answer. The prompt template's sha256 is recorded.
- `plugin_proof.py --user scripted|persona:<card>`: every completed host
  turn is offered to the persona (the loop no longer ends when a turn
  does not ask); the step ends on `DONE`, on the step's turn cap (an
  explicit `incomplete: turn cap` in the step, never a pass), or on the
  driver's own completion predicate; satisfaction (`DONE`) and completion
  (the predicate) are recorded apart. Per step the persona is given the
  step's intent; the driver keeps its out-of-band acts and names them in
  `user.interventions`: the key written where the request's fix line says
  before the person says so (inbox), the fixture written (the criteria
  steps), the harness's module answers as the `trading-author` card's
  knowledge (harness new), "do not launch" as the criteria personas' wants.
  The pushback check: the churn task view states the baseline as 0.90
  where the card knows about 0.80; the proposal's baseline line is
  expected to carry the wrong figure and the persona to correct it; a
  persona that does not push back makes the arm advisory for the
  `not annoying` and `engaging` dimensions, said in the record.
- `scripts/redesign/judge.py`, a standalone pass on the development box
  over a fetched record directory: `judge <record-dir> --rubric <name>`
  renders each conversation step as the user's messages and each turn's
  final text (what the rubric grades; the streams are never fed whole),
  one model call per step, two blind passes, the step's dimension score
  the call's, the run's dimension score the minimum over steps (the worst
  step binds), a third pass adjudicating a straddling dimension; the
  reply must be exactly one JSON object (a code fence around it allowed)
  with exactly the rubric's dimensions, integer scores in 1 to 5, and
  evidence entries `{where: <transcript or artifact path>:<line>, quote}`
  whose quote occurs at that location; anything else is a judge failure
  with the raw reply kept. The vendor: Gemini `gemini-4-argon` on Vertex
  in the credit project through LiteLLM, preflighted with one small call
  before any machine run; there is no idle vendor when Claude Code and
  Codex have played host and user, so without the route the run is
  reported **unjudged**, the hard metrics stand and the judged bar is
  "not established": acceptance blocked, never a weaker judge. The
  rubrics as files under `tests/semantic/rubrics/`: `s2.md` (the design's
  five dimensions; the not-annoying clause reads the step's own line
  budget, which the judge's material states beside the exchange; a step's
  `judged` list in the suite says which dimensions it is scored on), `s4.md` (six questions: Q1, Q3, Q4, Q5
  scored against the fact sheet's extracted facts; Q2 and Q6 on two tests,
  every cited fact checks out against the record and the conclusion names
  its evidence), `s1.md` (the comprehension key per verb and the three
  design judgments). A drift test pins the rubrics to the design's words.
- `scripts/redesign/s1_cold_engineer.py` and its task table:

  | task | starts from | the counted call | success evidence |
  |---|---|---|---|
  | 1 build with an evaluator | the churn task view (`repo/`, a task README with no Kapso line and no recorded result, the evaluator) | the first execution of `kapso build` / `Kapso.build` | a launch receipt and a status `running`, or a `Solution` returned |
  | 2 build without one | the fraud task view | the same | the same, the evaluation built and approved in the exchange |
  | 3 load a harness and build | the churn task view with `harness/` (the trading example's harness copied in; the bundled directory holds no harness until WP8, so the task says "the harness at ./harness", a deviation from "by name", said) | `kapso build --harness ./harness` / `load_harness` | the status header names the harness |
  | 4 deploy the result | the arm's prerequisite campaign, delivered (built once per arm by the driver, sixty minutes, before the tasks) | `kapso deploy` / `deploy` | a deployment directory with a proved call |
  | 5 learn from it | the same campaign | `kapso learn` / `learn` | the learn launched (a status file) |
  | 6 resume a killed run | a second prerequisite campaign the driver kills at the writer five minutes in | `kapso build --resume` / `build(resume=True)` | the status `running` again with the checkpoint's attempts kept |

  Per task and surface: `first_try` (the counted call's first execution
  succeeds: exit 0 and the evidence), `wrong_calls` (errored executions of
  the counted verb before success; `--help`, `doctor`, reads and searches
  never count), `minutes_to_launch` (from the session's first event to
  the evidence), `error_led_to_fix` (an errored execution followed by the
  next execution of the same verb succeeding), the tool results and exit
  statuses kept. The counts the design names are metrics: the Python flow
  of the six tasks in at most twelve lines, the CLI flow in at most six
  commands (counted from the sessions' executions). The sandbox: a
  plugin-free, server-free host session with no web (proved from the
  session's init event as the isolation step proves it), over a directory
  holding the task view and `docs/` as an allow-listed snapshot (the
  public pages, no `docs/plans`, no `docs/research`); the wheel installed
  into a venv that is the Python the engineer's sessions use, its import
  and the CLI's provenance verified. `--package released`: the released
  wheel 0.7.10 by sha256 and the tag's docs, staged into the harness pack as
  `released-docs/` by semantic.sh (the clone reaches the machine without `.git`),
  its prerequisite campaigns built by 0.7.10's own `evolve` (backgrounded and
  signalled by pid: that package has no `--detach`, stop or `--version`),
  the tasks' goals version-neutral; a verb 0.7.10 lacks is "unsupported",
  counted in the denominator as a miss and said; labelled a retrospective
  baseline, not MASTER's pre-WP1 one.
- `scripts/redesign/s4_reading.py`: a reader (each vendor; Codex advisory
  or blocked as above) given `kapso trace`'s text and the campaign
  directory answers the six questions; the campaign is S5's tampering
  injection's (a void with its hash evidence, a rejection, a partial cost
  coverage), so Q3 and Q4 are not vacuous; the fact sheet is extracted by
  the driver from `solution.json`, the attempts' verdicts, the evaluator
  outputs, the sessions' records, the delivered commit's history (the
  labels check) and the cost's coverage, checked by hand once, kept out of
  the reader's directory, and handed to the judge with `s4.md`. "Not
  established" is a correct answer where the record does not settle it.
  The human reading the design names is a milestone of WP11's release
  checkpoint with the owner.
- `scripts/redesign/s5_injections.py`, six injections on the churn fixture
  with the operating skill on Claude Code in the loop and a scripted user
  (two turns at most: "what happened?" and the fix the skill names), each
  with `inject`, `expect` and the user-message window (from the first
  presentation of the failure to the verified recovery):
  - `provider-limit`: a `PATH` shim before `claude` that passes every
    invocation through except a session turn (`-p` with the stream
    format; `--version`, `auth status` and `doctor`'s calls untouched),
    keeps its count in a file, arms after the status reaches
    `implementation` (a phase barrier the driver watches), and replays a
    recorded real limit N times (stdout, stderr, exit status and the
    stream event copied from a captured 429 of the Claude Code CLI), then
    execs the CLI. Handled means: the run entry says `error` with the
    limit's text, the attempt fails, the campaign goes on or stops
    truthfully, `watch` and `trace` show the class, the skill names it
    and the fix (wait for the window; resume). The engine has no
    rate-limit path of its own: this proves the adapter's handling of
    that failure, not a real limit or a backoff; said in the record.
  - `evaluator-crash`: after attempt one completes, the driver flips a
    marker the evaluator script reads to crash on every invocation; the
    engine's own evaluation of attempt two meets it (the implementer's
    too, which is the point: WP6's one-shot crash was absorbed by the
    implementer and never reached the engine). Expect: the attempt's
    `evaluation.output` carries the crash, the judge's rejection names it,
    the status is truthful, the skill names the evaluator and the fix.
  - `missing-key`: a local service on the machine (`enrichment_service.py`,
    an HTTP server on 127.0.0.1 that answers 401 without
    `Authorization: Bearer <DATA_API_KEY>` and the enrichment table with
    it, logging every request); the task's brief requires the table from
    that service before training; `.env` lacks the key; the session asks
    through the inbox; the driver writes the key, the user says so, the
    reply resumes the campaign with forty minutes and two experiments
    left, and the resumed attempt fetches the table (the service's log
    shows the authorised fetch) and scores. The request names the
    variable, never a value. The task's requirement is never lifted.
  - `killed-session`: an implementation CLI killed mid-run (WP6's case:
    the run entry ends `error`, the attempt fails, the campaign continues
    to its next attempt, automatic recovery, no user needed) and,
    separately, `killed-writer`: the campaign's writer killed with
    SIGKILL after the first checkpoint; `watch` reports DEAD after the
    config's three missed heartbeats, the skill names "dead, not running"
    and the one-flag resume, the resume continues from the checkpoint
    (the attempts kept, the next number continues).
  - `full-disk`: a 64 MB tmpfs mounted at the campaign directory before
    the launch (the campaign initialises in it), filled by the driver
    after the first checkpoint; the status writer's next write fails with
    ENOSPC and, with no `try/except`, the writer dies with the errno in
    the launch's log (the parent directory, outside the tmpfs); `watch`
    reports DEAD within three heartbeats with the log's last line; the
    user frees the filler and resumes with one flag; the checkpoint from
    before the fill is intact. Where the truth lives when the campaign
    directory is full is the log and the receipt; an engine change (the
    writer surviving ENOSPC) is a finding for the observability package.
  - `tampering`: the driver edits the evaluator inside attempt one's
    workspace while the status shows implementation; the engine's
    integrity check voids the attempt with the hash evidence; the trace
    shows it; this campaign is S4's. The hold-out's readability (WP7's
    finding) is stated as the current limit: a read is not prevented, an
    edit is voided.
  With a seeded bank loaded (one card, S6's or a fixture bank), the bank's
  commit before and after each injection is compared: nothing banked is
  lost.
- `scripts/redesign/status_timeline.py`: samples `kapso watch <campaign>
  --json` every `budget.checkpoint_heartbeat_seconds` into
  `timeline.jsonl` (timestamp, state, phase, iteration, best); the common
  elapsed-budget grid for S6 and the "truthful within one heartbeat"
  evidence for S5 (the stored state against the observed liveness, both
  sampled).
- `scripts/redesign/s6_experience.py`: two builds of the churn fixture at
  sixty minutes and three experiments (a tiny budget delivers nothing:
  WP1, WP4, WP6 and WP7 delivered 0.845, 0.847, 0.851 and nothing twice at
  that budget; the spread is recorded with the result), from the same
  seed repository, data, evaluator, config, models and machine type;
  build one with an isolated bank home; the learn of build one must
  complete through mining, the exam and the update crew's commit, banking
  at least one card in a scope the second build is served (`mine:all`),
  pinned by its head; build two served `mine:all` on that head; the
  timelines sampled; the anytime series (the incumbent's score at each
  grid point, missing until the first score) and the gap per point; the
  trace's cards `read`, `load_bearing` and the lessons' `read_by`; the
  review names them. The bar is the design's (a non-negative gap at every
  checkpoint and cited lessons), reported as an observed pair with the
  spread beside it; both builds must have at least one scored
  observation, else the pair is "no observation"; a rerun is a second
  record, both reported, never a choice. The learn's grader roles need
  Codex: the learn runs on the development box over the fetched campaign
  (advisory for smoothness, exact for its product: the bank's commit), and
  the bank reaches the machine for build two as a bare remote the second
  build loads by reference (the second engineer's own path).
- `scripts/redesign/author_test.py`: WP2's author test again (2026-10-25:
  66 and 65 guesses, the guide revised the same day), now on a runnable
  fixture, a different one, so the counts are not comparable and are
  recorded beside WP2's as a second round. A model author (Claude Code;
  Codex advisory or blocked) with `docs/harnesses/write.mdx`,
  `docs/harnesses/index.mdx`, `docs/reference/harness.mdx`,
  `docs/harnesses/example-trading.mdx` and `examples/harnesses/trading`
  writes a harness for `examples/pipeline-dbt`, logging every guess as a
  line (the grammar: `GUESS: <what> | <where it looked> | <what it chose>`);
  the author may not run `check` (WP2's rule); the driver runs `check`; the
  judge classifies each guess as a structural gap (a field, file, key,
  convention or host behaviour the engine or `check` would reject if
  guessed wrong), a contradiction in the guide, a domain decision, or a
  thing the guide already says, and reviews the harness against the
  guide's rules. One cold author per run, on the guide as committed (the
  record pins the guide's hash): the structural gaps and contradictions a
  run logs are fixed in the guide (this package owns those pages for that)
  and committed, and the next run's fresh author is the design's round
  two. The bar is zero structural gaps and a green `check`; both runs'
  counts are recorded beside each other.
- `scripts/redesign/semantic.sh <s1|s2|s4|s5|s6|author> <host> [--machine
  <id>] [--advisory]`: preflights every role's route (the host CLI's
  login, the persona's vendor, the judge's route, the Codex key's credit
  with one small call), provisions the machine with the test's
  `KAPSO_FRESH_MAX_RUN`, installs the wheel built from the branch and the
  fixtures' dependency venv first on PATH (numpy, pandas, scikit-learn,
  duckdb, dbt-core, dbt-duckdb at the examples' pins), keeps the CLI
  versions in the install log, runs the test under an immutable run id, archives (below),
  verifies the archive is fetched, deletes the machine, judges on the
  development box, renders the report under `tests/semantic/reports/`;
  `--advisory` runs on the development box under a fresh Linux user with
  nothing of the checkout and marks the record.
- **The archive** per run under `scripts/redesign/runs/wp9/<run_id>/`: the
  record, both sides' raw transcripts, the tool results, the pins, the
  effective config, the fixture manifests, the role prompts and settings,
  the injection timestamps, the checkpoints, the campaign directories as
  one archive each, the delivered commit's history, the deployment proofs,
  the learn's mining, exam and update outputs, the bank heads, the serving
  records and pull logs, the judge's prompt, raw replies and extracted
  facts, the verdict; failed runs kept; the report cites the run id.
- `examples/pipeline-dbt`: built (change 9): three seeded exports with
  their defects, a dbt project on DuckDB, an evaluator that builds the
  project with its own profile into a DuckDB file under the protected
  directory and runs thirteen assertions with DuckDB directly (the
  project's own tests are the engineer's), the metric as the last line,
  `result.json` in the engine's shape, exit 2 with dbt's last lines when
  the project does not build, exit 3 without a project, `--fast` the
  staging layer alone and marked, four seconds a cycle, the shipped
  project 2 of 13 (0.1538), `baseline.json`, `run.py`, the versions
  pinned, a contract test that skips without `dbt` on PATH.

**Consumed.** `scripts/redesign/fresh_machine.sh` and the installer (WP0,
extended in WP7); `plugin_proof.py`'s hosts, steps and policies (WP7);
`kapso trace --json`, `kapso watch --json`, the receipt, the status
writer's three-heartbeat rule (WP6); `kapso learn`, the bank's serving, the
pull log, the share and the load by reference (WP3); the examples and
their generators (WP1, WP10); `Solution.open`, the facade's `on_status`
(WP1); `load_config` for `budget.checkpoint_heartbeat_seconds` (WP4); the
authoring guide (WP2); LiteLLM for the judge's route.

## Ownership

Edits: `tests/semantic/` (the README, `suite.json`, the personas, the
rubrics, the reports it cites, `report.py`, the re-derivation of WP7's
records), `scripts/redesign/` (the new drivers, `plugin_proof.py`,
`semantic.sh`, the installer's venv, `README.md`), `examples/pipeline-dbt/`
(built) and `examples/README.md` (its row), `src/kapso/learning/mining.py`,
`src/kapso/learning/crews/mining/mined_format.md` and
`src/kapso/learning/graders/frame.py` (change 1, built), the authoring
guide pages `docs/harnesses/write.mdx`, `docs/harnesses/index.mdx`,
`docs/reference/harness.mdx` (the author test's fixes, WP10's slice),
`docs/plans/redesign/` (this file, DECISIONS, MASTER's row), and under the
bounded exception of the Scope, a sentence in `plugin/skills/*/SKILL.md`,
`plugin/commands/*.md`, `plugin/evals/**`, `docs/**.mdx`.

Reads, never edits: every other file under `src/kapso/**` (a finding
here, a fix there), `examples/churn-first-build`, `examples/fraud-no-
evaluator`, `examples/trading` (the fixtures as they are; a generator fix
is WP10's).

## Changes

1. **The learn completes on the two cases the plugin round found**
   (built: `d47187a2`). The mined-view validator names a frontmatter line
   whose unquoted reference carries a colon in its fragment as a finding
   for the repair round, and the crew's format document says to quote it;
   the general case (any document that does not parse) is not
   implementable without the `try/except` CLAUDE.md forbids, so the next
   unparsable shape still ends a learn, with the file and the line named
   and the mined view regenerable. The exam frame's role runner already
   retried a session once; it now fails loud with what each session said,
   which hid the round's real cause: the grader roles run on Codex and the
   machine's Codex key has no credit. Tests on both. The acceptance is a
   measured learn: WP7's archived churn campaign mined and examined to at
   least one banked card, on the development box (the Codex credit), and
   on the machine when the credit exists.
2. **The suite's one home and the record's second shape.** `suite.json`;
   `report.py` for the kinds, the metric bars, the judge's two passes, the
   pins, the advisory flag and the verdict; `budgets.json` deleted; the
   WP7 records re-derived and re-rendered. Tests: the verdict's every
   clause on built records (a deferred required step fails; a judge
   failure fails; an unjudged run where a judge is required fails; an
   advisory arm cannot be a fresh-machine acceptance); every driver's step
   names in `suite.json`; the knobs read from one place.
3. **The persona driver.** `simulated_user.py`, the three new cards, the
   prompt template with its sha256. Tests: the prompt carries the card,
   the task view's README, the whole history and the host's message, never
   clipped (Rule 6); `DONE` alone is `done`, `DONE` inside a sentence is
   not; a non-zero exit, a timeout and an empty reply raise; the patience
   count reaches the prompt; the vendor is the other one, by host.
4. **The plugin round with the persona.** `plugin_proof.py --user`, the
   loop offering every turn, the turn cap as an explicit incomplete, the
   interventions recorded, the per-step intents, the pushback check, the
   second engineer's served build as the ninth step, `learn` and
   `harness improve` and `experience share` no longer deferred on Codex
   (advisory there until the credit), the fraud evaluator contract-tested
   (the fixture contract test run on the session's evaluator), the deploy
   step's parity check (the deployed call's answer against the evaluated
   solution's on a sample), the harness interview's silent modules
   resolved (the persona asks or the pages are written). Tests: the policy
   adapter from real archived transcripts (WP7's), the predicates on real
   artifacts, the interventions' shape.
5. **The judge.** `judge.py`, the three rubrics, the route's preflight, the
   JSON contract, the quote-at-location rule, two passes and adjudication,
   the unjudged outcome. Tests: the rubrics are the design's words (drift);
   the contract (a malformed reply, a wrong dimension set, a score out of
   range, a quote not at its location each a judge failure with the raw
   reply kept); the rendering of a step from a real archived transcript;
   the aggregation (the minimum binds; straddling adjudicated).
6. **S1.** `s1_cold_engineer.py`, the task table, the sandbox's proof, the
   predicates, the counts, `--package released`. Tests: each predicate on
   archived shapes (a receipt, a deployment, a resumed status), the
   `wrong_calls` rule on a real stream with a `--help` and an error, the
   one-step rule, the line and command counts.
7. **S4.** `s4_reading.py`, `s4.md`, the fact sheet's extraction. Tests:
   the extraction on WP7's archived campaign and on a campaign with a void
   (a built record), the "not established" answer.
8. **S5.** `s5_injections.py`, the shim, the service, the tmpfs mount, the
   six `expect`s, `status_timeline.py`. Tests: the shim passes through and
   counts (a real local subprocess), the service's 401 and 200, each
   `expect` on a built status history and inbox, the user-message window,
   the bank compare.
9. **S6.** `s6_experience.py`. Tests: the anytime series and the gap from
   two timelines on a common grid, missing observations, the served and
   used cards from a real trace, the review's naming.
10. **The dbt fixture** (built: `2c19d9d9`, `83fdc7f1`).
11. **The author test.** `author_test.py`, the guess grammar, the
    classification rubric, the two-round flow, the guide's fixes. Tests:
    the log's parsing, the classification's shape, the rubric's drift.
12. **The runner, the installer's venv, the archive, the README.**
13. **The runs.** The learn on WP7's archive (change 1's acceptance); S2
    proper advisory on the development box for both hosts and on the fresh
    machine for Claude Code with the persona on Codex only when the credit
    exists; S1 on the fresh machine for Claude Code (two packages), the
    Codex arm when the credit exists; S5 on the fresh machine; S6 with its
    learn on the development box; S4 on S5's tampering campaign; the author
    test, two rounds; each archived and recorded below with its report
    cited; the findings for the packages; MASTER's row.

## Tests

- Syntactic: `tests/test_learning_repairs.py` (built), `tests/test_
  examples_pipeline_dbt.py` (built), `tests/test_semantic_suite.py` (the
  suite's one home, the verdict, the re-derivation), `tests/test_simulated_
  user.py`, `tests/test_judge.py`, `tests/test_s1_cold_engineer.py`,
  `tests/test_s4_reading.py`, `tests/test_s5_injections.py`, `tests/test_
  s6_experience.py`, `tests/test_author_test.py`, `tests/test_semantic_
  report.py` extended. The fixtures the predicates run on are archived
  WP6 and WP7 transcripts and records, not hand-written shapes. Every
  provider boundary mocked; every test asserts a shape a driver produces,
  a fail-loud path, or a contract the design pins; a test that only
  passes a mock through is not written.
- Proof run: each test's run as change 13 says, archived under its run id,
  its report under `tests/semantic/reports/`.
- Semantic hooks: this package is the hooks. The numbers recorded in the
  Proof run section: S1's twelve attempts per package and host with the
  two counts, S2's budgets and the five scores per host with the
  advisory flag, S4's twelve verdicts, S5's six classes with their
  message counts, S6's gap per grid point with the spread, the author
  test's two rounds' counts beside WP2's.

## Hours and spend

| test | machine hours | `KAPSO_FRESH_MAX_RUN` | model spend (Claude, recorded) | Codex | development box |
|---|---|---|---|---|---|
| the learn on WP7's archive | none | | the mining lead on opus (`--learn-model`, the Fable window) | the graders | yes, advisory for smoothness |
| S1, one package, Claude Code | two prerequisite builds of an hour, twelve attempts, about four hours | 6h | about $20 | blocked | the Codex arm, advisory |
| S2, Claude Code host | about three and a half hours | 6h | about $30 with the persona | the persona: blocked | both arms, advisory |
| S4 | the readings, under an hour, on S5's machine | | about $5 | the reader: blocked | |
| S5 | six injections, about four hours; run as two arms of three | 6h | about $25 | | |
| S6 | two builds of an hour and the bank's transfer, about three hours | 6h | about $20 | the learn's graders | the learn |
| the author test | two rounds, about an hour | 3h | about $10 | the author: blocked | |

The Claude token's weekly windows are read before each run (the token
rule): the Fable window is spent until 2026-10-30 14:00 UTC, so the
learning crews run on opus by `--learn-model`, said in each record. Codex
dollars on the development box are the owner's ChatGPT plan, not metered;
on the machine the key's credit, when it exists.

**As run (2026-10-27 to 29), the machine hours the launch logs recorded
at $0.134 per hour; the caps are now derived from the suite (see
`machine_hours`).** The runs this document cites, with the re-runs that
re-measured a row:

| test | runs | machine hours | about |
|---|---|---|---|
| S1 (the new stack) | `s1-claude-1` | 5.72 | $0.77 |
| S1 (the released baseline) | `s1-released-2` | 3.92 | $0.53 |
| S2, Claude host | `s2-claude-1` 2.68, `s2-claude-2` 6.00 (lost at the cap), `s2-claude-3` 3.79; the targeted arms (inbox ×5, review ×2, propose, data-only) 5.69 | 18.2 | $2.44 |
| S2, Codex host | `s2-codex-1` (fetched, no report), `s2-codex-4` 2.46 (stopped), `s2-codex-5` 4.31; the inbox arms 0.57; `s2-codex-triggers-1` 0.93 | 8.3 and the first run | about $1.20 |
| S4 | `s4-claude-1` | 0.12 | $0.02 |
| S5 | arms 1 to 4 (stopped early), `s5-claude-5` 1.21, `s5-claude-6` 2.72, `s5-claude-7` 4.14 | 8.1 and the first four | about $1.20 |
| S6 | rounds 1 to 4 (stopped), `s6-claude-5` 2.97, `s6-codex-1` 2.95 | 5.9 and the rest | about $0.80 |
| the author test | six rounds of about ten minutes | 1.0 | $0.14 |

Model spend: the Claude Max tokens' windows, read before each launch and
never metered in dollars; one learn on Opus 5.5 (`s6-claude-5`'s lesson
crew) reported $15.28 for 88 minutes and 204 tool calls, and a churn
campaign on the Claude host reports $4 to $6 per hour of sessions.

## Acceptance

- The learn of WP7's archived churn campaign completes through mining,
  the exam and the update crew's commit, banking at least one card (on the
  development box; on the machine when the credit exists), and the two
  repairs are pinned by tests.
- S1 on the branch's package, Claude Code, fresh machine: at least nine
  of the twelve attempts succeed first try; every error leads to its fix
  in one step; the comprehension key correct on every verb; the Python
  flow in twelve lines, the CLI flow in six commands; no judge finding of
  a surprising name. The retrospective baseline on 0.7.10 recorded beside
  it with its unsupported verbs said.
- S2 with the persona: every budget and every required step on both
  hosts; every dimension at 4 or above in both passes, straddles
  adjudicated; the second engineer's served build scored; the deployed
  call's parity; the fresh-machine arm for Claude Code when the persona's
  Codex credit exists, the advisory arms otherwise, each marked.
- S4: the six questions answered correctly by both readers from the
  record alone, on a campaign with a void and a rejection.
- S5: each of the six classes handled with at most two user messages;
  the stored state and the observed liveness truthful within one
  heartbeat on the sampled timeline; no value in a request; the resumed
  campaign continues from its checkpoint; nothing banked lost.
- S6: the pair reported on the common grid with the spread; the served
  cards read and cited in the trace and named by the review; the gap
  non-negative at every point where both observed, or the pair reported
  as the design's bar unmet with the numbers.
- The author test's run after the guide's fixes: `check` green, zero
  structural gaps, the fixes committed; both runs' counts recorded beside
  WP2's.
- `semantic.sh` runs each test from one line, preflights the routes,
  archives and verifies before deleting, renders a report with the
  verdict the runner's exit status carries; the reports cited here are
  committed under immutable ids.
- The gate is green; the docs checks pass; MASTER's row written, its
  size corrected.

**Status against these lines (2026-10-29, from the records under "Proof
run"):**

- **The learn of WP7's archive: met.** The development-box learn banked
  twelve cards (four insights, eight procedures) with the Codex grader
  crew, and the two repairs are pinned in `tests/test_learning_repairs.py`;
  on the machines, the learns of S6 and S2 completed on both hosts with
  two cards each, the Codex roles on the device-auth session that stands
  in for the credit.
- **S1: met, one bar unmet by decision.** `s1-claude-1`, re-read under
  the package's own verbs and true invocations (2026-10-29): first try 9
  of 12 against 9, the one errored call fixed in one step, the
  comprehension key 7 of 7, the CLI flow in 2 commands, the judge's names
  and docs dimensions passing over the answers and the flows; the Python
  flow 16 lines against 12, the judge's lengths dimension failing on the
  same cause, kept as a finding and not a loosened bar (DECISIONS
  2026-10-27). The released baseline `s1-released-2` beside it, re-read
  the same way: first try 6 of 12 (not the 1 first written), two errored
  calls neither fixed in one step, comprehension 0 of 7, a 30-line flow,
  its unsupported verbs said in the engineer's own words.
- **S2: met with caveats, three of them the owner's call.** Every
  required step is true on a clean run of its host (`s2-claude-3` 19 of
  25, `s2-codex-5` 17 of 24, the targeted arms for the rows those left
  false), each false row traced in the record to a fix, a finding or a
  calibration. The caveats: the Claude host's build and review
  conversations run 13 to 20 lines against the 12-line budget, the
  skill's prescribed message against the design's budget (DECISIONS
  2026-10-28, the owner's call); the judge's clear and not-annoying
  dimensions pass at 4 on both hosts while proactive, engaging and return
  on attention fail on the worst item (the deploy conversation with
  nothing to deploy on the Claude host; the right, terse answers on the
  Codex host), a finding on the Codex host's skill wording and the owner's
  call on whether terseness binds; the deployed call's parity "differs" on
  both hosts where a delivery existed, the delivery re-fitting at load
  (WP5's call); the learn-complete step outrun on the Codex host
  (DECISIONS 2026-10-28); the second engineer's served build died at the
  engine's preflight on the clean run for want of a Codex login, a
  finding, and is re-measured by `s2-claude-second-1`, running at this
  writing. The fresh-machine arms ran on both hosts, marked in each record
  as running the Codex roles on the device-auth session rather than the
  persona's own credit.
- **S4: met on the readings, half met on the campaign.** `s4-claude-1`:
  both readers 6 of 6 in both passes, once the fact sheet filed a void by
  the engine's own semantics; the campaign held the integrity void and no
  judge rejection (the report's `campaign_has_rejection` bar reads FAIL),
  and no archived campaign holds both — the Codex reader's coldness is
  reported as not established, the machine being fresh.
- **S5: met.** Across `s5-claude-5` to `s5-claude-7` every one of the six
  classes was handled as designed with at most two user messages, the
  shown state truthful within a heartbeat on every sampled timeline, the
  one request naming its variable and never a value, the resumed campaigns
  continuing from their checkpoints, the seeded bank intact after every
  injection; the clean arm met every bar, its one false row the
  engineer's slip on a class arm 6 had passed.
- **S6: met in the acceptance's second form.** `s6-claude-5` on the Claude
  host: the pair on the common grid with the spread, the cards read,
  load-bearing and named by the review, the gap vacuous at one scored
  observation each and said so; `s6-codex-1` on the Codex host with the
  grid fix: a real grid, both cards read and load-bearing, the gap −0.0004
  at every common point, the bar reported unmet with the numbers.
- **The author test: met.** `author-claude-4` and `author-codex-2` on the
  guide after four rounds of fixes: `check` green, zero structural gaps,
  zero contradictions, the four judge dimensions passing, the fixes
  committed; every round's counts in the record beside WP2's.
- **`semantic.sh`: met.** Each test runs from one line, the routes
  preflighted, the archive fetched and verified before the machine's
  deletion, the report rendered with the verdict the runner's exit
  carries; every report cited here is committed under its immutable id.
- **The gate, the docs checks, MASTER's row: met.** 1967 passed on the
  full gate (two live Codex tests deselected, as CI does);
  `check_docs_coverage.py` and `check_docs_geo.py` green on the branch;
  MASTER's WP9 row written, its size L.

## Risks

- **The Codex login is the owner's device-auth session.** Every Codex role
  on a fresh machine runs on a copy of the owner's personal ChatGPT login
  (the API key has no credit): the copy sits on a throwaway VM and in a
  second Unix user's home for the served build, and a token refresh by
  any copy can revoke the others. The mitigation is the runner's: the
  session is re-logged before a wave, verified by a one-token call in the
  preflight, and never pushed through a command line (ssh stdin only);
  the machines are deleted after the fetch.
- **The persona's variance and its blind spots.** A model user is never
  bored and says "go" too readily; the pushback check planted in the task
  view tells a persona that reads from one that nods, and the arm is
  advisory for two dimensions when it nods. Two runs differ; a rerun is a
  second record, both reported.
- **The judge's route.** Gemini on Vertex from the development box; its
  preflight runs before any machine; without it the run is unjudged and
  acceptance blocked, never a same-vendor judge.
- **The learn's residual case.** An unparsable shape other than the
  colon's still ends a learn, with the file and line named; the mined
  view is regenerable. The general repair needs `try/except`.
- **S6 at one pair.** The gap at sixty minutes is dominated by whether an
  attempt landed; the result is an observed pair with the spread, and the
  claim it supports is that the served cards were read and cited.
- **The injections' fidelity.** The provider limit is a replayed failure,
  not a limit; the full disk kills the writer by design (no `try/except`),
  and the truth lives in the log and the receipt; said in the records.
- **Hours against the machine's lifetime.** Each test's `KAPSO_FRESH_
  MAX_RUN` is set above its hours; the archive is verified fetched
  before the deletion.
- **The token windows.** The Fable window is spent until 2026-10-30; the
  crews run on opus by the recorded accommodation; a window reached
  mid-run ends the run as a recorded failure, rerun after the reset.

## Review

The sub-plan's cross-model review (`scripts/redesign/review.sh`, the brief
in `scripts/redesign/runs/wp9-plan-review/brief.md`, Codex `gpt-6-astra`
at xhigh and Claude `claude-opus-5`, 2026-10-27): sixty-three findings,
answered by this second version, each row naming where.

### Codex

| # | finding | answer |
|---|---|---|
| 1 | P1: the report is not a semantic gate | fixed: `suite.json` names each test's required steps and bars; the verdict (Interface) requires them, the judge's bar, no deferral of a required step, no judge failure; the runner's exit carries it |
| 2 | P1: replacing answer policies does not complete S2 | fixed: change 4 lists the nine steps' artifact-backed predicates, the deferrals lifted (advisory on Codex until the credit), the second engineer's served build, the deploy parity check, the fraud evaluator's contract test, the silent modules resolved |
| 3 | P1: the conversation can stop before the persona participates; first-line replies clip | fixed: every host turn is offered; `DONE` alone ends; the whole reply is the message (Rule 6); the turn cap is an explicit incomplete; satisfaction and completion recorded apart |
| 4 | P2: the persona needs a behavioural and reproducibility contract | fixed: the prompt's inputs and exclusions, the mechanical patience count, the pins in `user` and `pins`, the interventions named, a rerun as a second record never a selection, the pushback check |
| 5 | P1: the fallback vendor does not exist | fixed: the route preflighted before any machine; without it the run is unjudged and acceptance blocked; the provider and the route recorded apart |
| 6 | P2: valid JSON and real quotations are insufficient | fixed: exact dimensions, integer range, evidence at a location, judge failure kept apart from product failure, the raw reply kept, neither a pass; the rubrics the design's words, drift-tested |
| 7 | P1: S1's six tasks lack executable prerequisites | fixed: the task table with its prerequisite campaigns built by the driver per arm; the harness task on a path with the deviation said (the bundled directory is empty until WP8) |
| 8 | P1: a fresh session is not a cold sandbox | fixed: plugin-free, server-free, no web, proved from the init event; the docs snapshot allow-listed; the task view without Kapso lines; the wheel in the engineer's own venv, import and CLI verified |
| 9 | P2: the released baseline needs an immutable definition | fixed: 0.7.10 by sha256 and the tag's docs; version-neutral goals; unsupported verbs counted and said; labelled retrospective |
| 10 | P1: "first try" and the brevity tests undefined | fixed: the counted call, `wrong_calls` on the counted verb only, the one-step rule, the launch timestamp, the two counts as metrics, the three design judgments in `s1.md` |
| 11 | P1: S4's answer key is partly circular | fixed: the fact sheet extracted from the record's files and checked once, hidden from the readers; S5's tampering campaign with a void and a rejection; "not established" allowed; the human reading a WP11 milestone |
| 12 | P1: the provider-limit shim's injection point unspecified | fixed: the shim passes everything but a session turn through, arms after a phase barrier, replays a captured real failure (stdout, stderr, exit, event), and what "handled" means is written; a fault injection, said |
| 13 | P1: evaluator crash and killed session repeat WP6's gap | fixed: the crash on every invocation from attempt two so the engine's evaluation meets it; the killed implementation CLI (automatic recovery) and the killed writer (the user's one-flag resume from the checkpoint) as two cases |
| 14 | P1: the missing-key recovery lifts the task | fixed: the local enrichment service with the key, the requirement kept, forty minutes and two experiments reserved, the resumed attempt's authorised fetch in the service's log |
| 15 | P1: the full disk kills what the test reads | fixed: the tmpfs mounted before the launch and filled after a checkpoint; the truth in the log and the receipt; `watch` DEAD within three heartbeats; free and resume; the writer surviving ENOSPC routed to the observability package |
| 16 | P2: message counts and preservation can pass vacuously | fixed: the user-message window defined; the classes with no request named; a seeded bank compared by commit; the tampering case added with the hold-out limit stated |
| 17 | P1: S6's measurement unspecified | fixed: `status_timeline.py` at the config's cadence, a common grid, the incumbent, missing observations, scored observations required, the pins, the pair reported with the spread |
| 18 | P1: a learn between them does not guarantee experience | fixed: the learn through mining, exam and the update commit, at least one card in a served scope, the head pinned, read and load-bearing in the trace, named by the review, the same seed for both builds |
| 19 | P1: the learning repair misdescribed and beyond its files | fixed: change 1 describes what was built, its residual, the crew document in Ownership, and the real cause (the Codex credit) |
| 20 | P2: the dbt evaluator contract unfinished | fixed in the build: thirteen assertions in the protected evaluator, one formula, exits 2 and 3 with reasons, `--fast` marked, four seconds, `run.py`, the pins, the manifest and the baseline |
| 21 | P1: the guide's repair required but not owned | fixed: the three authoring pages owned for the author test's fixes; the test named as WP2's second round |
| 22 | P2: zero self-reported guesses is not completeness | fixed: the structural gap defined against a domain decision, the judge classifies, two rounds, the author may not run `check`, the counts recorded beside WP2's |
| 23 | P1: the development-box exception defeats the isolation | fixed: the preflight of every route; the advisory flag on every development-box arm; fresh-machine arms needing Codex reported incomplete until the credit; the owner's action named |
| 24 | P2: the schedule is not budgeted | fixed: the Hours and spend table with `KAPSO_FRESH_MAX_RUN` per test, the venv, the CLI versions recorded, a fresh user per advisory run |
| 25 | P2: a record file cannot reproduce the judgment | fixed: the archive list, immutable run ids, failed runs kept, the fetch verified before deletion |
| 26 | P2: configuration ownership and meaningful tests | fixed: `suite.json` the one home (the cadence from the engine config); the tests named by what they pin, the mock-only ones not written |
| 27 | P3: the run matrix and cadence implicit | fixed: change 13 and the Hours table name the runs; the cadence after a skill, page, help or public-doc change stays the design's and is restated in the README; the human S4 reading a WP11 milestone; S6 without WP8 as the churn pair |

### Claude Code

| # | finding | answer |
|---|---|---|
| 1 | P1: the second fail-loud case is not fixed; the real cause is the Codex quota | fixed in the plan: change 1 names the cause and what was built; the acceptance is a measured learn banking a card; the grader roles' models stay the owner's (no swap) |
| 2 | P1: the evaluator crash reuses WP6's wrong shape | fixed: the crash on every invocation from attempt two; the expect on the attempt's evaluation output and the rejection |
| 3 | P1: S5's acceptance needs a host in the loop | fixed: the operating skill on Claude Code with a scripted user of at most two turns; a user message is one user turn |
| 4 | P1: the persona cannot carry three steps | fixed: per-step intents and interventions; the `trading-author` card holds the module answers; the inbox act stays the driver's and is named; the criteria personas want no launch |
| 5 | P1: the example README leaks the answers | fixed: the task view without Kapso lines or recorded results for S1 and the persona; the example README stays for readers |
| 6 | P1: S1's tasks 4 to 6 need campaigns | fixed: the prerequisite campaigns per arm in the task table and the hours |
| 7 | P1: the Codex quota contaminates every arm | fixed: the owner's action; advisory arms marked; fresh-machine arms incomplete until the credit |
| 8 | P1: WP7's nine deferrals | fixed: the "what WP7 deferred here" list in the Scope |
| 9 | P1: the record shape does not fit the new tests | fixed: the second shape with `kind` and `metrics`, the judge sub-record, `suite.json`, the verdict computed, WP7's records re-derived |
| 10 | P1: the author test's bar and definition | fixed: WP2's second round, the structural gap defined, two rounds, the author may not run `check`, the counts not comparable and said |
| 11 | P2: S4 needs a void and a rejection | fixed: S5's tampering campaign |
| 12 | P2: Q2 and Q6 have no ground truth | fixed: scored on every cited fact checking out and the conclusion naming its evidence |
| 13 | P2: `first_try` undefined | fixed: the counted call and the rules |
| 14 | P2: the sandbox not enforced | fixed: proved from the init event, no web, the snapshot |
| 15 | P2: the released docs are not in this tree | fixed: the tag's docs, staged into the pack by semantic.sh, pinned |
| 16 | P2: the comprehension key and the counts | fixed: in `s1.md` and the metrics |
| 17 | P2: no status history | fixed: the sampled timeline at the config's cadence |
| 18 | P2: S6 at one pair | fixed: sixty minutes, the spread recorded, the learn's output requirements, the claim stated |
| 19 | P2: the shim and the preflight | fixed: pass-through of everything but a session turn; "handled" defined |
| 20 | P2: the full disk kills the writer | fixed: the truth in the log and the receipt; the tmpfs filled after a checkpoint; the engine change routed |
| 21 | P2: the judge on the machine | fixed: a standalone pass on the development box over the fetched record; one JSON object, a fence allowed |
| 22 | P2: the judge's input | fixed: the rendered conversation per step, one call per step, the minimum binds |
| 23 | P2: the fallback vendor | fixed: unjudged with the hard metrics standing, acceptance blocked |
| 24 | P2: a single judge pass | fixed: two blind passes, a third adjudicating a straddle |
| 25 | P2: `None` hides a user-side failure; the pins | fixed: a failure raises; `done` only on `DONE` alone; the pins in `user` and `pins` |
| 26 | P2: the persona never bored, says go | fixed: the planted pushback check; the arm advisory for two dimensions when it nods |
| 27 | P2: the mining repair's general form | fixed: said as built, with the residual |
| 28 | P2: the installer lacks the fixtures' dependencies | fixed: the venv first on PATH at the examples' pins |
| 29 | P2: hours, dollars, the machine's lifetime | fixed: the Hours and spend table |
| 30 | P2: which tests earn their place | fixed: the Tests section names them; the fixtures from archived transcripts; the step names checked against `suite.json` |
| 31 | P2: scope versus ownership | fixed: the exception bounded to a sentence in the named files, never engine code |
| 32 | P2: the judge's prompt and raw reply | fixed: in the archive |
| 33 | P3: the README parameter | fixed: `task_dir`, the task view's README read from it |
| 34 | P3: the data-engineer card's role | fixed: the author test's reader, not an S1 arm |
| 35 | P3: size L versus M | fixed: L, MASTER's row corrected at merge |
| 36 | P3: the knobs' home | fixed: `suite.json` |

## Flow review (post-build, cross-model)

After the drivers were built, a second cross-model review read the whole
user flow and the metrics against the engine's real contracts (the brief
in `scripts/redesign/runs/wp9-flow-review/brief.md`, Codex `gpt-6-astra`
at xhigh and Claude `claude-opus-5`, 2026-10-27; their findings in
`codex.md` and `claude.md` beside it). The two converged: as built, the
suite would have crashed on the first step of several arms, recorded false
metrics on others, and the runner would have deleted machines before
verifying the archive. The findings are answered below, grouped by the
commit that closed them; the two reviews overlap, so each row cites the
substantive fix.

| area | finding (both reviews) | answer | commit |
|---|---|---|---|
| runner | the exit status did not carry the verdict; the archive was fetched to one directory and verified in another, after the delete; the wheel path carried the build log; the scaffold omitted the plugin and `docs.json`; the drivers were not given the wheel; the preflight gated nothing; the `author` run cap used the wrong key; the advisory user could not authenticate | the report's exit is the runner's; the archive is moved under the run and the record verified before the delete; the wheel path is clean; the scaffold ships the plugin, its manifest and `docs.json`; one env holds the wheel and the fixtures' deps; the preflight makes a real call per route and the Codex credit call and stops on failure; the lowercase `author` key; the advisory user gets the wheel, the deps and a token | `e1d45ef6` |
| judge | a top score with no evidence passed; a citation could name any file; a malformed reply left a stale block (JSON errors escaped the typed failure); follow-up turns went unjudged; a missing transcript was silently dropped; one adjudicated item could hide another's disagreement; the pass count was hard-coded | evidence is non-empty and must quote the material's own file; a pending non-passing block is written first; a conversation step is judged with all its transcripts and a missing one raises; each straddling item is adjudicated and the worst binds; the pass count reads the suite; the s2 line cap reads the step's budget | `e1d45ef6` |
| S1 | the Codex arm recorded 0/12; comprehension had no producer and the S1 judge nothing to judge; the one-step metric accepted many errors; `wrong_calls` was ungated; prerequisites leaked between surfaces; the learn status was sought in the wrong directory; flow counts conflated a reused filename; a missing init was a silent pass | executions read both hosts; `--grade` fills comprehension_correct from the judge; the one-step metric is exactly one wrong call, gated by `wrong_calls_max`; prerequisites are snapshotted and restored per surface; the status dir is globbed from the cwd; flow counts are per task; a Codex session's coldness is reported, not passed | `851ba1d1` |
| S4 | "what was rejected" listed the scored losers; the leak check grepped one path with `--all`; the grade ignored adjudication | a rejection is a voided entry split by reason, the losers reported apart; the leak check reads the delivered commit's ancestry by filename and the private path; the grade resolves each question as the verdict does | `6cd5d3af` |
| S5 | the timeline measured `/proc`, not `watch`; every launch named a missing config; evaluator-crash and tampering edited the wrong tree and could not reach the engine; "handled" was a loose substring and the fix was never gated; the user-message bar was a tautology; the resumed fetch/score was not correlated; the bank compare treated a bare repo as unreadable-but-intact; the full-disk campaign was discarded before archival; the enrichment table missed the hold-out ids | the timeline samples what `watch` shows; the launch uses packaged defaults; the labels moved are the ones the evaluator reads by absolute path, the tampering edits the running session clone and the void must be the integrity one; each injection gates on the fix; the fetch and score must follow the reply; the bare bank is read with git and an unreadable comparison fails; the campaign is copied off and verified before unmount; the table covers the fixture's hold-out range | `8c80fdee` |
| S6 | the bank home used a rejected config key; the gap dropped build-one-only intervals and was a hard bar on a noisy quantity; cited counted mere reading; the delivered score read a nonexistent field | the key is `learning.bank.local_path`; the gap uses a common horizon with behind-intervals counted, and `gap_min` is reported, not gated; cited means load-bearing; the delivered score resolves to its attempt | `be16d406` |
| S2 / persona | the turn cap was not a failure; one card drove every step; a refused persona read as satisfied; harness-export crashed on a missing README; deploy passed when predictions differed; review/watch/criteria/session-brief/second-engineer completions were not evidence; the inbox removed the requirement; a failed launch earned completion; the evaluator contract accepted anything; host models and budgets were hard-coded | the turn cap makes a step incomplete; a per-step card answers the interview and the served build; a refused persona raises; the README is optional; deploy requires parity "same"; the completions require the real evidence (the branch named, the state reflected, no new campaign, a succeeded bank tool, a scored served build); the inbox requires a continued event; a launch must reach running with a proposal; the contract requires a finite score and rejects a malformed submission; the knobs move to `suite.json` | `2c140296` |

Two findings are answered as scoped decisions rather than full rebuilds,
recorded in `DECISIONS.md`: the second engineer's build stays
driver-launched (now gated on a scored, served delivery) rather than
driven through the teammate's own persona and host; and S1's flow count
reads a script in its final state, a stated limit when one filename is
reused within a task.

## Pull-request review (cross-model, 2026-10-29)

The pull request's cross-model review (`scripts/redesign/review.sh`, the
brief in `scripts/redesign/runs/wp9-pr-review/brief.md`, Codex
`gpt-6-astra` at xhigh and Claude `claude-opus-5`): fifty-nine findings
— Codex twenty-two (eight P1, fourteen P2), Claude thirty-seven (five P1,
twenty-one P2, eleven P3) — each fixed on the branch or answered here.
Three of them changed what this document had claimed: the S1 headline
(a detector artifact: nine against six, not ten against one), the S6
round recorded as the Codex host's (it had run on Claude Code), and the
Codex trigger miss (the machine's sandbox, not the host). The re-derived
records and the reruns they called for are in the Proof run below.

### Codex

| # | finding | answer |
|---|---|---|
| 1 | P1: the trigger failure is misattributed to skill discovery | fixed: 153 of the 356 main runs and all 10 holdout runs said `bwrap: loopback: Failed RTM_NEWADDR`; the runner probes the sandbox once, classifies such a run as the machine's failure (`codex_triggers.sandbox_failure`), counts it apart in the bar (not established, never a miss), re-graded `s2-codex-5` (7 of 89 cases established), rewrote the finding, and re-ran the suite unsandboxed by its own word (`s2-codex-triggers-1`) |
| 2 | P1: S1's first-try count scans searches and misses the released verbs | fixed: the verb table is per package (0.7.10's `evolve`); an execution is a segment that invokes kapso or runs a script with python (`command_segments`, `invocations`, `counted`); both arms re-graded from their archives — nine against six — and the headline corrected here and in MASTER. The comprehension key is the design's question (does the tool teach these names?); the baseline's 0 of 7 against it is reported as such |
| 3 | P1: the second engineer's score predicate reads a key the product never writes | fixed: the solution record's own `score`; the second user's campaign log and status archived; `s2-claude-second-1` had run on the broken key (its served build launched with the bank's two cards and no status appeared within a ten-minute budget); the budget raised to one an attempt can score in (DECISIONS) and the arm re-run as `s2-claude-second-2` |
| 4 | P1: the judge receives the exchange out of order, the persona's reply twice | fixed: follow-ups sort after their step by number, the reply is rendered once, an unsent reply is marked, DONE reads as the user satisfied; the S2 runs re-judged |
| 5 | P1: unobserved S5 injections leave the denominator | fixed: the shown verdict is held against the observed liveness sample by sample (WAITING truthful), an injection with no sample in the judged window is counted unobserved and the bar wants none; the three records re-derived (the partial arms had one each); `s5-claude-8` re-run under the rule |
| 6 | P1: the checkpoint-retention proof is vacuous | fixed in part: retention compares the attempts' identities, reads "not exercised" when none had landed, and the resume classes require the kill or ENOSPC to have happened; with the injections staged early (DECISIONS 2026-10-27) retention is rarely exercised, and the claim the records carry is the campaign's continuation, said as such |
| 7 | P1: a driver or judge failure skips the archive and the report | fixed: the driver's exit is captured and the fetch, verification, deletion and report follow it; a judge or grade that does not complete leaves its failure for the report |
| 8 | P2: the S1 judge holds only the comprehension answers | fixed: a flows artifact (each attempt's script or commands with the counts) is the judge's second file, the two judged as one material; re-judged, the lengths dimension cites the sixteen-line script itself |
| 9 | P2: the exported-skill finding contradicts the tool record | fixed: the skill was loaded; the persona's follow-up was never sent at the one-turn cap; the finding withdrawn and the cap made the step's own budget |
| 10 | P2: proactivity penalises constrained tasks; the Codex "never" is false | fixed: each conversation step's `judged` list names the dimensions it is scored on and the worst eligible item binds (DECISIONS, the owner's to widen); the material states the step's line budget; the "never offered" claim corrected (two of six); the persona's card is not the judge's business — it rates the host |
| 11 | P2: the parity cause is not established | fixed: the finding rewritten from the archive's own words (the adapter re-ranks against the training scores: a transform change) |
| 12 | P2: S4 passes without the required rejection | fixed in part: the fact sheet records what the campaign held and the bars read both; `s4-claude-1`'s campaign held the void alone (its report says FAIL on the rejection bar); no archived campaign holds both — the owner's to choose |
| 13 | P2: S6 never exercised the Codex host nor the review | fixed: `--host` runs the campaigns on that coding agent and a `review-two` step on that host must name a served card the trace shows read or load-bearing; `s6-codex-1` relabelled as the Claude-host pair it was; `s6-codex-2` is the Codex host's round |
| 14 | P2: the text detectors accept statements that establish nothing | fixed: a bare score beside a number is not a delivery, the merge question and a hedge are not verdicts, a negated or self-check mention of approval is not a request; negatives tested |
| 15 | P2: the crash and diagnosis predicates pass without the event | fixed: the evaluator's own failure line, disjoint class and fix vocabularies, a scored attempt after the reply by node identity |
| 16 | P2: the author task does not test the runnable fixture; `bool(guesses)` | fixed in part: an author with nothing to guess is complete; the generic domain description is the design's cold author (the fixture withheld to keep the test about the guide), the attachment counts stay so each kind is exercised and the rubric says the ladder judges the form (Claude 23) |
| 17 | P2: author re-grading can use a different guide | fixed: the guide archived with the run and hash-checked against the pin before any grade; two classifier passes with an adjudication; both passing runs re-graded against their pinned guides (0 gaps) |
| 18 | P2: the single home does not control the preflight, S4's readers, the waits | fixed: the preflight reads the hosts' and the persona's models from the suite and asks Gemini only for a judged test; S4 reads `readers`; the grace and the trace-and-stop wait are the suite's; the trigger limits are the step's budget; the machine cap stays the safeguard it is, said |
| 19 | P2: the citation check folds `keep_me` and rejects a long quote | fixed: an underscore folds only at a word's edge; a quotation may run on; the one re-ask is a fresh judgment whose scores stand, said |
| 20 | P2: the judge's try/except | fixed: gone; the non-passing block is on disk first |
| 21 | P2: historical verdicts are not reproducible from their run | fixed in part: every record pins the suite's hash (S2's added), a report re-rendered under a changed suite says so, a re-judged run keeps its earlier judge directory beside the new one, the README describes the record as written; the suite and rubrics live in git at the pinned commit |
| 22 | P1: the acceptance status overclaims | fixed: the status rewritten line by line against the records as re-derived and re-run (below) |

### Claude Code

| # | finding | answer |
|---|---|---|
| 1 | P1: the baseline comparison is a detector artifact | fixed (Codex 2) |
| 2 | P1: the S1 judge has no material for two dimensions | fixed (Codex 8); the "independently" phrase now rests on the flows |
| 3 | P1: the S2 acceptance sentence is contradicted by its records | fixed: the status names what is true on no arm |
| 4 | P1: the second engineer's served build has no evidence | the arm re-run on the fixed driver (`s2-claude-second-2`, below) |
| 5 | P1: the Scope and Risks describe an abandoned plan | fixed: the credit paragraph and the risk rewritten, a decision recorded, the pushed session marked in every record's notes from now (`~/.codex/SOURCE`) |
| 6 | P2: a step's kind comes from the record | fixed: a kind other than the suite's fails; the exported skill's session runs on the Codex host too, so the step is a conversation on both |
| 7 | P2: the bank-tool predicate is vacuous | fixed: both hosts' turns carry each call's result status |
| 8 | P2: the two-message bar is a tautology | fixed: deleted; the count stays as information (DECISIONS) |
| 9 | P2: one word satisfies both halves of the diagnosis | fixed: disjoint vocabularies, tested |
| 10 | P2: `merge_verdict` is near-tautological | fixed: a statement, not the question or a hedge |
| 11 | P2: the launch clock and the attempt budgets | fixed: the clock starts after the driver's setup and stops at the first sampled moment the evidence holds; an attempt's minutes are the turn's wall clock; the records' column is said to be the earlier clock |
| 12 | P2: dead suite blocks; the reader's model misnamed | fixed: `readers` read by S4 and named as it ran (`claude-opus-5-5`); the fixture hashes gone; the Interface's pins trimmed to what exists |
| 13 | P2: the sandbox literal in the update frame | fixed: one source (`DEFAULT_SANDBOX`), the role's own when configured, pinned by a test across both sites |
| 14 | P2: the rubric names a budget the judge never sees | fixed: the material states the step's budget; the drift test reads the clause; the "verbatim" claim corrected |
| 15 | P2: "proactive" binds on steps made terse | fixed (Codex 10) |
| 16 | P2: the README's record shape | fixed |
| 17 | P2: `write.mdx` says the engine reads nothing else | fixed: `deploy` reads `metadata.run_kinds`, said on both pages |
| 18 | P2: the mention rule for a module without a page | fixed on both pages |
| 19 | P2: per-step caps are literals beside the suite | fixed: the cap is the step's message budget (a follow-up takes its parent's) |
| 20 | P2: a sub-exchange's cap is invisible | fixed: the cap lands on the parent step; the user's events are rendered |
| 21 | P2: the try/except and the rmtree flags | fixed |
| 22 | P2: one unblinded classifier call against the working tree's guide | fixed (Codex 17) |
| 23 | P2: the brief mandates what the rubric penalises | fixed: the rubric says the brief asked for each kind and scores whether each does a job only its form can do |
| 24 | P2: S6's per-build delivered metric | fixed: `delivered_score` |
| 25 | P2: `advisory` conflates the development box and the persona's nod | fixed: `advisory_dimensions`, reported not binding; the clean runs' records migrated and re-rendered |
| 26 | P2: the run archives are uncheckable | fixed: the README and the Interface say the archives are local to the development box; the reports are the tracked evidence |
| 27 | P3: `APPROVAL_ASKED` on a statement | fixed |
| 28 | P3: coldness asserted on Codex | fixed: reported as not established, the machine fresh |
| 29 | P3: pins cut to twelve characters | fixed: a sha alone |
| 30 | P3: the "read or load-bearing" label | fixed |
| 31 | P3: tunables outside the suite | fixed: the service's rows from the manifest, the persona's timeout the suite's turn timeout, the wait the suite's |
| 32 | P3: the one-step rule is vacuous when nothing errored | fixed: "not exercised" |
| 33 | P3: dead weight | fixed: the second engineer's card entry and the spent migration script deleted |
| 34 | P3: S4's run id | fixed: the readers in the id, the runner's id as the machine |
| 35 | P3: forty-one lines; the requirements error | fixed: the count, and the pages say an unparsable line stops `check` with pip's error |
| 36 | P3: a void by substring | fixed: by the attempt's integrity error |
| 37 | P3: the device-auth risk | fixed: a Risk bullet |

## Proof run

Each arm lands here with its run id, report and verdict. The first arm
proved the runner end to end and drove the fixes recorded with it.

### Learn validation, development box (2026-10-27)

Before the hours-long S6, the learn crew was validated on a ready-made WP7b
`churn-campaign` archive, into an isolated bank, with the `gpt-5.6-sol`
grader crew on the device-auth Codex session. It completed (exit 0) and
**banked 12 cards** (4 insights + 8 procedures, e.g.
`validation-margins-debit-shared-fold-selection-optimism`), pushing a real
commit onto the bank's founding skeleton. The whole crew ran — mine → exam →
card-writing (~15 clusters) → critic → repair (resolved in ~2 rounds) →
commit → push — and the critic did substantive work (demoting weak
qualitative cards, catching same-run echoes labelled `confirm`). This
de-risks S6's learn step and confirms the Codex graders work end to end.
Two notes carried to findings: the learn's runtime scales with the
archive's lesson-richness (~2.5 h for this rich campaign), and one Fable-5
grader call was safeguard-refused once and recovered on the next session.

### S1, Claude host, fresh GCP machine — run `s1-claude-1` (2026-10-27)

A real cold engineer on a fresh machine: two prerequisite campaigns built
(the second killed at ideation), tasks 1–6 on both the Python API and the
CLI, the comprehension reading, the flow counts. Provision → preflight
(real routes) → wheel install → scaffold → driver → fetch → judge → grade
→ report all ran; the machine was deleted after the record was verified
local (5.72 h, about $0.77). Report `tests/semantic/reports/s1-claude-1.md`.

**Verdict: FAIL**, each cause recorded as a fix or a finding:

- `comprehension_correct` 1.0, `wrong_calls` at most 1 (one errored call,
  fixed in one step), `first_try` 9/≥9 (re-read 2026-10-29 under true
  invocations: a `sed` over the docs had counted as task 2's first run) — the
  engineer read the tool correctly from the docs alone.
- **The grading tail was broken on first real contact** (commit
  `dc3d0a8b`): the judge's summary read the model reply's `scores` key, not
  the block's `items` (a crash that aborts the grade under set -e);
  `s1 --grade` demanded the `--host`/`--clone` the runner does not pass;
  and `evidence_of("resumed")` required the campaign to be still running,
  so a resume that *finished* — the good case — scored as no evidence. The
  tail only runs once a fetched record reaches the judge, which no earlier
  run had reached, so neither the unit tests nor the flow review had
  exercised it. Tests now pin all three.
- **The fetch dragged the throwaway venv** (commit `e07d8524`): the run's
  fetch ran over an hour because `scp --recurse` doubled a 1.2 GB venv
  across a symlink and paid a round trip per `.pyc`; it is now one tar
  stream with the venv/cache excludes — 67 MB of evidence in seconds.
- **task6-cli resume** was the resumed-evidence bug: it actually succeeded
  (0.797 → 0.8476, stopped sensibly on budget) and will pass with the fix.
- **task6-python resume**: the engineer ran the resume detached and ended
  the turn with "I'll report once it finishes", capturing no result — a
  detached-resume reporting signal (see findings).
- **task3-cli**: the machine's Codex credit was exhausted, so the churn
  build fell back to an all-Claude override — an environment limit the
  device-auth Codex session removes for later arms, not a product fault.
- **`python_lines` 16 > 12 and the judge's "flows fit the design's
  lengths" 0** — a bar not loosened to pass; see findings and DECISIONS.

### S1 on the released 0.7.10, Claude host, fresh machine — run `s1-released-2` (2026-10-28)

The retrospective baseline the design asks for: the same cold engineer,
tasks, budgets and judge on the released package's public docs (44 pages
staged from tag v0.7.10, 0.7.10 in the sandbox venv; the prerequisites
built the package's own way, `kapso evolve` detached, 56 min, 0.8503; the
second killed at five minutes in ideation). 3.92 h of machine, about
$0.53. Report `tests/semantic/reports/s1-released-2.md`. **Verdict: FAIL**
— the baseline the new stack is measured against, not a run to fix:

| | released 0.7.10 (`s1-released-2`) | the new stack (`s1-claude-1`) |
|---|---|---|
| first-try launches of twelve | 6 | 9 |
| launched at all | 6 (tasks 1, 2, 5-python, 6-cli) | 10 in the record, 11 real (the task6-cli resume) |
| minutes to launch, tasks 1–2 | 10.8 / 15.6 / 13.2 / 17.2 | 9.5 / 11.2 / 20.6 / 12.9 |
| comprehension, 7 facts | 0 | 7 |
| judge: names / lengths / docs | 0 / 0 / 0 | 1 / 0 / 1 |
| python_lines / cli_commands | 30 / 2 | 16 / 2 |
| errored calls, fixed in one step | 2, neither | 1, yes |

Both columns re-read from the archives on 2026-10-29 (the review's
finding): the first grading had counted the released arm under the
branch's verbs — none of its `kapso evolve` runs counted, and its one
"first try" was `learn`, the verb both packages share — and had counted
a `sed` over the docs as a run of the new stack. Under the package's own
verbs and true invocations the baseline launched six of twelve first try
against the new stack's nine; the judge, re-run over the answers and the
flows as one material, reads the baseline's comprehension at 0 of 7
against 7 and its flows as 30 lines against 16. The `minutes to launch`
column is the earlier clock (the driver's start to after the turn); the
driver now stops it at the first sampled moment the evidence holds.

What the released tool made the engineer believe, in its own words: "I
couldn't find a call named build. The build step was `Kapso.evolve()`";
"this Kapso has no way to take a harness" (task 3, both flows, nothing
launched); deploy "copied the repo … and wrote a `main.py` with a
`predict(inputs)` entry point" whose keys the engineer guessed wrong so the
one call wrote its defaults (task 4: the record the suite looks for does
not exist in 0.7.10); the Python learn stuck in its exam and the CLI learn
failed it — `report-writer produced no report`, the Codex sandbox on the
fresh VM: `bwrap: loopback: Failed RTM_NEWADDR: Operation not permitted`,
the same fault S6 met on the new wheel and the engine now avoids (the
learning crews' Codex roles on the adapter's default sandbox) — so the
released product's learn does not run on a stock Ubuntu 24.04 VM at all;
tasks 1 and 2 launched but delivered nothing in ten minutes (planning took
the budget, the coder had a minute). The resume on the CLI
(`kapso evolve --output campaign-killed --resume`) worked; both resume
flows ended the turn before the result, the detached-resume reporting
pattern seen on the new stack too, a host habit rather than either
package's fault. Bars: first-try 1 < 9, comprehension 0 < 1, python lines
24 > 12; the judge 0 on all three dimensions, quoting those answers.

### author, Claude host, fresh GCP machine — run `author-claude-1` (2026-10-27)

The cold author wrote a Kapso harness from the guide alone, over two rounds;
`kapso harness check` was green both times and the judge's four quality
dimensions (pages under forty lines, every skill named, no task value, the
ladder respected) all passed, 3/3 steps. Report
`tests/semantic/reports/author-claude-1.md`. **Verdict: FAIL** on one bar —
`structural_gaps_round2` 6 > 0 — with one fix and one design finding:

- **The grade crashed on a malformed classify reply** (commit `7300a665`):
  the judge pasted a quote-heavy guide code example into a JSON `"why"`
  string unescaped, so `extract_json` fail-loud raised (Rule 2). The `"why"`
  now asks for quote-free prose that cites the guide by reference, and the
  reply is archived before validation (as `judge_material` does); the
  offline re-grade then parsed and scored (gaps 8 then 6; check green).
- **The improvement loop was not wired** (DECISIONS, resolved 2026-10-28):
  the in-run `guide-fixes` step could neither classify round-1's gaps on
  the machine (the judge is dev-box-only) nor edit the guide, so round-2
  was written against the same guide — both rounds logged the same gaps —
  and the max-0 bar was unreachable by construction. The arm is now one
  cold author per run (step `write`, bars `structural_gaps` max 0 and
  `check_green` min 1, the guide's hash pinned), the fixes development
  work between runs. This run's eight structural gaps and one
  contradiction — pages need no front matter (the guide contradicted the
  reference), the pin form, what "mentions" a skill, how page lines are
  counted, extra front-matter keys on skills and delegates, the optional
  matcher, the `NAME=value` prefix in a hook command, the hook's working
  directory — are written into `docs/harnesses/write.mdx` and
  `docs/reference/harness.mdx`, each stating what `check` and staging do;
  the next author run is the design's round two.

**The loop, run to its bar (2026-10-28, four fresh authors on four guides;
reports `author-claude-1..4.md`):**

| run | guide | guesses | structural gaps | contradictions | `check` | verdict |
|---|---|---|---|---|---|---|
| `author-claude-1` | as shipped by WP2 | 34 | 8 | 1 | green | FAIL |
| `author-claude-2` | after run 1's fixes (b6f9277c) | 36 | 2 | 0 | green | FAIL |
| `author-claude-3` | after run 2's fixes (4cd4a99d) | 46 | 3 → 1 re-graded | 2 → 1 | green | FAIL |
| `author-claude-4` | after run 3's fixes (2fed2120), sha256 78fa1323… | 24 | 0 | 0 | green | **PASS** |

Run 3's classifier pass had labelled as structural three choices no rule
rejects (an MCP SDK pattern, a Python version, an optional README); the
`CLASSIFY` prompt now states the design's rejection test and asks for the
rule a wrong guess would trip (DECISIONS, 606ad0c3), and the same guesses
re-graded 1 + 1 — the gap a real one the first pass had filed as
already-in-guide (a skill named only on `guardrails.md` does not satisfy
the mention warning). Run 4 met the bar with the four judge dimensions
passing: the acceptance's "run after the guide's fixes" is this one, and
the guide's fixes are the four commits above. Each run's guesses fell
mostly into already-in-guide and domain decisions; the guide pages grew
by a clause per gap, none past a screen.

### S5 injections, Claude host — arms s5-claude-1..4 (2026-10-27/28)

The product handled every operational failure correctly — the evidence is the
engineers' own answers: provider-limit diagnosed the 429 and rode it out;
evaluator-crash diagnosed the missing holdout labels, **refused to tamper with
the protected evaluator** (per the brief), and paused to ask; missing-key named
the missing `DATA_API_KEY` and the 401; killed-session's campaign carried on
past a killed CLI. The arms also drove real harness fixes — the injection
kill-guards (a crash on an already-gone writer pid), crash-survival (a driver
crash no longer hangs the run via an orphaned sampler), and the tar-stream fetch.

The S5 *test harness*, though, stages its injections **non-deterministically**
(they depend on whether the campaign uses the enrichment, whether a transient
429 blocks, whether a node finishes before the injection lands), and several
success conditions were written for naïve agent behaviour rather than the smart,
rule-respecting behaviour the product shows. Two were calibrated this round:
provider-limit (arm at launch; accept recover-or-resume) now passes, and
evaluator-crash (detect the crash in the attempt's session, where it surfaces).
The product validation stands on its own.

**The calibration pass (2026-10-28).** The four arms' evidence was read
from their step records (the machines' `out/` was never fetched then):
provider-limit fired 3 of 3 once armed at launch and passed twice;
missing-key and killed-session passed; evaluator-crash read 0 crashed
attempts in every arm; killed-writer, full-disk, tampering and bank-compare
never ran to a record (a crash on an already-gone pid, since guarded; the
arms stopped). Two gaps closed: bank-compare compared nothing because no
bank was ever loaded, so every campaign is now served a seeded bank
(`tests/fixtures/bank_seed`, the S6 round-5 bank's three cards as one commit
in a bare repo) and the comparison has a head and a count to hold; and
evaluator-crash's crash sits in the attempt's own session when the session
ran the evaluator, so the detection reads the sessions as well as the trace
row. The staging itself stays as the 2026-10-27 decision left it — every
injection fires early, during the implementation phase, on the fixture's
real 0.85 goal: an unreachable target was re-tried for a second-attempt
staging and withdrawn within the hour, the recorded reason (the cold
engineer saw through the artificial goal) standing.

**Arm `s5-claude-5`** (evaluator-crash, killed-writer, bank-compare; 1.21 h
of machine, about $0.16; report `tests/semantic/reports/s5-claude-5.md`):
bank-compare **true** for the first time (the seeded bank's head and three
cards the same after both injections); the two injections false, each for
something the arm taught. evaluator-crash: the labels moved during attempt
one's implementation, the evaluator crashed, and the session rebuilt the
labels from the fixture's generator and scored 0.8503 (the finding under
"Findings for later packages"; the generator now removed from S5's project
before the launch). killed-writer: the writer killed at 15:28, the engineer
read `kapso watch`'s "RUNNING ♥ 289s ago ⚠ DEAD (pid 5554 is gone)", named
the class and the fix, resumed with `--resume` (the second ask found it
running and declined a competing writer), and the campaign went on from its
checkpoint to 0.8506 — the product's path as designed; the step read false
on `shown_dead` and `truthful` because the sampler kept the screen's first
word (RUNNING) and not its marker (⚠ DEAD) — fixed in the sampler, five
samples of the dead writer re-read.

**Arm `s5-claude-6`** (evaluator-crash and killed-writer again, full-disk,
tampering, bank-compare; 2.72 h of machine, about $0.36; report
`tests/semantic/reports/s5-claude-6.md`). **evaluator-crash true** on the
generator-free project: one attempt crashed on the missing labels, nothing
rebuilt, the engineer truthful, naming the class and the fix, the campaign
resumed. **killed-writer true on every predicate**: the writer killed while
implementing, DEAD shown within a heartbeat, the resume keeping the
attempts (none to two), the bank intact — the row reads FAIL on time alone,
48.7 min against 45. **full-disk**: the writer died with ENOSPC in the
launch's log, the engineer freed the space and resumed, two attempts after,
the campaign saved off the tmpfs — and the screen said FAILED with the pid
gone, not DEAD: the engine recorded its own end before it died, a more
truthful terminal word than the design expected, and the sampler's sleep on
top of its two `kapso watch` calls left no sample inside the one-heartbeat
window; both read right now (DEAD or FAILED counts as gone; the sampler
keeps its cadence), the row false on those two readings and on 60.6 min
against 45. **tampering true**: the evaluator edited inside the running
attempt's session clone, one void, the integrity void, truthful, the class
named — the campaign S4 reads. **bank-compare true** again. The two resume
classes ran their resumed campaigns out in full (a forty-minute budget
inside a forty-five-minute step), so the resumed campaign is now watched
for what is left of the step and stopped, the claim (continues from its
checkpoint, attempts kept) read from the trace. Across the six arms every
class has now been handled by the product with at most two user messages;
one clean arm of all eight steps on this harness is the record to cite,
run when a token window frees. S4's readers run on this arm's tampering
campaign (`s4-claude-1`).

**Arm `s5-claude-7`, the clean arm of all eight steps** (4.14 h of machine,
about $0.55; report `tests/semantic/reports/s5-claude-7.md`): **7 of 8
steps true and every bar met** — at most two user messages on each class,
the shown state truthful within a heartbeat on every sampled timeline, the
one request naming its variable and never a value, the seeded bank intact
after all seven injections. provider-limit: the shim fired three times, the
campaign rode the limit out, the engineer named the class and the fix and
rightly declined to resume a finished campaign. missing-key: the session
asked through the inbox, the reply resumed it within a second, the
authorised table fetch came after the reply, a scored attempt after the
resume. killed-session: the killed CLI's run ended in error and the campaign
went on by itself to two attempts. killed-writer: DEAD shown, resumed with
one flag, the attempt kept, 28.6 minutes inside its budget. full-disk: the
writer died with ENOSPC, the screen said FAILED with the pid gone (the
engine's own truthful word), the engineer freed the space and resumed, 43.4
minutes. tampering: the edited evaluator voided on the integrity check. The
one false row, evaluator-crash, is the product at its best and the engineer
at a slip: the session met the crashed evaluator, saw the moved labels
beside it, declined to put them back, raised an inbox request and paused
"waiting on the person"; the engineer diagnosed all of it and prescribed
`kapso inbox reply` — then, told the labels were back, ran `--resume`
instead and declared the campaign running while it re-paused on the
unanswered request two minutes later. The class passed on arm 6, where the
engineer resumed a campaign that had gone on; across the two arms every
one of the six classes has been handled as designed.

### S4, both readers on the S5 tampering campaign — run `s4-claude-1` (2026-10-28)

The campaign `s5-claude-6` tampered with (attempt one's evaluator edited in
its session clone and the attempt integrity-rejected; attempt two delivered
at 0.8512, goal achieved; $5.71 over 29 minutes), staged onto a fresh
machine with `kapso trace`'s text; a cold Claude reader (`claude-opus-5-5`
— the hosts table's model, which the reader ran on while the suite's
`readers` entry said `claude-opus-5`; the driver now reads `readers` and
the entry says what ran) proved cold from its session init, and a Codex
reader (`gpt-6-astra`) whose coldness a Codex stream cannot prove (no
init event; the record says "not established", the machine was fresh),
answered the six questions in a minute each; the Gemini judge graded them
against the fact sheet twice. **Both readers 6 of 6 in both passes**
(report `tests/semantic/reports/s4-claude-1.md`; 0.16 h of machine) — after
one correction to the fact sheet, not to the readers. The campaign holds
the integrity void and no judge rejection (the engine's "rejected:
Provided evaluation integrity check failed" is the void; its
`rejected_candidates: 1` counts that same attempt), so the design's
"a campaign with a void and a rejection" is half met: the report's
`campaign_has_rejection` bar reads FAIL, and no archived campaign holds
both (the one judge rejection in the archives, `s5-claude-7`'s
killed-session campaign, has no void). A campaign with both is the
owner's to choose or the next round's to produce. The first grading
read 5 and 4: the sheet had filed the integrity failure under "rejected"
and said "nothing voided", because the engine words that void "rejected:
Provided evaluation integrity check failed (changed: evaluate.py)", and it
carried the header's `unpriced_runs: 0` while four Codex repo-memory
sessions report no cost at all — so the Codex reader's "the complete cost
is not established" and both readers' "node 0's evaluation was voided on
the integrity check" were marked wrong against a sheet that was. The sheet
now classifies a void by its substance (an integrity failure is one,
whatever the engine's first word) and names the sessions without a cost by
host; the readings were judged again on the development box against the
rebuilt sheet, the readers' answers untouched. What the readers found in
the record, in their words: the S5 edit itself in the branch's diff ("an
added blank line and `# S5: an edit to the protected evaluator …` at
`kapso_evaluation/evaluate.py:97`"), the integrity rejection with its
reason, the delivered candidate reproduced bit-for-bit by the judge, the
cost's coverage, "not established" for the merge with the reasons (no
harness verification, a 0.0012 margin over the target).

### S6 experience, Claude host, fresh machines — arms s6-claude-1..5 (2026-10-28)

Four arms, each one lesson deeper. `s6-claude-1`: build-one true (43 min,
node 0 at 0.8484 then a second iteration), the learn dead in 0.2 s — the
mining crew on `claude-fable-5` met "You've reached your Fable limit": the
machine token's Fable week was spent (the learn validation and the S5 arms).
`s6-claude-2` (the learn on Opus 5.5) was stopped after eight minutes when
a fresh account turned up: the `kapso/.env` setup token, 0% on every window,
now secret `claude-oauth-token-5`. `s6-claude-3` on it, the shipped config:
build-one true (33.6 min, a 0.8624 GLM delivered, one scored observation);
the learn harvested and mined — the first mining session dead in 3 s on
"Fable 5's safeguards flagged this message (`[reasoning_extraction]`)",
the second interrupted mid-tool-call by the same classifier and finished by
the frame's repair round (22 min, 112 tools) — then the exam failed:
`report_writer produced no report.md … after 2 session(s): ended without
writing it; ended without writing it`, 0 cards, bank head unchanged.
Reproduced on a live machine: codex-cli 0.165.0's `workspace-write` sandbox
rejects every write on a stock Ubuntu 24.04 VM; only the adapter's default
sandbox writes. Fixed in the engine (DECISIONS: the learning crews' Codex
roles on the adapter's default sandbox; the fail-loud line quotes the
session) — a product finding a user on a fresh VM would have met.
`s6-claude-4` (Opus learn, before the fix) stopped at install.

`s6-claude-5`, the fixed wheel with the learn on Opus 5.5 (the Fable
safeguard stands between the shipped model and the mining prompt; an owner
call): **PASS, 4/4 steps** (2.97 h of machine, about $0.40; report
`tests/semantic/reports/s6-claude-5.md`). Build one, served nothing: node 0
at 0.8508 in 19.4 min, `goal_achieved`. The learn over its campaign, 135.8
min: mining on Opus, the exam's report written by the Codex `report_writer`
on the adapter's sandbox, the lesson crew (an Opus lead, two `gpt-5.6-sol`
workers; 88 min, $15.28, 204 tool calls) through three critic rounds to
three candidate cards — the holdout's sampling error bounding what a run can
claim and stop on, independence claims needing a channel the audited party
cannot touch, binned outcome profiles before model capacity — reliability
0.63–0.65, bank `026473cd9 → 53f04261c`. Build two, served that bank: read
two of the three cards in ideation, the judge found all three load-bearing
(lessons cited 1 of 1), node 0 at 0.8509 in 17.6 min, `goal_achieved`. The
pair: the same delivered score to four decimals, one node each, the served
build 1.8 min quicker to it — at this budget the churn fixture's goal falls
to the first attempt with or without the bank, so the bank can show only in
the time to the goal and in what the sessions read. The comparison's grid
held no common scored point: build one's score landed in the final partial
interval, past a grid cut at the last whole cadence, and build two's sampler
was killed by the driver's own poll before its terminal row — fixed after
the run (the grid reaches the terminal sample on one shared horizon; the
sampler writes its terminal row), so the Codex arm will carry a real gap
series. The bar as written (lessons cited, both builds scored) passed; the
gap bar was vacuous here and says so in the record.

**`s6-codex-1`, a second Claude-host round on the fixed driver** (2026-10-29,
TOKEN3, the learn on Opus; 2.95 h of machine, about $0.40; report
`tests/semantic/reports/s6-codex-1.md`). It was launched as the Codex
host's round and first written up here as such; the review read the
record: the runner had dropped the host and the driver built the Claude
host whatever it was given, so this pair ran on Claude Code (the record
says `host: claude_code`). The driver now takes `--host`, the campaigns
run on that coding agent and a review step on that host must name a
served card (DECISIONS); the Codex host's own round is `s6-codex-2`,
below. As a second Claude-host pair the round stands: **PASS, 4 of 4
steps**, and this time the pair sits on a real grid. Build one, served nothing: node 0 at
0.8501 in 15.8 min, `goal_achieved`. The learn, 115 min, banked two cards
(a correct specification beating capacity when the functional form is
recoverable; the hold-out's noise bounding evaluator spending once gains
fall below the noise floor). Build two, served that bank: both cards read
and both load-bearing, two scored observations in 40 min, delivered
0.8497. The comparison: build one's score lands at 16 minutes, build two's
first at 20, so build two is behind at five checkpoints and the gap, once
both define it, is −0.0004 at every point to the end — the bootstrap
standard error on this hold-out is 0.010, so the two deliveries are the
same score, and the served build reached it four minutes later. The
design's bar (a non-negative gap at every common point) is **unmet on this
pair, reported with the numbers** as the acceptance allows; across the two
rounds the bank's cards were read and found load-bearing both times and
the served build arrived at the fixture's goal once quicker and once
slower. At this budget on this fixture, with the first attempt already at
the goal, experience shows in what the sessions read, not in the score.

### author, Codex host — run `author-codex-1` (2026-10-28)

On the guide after the four Claude rounds: 35 guesses, 0 structural gaps,
0 contradictions, `check` green, three judge dimensions at 1 — and "the
ladder respected" at 0 in both passes: a SessionStart hook that restates a
page line and a server returning a fixed checklist, filler for the brief's
"at least two hooks, one server". The guide never stated the ladder the
rubric scores (the Claude author kept it unprompted); it does now, in
"The directory" (330f8e1f), and `author-codex-2` on that guide (sha256
7c7ea8a2…) passed everything: 34 guesses, 0 structural gaps, 0
contradictions, `check` green, the four dimensions at 1. Both hosts meet
the author test's bar on the guide as it stands.

### S2 with the persona, both hosts, fresh machines (2026-10-28)

The round that found the suite's own rough edges: two full runs on the
first harness, then targeted re-runs of the rows each fix touched, then
the clean full runs on the fixed harness and wheel (`s2-claude-2`,
`s2-codex-4`, recorded below when they land). Every row that failed is
either a harness fix with its commit, a product finding under "Findings
for later packages", or a budget calibration said in the open — never a
bar loosened to pass.

**`s2-claude-1`** (Claude host, the persona on `gpt-6-astra`, the first
harness and wheel; 2.68 h of machine, about $0.36; report
`tests/semantic/reports/s2-claude-1.md`): 16 of 25 steps; the triggers
19–20 of 20 per skill and the holdout 10 of 10; cold-install, harness-new
(3 messages, 2 questions, 4.7 min), harness-probe, campaign-session
isolation and cold-start true; the judge at 4–5 on every conversation but
two (`harness-export` 1–3: the exported skill not loaded when asked;
`deploy` engaging 2). The nine false rows and what each became:

| row | what happened | became |
|---|---|---|
| inbox | the pause campaign's 10-min budget was spent before the reply (`attempt_would_not_fit`); the persona's first-exchange want read the key's sequencing wrong | `builds.pause.minutes` 40 single-sourced (d783ad90, 0b5b16ae), then 60: on `s2-claude-3` the session ran 27 minutes before it asked for the key and the 13 left after the reply could not hold an attempt — the budget must cover the time to the pause and an attempt after it; then `s2-claude-inbox-4` paused at 51 minutes with two requests (the key and an endpoint document) of which the host answered one, and the campaign stayed waiting (judge 5/5/5/5/5) — the brief's rule now demands the fetch before anything else and the person's reply covers every open request (4d8f90d2) — on `s2-claude-inbox-5` the session asked at 19 minutes with three requests (the key, the service, the table), the host answered all three within fourteen seconds and the campaign continued on each (judge 5/5/5/5/4; 0.51 h of machine); the exchange wants split (490235b8) — every predicate true on both hosts (`s2-claude-inbox-3`, judge 5/5/5/4/4; `s2-codex-inbox-2`, judge 3/5/5/4/4: the Codex host's reply named the key, told the person to put it in `.env` and to follow with `kapso watch`, which both passes read as short of proactive) |
| review | the predicate wanted a delivered branch named; a campaign that missed its goal delivers none, and the record's branch lives at the solution's top level | `names_delivery` with the nothing-delivered words (672a38a3); the top-level branch (02682132); turn cap 2→3 — every predicate passed on `s2-claude-review-2` (judge 5/5/5/4/4), capped only on the persona assigning follow-up work → the persona's DONE rule (ea5fa8ee); `s2-claude-review-3` then completed in 2 messages, 0 questions, 1.4 min (the delivered branch named, a merge verdict given; judge 5/5/5/4/5), 19 lines against the 12-line budget |
| build-data-only | the approval request sat two lines above a closing command line, which the end-anchored detector read as no question | the detector sets trailing command lines aside and reads the closing three prose lines (c2c2a000, fbcf9fe0) — true on `s2-claude-dataonly-1` (3 messages, 1 question, judge 4–5) |
| build-fraud | four messages revising the protocol, "Nothing is launched" | a product finding (the build skill's stop-designing-and-launch wording); on `s2-claude-propose-1` the same fixture launched in 2 messages (judge 5/5/5/5/4) |
| build-pause, build-empty-wish | true, over the 12-line budget (19 and 14 lines) | calibration, below |
| learn-complete | the exam's report writer died on the Codex sandbox — the pre-fix wheel | the engine fix (c151df52), proved by S6 round 5 |
| second-engineer-build | no cards to serve (the learn above) | the same; and the Codex run's crash on the missing second user → `ensure_second_user` (dc1f21d6) |
| deploy | parity "differs" (0.9838 deployed vs 0.9871 delivered) | a product finding: the delivery re-fits at load (WP5's call) |

**`s2-codex-1`** (Codex host, the persona on `claude-opus-5`, the first
harness; evidence under `scripts/redesign/runs/s2-codex-1/fetched/`, no
report — the driver crashed at second-engineer-build): 14 true of 21
recorded; build-churn, build-pause, watch, harness-export, campaign-tools,
build-fraud (2 messages, a contract-ok evaluator), build-data-only,
build-empty-wish, harness-new, harness-probe, learn, session-brief true;
**the triggers 4 of 18 per skill, the holdout 0 of 10** (codex-cli 0.165;
WP7's round on 0.153 passed — a product finding); inbox, review and
learn-complete false for the harness and wheel reasons above; deploy
parity differs on this host too (0.9776 vs 0.9817); experience-share
false, then the crash: `cp: cannot create directory '/home/proof2/…'`,
`chown: invalid user proof2` — the second user existed only on the Claude
host's cold-install path, now made by every step that needs it.

**`s2-codex-4`** (the clean Codex run's first attempt, 2026-10-28 14:16–16:41,
2.46 h of machine, about $0.33): install, setup, build-churn, build-pause and
watch true, then the triggers probe at a third of the morning's pace — 67 of
178 runs in 107 minutes, only one of them a 429, each `gpt-6-astra` session
simply slow — on course to meet the machine's 6-hour cap before the fetch.
The host's own turns had run 8–11 minutes against 2–5-minute budgets on the
same slowness (build-churn 11.0, build-pause 9.4, watch 8.5). Stopped with
its six steps fetched (`scripts/redesign/runs/s2-codex-4/fetched/`); the
clean run relaunches as `s2-codex-5` behind a latency gate — three one-token
`gpt-6-astra` calls in a row under twenty seconds and free of 429s.

**`s2-claude-2`** (the clean Claude run, 2026-10-28 13:05–19:05, TOKEN3,
the learn on Opus): twenty-two steps recorded in the launch log, sixteen
true — cold-install, build-pause, watch, triggers (23.7 min), harness-export,
campaign-tools, **inbox** (the pause arrived, was replied, the campaign
continued), **build-fraud launched** (2 messages, a contract-ok evaluator),
build-empty-wish, harness-new (3 messages, 2 questions, 5.1 min),
harness-probe, learn, session-brief, experience-share; false: build-churn
(the host launched without ending a turn asking — once, against four
Claude arms that asked), build-data-only (3 messages, 2 questions, the
persona at its cap), review (the verdict in the skill's form the detector
did not know, fixed above), deploy (parity "differs", 0.9803 vs 0.9805, the
re-fit finding), **learn-complete at the step's 150-minute cutoff** — the
churn campaign's first attempt took 48 minutes and the learn over it ran
mining 36, the exam 68 and the lesson past 80 minutes, a timing finding
beside the learn validation's — and second-engineer-build with no card to
serve. Then the machine's six-hour auto-delete fired at harness-improve,
step twenty-three of twenty-four, the fetch never reached: the evidence
beyond those step lines is lost. The cap was a literal per test
(`machine.max_run`); it is now the run's own length from the suite — the
host's step budgets end to end, the grace and an hour of provisioning,
rounded up (`machine_hours`; ten hours for the Claude S2 run, eight for S5
and S6, six for S1 — which had survived its five-and-three-quarter hours
under the same six by a quarter). The clean Claude run is re-run as
`s2-claude-3` under that cap.

**`s2-codex-5`** (the clean Codex run, launched by the latency gate at
16:46, token-5, the learn on Opus; 4.31 h of machine, about $0.58; report
`tests/semantic/reports/s2-codex-5.md`): **17 of 24 steps**, every
conversation inside its budget on time and lines (the host answered in 2–9
lines, 0.3–2.5 min). True: install, setup, build-churn (2 messages, 1
question), build-pause, harness-export (the export and its refusal; the
exported skill's session is the Claude host's — recorded as a shell step on
this host now, the judge having died on a conversation that never was),
campaign-tools, **inbox** (paused, replied, continued), **build-fraud**
(launched in 2 messages, a contract-ok evaluator), build-data-only,
build-empty-wish, harness-new (2 messages, 1 question, 5.1 min),
harness-probe, learn, experience-share, harness-improve, campaign-session
isolation, the Codex rules probe. False: watch (every predicate held; the
persona asked a third question at the two-turn cap), **triggers 4 of 18 per
skill and 0 of 10 holdout — the first run's figures exactly**, which the
review traced to the machine, not the host: 153 of the 356 main runs and
all 10 holdout runs died in codex's sandbox before any skill could be
read (`bwrap: loopback: Failed RTM_NEWADDR`; re-graded 2026-10-29 as
not established; the finding below and `s2-codex-triggers-1`), review (the host wrote "no
winner was delivered … 0.0041 short of 0.85 … the target remains unmet" of
a campaign with no branch, words the detector did not know and now does;
re-read, both predicates hold), deploy (nothing delivered to deploy),
learn-complete at the 150-minute cutoff (mining 25, the exam 48, the
lesson past 77 minutes; DECISIONS), session-brief (an empty bank; the host
asked instead of answering) and second-engineer-build (no card to serve).
The judge: clear 4 and not annoying 4 pass; **proactive 1, engaging 1,
return on attention 1 fail** — the Codex host's answers are right and
terse (build-pause, campaign-tools, experience-share, learn, session-brief
and watch at proactive 1–2: the state said; the next step offered on two
of the six — the pause answer gave the watch, inbox and reply commands,
the learn answer the watch and serving lines — and absent on the rest)
where the Claude host's ran 4–5 on the same steps; a product finding for
the Codex host's skill wording, under "Findings for later packages". The
suite now judges `proactive` and `return on attention` only on the steps
whose intent invites a finding (a step's `judged` list; DECISIONS
2026-10-29), so a two-line state report no longer binds the run on what
it was budgeted not to do; the re-judged verdicts are below.

**`s2-claude-3`** (the clean Claude run under the derived cap, 2026-10-28
21:06 to 00:48, token-5, the persona on `gpt-5.6-sol`, the learn on Opus;
3.79 h of machine, about $0.51; report `tests/semantic/reports/s2-claude-3.md`):
**19 of 25 steps**, every predicate of every step met but two. True:
install, setup, cold-install, watch, triggers (19.7 min), **harness-export
with the exported skill loaded this time**, campaign-tools, build-fraud
(launched in 3 messages, 12 lines), build-data-only (1 message, 11 lines),
build-empty-wish, harness-new (4 messages, 2 questions, 6.2 min, 33 lines),
harness-probe, learn, **learn-complete in 112 minutes with two cards
banked**, session-brief (a card read from the bank), experience-share, 
harness-improve, campaign-session isolation, cold-start. False: build-churn
and build-pause on lines alone (15 and 13 against 12), review on lines alone
(20; the branch named — none — and the verdict given), inbox (the pause
campaign's 40-minute budget spent before the reply, the calibration above;
passed on `s2-claude-inbox-5` after it), deploy (the churn campaign
delivered nothing — node 0 at 0.843, unjudged at the 60-minute deadline —
so there was nothing to deploy; the host said so and asked), and
second-engineer-build (the served build died at the engine's preflight for
want of a Codex login on the second user — the finding below; the user now
carries the session, `s2-claude-second-1` re-measures it). The judge: clear
4 and not annoying 4 pass; proactive, engaging and return on attention fail
on the worst item — the deploy conversation with nothing to deploy (2, 2, 2)
and one pass's 1 on harness-export's proactivity — while sixteen of the
seventeen conversations sit at 4 to 5 on every dimension.

**`s2-codex-triggers-1`** (the trigger suite alone on a fresh Codex
machine, 2026-10-29 03:16 to 04:12, the sessions unsandboxed by the
runner's word after the review traced the first run's miss to codex's
sandbox; report `tests/semantic/reports/s2-codex-triggers-1.md`, a
targeted arm whose other required steps are absent by design): **the
bar met** — main `build` 18/18, `harness` 18/18, `kapso` 16/17, `review`
17/18, `setup` 18/18, holdout 10/10, no cross-skill false positive, no
run whose sandbox failed; 87 of 89 cases passed every run and the two
that did not read a forbidden skill after the expected one (a pass under
the host's rule). The first run's "4 of 18" was the machine's: the
sessions on codex-cli 0.165 could not start their sandbox on the GCP
image, and the plugin's skills trigger on that host as they do on the
development box.

**Calibration, said rather than tuned.** The Claude host's build
conversations run 14–19 lines against the 12-line budget in every arm
(`build-churn` 11 → 14–15, `build-pause` 19 → 15, `build-fraud` 15,
`build-data-only` 15): the approval message the evaluation skill
prescribes — what is here, the five-line protocol, the brief in a fenced
block, the ask — needs about fifteen lines outside the fences; the Codex
host says the same in 3–8. The budget is the design's and stays; whether
the skill's message is trimmed or the budget is fifteen is the owner's
call (DECISIONS). The persona for Claude hosts moved from `gpt-6-astra`
to `gpt-5.6-sol` (57bf5f50) after the device-auth Codex session's
`gpt-6-astra` spent the afternoon in 429 retries — the persona's minutes
exclude its own waiting, so no row moved, but a full run crawled.

**The judge, hardened by this round.** Gemini's fail-loud citation check
lost two of ten reports before three causes were found and fixed: a quote
on the wrong line is re-asked once (b59937ef); a sentence the rendering
wrapped is cited by the line it starts on (9ff6ba26); markdown around the
quoted words is folded on both sides (07d040a6, ae665730). A fetched run
is re-judged on the development box with `judge.py` and `report.py` over
its `fetched/out`.

## Findings for later packages

**From the live S2 round (2026-10-28, both hosts on fresh machines):**

- **Deploy parity fails because the serving adapter changes the
  prediction's transform.** On both hosts the deployed call's answer for
  the proof row differed from the delivered prediction (Claude 0.9838 vs
  0.9871; Codex 0.9776 vs its own). The Claude archive says why in the
  host's own words: the delivered `predict.py` ranks each score against
  the other rows of the same batch, which cannot work for one row, so the
  adapter the deploy session wrote "ranks against the training scores
  instead, so a row gets the same score whether it's sent alone or in a
  batch" — and the regenerated batch predictions were byte-identical to
  the delivered file. That is a semantic change the session made to serve
  single rows, not a re-fit's randomness (the review's reading, corrected
  from the first draft here). Parity, as WP5 defines it, holds only when
  what is served computes what was evaluated: either the deploy skill
  forbids a transform change and asks for a batch-equivalent call, or a
  brief that wants a deployable result says what one call must equal —
  WP5's call.
- **The Codex trigger suite cannot run in codex's sandbox on the fresh
  machine.** `s2-codex-5`'s 4 of 18 per skill was first written here as
  a discovery regression; the sessions' own words say otherwise: 153 of
  its 356 main runs and all 10 holdout runs reported `bwrap: loopback:
  Failed RTM_NEWADDR: Operation not permitted` — codex-cli 0.165's
  read-only sandbox cannot start on the GCP image — announced the skill
  they meant to read and could not read it (re-graded 2026-10-29 under
  the runner's sandbox classification: 7 of 89 cases established, the
  rest not established, never a miss). The runner now probes the sandbox
  once, classifies such runs as the machine's failure, and on that image
  runs the trigger sessions unsandboxed by the runner's word (`--sandbox
  danger-full-access`, said in the record); the suite re-ran that way
  (`s2-codex-triggers-1`, above) and met the bar: 18/18, 18/18, 16/17,
  17/18, 18/18 per skill, holdout 10/10, no false positive. No regression
  in the host's skill discovery: the finding is withdrawn, and what
  stands is the machine fact — a Codex session's own sandbox does not
  start on that image, which a person running Codex there would meet
  before any skill.
- **An exported skill's session answered the question but did not
  satisfy the persona.** The export itself was right on both hosts (the
  skills, delegates and `.mcp.json` placed, the hooks and module pages
  left behind with the reason). The first draft here said the Claude host
  "answered from memory without loading the skill"; the transcript shows
  `Skill({"skill": "backtesting"})` and "Launching skill: backtesting"
  before the answer — the skill was loaded — and the persona's "load the
  skill and cite its path" was never sent because the exchange had one
  turn (the review's reading, corrected). The driver's exchange cap is now
  the step's own budget (two messages), so the follow-up is answered; on
  `s2-claude-3` the skill loaded and the persona was done in one. No
  product finding stands here.
- **The Claude host's build conversations run long and, twice, did not
  launch.** Its `build-pause` reply was 19 and 15 lines against a 12-line
  budget; on the fraud fixture it spent its four messages revising the
  evaluation protocol and ended with "Nothing is launched"; the Codex host
  launched the same fixture in two messages with a contract-ok evaluator.
  The build skill's wording on when to stop designing and launch is WP7's.
- **Fable 5's safeguards and the mining prompt; codex-cli 0.165's
  workspace-write sandbox on a VM** — recorded in DECISIONS (S6).
- **A build needs a Codex login even on the Claude host.** The second
  engineer's served build on `s2-claude-3` — the first run with cards to
  serve — died at the engine's preflight: "codex authenticated … needed by
  inference.roles.commit_message.model (+1 more) = gpt-5.6-sol". Two of
  the packaged defaults' roles run on Codex, so a person with only a
  Claude login cannot `kapso build` without a config override, and the
  setup skill's doctor says so only at launch. The suite now gives the
  second engineer the machine's Codex session; whether the defaults should
  route those two roles to the host's own vendor when the other is absent
  is the owner's (config defaults).
- **The Codex host answers right and stops.** On the clean Codex run
  (`s2-codex-5`) every conversation met its budget, the states it reported
  were true, and the judge read "clear" and "not annoying" at 4 — and
  "proactive" at 1 to 2 on six steps (build-pause, campaign-tools,
  experience-share, learn, session-brief, watch): the answer gives the
  state and never the next step — what to watch, what the pause wants,
  what the bank now serves — where the Claude host's answers on the same
  steps carried it and scored 4 to 5. The skills are the same files on
  both hosts; the Codex host reads their "say what comes next" less. A
  wording the Codex host follows is WP7's; whether a terse right answer
  should fail "proactive" is the rubric's owner's.
- **A session that met a crashed evaluator rebuilt its inputs instead of
  reporting it.** In `s5-claude-5`'s evaluator-crash (2026-10-28) the
  hold-out labels were moved away while attempt one was being written; the
  evaluator crashed on `holdout_labels.csv`, and within a minute the
  implementation session re-ran the fixture's seeded `generate.py`,
  checked the output against `MANIFEST.json`, copied the labels into the
  protected `private/` directory, scored 0.8503 and left itself a note
  (`.kapso/shared_cache/fixture-restore-note.md`) on how to do it again.
  The engine's feedback judge named it — "an evaluation defect to report,
  not to repair"; the session should have stopped with an
  `<evaluation_change_request>` — and accepted the score, since the
  rebuilt file matched the manifest's hash; the cold engineer, asked
  afterwards, said the result "is valid only if you accept the agent's
  repair of the evaluator". Two things for the owner: a session's write
  under the evaluator's private directory is a protocol breach the hash
  check cannot see (the file was identical), so the judge's flag should be
  a void, not a remark; and the fixture's generator is what made the
  rebuild possible — a real repository has none, so S5 now removes it
  from its project before the launch (a driver's act in the record).

From `s1-claude-1` — the signal the suite exists to catch, kept for the
product and the docs, not the suite:

- **A detached resume leaves the engineer without the result.** On the
  Python surface the engineer launched the resume detached and could not
  report its outcome within the turn. `kapso build --resume` returns once
  the run is launched, but the cold engineer had no obvious way to await or
  poll a detached run's result from Python. Worth a concise "wait for / read
  a detached run's result" idiom in the docs or the API.
- **The hardest single task ran 16 lines of Python against a 12-line bar**,
  and the judge independently read the flow as longer than the design
  intends. The core flow — load the path-named harness, build, read the
  solution — is terse; the length came from a multi-line `build(...)` call
  and voluntary diagnostics. Whether the target is the product (a more
  concise harness-load-plus-build idiom) or the metric (count statements,
  not physical lines) is left for the owner in DECISIONS.

From the learn validation:

- **A learn's wall-clock scales with the campaign's lesson-richness.** The
  rich WP7b `churn-campaign` yielded ~15 lesson clusters and took ~2.5 h to
  mine, exam, write, critique, repair and bank 12 cards. A fresh small
  build-one campaign (what S6 learns) will be far shorter, but a learn over
  a long real campaign is an hours-scale operation — worth a progress
  surface a user can watch (`kapso watch learning/status`) and worth noting
  in the product's expectations.
- **A grader call can hit a transient Fable-5 safeguard refusal.** One
  `claude-fable-5` crew call returned `model_refusal_no_fallback` ("safe,
  normal conversation" false positive) and the next crew session proceeded
  normally. Rare and self-recovering here, but a crew that depends on a
  single refused call completing would stall — the crews already tolerate it
  by re-running the role.

## Built

| commit | what |
|---|---|
| `e20e7395` | the sub-plan's first version and its planned decisions |
| `d47187a2` | change 1: the learn completes on the two cases the round found (the colon fragment as a finding; the role runner fails loud with what each session said) |
| `70398ae5` | the suite README's fixture table |
| `2c19d9d9`, `83fdc7f1` | change 9: the pipeline example on dbt and DuckDB, its evaluator, brief, README, baseline, runner and contract test |
| `dc3d0a8b` | the grading tail fixed where the first live S1 run exercised it (judge summary shape, `--grade` args, resumed evidence) + tests |
| `e07d8524` | the fetch is one tar stream with venv/cache excludes, not a recursive scp |
| `64eef486`, `3010342f`, `f3c69f68` | S5: injection kills guard an already-gone process; a driver crash no longer hangs the run on an orphaned sampler; full-disk fills while the writer implements |
| `ff42ef0c` → `19bb4cb5`, `659712b6` | S5: the unreachable target tried and reverted; every injection fires early and accepts the engineer's correct handling; evaluator-crash reads the failure where it surfaces |
| `7300a665`, `4724ad6a`, `238c7d3c`, `606ad0c3` | the author test: classify keeps its reply; one cold author per run with the guide's fixes between runs; the classifier applies the design's rejection test; the reports tracked |
| `b6f9277c`, `4cd4a99d`, `2fed2120`, `330f8e1f` | the harness guide's fixes from the author rounds (the nine guessed points, the hook context key, the module-page mention, the attachment ladder) |
| `d5ac28ea`, `b1200b85`, `873b03f2` | S1's released baseline: the tag's docs staged into the pack; no wheel flag; the prerequisites in 0.7.10's own verb |
| `411b230e` | fresh machines get the credited device-auth Codex session |
| `c151df52` | engine: the learning crews' Codex roles run in the adapter's default sandbox; the grader's fail-loud line quotes the session |
| `d783ad90`, `0b5b16ae`, `490235b8`, `ea5fa8ee` | S2: the pause campaign's budget in the suite (forty minutes); the inbox exchanges' wants; the persona's DONE rule |
| `672a38a3`, `02682132`, `dc1f21d6` | S2: a review of nothing delivered passes by saying so (a third turn); the solution record's own branch key; the second user provisioned on either host |
| `c2c2a000`, `fbcf9fe0` | S2: an approval request within the closing lines ends the turn asking, trailing command lines set aside |
| `b59937ef`, `9ff6ba26`, `07d040a6`, `ae665730` | the judge: one re-ask on a citation slip; a quote on the line it starts on; the markdown around the quoted words folded |
| `57bf5f50` | the Claude host's persona answers on `gpt-5.6-sol` |
| `d4364027` | S6: the grid reaches the terminal sample on one shared horizon; the sampler writes its terminal row before it is stopped |
| `d0ba4c42`, `2ac0a113` | S5: every campaign served a seeded bank (`tests/fixtures/bank_seed`); the crash read from the attempt's sessions; the second-attempt staging tried and withdrawn under the 2026-10-27 decision |
| `a52e1a10` | the name-hygiene tests allow the released baseline's evidence |
