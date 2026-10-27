# WP9: the semantic suite

2026-10-27. Owner: the redesign's author. Branch `wp9-semantic-suite`
off `redesign` after WP7's merge (5cca2905). Size: L, spread over the
packages it reads: the suite is a release gate, not a per-commit check,
and every run costs hours and model spend.

## Scope

The semantic production tests of `docs/plans/semantic-production-tests.md`
made runnable and run once each: a simulated user from a persona card
driving the host turn by turn (the other vendor's CLI playing the
engineer), a judge from a third vendor grading transcripts and artifacts
against the rubrics, S1 (the cold engineer on the Python and CLI flow,
with its baseline on the released package), S2 proper (the plugin round
with the simulated user and the judge, both hosts), S4 (the trace read
without the agent, judged), S5 (five scripted injections), S6 (two builds,
the second served the first's lessons), and S3's third part, the author
test on a third domain (`pipeline-dbt`); one runner per test over the
fresh machine; one report per run. The learn's two fail-loud cases the
plugin round found (an unquoted scalar in a flow file; a crew that wrote
no report) are fixed first, since S6 needs a learn that completes.

**Not in scope.** S3's non-regression and abstraction parts (the harness
ports, WP8, parked until the owner says go). The release gate's full run
from the wheel to be released (WP11). The docs' pages for the suite
beyond `tests/semantic/README.md` (WP10). A skill, page or verb the suite
finds wanting is a finding here and a fix in its package (MASTER: "anything
that fails there reopens its package"), except where one line settles it
and the package is merged, which this package does and says.

## Interface

**Exposed.**

- `tests/semantic/personas/<name>.yaml`, a card with `name`, `role`,
  `expertise`, `knows`, `wants`, `patience`, `answers`, `pushes_back_when`
  (the README's contract); three cards: `ml-engineer` (exists),
  `data-engineer` (the dbt fixture's owner, for S1's second persona and
  the author test's reader), `second-engineer` (the teammate of S2's last
  step, terse, no context).
- `scripts/redesign/simulated_user.py`: `next_message(card, task, history,
  host_message, vendor) -> Optional[str]`: the persona's next message
  from the other vendor's CLI (`codex exec` when the host is Claude Code,
  `claude -p` when the host is Codex), or `None` when the persona is done
  (it says `DONE` alone). The prompt carries the card, the fixture's
  README, the whole history and the host's message; the reply is one
  message in the persona's voice. The transcript records both sides and
  the vendor's own session id.
- `scripts/redesign/judge.py`: `judge(rubric, transcript_paths,
  artifact_paths, vendor) -> dict`: dimension or question to `{score,
  evidence}` as JSON the judge must return whole (malformed JSON raises:
  no retry hides a judge that cannot follow the rubric); the rubrics as
  files under `tests/semantic/rubrics/` (`s2.md` five dimensions 1 to 5,
  `s4.md` six questions right or wrong with the answer, `s1.md` three
  questions). The vendor: Gemini (`gemini-4-argon` on Vertex through the
  LiteLLM bridge the campaign adapter uses) when the credit project is
  reachable, else the vendor that did not play either side; the record
  says which.
- `scripts/redesign/plugin_proof.py` gains `--user scripted|persona:<card>`
  (the scripted policies, as in WP7's round, or the persona for every
  answer) and `--judge <vendor>`; the record gains `user` and `judge`
  (`model`, scores) and keeps every other field. The test name becomes
  `S2` for a persona run, `S2-mechanical` for a scripted one.
- `scripts/redesign/s1_cold_engineer.py`: six tasks, each in Python then
  on the command line, each a fresh host session with the public docs
  (the clone's `docs/`) and the churn fixture and nothing else; per
  attempt `first_try` (the task's success predicate), `wrong_calls` (tool
  calls that errored before success), `minutes_to_launch`,
  `error_led_to_fix` (an errored call followed by the fixing call within
  one step); then the comprehension questions, graded by the judge
  against the record's own facts. `--package released` runs it on the
  released wheel and its docs, the baseline.
- `scripts/redesign/s4_reading.py`: a reader (each vendor) given `kapso
  trace`'s text and the campaign directory answers the six questions;
  the judge grades against the record (`solution.json`, the trace's
  JSON); per reader the six verdicts.
- `scripts/redesign/s5_injections.py`: five injections on the churn
  fixture, each a step with its own `inject` and `expect`: `provider-limit`
  (a `PATH` shim before the host CLI that answers the vendor's rate-limit
  error N times then execs the real CLI), `evaluator-crash` (WP6's),
  `missing-key` (the pause of S2), `killed-session` (WP6's), `full-disk` (a
  small tmpfs mounted at the campaign directory, root on the machine).
  Per injection: the state within one heartbeat, the inbox request's
  text (a variable or path, never a value), the diagnosis's class and fix,
  the resume's flag, the bank before and after; the user messages counted.
- `scripts/redesign/s6_experience.py`: two builds of the churn fixture at
  the same small budget, a learn between them, the second with `mine`;
  the anytime score per checkpoint from both status histories, the cards
  served and the ones an attempt used from the trace, the review's naming
  of them; the gap per checkpoint.
- `scripts/redesign/author_test.py`: a model author (each host) with the
  authoring guide, the design and the trading example writes a harness for
  `examples/pipeline-dbt`, logging every guess as a line; `kapso harness
  check`; the judge against the guide's rules; the guesses listed.
- `scripts/redesign/semantic.sh <s1|s2|s4|s5|s6|author> <host> [--machine
  <id>]`: provisions the machine (or reuses one), installs the wheel built
  from the branch, runs the test, fetches the record, judges on the
  development box, renders the report under `tests/semantic/reports/`,
  deletes the machine; the Codex half of S2 runs on the development box
  when the machine's Codex key is over quota, said in the record.
- `examples/pipeline-dbt`: a small dbt project on DuckDB (three sources,
  five models, tests, a seeded generator), with an evaluator (the share
  of tests passing on a fresh build plus a freshness check, one number)
  and a brief; the third domain for the author test.
- `tests/semantic/reports/<date>-<test>-<host>.md`, one per run, the ones
  cited here committed.

**Consumed.** `scripts/redesign/fresh_machine.sh` (WP0, extended in WP7);
`plugin_proof.py`'s hosts, steps and record shape (WP7); `kapso trace
--json`, `kapso watch --json`, the status history (WP6); `kapso learn`,
`load_experience`, the bank's serving and the pull log (WP3); the
examples and their generators (WP1, WP10); `Solution.open` (WP1); the
LiteLLM bridge (WP4's hosts table) for the judge; the authoring guide
(WP2).

## Ownership

Edits: `tests/semantic/` (the README, the personas, the rubrics, the
reports it cites, `report.py` for the new fields, `budgets.json` for S1,
S4, S5, S6 and the author test's steps), `scripts/redesign/` (the new
drivers, `plugin_proof.py`, `semantic.sh`, `README.md`),
`examples/pipeline-dbt/` (new), `examples/README.md` (the row),
`src/kapso/learning/mining.py` and the exam's crew runner (the two
fail-loud cases, with their tests), `docs/plans/redesign/` (this file,
DECISIONS, MASTER's row).

Reads, never edits: `src/kapso/**` beyond the two learning files (the
packages' owners; a finding here, a fix there), `plugin/**` (WP7; the same
rule), `examples/churn-first-build`, `examples/fraud-no-evaluator`,
`examples/trading` (the fixtures as they are; a generator fix is WP10's).

## Changes

1. **The learn completes on the two cases the round found.**
   `src/kapso/learning/mining.py`: the mining prompt's evidence grammar
   quotes a reference whole when its fragment holds a colon, and the
   validator hands a document that does not parse back to the crew as a
   finding for the repair round that already exists for a missing key
   (one more pass, then fail loud with the file named). The exam's crew
   runner: a crew session that ends without its file gets the one retry
   the build's sessions have, then fails loud naming the crew and the
   file. Tests: a flow file with the unquoted fragment is repaired and
   mined; a crew's missing report retried once; the second miss raises
   with the name.
2. **The persona driver.** `scripts/redesign/simulated_user.py` and the
   two new cards. Tests: the prompt carries the card, the README, the
   whole history (never clipped) and the host's message; `DONE` alone is
   the end; the reply's first line is the message; the vendor's CLI call
   is the other vendor's, by host.
3. **The plugin round with the persona and the judge.** `plugin_proof.py
   --user persona:<card> --judge <vendor>`; the scripted policies kept
   behind `--user scripted`; the transcript with both sides; `report.py`
   renders `user` and the judge's table (it already renders `judge`).
   Tests: the policy adapter answers from the persona and records the
   user's text; the record's new fields.
4. **The judge.** `scripts/redesign/judge.py`, the three rubrics, the
   vendor choice. Tests: the rubric's rendering, the JSON contract
   (malformed raises), the evidence quotes must occur in the transcripts
   (a quote that is not there fails the judge, not the test).
5. **S1.** `s1_cold_engineer.py`, its six task predicates, `--package
   released`. Tests: each predicate on a fixture transcript (a launched
   campaign's receipt; a deploy's call; a resume's second entry), the
   wrong-call count, the one-step rule.
6. **S4.** `s4_reading.py` and `s4.md`. Tests: the six answers extracted
   from a record (what won, the voided attempts, the cost) so the judge
   grades against facts, not its own reading.
7. **S5.** `s5_injections.py`, the shim, the tmpfs mount, the five
   `expect`s. Tests: the shim counts and execs; each `expect` on a fixture
   status history and inbox; the user-message count.
8. **S6.** `s6_experience.py`. Tests: the anytime series from two status
   histories, the gap, the served and used cards from a trace, the
   review's naming.
9. **The dbt fixture.** `examples/pipeline-dbt` with its generator,
   evaluator and brief; the examples' README row; the fixture's evaluator
   contract test (the one every fixture meets).
10. **The author test.** `author_test.py`, the guess log's grammar, the
    judge's rules. Tests: the log's parsing; the rules' rendering.
11. **The runner and the suite's README.** `semantic.sh`, the README's
    table and the runs' layout, `scripts/redesign/README.md`.
12. **The runs.** S1 (both packages, both hosts), S2 proper (both hosts),
    S4 (both readers), S5, S6, the author test (both hosts), each archived
    and recorded below with its report cited; the findings for the
    packages listed; MASTER's row.

## Tests

- Syntactic: `tests/test_simulated_user.py`, `tests/test_judge.py`,
  `tests/test_s1_cold_engineer.py`, `tests/test_s4_reading.py`,
  `tests/test_s5_injections.py`, `tests/test_s6_experience.py`,
  `tests/test_author_test.py`, `tests/test_pipeline_dbt_fixture.py`,
  `tests/test_learning_repair.py` (the two fail-loud cases), the semantic
  report's new fields in `tests/test_semantic_report.py`. Every provider
  boundary mocked; every test asserts the shape a driver produces or a
  fail-loud path.
- Proof run: each test's run on the fresh machine (the development box
  for the Codex half of S2 when the machine's key is over quota, said),
  from the wheel built from the branch, archived one file per run under
  `scripts/redesign/runs/wp9/<test>-<host>/`, its report under
  `tests/semantic/reports/`.
- Semantic hooks: this package is the hooks. The numbers recorded in the
  Proof run section: S1's twelve attempts per package and host, S2's
  budgets and five scores per host, S4's twelve verdicts, S5's five
  classes with their message counts, S6's gap per checkpoint, the author
  test's guesses.

## Acceptance

- The learn completes on the churn campaign from the plugin round's
  archive (the flow file with the colon, the crew's missing report) with
  the two repairs, each pinned by a test.
- S1: at least nine of the twelve attempts succeed first try on the
  branch's package and docs; every error message leads to its fix in one
  step; the comprehension correct on every verb; no judge finding of a
  surprising name. The baseline on the released package recorded beside
  it, whatever it reads.
- S2: every budget of `tests/semantic/budgets.json` met and every step
  complete on both hosts with the persona; every dimension at 4 or
  above; a dimension under 4 named with the judge's evidence.
- S4: the six questions answered correctly from the record alone by both
  readers.
- S5: each of the five classes handled with at most two user messages;
  the state truthful within one heartbeat; no value in a request.
- S6: the second build's anytime score at or above the first's at every
  checkpoint; the served cards and the used ones in the trace; the review
  names them.
- The author test: `check` green; zero structural guesses after the
  guide's fixes, each guess a sentence added to the guide.
- `semantic.sh` runs each test from one line, deletes its machine, and
  leaves a report; the reports cited here are committed.
- The gate is green; the docs checks pass; MASTER's row written.

## Risks

- **Spend and hours.** S2 proper is three hours of machine time per
  host; S6 is two builds and a learn; S1 is twelve sessions per package
  and host. The suite runs once here and once as WP11's gate; nothing of
  it is in the per-commit gate.
- **The persona's variance.** Two runs of the same persona differ; the
  bar is per run and the transcript is kept whole; a failure is re-run
  once with the same card, both runs recorded.
- **The judge's vendor.** Gemini on Vertex needs the credit project from
  the development box, where the judge runs over fetched transcripts; if
  it is unreachable the judge is the vendor that played neither side,
  and the record says so.
- **The learn's repairs may not be small.** If the two cases grow beyond
  the mining frame's repair round and one retry, S6 is reported blocked
  with the finding and the fix goes to the learning package's own
  pull request.
- **The provider-limit injection is a shim**, not the vendor's own limit:
  it exercises the adapter's handling of the error text the vendor
  returns, which the shim copies from a real one; said in the record.
- **The machine's Codex key quota** (WP7's risk, met) moves S2's Codex
  half to the development box, said in the record.
- **A full disk on the machine** is a tmpfs at the campaign directory,
  root on the machine; the engine's own status writer must survive the
  write failure to say so, which is the test.

## Review

(The cross-model review of this sub-plan: its findings and their
answers; the owner's standing go.)
