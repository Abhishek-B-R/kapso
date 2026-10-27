# Kapso plugin: the settled decisions and the user flow

*2026-10-12, branch `kapso-plugin`. Companion to `kapso-plugin-mental-model.md`:
that document holds the modules and the seams, this one holds what was
decided and the experience the plugin is built to deliver.*

## 1. Settled

The ten questions of the mental model, answered on 2026-10-12.

1. **No live UI in the first release.** The plugin is one tree: the
   manifests, one skill, the commands, and a self-bootstrapping MCP launcher.
   It is identical on every host; Claude Code gets nothing the others lack.
   The live surfaces (status line, pane, inbox band) stay in the mental
   model as a later layer.
2. **Packaging: `plugin/` in this repository, and the repository is the
   marketplace.** Verified against the installed plugins on this machine:
   Claude Code reads `.claude-plugin/marketplace.json` at the repository
   root with `"source": "./plugin"`; Codex reads
   `.agents/plugins/marketplace.json` (name, `interface.displayName`, a
   `plugins` list of `{name, source: {source: local, path}, policy,
   category}`), the format of its own bundled marketplace. The plugin's
   `version` equals the package version, the launcher pins
   `leeroo-kapso==<that version>`, and the version test pins all three. The
   per-host `skills/<host>/kapso` folders fold into `plugin/skills/kapso`,
   one copy, with the Codex sidecar `agents/openai.yaml` beside it.
3. **Everything inside the plugin.** The well-known plugins never ask for a
   manual install: their MCP entries are commands that install themselves on
   first run (`npx -y …`, `uvx --from …` for Python servers, a launcher
   script under the plugin root), and the plugin that wraps a CLI, OpenAI's
   Codex plugin, ships a `/codex:setup` command and one command per verb.
   Kapso does the same. The MCP entry is `plugin/scripts/kapso-mcp`, which
   runs `kapso-mcp` from PATH when the package is installed, else
   `uvx --from leeroo-kapso==<version> kapso-mcp`, else `pipx run`, else
   exits with one line naming `/kapso:setup`; so the tools work from the
   first session wherever `uv` or `pipx` exists. `/kapso:setup` does the real
   install: the package as a tool (`uv tool install`, `pipx install`, or
   `pip install` into the active environment), the two coding-agent CLIs
   when missing, the logins with their links, the keys into `.env`,
   `kapso doctor`, and the one-token model probe on request. It is the
   setup prompt the installation page already carries, turned into a
   command.
4. **Leeroopedia is its own plugin**, `Leeroo-AI/leeroopedia-mcp`.
   `/kapso:setup` offers its install line when no key is present. Campaigns
   keep reaching the hosted gate through the config, unchanged.
5. **Repo memory is never built by default.** The gate rides only in a
   repository where a campaign built one. A `/kapso:memory` command may
   build it on request later.
6. **Bank serving** follows the config (`learning.serving.enabled`); the
   task family defaults to the config's `default_mode` lowercased, the pull
   log lives under `learning.serving.session_root`. The session-start brief
   waits for the live-UI layer; until then the bank is reached through its
   three tools when the agent decides to look.
7. **Launch is command-driven first.** The engineer, or the agent on the
   engineer's request, runs `/kapso:evolve`; the agent-driven delegation
   tools (`kapso_evolve_start`, `kapso_status`) come after the commands.
8. **One skill body** for every host, built on `--detach`. Done.
9. **Configuration surface.** The plugin carries no settings of its own.
   Kapso's knobs stay in Kapso's config file; the plugin's one convention is
   that a `kapso-config.yaml` in the project root is passed with `--config`
   by every command, so "turn serving on" is a one-line edit the agent can
   make and every later command honours.
10. **Naming.** Commands are `/kapso:<verb>`; the skill keeps the name
    `kapso`, invocable as `/kapso` in Claude Code and `$kapso` in Codex. The
    skill is the procedure, the commands are its entry points.

## 2. What the plugin ships

*Superseded on 2026-10-27 by `docs/plans/redesign/wp7-plugin.md`: the tree shipped is `plugin/` with ten commands (`setup build watch inbox resume review learn deploy harness experience`), six skills and the host MCP files; `/kapso:evolve`, `research` and `bank` are WP1's `build` and WP3's `experience` now.*

