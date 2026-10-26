# Writing a Kapso harness

A harness is one directory per domain. It tells the engine's agents how work
is done in that domain, with what, under which rules, and nothing about any
particular task. This guide says what goes in each part and how to write it.
The design it follows is `harness-design.md` beside this file. The worked
example, referred to throughout, is `examples/harnesses/trading/`.

## 1. What you are writing

Kapso is three layers. The engine runs seven modules (setup, ideation,
implementation, verification, feedback, learning, deployment) and owns the
goal, the evaluation, the budget and the record. The task arrives at build
time: `kapso.build(goal, evaluation=..., data=..., repo=..., budget=...)`. The
harness sits between them: everything a domain expert would tell a new hire
before the first task, and nothing about the task itself.

Three questions decide whether something belongs in the harness:

1. **Is it true for every task in this domain?** A rule about look-ahead is.
   A drawdown limit of 20%, a dataset path, a deadline, a submission
   allowance is not: that is the build call's or the task statement's.
2. **Is it about how Kapso's own agents run?** Models, CLIs, budgets, lanes,
   retries, gates are the Kapso config. The harness and the config never
   share a key.
3. **Would the engine have to parse it?** Then it is not a harness field. The
   harness is pages, skills, delegates, servers and hooks. The engine reads
   lists of names and stages files; it never reads structured domain data.

When layers disagree, the order is fixed: engine rules, then the task's
constraints, then the harness. Write the harness to say *where* the task's
rules are and *how* to respect them, never what they are.

## 2. Start with two files

```
kapso harness new trading
```

```
trading/
├── harness.yaml
└── instructions/guardrails.md
```

That is a valid harness. Grow it one part at a time, and only when you can
name the failure the part prevents or the domain rule it carries. A part you
cannot justify that way costs context on every session and buys nothing.
The usual order of growth: the module pages where the domain has something
to say, then skills for recurring situations, then a delegate for a judgment
the page cannot make, then servers for data or systems the agents must reach,
then hooks for the mistakes you have watched agents make.

## 3. The directory

| Part | What it is | Reaches the agent | Add it when |
|---|---|---|---|
| `harness.yaml` | identity, environment, which module gets what | the engine reads it | always |
| `instructions/guardrails.md` | the domain's standing rules and where to look | every session, always on | always |
| `instructions/<module>.md` | how one module does its job here | that module's sessions, always on | the domain has a say in that module |
| `skills/<name>/SKILL.md` | a procedure for a recognisable situation, with its scripts and references | on demand, when the situation arises | the same situation recurs across tasks |
| `agents/<name>.md` | a delegate: a bounded investigation or judgment with a small answer | when the session asks | the page needs a second pair of eyes |
| `mcp.json` + `servers/` | tool servers the agents call | mounted in the listed modules | agents need data or a system behind a guard |
| `hooks/<name>/` | a `hook.json` in the host's hooks format and its script | at the tool call, session start or stop | a mistake is worth catching at the moment it happens |
| `requirements.txt` | what the harness's own scripts and servers need | the run's environment | the harness ships code |

Everything except the pages is defined once and listed in the manifest where
it applies. Pages are attached by filename.

## 4. harness.yaml

```yaml
schema_version: 1
name: trading                      # [a-z0-9][a-z0-9-]*; what the engine records (the directory may be named anything)
version: 0.1.0                     # required, any string; bump when behaviour changes, the engine records it with every run
description: Research, implement, verify and deploy systematic trading strategies.

environment:                       # every key optional; reported by check, never installed by the engine
  python: requirements.txt         # one path, relative to the harness; checked against python3 on PATH, where servers and hooks run
  commands: []                     # bare program names that must be on PATH
  gpu: false

modules:
  setup:
    skills: [market-data]
    mcp_servers: [market-data]
    hooks: [session-brief, deny-web-fetch, protect-prepared]
  implementation:
    skills: [backtesting, market-data, risk-limits, lookahead-scan]
    mcp_servers: [market-data]
    agents: [lookahead-auditor]
    hooks: [session-brief, deny-web-fetch, deny-web, protect-prepared, deny-snapshot, scan-writes, require-results]
```

