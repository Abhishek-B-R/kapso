# The plugin's skills

2026-10-24, revised the same day. Companion to `kapso-plugin-user-flow.md`
(the settled plugin decisions) and `docs/research/redesign-status.md`
(step 7). A skill is a procedure the agent follows when a recognisable
situation arises: its description is the trigger, its body the steps, the
rules, and what it never does. The plugin ships six.

Two principles hold across all of them:

- **Kapso builds and verifies an objective end to end.** It is not a
  metric-improvement tool and the skills never present it as one. "Improve
  the AUC" is one shape of objective; "build a pipeline that produces X and
  prove it", "ship a model that meets Y", "make this pass the benchmark"
  are the same thing. A skill triggers on the intent to build something
  with a success criterion, not on the word "improve".
- **Proactive, then one message.** The agent discovers everything it can
  from the repository and the environment first, in silence, and then
  speaks once: what it found, what it proposes, what it needs. The user
  reacts with a word or an edit. No skill asks a question the repository
  can answer, asks twice, or sends more than two rounds before acting.

| Skill | Entry points | What it is | Budget |
|---|---|---|---|
| `kapso-setup` | `/kapso:setup`; any command when `doctor` is red | from a bare machine to a green `doctor`, a chosen harness, a first experience source | under five minutes, at most three questions, two link clicks |
| `kapso-build` | `/kapso:build`; "build X and verify it", "I need Y that meets Z", "improve W" | iterating the objective and its success criterion with the user, finding the data and the evaluation in the repository, then launching | at most two rounds, one question each, under five minutes including the evaluation's approval |
| `kapso-evaluation` | called by `kapso-build`; not user-invocable | builds the evaluator Kapso will protect, or audits the one found, runs the baseline, gets one approval | one approval message |
| `kapso-harness` | `/kapso:harness new`, `/kapso:harness improve <campaign>`; "write a harness for X" | authoring a harness from what the repository already shows, module by module, files not forms; improving one from a run's trace | first proposal within two minutes of reading; at most eight questions; a `check`-green harness in about twenty minutes |
| `kapso-review` | `/kapso:review <campaign>`; "what did it do", "why this one", "is it safe to merge" | reading a finished run: the winning diff, the evidence, what was voided and rejected, the next action | one message, then questions |
| `kapso` | `watch`, `inbox`, `resume`, `learn`, `deploy`, `doctor`, the `harness` and `experience` wrappers | operating a run, and diagnosing one that is slow or dead | the four-line handoff |

Every host gets the same six: Claude Code and Cursor as skills with
commands, Codex as skills invoked by name with the sidecar's prompts.
`kapso-evaluation` is marked not user-invocable on Claude Code and keeps
implicit invocation on Codex, so `kapso-build` can call it and nobody else
needs to.

## 1. `kapso-setup`

1. **Detect before asking.** node, python, git, `uv` or `pipx`; `kapso` and
   `kapso-mcp` on the path; which of `claude` and `codex` exist and are
   logged in; what `.env` holds, by variable name; whether the project has a
   `kapso-config.yaml` or a harness directory.
2. **Install what is missing** with the method the machine has (`uv tool
   install leeroo-kapso`, else `pipx`, else `pip` into the active
   environment, never the global Python); the CLIs via npm when absent.
   Say what was installed and where.
3. **Logins.** Start each missing login, show the link, wait.
4. **Keys.** Ask only for the keys the engineer's next step needs
   (Leeroopedia and an embedding key are optional); write them to `.env`
   without printing them.
5. **`kapso doctor`** until every required row is green; offer the one-token
   model probe.
6. **Orientation.** `kapso harness list` in one line per bundled harness;
   recommend one from what the repository looks like (dependencies, data
   files, notebooks); offer `kapso experience add mine`, and Leeroopedia's
   plugin line when no key is present.
7. **End with three lines:** what to run next on this repository, where the
   record will go, how to watch.