```text
plugin/
├── .claude-plugin/plugin.json      name kapso, version = package version
├── .codex-plugin/plugin.json       skills, mcpServers, interface
├── .cursor-plugin/plugin.json      skills, mcpServers
├── .mcp.json                       kapso: scripts/kapso-mcp (stdio)
├── scripts/kapso-mcp               the self-bootstrapping launcher
├── skills/kapso/SKILL.md           the operating procedure (today's skill)
│   └── agents/openai.yaml          the Codex sidecar
└── commands/                       setup evolve watch inbox resume learn research deploy bank doctor
```

A command is a short prompt that names the skill's rule for that moment
and the exact CLI line, so the agent reaches the right command first. In
Codex the same procedures ride the skill's `$kapso` and the sidecar's
default prompts.

## 3. The flow

An engineer, working in Claude Code or Codex on a repository with a model
to improve, reads the Kapso README. Each step says what the engineer does,
what the agent does, and how long it takes.

**Step 0, discover (one minute).** The README's first block is the install
line for each host, nothing else to read:

```text
/plugin marketplace add Leeroo-AI/kapso        then  /plugin install kapso@kapso      (Claude Code)
codex plugin marketplace add Leeroo-AI/kapso   then  codex plugin add kapso@kapso     (Codex)
```

**Step 1, install (seconds).** The plugin loads: the skill, the commands,
the MCP server. The launcher starts the server through `uvx` even though
nothing is installed yet, so `research_idea` and `research_implementation`
are already there when the codex CLI is on PATH; the other tools appear as
their stores do. Nothing was written to the project.

**Step 2, `/kapso:setup` (three to five minutes, once per machine).** The
agent checks node, python and git, installs `leeroo-kapso` as a tool so
`kapso` and `kapso-mcp` are on PATH, installs whichever of `claude` and
`codex` is missing, starts each login that is missing and shows the link,
asks for the optional keys (Leeroopedia, an OpenAI key for embeddings) and
writes them to `.env` without ever printing them, runs `kapso doctor evolve`
until every required row reads `[OK ]`, offers `kapso doctor --models`, and
offers the Leeroopedia plugin's install line. It ends with three lines on
what it can now do. The engineer answers two or three questions and clicks
two links.

**Step 3, the first campaign (one tool call, then hours unattended).** The
engineer says "get the churn model's accuracy above 0.85", or runs
`/kapso:evolve`. The skill's goal flow runs: the agent finds the evaluator
the repository already has, runs it once for the baseline, writes the goal
with the metric, the target and the judge named, adds the data rules as
invariants, and launches:

```bash
kapso evolve --goal "…" --initial-repo . --eval-dir eval --data-dir data \
  --output ../churn-campaign --time-budget-minutes 60 --iterations 10 --detach
```

The command returns at once with the pid, the log, the status path and the
watch line. The agent's reply is the handoff: the goal it passed, what it
assumed and that the engineer's own metric can replace it, and
`kapso watch ../churn-campaign --follow`. The engineer keeps coding.

**Step 4, following (seconds, whenever asked).** The status file exists
within seconds of the launch, in phase `setup` while the workspace is
seeded and repo memory is bootstrapped, then iteration by iteration.
"How is the campaign?" or `/kapso:watch` has the agent read
`kapso watch --json` and answer in three lines: iteration, best score and
node, budget left, and what the last node consulted. `--tree` gives the
lineage when the engineer wants the whole search.

**Step 5, the inbox (a minute).** An implementation session needed a key
that is not in `.env`. The campaign paused and exited with `WAITING ON YOU`.
The agent sees it on the next status read and shows the request rows: the
key, what the session hit, what it tried, where the value goes, what it
will do next. The engineer puts the key in the project's `.env` and says
"done". The agent runs `kapso inbox reply --detach` with a note, never the
value; the campaign resumes in a session of its own, continuing the very
session that asked. A credential pasted to the agent by mistake is refused
by the record itself.

**Step 6, the result (minutes).** `COMPLETED`, the score, the winning branch
`generic_exp_N`, the stop reason. The agent shows the diff of the winning
branch against the baseline and `solution.explain()`; the engineer merges
the branch, cherry-picks, or asks for another round with a bigger budget
(`/kapso:resume`, which is the same `--detach` launch).

**Step 7, learning from it (one command, hours unattended).** `/kapso:learn`
on the campaign directory starts the mining, grading and update crews in a
session of their own and hands back `kapso watch learning/status`. The
cards land in the lesson bank at `~/.kapso/bank.git`, each with its
evidence. The agent then offers to turn serving on: a one-line edit of
`kapso-config.yaml` in the project, which every later command passes.

