# WP6: Observability

2026-10-25. Owner: the redesign. Branch `wp6-observability` off `redesign`
(after WP3's pull request #157). Size M. Revised after the review below.

## Scope

What a person, a model, or the plugin's skills can read of a campaign
without the agent that ran it, live and afterwards: every session's
record completed from both hosts' transcripts, one run entry per host
invocation, with the hooks that fired and what each decided, the
delegates asked and what they reported, the tools and gates used, the
duration, the cost where the host reports one, and how the invocation
ended; the record's lifecycle made truthful (the delivery inside the
orchestrator's protected region, the record written before `done`,
`failed` with the error from the first status write on, the engine's own
errors printed as their message with no traceback); `kapso trace`, the
campaign read after the fact as text and as JSON, the evidence for S4's
six questions laid out section by section; `kapso watch` completed (the
harness and the sources in the header, a launch receipt so a campaign
that died before its status says so, a no-argument listing of the
campaigns alive or waiting); `kapso doctor --json`; a refused mining lead
relaunched and named. S4 and S5 become runnable.

**Not in scope.** The budget's end and the judge's retry (WP4: the
finalisation reserve, the retry carrying its prompt); config without
modes and `--coding-agent` routing (WP4); the plugin's commands and the
`kapso-review` and `kapso harness improve` skills that read the trace
(WP7); the semantic suite's driver, judge and report (WP9: this package
makes S4 and S5 runnable and runs S4's reading and two of S5's five
injections by hand); `events.jsonl` and the OTel vocabulary, threshold
alerts, an OTLP exporter (the observability design's deferred list,
still deferred); a static page or notebook export of the trace (text and
JSON are what a reader and a script need); a merge verdict rendered by
the engine (the trace lays out the evidence; `kapso-review` makes the
recommendation, as its specification says); the evaluation archive's
own selection records (evaluation governance, read as they are); the
rename of `stopped_reason` and `requests` WP1 left open (declined: both
names are in the status file, the checkpoint and the API, and a rename
buys nothing).

## Interface

**Exposed.**

- **The session record**, `<campaign>/.kapso/sessions/<label>/session.json`,
  one per staged session on either host, with or without a harness. The
  staging writes it at session start with the fields WP2's record
  carried, unchanged: `module`, `host`, `harness` (the identity, or null
  without one), `session_dir`, `pages`, `skills`, `mcp_servers`,
  `agents`, `hooks` (the attachments staged), `prepared`, `stream`; and
  `runs: []`. The adapter appends one entry to `runs` at the end of each
  host invocation it makes for the session (a first turn, a resume, a
  retry), in its own `finally`, so a session that raises still records
  how far it got:

  ```
  {"started": "...", "ended": "...", "duration_seconds": 451.0,
   "cli_session_id": "f6b235b9-…", "model": "claude-opus-5",
   "exit": "success" | "error" | "timeout" | "paused" | "refused",
   "error": null | "the message",
   "cost_usd": 3.92 | null,          # null where the host reports none
   "turns": 37,
   "tools": {"Bash": 49, "Agent": 1, "Read": 1},
   "gates": {"gated-knowledge": {"bank_index": 1, "bank_get_card": 1},
             "market-data": {"snapshot": 1}},
   "hooks": [{"event": "PreToolUse", "name": "deny-snapshot",
              "decision": "deny", "reason": "…"}] | null,   # null where the host reports no hook events
   "delegates": [{"name": "lookahead-auditor", "status": "completed",
                  "usage": {"total_tokens": 13018, "tool_uses": 1, "duration_ms": 2234},
                  "report": "…the delegate's answer, in full…"}],
   "files_changed": ["strategy.py"],
   "last_message": "…the invocation's closing text, in full…"}
  ```

  `paused` is an invocation the inbox stopped (the adapters return
  `success=True` for it today, with `stopped_for_inbox` in the metadata;
  the run entry says `paused`). `refused` is an invocation whose answer
  was the model's safeguard refusal. `harness.json` goes (Rule 7).
