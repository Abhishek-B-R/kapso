# WP5: Deploy

2026-10-26. Owner: the redesign's implementer, autonomously, the owner
checking the decisions. Branch `wp5-deploy` off `redesign` at `24b95801`.
Size: M (one package rewritten around two ideas, the `target` argument and
the targets as skills; the facade's `deploy()`, one CLI verb, one config
block, two pages).

## Scope

`deploy()` takes a `target`, the call's or the config's: `auto`, one of
the five bundled targets, or a target a harness ships as a skill. The five
bundled targets become skills with their scripts, shipped in the package
and staged into one deployment session exactly as a harness's skills are;
the engine keeps no target-specific Python. The session adapts a copy of
the solution, deploys it with the target's scripts, proves one call and
writes the deployment result; the engine records the deployment under the
campaign and hands back a `Software` that runs, stops, starts and reports
through the record and the target's scripts, from this process or any
later one (`Software.open`).

**Not in scope.** The plugin's `/kapso:deploy` command and skill (WP7). The
deploy step of the semantic suite, S2, and its parity check (WP9; this
package records the parity figure its proof run measures). The docs tab's
reorganisation beyond the Deploy group (WP10). A deployment's appearance
in `kapso trace` beyond what the session records already give it (WP6's
renderer lists every session under the campaign; a deployments section is
a finding for later). Live runs against Modal, BentoCloud and LangGraph
Platform (accounts the proof machine does not have; their skills and
scripts are built and exercised with fakes, and the release gate, WP11,
runs them where the owner's credentials are). A `kapso deploy --stop`
verb (`Software.open(...).stop()` is the way; a verb is a finding for
later).

## Interface

### Exposed

**The call.**

```python
software = kapso.deploy(solution, target=None, env=None, coding_agent=None)
```

- `solution`: a `Solution` from `build()` or `Solution.open(path)`, with a
  delivered candidate and the campaign checked out at it (WP1's two
  refusals stand).
- `target`: the target's name, or `None` for the config's
  `deployment.target` (`auto` as packaged). `auto` lets the session choose
  among the targets available to this deployment; a bundled name
  (`local`, `docker`, `modal`, `bentoml`, `langgraph`) or a harness target
  (a skill the build's harness lists on its deployment module, named for
  the target, `paper-trading` in the trading example) names one. Any
  other name is refused before a session starts, naming the targets:
  `deploy(target='k8s'): no such target; the targets are auto, local,
  docker, modal, bentoml, langgraph (bundled) and paper-trading (the
  trading harness's)`. A harness target on a build without a harness is
  refused the same way, the bundled list alone.
- `env`: variables the software needs at runtime. Written to `.env` at
  the deployment workspace's root, named (never valued) in the session's
  prompt, and set on every runtime the engine or the target's scripts
  manage.
- `coding_agent`: the host the deployment session runs on, an entry of
  the config's `hosts` table; `deployment.cli` when unset. The model and
  effort are `deployment.model` and `deployment.effort`, else the host
  entry's. `model=` is gone from the call, as it is gone from `build()`.

The returned `Software`:

| Member | What it does |
|---|---|
| `run(inputs)` | One call of the deployed software by the record's run kind (below); `{"status": "success", "output": …}` or `{"status": "error", "error": …}`; `software(inputs)` is the same |
| `run_batch(list)` | `run` over each, in order |
| `stop()`, `start()` | The target's `scripts/stop.sh` and `scripts/start.sh` over the workspace with the record's values in the environment; `start()` after `stop()` recreates the same deployment (the same name, port, variables) |
| `is_healthy()` | `scripts/health.sh` exits 0; false after `stop()` without a `start()` |
| `logs()` | `scripts/logs.sh`'s output, the engine's own lines first |
| `target`, `endpoint`, `workspace`, `record` | The target's name; the endpoint the session reported (an URL, a log path, or `None`); the workspace path; the record's path |
| `Software.open(campaign, number=None)` | The campaign's latest deployment (or the numbered one) from its record, in any process; refuses a campaign with no deployment, naming the path it looked at |
| `with kapso.deploy(...) as software:` | `stop()` on exit |

Run kinds, chosen by the target's skill and written in the result:

| Kind | Keys | `run()` |
|---|---|---|
| `function` | `module`, `callable` | imports `<workspace>/<module>.py` once in this process (the caller's variables set first; modules of another deployment evicted, as today) and calls `callable(inputs)` |
| `http` | `url`, `path` | `POST <url><path>` with the inputs as JSON, the reply as the output |
| `script` | none | runs the target's `scripts/run.py` from the workspace: the inputs as JSON on stdin, the output as JSON on stdout, a non-zero exit as the error |
| `none` | `reason` | refuses with the reason (`this target runs on its schedule; see logs()`), the kind of a scheduled runner such as paper trading |

**The verb.**

```
kapso deploy <campaign> [--target NAME] [--env KEY=VALUE ...] [--coding-agent CLI]
                        [--config FILE] [--harness REF] [--interactive]
```

`--strategy` and `--model` are gone; `--target` is the call's `target`
and `--coding-agent` the session's host. The summary after a deployment:
the target (and, under `auto`, the session's reasoning in one line), the
endpoint, the workspace, the record's path, and the line that calls it
from Python (`Software.open("<campaign>")`). `--interactive` keeps the
process alive and stops the software on Ctrl-C, as today.

**The config block.**

```yaml
deployment:
  target: auto         # what deploy() targets when the call names none
  cli: claude_code     # the host the deployment session runs on (an entry of hosts)
  model: null          # the host entry's when null
  effort: null
  timeout: 1800        # the deployment session's deadline, seconds
```

A session spec over the hosts table in the shape of WP4's roles (`cli`,
`model`, `effort`, `timeout`), plus `target`. `validate_config` checks it
with the roles: a `cli` the table lacks, a `target` that is not a non-empty
string, a `timeout` that is not a positive number are refused by key.
`coding_agent` and `model` leave the block (`kapso doctor` and the
retired-name check see them go).

**The target skill.** A target is a skill directory, bundled under
`src/kapso/deployment/targets/<name>/` or shipped by a harness under its
`skills/<name>/` and listed on its deployment module. What the skill
holds:

```
<name>/
├── SKILL.md            front matter name, description, metadata.requires; the workflow
└── scripts/
    ├── deploy.sh       build and start the deployment (the session runs it)
    ├── start.sh        start it again after a stop, the same deployment
    ├── stop.sh         stop it and release what it holds
    ├── health.sh       exit 0 while it answers
    ├── logs.sh         its logs on stdout
    └── run.py          one call, for the `script` run kind only
```

- The front matter is the harness check's (`name` the directory's name,
  `description` what it deploys to, then `Use when …`), and may carry
  `metadata.requires: {binary, install}`, the tool the deploying machine
  needs; the preflight reads it. A bundled target passes `kapso harness
  check`'s skill rules, which a test pins.
- The body is the workflow the session follows: what it has, the steps
  (adapt the solution to the target's entry point, run `scripts/deploy.sh`,
  prove one call), what to write as the result, what never happens.
- Every script runs with the workspace as its working directory and
  these variables set: `KAPSO_DEPLOYMENT_NAME` and `KAPSO_PORT` (derived
  from the campaign's path, distinct per solution, stable across
  re-deployments: the names and ports of today's `deployment_context`),
  `KAPSO_WORKSPACE`, `KAPSO_ENDPOINT` (after the result is written),
  `KAPSO_ENV_FILE` when the call passed `env`. A script a target does not
  need is absent: a scheduled runner has no `run.py`; `Software` says so
  when asked (`this target has no scripts/run.py`).

The five bundled targets, what each one's scripts do:

| Target | `deploy.sh` | run kind | `stop.sh` / `start.sh` | needs |
|---|---|---|---|---|
| `local` | `python -c "from main import predict; …"` proves the import | `function` (`main`, `predict`) | nothing to stop; `start.sh` proves the import again | nothing |
| `docker` | `docker build` the image `kapso-$KAPSO_DEPLOYMENT_NAME`, `docker run` the container with `--env-file` and the port; waits for `/health` | `http` (`http://localhost:$KAPSO_PORT`, `/predict`) | `docker rm -f`; `docker run` again with the same name, port, env file and GPU request | `docker`, the daemon running |
| `modal` | `modal deploy modal_app.py` | `script` (`scripts/run.py` looks the function up by app name and calls it) | `modal app stop`; `modal deploy` again | `modal` |
| `bentoml` | `python deploy.py` against BentoCloud | `http` (the deployment's URL, `/predict`) | `bentoml deployment terminate`; `bentoml deployment apply` | `bentoml` |
| `langgraph` | `langgraph deploy` | `script` (`scripts/run.py` posts a run through the platform's SDK) | nothing to stop on the platform; `start.sh` re-checks the deployment | `langgraph` |

**The deployment result.** The session writes `kapso_deployment.json` at
the workspace root, the path named in its prompt:

```json
{"target": "docker", "reasoning": "a FastAPI app with system packages; docker is present",
 "endpoint": "http://localhost:8123", "run": {"kind": "http", "url": "http://localhost:8123", "path": "/predict"},
 "artifacts": ["Dockerfile", "app.py", "requirements.txt"], "summary": "one call answered in 0.4 s"}
```

`reasoning` is required under `auto` and ignored otherwise; `endpoint` may
be null; `run.kind` is one of the four with its keys; `artifacts` lists
the files the session wrote or changed. A malformed file raises
`DeployError` naming the file and the field; a missing one resumes the
session once with the finding; missing again, `DeployError` names the
session's record.

**The deployment record.** `<campaign>/.kapso/deployments/<n>/`, numbered
from 1 per campaign:

```
deployments/<n>/
├── deployment.json     the record
└── workspace/          the solution at the delivered commit, adapted and deployed
```

```json
{"number": 2, "target_requested": "auto", "target": "docker", "reasoning": "…",
 "host": "claude_code:claude-opus-5", "harness": null,
 "workspace": "/…/.kapso/deployments/2/workspace", "env_names": ["API_KEY"],
 "result": {…the session's file…}, "session": "deployment/2",
 "started": "2026-10-27T10:02:11Z", "finished": "2026-10-27T10:09:40Z", "healthy_at_finish": true}
```

The session's own record (WP6: its runs, hooks, tools, cost) is at
`<campaign>/.kapso/sessions/deployment/<n>/`. The workspace is a copy of
the campaign at the delivered commit without `.git` and `.kapso`;
re-deploying writes a new number and leaves the earlier one (a `stop()` on
the earlier `Software.open(campaign, number=1)` still works).

**The session.** One session on the workspace, on the host
`deployment.cli` with the spec's model and effort, under the spec's
`timeout`, with WP4's one precedence for its settings (`strict_mcp_config`,
the hosts entry's settings). Staged into it: the harness's deployment
module when the build had one (WP2: its page as guidance, its skills,
servers and hooks, the records); the target's skill (every bundled
target's under `auto`); the engine's `protect-harness` hook (WP4). Its
prompt (`deployment_prompt.md`): the objective and the delivered
candidate's score and branch; that the workspace is a copy to adapt in
place; the variables above and the env names; the target, or under `auto`
the targets available with their descriptions and whether each one's tool
is present on this machine; the instruction to open the target's skill
and follow it, run its `scripts/deploy.sh`, prove one call, and write the
result file; and that it must not touch the campaign itself. The engine's
rules stand over the harness's page (WP2).

**The preflight.** `kapso doctor deploy` and the call's preflight: the
session's host row and its host-and-model pairing (WP4's rows); for a
named bundled target, the row its `metadata.requires` names (`docker`
also checks the daemon, as today); under `auto`, the host alone (the
session is told which tools are present); for a harness target, nothing
beyond the harness's own prerequisites (the verb's module check, WP2).
The doctor with no call in flight lists every bundled target's tool as an
advisory row, `only needed for --target <name>`.

**Errors.** `DeployError` (`kapso.deployment.DeployError`, a `ValueError`)
is the engine's own refusal around a deployment (no such target, a
malformed result, a session that wrote none, a campaign with no
deployment to open) and prints as one line from the CLI (it joins
`ENGINE_ERRORS`); WP1's refusals of a solution with no candidate or a
campaign not at the delivered commit keep their messages.

### Consumed

- WP1: `Solution` (`campaign`, `commit`, `branch`, `brief`, `score`,
  `harness`), `Solution.open`.
- WP2: `Harness`, `stage_harness` (the deployment module's attachments
  and guidance, the session record), `kapso harness check`'s skill rules,
  `_harness_for(solution, verb="deploy")` and the module's prerequisite
  check; the trading example's deployment page and `paper-trading`
  skill.
- WP4: the hosts table and `resolve_spec`, `validate_config`,
  `ConfigError`, `CodingAgentFactory.session_config`, the preflight's
  `SessionSpec` rows and pairing, the engine hook; `--coding-agent` as
  the host.
- WP6: the session record the adapters fill (runs, hooks, tools, cost),
  listed by `kapso trace` under the campaign.

What this package asks of a file it does not own: the staging takes an
`engine_skills` argument, skill directories copied beside the harness's
into the session's skills directory (as `ENGINE_HOOKS` are merged into
the hooks), used by the deployment session for the target skills.

