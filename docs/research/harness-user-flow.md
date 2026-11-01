# The harness user flow: from creating a harness to build, deploy and learn

2026-10-24. Companion to `harness-design.md` (the interface) and
`harness-authoring-guide.md` (how to write one). This document is the
experience, end to end, in the order an engineer meets it: an author makes
the domain's harness once, every engineer in that domain uses it on every
task, and the two loops feed each other. Verbs are the redesign's
(`kapso-interfaces.md`): `build`, `deploy`, `learn`; the session mechanics
are the plugin flow's (`docs/plans/kapso-plugin-user-flow.md`): `--detach`,
`watch`, the inbox, the brief.

## 0. Two people, one directory

**The author** knows the domain: a quant who knows what look-ahead looks
like, a data engineer who knows what a warehouse job must never do. The
author writes the harness once and improves it from what runs show. **The
engineer** has a task in that domain and wants a verified outcome: a
strategy with a Sharpe above a number, a model above a metric. The engineer
never opens the harness. Often they are the same person on different days.

Everything between them is one directory, versioned, with a content hash the
engine records on every run and every lesson.

## 1. The author creates the harness

**Step A1, start (one minute).**

```
kapso harness new trading
```

```
trading/
├── harness.yaml                  name, description, empty module lists
└── instructions/guardrails.md    a template: "read the task statement first", then rules
```

In a coding agent the same step is `/kapso:harness new trading`, and the
authoring plugin takes over: it interviews the author module by module and
writes the files from the answers. The questions are the guide's sections
in order. What holds for every task here (guardrails). What must be pinned
and what the task statement must record (setup). The kinds of change the
domain knows, and what every proposal must state (ideation). The discipline
of an attempt and what to save (implementation). What must never pass, and
how to tell (verification). How to score and when to stop (feedback). The
words lessons are filed under (learning). How the winner runs, per target
(deployment). For each answer the plugin decides the cheapest form: a line
on a page, a skill with its script, a delegate, a server, a hook, and fills
the manifest's lists. The author reads the result as files, not as a form.

**Step A2, check (seconds, repeated).**

```
kapso harness check ./trading
```

Structure first: every listed name resolves, front matter is present,
`mcp.json` and every `hook.json` parse, no secret literal, no unknown key.
Then warnings: a skill no page mentions, a defined hook no module lists, a
page over the size the config sets. Then, separately, what this machine
lacks for this harness: a command not on PATH, an env variable a server
references, a GPU. The author fixes and re-runs until it is quiet.

**Step A3, the first run on a known task (hours, unattended).** The author
builds with the harness on a task whose answer is known, with a short
budget:

```
kapso build --harness ./trading --goal "Sharpe above 1.0 out of sample on the 2023 window" \
  --evaluation ./backtest --data ./prices --repo ./strategy \
  --output ../trading-probe --budget-minutes 120 --detach
```

Then reads the trace: `kapso watch ../trading-probe --tree`, and afterwards
the record under `../trading-probe/.kapso/`: each attempt's branch, verdict
and log, what each session consulted, which hooks denied what and with
which reason. The question the author asks of every attempt is the one from
the guide: where did attempts diverge, and which part would have prevented
it. One line on a page, a skill, a script, a delegate, a server, a hook. The
author adds the smallest one, bumps `version`, runs again.

**Step A4, share (one commit).** The harness lives in the project repository
(`harness/trading/`) or in a repository of its own. A teammate loads it by
path or git URL. A harness Leeroo ships is bundled with the package and
loads by name. `kapso harness export ./trading --format claude` writes the
host's plugin layout from the skills, delegates, servers and hooks, for an
engineer who wants the same tools in an ordinary coding session; the export
says what the host cannot reproduce (module routing, the pages).

## 2. The engineer builds with it

**Step B0, setup (once per machine).** Unchanged from the plugin flow:
`/kapso:setup` installs the package and the CLIs, runs the logins, writes
keys to `.env`, runs `kapso doctor`.

**Step B1, pick the harness (a minute).**