- **The transcript digests**, `kapso.execution.coding_agents.transcripts`:
  `digest_claude(lines) -> dict` over Claude Code's `stream-json` events
  and `digest_codex(lines) -> dict` over Codex's `exec --json` events,
  the same keys as a run entry's `turns`, `tools`, `gates`, `hooks`,
  `delegates`, `last_message`, `cost_usd` and `model`, null where a host
  has nothing to say. The adapter hands each digest the lines its own
  invocation appended to the stream (it knows the offset it started
  at), so a resumed session's second run is digested alone; cost is the
  invocation's delta of the host's cumulative figure. Lines that are not
  events (merged stderr, warnings, the CLI's own text) are skipped, as
  the adapters' parsers skip them today; an event-shaped line that does
  not parse raises. What each host's events give: Claude Code's
  `system/init` (model, servers mounted), `assistant` `tool_use`
  (tools; `mcp__<server>__<tool>` as gates), `system/hook_response`
  (event, hook name, the decision and reason from `hookSpecificOutput`,
  the exit code and outcome), `system/task_started` with
  `task_type: local_agent` (a delegate, `subagent_type` its name) joined
  to its `task_notification` (status, usage) and to the `Agent` tool's
  result (the report), `result` (cost cumulative, duration, turns);
  Codex's `thread.started` (the thread id), `item.completed` with
  `command_execution`, `file_change`, `mcp_tool_call` (by server),
  `collab_tool_call` (a delegate), `agent_message` (the last one is the
  closing text) and `error`, `turn.completed` with its token usage (kept
  as `usage`), and no hook events, no cost.
- **The pull log's session key.** Every event the bank gate writes
  carries `session`, the label of the session the gate serves (the
  staging passes it to the gate's environment beside `KAPSO_BANKS`), so
  a read is attributed to the session that made it, however many run at
  once; `exposure_ladder` is unchanged.
- **The record's lifecycle.** `solve(..., finish=None)`: a callable the
  orchestrator runs inside its protected region after the search and
  before the terminal publish; the facade's `finish` checks the
  deliverable out and writes `solution.json`; the checkpoint is marked
  `completed` after `finish` returns, so a delivery that raises leaves
  `failed` in the status with the error, no record, and a checkpoint
  `--resume` can finish from. The benchmark runners pass no `finish` and
  keep today's behaviour. From the first status write on, whoever
  writes owns the failure: the strategy constructor publishes `failed`
  for an exception in its own setup after the status is born; the
  facade for the stretch between construction and `solve()` (the
  serving, the launch record); `solve()` from its first line, the
  harness setup included. `Solution.open` succeeds the moment `kapso
  watch` says `done`.
- **The launch receipt**, `<campaign>.launch.json` beside the log:
  `{pid, log, argv, started_at}`, written by `--detach` before the child
  starts. `kapso watch` on a campaign with no status reads it, whether or
  not the campaign directory exists yet: the pid alive is `starting (pid
  N, 12s ago; log: …)`; the pid gone is `stopped before writing a
  status; the log says why: <log>` (exit 1, and `--follow` stops
  waiting); without a receipt the line stays `no status yet … or nothing
  runs there`.
- **`kapso watch` completed.** The header renders `harness: trading
  0.1.0 (83b6c0b60d6a)` and one `served:` line per source from the
  status file's own fields. With no path it lists, newest first, the
  campaigns the registry knows that are alive or waiting, and the
  running `learn` and `experience` operations under
  `learning.status_dir`: one line each (`state`, `phase`, the heartbeat's
  age, `best`, the path); `--all` lists every one with its state;
  `--json` with no path prints `[{"path", "operation", "state", "phase",
  "heartbeat_age_seconds", "best", "stopped_reason"}]`; `--follow` and
  `--tree` with no path are refused by name. The rule, `live_campaigns`
  in `kapso.execution.inbox`: a status whose `OperationStatusView.alive`
  is not `False` (running or starting, with a fresh beat, or no cadence
  to judge by) or whose state is `done` with `stopped_reason:
  waiting_for_user`. The registry is written on every launch through the
  facade, inbox on or off, before the launch checks when the launch names
  an output directory, so a launch that dies at a check is listed by its
  receipt (the reader keeps a path with a receipt beside it). `kapso inbox` is unchanged: it lists requests,
  not campaigns. `--tree` is retired: the trace renders the attempts.
- **`kapso doctor [verb] --json`**: `{"scope", "version", "kapso" (the
  executable), "python", "config_path", "ok", "requirements": [{"label",
  "ok", "required", "origin", "fix", "detail"}]}`; exit 1 when a required
  item fails, as the text form; `--models` adds the live rows; `config`
  is reserved for WP4 (the effective config).
- **The engine's errors at the CLI.** `kapso` prints the message alone to
  stderr and exits 1 for the engine's own error classes (`BriefError`,
  `HarnessError`, `HarnessReferenceError`, `ManifestError`,
  `ExperienceError`, `ExperienceReferenceError`, `IngestError`,
  `EvaluationIntegrityError`, `PreflightError`, `GitReferenceError`,
  `InboxOpenError`, the `RunCheckpointError` family,
  `WorkspaceCheckoutError`, `GateCapabilityError`): a message may span
  lines (the preflight's is a report), it never carries a traceback; any
  other exception keeps its traceback, since it is a bug. The CLI's own
  refusals (`Error: …` lines) move to stderr with them. The detached
  child installs the same hook through `main()`, so its log shows the
  message.
- **`kapso trace <campaign> [--json] [--branch <name>]`** and
  `Kapso.trace(path) -> TraceView` (`view.data`, `view.explain()`,
  `view.attempts`, `view.delivered`), a pure reader. `--branch` narrows
  the attempts to one with its evidence in full. The text has the
  sections below; `--json` prints `data`:

  ```
  {"schema_version": 1, "campaign": "...",
   "state": "complete" | "partial",     # partial: the status is not done, or the record predates the checkpoint's last write
   "header": {"objective", "harness", "experience": [labels], "evaluator": {"version", "provenance"},
              "budget": {"elapsed_min", "total_min"}, "cost": {"usd", "coverage": "claude_code" | "all"},
              "stopped_reason", "stop_detail", "experiments", "rejected", "delivered": {"branch", "commit"}},
   "attempts": [{"node", "parent", "branch", "idea", "sessions": [{"label", "module", "host", "runs": [run entries]}],
                 "evaluation": {"score", "valid", "provenance", "integrity_error"},
                 "verification": {"verdict", "summary", "findings"} | null,
                 "judge": {"stop", "valid", "feedback"},
                 "cards": {"read": [...], "load_bearing": [...]}}],
   "lessons": [{"reference", "provenance", "head", "served", "read_by": {label: [cards]}, "load_bearing_by": {node: [cards]}}],
   "voided": [{"node", "branch", "reason", "evidence"}],
   "failures": [{"label", "module", "host", "exit", "error", "every_run": bool}],
   "delivered": {"branch", "commit", "base_commit", "files_changed", "verification", "feedback"}}
  ```

  The sections in the text: the header; the attempts, one block per
  node in order; the lessons; what was voided or rejected, each with its
  evidence; the sessions that failed, each with its error, and the kinds
  of which every run failed; the delivered candidate. No verdict line:
  the evidence for "safe to merge" is the delivered candidate's
  verification, its integrity, the hooks' denials in its sessions and
  the failures, each printed.

  Built with these keys beyond the sketch above (DECISIONS.md, "The
  trace's JSON carries keys the plan did not list"): top-level
  `sessions` (the sessions that belong to no attempt: the harness setup,
  a node in flight) and `branch` (the branch a view is narrowed to);
  `header.status` (`state`, `phase`, `error` of the status file) and
  `header.cost.unpriced_runs` (the Claude Code runs that ended with no
  cost figure); `attempts[].evaluation.output`, `attempts[].cost_usd`,
  `attempts[].duration_seconds` and `attempts[].cards.listed`;
  `lessons[].kind`. The delivered candidate's `files_changed` are the
  files its branch's diff names; a run entry's are the host's own
  account of what it wrote.
- **The summary's failed-sessions line.** `Solution.session_failures`
  (schema 5): the run entries that ended `error`, `timeout` or
  `refused`, each `{label, module, host, exit, error}`;
  `Solution.explain()` prints `Sessions failed: implementation on codex
  ×2 (Quota exceeded …)` after the experiments line, so a session kind
  that fails every time reaches the summary, as WP2 asked.
- **The refusal.** `CodingResult.refused` (the Claude Code adapter sets
  it when the invocation's answer is the model's safeguard refusal; the
  run entry's `exit` is `refused`); the mining frame relaunches a refused
  lead once (`learning.mining.refusal_relaunches: 1`, config) before the
  validator runs, and notes `lead refused by the model's safeguards;
  relaunched` through the learn status it is handed (`mine(...,
  status=None)`).
- **The session id.** `kapso.execution.inbox.new_session_id()` mints the
  UUID the inbox gate and the host share; the record's directory keeps
  its label (`generic_exp_0`, `verification/<branch>`,
  `ideation/iter1/claude_code`); the UUID is the run entry's
  `cli_session_id`.

**Consumed.** WP1's `Solution` and record, the status file and
`OperationStatusView`; WP2's staging (`StagedHarness`, `record()`,
`merged_agent_specific`), the verification directory (`verdict.json`,
`diff.patch`, `evaluation_output.txt`), the task statement; WP3's serving
record, pull log and `exposure_ladder`, the sources' labels, the node's
`cards_load_bearing`; the checkpoint's node history; the inbox registry
and `Request`; the preflight's `Requirement`; the two adapters' stream
artifacts and `CodingResult.metadata` (`elapsed_seconds`, `cost`,
`tool_calls`, `files_changed`, `cli_session_id`, `stopped_for_inbox`).

Frozen once reviewed; a change afterwards is a note here and a line to
WP4 (`doctor --json`'s reserved key, the budget's end reading the run
entries), WP7 (the skills read `kapso trace --json`, `watch --json` and
`doctor --json`) and WP9 (S4 and S5 read the trace and the status).

## Ownership

Edits: `src/kapso/execution/trace.py` (new), `src/kapso/cli/trace.py`
(new), `src/kapso/execution/coding_agents/transcripts.py` (new),
`src/kapso/cli/watch.py`, `src/kapso/cli/doctor.py`,
`src/kapso/cli/__init__.py` (the verb, the error hook),
`src/kapso/cli/common.py` (the receipt, the summary line, stderr),
`src/kapso/cli/build.py`, `harness.py`, `experience.py`, `learn.py`,
`deploy.py`, `inbox.py` (stderr for refusals), `src/kapso/execution/
observability.py` (the header, the listing, `--tree` retired),
`src/kapso/execution/inbox.py` (`live_campaigns`, `new_session_id`,
the receipt reader), `src/kapso/harness/staging.py` (the record without
a harness, `runs`, the session label in the gate's environment, the
record path in `agent_specific`), `src/kapso/execution/coding_agents/
base.py` (`CodingResult.refused`), the two adapters (the run entry in a
`finally`, the stream offset, the refusal, Codex's unclosed pipe),
`src/kapso/execution/search_strategies/generic/codex_ideation.py`
(`--json`, the run entry), `src/kapso/learning/update_frame.py` (the
workers' `--json`, their run entries), `src/kapso/learning/mining.py`
(the refusal relaunch, the status), `src/kapso/learning/trajectory_store.py`
and the graders (the record's name), `src/kapso/gated_mcp/gates/
bank_gate.py` and `src/kapso/learning/retriever.py` (the session key),
`src/kapso/learning/serving_launch.py` (the key in the serving
environment), `src/kapso/kapso.py` (`finish`, the failure ownership,
`Kapso.trace`, the registry on every launch, `session_failures`),
`src/kapso/execution/orchestrator.py` (`finish`, the protected region
from the first line, the completion save after `finish`),
`src/kapso/execution/search_strategies/base.py` (the constructor's
failure ownership), `src/kapso/execution/search_strategies/generic/
implementation.py` (the session id), `src/kapso/handles.py`
(`session_failures`, the summary line), `src/kapso/config.yaml`
(`learning.mining.refusal_relaunches`), `tests/`, `tests/harness_support.py`
(the orchestrator fixture), `tests/fixtures/transcripts/` and
`tests/fixtures/trace/` (new, with their generator), `docs/build/trace.mdx`
(new), `docs/build/run-and-watch.mdx`, `docs/reference/cli.mdx`,
`docs/reference/kapso-api.mdx`, `docs/reference/harness.mdx`,
`docs/harnesses/use.mdx`, `docs/harnesses/write.mdx`, `docs.json`, the
examples' READMEs.

Reads, never edits: the strategy's phases and budget (WP4), the feedback
generator's prompts and retry (WP4), the harness modules' content
(WP2), the experience package's grammar and store (WP3), the plugin
documents (WP7), `tests/semantic/` (WP9), the benchmark runners (they
call `solve()` as today).

## Changes

1. **The session record for every session.** `stage_harness` writes the
   record with or without a harness (`no_harness` becomes a staging with
   a record path, a stream path and `harness: null`); the record's name
   is `session.json`; `runs: []`; the record path rides to the adapter
   in `agent_specific["session_record_path"]` beside the stream path,
   per session, through `merged_agent_specific`. Readers: `test_harness_
   deploy_learn.py`, `test_harness_setup.py`, `test_trajectory_store.py`,
   `docs/reference/harness.mdx`, `docs/harnesses/use.mdx` and
   `write.mdx`, `examples/trading/README.md`; `harness.json` joins the
   drift test's patterns. Tests: a session without a harness has a record
   with `harness: null` and the stream path; the record's fields are
   WP2's, unchanged, plus `runs`.
2. **The transcript digests.** `transcripts.py` as the interface says.
   Tests: goldens on committed excerpts under `tests/fixtures/transcripts/`:
   the trading build's implementation stream (an `Agent` delegate with
   its notification and report, three `result` events with cumulative
   cost, `SessionStart` context), its harness-setup stream (the
   market-data gate calls), a Claude Code session captured by a scripted
   probe against the trading harness's `deny-snapshot` hook (a real
   `PreToolUse` denial; the probe script committed under
   `scripts/redesign/`), the implementation and harness-setup streams of
   WP2's development-box Codex campaign (`codex exec --json`:
   `command_execution`, `mcp_tool_call` on `market-data`, two
   `collab_tool_call` spawns, `turn.completed` usage, Codex's own
   diagnostics merged in); a stream with merged diagnostics skips them;
   a broken event raises; a slice that starts at the second `init`
   digests the second run alone with its cost delta.
3. **The run entries.** Both adapters append the entry at the end of
   every invocation in a `finally` with `sys.exc_info()` (Rule 2: the
   error propagates; the entry records it): the offset of the stream
   before the invocation, the digest of the lines after it, the
   `CodingResult`'s own fields where they exist (`elapsed_seconds`,
   `files_changed`, `cli_session_id`, `stopped_for_inbox` → `paused`,
   the deadline kill → `timeout`), the digest's where they do not; cost
   from the digest's delta (null on Codex). The Claude Code adapter sets
   `CodingResult.refused` and `exit: refused` on the safeguard refusal.
   The Codex adapter closes `process.stdout` (the `ResourceWarning` of
   WP2's finding). Tests: fake processes on both adapters: a success, an
   error raised mid-invocation (the entry has `exit: error` and the
   error, and the exception reaches the test), a timeout, an inbox pause,
   a refusal; a resume appends a second entry; `-W error` passes.
4. **The two Codex paths outside the adapters.** `run_codex_ideation`
   runs `codex exec --json`, streams to `stream.jsonl` under the member's
   session record directory, and appends its run entry at its end;
   the update crew's launcher adds `--json` and the frame appends one
   entry per worker from the worker's log to the crew's record. Tests:
   the member's record after a fake `codex exec`; the workers' record
   after a fake launcher.
5. **The pull log's session key.** The staging passes
   `KAPSO_SESSION=<label>` to the gate's environment for every session
   that serves banks; the bank gate stamps `session` on every event;
   `exposure_ladder` ignores it. Tests: the gate's events carry the
   label; the serving plan's environment per session.
6. **The record's lifecycle.** `solve(finish=)`: the protected region
   starts at `solve()`'s first line (the harness setup inside it); the
   facade's `finish` does the checkout and writes the record; the
   checkpoint's `completed` save moves after `finish`; `done` is
   published after it, as today, with its payload. The strategy
   constructor owns a failure in its own setup after the status is born
   (`finally` + `sys.exc_info()`, `failed` if not terminal); the facade
   owns the stretch between construction and `solve()` the same way,
   reading the status from the strategy and checking `terminal` before
   publishing. Tests: on the patched engine, `Solution.open` succeeds
   once the status says `done` and the record's write precedes
   `finished_at`; a checkout that raises leaves `failed` with the error,
   no record, and a checkpoint `--resume` accepts; a harness setup that
   raises publishes `failed`; a serving staging that raises publishes
   `failed`; the runners' path unchanged (`solve()` without `finish`
   publishes `done`; `test_run_checkpoint.py` and the others that pin
   `done` after `solve()` stay as they are).
7. **The launch receipt and the watch header.** `--detach` writes the
   receipt; `kapso watch` reads it when no status exists; the header
   renders the harness and the sources; `--tree` is retired. Tests: the
   receipt's shape; the three `watch` lines (starting with a live pid,
   stopped with the pid gone, no receipt); renderer goldens for a status
   with a harness and two sources, and for `failed`.
8. **The listing.** `live_campaigns(registry, status_dir)` and `kapso
   watch` with no path, `--all`, `--json`; the registry written on every
   launch. Tests: the filter's cases (`starting` fresh, `running` fresh
   with a live pid, `running` with no `/proc` and a fresh beat, `running`
   stale, `running` with the pid gone, `done` plain, `done` waiting,
   `failed`, a gone directory); the listing's order and shapes;
   `--follow` and `--tree` refused with no path.
9. **`doctor --json`.** Tests: the shape, the exit code, the `--models`
   rows, nothing else on stdout.
10. **The error hook and stderr.** Tests: a `HarnessError` from a handler
    prints its message on stderr with no traceback and exits 1; a
    `PreflightError` prints its whole report; a `TypeError` prints the
    traceback; the CLI's own refusals are on stderr; a detached child's
    log carries the message (a subprocess test over `kapso build
    --detach` with a bad harness reference).
11. **`kapso trace`.** `execution/trace.py` and `cli/trace.py` as the
    interface says; `Kapso.trace`; `Solution.session_failures` and the
    summary line; the examples' READMEs end "What to look at" with
    `kapso trace campaign`. Tests: goldens on three fixture campaigns
    under `tests/fixtures/trace/`, generated by the committed
    `tests/fixtures/trace/build_fixture.py` from an archived campaign
    (it keeps the records, the verdicts, the serving record and the
    pull log, rebuilds every `session.json` with its run entries by
    running the digests over the archived streams, drops the streams,
    and rebases paths), run over WP3's trading build (a void, a budget
    cut, served cards, a delegate), WP3's churn build (a score under no
    harness, no sessions with a harness) and WP2's first machine (a
    delivered candidate with a verification): the three archives are the
    fixtures' sources and the generator reproduces them byte for byte; a
    campaign without a record renders partial from the status and the
    checkpoint; a resumed campaign whose record predates the checkpoint
    renders partial; a directory that is not a campaign exits 1 by name;
    `--json` round-trips through `TraceView(data)`.
12. **The refusal relaunch.** `mine(..., status=None)` and the facade's
    learn chain passing its `LessonStatus`; `refusal_relaunches` in the
    config; the hermetic tests in a new `tests/test_mining_refusal.py`
    (the existing `test_mining_frame.py` is live, skipped by the gate):
    a fake lead whose first result is `refused` → one relaunch, the
    note, the repair count untouched; two refusals → the frame fails
    loud; an ordinary error naming the word is not a refusal.
13. **The orchestrator fixture.** `tests/harness_support.py` gains
    `real_orchestrator(...)`: the real `OrchestratorAgent` with the fake
    LLM and agents, the real factory and the real `GenericSearch` over a
    seeded workspace with repo memory disabled, so construction writes
    the real status file; WP3's seam test moves onto it. Tests:
    construction without an embeddings key; the status after
    construction carries `harness` and `experience`; a constructor
    setup that raises publishes `failed`.
14. **Docs.** `docs/build/trace.mdx` ("Read the record": the sections,
    the six questions and where each answer sits, `--json`, the session
    record and its run entries, where each file lives);
    `run-and-watch.mdx` (the header, the listing, the receipt's lines,
    `kapso trace` as the next step); `reference/cli.mdx` (`kapso trace`,
    `watch` with no path, `--all`, `--json`, `--tree` gone, `doctor
    --json`, the status fields `harness`, `experience`, `error`);
    `reference/kapso-api.mdx` (`Kapso.trace`, `Solution.session_failures`);
    `reference/harness.mdx`, `harnesses/use.mdx` and `write.mdx` (the
    record's name and its runs); `docs.json`; the coverage check.
15. **The proof run** (below) and **the record of this package**: the
    review, the decisions, the findings, the master's row.

## Tests

- Syntactic: `test_session_record.py` (1), `test_transcripts.py` (2,
  goldens on captured excerpts), `test_run_entries.py` (3),
  `test_codex_paths_records.py` (4), `test_bank_pull.py` extended (5),
  `test_record_lifecycle.py` (6), `test_watch_header.py` and
  `test_launch_receipt.py` (7), `test_live_campaigns.py` (8),
  `test_cli_doctor.py` extended (9), `test_cli_errors.py` (10),
  `test_trace.py` (11, goldens from the generator), `test_mining_refusal.py`
  (12), `test_orchestrator_fixture.py` (13), `test_no_retired_names.py`
  extended (`harness.json`, `--tree`), the docs coverage check.
- Proof run, on a fresh machine with WP3's learned bank carried over:
  the trading example built detached with `--harness` and `--experience
  mine`, forty-five minutes and two experiments, so the record holds
  served cards, a delegate, the harness's hooks and a verification; while
  it runs, `kapso watch` with no argument lists it and the header shows
  the harness and the source; after it, `kapso trace campaign` and
  `--json` archived, every attempt with its runs, the pull log joined by
  session, the cards the judge found load-bearing, `Solution.open` the
  moment `watch` says done. The churn example built detached with two
  of S5's injections: the implementation's CLI process killed mid-run
  (the run entry ends `error`, the attempt fails, the campaign goes on
  to its next or stops truthfully, the trace lists it under the
  failures) and the evaluator made to crash on one attempt (its
  evaluation output and the rejection's reason in the trace). A
  deliberately broken launch (`--harness` naming nothing) to show the
  receipt's line and the one-line error in the log. S4's reading: Codex
  and Claude Code, each given the trace's text and the campaign
  directory, answer the six questions; their answers are graded against
  the record and recorded here, with the claims they got wrong. A Codex
  session's run entry from the development box (the fresh machine's
  Codex key has no quota), on the trading example's implementation
  session.
- Semantic hooks: S4 (the trace legible without the agent) and S5 (two
  of five injections) runnable; the numbers recorded here; the full S5
  and the judged S4 are WP9's.

## Acceptance

- `kapso trace` on the three fixture campaigns renders every section
  with no field empty that the record fills; `--json` round-trips; the
  generator reproduces the fixtures from the archives.
- Every staged session of a build on either host, with or without a
  harness, leaves one `session.json` with a run entry per invocation,
  filled as far as its host reports; no `harness.json` remains in the
  tree, the tests or the docs.
- A session that raises leaves its run entry with the error; a resumed
  session has two entries; a refused one says so.
- `kapso watch` shows the harness and the sources of a running
  campaign, the error of a failed one, the receipt's line for one that
  stopped before its status; with no argument it lists only live or
  waiting campaigns and the running learns and ingests.
- `kapso doctor --json` is parseable by a script that reads nothing
  else; `kapso` prints the engine's errors as their message on stderr
  and nothing else.
- `Solution.open` never fails on a campaign `watch` reports `done`; a
  delivery that fails leaves a checkpoint a resume can finish.
- The summary names the sessions that failed; a refused mining lead is
  relaunched once and named in the status.
- The gate is green; the docs checks pass; the proof run is archived
  and recorded here with S4's two graded readings.

## Risks

- Codex's stream carries no hook events and no cost: the run entries
  say null, the trace says "hooks: not reported by this host" and
  prints the cost with its coverage; the host-facts probe stays the
  canary for Codex hooks.
- The digests read only the invocation's slice; a stream a host rotates
  or truncates would digest short, and the entry's `turns` against the
  `CodingResult` would show it.
- The record's name touches the learning side; the drift test, the
  fixture generator over the three archives and the harvest tests catch
  a reader left behind.
- Extending the protected region and adding the constructor's and the
  facade's `finally` blocks must not publish twice: each checks
  `terminal` first, and a test raises inside each region.
- The error hook must not hide a bug: only the named classes print the
  message alone, and the `TypeError` test pins the traceback.
- Capturing the hook-denial and Codex fixtures needs two short live
  sessions on the development box; the probe script makes them
  repeatable.

## Review

Codex (`gpt-6-astra`, xhigh) and Claude Code (`claude-opus-5`) reviewed
the first draft (`scripts/redesign/runs/wp6-plan-review/`). The findings
and how each was answered in this revision:

### Codex

| Finding | Answer |
|---|---|
| P1 the lesson-to-attempt join has no key: the pull log records no session | the staging passes the session's label to the gate (`KAPSO_SESSION`) and every event carries `session` (change 5); the trace joins by it and prints the judge's `cards_load_bearing` per node; the `[card:…]` regex over ideas is dropped |
| P1 the digest discards hook decisions and delegate reports; configured hooks overwritten | the run entry keeps per-hook rows (event, name, decision, reason) and per-delegate rows with the report in full; the staging's `hooks` list is untouched, the runs live under `runs` |
| P1 the failure wrapper cannot cover the setup failure; a second terminal transition masks the error | ownership from the first status write: the constructor's own `finally` after the status is born, the facade's between construction and `solve()`, `solve()`'s from its first line with the harness setup inside; each checks `terminal` before publishing |
| P1 removing `done` from `solve()` strands five runners and a pinned test | `done` stays in `solve()`; the facade passes `finish=` (the checkout and the record inside the protected region, before the terminal publish); the runners pass nothing |
| P1 `finish(result)` has no contract for a session that raises | the adapter writes the run entry in its own `finally` with `sys.exc_info()`; no call-site `finish`; the exception propagates |
| P1 a staging record is not one host invocation; a paused session is not a success | `runs: []`, one entry per invocation (first turn, resume, retry), digested from the invocation's own slice of the stream; `exit: paused` for the inbox stop |
| P1 several staged paths produce neither transcript format | the ensemble members and selector run `codex exec --json` and record their runs; the update crew's launcher adds `--json` and the frame records one entry per worker (change 4); the feedback generator needs no change since its adapter writes the entries |
| P1 a resumed or failed-delivery campaign presented as finished | `state: partial` when the status is not `done` or the record predates the checkpoint's last write; a delivery that raises writes no record at all (the `finish` design) |
| P2 the stopped-before-status line lacks its evidence | the launch receipt beside the log, with the pid and the actual log path; the line reads it |
| P2 the liveness rule differs from the view and excludes `starting` | the rule is `view.alive is not False`, `starting` included, through the existing properties |
| P2 the liveness filter applied to the inbox hides requests | `kapso inbox` is unchanged; the filter serves `kapso watch` alone |
| P2 delivery failure unrecoverable through resume | the checkpoint's `completed` save moves after `finish`; a failed delivery leaves a resumable checkpoint |
| P2 the parser misidentifies events and leaves cumulative cost undefined | the digest reads `task_type: local_agent` only, joins the notification and the `Agent` result, takes the invocation's slice and the cost delta, skips non-event lines as the adapters do |
| P2 the failure list hides timeouts and refusals; the summary printer unassigned | the failures section lists every run that ended `error`, `timeout` or `refused`, grouped, with `every_run` flagged; `Solution.session_failures` and the summary line (the interface) |
| P2 "safe to merge" and "rejected" have no contract; evaluator provenance per score | no verdict line (the evidence is printed per section); `voided` is a node with `evaluation_valid` false or a `void` verdict, with its reason; each attempt's evaluation carries its own provenance; unselected ensemble ideas are out of the record and out of the trace |
| P2 session records absent without a harness | change 1: the record is written for every session |
| P2 the one-line error conflicts with the preflight's report and the detached child | "the message alone, no traceback", on stderr; the child installs the hook through `main()`; the preflight that runs in the child shows in its log |
| P2 the refusal signal and status interface do not exist | `CodingResult.refused` set by the adapter; `mine(..., status=None)`; the count in the config |
| P2 the JSON contract not frozen for WP7 | the trace's JSON keys, the listing's JSON and `doctor --json` are written out in the interface |
| P2 the fixture plan cannot reproduce its evidence; no denial example in the archives | a committed generator rebuilds the trace fixtures from the archives by running the digests; the denial and the Codex excerpts come from a scripted probe, committed |
| P2 two tests would leave their regressions untested | the refusal tests in a hermetic module; the fixture constructs the real `GenericSearch` with repo memory off |
| P2 the proof cannot establish breadth; S4 self-confirming | the trading example with the harness and the bank is the main proof; the churn build carries the injections; the readers get the trace and the record and are graded against the record |
| P2 the rename inventory misses docs and tests | listed in change 1; the archives are historical documents, the fixtures regenerated |
| P2 unknown spend becomes a total | the cost line carries its coverage (`claude_code` when any Codex run exists) |
| P3 `--attempt` is a vocabulary mismatch | `--branch` |

### Claude Code

| Finding | Answer |
|---|---|
| P1-1 no session record without a harness; the proof has none | change 1; the proof's main build has the harness and the churn build shows the harness-less record |
| P1-2 the field list is wrong and drops the harness identity | the record's fields are WP2's, unchanged (`harness` included), plus `runs` |
| P1-3 "a malformed line raises" raises on both hosts' real streams | non-event lines are skipped as the adapters do; only an event-shaped line that does not parse raises |
| P1-4 two Codex session kinds have no `item.*` stream | change 4 |
| P1-5 the pull log has no session; `cards_load_bearing` exists | change 5 and the load-bearing cards per node in the trace |
| P1-6 moving `done` strands callers and can publish twice | `finish=` inside `solve()`; `done` stays; the `terminal` check before every publish |
| P1-7 `failed` without the status object is not implementable | the owners are where the object is: the constructor, the facade (through the strategy), `solve()`; no second `BuildStatus` |
| P2-1 the pre-checkout record invents a delivery state | no provisional record: the checkout and the record happen inside `finish`; a failure leaves `failed` and no record |
| P2-2 the digest re-derives numbers three sources hold | precedence stated per field: the `CodingResult` for elapsed, files, the session id and the pause; the digest for hooks, delegates, tools, gates, turns and the cost delta |
| P2-3 counters do not serve the skills | per-hook and per-delegate rows with reasons and reports |
| P2-4 `task_started` is not the delegate signal | `task_type: local_agent` with `subagent_type`, verified on the WP3 archive (one `local_agent`, four `local_bash` in the implementation session) |
| P2-5 a resumed session appends to one stream | one run entry per invocation, digested from its own slice |
| P2-6 `exit: refused` has no source; the frame has no status channel; the count is a knob | `CodingResult.refused`; `mine(..., status=)`; `refusal_relaunches` in the config |
| P2-7 `watch` cannot tell dead from starting | the launch receipt |
| P2-8 the filter hides `starting` and breaks without `/proc` | `alive is not False` |
| P2-9 the inbox's meaning changes | `kapso inbox` unchanged |
| P2-10 no machine-readable listing; `doctor --json` thin; WP4's key | `watch --json` with no path; `version`, `kapso`, `python`, `config_path` in the doctor's JSON; `config` reserved for WP4 |
| P2-11 the trace's JSON keys unspecified | written out |
| P2-12 `watch --tree` duplicates the trace | `--tree` retired (a decision) |
| P2-13 the one-line error mangles the report; stdout vs stderr | the message alone, however many lines; errors on stderr throughout |
| P2-14 the failed-session list empty in the case that created it | the adapters record every invocation, handled failures included; the summary line |
| P2-15 the trace goldens cannot be regenerated | the committed generator over the archives |
| P2-16 S4 circular; the chosen S5 injection is not S5's | no answers section; the readers get the trace and the record; the injections are the killed session and the evaluator crash, the launch refusal shown beside them |
| P3-1 the rename inventory wrong in both directions | corrected in change 1 and Ownership |
| P3-2 `new_session_id` in the wrong module; label vs UUID | `kapso.execution.inbox.new_session_id`; the label names the directory, the UUID is a run field |
| P3-3 the Codex warning is the pipe, not the file | `process.stdout` closed |
| P3-4 per-session cost reopens a settled decision | null on Codex, the coverage printed with the total (a decision) |
| P3-5 `kapso trace` is the word WP1 retired | kept: the master names the verb, and the trace renders the record, not a log; a note in DECISIONS |
| P3-6 a merge verdict in a reader | removed; the evidence is printed, the recommendation is the skill's |
| P3-7 the fixture's status write is not on its path | the fixture constructs the real `GenericSearch` |
| P3-8 nothing points at the trace | the summary and the done frame end with `kapso trace <campaign>` |
| P3-9 `--all` is not every campaign | the registry written on every launch; the learn and ingest statuses listed from `learning.status_dir`; taking `watch --all` off the deferred list is a decision |
| P3-10 Ownership contradicts itself and MASTER | rewritten; the staging and the pull log are this package's asks of WP2 and WP3, both merged |