## Ownership

Edits: `src/kapso/deployment/` (rewritten: `__init__.py`, `targets.py`,
`session.py`, `deployment_prompt.md`, `record.py`, `software.py`,
`targets/<name>/`), `src/kapso/cli/deploy.py`, the `deploy()` method of
`src/kapso/kapso.py`, `src/kapso/__init__.py` (the exports),
`src/kapso/config.yaml` (the `deployment` block), `src/kapso/core/roles.py`
(`check_deployment` beside `check_maintainer`, called by
`validate_config`), `src/kapso/core/preflight.py` (`deploy_tools`,
`deploy_requirements`), `src/kapso/cli/errors.py` (`DeployError` in the
list), `src/kapso/harness/staging.py` (the `engine_skills` argument, with
WP2's owner's consent: the same implementer), `examples/harnesses/trading/
skills/paper-trading/` (its scripts), the tests named below, `docs/deploy/`,
`docs.json`, the deploy sections of `docs/reference/{cli,kapso-api,
configuration,harness}.mdx`, the mentions in `docs/{installation,
first-build}.mdx`, `docs/build/review.mdx`, `docs/evolve/overview.mdx`,
`README.md`, `skills/*/kapso/SKILL.md`, `tests/test_no_retired_names.py`.

Deletes: `src/kapso/deployment/{base,factory}.py`, `adapter/`, `selector/`,
`strategies/` (the enum, the factory, the registry, the five runners, the
validator, the instruction files), `tests/test_deployment_{adapter,
registry,runners}.py`, `tests/deployment_examples/`, `docs/deployment/`
(five pages, redirected to the Deploy group).

