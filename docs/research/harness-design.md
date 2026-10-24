# Kapso harness: the design

Settled 2026-10-23 on the `kapso-plugin` branch. The authoring guide is
`harness-authoring-guide.md` beside this file; the worked example is
`examples/harnesses/trading/`.

## 0. Three layers

**The engine** is the machinery: it works a goal until it is met, measures
every attempt with an evaluation the agents cannot touch, keeps every step on
record, within a budget. It is built from seven modules, each one or more agent
sessions:

| Module | What its agents do |
|---|---|
| setup | turn the user's call into a runnable task: data in place, evaluation registered, task statement written |
| ideation | propose the next change |
| implementation | build the change on a branch and run the evaluation |
| verification | keep the evaluation honest: check the attempt, register the measurement, void bad attempts |
| feedback | score the attempt from the diff and the evaluation output; say what next; say when done |
| learning | mine, grade and bank lessons from the run |
| deployment | adapt the winner to a target and run it |

**The harness** is the domain's playbook, one per domain, used for every task
in that domain. It is meta-knowledge: how work is done here, with what, under
which rules. It attaches to the modules' agents as instruction pages, skills,
tool servers, delegates and hooks. It never knows the task, and it never
configures the engine.

**The task** arrives at build time and stays out of the harness:

```python
kapso = Kapso()
kapso.load_harness("trading")                        # bundled name, path, or git URL
solution = kapso.build("Sharpe above 1.5 out of sample, drawdown under 20%",
                       evaluation="./backtest",      # this task's evaluator, or a criterion to build one from
                       data="./prices", repo="./strategy", budget=Budget(hours=8))
software = kapso.deploy(solution, target="paper-trading")   # the target is the call's, or the config's default
lesson = kapso.learn(solution)
```

Precedence is fixed: engine rules, then the task's constraints, then the
harness. A harness explains how to discover and respect the task's rules; it
never carries their values.

## 1. Layout

Plugin-shaped. An engineer who has built a Claude Code, Codex or Cursor plugin
recognises every directory; the Kapso-specific part is one YAML file and one
`instructions/` directory.

```
trading/
├── harness.yaml          identity, environment, which module gets what
├── instructions/         guardrails.md for every module, <module>.md for one; attached by filename
├── skills/               <name>/SKILL.md with scripts/ and references/          (plugin standard)
├── agents/               <name>.md: name and description front matter, then the prompt   (plugin standard)
├── mcp.json              tool servers; ${PLUGIN_ROOT} resolves to the harness   (plugin standard)
├── servers/              code behind local tool servers
├── hooks/                <name>/hook.json in the host's hooks format, with its script beside it
└── requirements.txt      what the bundled tooling needs
```

The minimal harness is two files: `harness.yaml` with `schema_version`, `name`
and `description`, plus one instruction page. `kapso harness new` produces
exactly that.

## 2. harness.yaml

Every module has the same four fields, and they mean the same thing on every
module: what the module's sessions get.

```yaml
schema_version: 1
name: trading
version: 0.1.0
description: Research, implement, verify and deploy systematic trading strategies.

environment:                # prerequisites, prepared in the run's environment
  python: requirements.txt  # a requirements file
  commands: []              # external commands that must be on PATH
  gpu: false

modules:                    # any of the seven; a module left out still gets its pages
  <module>:
    skills: []              # directories under skills/
    mcp_servers: []         # keys in mcp.json
    agents: []              # delegates: files under agents/ the session may hand work to
    hooks: []               # directories under hooks/, each holding a hook.json
```

Rules short enough to remember:

- `instructions/guardrails.md` applies to every module; `instructions/<module>.md`
  to that module, after it. The guardrails page holds the domain's standing
  rules and where to look. There is no memory file.
- Everything else is defined once and listed where it applies. Lists are
  complete; nothing is inherited between modules. A skill or a hook wanted in
  six modules is listed in six modules. Adding a file never exposes a
  capability; a list does.
- Delegates inherit the module's pages, skills and servers, under the engine's
  permissions.
