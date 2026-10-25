# WP6: Observability

2026-10-25. Owner: the redesign. Branch `wp6-observability` off `redesign`
(after WP3's pull request #157). Size M.

## Scope

What a person, a model, or the plugin's skills can read of a campaign
without the agent that ran it, live and afterwards: the record completed
(every session's digest from both hosts' transcripts: the hooks that
fired and what they decided, the delegates asked, the tools and gates
used, the cost and the duration, how it ended); the record's lifecycle
made truthful (a record saved before the delivery steps that can raise,
`done` published after it, `failed` with the error on every unhandled
exception, the engine's own errors printed as one line); `kapso trace`,
the campaign read after the fact as text and as JSON, built to answer
S4's six questions from the record alone; `kapso watch` completed (the
harness and the sources in the header, the error of a failed campaign, a
campaign that stopped before its status, a no-argument listing through
the registry's liveness filter); `kapso doctor --json`; the learning
status naming a refused lead. S4 and S5 become runnable.

**Not in scope.** The budget's end and the judge's retry (WP4: the
finalisation reserve, the retry carrying its prompt); config without
modes and `--coding-agent` routing (WP4); the plugin's commands and the
`kapso-review` and `kapso harness improve` skills that read the trace
(WP7); the semantic suite's driver, judge and report (WP9: this package
makes S4 and S5 runnable and runs S4's reading and two of S5's five
injections by hand on the proof machine); `events.jsonl` and the OTel
vocabulary, threshold alerts, an OTLP exporter (the observability
design's deferred list, still deferred); a static page or notebook
export of the trace (decided against: text and JSON are what a reader
and a script need); the evaluation archive's own selection records
(evaluation governance, read as they are).

## Interface

**Exposed.**

- `kapso trace <campaign> [--json] [--attempt <branch>]`. `<campaign>`
  is a campaign directory (the solution's trace) or the path of a
  record in it. Text by default; `--json` prints the trace's data;
  `--attempt` narrows the attempts section to one branch with its full
  evidence. Exit 1 when the directory holds no campaign.
- `Kapso.trace(path) -> TraceView`, a classmethod like `Kapso.status`:
  `view.data` (the JSON), `view.explain()` (the text the CLI prints),
  `view.attempts`, `view.delivered`, `view.answers` (the six). A pure
  reader over the record: it never writes.
- The trace's sections, in order: the header (the objective's first
  line, the harness identity, each source's label, the evaluator's
  version and provenance, the budget spent of the budget given, the
  cost, the outcome line of `Solution.explain()`); the attempts, one
  block per node in order (the idea's first line, the branch and parent,
  the implementation session's digest, the evaluation's score with its
  validity or integrity error, the verification's verdict with its
  findings, the judge's call in one line, the lessons the attempt read
  and cited); the lessons (per source: served, read, cited, by which
  attempts); what was voided or rejected, each with its evidence; the
  sessions that failed every time they ran, by kind; the delivered
  candidate (branch, commit, files changed against the seed); the six
  answers (what won, why, what was voided and on what evidence, what was
  rejected and why, what it cost, whether it is safe to merge), each a
  line that cites the record it comes from.
- The session record, `<campaign>/.kapso/sessions/<id>/session.json`,
  one per staged session on either host, written by the staging at
  session start (the fields WP2's `harness.json` carried: `module`,
  `host`, `session_id`, `skills`, `mcp_servers`, `agents`, `hooks`,
  `stream`) and completed at session end with the digest: `started`,
  `ended`, `duration_seconds`, `cost_usd` (null when the host reports
  none), `exit` (`success` | `error` | `timeout` | `refused`),
  `turns`, `tools` ({tool: count}), `gates` ({server: {tool: count}}),
  `hooks` ({`responses`, `denials`, `blocks`, `context`}, or null when
  the host reports no hook events), `delegates` ([{name, count}]),
  `files_changed`, `last_message` (the session's closing text, in full).
  `harness.json` goes (Rule 7); the harvest, the exam and the hindcast
  read `session.json`.
- The transcript digests, `kapso.execution.coding_agents.transcripts`:
  `digest_stream(host, path) -> dict`, one parser per host over the
  stream the adapter writes (Claude Code's `stream-json` events; Codex's
  `item.*` events), the same keys for both, null where a host has
  nothing to say. The trace and the session record are its only
  readers.
- The status file gains nothing new in shape; `kapso watch` renders
  the `harness` and `experience` fields it already carries, and the
  `error` of a `failed` state, in the header. A campaign that stopped
  before writing a status is one line naming its log.
- `kapso watch` with no path: the campaigns of `inbox.registry` that
  are alive or waiting, one line each (state, phase, age, best, path),
  newest first; `--all` lists every registered campaign whose directory
  exists, with its state. The liveness filter,
  `kapso.execution.inbox.live_campaigns(registry) -> list`, keeps a
  campaign whose status is `running` with a fresh heartbeat and a live
  process, or `done` with `stopped_reason: waiting_for_user`; `kapso
  inbox` with no argument reads the same list.
- `kapso doctor [verb] --json`: `{"scope": "kapso doctor <verb>",
  "ok": bool, "requirements": [{"label", "ok", "required", "origin",
  "fix", "detail"}]}`; exit 1 when a required item fails, as the text
  form; `--models` adds the live rows.
- The CLI's error line: `kapso` prints `Error: <message>` and exits 1
  for the engine's own error classes (`BriefError`, `HarnessError`,
  `HarnessReferenceError`, `ManifestError`, `ExperienceError`,
  `ExperienceReferenceError`, `IngestError`, `EvaluationIntegrityError`,
  `PreflightError`, `GitReferenceError`, `InboxOpenError`, the
  `RunCheckpointError` family, `WorkspaceCheckoutError`,
  `GateCapabilityError`), whose messages are written to be read alone;
  any other exception keeps its traceback, since it is a bug. The
  detached child prints the same into its log.
- The record's lifecycle: `build()` saves the solution record before
  the final checkout and the summary, then publishes `done`; an
  exception after the status exists publishes `failed` with the error
  (the orchestrator's `finally` already does it inside `solve()`; the
  facade does the same around the rest). `Solution.open` succeeds the
  moment `kapso watch` says `done`.
- The learning status: a mining lead whose first turn is refused
  (`exit: refused` in its session record) is relaunched once before any
  repair round, and the learn status notes it.

**Consumed.** WP1's `Solution` and record, the status file and
`OperationStatusView`; WP2's staging (`StagedHarness.record()`), the
verification directory (`verdict.json`, `diff.patch`,
`evaluation_output.txt`), the task statement; WP3's serving record and
pull log, the sources' labels; the checkpoint's node history; the
inbox registry and `Request`; the preflight's `Requirement`; the two
adapters' stream artifacts and their `CodingResult`.

Frozen once reviewed; a change afterwards is a note here and a line to
WP7 (the skills read the trace and `doctor --json`) and WP9 (S4 and S5
read the trace and the status).

## Ownership

Edits: `src/kapso/execution/trace.py` (new), `src/kapso/cli/trace.py`
(new), `src/kapso/execution/coding_agents/transcripts.py` (new),
`src/kapso/cli/watch.py`, `src/kapso/cli/doctor.py`,
`src/kapso/cli/__init__.py` (the verb, the error line),
`src/kapso/execution/observability.py` (the header, the listing),
`src/kapso/execution/inbox.py` (the liveness filter),
`src/kapso/harness/staging.py` (the session record), the two adapters'
`cleanup` and the stream close, `src/kapso/kapso.py` (the record's
lifecycle, `Kapso.trace`), `src/kapso/execution/orchestrator.py` (`done`
leaves `solve()`), `src/kapso/execution/search_strategies/generic/
strategy.py`, `ideation.py`, `implementation.py` and the orchestrator's
setup session (the session's `finish` call, the session id from the
adapter), `src/kapso/learning/mining.py` and `update_frame.py` (the
record's name, the refusal), `src/kapso/learning/trajectory_store.py`
and the graders (the record's name), `tests/`, `tests/harness_support.py`
(the orchestrator fixture), `docs/build/trace.mdx` (new),
`docs/build/run-and-watch.mdx`, `docs/reference/cli.mdx`,
`docs/reference/kapso-api.mdx`, `docs.json`, the examples' READMEs ("What
to look at").

Reads, never edits: the strategy's phases and budget (WP4), the feedback
generator (WP4), the harness modules (WP2), the experience package
(WP3), the plugin documents (WP7), `tests/semantic/` (WP9).

## Changes

1. **The session record.** `harness.json` becomes `session.json`, the
   staging's fields unchanged, written at session start by
   `StagedHarness.record()`; `StagedHarness.finish(result)` completes it
   at session end from the stream and the `CodingResult` (the digest
   above). Every site that stages a session calls `finish` after the
   session: the harness setup, lens planning, ideation (each member),
   implementation, verification, feedback, the mining lead, the update
   lead and the workers (the workers' record is one per crew, as WP3
   left it, with the digest of the launcher's log: Codex's own stream
   per worker). The harvest, the exam, the hindcast, the behaviour
   runner and the drift test read the new name. Tests: the record's two
   halves (start, finish) per host on fixture streams; a session with no
   stream (a fake agent) finishes with the fields null; the retired name
   joins `test_no_retired_names.py`.
2. **The transcript digests.** `transcripts.py`: `digest_stream("claude_code",
   path)` reads Claude Code's `stream-json` (`system/init` for the
   model and the mounted servers, `assistant` content for `tool_use`,
   `system/hook_response` for hooks with `permissionDecision`,
   `decision: block` and `additionalContext` counted, `task_started` for
   delegates, `result` for cost, duration and turns);
   `digest_stream("codex", path)` reads Codex's events (`item.completed`
   with `command_execution`, `file_change`, `mcp_tool_call` by server,
   `collab_tool_call` for delegates; no hook events, so `hooks` is null;
   no cost, so `cost_usd` is null). Tests: goldens on excerpts of the
   WP2 and WP3 proof streams (a Claude ideation session with bank reads,
   a Claude implementation session with hook denials and a delegate, a
   Codex implementation session with a `collab_tool_call`), committed
   under `tests/fixtures/transcripts/`; a malformed line raises.
3. **The record's lifecycle.** `build()` saves the record before the
   final checkout (branch and commit filled after it; a checkout that
   raises leaves the record with the candidate named and `commit`
   null, and the error in the status); `solve()` returns without
   publishing `done`; the facade publishes `done` after `solution.save()`
   and `failed(error)` from a `finally` with `sys.exc_info()` (Rule 2)
   for anything that raises after the status exists. Tests: on the
   patched engine, the status's `finished_at` is later than the record's
   write and `Solution.open` reads what `done` announced; a checkout that
   raises leaves `failed` with the error and a record; the orchestrator's
   own `failed` path unchanged.
4. **One line for the engine's errors.** `kapso.cli.main` installs
   `sys.excepthook` for the classes above: `Error: <message>` on stderr,
   exit 1; everything else unchanged. Tests: a `HarnessError` from a
   handler prints the line and no traceback; a `TypeError` prints the
   traceback. The detached child inherits it (the log shows the line).
5. **`kapso watch` completed.** The header renders the harness
   (`harness: trading 0.1.0 (83b6c0b60d6a)`) and the sources (one
   `served:` line per source from their labels) from the status file;
   a `failed` state shows its `error`; a campaign directory with no
   status and no process prints `stopped before writing a status; the
   log says why: <campaign>.log` (exit 1, no wait with `--follow`);
   `kapso watch` with no path lists `live_campaigns(registry)`, `--all`
   every registered one; `kapso inbox` reads the same list. Tests:
   renderer goldens for the three headers; the filter's cases (a gone
   directory, `done`, `done` waiting, `running` fresh with a live pid,
   `running` stale, `running` with the pid gone, `failed`); the listing's
   order and `--all`.
6. **`doctor --json`.** The shape above from the same `requirements_for`
   call; `--models` rows included. Tests: the shape, the exit code, no
   text on stdout beside the JSON.
7. **`kapso trace`.** `execution/trace.py`: `TraceView.open(campaign)`
   reads `solution.json` (or, before the build returns, `status.json`
   and `run_state.json` alone, marking the trace partial), the
   checkpoint's node history, every `session.json`, the verification
   directories, the serving record and pull log, the launch record; the
   attempts are ordered by node id with their parent; the lessons
   section joins the pull log's reads to the attempts by session and the
   ideas' `[card:<name>]` citations; the voided list is every node with
   `evaluation_valid` false or a `void` verdict, with the integrity error
   or the first finding; the failed-sessions list is every session kind
   whose records all ended `error`; the six answers are composed from
   those parts, each line naming its file. `explain()` renders the text
   with the same label column as `Solution.explain()`; `--attempt`
   prints one attempt with its session digest, verdict findings and
   judge text in full. `cli/trace.py` adds the verb. Tests: goldens on
   three fixture campaigns built from the proof archives' records (WP3's
   trading build with a void and a budget cut, WP3's churn build with a
   score, WP2's first machine with a delivered candidate; the fixtures
   hold the records, the session records, the verdicts and the pull
   log, never a stream); a campaign without a record renders partial; a
   directory that is not a campaign exits 1 by name.