Rules:

- `name`, `version` and `description` are required. The module keys are
  exactly `setup`, `ideation`, `implementation`, `verification`, `feedback`,
  `learning` and `deployment`; any other key, anywhere, fails `check`.
- Every module has the same four lists: `skills`, `mcp_servers`, `agents`,
  `hooks`. They mean the same thing on every module. A list is complete:
  nothing is inherited, and a thing wanted in six modules is listed in six
  modules. A list left out is empty; a module left out gets its
  instruction pages and nothing else, so leave a module out when the domain
  has nothing to attach there. Order matters only in `hooks`, which the
  engine merges in manifest order.
- A name resolves by kind: a skill to `skills/<name>/SKILL.md`, an agent to
  `agents/<name>.md`, a server to a key in `mcp.json`, a hook to
  `hooks/<name>/hook.json`. Names may carry hyphens. A reference that does
  not resolve fails `check`.
- There are no other fields. Exploration axes go in the ideation page,
  checks go in the verification page, the deployment target is the
  `deploy()` call's.

Never in the manifest, or anywhere in the harness: an evaluator, a dataset, a
goal, a budget, a stop rule, a submission allowance, a credential value, a
model or CLI for Kapso's own agents.

## 5. Instruction pages

Pages are the heart of a harness and the only always-on part. Every word of
a page is in context on every session of its module, competing with the
agent's own work, so a page is short: rules and where to look, not an essay.
`check` warns above the config's `harness.page_warning_lines`, forty lines.

What the engine puts around a page: the session's prompt carries a
`## Domain guidance (harness <name> <version>)` block holding
`guardrails.md` whole, then the module's page whole, then a `### Paths`
list with the task statement's path and each prepared resource's. A
verification session's prompt also names the attempt's diff, its
evaluation output and the verdict file it must write. So a page refers to
these by name, "the task statement", "the diff", "the verdict", never by a
path it would have to guess. The only files under `instructions/` are
`guardrails.md` and `<module>.md` for the seven module names; another file
there is a warning. A page's heading is free.

Rules for every page:

- **Imperative and checkable.** "Before launching the evaluation, run the
  lookahead-scan script on your diff" beats a paragraph about why look-ahead
  is bad. The agent must be able to tell whether it has done what the line
  says.
- **Name the attachments in the situation that calls for them.** "When the
  change touches signal timing, ask the lookahead-auditor." A skill or
  delegate the page never mentions is rarely used; `check` warns about it.
- **Say where, not what.** "Costs and slippage come from the task statement"
  is right. "Fees are 10 basis points" is a task value and wrong for the
  next task.
- **Only the harness's own conventions are concrete.** `prepared/market-data/`
  and `results/equity_curve.csv` are paths the harness itself introduces, so
  the pages may name them. A path from a particular repository may not
  appear.
- **Situational detail goes to a skill.** If a paragraph only matters in one
  situation, it is a skill, and the page keeps one line pointing at it.

### guardrails.md

The domain's standing rules, read by every module. Its first line tells the
agent to read the task statement and what to look for in it; then four to
seven rules that hold for every task in the domain; then the conventions the
harness introduces.

```markdown
# Trading guardrails (every module)

Read the task statement before anything else: instruments, bar frequency, the
cost and slippage model, the evaluation command and what it measures, the
development and out-of-sample windows, position and leverage limits. The task's
numbers win over anything written here.

## Standing rules

- A signal at time t uses only data stamped at or before t. A position decided
  at t earns from t+1. Fills happen no earlier than the next bar, at the price
  the task's cost model specifies.
- Every price comes from the pinned snapshot through the market-data server.
  No live fetches inside a run.
- If the task names an out-of-sample window, nothing but the registered
  evaluation reads it. Parameter choices come from the development window.
- Report risk in the task's units beside any return metric. A strategy without
  a risk line is unfinished.
```

Not here: procedure for one module, anything that only matters sometimes.