```
kapso harness list
  bundled    predictive-modelling   relational-prediction   trading   ...
  installed  acme-pipelines   (git+https://github.com/acme/kapso-harnesses, rev 3f2a)
  local      ./harness/trading
```

No harness that fits means the engineer is the author for an afternoon
(section 1), or builds without one, which is today's generic behaviour.

**Step B2, the brief (a minute, the agent writes it).** The entrance rule
from the plugin flow stands: the agent proposes, never gates. With a
harness loaded the brief is better informed, because the harness's setup
page says what a task statement in this domain must record. For trading
that is instruments, bar frequency, the cost model, the evaluation command
and what it measures, the windows, the position limits. The agent reads the
repository, finds the backtest, runs it once for the baseline, and writes
`kapso-brief.md` with those fields filled or marked unknown. The engineer
corrects one line or says "go".

**Step B3, launch (one command, then hours).**

```
kapso build --harness trading --goal-file kapso-brief.md \
  --evaluation ./backtest --data ./prices --repo ./strategy \
  --config kapso-config.yaml --output ../btc-momentum --budget-minutes 480 --detach
```

or, in Python:

```python
kapso = Kapso(config="kapso-config.yaml")
kapso.load_harness("trading")
kapso.load_experience("mine")
solution = kapso.build(brief, evaluation="./backtest", data="./prices", repo="./strategy",
                       output="../btc-momentum", budget=Budget(minutes=480))
```

What happens in the first seconds, before any agent runs: the harness is
resolved (name, path or URL) and checked; its prerequisites are verified
against this machine and the run stops with the missing names if any; its
`requirements.txt` is prepared in the run's environment; the launch record
and the status file are written with the harness name, version and hash.
The command returns with the pid, the log, the status path and the watch
line. The agent's reply is the handoff, as before, plus one line naming the
harness and its version.

**Step B4, the run (hours, unattended).** Each module's sessions carry what
the manifest lists for that module and nothing else. What the engineer can
see of it:

- `kapso watch ../btc-momentum` shows the harness in the header, then the
  phases. Setup's session pins the snapshot and returns it as
  `prepared/market-data`; the task statement lists it.