8. **The learning status names a refused lead.** The mining frame reads
   the lead's session record after the first turn: `exit: refused`
   (the adapter's refusal signal, the safeguard line in the result)
   relaunches the lead once with the same prompt before the validator
   runs, and the learn status notes `lead refused by the model's
   safeguards; relaunched`; the repair rounds are spent only on a mined
   view. Tests: a fake lead whose first output is a refusal → one
   relaunch, the note, the repair count untouched; two refusals → the
   frame fails loud.
9. **The orchestrator fixture.** `tests/harness_support.py` gains
   `real_orchestrator(...)`: the real `OrchestratorAgent` with the fake
   LLM and agents and the real strategy factory over a fake strategy
   class registered for the test, so the construction path (knowledge
   search off, the factory's keywords, the status file's first write) is
   exercised; WP3's seam test moves onto it. Tests: construction without
   an embeddings key; the status file exists after construction with
   `harness` and `experience`.
10. **The adapters' loose ends.** The Codex adapter closes its stream
    file (the `ResourceWarning` of WP2's finding); the Claude Code
    adapter mints the session id (`new_session_id()`, a UUID) that the
    inbox gate and the staging share, and the two callers that minted
    their own use it. Tests: no `ResourceWarning` under `-W error` for
    the Codex fake run; the id reaches the inbox record and the session
    record alike.
11. **Docs.** `docs/build/trace.mdx` ("Read the record": the trace's
    sections, the six questions, `--json`, the session record's fields,
    where each file lives); `run-and-watch.mdx` (the header lines, the
    no-argument listing, the failed line, the stopped-before-status
    line); `reference/cli.mdx` (`kapso trace`, `watch` with no path and
    `--all`, `doctor --json`, the status file's `harness`, `experience`,
    `error`); `reference/kapso-api.mdx` (`Kapso.trace`); `docs.json`;
    the three examples' "What to look at" ending with `kapso trace
    campaign`; the coverage check counts the two new commands.
12. **The proof run** (below) and **the record of this package**: the
    review, the decisions, the findings, the master's row.

## Tests

- Syntactic: `test_session_record.py` (change 1), `test_transcripts.py`
  (2, goldens), `test_record_lifecycle.py` (3), `test_cli_errors.py`
  (4), `test_watch_header.py` and `test_live_campaigns.py` (5),
  `test_cli_doctor.py` extended (6), `test_trace.py` (7, goldens),
  `test_mining_frame.py` extended (8), `test_orchestrator_fixture.py`
  (9), `test_codex_agent.py` and `test_inbox_gate.py` extended (10),
  `test_no_retired_names.py` extended (`harness.json` as a session
  record, `SolutionResult.trace`), the docs coverage check.
- Proof run, on a fresh machine: the churn example built detached at a
  small budget (fifteen minutes, one experiment) with `--experience
  mine` over a bank carried from WP3's learn; while it runs, `kapso
  watch` with no argument lists it and the header shows the sources;
  after it, `kapso trace campaign` and `--json` archived, every attempt
  with its session digest, the pull log joined to the attempt, the six
  answers filled; `Solution.open` the moment `watch` says done. Two of
  S5's injections on the same fixture: a missing key (the launch
  refuses with one line, no campaign started) and a killed session (the
  implementation's CLI process killed mid-run: the attempt ends `error`
  in its session record, the campaign goes on or stops truthfully, the
  trace lists the session under the failures). S4's reading: Codex and
  Claude Code, each given the trace's text alone, answer the six
  questions; their answers checked against the record and recorded
  here. A Codex session's digest from the development box (the fresh
  machine's Codex key has no quota), on the trading example's
  implementation session.
- Semantic hooks: S4 (the trace legible without the agent) and S5 (two
  of five injections) runnable; the numbers recorded here; the full S5
  and the judged S4 are WP9's.

## Acceptance

- `kapso trace` on the three proof archives of WP2 and WP3 renders the
  sections above with no field empty that the record fills; `--json`
  round-trips through `TraceView`.
- Every staged session of a build on either host leaves one
  `session.json` with the digest filled as far as its host reports;
  no `harness.json` remains in the tree or the tests.
- `kapso watch` shows the harness and the sources of a running
  campaign, the error of a failed one, the log of one that stopped
  before its status; with no argument it lists only live or waiting
  campaigns.
- `kapso doctor --json` is parseable by a script that reads nothing
  else; `kapso` prints one line for the engine's own errors.
- `Solution.open` never fails on a campaign `watch` reports `done`.
- A refused mining lead is relaunched once and named in the status.
- The gate is green; the docs checks pass; the proof run is archived
  and recorded here with S4's two readings.

## Risks

- Codex's stream carries no hook events, so the digest's `hooks` is
  null on that host: the trace says "hooks: not reported by this host"
  rather than zero; the host-facts probe (WP2) stays the canary.
- The streams are large (a verification session's runs to megabytes);
  the digest is computed once at session end, never by the trace;
  `--attempt` reads the digest and the verdict, not the stream.
- Renaming `harness.json` touches the learning side (harvest, exam,
  hindcast, behaviour); the drift test and the three archives' fixtures
  catch a reader left behind.
- Moving `done` out of `solve()` changes when a watcher sees the end;
  the ordering test pins it, and the checkpoint's own `completed`
  status is unchanged.
- The excepthook must not swallow the traceback of a genuine bug: only
  the named classes print one line, and the test for a `TypeError`
  pins it.

## Review

The reviewers' findings and how each was answered.
