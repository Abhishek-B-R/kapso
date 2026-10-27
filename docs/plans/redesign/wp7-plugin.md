# WP7: Plugin

2026-10-26. Owner: the redesign's implementer, autonomously, the owner
checking the decisions. Branch `wp7-plugin` off `redesign` at `e792fadd`.
Size: L (one source tree for three hosts, six skills written for the
mistakes the lab recorded, eleven commands, the launcher, the marketplace
files, four engine seams, the evals, and a proof round on both hosts; the
long pole of the critical path). Revised after the cross-model review
(the Review section) and the host probes
(`scripts/redesign/runs/wp7-hostfacts/FACTS.md`): the per-host MCP
files, the campaign tools' contract, the stop and detach seams, the
evaluator's contract, the export's files, the proof's matrix.

## Scope

The plugin is how an engineer meets Kapso from the coding agent they
already work in. One source tree, `plugin/` in this repository, carries
everything: three thin manifests (Claude Code, Codex, Cursor), one MCP
file per host, the self-bootstrapping launcher Claude Code runs, ten
commands (`/kapso:setup`, `build`, `watch`, `inbox`, `resume`, `review`,
`learn`, `deploy`, `harness`, `experience`), and six skills
with their Codex sidecars (`kapso-setup`, `kapso-build`,
`kapso-evaluation`, `kapso-harness`, `kapso-review`, `kapso`), each the
procedure for one recognisable moment, written to the budgets of
`docs/plans/kapso-plugin-skills.md`. The repository is the marketplace:
`.claude-plugin/marketplace.json` and `.agents/plugins/marketplace.json`
at its root, so the install is one line per host. The plugin's version
is the package's, pinned by one test. Four engine seams serve it: the
host-session server gains the campaign tools (`kapso_build_start`,
`kapso_status`, `kapso_stop`), so an agent can delegate a build and
follow it without a shell, and reads what a project's config names under
`experience.session_sources`; `kapso build --stop` ends a campaign and `kapso
learn` and `kapso experience add` take `--detach`, so every long
operation has one durable launch and one way to end; `kapso harness
export` writes a harness's skills, delegates and servers in a host's own
layout for an ordinary session; the adapters keep the installed plugin
and the person's own Kapso server out of campaign sessions (the probe:
a user-scope plugin's skills ride into every `claude -p` and `codex
exec` session otherwise). The three per-host skill folders under
`skills/` fold into `plugin/skills/kapso`. A trigger suite
(`plugin/evals/`, run by `claude plugin eval` on Claude Code and by a
runner of ours on Codex) and the outcome rubrics of the skills document
become the plugin's tests, replacing the skill lab's with-and-without
table of 2026-09 (the master's "skill lab re-run": the lab's prompts are
the suite's cases, its rubrics the proof's checklist, and the page's old
table goes); the proof run is the plugin round, S2's nine steps without
the simulated user and the judge, on a fresh machine (Claude Code) and
on the development box (Codex), recorded in the semantic suite's record
shape under its own name (`S2-mechanical`) so WP9's report renders it
and its real S2 is never conflated with it.

**Not in scope.** A live UI in Claude Code (the status line, the pane,
the inbox band: the owner's decision of 2026-10-12, a later layer). A
session-start hook injecting the bank's brief: the host-session server
serves the intro of what it loads as its instructions, which every host
shows the session on connect, so the brief rides without a hook (the
decision is recorded; the proof checks each host shows it). Learning from
host sessions (S7, the transcript translator: the August brief's P3).
Live verification on Cursor (the manifest is written to the format the
installed plugins use; the owner's Cursor is the first run). The
simulated-user round, S2, and the judge (WP9: this package makes every
step of it runnable and records the mechanical round in S2's record
shape). The docs tab's reorganisation (WP10; this package writes the
plugin page, the "plugin page at 7" of WP10's row, and the README's
install lines). The marketplace submissions (Anthropic's directory,
Codex's curated tab, cursor.directory: WP11, release). `/kapso:memory`
(repo memory built on request: the owner's decision 5 left it for
later). A plugin-provided MCP server under Codex: the host registers and
starts it but a `codex exec` session is not offered its tools (the
probe), so Codex's tools come through `codex mcp add`, which the setup
skill runs; the interactive host is the owner's to try.

## Interface

### Exposed

**The tree.**

```text
plugin/
├── .claude-plugin/plugin.json      name kapso, version = the package's, skills, commands, mcpServers: ./hosts/claude/mcp.json
├── .codex-plugin/plugin.json       name, version, skills, mcpServers: ./hosts/codex/mcp.json, interface
├── .cursor-plugin/plugin.json      name, displayName, version, skills, mcpServers: ./hosts/cursor/mcp.json
├── hosts/
│   ├── claude/mcp.json             kapso: ${CLAUDE_PLUGIN_ROOT}/scripts/kapso-mcp (stdio)
│   ├── codex/mcp.json              kapso: kapso-mcp on PATH, default_tools_approval_mode approve, startup_timeout_sec 60
│   └── cursor/mcp.json             kapso: kapso-mcp on PATH
├── scripts/kapso-mcp               the launcher (bash)
├── commands/                       setup build watch inbox resume review learn deploy harness experience
├── skills/
│   ├── kapso/                      SKILL.md, the operating procedure folded from skills/<host>/kapso; agents/openai.yaml, the Codex sidecar
│   ├── kapso-setup/                from a bare machine to a green doctor (each with its own SKILL.md and sidecar)
│   ├── kapso-build/                the objective, the evaluation, the launch
│   ├── kapso-evaluation/           called by kapso-build: the evaluator built or audited
│   ├── kapso-harness/              authoring from the repository; improving from a run
│   └── kapso-review/               reading a finished run
├── evals/                          the trigger suite: one case directory per prompt, graders beside
├── README.md                       what the plugin is, the install lines, the layout
└── LICENSE                         the repository's
.claude-plugin/marketplace.json     at the repository root: the marketplace `kapso`, plugin `kapso` from ./plugin
.agents/plugins/marketplace.json    the same for Codex
```

No `.mcp.json` at the plugin root: both hosts would read it, and the two
need different commands (the host facts). `${CLAUDE_PLUGIN_ROOT}` is
expanded by Claude Code in the MCP file and nowhere else it is needed;
the launcher is Claude Code's path to the tools before the install, the
PATH entry Codex's and Cursor's.

**The manifests.** `plugin/.claude-plugin/plugin.json`: `name` `kapso`,
`version` (the package's), `description`, `author` `{name: Leeroo}`,
`homepage`, `repository`, `license` `Apache-2.0`, `keywords`, `skills`
(the six directories, listed), `commands` `./commands/`, `mcpServers`
`./hosts/claude/mcp.json`. `plugin/.codex-plugin/plugin.json`: `name`,
`version`, `description`, `author`, `homepage`, `repository`, `license`,
`keywords`, `skills` `./skills/`, `mcpServers` `./hosts/codex/mcp.json`,
`interface` (`displayName` Kapso, `shortDescription`, `longDescription`,
`developerName` Leeroo, `category` Developer tools, `capabilities`
`[Interactive, Read, Write]`, `websiteURL`, `defaultPrompt`: three
starter prompts under 128 characters, one per entry skill). The Cursor
manifest: `name`, `displayName`, `version`, `description`, `author`,
`skills` `./skills/`, `mcpServers` `./hosts/cursor/mcp.json`. The formats
are the installed plugins' (Canva's three manifests; Codex's bundled
`visualize`; Codex's own `plugin-json-spec`), read before writing; `claude
plugin validate plugin --strict` passes in the suite when the CLI is on
PATH (CI installs it). The version: `kapso.__version__`,
`pyproject.toml`, the three manifests, both marketplace entries and the
launcher's pin are one number, pinned by `tests/test_version.py`.

**The marketplace files.** `.claude-plugin/marketplace.json`: `name`
`kapso`, `description`, `owner` `{name: Leeroo}`, `plugins: [{name:
kapso, source: ./plugin, description, version, category}]` (the
validator passes it with `--strict` once `description` is present).
`.agents/plugins/marketplace.json`: `name` `kapso`, `interface:
{displayName: Kapso}`, `plugins: [{name: kapso, source: {source: local,
path: ./plugin}, policy: {installation: AVAILABLE, authentication:
ON_USE}, category: Developer tools}]` (`authentication` is one of
`ON_INSTALL`, `ON_USE`; verified). The install lines, verified on this
box against a local clone and at release against GitHub:

```text
claude plugin marketplace add Leeroo-AI/kapso   &&  claude plugin install kapso@kapso
codex plugin marketplace add Leeroo-AI/kapso    &&  codex plugin add kapso@kapso
```

A clone's path takes the place of `Leeroo-AI/kapso` on a branch; the
interactive `/plugin marketplace add` and `/plugin install` forms are the
same operations; `claude plugin install kapso --marketplace
Leeroo-AI/kapso` is the one-step form. A repository that wants its
contributors offered the plugin commits `.claude/settings.json` with
`extraKnownMarketplaces: {kapso: {source: {source: github, repo:
Leeroo-AI/kapso}}}` and `enabledPlugins: {"kapso@kapso": true}`; the page
shows it.

**The launcher**, `plugin/scripts/kapso-mcp`, what Claude Code's MCP file
runs: `exec` of the first executable found, `kapso-mcp` on PATH, else
`uvx --from leeroo-kapso==<pin> kapso-mcp`, else `pipx run --spec
leeroo-kapso==<pin> kapso-mcp`, with the arguments it was given passed
through; none found, one stderr line naming `/kapso:setup` and exit 1.
An executable that is found and then fails is never followed by another:
the server's exit code is the launcher's, its stderr the host's MCP log.
A `kapso-mcp` on PATH of another version runs as it is; `kapso-mcp`
prints its version on stderr at start, so the log shows the mismatch
against the plugin's (the skill's facts are the plugin's version;
`kapso-setup` installs that version). The `<pin>` is the package's
version, substituted by the version test's twin at release time (the
launcher reads it from a line of its own, `KAPSO_VERSION=…`). The package's version is bumped in change 1 to a
development number (`0.8.0.dev1`): `0.7.10` is on PyPI without
`kapso-mcp`, and a pin to it would resolve a real wheel and die on the
missing entry point (Claude Code's review); the development number is on
no index, so until WP11 ships the `uvx` and `pipx` branches fail to
resolve and the last line is what a bare machine sees, which the setup
command answers. At release the version is the one shipped.

**The project's config.** The one convention the owner settled (decision
9): a `kapso-config.yaml` at the project root is passed by every command.
The project root is the git top level of the working directory, else the
working directory; every command's line carries `--config
<root>/kapso-config.yaml` when the file exists, and the `kapso` skill's
first rule says so (a build launched without it would run on the packaged
defaults while `doctor` shows the override, and a resume that changes
the config is refused by name); the CLI-line test checks each line for
it, not only that it parses. `kapso-mcp` finds the same file by the same
rule when `--config` is absent (the host starts it without a person
typing flags), so the server and the commands read one config. `kapso
trace` and `kapso watch` take no config and need none (they read
records). An explicit `--config` wins everywhere.

**What a host session is served.** The host-session server (`kapso-mcp`,
WP3's) serves the gates the directory holds (`research`, `repo_memory`,
`experiment_history`, and `bank` over what is loaded) and, new in this
package, the `campaign` gate (below) and what the project's config names
under `experience.session_sources`:
a list of references in the grammar `kapso experience list` shows, empty
as packaged, validated at start (a wrong type or a reference outside the
grammar is one stderr line and exit 1). `--experience` on the command
line replaces the list (an explicit empty string loads nothing); a
reference in the list whose source does not exist leaves the bank gate
off, with the `add` line that makes it in the notes and in the
instructions, the other gates served (a session that only wanted the
research tools keeps them); an explicit `--experience` stays strict, as a
build is refused. A host session's coordinate is `none` unless
`--harness` is passed, so `mine` serves the cards under no harness; the
server notes a bank that resolves to zero cards, and the offer the skill
makes is `mine:all`. Edits take effect at the next session. The server
never exits for want of a gate: with every gate off (a bare project, no
`codex` on PATH) it still connects, serves the campaign tools, and its
instructions carry the notes, so the host shows a server with its
reasons rather than "failed to connect" (an engine change; recorded).
The intro naming the loaded sources is the server's instructions, shown
on connect: the session-start brief, without a hook; the proof checks
each host shows it and makes one retrieval. A host spawns its MCP servers
once at session start, so `/kapso:setup`'s closing lines say how the
session gets the tools it just installed: `/mcp` and reconnect on Claude
Code, a new session on Codex. `/kapso:learn` ends by offering the
one-line edit (`session_sources: [mine:all]` under `experience:` in
`kapso-config.yaml`) that serves the bank to every later session of the
project; it serves sessions, not builds, which load what their brief or
flags name.

**The campaign gate**, `campaign`, host sessions only:

| Tool | Arguments | Does | Returns |
|---|---|---|---|
| `kapso_build_start` | `brief` (a path to a brief file) or `goal` (one line), `repo`, `output`, `evaluation`, `data`, `budget_minutes`, `budget_experiments`, `harness`, `experience` (a list of references), `config` | `kapso build … --detach` on the server's interpreter (`sys.executable -m kapso.cli`, never `kapso` from PATH), a subprocess of the server with the server's working directory as its own (so `.env` and every relative path resolve as the person's shell would), outside the host's shell sandbox; the config the argument names, else the launcher's rule; refused with one line when `kapso` is not on PATH (an hours-long campaign never runs from a bootstrap environment the person has no CLI to follow) | the launch receipt composed from the receipt file the verb writes beside the log (`pid`, `log`, `started_at`) and the paths the gate knows: `{"accepted": true, "pid", "log", "status", "watch", "campaign", "started_at"}`; a refusal `{"accepted": false, "exit", "error"}` with the verb's stderr whole |
| `kapso_status` | `path` | `kapso watch <path> --json` | the status as data, or the launch state before the status exists (`{"state": "starting"|"stopped"|"no_status", …}` as the verb prints it), with the verb's exit code under `exit` |
| `kapso_stop` | `path` | `kapso build --output <path> --stop` | `{"stopped": true, "pid"}`, or the refusal with its line |

"Accepted" is the receipt; "running" is what `kapso_status` says. The
tool descriptions carry the skill's rules (one launch per request, never
a second; `WAITING ON YOU` is answered through `kapso inbox reply`, a
line the person or the agent runs with a note, never a value). Host-only
means three things: `GateDefinition.host_only` keeps `get_mcp_config`
from ever emitting the gate for a campaign session; the Codex adapter
passes `-c mcp_servers.kapso.enabled=false` to every campaign session, so
the person's own server (added by `codex mcp add kapso -- kapso-mcp`, the
setup skill's line) does not ride into a campaign (verified to hide a
user-config server's tools); and the gate's tools refuse with one line
when the server's working directory is inside a campaign's session
workspace (the verb's own refusals stand behind them). The gate's
subprocess outcomes are return codes, never caught; a receipt that does
not parse raises. The gate reads nothing from the environment: the
config path and the working directory reach it through `GateConfig`
from `kapso-mcp`.

**The plugin stays out of campaign sessions.** A user-scope plugin's
skills ride into every `claude -p` and `codex exec` session (the probe:
an installed probe plugin's skills were listed by both), so an
implementation session could reach `kapso-build`. The Claude adapter
passes `enabledPlugins: {"kapso@kapso": false}` in the settings of every
campaign session (verified to hide the skills), merged with the
harness's hooks settings; Codex has no per-session switch (`plugins."…".
enabled=false` in a `-c` override did not hide them), so the Codex
adapter stages an execpolicy rule (`.codex/rules`, the mechanism WP2
verified) refusing `kapso build`, `kapso learn` and `kapso deploy`
inside its sessions with the reason shown to the model, and the six
skills' descriptions carry "never inside a Kapso campaign session". The
proof installs the plugin at user scope on both hosts and lists a
campaign session's skills and tools.

**`kapso build --output <campaign> --stop`.** Ends a running campaign:
the process group of the pid the status file names (SIGTERM, then
SIGKILL after `build.stop_grace_seconds`, a new key beside the other
build knobs), the status marked `failed` with the error `stopped by the
person` and `stopped_reason: stopped`, the receipt removed; a campaign
whose status is terminal or whose writer is gone is refused by state in
one line; `--resume` afterwards continues from the checkpoint, and a
resume of a campaign whose heartbeat is fresh is refused as live. Another
campaign's process is never touched: the pid is the status file's. The
`kapso` skill's diagnosis section distinguishes a slow run from a dead
one before any stop.

**`--detach` on learn and ingest.** `kapso learn <campaign> [--harness]
--detach` and `kapso experience add --repo|--research … --name <n>
--detach` run in a session of their own through the one detach helper:
the log beside the target (`<campaign>.learn.log`, `<indexes>/<name>.log`),
the receipt, the lines `kapso watch learning/status` as the follow. Deploy
stays foreground with the host recipe WP5 wrote (Claude Code's Bash tool:
once in the background with a log, never twice).

**The commands.** Ten `commands/<name>.md`, each a short prompt on one
template and nothing else: the frontmatter's `description` and
`argument-hint` (no other key); the body hands over to the skill with the
request, and carries no procedure. The template, `commands/review.md`:

```markdown
---
description: Read a finished Kapso run: what won, the evidence, what was voided, the next action
argument-hint: "[campaign]"
---
Follow the `kapso-review` skill (`/kapso:kapso-review`) for: $ARGUMENTS