- References resolve by kind and are local to the harness: a skill name is a
  directory under `skills/`, an agent name a file under `agents/`, a server
  name a key in `mcp.json`, a hook name a directory under `hooks/`. A skill
  that documents a server carries the server's name.
- Engine rules and the task's constraints override anything a harness says.

Anything the engine would have to parse is not a harness field. Exploration
axes are a list in the ideation page, or in the goal the user gives at build
time. What verification checks, and with what, is the verification page plus
the delegates and skill scripts it names. The deployment target is the
`deploy()` call's or the config's. Routing between modules is the engine's and
deterministic: a skill attached only to implementation cannot be used in
ideation. Inside a session the model chooses among the module's attachments,
guided by the page and the descriptions.

## 3. What each module receives, and what each attachment does

| Module | Receives | Returns |
|---|---|---|
| setup | goal, repository, data, evaluation reference, the setup page and attachments | the task statement; prepared resources, mounted for every later session under `prepared/<name>` and listed in the statement |
| ideation | the task statement, attempts so far with verdicts | candidate ideas |
| implementation | the chosen idea, the branch, the evaluation command | the attempt |
| verification | the attempt's diff and its evaluation output | the registered measurement and the attempt's validity |
| feedback | diff, evaluation output, the verification result | score, feedback, continue or stop |
| learning | the run's trajectory | lessons |
| deployment | the selected solution, its repository and artifacts, the target and options of the call | the deployment result |

Every session finds the task statement at the path the engine names in its
prompt (goal, constraints, evaluation reference, prepared resources, harness
name and version), prepared resources under `prepared/`, and, in verification
and feedback, the attempt's diff and evaluation output at named paths. Task
constraints reach agents that way; the harness tells them to read it, never
what it says.

- **instructions**: appended to the module's prompts under a "Domain guidance"
  heading. The engine's prompts stay; the harness adds.
- **skills**: staged where the coding agent discovers them in the session
  workspace (`.claude/skills`, `.agents/skills`), supporting files intact, and
  listed in the prompt. Scripts resolve from `KAPSO_HARNESS_ROOT`, which every
  session and server gets.
- **mcp_servers**: the named servers from `mcp.json` mounted beside the
  engine's own tools, started in the session workspace unless `cwd` says
  otherwise. Agent Plugins schema: a `mcpServers` map of stdio servers
  (`command`, `args`, `env`, `cwd`) or `streamable-http` servers (`url`,
  `headers`), `${PLUGIN_ROOT}` expanded in args, env values and cwd. Env
  references name variables; values come from the user's environment and
  `.env`, never from the harness. `kapso doctor` lists the names a harness
  needs.
- **agents**: delegates. On a CLI without sub-agents the engine runs the agent
  as its own session with the agent file as its prompt. A delegate reports to
  the session that asked, in whatever form the page asks for.
- **hooks**: the listed hook files merged into one and staged for the session;
  section 5.
- **environment**: `python`, `commands`, `gpu`. Nothing here selects the
  engine's agent model, provider or runner.

The engine records the harness name, version and content hash with every run
and lesson.

## 4. Checks

A domain's checks are written, not configured. The verification page says
what to look for and with what; a delegate does the judgment; a skill script
does the deterministic part; the engine's verification module, which always
runs, turns the findings into the validity verdict. For the trading example:

- `instructions/implementation.md` says: before launching the evaluation, run
  the lookahead-scan skill's script on your diff and resolve or justify every
  finding. That is the check before the costly backtest.
- `instructions/verification.md` says: run the same script on the final diff,
  ask the lookahead-auditor for the judgment a pattern cannot make, and void
  the attempt on a finding with evidence the implementer did not justify.
- `instructions/feedback.md` says: ask the risk-reviewer on every evaluated
  attempt; its report says whether the attempt stayed inside the task's
  limits, and a broken limit caps the score.

What the engine guarantees: verification runs on every attempt with its page
and attachments, and its validity verdict is the engine's to act on. What it
does not guarantee: that a page was read to the end. A check that must bind
at the moment of a tool call is a hook. A check that must bind regardless of
the model is a boundary: the engine's permissions, a credential-holding
server's own guard, the task's evaluator.

