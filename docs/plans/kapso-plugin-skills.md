# The plugin's skills: onboarding, the brief, the harness, operating

2026-10-24. Companion to `kapso-plugin-user-flow.md` (the settled plugin
decisions) and `docs/research/redesign-status.md` (step 7). The October
plan had one skill, the operating procedure, with commands as its entry
points. Three flows decide whether Kapso feels smooth, and each is a
procedure of its own, so the plugin ships four skills.

| Skill | Entry points | What it is | Budget |
|---|---|---|---|
| `kapso-setup` | `/kapso:setup`; any command when `doctor` is red | from a bare machine to a green `doctor`, a chosen harness, a first experience source | under five minutes, at most three questions, two link clicks |
| `kapso-brief` | `/kapso:build`; "improve X", "get the metric above Y" | what the engineer has, turned into the brief `build` takes; proposes, never gates | under two minutes, at most one question |
| `kapso-harness` | `/kapso:harness new`; "write a harness for X" | a harness authored module by module, files not forms, `check` green | a first usable harness in about twenty minutes, one question per module |
| `kapso` | `watch`, `inbox`, `resume`, `learn`, `deploy`, `doctor`, and the `harness` and `experience` wrappers | the operating procedure, built on `--detach` | the handoff in four lines |

Every host gets the same four: Claude Code and Cursor as skills with
commands, Codex as skills invoked by name with the sidecar's prompts.

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

## 2. `kapso-brief`

1. **Read the repository**: evaluators (`evaluate.py`, test suites, a
   notebook's metric cell, a benchmark command), data, README. Confirm the
   loaded harness or recommend one. Read the harness's setup page: it says
   what a statement in this domain must record, and those become the
   brief's questions to the repository, not to the engineer.
2. **Baseline.** Run the evaluator once when it is cheap; otherwise say how
   long it would take and leave the baseline unknown.
3. **Draft `kapso-brief.md`** with every field filled from evidence or
   marked unknown: objective (one line), measured by, baseline, target with
   its headroom reasoning, rules (the harness's guardrails as invariants,
   plus the repository's own: evaluator untouched, no fitting on the
   hold-out, read-only data), budget with defaults stated, harness,
   experience.
4. **The one question**, decided by the entrance's three cases: an
   evaluator present means no question; a criterion without an evaluator
   gets a proposed protocol and a target, with the offer to write the
   evaluator for review, and one yes-or-edit; nothing at all gets two or
   three candidate criteria from what the repository holds, a
   recommendation, and launches on "go" or a single edit.
5. **Launch** detached with `--goal-file kapso-brief.md`, hand back the
   watch line, the harness and version, and the note that the engineer's
   own metric can replace the assumed one.

Rules: never says it cannot proceed; never asks twice; never writes an
evaluator unasked; the brief is text the engineer edits, not a form; rules
go in as invariants, methods do not.

## 3. `kapso-harness`

1. **One opening question:** what kind of work, and what must never happen
   in it. Write `harness.yaml` and `instructions/guardrails.md` from the
   answer and show them, so the author reads files within the first minute.
2. **One question per module,** each with the authoring guide's example as
   the prompt: setup (what to pin, what the statement must say), ideation
   (the exploration axes, what every proposal states), implementation (the
   discipline, what to save), verification (what must never pass, how to
   tell), feedback (the limits, robustness, when to stop), learning (the
   scoping vocabulary), deployment (how the winner runs, per target). Skip
   a module the author has nothing to say about.
3. **Choose the form for each answer** by the guide's ladder: a line on the
   page, a skill with a script, a delegate, a server, a hook. Write it, list
   it in the manifest, and say in one sentence what was written and why
   that form.
4. **Attach what exists.** Tools the author names become `mcp.json` entries
   with a skill of the same name; notes and runbooks become skills with
   references; a check the author describes as deterministic becomes a
   script inside a skill plus, when it must bind at a tool call, a hook.
5. **`kapso harness check`**, clear the warnings, show the tree.
6. **Offer the probe run** on a task with a known answer; after it, read
   the trace, name where attempts diverged, and propose the smallest edit.

Rules: nothing added without a named failure or domain rule; pages under
forty lines; a skill's description names the situation; secrets never in
files; the author can stop after any module and have a valid harness.

## 4. `kapso`

Unchanged in purpose: launch with `--detach`, follow with `watch`, answer
the inbox, resume, learn, deploy, doctor. It gains the `harness` wrappers
(check, list, add, update, remove, export) and the `experience` wrappers
(add, list, share), and the rule that a `/kapso:build` request goes through
`kapso-brief` first.

## 5. Measuring smoothness

The skill lab (`~/kapso-skill-lab`, eval-first, prompts plus rubrics plus
fixtures) runs two kinds of test per skill:

- **Trigger tests:** twenty phrasings of each request; the right skill
  loads, the wrong ones do not. Claude Code's `claude plugin eval` with the
  skill-use grader gives the number on that host; the lab covers Codex.
- **Outcome rubrics** against the budgets: setup ends green in at most
  three questions; the brief has every field present or marked unknown
  after at most one question and a measured baseline when the evaluator
  was cheap; the harness passes `check` with every skill named on its
  module's page and no page over forty lines.

A skill ships when both pass on both hosts.