### setup.md

How to turn the user's call into a runnable task in this domain. Say what to
prepare and the name to leave it under, what the domain statement must
record for this domain (the fields later modules will read), and what setup
must not do (no attempt work, no evaluation run, nothing under
`kapso_evaluation/` or `kapso_datasets/`, which the engine verifies
afterwards). The mechanics are the engine's and need no words on the page:
a prepared resource is a directory the session leaves under
`prepared/<name>/` at the campaign root, with whatever files the harness's
convention says (nothing is registered, and the engine lists each name in
the task statement and mounts the directory in every later session at the
same relative path); the domain statement is written to the path the
engine's prompt names, and the engine puts it into the task statement.

```markdown
1. Read the task's data reference. Build a pinned snapshot with the
   market-data skill's `snapshot` tool: one file per instrument, closed bars
   only, and a `MANIFEST.json` with the source, the range and a content hash.
2. Write the task statement: instruments, bar frequency, the cost and slippage
   model, the evaluation command and what it measures, the development and
   out-of-sample windows if the task names them, position and leverage limits,
   the budget.
3. Return the snapshot as a prepared resource named `market-data`. Do not run a
   backtest in setup.
```

### ideation.md

How ideas are proposed here. This is where the exploration axes live: a
numbered list of the kinds of change the domain knows, with the instruction
to status each one every iteration and to say which axis a proposal moves on.
Then what every proposal must state, which catalogue skill to consult, and
what does not count as a new idea.

```markdown
Exploration axes to keep in play. Status each one every iteration as active,
saturated with evidence, or deferred, and say which axis a proposal moves on:

1. signal construction
2. feature representation
3. portfolio construction
4. execution and costs

- Every idea states its family, its economic rationale (who is on the other
  side of the trade and why they pay), the regime in which it should lose, and
  its expected turnover against the task's cost model. The strategy-families
  skill is the catalogue.
- An iteration that only re-tunes the previous signal is not a new idea.
```

A user may also name axes in the goal at build time; the page is the
domain's default, the goal can add to it.

### implementation.md

The discipline of building an attempt. In order: the first thing to get
right, where inputs come from, how to develop (subsample, then full), the
check to run before launching the evaluation, the delegate to ask and when,
and what to save for the reviewers. The files an attempt saves (the
`results/` names below) are the harness's own convention, introduced here
and required by its hooks and reviewers; the engine requires none of them.

```markdown
- Timestamp discipline first: compute signals from a frame that stops at t,
  then shift the position by one bar. The backtesting skill has the reference
  pattern and how to read the output.
- Develop on a subsample of the development window (one instrument, one year)
  until the pipeline is correct, then run the full evaluation once. Do not
  sweep parameters against the evaluation output.
- Before launching the evaluation, run the lookahead-scan skill's script on
  your diff. Fix every finding, or write in the attempt notes why it is safe.
  When the change touches signal timing, joins across sources or resampling,
  also ask the lookahead-auditor; its report is cheaper than a voided attempt.
- Finish with the risk line from the risk-limits skill beside the return
  metric, and save `results/equity_curve.csv` and `results/trades.csv` with
  the attempt.
```

### verification.md

What makes an attempt invalid in this domain, and how to find out. Write the
steps in order (script, then delegate, then decision), then what the failure
modes look like here, then what voids an attempt as opposed to what merely
lowers its score. The engine runs one verification session per scored
attempt when the harness has this page or a verification attachment, in a
checkout of the attempt, with the diff and the evaluation output at paths
its prompt names; the session writes the verdict file the prompt names
(`valid` or `void`, a summary, findings with evidence), and a void attempt is
never delivered. The page decides what the session checks, not how the
verdict is filed.