## 5. Hooks

A hook is a directory under `hooks/` holding a `hook.json` in the host's own
hooks format (events, matchers, commands) and the script the command runs.
It is defined once and listed on every module whose sessions should carry
it, like a skill. `PreToolUse` can deny or rewrite a call with a reason the
model sees; `PostToolUse` can add context or run a formatter; `Stop` can ask
for one more pass; `SessionStart` can add context.

How the engine integrates them: for a session of module M it takes
`modules.M.hooks` in manifest order, reads each `hooks/<name>/hook.json`,
concatenates their event lists into one hooks file, expands `${PLUGIN_ROOT}`
to the harness path, and stages the result where the host reads hooks (Claude
Code: the session's settings; Codex: the workspace `.codex/hooks.json`,
launched with the trust bypass). It injects nothing into events and no script
needs to know its module: the manifest is the whole assignment. Hook commands
run in the session workspace, so `prepared/` and `results/` are relative
paths.

Hooks catch mistakes on the paths they can see: a read under `holdout/`
through the file tool, a `kaggle competitions submit` typed in the shell, a
`curl` to the web. They are not a boundary: a script can read a file without
a tool call, a shell matcher does not see what a process does. There are no
engine lifecycle hooks: approvals go through the inbox, notifications are the
user's config.

The trading example defines six: `session-brief` (SessionStart, context),
`deny-web-fetch` (PreToolUse on the shell), `protect-prepared` (PreToolUse on
the file tools), `deny-snapshot` (PreToolUse on one server tool, matcher
`mcp__market-data__snapshot`), `scan-writes` (PostToolUse advisory after a
write, sharing the lookahead-scan skill's rules) and `require-results` (a Stop
gate that asks once). The first three are listed on six modules, the snapshot
denial on implementation and deployment, the last two on implementation only.
Setup may build the snapshot because setup does not list the denial.

## 6. Where knowledge goes

The question every author asks: "I know something about this domain; where
does it go?" Cheapest form first. Always-on text is the expensive form: every
word of it is in context on every session, competing with the agent's own
work.

| The knowledge is... | Put it in | Reaches the agent |
|---|---|---|
| a rule that holds for every task in the domain | `instructions/guardrails.md` | always, every module |
| how one module does its job here, including its axes or its checks | `instructions/<module>.md` | always, that module |
| a procedure for a recognisable situation | `skills/<name>/SKILL.md`, listed on the module | on demand, when the situation arises |
| a deterministic operation agents get wrong by hand | a script inside the skill | when the page or the skill says to run it |
| a bounded investigation with a small answer | `agents/<name>.md`, listed on the module | when the session asks |
| a mistake worth catching at the tool call | `hooks/<name>/hook.json`, listed on the module | at the call |

Three sentences cover the rest. If it must happen, the module's page says so
and the engine's module runs. If it may happen, it is an attachment. If it
must not happen, it is not attached, or denied with a reason, and the real
boundary is the engine's.

Pages stay short: rules and where to look, not essays. Situational knowledge
goes into skills, which cost nothing until invoked. A skill the module page
never mentions is rarely opened; `check` warns about it. There is no memory
file: cross-task memory is the learning module's output, banked in the
knowledge base and scoped by the harness's learning page.

## 7. Never in a harness

An evaluator, a dataset, a goal, a budget, a stop rule, a submission
allowance, a credential value, a model or runner choice for Kapso's own agents,
an engine event, a memory of past tasks, a deployment target choice, or any
field the engine would have to parse. Domain commands, API connections and
model names inside domain content are fine.

## 8. Surface

```
kapso harness new trading                     # the two-file starter
kapso harness check ./trading                 # see below
kapso harness list                            # bundled and installed
kapso harness export ./trading --format claude | codex | cursor
kapso build --config ./kapso-config.yaml --harness ./trading --goal "..." --evaluation ./backtest --data ./prices --repo ./strategy
kapso deploy --harness ./trading --target paper-trading
```

