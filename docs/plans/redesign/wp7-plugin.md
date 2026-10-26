# WP7: Plugin

2026-10-26. Owner: the redesign's implementer, autonomously, the owner
checking the decisions. Branch `wp7-plugin` off `redesign` at `e792fadd`.
Size: L (one source tree for three hosts, six skills written for the
mistakes the lab recorded, eleven commands, the launcher, the marketplace
files, two engine seams, the evals, and a proof round on both hosts; the
long pole of the critical path).

## Scope

The plugin is how an engineer meets Kapso from the coding agent they
already work in. One source tree, `plugin/` in this repository, carries
everything: three thin manifests (Claude Code, Codex, Cursor), one MCP
entry that bootstraps itself, eleven commands (`/kapso:setup`, `build`,
`watch`, `inbox`, `resume`, `review`, `learn`, `deploy`, `doctor`,
`harness`, `experience`), and six skills with their Codex sidecars
(`kapso-setup`, `kapso-build`, `kapso-evaluation`, `kapso-harness`,
`kapso-review`, `kapso`), each the procedure for one recognisable moment,
written to the budgets of `docs/plans/kapso-plugin-skills.md`. The
repository is the marketplace: `.claude-plugin/marketplace.json` and
`.agents/plugins/marketplace.json` at its root, so the install is one line
per host. The plugin's version is the package's, pinned by one test. Two
engine seams serve it: the host-session server gains the campaign tools
(`kapso_build_start`, `kapso_status`), so an agent can delegate a build
and follow it without a shell, and reads what a project's config names
under `experience.sessions`; `kapso harness export` writes a harness's
skills, delegates, servers and hooks in a host's own layout for an
ordinary session. The three per-host skill folders under `skills/` fold
into `plugin/skills/kapso`. A trigger suite (`plugin/evals/`, run by
`claude plugin eval` on Claude Code and by a runner of ours on Codex) and
the outcome rubrics of the skills document become the plugin's tests; the
proof run is the plugin round on a fresh machine (Claude Code) and on
Codex, recorded in the semantic suite's record shape so WP9's report
renders it.

