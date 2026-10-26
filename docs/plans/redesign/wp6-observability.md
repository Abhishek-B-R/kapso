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
  `sessions[].hooks_staged` (what the session was staged with, so "no
  hook fired" is told from "no hook could"); `lessons[].kind`. The
  delivered candidate's `files_changed` are the
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

- Syntactic: `test_harness_staging.py` (1, the record for every session), `test_transcripts.py` (2,
  goldens on captured excerpts), `test_run_entries.py` (3),
  `test_codex_paths_records.py` (4), `test_bank_pull_session.py` (5),
  `test_record_lifecycle.py` (6), `test_watch_header.py` (7, the receipt
  included), `test_live_campaigns.py` (8),
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

## Proof run

**The fresh machine, `kapso-fresh-wp6`** (`e2-standard-4`, Ubuntu
24.04, created 22:05 UTC on 2026-10-25, the wheel from `cc4190d8` as a
`uv` tool, Claude on the shared token, Codex on the API key), the
trading harness and the trading and churn examples from the branch with
their data generated on the machine, `mcp` pinned below 2, WP3's learned
bank carried over as the machine's own (`mine  ~/.kapso/bank.git  head
a9ddad3d302d  15 cards  no remote`). `kapso harness check` printed `check
ok (7 skills, 2 agents, 2 servers, 6 hooks)`; `kapso doctor build`
passed its six checks and `kapso doctor build --json` printed the same
six rows as data (`scope kapso doctor build, ok true, version 0.7.10`,
exit 0).

**The first launch died at a check, and the receipt did not say so.**
The fixture had carried the development checkout's gitignored
`evaluation/result.json` again (WP3's finding, the other way round);
the launch refused it before any session, and the detached child's log
carried the one line change 10 promised, `Error: …/evaluation/result.json
is the evaluator's own output, left by an earlier run; … Remove it and
launch again.`, with no traceback. But `kapso watch campaign` two
seconds later said `no status yet at campaign — the campaign is still
starting…`, and `kapso watch` with no path listed nothing: the receipt
was read only once the campaign directory existed, which a launch that
dies at a check never creates; the registry was written after the
orchestrator's construction; and its reader dropped a path with no
directory. Fixed in `2faa4078` (the receipt read regardless, a launch
with an output directory registered before its checks, the reader
keeping a path with a receipt beside it; a decision in DECISIONS.md),
the wheel rebuilt and reinstalled, the stale file removed, and the build
relaunched at 22:12.

**The trading build, 22:12 to 22:59 UTC**, `kapso build --harness
../harnesses/trading --experience mine`, forty-five minutes and two
experiments. Within three seconds `kapso watch campaign` showed the
header the plan asked for:

```
STARTING ♥ 3s ago      pid 5250
harness: trading 0.1.0 (83b6c0b60d6a)
served: mine at a9ddad3d302d, measured by you
phase: setup — 0.1m elapsed
```

and `kapso watch` with no path listed it (`RUNNING   build
harness_setup      20s ago  best -        /home/ubuntu/fixture/examples/trading/campaign`).
`kapso trace campaign` while it ran rendered partial (`— partial: the
campaign is running (phase harness_setup)`, the header from the status,
`harness_setup … no run recorded`, `15 cards served … read by nobody`).
`kapso watch --follow` returned the moment the campaign was done and
`Solution.open` in the same breath returned the record (`branch None,
score None, stopped_reason budget_exhausted, 3 session failures`).

What the campaign did: two attempts, both scored by the provided
evaluator (Sharpe 1.9233 and 1.8647), neither delivered. The first's
verification session wrote a `valid` verdict with no findings (the
lookahead scan clean, the number reproduced byte-identically) and then
ran past its ten-minute deadline waiting on its auditor; its judge
session answered `stop true, valid, 1.9233` in a first run whose last
message was a stray alarm note without the tags, so the engine asked
again in a fresh session that had no context and answered that it had
nothing to judge, which is the answer the record kept. The second's
verification was cut at its clamped deadline (380 s) and stayed
unverified; its judge's first run was killed at the sixty-second floor
and the retry answered likewise. `budget_exhausted` at 46.1 of 45
minutes, `2 rejected`, $16.21. The summary's new row read `Sessions
failed: feedback on claude_code ×1 (Claude Code CLI exceeded its 60.0s
deadline …); verification on claude_code ×2 (… 380.5 s …)`. Every one of
these facts is on the trace (the archive:
`scripts/redesign/runs/wp6/campaign1.tgz`, with the trace's text and
JSON beside the campaign): the two feedback runs per attempt (`run 2 …
0.1 min  $0.055  1 turns`), the verification timeouts with the verdict
that survived one of them, the five cards read in iteration 1 and the
fifteen listed in both, the lookahead-auditor delegates with their
reports in `--branch`, the `SessionStart` hook in every session, the
judge's `cards_load_bearing` parsed as a card named `false` (a finding
below).


**The Codex session, on the development box, 22:33 to 22:50 UTC.** The
trading example with its harness, the implementation on Codex
(`search_strategy.params.implementation_cli: codex`,
`implementation_model: gpt-5.6-sol` in a config copy whose homes lie
under a scratch directory), twenty minutes and one experiment: the
setup session, the implementation and the verification ran on Codex,
the ideation and the judge on Claude Code. The attempt scored a Sharpe
of 1.7295, the verifier found it `valid`, the judge stopped the campaign
on it, and it was delivered (`generic_exp_0 @ 4f37ae900580`). The trace
(`scripts/redesign/runs/wp6/devbox-codex.tgz`) renders the Codex runs
as the plan said a Codex host reports: `codex  success  1.5 min  712k
in, 5.4k out tokens  1 turns  tools command_execution 10, file_change 2
gates gated-knowledge 4, market-data 4  hooks not reported by this host
collab wait 1`, the campaign's cost line `$4.379 (Claude Code sessions
only; Codex reports no cost)`, and the delivered files from the
branch's diff. A first launch of the same build with `--coding-agent
codex` had run every session on Claude Code (a finding below;
`devbox-claude.tgz`), and its judge's retry on the sixty-second floor
is the same shape as the machine's.

**The churn build with S5's injections, 23:00 to 23:43 UTC (the
machine's clock)**, `kapso build --experience mine`, no harness, sixty
minutes and three experiments, with an injector armed beside it: ninety
seconds into the first implementation phase it sent `SIGTERM` to the
Claude Code CLI (`23:23:40 sent SIGTERM to 13518`) and then touched the
marker that makes the fixture's evaluator raise once. The record and
the trace (`scripts/redesign/runs/wp6/campaign2.tgz`):

- The killed session is one run entry, `generic_exp_0  claude_code
  error  1.7 min  cost n/a  0 turns  tools Bash 7, Write 1  CLI exited
  with code 143`, and the campaign went on truthfully: node 0 completed
  with no score, the judge said `a complete, correct artifact exists but
  was NEVER SCORED … Do not rebuild it — validate it`, iteration 2
  started at 49% of the budget, and the second attempt scored 0.8508 on
  the provided evaluator, cleared the 0.85 target and was delivered
  (`generic_exp_1 @ 6bc3e8c47d9f`, `goal_achieved`, $6.39). The summary
  read `Sessions failed: implementation on claude_code ×1 (CLI exited
  with code 143)`; the trace lists it under SESSIONS FAILED and the
  delivered candidate's `failures  none in its sessions`.
- The evaluator's crash was absorbed by the implementer: the second
  attempt ran the evaluator itself first, met the injected
  `RuntimeError`, ran it again (its judge's words: "Three evaluator
  invocations ≈ 8 s total (one absorbing the documented one-shot crash
  injection …)"), so the engine's own evaluation of the attempt
  succeeded. The injection reached a session, not the engine's
  evaluation; the engine-side crash stays for WP9's S5 to inject
  differently (a crash the engine's evaluation meets would show in the
  attempt's `evaluation.output` and the judge's rejection, the path the
  trace already prints).
- A gap the trace exposed and the branch fixed: without a harness, the
  judge's sessions had records but no run entries
  (`feedback/generic_exp_0  claude_code  no run recorded`); the judge
  attached its staged session only when a harness gave guidance. Fixed
  in the commit after the proof run; the archive keeps the gap as it
  was.

**A detached launch that dies at a check, on the reinstalled wheel.**
With a stale `result.json` in the churn example's evaluation directory,
`kapso build … --output campaign-dead --detach` returned the launch
banner and the pid; one second later `kapso watch campaign-dead` said
`stopped before writing a status; the log says why:
…/campaign-dead.log` (exit 1), the log held the one line (`Error:
…/evaluation/result.json is the evaluator's own output, left by an
earlier run; … Remove it and launch again.`, no traceback), and `kapso
watch --all` listed it `STOPPED   build      -                        -
best -        …/campaign-dead` above the two `DONE` campaigns, `--json`
giving `"state": "stopped"`. A launch whose `--harness` names nothing
is refused in the parent before it detaches (`Error: no directory
…/nowhere (and ./nowhere is not a bundled name or a git reference); the
forms are: …`, exit 1): nothing to watch, by design.

The machine was deleted at 23:49 UTC after 1.77 hours ($0.24); the run's
local record (`scripts/redesign/runs/wp6/`) holds the create and install
logs, three wheel hashes, the run logs and the two archives beside the
development box's two.

**S4's first reading, the trading build.** Both readers were given the trace's text and JSON, the campaign directory (streams and bank clones left out) and the log, and the brief in `s4/campaign1/brief.md`. Graded against `run_state.json`, the session records, the verdicts, the pull log and the log.

| Question | Codex (gpt-6-astra, xhigh) | Claude Code (opus-5) | The record |
|---|---|---|---|
| 1 What won | nothing delivered; the two attempts' own Sharpe 1.9233 and 1.8647; measured by the provided evaluator, no registered evaluator — correct | the same, plus the evaluator's hash pin and the verifier's byte-identical reproduction — correct | `solution.json` branch/commit/score null; `evaluation_output` 1.9233 / 1.8647 |
| 2 Why | both judges invalidated for "no attempt to analyse", then the time budget — correct; found the first judge's valid/1.9233/stop answer in the log — correct | the same, and traced the mechanism: run 1's last message was a stray alarm note without the tags, the engine re-asked in a fresh session that had no context — correct | `sessions/feedback/generic_exp_0/session.json` runs[0] (success, no tags in the last message), runs[1] (a different `cli_session_id`, 1 turn, $0.055) |
| 3 Voided, evidence | nothing voided by the verifier; node 0 `valid` with no findings, node 1 unverified; the trace's section lists "judged not valid", not verifier voids — correct | the same, with the verifier's evidence listed and its three non-voiding caveats — correct | `verification/generic_exp_0/verdict.json` valid, findings []; `verification/generic_exp_1/` has no verdict |
| 4 Rejected, why | both by the judge's invalidation; no integrity failure; the timeouts distinguished — correct | the same; node 1 also unverified — correct | `evaluation_integrity_error` "" on both; `rejected_candidates` 2 |
| 5 Cost | $16.210, split 9.874 / 4.774 / 1.562; one killed run with no cost; `coverage: all` is not "every run costed" — correct, a fair reading of the label | the same, plus the phase split (verification 35%), delegates in tokens only, money never a budget — correct | `cumulative_cost`, `cost_by_component`; `feedback/generic_exp_1` runs[0] `cost_usd` null |
| 6 Safe to merge | would not approve: nothing delivered, the first attempt's verification conflicts with its judge, the second unverified — a defensible conclusion from the evidence | the code change on `generic_exp_0` is safe on the evidence (verification strong, integrity clean, no denial in its sessions) but nothing names the commit to merge; `generic_exp_1` is not — a defensible conclusion; the missing commit is a real gap | no node carries its commit; the only denial in the campaign was the setup session's |

No claim either reader made was wrong against the record. Both had to open files for the same two facts the trace did not carry: why the judge's session had a second run (the first run's answer lacked the tags; the retry ran with no context), and that the setup session's `deny-web-fetch` hook denied a shell command, which the log shows and the session record does not (Claude Code reports a blocking PreToolUse hook as the tool's error result, not as a `hook_response` event — the digest read only the latter; fixed below). Both read `coverage: all` as weaker than it sounds, and both noted the brief's 75-minute budget line against the launch's 45 (the flag wins, by design; the record shows both).

What the readings changed in the trace: a hook's denial reported through the tool result is now a hook entry (`decision: deny`, the reason the hook printed); the header's cost line names the runs that ended with no cost figure; the cards line shows how many cards a session listed beside the ones it read. Left for later packages: the judge's retry must leave its reason in the record (WP4, with the retry itself); a node should record the commit it was evaluated at (WP4's checkpoint, or WP1's record); the judge's `cards_load_bearing` parsed `false` as a card (WP4).

**S4's second reading, the churn build with the injections**
(`scripts/redesign/runs/wp6/s4/campaign2/`, the trace re-rendered by the
branch at `b6d1b1df`'s parent, the records as the machine's wheel wrote
them). The same brief, the same two readers.

| Question | Codex (gpt-6-astra, xhigh) | Claude Code (opus-5) | The record |
|---|---|---|---|
| 1 What won | `generic_exp_1 @ 6bc3e8c4…`, AUC 0.8508 on the 3,000 held-out rows by the provided evaluator, reproduced by the judge — correct | the same, with the full SHAs, the brief's target and baseline, and the judge's re-run found in the log — correct | `solution.json`; `campaign.log` 5095–5122 |
| 2 Why | the reproduced score over the bar, the integrity audit clean, nothing better unbanked, the margin inside noise — correct | the same, section by section of the judge's words — correct | `attempts[1].judge` |
| 3 Voided, evidence | nothing, because no verifier ran: absent checks, not passing verdicts — correct | the same; no `.kapso/verification/` directory at all — correct | `harness: null` |
| 4 Rejected, why | nothing rejected; the one failure is node 0's implementation killed (`exit 143`) and kept valid by its judge, who told the next iteration to validate it — correct | the same, and the engine's own failures that rejected nothing (the repo-memory bootstrap on a Codex quota, the fallback reconstruction) — correct | `rejected_candidates: 0`; `session_failures[0]` |
| 5 Cost | $6.389, split by attempt; the killed run unpriced; the feedback phases' cost present in the checkpoint though the judge sessions recorded no run — correct | the same, by phase from the checkpoint; the three failed Codex repo-memory calls unpriced; `coverage: all` beside `unpriced_runs: 1` read as self-contradictory — a fair reading of the label | `cost_by_component`; `unpriced_runs: 1` |
| 6 Safe to merge | yes for the stated task, with limited assurance: no verification layer, no hook policy, the judge's reproduction real — defensible | yes for `predict.py`, not for the commit as it stands: it carries build output and a new file inside the evaluator's directory; the clean hook line is uninformative because no hook was staged — defensible, and the sharper reading | the delivered diff's files; `sessions/*/session.json` `hooks: []` |

No claim either reader made was wrong against the record. What they
had to open files for: the judge sessions' runs (`no run recorded`, the
gap fixed in `b6d1b1df` after the run), the full SHAs and the brief's
fields (the trace prints twelve hex digits and the objective's first
line), the meaning of `integrity provided; intact` (the manifest in the
checkpoint), and whether `hooks none fired` meant no denial or no hook
(the latter: the trace now says `none staged` in that case). Both named
what the record cannot settle: who sent the `SIGTERM` (the injector,
outside the record by design), and the killed run's own spend.


## Findings for later packages

- **The judge's retry must leave its reason in the record** (WP4, with
  the retry carrying its prompt). Three times in the proof run a judge
  session had two runs: the first answered in full and ended on a stray
  message without the tags (the trading build's node 0: `stop true,
  valid, 1.9233`, discarded), or was killed on the sixty-second floor at
  the budget's end (node 1 of the same build, both dev-box builds), and
  the engine asked again in a fresh session with none of the context,
  which answered that it had nothing to judge; the record kept the
  second answer. The trace shows the two runs and the second's words;
  it cannot show why the second ran, because nothing in the record
  says. The retry should record its reason (`tags missing`, `deadline`)
  and the run entry should carry it, and the retry should resume the
  session rather than start one (both S4 readers named this as the one
  fact they had to dig out of the log).
- **`--coding-agent codex` does not reach the implementation host**
  (WP4, the `--coding-agent` routing). The generic strategy's host is
  its own parameter (`search_strategy.params.implementation_cli`,
  default `claude_code`); a build launched with `--coding-agent codex`
  ran every session on Claude Code while its launch record said
  `coding_agent: codex`. The flag must route the implementation or
  refuse by name.
- **The judge's `cards_load_bearing` parses `false` as a card** (WP4,
  the judge's contract). With nothing served, or nothing load-bearing,
  the judge wrote `false`; the parser treats only `none` as empty, so
  the node carries a card named `false` and the trace prints
  `load-bearing  1: false`. Accept `false` and `null`, or have the
  prompt ask for `none`.
- **A node should record the commit it was evaluated at** (WP1's record
  or WP4's checkpoint). The delivered candidate's commit is in the
  solution record alone; an attempt that was not delivered has a branch
  but no commit anywhere in the record, so a reader who wants to merge
  the verified attempt of a campaign that delivered nothing (the trading
  build's node 0, verified `valid`) cannot name what to merge.
- **The budget's end, again** (WP4's finalisation reserve): every
  campaign of the proof run that reached its time budget spent its last
  minutes on a verification cut at its clamped deadline and a judge on
  the sixty-second floor, and rejected a scored attempt for it. The
  trace now shows exactly this; the fix is the reserve.
- **The brief's budget line and the launch's flag both stand in the
  record** (WP1, a wording): the trading brief says `minutes=75` and the
  launch set 45; both readers noticed and neither could tell which was
  meant. The record is right (the flag wins); the trace could say so on
  the budget line.
- **The hosted gate's reads are not in the pull log** (WP3): a hosted
  source's calls appear in the sessions' gates columns only, by tool,
  never by page; `lessons` says so. If the hosted gate ever reports what
  it served, the trace's `read_by` is ready for it.
- **A killed session's fallback reconstruction misdiagnosed the loss**
  (WP4, the session-end facts): node 0 of the churn build, whose
  implementation was killed by the injector, got a reconstructed
  `technical_difficulties` saying its artifact was permanently lost,
  while the branch held it at `d9cb8e5` and the next attempt scored it.
  The reconstruction should read the branch before it concludes.
- **Build output committed inside the evaluator's directory** (the
  evaluation governance, WP4): the delivered churn commit carries
  `predictions.csv`, `kapso_evaluation/result.json` and a new
  `kapso_evaluation/eval_profile.md`; the integrity manifest pins
  `evaluate.py` and `private_dir.txt`, so a new file beside them passes.
  Whether a candidate may add files to the protected directory is a rule
  the governance should state; the trace's delivered files list shows
  it either way.
- **The fixture's `evaluation/result.json` rode into a proof machine a
  second time**: the development checkout keeps the evaluator's own
  output (gitignored) and an `rsync` of the example carries it. The
  examples' `.gitignore` is right; the proof scripts now exclude it;
  the launch's refusal did its job both times.

## Built

Branch `wp6-observability` off `redesign` at `588b44b6`, the commits
below, each with its tests and the gate green at every one (the last
gate before the proof run's commits: 1,616 passed, 27 skipped, 2
deselected; the docs coverage check 43 commands and methods, the
snippet check 6 quoted files, `mint validate` passing).

| Commit | What landed |
|---|---|
| `fb2dae8b`, `2a68543a` | the sub-plan, and its revision after the review with the planned decisions |
| `0c841816` | the transcript digests, one parser per host, over committed excerpts of real streams (change 2) |
| `caf1163d` | a session record for every session, harness or not, with `runs` (change 1) |
| `119edde7` | the adapters record every invocation in their own `finally`; the refusal (change 3) |
| `cba0488d` | the Codex paths outside the adapters record their runs; the pull log carries the session (changes 4 and 5) |
| `6d7ab482` | the record's lifecycle: the delivery inside the protected region, failure ownership from the first status write (change 6) |
| `b57c7947` | `kapso watch` completed: the header, the launch receipt, the no-path listing; `--tree` retired (changes 7 and 8) |
| `f93c43bf` | `kapso doctor --json`; the engine's errors print their message on stderr (changes 9 and 10) |
| `b0c71667` | `kapso trace`, `Kapso.trace`, `Solution.session_failures`, the fixture generator and three fixture campaigns with goldens (change 11) |
| `04605d32` | a refused mining lead launched again and named in the learn status (change 12) |
| `35a83e38` | the real orchestrator over the real strategy as a test fixture; the seam test on it (change 13) |
| `cc4190d8` | the docs: "Read the record", the CLI and API references, run-and-watch, the examples' pointers (change 14) |
| `2faa4078`, `92b43316` | the proof run's first finding: a launch that dies at a check is told by its receipt and listed by the registry |
| `48cd7f3a` | the proof run's second finding: a run's files from the host's own account, the delivered files from the diff |
| `60428655`, `04635a1b` | what S4's first reading asked: a blocking hook's denial in the record, the unpriced runs on the cost line, the cards listed beside the cards read; the keys noted in the plan |
| `b6d1b1df` | the proof run's third finding: the judge's runs recorded without a harness |
| `5ff0b4b5` | what S4's second reading asked: whether any hook was staged, why nothing was served |
| the last commit | the proof run's record: this section, the findings, this table |