The Python surface is three steps on one object: construct with engine
knobs, load what the run should use, call the verbs.

```python
from kapso import Kapso, Budget, Solution

kapso = Kapso(config="kapso-config.yaml")     # engine knobs only; optional, the packaged config otherwise

harness = kapso.load_harness("trading")       # a bundled name, a path, or a git reference
harness.name, harness.version, harness.hash   # "trading", "0.3.0", "9c1e…"
harness.modules["implementation"]             # {"skills": [...], "mcp_servers": [...], "agents": [...], "hooks": [...]}
harness.missing                               # prerequisites this machine lacks, [] when none

kapso.load_experience("mine")                 # a reserved name, a path or git reference to a bank, or an ingested index's name
kapso.load_experience("leeroopedia")          # order is the order the intro lists them

solution = kapso.build(
    "Sharpe above 1.5 out of sample on the 2022-2024 window, max drawdown under 20%",
    evaluation="./backtest", data="./prices", repo="./strategy",
    output="../btc-momentum", budget=Budget(minutes=480),
)
solution.branch, solution.score, solution.evaluator.version, solution.campaign   # names after the WP1 naming review (DECISIONS.md)
solution.harness                              # the triple the run was made with

software = kapso.deploy(solution, target="paper-trading")
experience = kapso.learn(solution)
```

- `Kapso(config=...)` reads engine knobs and nothing else; nothing starts.
- `load_harness(ref)` resolves, runs `check` and raises on failure, computes
  the hash, reads prerequisites into `missing` without raising, sets the
  object's harness and returns the handle. A second call replaces it: one
  object, one harness.
- `load_experience(ref, scope=None)` resolves by the reference grammar in
  `onboarding.md`, confirms the source is reachable, pins it, appends it to
  the object's sources and returns the handle (`kind`, `resolved`, `head`,
  `provenance`). Nothing is served until a verb runs. Scope defaults to the
  loaded harness.
- `build(...)` refuses while `missing` is not empty, naming each item and
  where it is read from; then prepares the harness's requirements in the
  run's environment, writes the launch record with the harness triple and
  the sources with their pinned heads, runs the modules with each session
  staged from the manifest, and returns a `Solution` carrying the triple.
- `deploy(solution, target=...)` and `learn(solution)` take the harness
  from the object when one is loaded and from the solution's record
  otherwise, so `Kapso().deploy(Solution.open("../btc-momentum"))` works.
  A loaded harness whose name differs from the record is refused; another
  version of the same name is allowed and recorded. The deploy target is
  the argument, with the config's `deployment` section as the default.
- No load at all is valid and is today's generic behaviour: the engine's
  own prompts, nothing attached, nothing served. No harness argument on the
  verbs, no harness or experience in the config, no `serving.enabled`.

`check` fails on: an unsupported `schema_version`; an unknown module or
field; a reference that does not resolve (skill, agent, server or hook); a
skill or agent without `name` and `description` front matter; a malformed
`mcp.json` or `hook.json`, a hook with an unknown event, or a hook command
whose script is missing; an env value in `mcp.json` that looks like a secret;
a missing requirements file. It reports separately what the machine lacks
(commands, GPU, env variables). It warns on: a skill, agent or hook directory
no module lists; a skill not mentioned in its module's page; an always-on
page over the size the config sets.

`export` writes the host's plugin layout from skills, agents, `mcp.json` and
every hook merged into the host's single hooks file, with a note of what the
host does not reproduce: module routing and the instruction pages, which
become the plugin's README.

## 9. Decisions

Kept from the earlier drafts: the seven modules; explicit routing with pages
by filename; `mcp_servers` not `tools`; `environment`; `libraries` cut; hooks
in the host's own format; no engine lifecycle hooks; host-specific export.

Taken 2026-10-23:

- No memory file. Kapso's learning module and knowledge base already bank
  lessons with evidence.
- The every-module page is `guardrails.md`: standing rules first, then where
  to look. Nothing else is always-on.
