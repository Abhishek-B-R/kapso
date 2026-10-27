# Review: the semantic suite's fidelity to the real user experience (WP9)

You are reviewing the semantic production suite built in WP9 of the Kapso
redesign. The suite's job is to prove, on fresh machines, that Kapso
delivers a good **user experience** across its whole surface: a person
builds, watches, pauses, learns, shares experience, authors a harness,
and reads a finished run — through a coding-agent CLI (Claude Code or
Codex), not our test harness. Your job is to judge whether these drivers
and their metrics actually capture that experience and the behaviour a
user should expect, and to find where they measure the wrong thing, let a
real failure pass, or diverge from how the product actually behaves.

This is NOT a style review. Report only findings that would make the
suite mis-measure the user experience, miss a regression a user would
hit, or record something false. Rank them by severity. For each: the file
and line, what is wrong, the concrete user-facing consequence, and the
smallest fix.

## Read these

The design and the plan:
- `docs/plans/redesign/wp9-semantic-suite.md` (the sub-plan: scope, the
  interface, the thirteen changes, the acceptance, the risks)
- `docs/plans/semantic-production-tests.md` (the original design)
- `docs/plans/redesign/MASTER.md` (where WP9 sits; the engine/harness/task
  layering the suite exercises)

The one home and the verdict:
- `tests/semantic/suite.json` (per test: required steps per host, run-level
  bars, the judge spec; per step: kind and budgets; the knobs)
- `tests/semantic/report.py` (the verdict: step passing, bars, the judge,
  the advisory and exit codes)
- `tests/semantic/README.md`, `scripts/redesign/README.md` (the contracts)

The drivers (all under `scripts/redesign/`):
- `plugin_proof.py` (S2: the plugin round, the persona loop, the per-step
  intents, the pushback check, the served second-engineer build, the
  deploy parity, the evaluator contract test)
- `simulated_user.py` (the persona: the card, the prompt, the other
  vendor's CLI, the turn cap, DONE)
- `judge.py` (the two-pass judge, the rubric contract, the quote-at-
  location rule, adjudication, the unjudged outcome)
- `s1_cold_engineer.py` (S1: the cold engineer, the task table, the
  prerequisite campaign, the comprehension and flow counts)
- `s4_reading.py` (S4: the trace read without the agent; the fact sheet
  extracted from the trace and the delivered branch's history; the six
  questions)
- `s5_injections.py`, `status_timeline.py`, `enrichment_service.py` (S5:
  the seven failure injections; the timeline; "truthful within one
  heartbeat")
- `s6_experience.py` (S6: two builds, the learn, the anytime series, the
  gap, the served-and-used cards, the review)
- `author_test.py` (the author test: the guess grammar, the
  classification, the two rounds, the bar)
- `semantic.sh` (the runner: preflight, the fresh machine, the fixtures'
  venv, the archive, verify, delete, judge and report on the dev box)

The rubrics (the judge's words): `tests/semantic/rubrics/{s1,s2,s4,author}.md`.

The engine the drivers drive (read what you need to check a driver's
assumptions against the real behaviour): `src/kapso/execution/trace.py`
(the trace JSON the fact sheet and S6 read), `src/kapso/execution/
observability.py` (the status file the timeline samples: `best`,
`heartbeat_at`, `pid`, `state`, `phase`), `src/kapso/execution/
evaluation_integrity.py` and `src/kapso/execution/search_strategies/
base.py` (how an attempt is voided; the protected suffixes), `src/kapso/
execution/inbox.py` (the request/reply/continued protocol S5's missing-key
and WP7's inbox use), `src/kapso/cli/build.py`, `src/kapso/cli/watch.py`,
`src/kapso/cli/learn.py` (the flags and the detached status the drivers
call).

## The questions

1. **Does each driver drive the flow a real user lives?** The host is a
   coding-agent CLI reading a skill; the user talks to it in at most two
   or eight turns. Is anything scripted that a real user would have to do
   themselves, or asserted by the driver that the host should have earned?
   Is a step's "completed" predicate actually evidence the user got what
   they needed?

2. **Are the metrics the right proxies?** S1's first-try count and
   errors-led-to-fix; S5's "truthful within one heartbeat" and
   user-message window; S6's non-negative gap and cited lessons; the
   author test's structural-gaps-in-round-two. For each bar in
   `suite.json`, is it measuring the experience the design claims, or a
   shadow of it? Call out a bar that could pass while the user experience
   is bad, or fail while it is fine.

3. **Do the drivers match the engine's real contracts?** The status
   `best`/`heartbeat_at`/`pid` keys, the trace's `delivered`/`voided`/
   `attempts`/`lessons`/`cards` shapes, the inbox events, the integrity
   void, the detached launch and `--stop`/`--resume`. Where a driver reads
   or writes one of these, is the shape right? S5 moves the sealed labels,
   edits the protected evaluator in the campaign tree, fills a tmpfs — do
   these actually trigger the failure the injection claims, given how the
   engine seals, commits and verifies?

4. **Is the judge sound?** Two passes, the minimum binds, a straddle
   adjudicated, a malformed reply a recorded failure. Can a lenient or
   adversarial judge reply slip a bad run through, or sink a good one? Is
   the quote-at-location rule enforceable against the rendered material?

5. **Is the failure handling honest?** CLAUDE.md forbids try/except and
   fallbacks (validate, fail loud). Rule 6 forbids truncating anything
   into an LLM call (the persona's history, the judge's material, the
   classifier's guide). Rule 1 forbids config-like literals outside the
   config. Find any place a driver swallows an error, truncates an LLM
   input, or hardcodes a value that belongs in `suite.json` or the engine
   config.

6. **The runner and the archive.** Does `semantic.sh` provision, run,
   archive, verify and delete correctly? Is the fixtures' venv actually on
   the path the evaluator's subprocess resolves? Would a failed run be
   kept and legible? Is anything about the Codex-credit and advisory split
   unsound?

Write your findings to the output file, most severe first.