- Each attempt's record shows the guidance it had (the pages), the skills
  staged, the delegates it asked and their reports, the hooks that fired
  with their reasons ("web fetch denied: use get_bars"), and the
  verification verdict with its evidence ("voided: centred window in
  strategy/signal.py:4, not justified in the attempt notes").
- Feedback reports against the axes from the ideation page: which axis the
  attempt moved on, which the next should.

**Step B5, the inbox (a minute, sometimes).** A harness server referenced
`BROKER_API_KEY` and `.env` has no such line, or a setup session could not
find the data the brief named. The campaign pauses with `WAITING ON YOU`
and a request that names the variable or the path, never a value. The
engineer fixes `.env` or the path and runs `kapso inbox reply --detach`
with a note. Hooks and servers never ask for a secret through the agent;
the record refuses one pasted by mistake.

**Step B6, the outcome (minutes).** `COMPLETED`, the score, the winning
branch, the stop reason. `Solution` carries the branch, the score, the
evaluation version, the trace, `explain()` and `diff()`. The engineer reads
the diff of the winning branch, the risk line beside the return metric
(the harness made it mandatory), and merges or asks for another round with
`--resume`.

## 3. Deploy

*Superseded on 2026-10-26 by `docs/plans/redesign/wp5-deploy.md`: the
campaign is the verb's positional argument (`kapso deploy ../btc-momentum
--harness trading --target paper-trading`), `options` carry the target's
options, and a harness target is a deployment skill holding
`scripts/deploy.sh`.*

```
kapso deploy --solution ../btc-momentum --harness trading --target paper-trading
```

```python
software = kapso.deploy(solution, target="paper-trading")
```

The target is the call's; with none named, the config's `deployment`
section decides. The deployment session gets the harness's deployment page,
the skills listed for deployment (here the `paper-trading` workflow and
`market-data`), the servers (`market-data`, `broker`) and the hooks. For a
harness target the listed skill is the workflow: it adapts the winner,
runs one cycle to prove it, and reports the endpoint (the runner's log),
the artifacts and a summary. For an engine target (`local`, `docker`,
`modal`, ...) the engine's own workflow runs with the deployment page as
guidance. `Software` comes back with the endpoint and how to call it; the
engineer tries one cycle.

## 4. Learn

```
kapso learn ../btc-momentum --detach
```

```python
experience = kapso.learn(solution)
```

The learning sessions get the harness's learning page, which fixes the
vocabulary lessons are filed under (asset class, bar frequency, strategy
family, cost regime) and what a lesson is not (this task's numbers). Every
lesson records the harness name, version and hash it came from. With
`load_experience("mine")` on the next build in the same harness, the bank
serves those lessons back; a lesson learned under one harness does not
serve another unless shared on purpose.

## 5. The loop closes

**The engineer's loop.** The next task in the same domain starts ahead:
the same harness, the bank it has fed, the repo memory of the last
campaign, an install `doctor` already verified. The handoff is the same
four lines.

**The author's loop.** The trajectories of every run under the harness are
the author's raw material. The question is always the same: where did
attempts diverge, and which part would have prevented it. The author edits
the pages and skills, bumps the version, and the hash on every later run
and lesson says which harness produced what. Later, this loop becomes a job
of the learning module: read the trajectories, propose harness edits, probe
them on the same task, keep what the contrast supports. The interface does
not change for that; only who edits the files.

## 6. The same flow inside a coding agent

The plugin's commands gain `--harness` and one new verb:

| Command | Does |
|---|---|
| `/kapso:harness new\|check\|list\|export` | the author's steps A1, A2, A4; `new` runs the interview |
| `/kapso:build --harness <ref>` | steps B2 and B3: the brief informed by the harness's setup page, then the detached launch |
| `/kapso:watch`, `/kapso:inbox`, `/kapso:resume` | unchanged; the harness appears in the status header |
| `/kapso:deploy --target <name>` | step 3 |
| `/kapso:learn` | step 4 |

The skill's goal flow reads the loaded harness's setup page when it writes
the brief. Nothing else in the plugin changes.

## 7. What the flow asks of the core

In the order the integration should land them:

1. **The harness package**: resolve a name, a path or a git URL (cached
   under `~/.kapso/harnesses/<slug>@<rev>`); validate (`check`); compute the
   content hash; record name, version and hash in the launch record, the
   status file, the checkpoint (a resume with a changed hash is refused by
   name) and the trajectory manifest.
2. **Staging per module**: pages appended to the module's prompts under
   "Domain guidance"; skills copied into the session workspace where the
   CLI discovers them and listed in the prompt; servers from `mcp.json`
   mounted beside the engine's gates, started in the workspace; delegates
   registered as sub-agents, or run as their own session where the CLI has
   none; hooks merged in manifest order, `${PLUGIN_ROOT}` expanded, staged
   into the session's settings or `.codex/hooks.json`.
3. **Prepared resources**: setup returns named resources; the engine mounts
   them under `prepared/<name>` for every later session and lists them in
   the task statement.
4. **Prerequisites**: `check` and `doctor` read `environment` and the env
   references in `mcp.json`; `build` refuses to start with missing ones and
   names them.
5. **The verbs**: `--harness` on `build`, `deploy` and `learn`; `--target`
   on `deploy` with the config's `deployment` section as the default;
   `kapso harness new | check | list | export`.
6. **The trace**: hook decisions with reasons, delegate reports and the
   verification evidence recorded per attempt, so `watch --tree` and the
   record show them.
7. **Retirements**: `design_axes` and the other domain knobs leave the
   config; `additional_context` and the benchmark handlers' prose become
   pages; the benchmarks and examples are ported to harnesses one at a
   time, each a thin runner over `kapso build --harness`.
8. **The authoring plugin**, `/kapso:harness new`, once 1 to 5 are in.