- No engine-facing fields. `exploration_axes`, `reviews` with their report
  contract and `when`, and `targets` with `default_target` are gone. Axes are
  a list in the ideation page or in the goal; checks are the verification and
  feedback pages with their delegates and skill scripts; the deployment target
  is the `deploy()` call's or the config's. The harness and the engine config
  never share a key.
- No routing fields either: an always-invoked skill is a page by another
  name, a per-server tool allow-list is two servers, a denied command prefix
  is a hook.
- Hooks are the fourth per-module list, defined once as `hooks/<name>/` with
  the `hook.json` and its script together, and listed wherever they apply,
  exactly like skills. No global hooks file, no hooks-by-filename, nothing
  injected into events.
- `servers/` holds the code behind local tool servers.
- `check` warns when an on-demand skill is never named by its module's page,
  and when a defined skill, agent or hook is never listed.

Recommended, the owner's to overrule:

- Shipped harnesses live under `harnesses/<name>/` in the repository; the
  examples and benchmarks fold into that directory as they are ported.
- The engine's lens planner derives the exploration axes from the ideation
  page and the goal and keeps statusing them per iteration; the `design_axes`
  config parameter is deleted rather than kept beside the page.
- The Harness² editor loop (read trajectories, propose harness edits, probe on
  the same task, keep by contrast) is a learning-module job, designed
  separately once this interface is in code.

## 10. The harness and the engine config

Today a run is configured by one YAML file (`src/kapso/config.yaml`, or a
benchmark's copy) resolved by `load_mode_config` as `defaults` deep-merged
under `modes.<MODE>`. Its contents are engine knobs: which CLI and model each
role runs (`coding_agent`, `feedback_generator`, `evaluation_maintainer`,
`learner`, `inference.roles`, `deployment`), how much (`budget`, `retry`, the
timeouts, `node_expansion_value`, `expansion_lane_env`,
`session_env_defaults`), and which engine features are on (`ideation_gates`,
`implementation_gates`, `inbox`, `knowledge_search`, `cost`, `preflight`).
The harness touches none of these; its schema has no such keys and `check`
rejects unknown ones. The config, in turn, never names a skill, a page, a
server, a delegate or a hook.

What moves, and where to:

| Today | Final design | Why |
|---|---|---|
| `search_strategy.params.design_axes` (RelBench's five axes, "task-specific vocabulary" in the config's own comment) | a list in `instructions/ideation.md`, or in the goal; the planner derives and statuses the axes | the axes are domain prose, not an engine parameter |
| `evolve(additional_context=...)`, `GenericProblemHandler.get_problem_context`, each benchmark's handler code | `instructions/*.md`, `skills/`, `agents/`, `servers/`, `hooks/` | domain prose and code, attached per module instead of concatenated into one prompt |
| `implementation_web: false` (RelBench's temporal-leakage rule) | a hook denying the web tools, listed on implementation; the engine's permission is the boundary | a domain rule enforced at the tool call, not a strategy parameter |
| the deployment target | `deploy(target=...)`, defaulting to the config's `deployment` section | a choice per deployment, config-like, never domain knowledge |

A run is therefore three inputs that never overlap: the config mode (engine
knobs), the harness (domain), and the build call (task). The engine reads the
harness where it reads `additional_context` today, at prompt assembly, and
mounts harness servers beside the gates the config lists: the config's gates
are the engine's knowledge tools (research, experiment history, repo memory,
bank), the harness's servers are the domain's.

## 11. The next layer: the authoring guideline and the authoring plugin

Because the manifest is uniform, everything domain-specific is in the pages,
and the quality of a harness is the quality of its pages. Two things make that
easy, in order:

1. **A guideline per module**, `harness-authoring-guide.md`: what a good page
   contains, with the trading and predictive-modelling examples as worked
   examples.
2. **An authoring plugin** on top of it, `/kapso:harness`, that interviews the
   author module by module, writes the pages, skills, agents and hooks from
   the answers, fills the manifest's lists, and runs `check`. In ideation it
   asks for the axes and writes the list; in verification it asks what must
   never pass and writes the page, the script skill, the auditor and the hook.