Rules: never a question the environment can answer; one summary at the end;
a failure names the row of `doctor` and the fix, and the skill retries after
the fix.

## 2. `kapso-build`

The objective is the user's; the skill's job is to make it buildable and
verifiable with as little talking as the repository allows.

1. **Listen for two things:** what the user wants to exist at the end, and
   how they would know it is done. Both may be vague ("a better churn
   model", "a working ingestion pipeline"); the skill proposes the
   measurable form rather than asking for it.
2. **Discover, in silence, in under a minute:** the repository's README and
   docs, data files and directories, notebooks and their metric cells, test
   suites, scripts named like evaluators or benchmarks, CI, dependencies.
   Infer the domain and the harness that fits (or confirm the loaded one),
   and read that harness's setup page: it says what a statement in this
   domain must record, and those become questions to the repository, not to
   the user. Note which experience sources exist (a bank with cards under
   this harness, a Leeroopedia key, an ingested index).
3. **Hand the evaluation to `kapso-evaluation`** (section 3): found, it is
   audited against the contract; absent, it is built from the criterion
   and the data found. Either way the baseline is measured when that is
   cheap. This happens before the user hears anything.
4. **One message.** What was found (data, evaluator, baseline, domain), the
   proposed brief as the file `kapso-brief.md` (objective in one line,
   measured by, baseline, target with its headroom reasoning, rules,
   budget with defaults, harness, experience), the evaluation's protocol
   for approval when one was built, and the single thing the user must
   confirm or edit. Short: the brief is the message, the prose around it is
   three lines.
5. **At most one more round.** The user edits a line or says go. A second
   round only when the edit changes the evaluation.
6. **Launch** detached with `--goal-file kapso-brief.md`; hand back the
   watch line, the harness and version, and the note that the user's own
   criterion can replace an assumed one at any time.

Rules: the criterion comes from the user or the repository, never invented;
proposals carry their evidence ("`evaluate.py` prints macro-F1 on
`data/dev.csv`, 1,204 rows"); never says it cannot proceed; never asks
twice; a one-file change with an obvious fix is done by hand, and the
skill says so instead of launching.

## 3. `kapso-evaluation`

Called by `kapso-build`, never from a menu. It owns the one thing the
product promise rests on: an evaluation Kapso can protect.

The contract an evaluator meets: one command that prints the metric on its
own line; a hold-out that lives outside the workspace the attempts can
reach; deterministic under a seed; a fast mode for development that keeps
the metric's meaning; fail-loud on a malformed submission; registered with
a version so no score crosses a version boundary.

1. **When an evaluator was found:** read it against the contract, run it
   once for the baseline, list the gaps (a hold-out inside the repo, a
   metric that is not printed, a random split without a seed). Fix the
   gaps in a copy the user approves, never in silence.
2. **When none was found:** build one from the success criterion and the
   data discovered: choose the split and the metric that match the
   criterion, write `kapso_evaluation/evaluate.py` and its fast mode, run
   it for the baseline, and write the protocol in five lines (data,
   hold-out, seed, metric definition, what counts as a pass).
3. **One approval message**, carried inside `kapso-build`'s message: the
   protocol, the baseline, the file path, and "approve, or edit a line".
   On approval the evaluation is registered as provided and protected from
   that moment.

Rules: proposes and builds, never waits for the user to describe a protocol;
never changes the user's own evaluator without the approval; says plainly
when a criterion cannot be measured from the data at hand and what data
would make it measurable.

## 4. `kapso-harness`

Two entry points: `new`, from a repository or an idea, and `improve`, from
a finished run.

**`new`.**

1. **Read before asking.** The repository's README and docs, Makefiles and
   task runners, notebooks, tests and linters, CI, scripts that recur,
   data layout, existing tool configurations (CLIs, MCP servers, API
   clients), and the user's own notes and runbooks when present.
2. **Propose a first harness in one message,** within two minutes: the
   domain in one sentence, the standing rules the repository implies
   (tests that always run, data that is never touched, conventions the
   docs state), candidate skills from recurring scripts and runbooks,
   servers from existing data access, checks from validators and tests,
   and the modules where the repository gave nothing. The tree is shown as
   it will be written. The user confirms or corrects.
3. **Write it,** then one question per module only where the repository
   was silent, each with the authoring guide's example as the prompt:
   setup, ideation, implementation, verification, feedback, learning,
   deployment. For each answer the agent chooses the cheapest form by the
   guide's ladder, a line on a page, a skill with a script, a delegate, a
   server, a hook, writes it, lists it, and says in one sentence why that
   form. Skip a module the domain has nothing to say about.
4. **`kapso harness check`**, clear the warnings, show the tree.
5. **Offer the probe run** on a task with a known answer, and hand over to
   `improve` when it finishes.

**`improve <campaign>`.** Read the run's trace: where attempts diverged,
which hooks fired, what verification voided, what feedback kept asking for.
Propose the smallest edit that would have prevented the divergence, in the
cheapest form, with the attempt that shows it. Apply on a word, bump the
version, re-run `check`.

Rules: nothing added without a named failure or domain rule; pages under
forty lines; a skill's description names the situation; secrets never in
files; the author can stop after any module with a valid harness. Tone:
show what was found and what it implies, in the author's own vocabulary;
one reason per suggestion; no questionnaires.

## 5. `kapso-review`

Triggers when a run has finished and the user asks what happened, why this
attempt won, or whether it is safe to merge; also the material for a
write-up.

1. Read the trace and the record: the tree, each attempt's verdict and
   evidence, the evaluation version it was measured under, hook decisions,
   delegate reports, what was consulted, what was spent.
2. **One message:** the winning branch's diff against the baseline in
   outline, the evaluation evidence with its version, the attempts that
   were voided and why, the ideas rejected and the reason, the risks the
   harness's reviewers flagged, the spend; then the next action with a
   recommendation: merge, cherry-pick, resume with more budget, or learn.
3. Answer questions from the record, never from memory of the run.

Rules: every number travels with the evaluation and version that produced
it; a voided attempt is reported as voided with its evidence, not hidden;
the recommendation is one line.

## 6. `kapso`

The operating procedure, built on `--detach`: launch when another skill
hands over, follow with `watch` in three lines, answer the inbox without
ever carrying a value, resume a dead run with one flag, learn from a
finished one, deploy with a target, `doctor`, and the `harness` and
`experience` wrappers (check, list, add, update, remove, export; add,
list, share).

It gains a **diagnosis section**: a slow run versus a stalled one by the
heartbeat and the phase (a long evaluation is not a stall); a dead run
classified from the log's last lines into provider limit, evaluator crash,
environment, disk, or a killed session, with the fix named before the
resume. And the rule that `/kapso:build` goes through `kapso-build`, and a
finished run's questions through `kapso-review`.

## 7. Measuring smoothness

The skill lab (`~/kapso-skill-lab`, eval-first, prompts plus rubrics plus
fixtures) runs three kinds of test per skill:

- **Trigger tests:** twenty phrasings of each request, including the
  build-and-verify phrasings that never say "improve"; the right skill
  loads, the wrong ones do not. Claude Code's `claude plugin eval` with the
  skill-use grader gives the number on that host; the lab covers Codex.
- **Outcome rubrics** against the budgets: setup ends green in at most
  three questions; `kapso-build` launches with every brief field present or
  marked unknown and an approved evaluation after at most two rounds; the
  evaluation meets the contract on a fixture repository with and without
  an existing evaluator; the harness passes `check` with every skill named
  on its module's page and no page over forty lines; the review names the
  winning branch, the evaluation version and a next action.
- **Annoyance rubric:** before a launch, at most three agent messages, at
  most two questions, no message over twelve lines plus the brief; every
  proposal carries the evidence it rests on.

A skill ships when all three pass on both hosts.
