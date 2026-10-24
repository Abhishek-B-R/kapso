# Semantic production tests

2026-10-24. The ordinary suite checks that the code does what the code
says. These tests check that Kapso does what an engineer expects: the flow
is smooth and intuitive in Python and on the command line, the plugin makes
a full round with a real-feeling user and earns its attention, the two
initial harnesses are abstract enough to hold their benchmarks and the
authoring guide is complete enough to write one from. Three were asked
for; a simulation of the whole flow added three more (section 5).

## 1. Common machinery

- **Fixture repositories** under `tests/semantic/fixtures/`, each small
  enough for a ten-minute build with a tiny budget: `churn-with-evaluator`
  (tabular, `evaluate.py` present), `fraud-notebook-only` (a metric in a
  notebook, no evaluator), `empty-wish` (a README and nothing else),
  `trading-strategy` (the author's fixture), `pipeline-dbt` (the third
  domain). Each carries the recorded result of its baseline.
- **A simulated user**: a model from the other vendor than the agent's
  (Codex plays the engineer when Claude Code is the host, and the reverse),
  with a persona card: role, expertise, patience (the number of questions
  before it gets terse), what it knows about its repository, what it wants,
  how it answers (short, sometimes wrong, sometimes changing its mind). It
  drives the host CLI turn by turn, and the transcript is recorded.
- **A fresh machine, never the development box.** The suite provisions a
  GCP machine in the benchmark project, installs the released package or a
  wheel built from the branch, the CLIs and the plugin from the marketplace
  line, and runs every test there, so nothing the development checkout
  happens to have (logins, caches, paths, half-installed tools) can make a
  flow look smoother than a user will find it. The machine is deleted
  after the report is written; S3's benchmark runs use the GPU boxes the
  benchmarks already use.
- **A judge**: a model from a third vendor when one is available, grading
  transcripts and artifacts against the rubric; beside it, hard metrics
  computed from the transcript (messages, questions, minutes, lines) and
  from artifacts (brief fields, `check` output, the evaluator contract).
- **Cadence**: the full suite per release and after any change to a skill,
  a page, CLI help text or a public doc; S3's benchmark runs when a
  harness changes. The suite is a release gate, not a per-commit check,
  because it costs hours and model spend.
- **Report**: one markdown per run with the budgets table, pass or fail per
  test, the transcript paths and the judge's findings, kept under
  `tests/semantic/reports/`.

## 2. S1: the Python and CLI flow is smooth and intuitive

**The cold engineer.** A model with no Kapso knowledge, given only the
public docs, in a sandbox with the package installed and a fixture
repository. Six tasks, each attempted in Python and then on the command
line from a clean session: build with an existing evaluator; build without
one; load a harness by name and build; deploy the result; learn from it;
resume a run that was killed. Afterwards, comprehension questions: what
did each call do, what did it return, where is the record.

Hard metrics: first-try success per task; wrong calls before success; time
to the launch; whether each error message led to the fix within one step.
Judge: do the names say what the calls do (nothing surprising, such as a
loader that ingests); does the whole Python flow fit in twelve lines and
the CLI flow in six commands; is anything needed that the docs do not say.

Bar: at least nine of the twelve attempts succeed first try; every error
message leads to its fix in one step; comprehension correct on every verb;
no judge finding of a surprising name.

## 3. S2: a full round with the plugin and a simulated user

The scenario, on Claude Code and on Codex, on the fresh machine:

1. install from the marketplace line; `/kapso:setup` to green;
2. `/kapso:build` on `churn-with-evaluator`: discovery, evaluation audited,
   one message, "go", detached launch at a tiny budget;
3. "how is it going" during the run; an injected pause (a server
   referencing a key `.env` lacks) answered through the inbox;
4. completion; `/kapso:review`; "is it safe to merge";
5. `/kapso:learn`; `/kapso:deploy` to local and one call against it;
6. `/kapso:build` on `fraud-notebook-only`: the evaluation built and
   approved; and on `empty-wish`: candidate criteria proposed;
7. `/kapso:harness new` on `trading-strategy`: the proposal from the
   repository, the module questions, `check` green, the probe run;
8. `/kapso:harness improve` from that run;
9. `/kapso:experience share` to a local bare remote; a second simulated
   engineer installs the plugin, loads the shared bank and builds.