Reads, does not edit: `kapso.harness.manifest` (`MODULES`, the deployment
module's attachments), `kapso.core.config` (the resolver), the adapters,
`kapso.handles`.

## Changes

1. **The config block in the spec shape.** `deployment: {target, cli,
   model, effort, timeout}` in the packaged file; `check_deployment` in
   `kapso.core.roles` (the spec over the hosts table through
   `resolve_spec`, `target` a non-empty string, `timeout` positive),
   called by `validate_config`; `configuration.mdx`'s block. Test:
   `tests/test_session_roles.py` (the block resolves over the hosts with
   the host's model; `cli: gemini`, `target: ""`, `timeout: -1` refused by
   key; `coding_agent:` in an override file refused by the walk).
2. **The target skills and their registry.** `targets.py`: `TargetSkill`
   (name, path, description, requires), `bundled_targets()` from
   `src/kapso/deployment/targets/`, `harness_targets(harness)` from the
   deployment module's listed skills, `resolve_target(requested, config,
   harness) -> (name | "auto", the available targets)` with the refusal.
   The five skills with their scripts, written from today's instruction
   files and runners (the docker scripts keep the recreate-with-env-and-GPU
   behaviour the runner tests pinned; the names and ports from
   `deployment_context`). Test: `tests/test_target_skills.py` (each
   bundled skill passes the harness skill check; its scripts are the
   contract's, executable; `requires` read; resolution: the call over the
   config, `auto`, a harness target on the trading example, the refusal
   naming both lists).
3. **The deployment session.** `session.py`: the numbered workspace
   under `.kapso/deployments/<n>/`, the copy at the delivered commit
   without `.git` and `.kapso`, the env file, the staging (the harness's
   module, the target skills through `engine_skills`, the engine hook),
   the prompt from `deployment_prompt.md` with the available targets and
   their tools' presence under `auto`, the session under the spec's
   timeout, the result file read and checked, one resume with the
   finding, `DeployError` naming the session's record. The staging's
   `engine_skills` argument. Test: `tests/test_deployment_session.py`
   with a fake agent that writes what the contract expects (the prompt
   names the result path and the target; `auto` lists the targets with
   their presence; the skills land in the session's skills directory on
   both hosts; the env file and names; the variables; the record written
   under `.kapso/sessions/deployment/<n>`; a malformed file raises naming
   the field; a missing file resumes once with the finding, then raises
   naming the record).
4. **`Software` from the record.** `record.py` (write, read, the next
   number, `latest`), `software.py` (the four run kinds, the lifecycle
   through the scripts with the environment, `open`, the context manager,
   `run_batch`, `__repr__`). Test: `tests/test_software.py` (a workspace
   with `main.py`: `function` imports once and calls, the caller's
   variables set before the import, two local deployments keep their own
   modules; `http` posts to a local test server; `script` runs
   `scripts/run.py` with stdin and stdout; `none` refuses with the
   reason; `stop`/`start`/`health`/`logs` run the scripts with
   `KAPSO_*` set, `is_healthy()` false after a stop; `open` reads the
   latest and the numbered record and refuses a campaign without one).
5. **The verb and the call on the new surface.** `Kapso.deploy()`
   (the target resolved, the preflight with the target, the session,
   the record, `Software`), `kapso deploy` (`--target`, the summary,
   `--interactive`), `kapso.__init__`'s exports (`Software`,
   `DeployError`; the enum, the config and the factory gone),
   `DeployError` in `ENGINE_ERRORS`, the preflight's deploy rows from the
   skills; the enum, the factory, the registry, the runners, the selector,
   the validator and the instruction files deleted. Tests:
   `tests/test_cli_deploy.py` (new: `--target` to the call, `--env`
   parsed, the summary's lines, an unknown target as one line),
   `tests/test_harness_deploy_learn.py` (the deployment session carries
   the module; the paper-trading target on the trading harness stages the
   skill; without a harness the session is unchanged), `tests/test_cli_
   doctor.py` (the deploy rows), `tests/test_no_retired_names.py`
   (`DeployStrategy`, `--strategy`, `DeploymentFactory`,
   `StrategyRegistry`, `selector_instruction`, `adapter_instruction`,
   `run_interface`, `deployment.coding_agent`), the three old deployment
   test files and `tests/deployment_examples/` deleted.
6. **The trading example's target with its scripts.** `paper-trading/
   scripts/{stop.sh,health.sh,logs.sh}` (the scheduled runner's loop
   stopped by its pid file, healthy while it runs, its log), the skill's
   body naming the result file and the `none` run kind; `kapso harness
   check` passes; the authoring guide's deployment section says the
   scripts. Test: in `tests/test_harness_deploy_learn.py`, a deploy on
   the trading harness with `target="paper-trading"` stages the skill
   and refuses `run()` by kind.
7. **The pages.** `docs/deploy/targets.mdx` (what `deploy()` does, the
   `--target` line and the config default, the five targets' table, `env`,
   `Software` and `Software.open`, the record on disk, a harness build's
   targets, what the doctor checks, the refusals), `docs/deploy/
   write-a-target-skill.mdx` (the skill contract, the scripts contract and
   their variables, the result file, where a target lives, testing one
   with `kapso harness check` and a deploy), `docs.json` (the Deploy group,
   redirects from the five old pages), the reference pages' deploy
   sections, the mentions, the README, the skills. The docs coverage and
   snippet checks green.
8. **The proof run** on the fresh machine, recorded below with the
   findings and the Built table.

## Tests

- Syntactic: `tests/test_session_roles.py` (the block's resolution and
  refusals), `tests/test_target_skills.py` (the skill contract, the
  registry, the resolution), `tests/test_deployment_session.py` (the
  session's staging, prompt, result and record, with the agent faked),
  `tests/test_software.py` (the run kinds, the lifecycle, `open`),
  `tests/test_cli_deploy.py`, `tests/test_harness_deploy_learn.py`,
  `tests/test_cli_doctor.py`, `tests/test_no_retired_names.py`. The
  provider boundary is the only fake: the session's agent. The staging,
  the record, the scripts and the resolver run for real.
- Proof run: a fresh `e2-standard-4` with the wheel of the branch's head.
  (a) The churn example built for twelve minutes (as WP4's run c) to a
  delivered candidate; `kapso doctor deploy` (the host row, the targets'
  tools: docker missing before its install). (b) `kapso deploy campaign
  --target local`: the record, `Software.open` from Python, parity on
  five held-out rows (the deployed `run()` against the delivered branch's
  `predict.py`), `stop`/`start`/`is_healthy`/`logs`. (c) Docker installed;
  `--target docker`: the container named and ported from the record,
  `stop()` removes it, `start()` recreates it with the env file,
  `is_healthy()` and `logs()`. (d) `--target auto`: the choice and its
  reasoning in the record, the tools' presence in the prompt (the session
  record shows it). (e) WP4's archived trading build restored on the
  machine with the example harness: `--target paper-trading`, the skill's
  workflow, the log path as the endpoint, `run()` refused by kind,
  `logs()`. (f) The refusals as one line: an unknown target naming both
  lists, a harness target on the churn build, `--target docker` before
  docker was installed. (g) On the development box, one `--target local`
  deploy with `--coding-agent codex`. Archived under
  `scripts/redesign/runs/wp5/`.
- Semantic hooks: none of S1 to S6 runs here; S2's deploy step and its
  parity check are WP9's over WP7's plugin. The numbers this run records
  for them: wall time and the session's cost per target, turns, and the
  parity figure (rows equal out of five).

## Acceptance

- `kapso.deploy(solution, target="docker")` and `kapso deploy campaign
  --target docker` deploy the churn build on the fresh machine; the record
  at `.kapso/deployments/1/deployment.json` names the target, the
  endpoint and the session; `Software.open("campaign").run(row)` answers
  as the delivered branch does on the proof's five rows.
- `deploy()` with no target follows `deployment.target`; `auto` writes
  the session's reasoning into the record; `deploy(target="k8s")` is one
  line naming the bundled targets and the harness's.
- `src/kapso/deployment/targets/` holds five skill directories, each with
  a `SKILL.md` that passes the harness skill check and the scripts the
  contract names; the engine imports no target-specific module;
  `strategies/`, `selector/`, `adapter/`, `factory.py` and the enum are
  gone, and the retired-name check refuses their names.
- The trading example's `paper-trading` skill deploys WP4's trading build
  on the fresh machine with its scripts; `run()` refuses by kind;
  `kapso harness check examples/harnesses/trading` passes.
- `deployment:` is a session spec over the hosts table; `kapso doctor`
  shows its host row and the targets' tool rows; `coding_agent` under it
  is refused by the walk.
- The two Deploy pages exist and `docs.json` reaches them; the five old
  pages redirect; the docs coverage and snippet checks pass; the gate is
  green; the proof run is archived and recorded here.

## Risks

- **The `function` kind imports in the caller's process**, as today's
  local runner does: fast for repeated calls, no isolation. Kept, with the
  module eviction today's runner has; the isolated path is `docker`.
- **Docker on the fresh machine**: the install and the group membership
  take minutes and a re-login; the proof script does it before the docker
  deploy and records the time.
- **The cloud targets are unproven live** in this package. Their scripts
  are what today's runners did, exercised by the tests with the CLIs
  faked; a wrong flag surfaces at the release gate or in the owner's own
  run, and the session's record shows which script failed.
- **`auto` choosing a target the machine cannot serve.** The prompt marks
  each target's tool as present or missing; a session that chooses a
  missing one fails at its `deploy.sh` with the tool's name in the record,
  and the summary says so.
- **A long session.** The spec's `timeout` (thirty minutes as packaged)
  cuts it; the record keeps what was written; a re-deploy takes a new
  number.
- **The workspace under `.kapso/`** surprises a person looking for the
  adapted copy beside the campaign, where today's `_adapted_<strategy>`
  was. The summary and the record print the path; the page says where it
  is.

## Review

The cross-model review of this plan (`scripts/redesign/review.sh`, Codex
`gpt-6-astra` at xhigh and Claude Code `claude-opus-5`, read-only; the
outputs under `scripts/redesign/runs/wp5-plan-review/`): to come, with
every finding and what the plan now says.