```markdown
Keep the evaluation honest. Do these on every attempt, in this order:

1. Run the lookahead-scan skill's script on the final diff. A finding the
   attempt notes do not justify is evidence against the attempt.
2. Ask the lookahead-auditor for the judgment a pattern cannot make. Give it
   the task statement, the diff and the evaluation output.
3. Decide validity. A look-ahead or leakage finding with evidence voids the
   attempt; say so in the verdict with the evidence. Otherwise register the
   measurement.

What look-ahead looks like: backward shifts, centred windows, joins on a future
timestamp, resampling that closes a bar before its last trade ...
What impossible numbers look like: a Sharpe far above the asset class's
history, no losing months ... Treat them as evidence of a bug until shown
otherwise.
```

### feedback.md

How to score and what to say next. Score against the task's own limits, and
name the delegate that checks them; say what counts for more than the
headline number; require the "next axis" sentence; say what "met" means in
the domain's terms. The stop itself is the engine's and the target the
task's: a page never sets a stop rule, it tells the judge what to weigh
before it says the target is met.

```markdown
- Ask the risk-reviewer on every evaluated attempt. Its report says whether
  the attempt stayed inside the task's limits; a broken limit caps the score
  whatever the return.
- Prefer robust to spectacular: consistency across sub-periods and a flat
  parameter neighbourhood count for more than a higher headline number.
- Say which exploration axis from the ideation page the next attempt should
  move on, and why, with the evidence from this attempt.
- The task's target is met only with every limit kept; an attempt that
  clears the number and breaks a limit is not there yet, say so.
```

### learning.md

The vocabulary lessons are scoped by, and what a lesson is not. Short.

```markdown
Scope every lesson by asset class, bar frequency, strategy family and cost
regime. A lesson states the operation that worked or failed and the evidence
from the attempts, never this task's parameters, returns or instruments as
facts for the next task.
```

### deployment.md

How to adapt the winner to each target the domain uses. Which skill carries
the workflow for which target, what never happens, what to return as the
endpoint. The target itself comes from the `deploy()` call or the config.

```markdown
The target comes from the `deploy()` call or the Kapso config, never from this
harness. For the paper-trading target follow the paper-trading skill; for the
engine's own targets (local, docker, ...) follow the engine's workflow.
Deployment never touches a live account.
```

## 6. Skills

A skill is a procedure for a situation that recurs across tasks: how to run
a backtest with timestamp discipline, how to use the market-data server,
what the standard risk line is, the catalogue of strategy families. It costs
nothing until the situation arises, which is why most domain knowledge
belongs here and not in a page.

```
skills/backtesting/
├── SKILL.md
├── scripts/        optional: deterministic helpers the skill tells the agent to run
└── references/     optional: long material the skill points at, read only when needed
```

The front matter is what the agent sees before opening the skill, on both
Claude Code and Codex, and it is all they see:

```markdown
---
name: backtesting
description: Build and run a backtest with timestamp discipline, then read its output. Use when implementing a strategy, running the task's evaluation, or checking signal timing, fills and costs.
---
```

- `name` equals the directory name.
- `description` is one or two sentences: what the skill does, then "Use
  when ..." with the situations that call for it. This sentence is what makes
  the agent open the skill; write the situation, not the topic. A
  description with a colon or another YAML special character is quoted.
- Other front matter keys are host-specific and are not read by Codex;
  `check` tolerates and ignores them. Do not rely on them.

The body: a short heading, the procedure or the reference pattern (code
beats prose where there is code), how to run the task's own evaluation
where that matters, how to read the output, the pitfalls. Under a hundred
lines; longer material goes to `references/`.

A deterministic operation that agents get wrong by hand is a script inside
the skill, and the skill says exactly how to invoke it:

```
git diff main...HEAD | python3 $KAPSO_HARNESS_ROOT/skills/lookahead-scan/scripts/scan.py
```

`KAPSO_HARNESS_ROOT` is set in every session, for hooks and servers too, and
names the harness directory. A script prints something a session can act
on, and its exit code says whether there is something to act on; the exact
codes are the skill's own convention, written in the skill. A script runs
on `python3` from PATH with its own directory on `sys.path`, so it may
import a sibling module by name; it is not run by `check`, and a path a
`SKILL.md` quotes is not checked, so a typo there is silent until a session
hits it. The campaign's base branch is `main`, so `git diff main...HEAD` is
the attempt's diff in every campaign.