**Step 8, knowledge while coding (no command).** With serving on, the host
session has `bank_index`, `bank_get_card` and `bank_get_card_with_evidence`;
inside a campaign directory it has the experiment history; a repository a
campaign has worked on has its repo memory; and web research is always
there. The agent reaches for them when the skill's rules say so: a repeated
failure, an unfamiliar subsystem, a design choice the bank has measured
before. Leeroopedia's tools come from its own plugin beside Kapso's.

**Step 9, research and imported knowledge (minutes, then hours).**
`/kapso:research "QLoRA memory optimizations"` writes findings to a JSON
file and the agent passes them as context to the next campaign.
`/kapso:learn-knowledge` ingests a repository or the findings into the
knowledge graph when the Weaviate and Neo4j containers are up; the command
checks that first and says what to start if they are not.

**Step 10, deploying (minutes, foreground).** `/kapso:deploy` runs
`kapso deploy --solution-path ../churn-campaign --strategy local` (or
docker, modal) and prints the predict call; the engineer tries one input.

**Step 11, the team (one command).** `/kapso:bank create org/kapso-bank`
gives the bank a remote; every later `learn` pushes, every teammate's
`learn` pulls, and a campaign anywhere starts from what the team measured.
The repository's `.claude/settings.json` names the marketplace, so a
teammate who clones is offered the plugin on their first session.

**Step 12, the next campaign (the loop closes).** The engineer asks for the
next improvement. The campaign starts ahead: served the bank, with the repo
memory the last campaign built, on an install that `kapso doctor` already
verified. The handoff is the same four lines as in step 3.

## 4. The entrance to the evolve loop

The critical moment, settled 2026-10-12: the agent proposes, never gates.
Most engineers arrive without an evaluator, some with a success criterion,
many with nothing but a wish. The skill used to make the whole reply one
question when the repository had no evaluator; that reads as "give me a
judge or I do not move". The replacement is a short proposal the engineer
reacts to with a word.

Before launching, the agent reads the repository and writes a **campaign
brief**, a file `kapso-brief.md` in the project passed with `--goal-file`:

```text
Objective    one line
Measured by  the evaluator (protected), or the protocol a campaign-built
             evaluator must follow (data, hold-out, seed, metric definition)
Baseline     measured before launch when an evaluator exists, else unknown
Target       given, or proposed with headroom and the reasoning
Rules        invariants the judge enforces: evaluator untouched, no fitting
             on the hold-out, no rows dropped, read-only data
Budget       time and experiments, defaults stated
```

Three cases, by what the engineer has:

1. **An evaluator.** The agent finds it, runs it once for the baseline,
   takes the engineer's metric and target as given (or proposes a target
   with headroom and says so in one line), launches with `--eval-dir`, and
   puts the brief in the reply. No question.
2. **A success criterion, no evaluator.** The agent proposes the protocol
   the campaign-built evaluator will follow and a target, offers to write
   the evaluator for review instead (then it is protected), and asks once:
   launch as proposed, or change anything. One round of edits, then launch.
3. **Nothing.** The agent proposes two or three candidate criteria from what
   the repository holds (a notebook's metric, a test suite, a benchmark
   command, the task's natural measure), recommends one with a target or an
   open "maximise within budget", states the default, and launches on "go",
   "you decide" or a single edit.

Rules that hold in every case: the agent never says it cannot proceed; it
never asks twice; rules go into the brief as invariants and methods do not;
it never writes an evaluator unasked. The core needs nothing new for this:
`--goal-file` exists, a campaign without `--eval-dir` builds its evaluator
and the judge checks fairness, and the seed copy carries the brief.

## 5. What the flow asks of the core

Found while writing the flow; the first three are small.

- A `kapso doctor --json` for `/kapso:setup` to read instead of parsing
  rows (seam S0).
- A way to learn from a campaign directory from the shell with `--detach`:
  today the everyday path is two Python lines and the `kapso learn`
  subcommands are the development regime; `/kapso:learn` needs one line
  (new seam S9).
- `kapso watch` with no argument listing the campaigns launched from this
  repository that are alive or waiting, from the registry with a liveness
  filter (seam S2).
- `kapso learn_knowledge` as a CLI verb with `--detach`, for step 9; today it
  is `python -m kapso.knowledge_base.learners`.
- The version test extended to the plugin manifests and the launcher pin.