The campaign is the argument; with none, the newest `kapso watch` lists.
Pass `--config kapso-config.yaml` on every line when the project root holds that file.
```

With no argument: `watch` lists every campaign, `review` and `learn` and
`deploy` take the newest, `inbox` the one waiting, `resume` asks when
more than one is dead, `build` asks for the wish in one line, `harness`
and `experience` print their skill's menu line. `/kapso:doctor` is not a
command: `kapso doctor` is one line the `kapso` skill knows and
`/kapso:setup` runs; `/kapso:experience` stays, the team's moment (share,
add a teammate's bank) deserving an entry. In Codex the same procedures
ride the skills' `$kapso-…` names and the sidecars' default prompts. A
plugin skill is `/kapso:<skill>` in Claude Code (`/kapso:kapso` for the
operating skill: the host's own naming, recorded as a reversal of the
owner's `/kapso`).

| Command | Follows | The line |
|---|---|---|
| `/kapso:setup` | `kapso-setup` | the install, the logins, `kapso doctor build --json`, `codex mcp add kapso -- kapso-mcp` on Codex |
| `/kapso:build <wish>` | `kapso-build` (and `kapso-evaluation`) | `kapso build --brief kapso-brief.md … --detach` |
| `/kapso:watch [campaign]` | `kapso` | `kapso watch [path] [--json]`, the three-line answer |
| `/kapso:inbox [campaign] [note]` | `kapso` | `kapso inbox <path>`, `kapso inbox reply <path> <id> "<note>" --detach` |
| `/kapso:resume <campaign>` | `kapso` | the diagnosis first (the body says so: a slow run is not resumed), then `kapso build --output <path> --resume --detach` |
| `/kapso:review <campaign>` | `kapso-review` | `kapso trace <path>`, `solution.explain()`, the diff |
| `/kapso:learn <campaign>` | `kapso` | `kapso learn <path> --detach`, then the serving offer |
| `/kapso:deploy <campaign> [--target]` | `kapso` | `kapso deploy <path> --target <t>` once, backgrounded when the tool's timeout is below the session's; `--target auto` when none is given |
| `/kapso:harness new\|improve\|check\|list\|add\|update\|remove\|export` | `kapso-harness` for `new` and `improve` (the interview and the trace reading, not subcommands); `kapso` for the rest | `kapso harness new\|check\|list\|add\|update\|remove\|export …` |
| `/kapso:experience add\|list\|share\|update\|remove` | `kapso` | `kapso experience …` (`add --repo|--research … --detach`) |

**The skills.** Six directories, the frontmatter the skills spec's core
(`name` equal to the directory, `description` at most 1,024 characters in
the form capability, "Use when …" with the literal phrases, "Do not use
for …", the trigger words first), the body under five hundred lines
(`kapso` under three hundred and fifty), the Codex sidecar
`agents/openai.yaml` beside each (`interface.display_name`,
`short_description`, `default_prompt`; `policy.allow_implicit_invocation`
as each host's own control, no parity invented: `kapso-evaluation` is
`user-invocable: false` on Claude Code, hidden from the menu and still
the model's to call, and `allow_implicit_invocation: true` on Codex,
which has no menu hiding). What each one is, from
`kapso-plugin-skills.md`, is the contract the evals check:

| Skill | Trigger | Body | Budget |
|---|---|---|---|
| `kapso-setup` | `/kapso:setup`; any command when `doctor` is red; "set up kapso" | detect before asking (node, python, git, uv or pipx, `kapso` and `kapso-mcp` on PATH and from the same install, the CLIs and their logins, `.env` by name, a `kapso-config.yaml` or a harness directory); install what is missing with the method the machine has (`uv tool install leeroo-kapso==<pin>`, else `pipx`, else `pip` into the active environment; uv itself when neither exists; never the global Python), say what was installed and where and the PATH line the shell needs; the logins with their links; on Codex `codex mcp add kapso -- kapso-mcp`; the keys the next step needs, written to `.env` without printing them; `kapso doctor build --json` until every required row is green (the next verb's rows, never the union), `--models` offered; orientation (`kapso harness list`, a harness recommended from the repository, `kapso experience add mine`, Leeroopedia's plugin line); three closing lines | under five minutes, at most three questions, two link clicks |
| `kapso-build` | `/kapso:build`; "build X and verify it", "I need Y that meets Z", "improve W", "get the AUC above 0.85" | listen for the two things (what should exist, how it is known done); discover in silence under a minute (README, data, notebooks and their metric cells, tests, scripts named like evaluators, CI, dependencies; the domain and the harness that fits, its setup page as questions to the repository; the experience sources that exist); hand the evaluation to `kapso-evaluation` by its three branches; one message: what was found with its evidence, the brief as `kapso-brief.md` (objective, measured by, baseline or `unknown`, target with the headroom reasoning, rules, budget with defaults, harness, experience), the evaluation's protocol for approval, the one thing to confirm; at most one more round; launch detached with `--brief kapso-brief.md` (`--evaluation` when one is approved) and hand back the watch line, the harness and version, and that the user's own criterion can replace an assumed one | at most two rounds, one question each, under five minutes with the approval |
| `kapso-evaluation` | called by `kapso-build`; not user-invocable | the contract (one command printing the metric on its own line as the last line and writing `kapso_evaluation/result.json` with `evaluation_script_path`, `evaluation_output` and `score`; the hold-out and its labels inside the directory passed with `--evaluation`, protected with it, never under `--data` (the churn fixture's pattern: `private/` named by `evaluation/private_dir.txt`), so no attempt can reach them; deterministic under a seed; a `--fast` mode whose number is marked not comparable; fail-loud on a malformed submission; the protocol's five lines name the split rule and the leakage checks run: time order, grouping, duplicates). Three branches: an evaluator found is read against the contract, run once for the baseline in a copy (no `result.json` left in the directory passed with `--evaluation`, which is refused at launch), its gaps listed and fixed in a copy the user approves; a criterion without an evaluator builds one from the criterion and the data (`kapso_evaluation/evaluate.py` and its fast mode), runs the baseline, writes the protocol in five lines; neither: candidate criteria from the repository with their evidence (a notebook's metric, a test suite, a benchmark command, the task's natural measure), one recommended with a target or "maximise within budget", and the single approval before anything is measured; a criterion the data at hand cannot measure is said plainly, with the data that would make it measurable. One approval message inside `kapso-build`'s; on approval the directory is passed with `--evaluation`, protected from that moment (versioned only when the config turns the maintainer on, which the packaged one does not: the skill says "protected", never "versioned") | one approval message |
| `kapso-harness` | `/kapso:harness new\|improve`; "write a harness for X" | `new`: read before asking (README, task runners, notebooks, tests and linters, CI, recurring scripts, data layout, tool configurations, runbooks); a first harness proposed in one message within two minutes (the domain in a sentence, the standing rules, candidate skills from recurring scripts, servers from existing data access, checks from validators and tests, the modules where the repository gave nothing; the tree as it will be written); on confirmation `kapso harness new <name>`, then the files, then one question per silent module with the guide's example as the prompt, the cheapest form chosen by the guide's ladder and said in a sentence; `kapso harness check` to green (no failure and no warning; what the machine lacks is a separate line, not a failure); the probe run offered. `improve <campaign>`: the trace read (where attempts diverged, which hooks fired, what verification voided, what feedback kept asking for), the smallest edit proposed in the cheapest form with the attempt that shows it, applied on a word, `version` bumped, `check` again. Rules kept from the design: nothing added without a named failure or domain rule; pages under forty lines; every skill named on its module's page; no secret in a file; nothing written before the proposal is confirmed; the harness valid after any module | the proposal within two minutes of reading; at most eight questions (its own budget, beside the two-round rule of the other skills); a `check`-green harness in about twenty minutes |
| `kapso-review` | `/kapso:review`; "what did it do", "why this one", "is it safe to merge" | the trace and the record read; one message: the winning branch's diff in outline, the evaluation evidence with its version when one was registered and "protected, unversioned" otherwise, the voided attempts and why, the rejected ideas and the reason, the reviewers' risks, the spend, the next action in one line (merge, cherry-pick, resume with more budget, learn); every number with the evaluation that produced it; questions answered from the record, never from memory of the run | one message under twelve lines plus the outline, then questions |
| `kapso` | `watch`, `inbox`, `resume`, `learn`, `deploy`, `doctor`, the `harness` and `experience` wrappers; "how is the campaign", "it died", "stop it", "deploy it" | the shipped skill's facts and procedures migrated (change 2, which lists every edit): the install facts, `--detach` and the four-line handoff, the inbox without a value, the stop line and the resume with one flag, learn with `--detach` and the serving offer, experience (what a session is served by the config against what a build loads), deploy with a target and the numbered lifecycle, the config as `hosts` and roles with `kapso doctor --show-config`, when Kapso is the wrong tool, the docs; the diagnosis section: slow versus stalled by the heartbeat and the phase (a long evaluation is not a stall; `STALLED` is three missed beats, not death), a dead run classified from the log's last lines into a provider limit, an evaluator crash, the environment, the disk or a killed session, with the fix named before the resume; `/kapso:build` goes through `kapso-build`, a finished run's questions through `kapso-review` | the four-line handoff |

Two rules hold across the six and are checked by the evals: Kapso builds
and verifies an objective end to end (a skill triggers on the intent to
build something with a success criterion, never on the word "improve"
alone), and the agent discovers everything the repository and the
environment can answer in silence, then speaks once, every proposal
carrying the evidence it rests on. The shipped skill's "whole reply is
one question" for a repository with no evaluator goes: the agent
proposes (the three branches above) and `kapso-evaluation` builds the
evaluator for one approval, the owner's revision of 2026-10-24
superseding the earlier "never write an evaluator" rule; recorded in the
decisions.

**`kapso harness export`.** `kapso harness export <ref> --host
claude_code|codex [--to <dir>] [--config <file>]` (the hosts' names are
the hosts table's, as `--coding-agent` names them; `--config` for the
store, as every harness subcommand takes it) writes, into `<dir>` (the
current directory by default), files an ordinary session discovers: for
Claude Code
`.claude/skills/<name>/` (each skill copied), `.claude/agents/<name>.md`
(each delegate in the agent file's frontmatter form) and `.mcp.json`
(each server, `${PLUGIN_ROOT}` expanded to the harness's path,
`KAPSO_HARNESS_ROOT` in its env); for Codex `.agents/skills/<name>/`,
`.codex/agents/<name>.toml` with the `[agents.<name>]` lines to add to
the user's config printed, and the `codex mcp add` line per server
printed. The union over the harness's modules by `Manifest.listed()`:
each attachment once, in first-occurrence order. Hooks are not exported
(campaign-bound: a verification Stop gate or a prepared-directory deny
would block an ordinary session), and the export says so, with the
module routing and the module pages it cannot reproduce; the standing
rules travel: `instructions/guardrails.md` is written as
`<dir>/kapso-harness-<name>.md` and the export prints the line that
includes it from the person's `CLAUDE.md` or `AGENTS.md` (never written
to: they are the person's files). Every destination is checked before
anything is written; one collision refuses the whole export by name. The
author flow's step A4.

**The page and the README.** `docs/coding-agent-skills.mdx` becomes the
plugin page (title "Install the Kapso plugin in Claude Code, Codex or
Cursor"): the install line per host, what the plugin ships (the commands
table, the skills table), the first session (`/kapso:setup`, then
`/kapso:build`), what a session is served and the `experience.session_sources`
line (sessions, not builds), the second engineer (`kapso experience add
<ref>` of the shared bank, `update`, `share`), the repository's
`.claude/settings.json` offer, OpenCode through the skills folder
(`ln -s <clone>/plugin/skills .opencode/skills`, the six at once; skills
only: the commands are Claude Code's and OpenCode's `opencode mcp` line
for `kapso-mcp` is the server's), `kapso-mcp` for a session without the
plugin, where each host shows the MCP log
(Claude Code: `/mcp` and the session's debug log; Codex: `codex mcp list`
and `~/.codex/log/`). The README's install block opens with the plugin's
two lines (the owner's step 0) before the manual steps; its "If you're an
AI agent" note points at `plugin/skills/kapso/SKILL.md`; the installation
page's "Set up through your coding agent" becomes `/kapso:setup` with the
prompt kept for a session without the plugin.

**Superseded.** `docs/plans/kapso-plugin-mental-model.md` §9 and §10 and
`docs/plans/kapso-plugin-user-flow.md` §2 (the tree with `/kapso:evolve`,
`research`, `bank`) get a superseded note pointing here; the verbs are
WP1's and WP3's names.

### Consumed

- WP1: `kapso build` with `--brief`, `--detach`, the receipt it writes
  beside the log, `--resume`; `Solution.open`, `solution.explain()` and
  `.diff()`; this package adds `--stop` and `build.stop_grace_seconds`
  (the same implementer).
- WP2: `kapso harness new|check|list|add|update|remove`, the manifest's
  `listed()`, the attachments' shapes (skills, agents, servers) that
  `export` renders; the authoring guide's sections the `kapso-harness`
  skill walks; `--harness` on the verbs; the Codex adapter's MCP
  overrides (this package adds the `enabled=false` line).
- WP3: `kapso-mcp` and its gates, `experience_settings`, the sources'
  grammar, `kapso experience add|list|share|update|remove`, `kapso learn
  <path>`; this package adds `experience.session_sources`, the `campaign` gate,
  `host_only` on the gate definition and `--detach` on `learn` and
  `experience add`.
- WP4: `load_config`, the one override file (`kapso-config.yaml` by the
  plugin's convention), `kapso doctor --json` and `--show-config`.
- WP5: `kapso deploy <campaign> --target … | --status | --stop | --start |
  --logs`, `Software.open`, the engine skill's deploy section (now the
  `kapso` skill's).
- WP6: `kapso watch [path] [--json] [--follow]`, the receipt before the
  status, the listing, `mark_failed`, `kapso trace <path> [--json]`,
  `kapso doctor --json`.
- WP0: `scripts/redesign/fresh_machine.sh`, the review script,
  `tests/semantic/` (the record shape and `report.py`).

## Ownership

Edits: `plugin/` (new, every file), `.claude-plugin/marketplace.json` and
`.agents/plugins/marketplace.json` (new, the repository root),
`tests/test_version.py` (the manifests and the pin), `tests/test_plugin_*`
(new), `tests/test_no_retired_names.py` (reads `plugin/`),
`scripts/check_docs_coverage.py` (reads the plugin's skills and commands
for CLI lines), `.github/workflows/tests.yml` (the paths `plugin/**`,
`.claude-plugin/**`, `.agents/**`, `scripts/**`),
`src/kapso/gated_mcp/host_session.py`, `presets.py` (`host_only`),
`server.py` (`GATE_CLASSES`) and a new `gates/campaign_gate.py` (WP3's
files, the same implementer), `src/kapso/config.yaml`
(`experience.session_sources`, `build.stop_grace_seconds`), `src/kapso/cli/build.py`
(`--stop`), `src/kapso/cli/learn.py` and `cli/experience.py` (`--detach`),
`src/kapso/cli/common.py` (the detach helper takes the log's and the
receipt's places), `src/kapso/execution/coding_agents/adapters/codex_agent.py`
(the `enabled=false` line, the execpolicy rule staged),
`src/kapso/execution/coding_agents/adapters/claude_code_agent.py`
(`enabledPlugins` in the session's settings), `src/kapso/cli/harness.py`
and a new
`src/kapso/harness/export.py` (`export`; WP2's verb), `README.md`,
`docs/coding-agent-skills.mdx`, `docs/installation.mdx` (the setup
section), `docs/reference/cli.mdx` (`kapso harness export`, `kapso build
--stop`, the `--detach` lines, `kapso-mcp`'s config rule and
`experience.session_sources`), `docs/reference/configuration.mdx` (the two keys),
`docs.json` (the page's title), `docs/plans/kapso-plugin-mental-model.md`
and `kapso-plugin-user-flow.md` (superseded notes), `scripts/redesign/`
(the plugin round's scripts), `tests/semantic/README.md` (the plugin
round's record named), a new `tests/semantic/budgets.json` (one entry per
step of the round, the skills document's numbers; the budgets judged by
hand named) and `tests/semantic/report.py` (a step without limits and a
missing artifact check fail the report); `.github/workflows/tests.yml`
pins the Claude Code CLI it installs (`@anthropic-ai/claude-code@2.1.310`),
so the validator in the gate never breaks on a release unrelated to the
branch.

Deletes: `skills/` (the three per-host folders and the README; the one
copy is `plugin/skills/kapso`), the docs' three symlink install lines.

Reads, does not edit: the Claude adapter (`--strict-mcp-config` already
keeps the person's servers out), `kapso.cli`'s parsers (the CLI-line test
parses against them), `kapso.harness.check`, the orchestrator (the stop
is a signal to its process group; nothing inside it changes).

## Changes

1. **The tree, the manifests, the MCP files, the launcher, the
   marketplace files.** `plugin/` with the three manifests, the three
   `hosts/<host>/mcp.json`, `scripts/kapso-mcp`, `README.md`, `LICENSE`,
   the two marketplace files at the root; the version test extended to
   the manifests, the marketplace entries and the launcher's pin;
   `tests/test_plugin_tree.py`: the manifests parse with their required
   fields, the three MCP files name the server `kapso` with their host's
   command, `claude plugin validate plugin --strict` and the marketplace's
   pass when the CLI is on PATH (skipped by name otherwise), the launcher's
   branches with fakes on PATH (`kapso-mcp` run with the arguments; none
   and a fake `uvx` the pinned form; none and a fake `pipx` the `run
   --spec` form; nothing at all exit 1 naming `/kapso:setup`; a found
   executable that exits 3 gives exit 3 and no second attempt). The host
   facts are the probe's (`wp7-hostfacts/FACTS.md`); the proof repeats the
   installs on the fresh machine. The version bumped to `0.8.0.dev1`
   (`pyproject.toml`, `kapso.__version__`, the manifests, the pin); the
   marketplace entry carries no version (the manifest's wins). The CI
   workflow's paths and its pinned CLI.
2. **The `kapso` skill, folded.** `plugin/skills/kapso/SKILL.md` from the
   three copies (one body, the sidecar beside it), with the migration:
   the goal flow out (to `kapso-build`), the finished-run questions to
   `kapso-review`, the harness and experience wrappers in, the config
   section on `hosts` and the roles with `kapso doctor --show-config`
   (no `modes.<MODE>.*`, no `python -c` line), the stop line and the
   diagnosis section (`STALLED` as the status defines it), learn with
   `--detach`, deploy's numbered lifecycle, the sidecar's prompts, "Everything below is 0.8.x" and every `modes`
   line gone (and the two forms, `modes.<MODE>` and a bare version claim,
   added to the retired-name patterns so the next drift fails the
   suite), `kapso watch` with no path, `kapso doctor --json` and
   `--show-config`, `kapso trace` named as `kapso-review`'s line, "never
   inside a Kapso campaign session" in the six descriptions; `skills/`
   deleted; the retired-name check and the docs coverage script read
   `plugin/`; `tests/test_plugin_skills.py`: every skill's frontmatter
   (name, the description's form and length), the body caps, each host's
   own invocability field on `kapso-evaluation`, every `kapso …` line in
   the skills and commands parsed against the CLI's own parsers (an
   unknown flag or verb fails by file and line), every command naming a
   skill that exists.
3. **The engine seams the skills need.** `kapso build --output <path>
   --stop` with `build.stop_grace_seconds`; `--detach` on `kapso learn
   <campaign>` and `kapso experience add --repo|--research`; the detach
   helper's log and receipt places; tests: a stopped campaign (a fake
   writer process in its own session, the status marked, the receipt
   gone, a terminal one refused), a detached learn's receipt and log.
4. **`kapso-setup`**, `/kapso:setup`, `/kapso:doctor`.
5. **`kapso-build` and `kapso-evaluation`**, `/kapso:build`; the
   fixtures' briefs (`examples/churn-first-build`, `examples/fraud-no-
   evaluator`) checked against the skill's brief form.
6. **`kapso-review`** and `/kapso:review`; the operating commands
   `/kapso:watch`, `inbox`, `resume`, `learn`, `deploy`, `experience`.
7. **`kapso-harness`**, `/kapso:harness`; `kapso harness export`
   (`harness/export.py`: the union by `listed()`, the renderers per host,
   the collision check) with its test on the trading example (the files
   for each host, the printed lines, hooks absent and said, the refusal
   of an overwrite).
8. **The campaign gate and `experience.session_sources`.**
   `gates/campaign_gate.py` with the three tools over the verbs on the
   server's interpreter (the receipt read from the launch receipt file; a
   refusal returned with the exit code and stderr; a receipt that does
   not parse raising), `GateDefinition.host_only`, the gate in `GATES` and
   `GATE_CLASSES`, mounted by `kapso-mcp` and never by `get_mcp_config`;
   the Codex adapter's `enabled=false` line and its execpolicy rule, the
   Claude adapter's `enabledPlugins` (verified on this box: the skills
   gone from a `claude -p` session's catalog); `experience.session_sources`
   read by the server when `--experience` is absent, with the validation
   and the per-source degrade; the server connecting with every gate off;
   `kapso-mcp`'s config rule and version line; tests
   with the verbs faked (the three outcomes each), the real server's tool
   listing through an MCP client (the campaign tools present in a host
   session, absent from a campaign session's config), `experience.session_sources`
   loaded, replaced by `--experience`, a missing listed source degrading
   the bank gate alone, a bad type refused.
9. **The evals.** `plugin/evals/`: one case directory per prompt
   (`prompt.md` with the pinned model, runs, `max_turns`, tools; `graders/`:
   `tool_used` on `Skill` with the exact skill name for a positive case,
   `max: 0` for a negative one, a `regex` on the answer where the skill's
   first line is pinned), the lab's twelve prompts and the build-and-verify
   phrasings that never say "improve", at least twenty per entry skill,
   sixty-forty between the skill's own phrasings and the near misses
   (half of them the hard confusions between the six: `kapso` against
   `kapso-build`, `kapso-review` against `kapso`, `harness improve`
   against `review`; half no Kapso skill at all), explicit commands
   separate from implicit phrasings, ten held-out paraphrases run once at
   the end; the bar per skill eighteen of twenty with no cross-skill
   false positive, two runs recorded, on a clean profile (no other
   plugin, no user skills); the run line
   `claude plugin eval plugin --ablation none --trust-plugin --json
   <out> --threshold 1.0 --model <m> --max-cost-usd <n>`; a Codex runner,
   `scripts/redesign/plugin_round.sh codex-triggers`, driving `codex exec`
   with the plugin installed and reading the skill-load event from the
   `--json` stream (a captured fixture pins the event's shape; a changed
   shape fails loud); the lab's outcome rubrics ported to the new verbs
   as the proof's checklist.
10. **The page, the README, the installation page**; the superseded
    notes; the reference pages' lines.
11. **The proof round**, the findings, the Built table.

## Tests

- Syntactic: `tests/test_version.py` (one number across the package, the
  three manifests and the launcher's pin); `tests/test_plugin_tree.py`
  (the manifests' fields, every path a manifest names existing, the
  skills listed by a manifest equal to the directories on disk, both
  marketplace entries' sources resolving to the plugin directory, the
  MCP files, the launcher executable, `claude plugin validate --strict`
  when the CLI is present, the launcher's branches and its
  no-second-attempt rule);
  `tests/test_plugin_skills.py` (the frontmatter contract, the caps, each
  host's invocability field, every CLI line parsed, every command naming
  a skill, no retired name); `tests/test_build_stop.py` (the stop, the
  refusals, the resume after); `tests/test_cli_detach.py` extended (learn
  and ingest); `tests/test_campaign_gate.py` (the three tools over faked
  verbs: the receipt's keys, a refusal as data, a malformed receipt
  raising, the gate absent from a campaign session's config and present
  in the host server's listing); `tests/test_harness_export.py` (the
  trading example exported for each host: the files, the printed lines,
  hooks absent, the collision refusal); `tests/test_host_session.py`
  extended (`experience.session_sources` loaded, replaced by `--experience`, the
  explicit-empty override, a missing listed source degrading one gate, a
  bad type refused, the config rule); `tests/test_codex_agent.py`
  extended (the `enabled=false` line, the rules file) and the Claude
  adapter's (`enabledPlugins` in the settings); `tests/semantic/report.py`'s
  own test (a step without limits fails; the budgets file covers every
  step of the round).
- Proof run (the plugin round), recorded step by step in the semantic
  record shape (`tests/semantic/README.md`, `test: S2-mechanical`) and
  rendered by `report.py` against `tests/semantic/budgets.json`, with
  these counting rules: a message is one assistant turn; a question is a
  turn that ends asking; rounds are messages; minutes exclude the wait
  for the person's answer; the brief's lines are exempt from the
  twelve-line cap; link clicks and evidence are judged by hand and said
  so; transcripts kept whole. The machine holds the clone (the local
  marketplace) and runs each fixture's `generate.py` first (no data is
  committed); the proof script does both. The acceptance-to-evidence
  matrix:

  | Step | Claude Code (fresh machine) | Codex (development box, scratch project) |
  |---|---|---|
  | install from the clone as a local marketplace; `validate --strict`; `details` (the always-on cost) | (a) | (a) install, `$kapso-probe`-style skill load |
  | `/kapso:setup` from a warm state (the wheel as a tool, the login present; the research gate off, the machine's Codex key being exhausted) | (b) | (b) `$kapso-setup`, `codex mcp add` line run |
  | cold local-wheel install: `uv tool install <wheel>` on a second fresh user, `kapso --version` and `kapso-mcp --version` from one install | (b2) | deferred (one machine) |
  | `/kapso:build` on the churn example: discovery, the evaluator audited, one message, "go", the detached launch at thirty minutes and three experiments | (c) | (c) `$kapso-build` |
  | "how is it going" twice; `/kapso:inbox` on an injected pause (a brief rule naming a key `.env` lacks, as S5 injects) | (d) | (d) |
  | completion with a delivered candidate; `/kapso:review`; "is it safe to merge" | (e) | (e) |
  | `/kapso:deploy --target local` and one call against it | (f) | (f) |
  | `/kapso:build` on the fraud example (a protocol, no evaluator: built and approved in two rounds); on a data-only copy (the protocol lines removed: candidate criteria, one approval); on an empty wish (a README alone: candidate criteria from nothing) | (g) | (g) the fraud case |
  | `/kapso:harness new` on a copy of `examples/trading/repo` with no harness: the proposal, the questions, `check` green, compared with the shipped harness; the probe run at a tiny budget | (h) | (h) |
  | `/kapso:harness improve` on the probe campaign | (i) | deferred |
  | `/kapso:learn` on the churn campaign: the detached launch, `learning/status` reaching `mine` | (j) | deferred (hours) |
  | `/kapso:experience share` to a local bare remote; a second user's `experience add <ref>` and a served build at a tiny budget | (k) | deferred |
  | `kapso harness export examples/harnesses/trading --format claude` into a scratch directory; a session there answering with the harness's skill; the Codex form's files | (l) | (l) the files |
  | the session brief: WP3's proof bank (`a9ddad3d`) staged as `mine`, `session_sources: [mine:all]` in the project's config; the instructions' sources recognised, one bank retrieval | (m) | (m) |
  | `kapso_build_start`, `kapso_status`, `kapso_stop` from a session; a campaign session's tool list without them (the plugin installed at user scope) | (n) | (n) |
  | the trigger evals: every case; the Codex trigger runner | (o) | (o) |
  | cold bootstrap latency of the launcher through `uvx` (release only: the pin is not on PyPI); the first turn's context cost | (p) partial | deferred |

  Archived under `scripts/redesign/runs/wp7/`: the transcripts, the
  records, the eval reports, the campaigns. The Codex half runs on the
  development box because the machine's Codex key is over its quota; the
  owner's key moves it to the machine.
- Semantic hooks: S2's nine steps become runnable (this round is S2
  without the simulated user and the judge; WP9 adds both); S5's injected
  pause runs here through `/kapso:inbox`.

## Acceptance

- `claude plugin marketplace add <clone>` and `claude plugin install
  kapso@kapso` install the plugin on this box and on the fresh machine;
  `claude plugin validate plugin --strict` passes in the suite; `codex
  plugin marketplace add` and `codex plugin add` install it on this box,
  its skills load by name, and its tools reach a `codex exec` session
  through the `codex mcp add` line the setup skill runs.
- The six skills and eleven commands exist with the contracts above,
  the rules kept from the design included; every CLI line in them
  parses; `skills/` is gone and the README, the docs and the installation
  page name the plugin, the plugin's lines first.
- Every row of the matrix marked for a host completes within the skills
  document's budgets on that host, recorded in the semantic record shape
  and rendered by `report.py` against the budgets file; the trigger evals
  reach eighteen of twenty per skill with no cross-skill false positive
  on Claude Code and on the Codex runner, two runs each; the rows marked
  deferred are said so in the record, and the skills document's ship bar
  (all three kinds of test on both hosts) is met for every row both
  hosts run and named deferred for the rest.
- A campaign session on either host, with the plugin installed at user
  scope, lists none of the six skills and none of the campaign tools.
- `kapso_build_start` launches a campaign from a host session,
  `kapso_status` reads it and `kapso_stop` ends it; a campaign's own
  sessions never see the gate, on either host, with the plugin installed.
- `kapso build --stop` ends a campaign whose resume then continues;
  `kapso learn --detach` and `kapso experience add --detach` return at
  once with their receipts.
- `experience.session_sources` in a project's config serves a host session the
  bank; the intro shows on connect on both hosts; a listed source that
  does not exist leaves the other gates served; an explicit `--experience`
  that does not exist stops the server with the add line.
- `kapso harness export examples/harnesses/trading --format claude|codex`
  writes the files an ordinary session discovers, says what it cannot
  reproduce, refuses an overwrite; tested and used in the proof.
- One version across the package, the manifests, the marketplace entries
  and the launcher's pin, pinned by the suite; the gate green; the proof
  archived and recorded here.

## Risks

- **Codex and plugin-provided servers.** A plugin's stdio server is
  started but not offered to a `codex exec` session (the probe); the
  `codex mcp add` line covers it and the interactive host is unverified.
  If the host fixes it, the Codex MCP file is already in place.
- **The launcher's pin names a development version** (`0.8.0.dev1`, on
  no index) until WP11 ships; until then the `uvx` and `pipx` branches
  fail to resolve and the launcher's last line names `/kapso:setup`,
  which installs the wheel. A pin to `0.7.10` would have resolved a real
  wheel without `kapso-mcp`. The tests fake the tools; the release gate
  runs the real one and measures the cold start.
- **Context budget.** Six skill descriptions in every session and three
  more tools: Claude Code lists each skill under a 1,536-character cap and
  Codex's catalog is two per cent of the context; the descriptions
  front-load their trigger words, `claude plugin details` reports the
  projected cost and the proof records the first turn's tokens.
- **The evaluator rule's reversal** ("never write an evaluator" becomes
  "build it for one approval") changes what the agent does with a bare
  repository; the proof's step (g) runs the three branches, and the
  decision is recorded for the owner.
- **A stop is a signal.** The orchestrator handles none; the checkpoint
  is written per iteration, so a stop loses at most the current one and
  `--resume` continues; a session the stopped campaign spawned dies with
  its process group (the detached launch is its own session).
- **The authoring interview's length.** Eight questions is the cap; the
  skill skips a module the repository answers and says so.
- **Codex's trigger runner reads an event stream** whose shape changed
  across Codex versions; the runner pins the fields it reads with a
  fixture and fails loud on a change.
- **The fresh machine's Codex key** is over its quota: the Codex steps
  run on the dev box in a scratch project until the owner funds the key;
  said in the proof, and the research gate is off on the machine.
- **Codex has no per-session switch for an installed plugin.** The
  execpolicy rule and the descriptions keep a campaign session from
  launching a nested build; a session can still read the skills' text.
  The proof's campaign-session listing says what it saw.

## Review

The cross-model review of the first plan (`scripts/redesign/review.sh`,
Codex `gpt-6-astra` at xhigh and Claude Code `claude-opus-5`, read-only,
2026-10-26; the outputs under `scripts/redesign/runs/wp7-plan-review/`),
and the host probes run beside it. Codex would have changed the plan
before building (ten P1s: the launcher's contract, the campaign gate on
Codex, the tools' schema, the evaluator's contract, the no-criterion
case, the export's files and semantics, the sidecar's policy, learn and
ingest without a durable launch, no way to stop a campaign, the proof's
coverage); Claude Code found eight P1s, most the same, and the ones only
it found (the hold-out of a session-built evaluator, the pin to a
released version without the entry point, the plugin's skills riding
into campaign sessions, the server's exit on a bare project) changed the
plan as much. Every finding and what the plan now says:
### Codex

| # | Finding | Answer |
|---|---|---|
| 1 | P1: the launcher's host contract is not frozen; a PATH-only fallback drifts from decisions 1 and 3 | frozen from the probe (`scripts/redesign/runs/wp7-hostfacts/FACTS.md`): one MCP file per host under `plugin/hosts/<host>/mcp.json`, none at the root. Claude Code's names the launcher by `${CLAUDE_PLUGIN_ROOT}` (expanded, verified); Codex takes the command verbatim (`${CLAUDE_PLUGIN_ROOT}`, `${PLUGIN_ROOT}` and a relative path all leave the launcher unrun, verified), and a plugin-registered stdio server's tools were not offered to a `codex exec` session even when the server ran and answered `ListTools`, while `codex mcp add` / `-c mcp_servers.*` exposes them. So Codex's file names `kapso-mcp` on PATH (for the interactive host, where the plugin's server may load) and `kapso-setup` runs `codex mcp add kapso -- kapso-mcp`, the form verified to work. The self-bootstrap through `uvx` is Claude Code's; on Codex the tools follow the install, which the setup skill is. A reasoned narrowing of decision 3 by a host fact, recorded |
| 2 | P2: the launcher's version and failure claims exceed its behaviour | specified: `exec` of the first executable found (`kapso-mcp` on PATH, else `uvx --from leeroo-kapso==<pin> kapso-mcp`, else `pipx run --spec leeroo-kapso==<pin> kapso-mcp`), the arguments passed through, the exit code the server's; an executable that is found and fails is never followed by another (no fallback after a start); diagnostics on stderr only; a PATH `kapso-mcp` of another version is run as it is, and `kapso-mcp` prints its version in its first stderr line beside the plugin's expected one when they differ (the skill's facts are the plugin's version). Tested with fakes on PATH |
| 3 | P1: excluding the gate from `get_mcp_config` does not make it host-only on Codex, whose campaign sessions inherit the user's servers | fixed: the Codex adapter passes `-c mcp_servers.kapso.enabled=false` for every campaign session (`enabled=false` verified to hide a user-config server's tools), and `get_mcp_config` never emits a host-only gate; the gate's tools also refuse with one line when the server runs inside a campaign directory's session workspace (`KAPSO_SESSION` is not read: the refusal is by the working directory, a campaign's `.kapso/experiment_history.json` above it). The adapter is in Ownership; the proof installs the plugin at user scope and lists a campaign session's tools |
| 4 | P1: the campaign tools need an actual contract | frozen: the schemas and every outcome's JSON in the Interface; `brief` is a path to a brief file (`goal` the one-line alternative), `experience` a list of references, relative paths resolved against the session's working directory, the receipt read from the launch receipt file (`<campaign>.launch.json`), a refusal returned as `{"exit", "error"}` with the verb's stderr whole; "accepted" is the receipt, "running" is `kapso_status`; the verb runs on the server's interpreter (`sys.executable -m kapso.cli`) |
| 5 | P1: the gate's wiring and rule compliance are missing from Ownership | added: `gated_mcp/server.py` (`GATE_CLASSES`), `GateDefinition.host_only`, the launcher's config path passed as an argument into `GateConfig`, no environment lookup, refusals by return code, malformed receipts raising, the timeout from the config (`experience.session_tool_timeout`? no: the verb's own `--detach` returns at once; `kapso_status` is a read; no timeout knob is needed) |
| 6 | P2: the project-config convention is only implemented for MCP startup | specified: every command's line carries `--config kapso-config.yaml` when the project root (the git top level, else the working directory) holds one, the `kapso` skill's first rule; `kapso-mcp` finds the same file by the same rule when `--config` is absent; `kapso trace` and `kapso watch` take no config and need none (they read records); explicit `--config` wins everywhere |
| 7 | P2: `experience.session_sources` needs shape validation and a narrower failure policy | fixed: a list of strings, each a reference in the grammar, validated by `kapso-mcp` at start (a wrong type or a bad reference is one line and exit 1); `--experience` replaces the list (an explicit empty string loads nothing); a reference in the list whose source does not exist leaves the bank gate off with the add line in the notes and the instructions, the other gates served; an explicit `--experience` stays strict; edits take effect at the next session; the default `[]` is the packaged file's |
| 8 | P1: the evaluator contract omits what the engine enforces | fixed: the contract names `result.json` (`evaluation_script_path`, `evaluation_output`, `score`), the baseline run in a copy of the evaluation directory so no `result.json` is left in the one passed with `--evaluation` (refused at launch otherwise), hold-out labels kept out of both copied directories, the fast mode's number marked not comparable; registration is the maintainer's and the packaged config ships it off, so the skill says "protected" and never "versioned" unless the config turns the maintainer on |
| 9 | P1: the no-criterion case is not safely specified | fixed: the three branches written out (an evaluator found; a criterion without one; neither: candidate criteria from the repository with their evidence, one recommended, the single approval before anything is measured); the fixtures: the churn example (an evaluator), the fraud example (a protocol, no evaluator), a data-only repository (the fraud data with the brief's protocol lines removed) and an empty wish (a README alone), the last two made by the proof script |
| 10 | P1: export's claimed layouts are not the staging's outputs | fixed: export writes files, not sessions: Claude Code's `.claude/skills/<name>/`, `.claude/agents/<name>.md` (the delegate's frontmatter form), `.mcp.json`; Codex's `.agents/skills/<name>/`, `.codex/agents/<name>.toml` with the `[agents.<name>]` lines to add to the user's config, and `codex mcp add` lines; `${PLUGIN_ROOT}` expanded to the harness's path, `KAPSO_HARNESS_ROOT` set in each server's env; hooks are not exported (campaign-bound: a Stop gate or a prepared-directory deny would block an ordinary session), said in the output |
| 11 | P1: export's union semantics are unspecified | fixed: the union over modules by `Manifest.listed()` (each attachment once, first occurrence), hooks excluded, every destination checked before anything is written and the whole export refused on one collision; tested on the trading example for both hosts |
| 12 | P1: the sidecar mirror reverses the policy | fixed: `kapso-evaluation` is `user-invocable: false` on Claude Code and `allow_implicit_invocation: true` on Codex, where no menu hiding exists; the test checks each host's file for its own field |
| 13 | P1: learning and ingestion strand the user in foreground operations | fixed: `kapso learn <campaign> --detach` and `kapso experience add --repo|--research … --detach` through the one detach helper (a session of its own, the log beside the target, the receipt, `kapso watch learning/status` as the follow line); deploy stays foreground with the host recipe (Claude Code's Bash tool: once in the background with a log) as WP5 wrote it |
| 14 | P1: the plugin can launch a campaign but not stop one | fixed: `kapso build --output <campaign> --stop` ends the campaign's process group (the status file's pid, SIGTERM then SIGKILL after `build.stop_grace_seconds`), marks the status `failed` with `stopped by the person`, and a later `--resume` continues from the checkpoint; the campaign gate gains `kapso_stop(path)`; a run whose heartbeat is fresh is refused by `--resume` as live, and the skill's diagnosis section says a slow run is not a dead one |
| 15 | P2: setup's green-doctor requirement forces infrastructure | fixed: `kapso doctor <next verb> --json` (`build` first), only required rows block; the interpreter: `uv tool install leeroo-kapso==<pin>` first, else `pipx`, else `pip` into the active environment, and `kapso --version` plus `kapso-mcp --version` must answer from the same install; the PATH refresh line per host |
| 16 | P2: command bodies and names remain guesswork | fixed: one command template (the skill named, the arguments passed as the request, the campaign inferred from `kapso watch` with one row else asked, the exact line) with the exceptions listed; `harness improve` is the skill's interview, not a subcommand; `add|update|remove` route to the `kapso` skill; `/kapso:kapso` is what Claude Code names a plugin skill, the owner's `/kapso` is the host's own naming, recorded as a reversal |
| 17 | P2: folding the operating skill needs a migration list | fixed: enumerated in change 2 (build intent to `kapso-build`, finished-run questions to `kapso-review`, the harness and experience wrappers, `hosts` and roles instead of `modes.<MODE>.*`, the config copy line, `python -c` replaced by `kapso doctor --show-config`, `STALLED` as the diagnosis section says, deploy's numbered lifecycle, the sidecar prompts) |
| 18 | P2: the compressed contracts drop rules | restored in the skills table and the acceptance (the forty-line page, a named failure or rule per addition, no secrets in files, every skill named on its page, confirmation before writing, a valid harness after any module; evidence provenance in build and review; `check` passing is not prerequisites met) |
| 19 | P1: the proof is smaller than S2's mechanical half | fixed: the acceptance-to-evidence matrix in Tests, every S2 step on Claude Code (learn launched and its first phase reached; the empty wish; sharing to a local bare remote and a second engineer's served build at a tiny budget; the authoring probe run; the inbox through `/kapso:inbox` on an injected pause), the Codex half naming each step run or deferred |
| 20 | P1: two proof steps lack viable prerequisites | fixed: the churn build at thirty minutes and three experiments with a delivered candidate required before review and deploy; `harness improve` on the authored harness's probe campaign; the fraud fixture's brief rewritten by the proof's `kapso-build` when it supplies the evaluator (a copy, the fixture untouched) |
| 21 | P2: the environment exceptions are partly reconciled | fixed: "warm setup" on the fresh machine (the wheel as a tool, the Claude login present; the research gate off since the machine's Codex key is exhausted), a cold local-wheel install test as a separate step, the PyPI bootstrap the release's; the acceptance line reads per host |
| 22 | P2: the budgets cannot produce a reliable report | fixed: the counting rules (a message is one assistant turn; a question is a turn that ends asking; minutes exclude the wait for the person's answer; the brief's lines are exempt from the twelve-line cap; the harness interview's eight questions are its own budget), the budgets file, `report.py` failing on a step without limits and on a missing artifact check, transcripts kept whole |
| 23 | P1: the trigger command can pass without enforcing skill selection | fixed: the trigger suite runs single-arm (`--ablation none`) with `tool_used` on `Skill` matching the exact skill name, negative cases asserting no invocation, model, runs and threshold pinned, `--allow-tools` named |
| 24 | P2: twenty cases are coverage, not soundness | fixed: expected and forbidden sets per case, explicit commands separate from implicit phrasings, held-out paraphrases, Codex evidence from the event stream's skill-load event with a captured fixture, isolated config and stores, the lab's rubrics ported to the new verbs |
| 25 | P2: the unit tests miss behaviour; CI misses plugin-only changes | fixed: the server's real tool listing, the bootstrap interpreter, a malformed receipt, the explicit-empty override, duplicate attachments, the collision refusal, the exported files' discovery; `plugin/**`, `.claude-plugin/**`, `.agents/**` and `scripts/**` in the workflow's paths; whole-tree assertions land with the tree |
| 26 | P2: discovery, OpenCode and team continuity regress | fixed: the plugin's install lines are the README's step 0; OpenCode symlinks `plugin/skills` whole; the second engineer's `experience add <ref>`, `update` and `share`; `extraKnownMarketplaces` offered in the page; `experience.session_sources` said to serve sessions, not builds |
| 27 | P2: the brief, diagnostics and cost lack measurable contracts | fixed: the proof recognises the sources in the instructions and makes one bank retrieval per host; the MCP log's place per host written; cold bootstrap latency and the aggregate context cost (`claude plugin details`, the session's first-turn tokens) recorded |

### Claude Code

| # | Finding | Answer |
|---|---|---|
| 1 | P1: decision 9 half implemented, no command line carries `--config` | fixed: every line in every command and skill carries `--config <root>/kapso-config.yaml` when the file exists, the root the git top level; the CLI-line test checks each line for it |
| 2 | P1: the baseline run leaves `result.json` where the launch refuses it | fixed, as Codex 8: the baseline runs in a copy; the contract line says so; the test asserts the skill names it |
| 3 | P1: the session-built evaluator's hold-out is unspecified | fixed: the hold-out and its labels live inside the directory passed with `--evaluation` (the churn fixture's `private/` named by `evaluation/private_dir.txt`), never under `--data`; the protocol names the split rule and the leakage checks (time order, grouping, duplicates); a criterion the data cannot measure is said plainly |
| 4 | P1: the fifteen-minute churn budget delivers nothing | fixed, as Codex 20: thirty minutes and three experiments, a delivered candidate required, the target not expected to be met (the review is asked of a candidate below target) |
| 5 | P1: the sidecar mirrors the wrong axis | fixed, as Codex 12: each host's own control, no mirror; Codex's parser drops `user-invocable` anyway, so the body says "called by `kapso-build`, never from a menu" |
| 6 | P1: export cannot reuse the staging's writers; they write a campaign session's artifacts | fixed, as Codex 10 and 11: export's own writer table per host and attachment kind, the union by `listed()`, `ENGINE_HOOKS` and every hook excluded and said, the guardrails page written as `kapso-harness-<name>.md` with the include line printed, the person's `CLAUDE.md`, `AGENTS.md` and `.claude/settings.json` never written |
| 7 | P1: `/kapso:learn` and `experience add` cannot finish in a tool call | fixed, as Codex 13: `--detach` on both, the one helper, `kapso watch learning/status` as the follow |
| 8 | P1: the first impression is a failed server; setup does not fix its own session | fixed: `kapso-mcp` connects with every gate off (the campaign tools are always there, the notes in its instructions) instead of exiting; the setup skill's closing lines say how the session gets the tools (`/mcp` reconnect on Claude Code, a new session on Codex); the README and the page say what the first session shows before setup and where each host's MCP log is |
| 9 | P2: a stale reference in the config takes every tool down | fixed, as Codex 7: a config-listed source that does not exist leaves the bank gate off with the add line; `--experience` stays strict |
| 10 | P2: the key's name and the scope semantics | fixed: `experience.session_sources`; the server notes a scoped bank resolving to zero cards; the offer is `mine:all`; the config does not name the session's harness (nothing in the config names a harness, by WP2's rule) |
| 11 | P2: the campaign gate under-specified in five places | fixed: `brief` is a path (`goal` the one-line form), the receipt composed from the receipt file and the known paths, the subprocess's working directory the server's, `sys.executable -m kapso.cli` never `kapso` from PATH, the config path through `GateConfig`; a launch is refused when `kapso` is not on PATH, so no campaign runs from a bootstrap environment |
| 12 | P2: acceptance lines with no step | fixed: the staged-bank step (WP3's proof bank as `mine`, `session_sources` set, the intro and a card read on both hosts), learn's launch, the share and the second engineer are rows of the matrix |
| 13 | P2: the Codex half is thinner than "both hosts" | fixed: the matrix names each row's Codex evidence (setup, build, inbox, review, deploy, the fraud case, harness new, export's files, the brief, the tools, the triggers) and the deferred rows (improve, learn, share, the cold install, the bootstrap latency); the acceptance reads per host and names the ship bar |
| 14 | P2: the pin resolves a released wheel without `kapso-mcp` | fixed: the version is `0.8.0.dev1` from change 1 (the version test pins it), the risk's text corrected; the bootstrap branches cannot verify an entry point that no index has yet, so the release gate does |
| 15 | P2: the plugin's skills leak into campaign sessions | fixed, verified: they do on both hosts; the Claude adapter's `enabledPlugins` hides them (verified), Codex's `-c` switch does not, so the Codex adapter stages an execpolicy rule and the descriptions say "never inside a Kapso campaign session"; the proof lists a campaign session's skills and tools |
| 16 | P2: the skill lab re-run dropped silently; the page's old table | fixed: the Scope says the trigger suite and the proof round replace the lab's with-and-without table, the lab's prompts and rubrics ported; the page's table goes |
| 17 | P2: the trigger suite's bar and its forty per cent | fixed: eighteen of twenty per skill with no cross-skill false positive, the near misses half cross-skill confusions and half no Kapso skill, a clean profile, two runs; `claude plugin eval` and the `tool_used` grader exist on 2.1.310 (the help and the docs), the Codex runner is the fallback's shape |
| 18 | P2: no budgets file; three budgets without a key; the record labelled S2 | fixed: `tests/semantic/budgets.json` with one entry per step, rounds mapped to messages, the hand-judged budgets named, the record's `test` `S2-mechanical` |
| 19 | P3: `--format claude\|codex` a third name for the hosts | fixed: `--host claude_code\|codex`, `--config` on the signature |
| 20 | P3: the commands' bodies unspecified | fixed: the template with one full body, the empty-argument rule per command, no procedure in a body |
| 21 | P3: the fold's edits under-listed; stale facts survive | fixed: change 2 lists each edit, the two stale forms join the retired-name patterns |
| 22 | P3: the tree's sidecar rendering; `bank` omitted from the default gates | fixed |
| 23 | P3: the version in seven places | fixed: the marketplace entry carries no version (the manifest's wins), one copy fewer |
| 24 | P3: contracts with no test (the manifests' lists, the launcher's bit, the sources) | fixed: in `test_plugin_tree.py` |
| 25 | P3: `/kapso:doctor` and `/kapso:experience` pass-throughs; `/kapso:resume` without the diagnosis | fixed in part: `doctor` dropped (ten commands); `experience` kept, the team's moment, said why; `resume`'s body says the diagnosis comes first |
| 26 | P3: OpenCode one skill, no MCP wiring | fixed: the whole folder symlinked, skills only, said |
| 27 | P3: the round's data and clone | fixed: the proof script generates each fixture's data and places the clone, said in Tests |
| 28 | P3: `extraKnownMarketplaces` nowhere | it is on the page (the Interface's marketplace paragraph) |
| 29 | P3: CI's newest CLI can break the gate | fixed: the workflow pins the CLI's version |

**The owner's ten decisions, checked.** Held: 2, 4, 5, 8, 10. Reasoned
and recorded: 1 (the commands are Claude Code's; Codex has the skills
and the sidecars), 3 (narrowed on Codex by a host fact), 6 (twice: WP3's
explicit loading, the brief as the server's instructions), 7 (the tools
land last in this package). Decision 9 was drift in the first plan and
is now the rule above. The owner checks the decisions.

## Built

Branch `wp7-plugin` off `redesign` at `e792fadd`, the commits below, each
with its tests and the gate green (the last full gate before the round:
1,832 passed, 27 skipped, 2 deselected after change 6; green again after
change 8; the docs coverage check 44 commands and methods, the snippet
check 6 quoted files, `mint validate` and `mint broken-links` passing).

| Commit | What landed |
|---|---|
| `dc196dfe`, `b39c44b5`, `2ab71462` | the sub-plan and its planned decisions; its two revisions after the cross-model review (Codex 27, Claude Code 29 findings) and the host probes |
| `4fe4d651` | the plugin's tree, the three manifests, the host MCP files, the launcher with its pin, the marketplace files, the version pinned across them, the validator in the suite (change 1) |
| `097dcec6`, `d5362e6d` | `kapso build --stop` with `budget.stop_grace_seconds`; `--detach` on `kapso learn` and on an ingest through the one detach helper (change 3) |
| `5c04471a` | the operating skill folded into `plugin/skills/kapso`, migrated to the redesign's verbs with the diagnosis section; `build_parser()`; the CLI-line test; the retired-name check reading `plugin/`; `skills/` deleted (change 2) |
| `32692ea8` | `kapso-setup`, `kapso-build`, `kapso-evaluation` and the `/kapso:setup`, `/kapso:build` commands (changes 4 and 5) |
| `00000058` | `kapso-review` and the operating commands `watch`, `inbox`, `resume`, `learn`, `deploy`, `experience` (change 6) |
| `fbb02541` | `kapso-harness`, `/kapso:harness`, `kapso harness export` with its tests on the trading example (change 7) |
| `e53d0863` | the `campaign` gate, `experience.session_sources`, `kapso-mcp`'s config rule, version line, brief and always-connect, the plugin kept out of campaign sessions on both hosts (change 8) |
| `0f323983` | the trigger suite under `plugin/evals/` and its two runners (change 9) |
| `a27a88e5` | the plugin page, the README's step 0, the installation page's `/kapso:setup`, the reference lines, the superseded notes, the validator's CLI pinned (change 10) |
| `1f952164`, `3e2ab47b` | the round's driver, budgets and report; `kapso --version` and `kapso-mcp --version` (change 11) |
| `1829844b` to `2a486161` | the round's findings as they landed: the driver's fixes (the wheel copy, the question among the closing lines, the second user's home, the pause as its own step, the token in each fixture's `.env`, an approval without a question mark), the churn example on pandas 3, the evaluation skill's churn note, the decisions of the build |