Conventions:

- One skill per situation. A skill that covers two situations gets opened
  for neither.
- A skill that documents a server carries the server's name (`market-data`
  the skill explains `market-data` the server).
- A deployment workflow is a skill like any other, named for its target,
  and its body says what the deployment session has and what to report.
- List the skill on every module whose sessions may need it, and mention it
  on that module's page in the sentence that describes the situation.

## 7. Delegates

A delegate is an agent the module's session may hand work to: a bounded
investigation whose input is large and whose answer is small, or a judgment
the page cannot reduce to a rule. The trading example has two: an auditor the
implementer asks before submitting a timing change and the verifier asks on
every attempt, and a risk reviewer the feedback writer asks on every
evaluated attempt.

```markdown
---
name: lookahead-auditor
description: Audits one attempt for look-ahead and leakage in signal timing, joins, resampling and data access, and reports pass, fail or inconclusive with evidence.
---
You audit one attempt of a trading strategy for look-ahead and leakage. You
never edit files.

Read, in this order: the task statement, the diff, then the evaluation output
when it is present. Open the changed files in the workspace where the diff is
not enough.

Check the verification page's list: ...

Report to the session that asked you: an outcome (pass, fail or inconclusive),
a one-paragraph summary, and findings, each with the rule and evidence a
reader can open. `fail` only with such evidence. `inconclusive` when the change
is beyond your reach, and say what would settle it.
```