Hard metrics: the budgets of `kapso-plugin-skills.md` per skill (messages,
questions, minutes, lines); every step completed; artifacts correct (brief
complete, evaluator meets the contract, `check` green, the deployed call
answers, lessons banked and served to the second engineer).

Judge rubric, five dimensions scored 1 to 5 from the transcript: proactive
(findings the user did not know, with evidence); clear (the user's
vocabulary, one reason per suggestion, no jargon the persona lacks); not
annoying (no repeated or answerable question, no message over twelve lines
plus the brief); engaging (the user says yes or edits one line rather than
re-explaining; the judge predicts the user would return); return on
attention (what the user got, a verified result, a reusable harness,
banked lessons, a deployed call, against the minutes of attention it cost).

Bar: every budget met; every step complete; every dimension at 4 or
above, on both hosts.

## 4. S3: the harnesses are abstract enough, and the guide is complete

Three parts.

**Non-regression.** One representative task per benchmark through its
harness at the benchmark's recorded budget and model: a banked RelBench
task, an MLE lite competition, an AHC problem, an IOAI practice task. The
score lands within noise of the recorded result or above it. The trace
shows the harness at work: pages in the prompts, skills opened, the
delegate's reports, hooks fired.

**Abstraction.** The scan: no dataset or task name, metric value, quota,
deadline or foreign path in a harness. The task swap: a task from the
domain the benchmark does not contain runs with no harness edit (a Kaggle
tabular competition; a second AHC problem; an IOAI 2025 task; a different
RelBench dataset). An edit needed to run is recorded as a finding against
the harness or the guide and fixed at the source.

**Guideline completeness.** A model author with only the authoring guide,
the design and the trading example writes a harness for `pipeline-dbt`,
and every point where it had to guess or would have asked is logged. The
result passes `check`; a judge reviews it against the guide's rules (pages
under forty lines, every skill named on its page, no task value, the
ladder respected). Each logged guess is a sentence missing from the guide,
and the guide is fixed before the test is re-run.

Bar: non-regression on all four; zero scan hits; zero edits on the task
swaps; zero structural guesses in the author test.

## 5. What the simulation added

Walking the whole flow with the three tests in hand, from install to the
team's second engineer, left these moments untested:

**S4: the trace is legible without the agent.** The one-liner promises
every step traced, and the agent is not always there to narrate. A reader
who did not watch the run, a model first and a sampled human later, gets
only the `kapso trace` output and the record, and must answer: what won,
why, what was voided and on what evidence, what was rejected and why, what
it cost, whether it is safe to merge. Bar: all six answered correctly from
the record alone.

**S5: the failure paths are as smooth as the happy path.** S2 injects one
pause; production runs die in more ways. Five scenarios, each a scripted
injection on the churn fixture: a provider limit mid-run, an evaluator
crash, a missing key, a killed session, a full disk. Judged on: the state
is truthful within one heartbeat (a pause is not a failure, a stall is not
a slow evaluation), the inbox request names the variable or path and never
a value, the diagnosis names the class and the fix, the resume is one
flag, and nothing banked is lost. Bar: every class handled with at most
two user messages.

**S6: experience pays.** The product says it learns from runs; the test
says whether the next run starts ahead. Two builds on the same fixture
family at the same small budget, the second with `mine` loaded. The
second's anytime score is at or above the first's at every checkpoint, the
trace shows which lessons were served and which an attempt used, and
`kapso-review` names them. Bar: a non-negative gap at every checkpoint and
cited lessons; the stronger claim waits for the A/B that is still running
elsewhere.

Two more were considered and folded into the tests above rather than added:
integrity under tampering (an attempt that edits the evaluator or reads the
hold-out is voided and the trace shows it) runs inside S3's non-regression
and S5; deployment parity (the deployed call answers the same as the
evaluated solution on a sample) is the last check of S2's deploy step.

## 6. Order of building the suite

1. The fixtures and the persona cards, with the simulated-user driver and
   the judge harness, grown from the skill lab at `~/kapso-skill-lab`.
2. S1 on the CLI and the API as soon as build step 1 exists; it is cheap
   and catches naming before it ships.
3. S2 as the plugin's skills land, one scenario step per skill.
4. S4 and S5 with step 6 of the build order (`kapso trace`, the record
   fields), since both read the record.
5. S3 with the harness ports; S6 once `load_experience` serves.