**Not in scope.** A live UI in Claude Code (the status line, the pane,
the inbox band: the owner's decision of 2026-10-12, a later layer). A
session-start hook injecting the bank's brief: the host-session server
already serves the intro of what it loads as its instructions, which every
host shows the session on connect, so the brief rides without a hook (the
decision is recorded). Learning from host sessions (S7, the transcript
translator: the August brief's P3). Live verification on Cursor (the
manifest is written to the format the installed plugins use; the owner's
Cursor is the first run). The simulated-user round, S2, and the judge
(WP9: this package makes every step of it runnable and records the
mechanical round in S2's record shape). The docs tab's reorganisation
(WP10; this package writes the plugin page, the "plugin page at 7" of
WP10's row, and the README's install lines). The marketplace submissions
(Anthropic's directory, Codex's curated tab, cursor.directory: WP11,
release). `/kapso:memory` (repo memory built on request: the owner's
decision 5 left it for later).

## Interface

### Exposed

**The tree.**

```text
plugin/
├── .claude-plugin/plugin.json      name kapso, version = the package's, skills, commands, mcpServers
├── .codex-plugin/plugin.json       name, version, skills, mcpServers, interface (display name, capabilities, default prompts)
├── .cursor-plugin/plugin.json      name, displayName, version, skills, mcpServers
├── .mcp.json                       mcpServers.kapso: scripts/kapso-mcp (stdio), the launcher below
├── scripts/kapso-mcp               the self-bootstrapping launcher (bash)
├── commands/                       setup build watch inbox resume review learn deploy doctor harness experience
├── skills/
│   ├── kapso/SKILL.md              the operating procedure, folded from skills/<host>/kapso
│   │   └── agents/openai.yaml      the Codex sidecar
│   ├── kapso-setup/                from a bare machine to a green doctor
│   ├── kapso-build/                the objective, the evaluation, the launch
│   ├── kapso-evaluation/           called by kapso-build: the evaluator built or audited
│   ├── kapso-harness/              authoring from the repository; improving from a run
│   └── kapso-review/               reading a finished run
├── evals/                          the trigger suite: cases, graders
└── README.md                       what the plugin is, the install lines, the layout
.claude-plugin/marketplace.json     at the repository root: the marketplace `kapso`, plugin `kapso` from ./plugin
.agents/plugins/marketplace.json    the same for Codex
```

**The manifests.** `plugin/.claude-plugin/plugin.json`: `name` `kapso`,
`version` (the package's), `description`, `author` `{name: Leeroo}`,
`keywords`, `skills` (the six directories), `commands` `./commands/`,
`mcpServers` `./.mcp.json`. `plugin/.codex-plugin/plugin.json`: `name`,
`version`, `description`, `author`, `homepage`, `repository`, `keywords`,
`skills` `./skills/`, `mcpServers` `./.mcp.json`, `interface`
(`displayName` Kapso, `shortDescription`, `longDescription`,
`developerName`, `capabilities` `[Interactive, Read, Write]`,
`websiteURL`, `defaultPrompt`: three lines, one per entry skill). The
Cursor manifest: `name`, `displayName`, `version`, `description`,
`author`, `skills`, `mcpServers`. The formats are the installed plugins'
on this machine (Canva's three manifests beside one `skills/` and one
`.mcp.json`; Codex's bundled `visualize`), read before writing; `claude
plugin validate plugin --strict` passes in the suite when the CLI is on
PATH (CI installs it). The version: `kapso.__version__`,
`pyproject.toml`, the three manifests, both marketplace entries and the
launcher's pin are one number, pinned by `tests/test_version.py`.

**The marketplace files.** `.claude-plugin/marketplace.json`: `name`
`kapso`, `owner` `{name: Leeroo}`, `plugins: [{name: kapso, source:
./plugin, description, version, category}]`.
`.agents/plugins/marketplace.json`: `name` `kapso`, `interface:
{displayName: Kapso}`, `plugins: [{name: kapso, source: {source: local,
path: ./plugin}, policy: {installation: AVAILABLE, authentication: NONE},
category}]` (the format of Codex's bundled marketplace; the policy values
verified on this box in change 1). The install lines, verified on this box
against a local clone and at release against GitHub:

```text
claude plugin marketplace add Leeroo-AI/kapso   &&  claude plugin install kapso@kapso
codex plugin marketplace add Leeroo-AI/kapso    &&  codex plugin add kapso@kapso
```

A clone's path takes the place of `Leeroo-AI/kapso` on a branch; the
interactive `/plugin marketplace add` and `/plugin install` forms are the
same operations.

**The launcher**, `plugin/scripts/kapso-mcp`: runs `kapso-mcp` from PATH
when the package is installed; else `uvx --from leeroo-kapso==<version>
kapso-mcp`; else `pipx run --spec leeroo-kapso==<version> kapso-mcp`; else
exits 1 with one line naming `/kapso:setup`. It passes
`--config kapso-config.yaml` when that file is in the working directory
(the plugin's one convention, decision 9), and every argument it was given.
`.mcp.json` names it by the root variable the host expands
(`${CLAUDE_PLUGIN_ROOT}/scripts/kapso-mcp` for Claude Code); a host that
expands no root variable names `kapso-mcp` on PATH, which `/kapso:setup`
puts there, in a manifest-level MCP file of its own (decided in change 1
on this box, recorded in the decisions). The server's stderr lines
(`kapso-mcp: <gate>: off (<reason>)`) are the host's MCP log; the
`kapso` skill says where each host shows it.

**What a host session is served.** The host-session server
(`kapso-mcp`, WP3's) serves the gates the directory holds (`research`,
`repo_memory`, `experiment_history`) and, new in this package, the
`campaign` gate (below) and what the project's config names under
`experience.sessions` (a list of references in the forms `kapso experience
list` shows, empty as packaged): `--experience` on the command line wins
over it, a reference that does not exist stops the server with the `add`
line that makes it, as a build is refused. The intro naming the loaded
sources is the server's instructions, shown on connect: the session-start
brief, without a hook. `/kapso:learn` ends by offering the one-line edit
(`sessions: [mine:all]` under `experience:` in `kapso-config.yaml`) that
serves the bank to every later session of the project.

**The campaign gate**, `campaign`, host sessions only (a campaign's own
sessions never get it, as the inbox gate is campaign-only):

| Tool | Does | Returns |
|---|---|---|
| `kapso_build_start(brief, repo, output, evaluation=None, data=None, budget_minutes=None, budget_experiments=None, harness=None, experience=None, config=None)` | `kapso build --brief … --detach` as a subprocess of the server (outside any sandbox, so the launch survives the host's shell policy), with `--config` from the argument or the launcher's | the receipt: `{pid, log, status, watch}` as `--detach` prints it, or the refusal's one line with a non-zero `exit` |
| `kapso_status(path)` | `kapso watch <path> --json` | the status as data, or the launch state before the status exists |

The tool descriptions carry the skill's rules (one launch per request,
never a second; `WAITING ON YOU` is answered through `kapso inbox reply`,
which stays a CLI line the person runs or the agent runs with a note).
`get_mcp_config` never emits the gate for a campaign session.

**The commands.** Each `commands/<name>.md` is a short prompt: the
frontmatter's `description` and `argument-hint`, then the skill to follow
for `$ARGUMENTS` and the exact CLI line of that moment, so the agent
reaches the right command first. In Codex the same procedures ride the
skills' `$kapso-…` names and the sidecar's default prompts.

| Command | Follows | The line |
|---|---|---|
| `/kapso:setup` | `kapso-setup` | the install, the logins, `kapso doctor` |
| `/kapso:build <wish>` | `kapso-build` (and `kapso-evaluation`) | `kapso build --brief kapso-brief.md … --detach` |
| `/kapso:watch [campaign]` | `kapso` | `kapso watch [path] [--json]`, the three-line answer |
| `/kapso:inbox [campaign] [note]` | `kapso` | `kapso inbox <path>`, `kapso inbox reply <path> <id> "<note>" --detach` |
| `/kapso:resume <campaign>` | `kapso` | `kapso build --output <path> --resume --detach` after the diagnosis |
| `/kapso:review <campaign>` | `kapso-review` | `kapso trace <path>`, `solution.explain()`, the diff |
| `/kapso:learn <campaign>` | `kapso` | `kapso learn <path>`, then the serving offer |
| `/kapso:deploy <campaign> [--target]` | `kapso` | `kapso deploy <path> --target <t>` once, backgrounded when the tool's timeout is below the session's |
| `/kapso:doctor [verb]` | `kapso-setup` | `kapso doctor [verb] [--models]` |
| `/kapso:harness new\|improve\|check\|list\|export` | `kapso-harness` | `kapso harness new\|check\|list\|export …` |
| `/kapso:experience add\|list\|share\|update\|remove` | `kapso` | `kapso experience …` |

**The skills.** Six directories, the frontmatter the skills spec's core
(`name` equal to the directory, `description` at most 1,024 characters in
the form capability, "Use when …" with the literal phrases, "Do not use
for …"; nothing a host does not read), the body under five hundred lines
(`kapso` under three hundred and fifty: the shipped one plus the
diagnosis section minus the goal flow), the Codex sidecar
`agents/openai.yaml` beside each (`interface.display_name`,
`short_description`, `default_prompt`; `policy.allow_implicit_invocation`
mirroring Claude Code's invocability). What each one is, from
`kapso-plugin-skills.md`, is the contract the evals check:

| Skill | Trigger | Body | Budget |
|---|---|---|---|
| `kapso-setup` | `/kapso:setup`; any command when `doctor` is red; "set up kapso" | detect before asking (node, python, git, uv or pipx, `kapso` and `kapso-mcp` on PATH, the CLIs and their logins, `.env` by name, a `kapso-config.yaml` or a harness directory); install what is missing with the method the machine has, never the global Python; the logins with their links; the keys the next step needs, written to `.env` without printing them; `kapso doctor` to green, `--models` offered; orientation (`kapso harness list`, a harness recommended from the repository, `kapso experience add mine`, Leeroopedia's plugin line); three closing lines | under five minutes, at most three questions, two link clicks |
| `kapso-build` | `/kapso:build`; "build X and verify it", "I need Y that meets Z", "improve W", "get the AUC above 0.85" | listen for the two things (what should exist, how it is known done); discover in silence under a minute (README, data, notebooks and their metric cells, tests, scripts named like evaluators, CI, dependencies; the domain and the harness that fits, its setup page as questions to the repository; the experience sources that exist); hand the evaluation to `kapso-evaluation`; one message: what was found, the brief as `kapso-brief.md` (objective, measured by, baseline, target with the headroom reasoning, rules, budget with defaults, harness, experience), the evaluation's protocol for approval, the one thing to confirm; at most one more round; launch detached with `--brief kapso-brief.md` and hand back the watch line, the harness and version, and that the user's own criterion can replace an assumed one | at most two rounds, one question each, under five minutes with the approval |
| `kapso-evaluation` | called by `kapso-build`; not user-invocable (Claude Code: `user-invocable: false`; Codex: the sidecar says so) | the contract (one command printing the metric on its own line; a hold-out outside the workspace; deterministic under a seed; a fast mode that keeps the metric's meaning; fail-loud on a malformed submission; registered with a version); an evaluator found is read against it, run once for the baseline, its gaps listed and fixed in a copy the user approves; none found, one is built from the criterion and the data (`kapso_evaluation/evaluate.py` and its fast mode), run for the baseline, its protocol written in five lines; one approval message inside `kapso-build`'s; on approval it is passed with `--evaluation`, protected from that moment | one approval message |
| `kapso-harness` | `/kapso:harness new\|improve`; "write a harness for X" | `new`: read before asking (README, task runners, notebooks, tests and linters, CI, recurring scripts, data layout, tool configurations, runbooks); a first harness proposed in one message within two minutes (the domain in a sentence, the standing rules, candidate skills from recurring scripts, servers from existing data access, checks from validators and tests, the modules where the repository gave nothing; the tree as it will be written); `kapso harness new <name>`, then the files, then one question per silent module with the guide's example as the prompt, the cheapest form chosen by the guide's ladder and said in a sentence; `kapso harness check` to green; the probe run offered. `improve <campaign>`: the trace read (where attempts diverged, which hooks fired, what verification voided, what feedback kept asking for), the smallest edit proposed in the cheapest form with the attempt that shows it, applied on a word, `version` bumped, `check` again | the proposal within two minutes of reading; at most eight questions; a `check`-green harness in about twenty minutes |
| `kapso-review` | `/kapso:review`; "what did it do", "why this one", "is it safe to merge" | the trace and the record read; one message: the winning branch's diff in outline, the evaluation evidence with its version, the voided attempts and why, the rejected ideas and the reason, the reviewers' risks, the spend, the next action in one line (merge, cherry-pick, resume with more budget, learn); questions answered from the record | one message, then questions |
| `kapso` | `watch`, `inbox`, `resume`, `learn`, `deploy`, `doctor`, the `harness` and `experience` wrappers; "how is the campaign", "it died", "deploy it" | the shipped skill's facts and procedures (the install facts, `--detach`, the inbox without a value, the resume with one flag, learn and the serving offer, experience, deploy with a target, models and config, when Kapso is the wrong tool, the docs), with the goal flow moved to `kapso-build` and a diagnosis section: slow versus stalled by the heartbeat and the phase (a long evaluation is not a stall); a dead run classified from the log's last lines into a provider limit, an evaluator crash, the environment, the disk or a killed session, with the fix named before the resume; `/kapso:build` goes through `kapso-build`, a finished run's questions through `kapso-review` | the four-line handoff |

Two rules hold across the six and are checked by the evals: Kapso builds
and verifies an objective end to end (a skill triggers on the intent to
build something with a success criterion, never on the word "improve"
alone), and the agent discovers everything the repository and the
environment can answer in silence, then speaks once. The shipped skill's
"whole reply is one question" for a repository with no evaluator goes:
the agent proposes (the three cases of `kapso-plugin-user-flow.md` §4)
and `kapso-evaluation` builds the evaluator for one approval, the owner's
revision of 2026-10-24 superseding the earlier "never write an evaluator"
rule; recorded in the decisions.

**`kapso harness export`.** `kapso harness export <ref> --format
claude|codex [--to <dir>]` writes, into `<dir>` (the current directory
by default), the host's own layout of the harness's skills, delegates,
servers and hooks, the union over its modules, with the staging's own
per-host writers: Claude Code's `.claude/skills/<name>/`, `.claude/agents/`,
`.mcp.json` and the merged hooks file; Codex's `.agents/skills/`,
`.codex/` agents, `mcp_servers` snippet and hooks. It prints what the host
cannot reproduce: the module routing (every skill is offered in every
session) and the pages (an ordinary session has no module). A path the
export would overwrite is refused by name. The author flow's step A4.

**The page and the README.** `docs/coding-agent-skills.mdx` becomes the
plugin page (title "Install the Kapso plugin in Claude Code, Codex or
Cursor"): the install line per host, what the plugin ships (the commands
table, the skills table), the first session (`/kapso:setup`, then
`/kapso:build`), what a session is served and the `experience.sessions`
line, OpenCode through the skills folder (`ln -s
<clone>/plugin/skills/kapso .opencode/skills/kapso`, the six if wanted),
`kapso-mcp` for a session without the plugin, where each host shows the
MCP log. The README's "If you're an AI agent" note points at
`plugin/skills/kapso/SKILL.md`; its Installation step 4 offers the plugin
and `/kapso:setup` where it offered the setup prompt; the installation
page's "Set up through your coding agent" becomes `/kapso:setup` with the
prompt kept for a session without the plugin.

**Superseded.** `docs/plans/kapso-plugin-mental-model.md` §9 and §10 and
`docs/plans/kapso-plugin-user-flow.md` §2 (the tree with `/kapso:evolve`,
`research`, `bank`) get a superseded note pointing here; the verbs are
WP1's and WP3's names.

### Consumed

- WP1: `kapso build` with `--brief`, `--detach`, the receipt it prints,
  `--resume`; `Solution.open`, `solution.explain()` and `.diff()`.
- WP2: `kapso harness new|check|list|add|update|remove`, the staging's
  per-host writers (`stage_harness`'s attachments, skills, servers, hooks,
  agents) that `export` reuses; the authoring guide's sections the
  `kapso-harness` skill walks; `--harness` on the verbs.
- WP3: `kapso-mcp` and its gates, `experience_settings`, the sources'
  grammar, `kapso experience add|list|share|update|remove`, `kapso learn
  <path>`; this package adds `experience.sessions` to the config block and
  the `campaign` gate to the server (the same implementer; listed in
  Ownership).
- WP4: `load_config`, the one override file (`kapso-config.yaml` by the
  plugin's convention), `kapso doctor --json` and `--show-config`.
- WP5: `kapso deploy <campaign> --target … | --status | --stop | --start |
  --logs`, `Software.open`, the engine skill's deploy section (now the
  `kapso` skill's).
- WP6: `kapso watch [path] [--json] [--follow]`, the receipt before the
  status, the listing, `kapso trace <path> [--json]`, `kapso doctor
  --json`.
- WP0: `scripts/redesign/fresh_machine.sh`, the review script,
  `tests/semantic/` (the record shape and `report.py`).

## Ownership

Edits: `plugin/` (new, every file), `.claude-plugin/marketplace.json` and
`.agents/plugins/marketplace.json` (new, the repository root),
`tests/test_version.py` (the manifests and the pin), `tests/test_plugin_*`
(new), `tests/test_no_retired_names.py` (reads `plugin/`),
`scripts/check_docs_coverage.py` (reads the plugin's skills and commands
for CLI lines), `src/kapso/gated_mcp/host_session.py` and
`src/kapso/gated_mcp/presets.py` and a new `gates/campaign_gate.py` (the
campaign gate, `experience.sessions`; WP3's files, the same implementer),
`src/kapso/config.yaml` (`experience.sessions`), `src/kapso/core/config.py`
only if the walk needs the key declared (it does not: the packaged file is
the schema), `src/kapso/cli/harness.py` and `src/kapso/harness/staging.py`
(`export`; WP2's files), `README.md`, `docs/coding-agent-skills.mdx`,
`docs/installation.mdx` (the setup section), `docs/reference/cli.mdx`
(`kapso harness export`, `kapso-mcp`'s `experience.sessions`),
`docs/reference/configuration.mdx` (the key), `docs.json` (the page's
title), `docs/plans/kapso-plugin-mental-model.md` and
`kapso-plugin-user-flow.md` (superseded notes), `scripts/redesign/`
(the plugin round's scripts), `tests/semantic/README.md` (the plugin
round's record named).

Deletes: `skills/` (the three per-host folders and the README; the one
copy is `plugin/skills/kapso`), the docs' three symlink install lines.

Reads, does not edit: the adapters, `kapso.cli` (the parsers the CLI-line
test parses against), `kapso.harness.check`, `tests/semantic/report.py`.

## Changes

1. **The tree, the manifests, the launcher, the marketplace files.**
   `plugin/` with the three manifests, `.mcp.json`, `scripts/kapso-mcp`,
   `README.md`, the two marketplace files at the root; the version test
   extended to the manifests, the marketplace entries and the launcher's
   pin; `tests/test_plugin_tree.py`: the manifests parse with their
   required fields, `claude plugin validate plugin --strict` passes when
   the CLI is on PATH (skipped by name otherwise), the launcher's four
   branches (a fake `kapso-mcp` on PATH is run with the arguments; none
   and a fake `uvx` runs the pinned form; none and a fake `pipx` the
   `run --spec` form; nothing at all exits 1 naming `/kapso:setup`; the
   `--config` line added when `kapso-config.yaml` is in the directory).
   Verified on this box, recorded in the decisions: `claude plugin
   marketplace add <clone>` then `claude plugin install kapso@kapso` and
   `claude plugin details kapso`; `codex plugin marketplace add <clone>`
   then `codex plugin add kapso@kapso` and the server listed by `codex mcp
   list` and answering a tool call from `codex exec`; whether Codex
   expands a plugin-root variable in the MCP file, and the manifest-level
   file the answer needs.
2. **The `kapso` skill, folded.** `plugin/skills/kapso/SKILL.md` from
   the three copies (one body, the sidecar beside it), the goal flow
   moved out, the diagnosis section in, the deploy and experience
   sections as WP5 and WP3 left them; `skills/` deleted; the retired-name
   check and the docs coverage script read `plugin/`;
   `tests/test_plugin_skills.py`: every skill's frontmatter (name, the
   description's form and length), the body caps, the sidecar's mirror,
   every `kapso …` line in the skills and commands parsed against the
   CLI's own parsers (an unknown flag or verb fails by file and line).
3. **`kapso-setup`**, `/kapso:setup`, `/kapso:doctor`.
4. **`kapso-build` and `kapso-evaluation`**, `/kapso:build`; the
   fixtures' briefs (`examples/churn-first-build`, `examples/fraud-no-
   evaluator`) checked against the skill's brief form.
5. **`kapso-review`** and `/kapso:review`; the operating commands
   `/kapso:watch`, `inbox`, `resume`, `learn`, `deploy`, `experience`.
6. **`kapso-harness`**, `/kapso:harness`; `kapso harness export` with
   its test on the trading example (the layout written for each host,
   the lines about what the host cannot reproduce, the refusal of an
   overwrite).
7. **The campaign gate and `experience.sessions`.** `gates/campaign_gate.py`
   with the two tools over `kapso build --detach` and `kapso watch
   --json` as subprocesses (the receipt parsed from the verb's own
   output; a refusal returned as data), the gate in `GATES` as
   host-only, mounted by `kapso-mcp`; `experience.sessions` in the config
   block and read by the server when `--experience` is absent; the
   launcher's `--config`; tests with the verbs faked.
8. **The evals.** `plugin/evals/`: the trigger cases (the lab's twelve
   prompts and the build-and-verify phrasings that never say "improve",
   at least twenty per entry skill, sixty-forty between the skill's own
   phrasings and the near misses that must not trigger it), graded by
   the skill-use grader; a Codex runner, `scripts/redesign/plugin_round.sh
   codex-triggers`, that drives `codex exec` with the plugin installed
   and reads the skill invocation from the event stream; the outcome
   rubrics of the skills document as the proof's checklist.
9. **The page, the README, the installation page**; the superseded notes.
10. **The proof round**, the findings, the Built table.

## Tests

- Syntactic: `tests/test_version.py` (one number across the package, the
  three manifests, both marketplace entries, the launcher's pin);
  `tests/test_plugin_tree.py` (the manifests' fields, `claude plugin
  validate --strict` when the CLI is present, the launcher's branches);
  `tests/test_plugin_skills.py` (the frontmatter contract, the caps, the
  sidecars' mirror, every CLI line parsed, every command naming a skill
  that exists, no retired name); `tests/test_campaign_gate.py` (the two
  tools over faked verbs: the receipt's keys, a refusal as data, the gate
  absent from a campaign session's config); `tests/test_harness_export.py`
  (the trading example exported for each host: the files, the lines, the
  overwrite refusal); `tests/test_host_session.py` extended
  (`experience.sessions` loaded, `--experience` winning, a missing source
  stopping the server with the add line).
- Proof run (the plugin round). The fresh machine (`e2-standard-4`,
  Claude Code logged in with the token the fresh-machine script reads;
  the wheel installed as a tool, so `kapso-setup` finds the package
  present and the PyPI install step is the release's to prove), the
  plugin installed from the clone as a local marketplace. Steps, each a
  `claude -p` session with the plugin, its transcript kept, its messages,
  questions and minutes recorded in the semantic record shape
  (`tests/semantic/README.md`) so `report.py` renders it against the
  skills document's budgets: (a) `claude plugin validate plugin --strict`,
  `claude plugin details kapso` (the token cost, recorded); (b)
  `/kapso:setup` from the bare state (no `.env`, no config); (c)
  `/kapso:build` on `examples/churn-first-build` ("get the churn model's
  AUC above 0.85"): the discovery, the evaluator audited, one message,
  "go", the detached launch at a fifteen-minute budget; (d) "how is it
  going" twice (`/kapso:watch` and the plain question); (e) completion,
  `/kapso:review`, "is it safe to merge"; (f) `/kapso:deploy --target
  local` and one call against it; (g) `/kapso:build` on
  `examples/fraud-no-evaluator`: the evaluation built and approved in two
  rounds, the launch; (h) `/kapso:harness new` on a copy of
  `examples/trading/repo` with no harness: the proposal, the questions,
  `check` green, compared with the shipped harness; (i)
  `/kapso:harness improve` on the churn campaign's trace; (j) the trigger
  evals, `claude plugin eval plugin --trust-plugin`, every case graded;
  (k) `kapso harness export examples/harnesses/trading --format claude`
  into a scratch directory, a session with the export answering a
  question with the harness's skill. On Codex (the dev box's login, in a
  scratch project outside this checkout, since the machine's key is over
  its quota; the owner's key moves it to the machine): the install from
  the local marketplace, `$kapso-build` on the churn fixture, `$kapso`
  for watch and stop, `kapso_build_start` and `kapso_status` called from
  a `codex exec` session, the Codex trigger runner. Archived under
  `scripts/redesign/runs/wp7/`: the transcripts, the records, the eval
  report, the campaigns.
- Semantic hooks: S2's nine steps become runnable (this round is S2
  without the simulated user and the judge; WP9 adds both); S5's
  injected pause is not run here (the inbox path is the shipped skill's,
  proven in WP1's and WP2's rounds).

## Acceptance

- `claude plugin marketplace add <clone>` and `claude plugin install
  kapso@kapso` install the plugin on this box and on the fresh machine;
  `claude plugin validate plugin --strict` passes in the suite; the same
  for `codex plugin marketplace add` and `codex plugin add`, with the MCP
  server listed and answering a tool call from a `codex exec` session.
- The six skills and eleven commands exist with the contract above;
  every CLI line in them parses; `skills/` is gone and the README, the
  docs and the installation page name the plugin.
- `/kapso:setup`, `/kapso:build` (an evaluator present; none present),
  `/kapso:watch`, `/kapso:review`, `/kapso:deploy`, `/kapso:harness new`
  and `improve` each complete on the fresh machine within the skills
  document's budgets, recorded step by step in the semantic record shape
  and rendered by `report.py`; the trigger evals pass on Claude Code
  (every case) and the Codex runner on the dev box.
- `kapso_build_start` launches a campaign from a host session and
  `kapso_status` reads it; a campaign's own sessions never see the gate.
- `experience.sessions` in a project's config serves a host session the
  bank; the intro shows on connect; a missing source stops the server
  with the add line.
- `kapso harness export examples/harnesses/trading --format claude|codex`
  writes the layout and says what the host cannot reproduce; tested.
- One version across the package, the manifests, the marketplace entries
  and the launcher's pin, pinned by the suite; the gate green; the proof
  archived and recorded here.

## Risks

- **Codex and the plugin root.** Codex may not expand a root variable in
  the MCP file; then its manifest names `kapso-mcp` on PATH and the
  bootstrap through `uvx` is Claude Code's alone. Settled on this box in
  change 1 before anything else is written.
- **The launcher's pin names an unreleased version** until WP11 ships;
  until then the `uvx` and `pipx` branches fail and the launcher's last
  line names `/kapso:setup`, which installs the wheel. The tests fake the
  tools; the release gate runs the real one.
- **Context budget.** Six skill descriptions in every session: Claude
  Code lists each under a 1,536-character cap and Codex's catalog is two
  per cent of the context; the descriptions front-load their trigger
  words and `claude plugin details` reports the projected cost, recorded
  in the proof.
- **The evaluator rule's reversal** ("never write an evaluator" becomes
  "build it for one approval") changes what the agent does with a bare
  repository; the proof's step (g) is the check, and the decision is
  recorded for the owner.
- **The authoring interview's length.** Eight questions is the cap; the
  skill skips a module the repository answers and says so.
- **Codex's trigger runner reads an event stream** whose shape changed
  across Codex versions; the runner pins the fields it reads and fails
  loud on a change.
- **The fresh machine's Codex key** is over its quota: the Codex steps
  run on the dev box in a scratch project until the owner funds the key;
  said in the proof.

## Review

The cross-model review of this plan runs before the build
(`scripts/redesign/review.sh`, Codex `gpt-6-astra` at xhigh and Claude
Code `claude-opus-5`, read-only; the outputs under
`scripts/redesign/runs/wp7-plan-review/`); every finding and its answer
below, then the pull-request review's.