The prompt has four parts: the role and what the delegate never does, the
reading order, what to check (pointing at the page or skill that holds the
list, so the two never drift), and the report's shape. The front matter is
`name` (the file's name) and `description`; nothing else is declared, no
tool name, arguments or report schema: a session calls a delegate by name
because the page told it to (on Claude Code it is a sub-agent, on Codex a
role, and the engine stages it either way), and the report's shape is the
convention the prompt sets. A delegate's prompt begins with the module's
guidance block, and it inherits the module's skills and servers, so it can
read the same material the session reads; a checklist owned by another
module's page is reached through `KAPSO_HARNESS_ROOT`. List it on every
module whose sessions may call it, and say on the page when to call it.

## 8. Servers

A server is for data or a system the agents must reach through a guard: a
pinned market-data store, a paper-trading account, a warehouse with a
restricted role, a submission office that holds the key. If the need is only
to run a command-line tool, a skill that documents the tool is enough; a
server earns its place when it holds state or a credential, or when the
engine must be able to mount it in some modules and not others.

```json
{
  "mcpServers": {
    "market-data": {
      "command": "python3",
      "args": ["${PLUGIN_ROOT}/servers/market_data.py"]
    },
    "broker": {
      "command": "python3",
      "args": ["${PLUGIN_ROOT}/servers/broker.py"],
      "env": {"BROKER_API_KEY": "${BROKER_API_KEY}"}
    },
    "docs": {
      "type": "streamable-http",
      "url": "https://docs.example.com/mcp",
      "headers": {"Authorization": "${DOCS_AUTHORIZATION}"}
    }
  }
}
```

- The file is the Agent Plugins `mcpServers` schema: stdio servers with
  `command`, `args`, `env`, `cwd`, or streamable-http servers with `type`
  (`streamable-http`), `url` and `headers`. `${PLUGIN_ROOT}` is the harness
  directory. A name matches `[A-Za-z0-9_-]+`; `gated-knowledge` is the
  engine's own server. The script's path and file name are free, named in
  `args`.
- A server starts in the session's directory unless `cwd` says otherwise,
  so it can find `prepared/<name>` by a relative path; `KAPSO_HARNESS_ROOT`
  is set for it, and on Codex the engine forwards the variables its `env`
  names, which that host does not inherit.
- Every `env` and `headers` value is one `${NAME}` reference and nothing
  else, a secret or a setting alike (`"BROKER_API_KEY": "${BROKER_API_KEY}"`,
  `"DBT_TARGET": "${DBT_TARGET}"`, `"Authorization": "${DOCS_AUTHORIZATION}"`
  with the `Bearer` prefix inside the variable); an `env` entry names the
  variable it forwards, never another one, because Codex forwards by
  name. The value comes from the user's environment or `.env` beside the
  run. A literal, a reference inside a longer value or an `env` key that
  references another name fails `check`, and an unset reference is
  reported as a need of the modules that mount the server.
- A stdio server is a small Python file on the `mcp` package's FastMCP:

  ```python
  from mcp.server.fastmcp import FastMCP

  server = FastMCP("market-data")

  @server.tool()
  def get_bars(instrument: str, start: str, end: str) -> list[dict]:
      """Bars of one instrument between two timestamps, from the pinned snapshot."""
      ...

  if __name__ == "__main__":
      server.run()          # stdio
  ```

  The decorated function's docstring is the description the agent sees;
  `mcp>=1.2` in `requirements.txt` is what this costs.
- List the server on the modules that may use it and nowhere else. A tool
  that must not be used in a module is kept out by not mounting its server
  there, or by splitting the server in two; a hook catches the slip.
- Document every server with a skill of the same name: the tools, what they
  return, the pitfalls the server does not fix. The tools' own docstrings
  are what the agent sees in the tool list; keep them one line each.
- Code lives under `servers/`. A server that a deployed program must also
  use is written as a library with the server on top, so the deployed
  program imports the same fill or query logic the agents used.

## 9. Hooks

A hook catches a mistake at the moment it happens, adds context a session
should have from its first turn, or asks for one more pass before a session
ends. It is not a boundary: a hook sees one tool call, not what a process
does afterwards. Boundaries are the engine's permissions, a server's own
guard and the task's evaluator.

A hook is a directory with the host-format `hook.json` and the script it
runs, defined once and listed on every module whose sessions should carry
it:

```
hooks/deny-snapshot/
├── hook.json
└── deny_snapshot.py
```

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "mcp__market-data__snapshot",
        "hooks": [
          {"type": "command", "command": "python3 ${PLUGIN_ROOT}/hooks/deny-snapshot/deny_snapshot.py"}
        ]
      }
    ]
  }
}
```

The file is Claude Code's hooks format, and the engine hands the merged
file to both hosts (`--settings` on Claude Code, `.codex/hooks.json` on
Codex). The events are `SessionStart`, `SessionEnd`, `UserPromptSubmit`,
`PreToolUse`, `PostToolUse`, `PermissionRequest`, `Stop`, `SubagentStart`,
`SubagentStop`, `PreCompact` and `PostCompact`; `matcher` is a regular
expression over the tool's name and is left out on events without a tool.
The command string runs through a shell in the session's directory, so an
environment prefix such as `PYTHONPATH=... python3 ...` works; name
`python3`, which a stock Ubuntu has, never `python`. Two hooks on the same
event both run.

The protocol is the host's: the script reads one JSON event on stdin and
prints one JSON decision on stdout; exit 0 with nothing printed is no
opinion. What the event holds, per tool: `tool_input.command` for `Bash`;
`tool_input.file_path` for `Write`, `Edit` and `MultiEdit` on Claude Code;
on Codex the file tool is `apply_patch`, a matcher `Edit|Write|MultiEdit`
fires on it too, and `tool_input.command` is the patch text with
`*** Add File:` and `*** Update File:` lines, so a file hook reads both
shapes; a server's tool is `mcp__<server>__<tool>` on both hosts. There are
five shapes worth knowing, each in the trading example:

| Shape | Event and matcher | Output | Example |
|---|---|---|---|
| context at start | `SessionStart` | `{"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": "..."}}` | `session-brief` reads the snapshot manifest and tells the session which market it is on |
| deny with a reason | `PreToolUse`, matcher `Bash` or `Edit\|Write\|MultiEdit` | `{"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny", "permissionDecisionReason": "..."}}` | `deny-web-fetch`, `protect-prepared` |
| deny one server tool | `PreToolUse`, matcher `mcp__<server>__<tool>` | same | `deny-snapshot`, listed on the modules where the server is mounted but the tool must not be used |
| advisory after a write | `PostToolUse`, matcher on the file tools | `{"hookSpecificOutput": {"hookEventName": "PostToolUse", "additionalContext": "..."}}` | `scan-writes` scans the written file and feeds findings back while the change is fresh |
| ask once at the end | `Stop` | top level, `{"decision": "block", "reason": "..."}`; the event's `stop_hook_active` is true once the session is already continuing because of a stop hook | `require-results` asks for the results files, and stays silent when `stop_hook_active` is set |

Rules:

- The reason is for the model. Write it as the instruction the model should
  follow instead: "Use get_bars on the market-data server."
- A hook script knows nothing about modules. Where it applies is the
  manifest's decision: list it on the modules that need it, and leave it off
  the ones that do not. Setup may build the snapshot because setup does not
  list `deny-snapshot`.
- A Stop hook asks once. Check `stop_hook_active` in the event and stay
  silent when it is true, so a session that truly cannot comply is not
  trapped.
- Share rules with the skill that owns them. The `scan-writes` hook imports
  the lookahead-scan skill's rule list, so the hook, the skill and the
  auditor agree.
- Keep hook scripts fast and dependency-free where possible; they run on
  every matching call, on `python3` from PATH, where the harness's
  requirements are installed when the user followed `check`; the standard
  library is the safe floor.
- A malformed or unexpected event is no opinion, not a denial: enforcement
  is the engine's, a hook is a mistake catcher.

## 10. Environment

`requirements.txt` lists what the harness's own scripts and servers import
(`mcp` for a server, `pandas` for a script that reads bars), not the
domain's tooling; `environment.python` names it, one path relative to the
harness. `commands` names external programs that must be on PATH, bare
names (`dbt`, `git`); `gpu: true` says a usable GPU is required. Every key
is optional.

Nothing is installed by the engine. `kapso harness check` reads each pin
against `python3` on PATH, the interpreter the harness's servers, hooks and
scripts run on, and reports what is missing or too old with the
`python3 -m pip install -r <file>` line; a program a hook or a server
runs is checked without being listed. A missing pin, program, variable or
GPU is a need, not a failure: `check` still exits 0 and says so, and a verb
refuses to start while a need of the modules it runs is unmet, naming the
fix. Nothing in `environment` selects a model, a CLI or a provider for
Kapso's own agents.

## 11. Check, run, iterate

```
kapso harness check ./trading
```

It fails on anything that would break a run: a reference that does not
resolve, a skill or agent without front matter, malformed `mcp.json` or
`hook.json`, a hook with an unknown event, a hook command whose script is
missing, a secret literal, an unknown key, a requirements file that does
not exist, no page at all. It warns on what makes a harness weaker than it
looks: a skill, agent, server or hook defined but never listed, a skill
never mentioned on its module's page (a literal occurrence of its name in
the page), a page under `instructions/` that is neither `guardrails.md` nor
a module's, an always-on page over `page_warning_lines`, a long opaque
value in a server's `env`. It reports, without failing, what the machine
lacks. It runs no script and starts no server, reads no path a `SKILL.md`
quotes, and does not compare the directory's name with `name`; files at
the harness root it does not know (a README, a LICENSE) are ignored.
Exit 1 on a failure, 0 otherwise.

Then run a task and read the trajectories. Where every attempt did the same
thing, the harness is already determining behaviour. Where attempts
diverged, one ran the scan and one did not, one burned its budget on a data
fetch, one stopped without results, the harness left a decision to chance.
That divergence is what to fix, with the cheapest part that fixes it:

| The failure was | Add |
|---|---|
| a required step was left implicit | one line on the module page |
| the agent improvised a procedure it should have known | a skill |
| the agent got a deterministic operation wrong by hand | a script inside the skill |
| the agent needed a judgment it could not make alone | a delegate |
| the agent needed data or a system it could not reach | a server |
| the agent made a mistake a tool call reveals | a hook |

If it must happen, the page says so and the engine's module runs. If it may
happen, it is an attachment. If it must not happen, it is not attached, or
denied with a reason, and the real boundary is the engine's.

## 12. The worked example

```
examples/harnesses/trading/
├── harness.yaml                    six modules; learning has no entry
├── requirements.txt                mcp, pandas, pyarrow
├── instructions/
│   ├── guardrails.md               the standing rules; read the task statement first
│   ├── setup.md                    pin the snapshot, write the statement, return market-data
│   ├── ideation.md                 the four axes; what every proposal states
│   ├── implementation.md           timing first; scan before the evaluation; what to save
│   ├── verification.md             scan, auditor, decide; what voids
│   ├── feedback.md                 the risk reviewer; robust over spectacular; the next axis
│   ├── learning.md                 the scoping vocabulary
│   └── deployment.md               the target is the call's; paper only
├── skills/
│   ├── backtesting/                the reference pattern; how to read output; results paths
│   ├── market-data/                the server's tools and the pitfalls it does not fix
│   ├── risk-limits/                the risk line, defined once
│   ├── strategy-families/          the catalogue, with when each fails
│   ├── market-structure/           sessions, funding, lot sizes
│   ├── lookahead-scan/             scripts/scan.py reads a diff; scripts/rules.py is shared with a hook
│   └── paper-trading/              the deployment workflow for the paper-trading target
├── agents/
│   ├── lookahead-auditor.md        asked by the implementer, and by verification on every attempt
│   └── risk-reviewer.md            asked by feedback on every evaluated attempt
├── mcp.json                        market-data and broker
├── servers/
│   ├── market_data.py              bars, calendar, snapshot; also a library
│   └── broker.py                   a paper account filled at the last close; also a library
└── hooks/
    ├── session-brief/              SessionStart: which market this run is on
    ├── deny-web-fetch/             PreToolUse on the shell
    ├── deny-web/                   PreToolUse on the native web tools (implementation)
    ├── protect-prepared/           PreToolUse on the file tools
    ├── deny-snapshot/              PreToolUse on one server tool
    ├── scan-writes/                PostToolUse advisory, sharing the skill's rules
    └── require-results/            Stop, asks once
```

`examples/harnesses/predictive-modelling/harness.yaml` is the same shape on
a second domain: a data-profile skill in setup, model families in ideation
with the axes on the page, a CV protocol and a leakage scan in
implementation with a leakage auditor, the scan and the auditor again in
verification, a predict-endpoint workflow in deployment.

## 13. Common mistakes

- **A task value in the harness.** A limit, a path, a deadline, an
  allowance, a metric. It is right for one task and wrong for the next. Say
  where the value is, not what it is.
- **An essay on an always-on page.** Every word is paid for on every
  session. Move the situational part to a skill and keep one line.
- **A skill nobody is told about.** If no page names the situation and the
  skill, it will rarely be opened. `check` warns; fix the page.
- **A delegate used as a gate.** A delegate is called when the session
  decides to call it. If a check must happen on every attempt, the
  verification page lists it as a numbered step.
- **A hook mistaken for a boundary.** A hook denies a tool call it can see.
  Data that must never be read does not enter the workspace; that is the
  engine's permission, not a hook.
- **Engine knobs in the harness.** Model names for Kapso's agents, budgets,
  lanes, gates. They are the Kapso config, and `check` rejects them.
- **A field the engine would have to parse.** Axes as YAML, reviews as a
  schedule, targets as a list. They are prose on a page, delegates and
  scripts the page names, and a `deploy()` argument.
- **Secrets in `mcp.json`.** Reference the variable by name; the value lives
  in the user's environment.
- **A stop rule on the feedback page.** "Stop when ..." is the engine's
  decision against the task's target. The page says what "met" means in
  the domain, nothing more.
- **`python` in a command.** A stock Ubuntu has `python3` only; `check`
  reports the program as missing, and a hook whose interpreter is absent
  fails open.
