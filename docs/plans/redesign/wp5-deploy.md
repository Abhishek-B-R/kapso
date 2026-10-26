# WP5: Deploy

2026-10-26. Owner: the redesign's implementer, autonomously, the owner
checking the decisions. Branch `wp5-deploy` off `redesign` at `24b95801`.
Size: M (one package rewritten around two ideas, the `target` argument and
the targets as skills; the facade's `deploy()`, one CLI verb, one config
block, two pages). Revised after the cross-model review (the Review
section): the deployment's identity, the record's lifecycle, the script
contract, the packaging, the options channel and the proof were all
re-specified from the findings.

## Scope

`deploy()` takes a `target`, the call's or the config's: `auto`, one of
the five bundled targets, or a target a harness ships as a skill. The five
bundled targets become skills with their scripts, shipped in the package
and staged into one deployment session exactly as a harness's skills are;
the engine keeps no target-specific Python. The session adapts a copy of
the solution, deploys it with the target's scripts, proves one call and
writes the deployment result; the engine checks the result against the
deployment it can observe, records the deployment under the campaign, and
hands back a `Software` that runs, stops, starts and reports through the
record and the target's scripts, from this process or any later one
(`Software.open`); `kapso deploy` stops, starts and reads it too.

**Not in scope.** The plugin's `/kapso:deploy` command (WP7; the engine
skill's deploy section is this package's). The deploy step of the
semantic suite, S2, and its parity check (WP9; this package records the
parity figure its proof run measures). The docs tab's reorganisation
beyond the Deploy group (WP10). A deployments section in `kapso trace`
(WP6's renderer lists the deployment session under the campaign already;
a section is a finding for later). Live runs against Modal, BentoCloud
and LangGraph Platform (accounts the proof machine does not have; their
skills and scripts are built and exercised against fake executables, and
the release gate, WP11, runs them where the owner's credentials are). A
GPU deployment (the proof machine has none).

## Interface

### Exposed

**The call.**

```python
software = kapso.deploy(solution, target=None, env=None, options=None, coding_agent=None)
```

- `solution`: a `Solution` from `build()` or `Solution.open(path)`, with a
  delivered candidate and the campaign checked out at it. WP1's two
  refusals keep their wording and become `DeployError`, so the CLI prints
  them as one line; a third joins them: a campaign whose tracked files
  differ from the delivered commit is refused naming the files (what was
  evaluated is the commit).
- `target`: the target's name, or `None` for the config's
  `deployment.target` (`auto` as packaged). `auto` lets the session choose
  among the targets available to this deployment; a bundled name
  (`local`, `docker`, `modal`, `bentoml`, `langgraph`) or a harness target
  names one. A harness target is a skill the build's harness lists on its
  deployment module **and that holds `scripts/deploy.sh`**: the structural
  mark of a deployment workflow, so `market-data` (listed on the trading
  harness's deployment module, a reference skill) is not a target and
  `paper-trading` is. A harness target named like a bundled target or
  `auto` is refused when the harness is loaded for a deploy. Any other
  name is refused before a session starts, naming the targets:
  `deploy(target='k8s'): no such target; the targets are auto, local,
  docker, modal, bentoml, langgraph (bundled) and paper-trading (the
  trading harness's)`; on a build without a harness the bundled list
  alone.
- `env`: variables the software needs at runtime, `{name: value}`. Names
  match `[A-Za-z_][A-Za-z0-9_]*`, values hold no newline; anything else
  is refused by name. Written to `.env` at the workspace root (an
  existing file's other lines kept, the call's keys winning, mode 0600, as
  today), named (never valued) in the session's prompt, and passed as
  `KAPSO_ENV_FILE` to every script; the `function` kind's worker loads it
  before the import. The values' one home is that file; the record holds
  the names.
- `options`: `{name: value}` strings for the target's workflow (the
  trading example's `schedule` and `cash`), named with their values in
  the prompt, recorded, and exported to every script as
  `KAPSO_OPTION_<NAME>` (the name upper-cased). A bundled target reads
  none; a harness target's skill says which it takes.
- `coding_agent`: the host the deployment session runs on, an entry of
  the config's `hosts` table; `deployment.cli` when unset, and when that
  is null the build's host, `search_strategy.params.host` (a project that
  moves to Codex changes one key). The model and effort are
  `deployment.model` and `deployment.effort`, else the host entry's.
  `model=` is gone from the call, as it is gone from `build()`.

The returned `Software`, and the one `Software.open` returns:

| Member | What it does |
|---|---|
| `run(inputs)` | One call by the record's run kind (below); `{"status": "success", "output": …}` or `{"status": "error", "error": …}`; refused with the state when the deployment is not `running` (`deployment 2 is stopped; start() it`); `software(inputs)` is the same |
| `run_batch(list)` | `run` over each, in order |
| `stop()`, `start()` | `scripts/stop.sh` and `scripts/start.sh` from the record's target directory, the workspace as working directory, the record's values in the environment; the state written to the record (`stopped`, `running`); `start()` recreates the same deployment (the same name, port, variables, values); a target without the script says so (`this target has nothing to stop`) and the state changes all the same |
| `is_healthy()` | The record's state is `running` and `scripts/health.sh` exits 0 (the `function` kind: and its worker answers a ping); without a `health.sh`, the state alone |
| `logs()` | The engine's own lines, then `scripts/logs.sh`'s output (nothing more without one) |
| `number`, `state`, `target`, `endpoint`, `workspace`, `record` | The deployment's number; its state (`deploying`, `running`, `stopped`, `failed`); the target's name; the endpoint the session reported (an URL, a log path, or `None`); the workspace path; the record's path |
| `proof` | The call the session proved, `{"inputs": …, "output": …}`, the example of what `run()` takes |
| `Software.open(campaign, number=None)` | The campaign's deployment of that number, or the highest number; refuses a campaign with none, naming the directory it looked at, and a record whose target directory, workspace or recorded harness is gone, naming the path |
| `with kapso.deploy(...) as software:` | `stop()` on exit |

Run kinds, chosen by the target's skill and written in the result:

| Kind | Keys in `run` | `run()` |
|---|---|---|
| `function` | `module`, `callable` | A worker process per handle, `sys.executable -m kapso.deployment.worker`, started in the workspace with the `.env` values: it imports `<workspace>/<module>.py` once and answers one JSON line per call with `callable(inputs)`. A call whose function raises ends the worker; the traceback is the error text and the next call starts a worker again. `stop()` ends the worker, `start()` starts one, `is_healthy()` pings it; the kind has no `stop.sh`/`start.sh`/`health.sh` |
| `http` | `url`, `path` | `POST <url><path>` with the inputs as JSON (`urllib`, no extra dependency); a 2xx reply's JSON is the output, any other status is the error with the body |
| `script` | none | `sys.executable <target>/scripts/run.py` from the workspace: the inputs as one JSON document on stdin, the output as exactly one JSON document on stdout, stderr as the error text when the exit is non-zero |

Every call is bounded by `deployment.call_timeout`; a worker or script
still running at it is killed and the call is an error naming the
timeout. There is no `none` kind: a target with nothing to call ships no
`run.py`, and `run()` says `this target has no scripts/run.py; see logs()`.
Errors come from exit codes and status codes, never from catching an
exception in the engine's code; a malformed JSON document on a worker's
or script's stdout raises.

**The verb.**

```
kapso deploy <campaign> [--target NAME] [--env KEY=VALUE ...] [--option KEY=VALUE ...]
                        [--coding-agent CLI] [--config FILE] [--harness REF]
kapso deploy <campaign> --status | --stop | --start | --logs   [--number N]
```

`--strategy`, `--model` and `--interactive` are gone. `--target` is the
call's `target` (not an argparse choice: a harness target is known once
the harness loads, and the refusal is the engine's one line). `--env` and
`--option` take `KEY=VALUE`; a value without `=` is refused by name. The
summary after a deployment: the number and state, the target (and under
`auto` the reasoning in one line), the run kind, the endpoint, the proof
call (its inputs and output, the example of what `run()` takes), health,
the workspace and the record's paths, what the campaign grew by, and the
next actions pinned to the number: the Python line
(`Software.open("<campaign>", <n>).run({...})`, the proof's inputs
inlined) and the three CLI lines (`--logs`, `--stop`, `--start`, each with
`--number <n>`). `--status` lists every deployment of the campaign with
its number, state, target, endpoint and health; `--stop`, `--start` and
`--logs` act on `--number`, the highest by default, through
`Software.open`. A deploy that fails prints the record's path and the
`--stop` line, since what `deploy.sh` started may be running.

**The config block.**

```yaml
deployment:
  target: auto         # what deploy() targets when the call names none
  cli: null            # the host the deployment session runs on; null follows search_strategy.params.host
  model: null          # the host entry's when null
  effort: null
  timeout: 1800        # the deployment session's deadline, seconds, its one resume included
  call_timeout: 300    # one run() call, seconds
  script_timeout: 600  # one lifecycle script, seconds
  port_base: 8000      # the host ports a deployment takes: port_base + (hash + number) % port_span, the first free
  port_span: 1000
```

A session spec over the hosts table in the shape of WP4's roles (`cli`,
`model`, `effort`, `timeout`), plus the target, the three deadlines and
the ports. `check_deployment` in `kapso.core.roles`, called by
`validate_config`, resolves the spec with `origin="deployment"` (a `cli`
the table lacks is refused against `deployment.cli`, naming the hosts a
deployment session runs on) and refuses a `target` that is not a
non-empty string and a timeout, a span or a base that is not a positive
number. `coding_agent` leaves the block (`kapso doctor` and the
retired-name check see it go); `model` stays, null by default, which
removes the packaged duplicate of `hosts.claude_code.model`.

**The target skill.** A target is a skill directory: bundled under
`src/kapso/deployment/targets/<name>/`, or a harness's `skills/<name>/`
listed on its deployment module. What the skill holds:

```
<name>/
├── SKILL.md            name, description (the choosing criteria, "Use when …"), the workflow
└── scripts/
    ├── deploy.sh       build and start the deployment (the session runs it); required
    ├── start.sh        start it again after a stop, the same deployment
    ├── stop.sh         stop it and release what it holds
    ├── health.sh       exit 0 while it answers
    ├── logs.sh         its logs on stdout
    └── run.py          one call, for the `script` run kind
```

- The front matter is the harness check's: `name` the directory's name,
  `description` what it deploys to and the criteria for choosing it, in
  the guide's `Use when …` form (the session under `auto` chooses by it;
  the test pins the form on every bundled target). A **bundled** target's
  front matter also carries `metadata.requires: {binary, install}`, the
  tool the deploying machine needs; the preflight reads it from the
  engine's own files only. A harness target declares its tools in
  `harness.yaml`'s `environment.commands`, which `check` and the verb's
  prerequisite refusal already read; `check` neither requires nor reads
  `metadata`, as the authoring guide says.
- The body is the workflow the session follows: what it has (below), the
  steps (adapt the solution to the target's entry point, run
  `scripts/deploy.sh`, prove one call), what to write as the result, what
  never happens. A bundled target's body carries what today's two
  instruction files said, the entry-point contract (`main.py` with a
  module-level `predict(inputs: dict) -> dict`; a class is not looked
  for) and the `.dockerignore` the docker target writes.
- The scripts are the target's, never the session's to edit: the engine
  runs `bash <target>/scripts/<name>.sh` and `sys.executable
  <target>/scripts/run.py` (no executable bit, no shebang needed) with the
  workspace as the working directory, bounded by `script_timeout`
  (`call_timeout` for `run.py`), and these variables set:
  `KAPSO_DEPLOYMENT_NAME`, `KAPSO_PORT`, `KAPSO_NUMBER`, `KAPSO_WORKSPACE`,
  `KAPSO_RECORD_DIR`, `KAPSO_TARGET_DIR`, `KAPSO_ENDPOINT` (after the
  result), `KAPSO_ENV_FILE` (when the call passed `env`),
  `KAPSO_OPTION_<NAME>` for each option, `KAPSO_VALUE_<KEY>` for each
  value the session recorded (below), and `KAPSO_HARNESS_ROOT` for a
  harness target. A script's stdout lines of the form
  `KAPSO_ENDPOINT=<url>` or `KAPSO_VALUE_<KEY>=<value>` update the record
  (a cloud target whose `start.sh` gets a new URL writes it back); the
  rest of stdout is the script's output. A script's non-zero exit raises
  `DeployError` with its stderr, except in `stop()`, which records the
  stderr and the state `stopped` all the same.
- A script a target does not need is absent, and `Software` answers as
  the table above says.

The five bundled targets, what each one's scripts do:

| Target | `deploy.sh` | run kind | `stop.sh` / `start.sh` | `requires` |
|---|---|---|---|---|
| `local` | proves `from main import predict` with `sys.executable` and the env file | `function` (`main`, `predict`): the worker | none: the worker is the engine's | none |
| `docker` | writes `.dockerignore` (`.env`, `.git`, `.claude`, `.agents`, `.codex`, `.kapso*`), `docker build -t kapso-$KAPSO_DEPLOYMENT_NAME .`, `docker run -d --name kapso-$KAPSO_DEPLOYMENT_NAME -p $KAPSO_PORT:$KAPSO_VALUE_CONTAINER_PORT --env-file … --restart unless-stopped [--gpus all]`, waits for `/health`; records `container_port` and `gpu` as values | `http` (`http://localhost:$KAPSO_PORT`, `/predict`) | `stop.sh` writes the last 200 lines of the container's logs to `$KAPSO_RECORD_DIR/container.log` then `docker rm -f`; `start.sh` runs the same `docker run` from the values; `logs.sh` prints the container's logs, else the saved file | `docker`, the daemon running |
| `modal` | `modal deploy modal_app.py` with the app `kapso-$KAPSO_DEPLOYMENT_NAME`; the `.env` attached as `modal.Secret.from_dotenv()` | `script`: `run.py` looks the function up by app name with the SDK and calls it | `modal app stop <app> --yes`; `modal deploy` again | `modal` |
| `bentoml` | `python deploy.py` against BentoCloud under the deployment name | `script`: `run.py` asks BentoCloud for the deployment's URL and posts with the SDK's own credentials | `bentoml deployment terminate`; `start.sh` applies again and prints `KAPSO_ENDPOINT=<the new url>` | `bentoml` |
| `langgraph` | `langgraph deploy`; records `deployment_url` as a value | `script`: `run.py` posts a run through the platform's SDK on a thread it keeps in `<workspace>/.kapso_langgraph_thread`, so a conversation persists across calls as today | `stop.sh` deletes the thread; `start.sh` re-checks the deployment | `langgraph` |

**The deployment result.** The session writes `kapso_deployment.json` at
the workspace root, the path named in its prompt:

```json
{"target": "docker", "reasoning": "a FastAPI app with system packages; docker is present",
 "endpoint": "http://localhost:8123", "run": {"kind": "http", "url": "http://localhost:8123", "path": "/predict"},
 "values": {"container_port": "8000", "gpu": "none"},
 "proof": {"inputs": {"tenure_months": 3, "plan": "basic"}, "output": {"churn_probability": 0.41}},
 "artifacts": ["Dockerfile", "app.py", "requirements.txt", ".dockerignore"],
 "summary": "the container answered the proof row in 0.4 s"}
```

`target` must be the requested target, or under `auto` one of the targets
offered; `reasoning` is required under `auto`; `endpoint` may be null;
`run.kind` is one of the three with its keys; `values` is a string map the
target's skill documents (`container_port`, `gpu`, `image`, `app`,
`deployment_url`), empty when the target needs none; `proof` holds the one
call the session made and its output; `artifacts` lists the files written
or changed, which must exist.

**The engine's acceptance.** When the session ends the engine checks, in
order: the session completed (a session killed at its deadline or failed
at launch is a failed deployment, not a missing file); the result file
parses and has the fields above with the right shapes (a malformed file
is a refusal naming the file and the field); the target is the one
requested or offered; the artifacts exist; `scripts/health.sh` exits 0
(or the worker starts, for `function`); and `run(proof.inputs)` answers
with status `success`. A result file missing or failing a check after a
completed session resumes the session once with the finding, under the
same deadline (the resume's room is what the deadline leaves); failing
again, the deployment is `failed` with the finding. Only a deployment
that passed every check is `running`.

**The deployment record.** `<campaign>/.kapso/deployments/<n>/`, `<n>`
minted by an atomic `mkdir` (two deploys in flight take distinct numbers,
in one process or two):

```
deployments/<n>/
├── deployment.json     the record, written at the session's start and completed at its end
├── target/             the target's skill directory, copied at deploy time: the scripts every later call runs
├── workspace/          the solution at the delivered commit, adapted and deployed; its own git repository
└── container.log       what the docker target saved before removing its container (that target only)
```

```json
{"number": 2, "state": "running", "state_at": "2026-10-27T10:09:40Z",
 "target_requested": "auto", "target": "docker", "reasoning": "…",
 "offered": [{"name": "local", "ready": "present"}, {"name": "docker", "ready": "present"}, {"name": "modal", "ready": "missing: pip install modal"}],
 "commit": "1a102cc2c8dc…", "branch": "generic_exp_0",
 "harness_built": {"name": "trading", "version": "0.1.0", "hash": "…"} , "harness": {…the loaded one, when it differs…} , "harness_root": "/home/me/trading",
 "host": "claude_code:claude-opus-5", "interpreter": "/home/me/.venv/bin/python",
 "deployment_name": "churn-build-3f9a1c-2", "port": 8769,
 "workspace": "workspace", "target_dir": "target", "env_names": ["API_KEY"], "options": {},
 "result": {…the session's file…}, "endpoint": "http://localhost:8769", "values": {"container_port": "8000", "gpu": "none"},
 "session": "deployment/2", "started": "2026-10-27T10:02:11Z", "finished": "2026-10-27T10:09:40Z",
 "error": null}
```

Paths inside the record are relative to its directory, so a moved
campaign still opens. `state` is one of `deploying` (written before the
session starts, with the number, the request, the host, the workspace and
the name and port already allocated), `running`, `stopped` and `failed`
(with `error`: the finding, the session's error or the deadline); `stop()`
and `start()` write it from any process, with `state_at`. A failed
deployment keeps its record, so `Software.open(campaign, n).stop()` and
`--stop` reach what `deploy.sh` may have started. `Software.open(campaign)`
opens the highest number whatever its state; `run()` refuses by state.
Re-deploying mints a new number and leaves the earlier deployment
running under its own name and port.

**Identity.** `deployment_name` is `<slug>-<hash6>-<n>` (the campaign
directory's name slugged, six hex digits of the sha1 of its absolute
path, the number); `port` is the first port free on this machine from
`port_base + (hash + n) % port_span`, upwards within the span, bound once
at allocation and recorded. Two deployments of one campaign, two targets
of one build, and two campaigns side by side never share a name or a
port; a script acts only on the identity in its own environment.

**The workspace.** A copy of the campaign's working tree at the delivered
commit (its tracked files must match the commit, else the refusal above),
without `.git`, `.kapso`, `.claude`, `.agents`, `.codex`, `kapso_task.md`,
`prepared`, `__pycache__`, `.pytest_cache`, `.mypy_cache`, `.venv`,
`venv`, `node_modules`; the untracked data the solution reads
(`kapso_datasets/`, artifacts) comes along. The copy is then its own git
repository with one commit (`deployment <n> of <campaign> at <commit>`),
so a session's git commands and the staging's collision check address the
workspace and never the campaign above it. With a harness, the staging
copies the task statement and links `prepared/` into the workspace as it
does for every session directory that is not the campaign root, and they
stay for the deployed code to read. After the session the staged skills
and hooks files stay in the workspace too (the docker target's
`.dockerignore` keeps them, with `.env`, out of its image). The page says
what a campaign grows by (each deployment is a copy of the solution with
its data) and that a `deployments/<n>/` directory may be deleted once
stopped, after which its `open` refuses by name.

**The session.** One session on the workspace, on the resolved host with
the spec's model and effort, under the spec's `timeout` (the one resume
included), with WP4's one precedence for its settings (`strict_mcp_config`,
the hosts entry's settings), its record at
`<campaign>/.kapso/sessions/deployment/<n>/` (WP6: its runs, hooks, tools,
cost), where `kapso trace` lists it under the campaign with no change to
WP6. Staged into it by `stage_harness`: the harness's deployment module
when the build had one (its page as guidance, its skills, servers, hooks,
the engine's `protect-harness` hook); and the engine's target skills
(the named target's; every bundled target's under `auto`), on either
host, with or without a harness. The prompt (`deployment_prompt.md`):
the objective **in full** (Rule 6), the delivered candidate's score and
branch; that the workspace is a copy to adapt in place and that the
campaign above it is not to be touched; the variables above, the env
names and the options with their values; the target, or under `auto` the
offered targets each with its description, how to open its skill in the
host's own syntax (the staging's guidance builder renders the list) and
its readiness on this machine (`present`, `missing: <install>`, or
`unverified` for a target that declares no tool, and for docker whether
the daemon answers); the instruction to decide the target first and say
why, open its skill and follow it, run `scripts/deploy.sh`, prove one
call with real inputs, and write the result file; and that the scripts
are not to be edited. The engine's rules stand over the harness's page
(WP2).

**The preflight.** `kapso doctor deploy` and the call's preflight resolve
the one deployment spec (the hosts entry, the model and effort) and check
the session's host row and its host-and-model pairing (WP4's rows; the
live tier probes the pair too, since `_specs_for` gets the spec); for a
named bundled target (the call's, or the configured `deployment.target`
when the call names none) the row its `metadata.requires` names, required
(`docker` also checks the daemon, as today); under `auto`, the host alone
(the session is told each target's readiness); for a harness target,
nothing beyond the harness's own prerequisites (the verb's module check,
WP2). The doctor with no call in flight lists the other bundled targets'
tools as advisory rows, `only needed for kapso deploy --target <name>`.

**Errors.** `DeployError` (`kapso.deployment.DeployError`, a `ValueError`)
is the engine's own refusal around a deployment (no such target, a dirty
campaign, a malformed or failing result after the resume, a session that
failed, a script that exited non-zero, a campaign with no deployment to
open, a record whose files are gone, a `run()` on a deployment that is
not running) and prints as one line from the CLI (it joins
`ENGINE_ERRORS`).

**The engine skill's deploy section** (`skills/claude-code/kapso/SKILL.md`,
`skills/codex/kapso/SKILL.md`): deploy once, in the foreground, with a
tool timeout above `deployment.timeout` (the section names the duration:
minutes, up to thirty); the record is written at the start, so a cut host
call leaves `kapso deploy <campaign> --status` something to read; then
reopen the numbered deployment (`Software.open(path, n)`) and call it, or
read `--logs` for a scheduled target; stop it with `--stop --number n`.
Never background the verb and poll.

**Superseded in the research documents.** `harness-user-flow.md` §3's
`kapso deploy --solution … --target …` (the campaign is positional, no
`--solution`), `harness-design.md` §8's `kapso deploy --harness ./trading
--target paper-trading` (no campaign), and `kapso-interfaces.md` §6's
`prompts/deploy.md` and `deploy.interface`: each gets a superseded note
pointing here, as WP4 did for the config section.

### Consumed

- WP1: `Solution` (`campaign`, `commit`, `branch`, `brief`, `score`,
  `harness`), `Solution.open`.
- WP2: `Harness`, `stage_harness` (the deployment module's attachments
  and guidance, the session record, the mounts), the module's listed
  skills, `check`'s skill rules, `_harness_for(solution, verb="deploy")`
  and the module's prerequisite check; the trading example's deployment
  page and `paper-trading` skill.
- WP4: the hosts table and `resolve_spec`, `validate_config`,
  `ConfigError`, `CodingAgentFactory.session_config`, the preflight's
  `SessionSpec` rows and pairing, the engine hook; `--coding-agent` as
  the host.
- WP6: the session record the adapters fill (runs, hooks, tools, cost),
  listed by `kapso trace` under the campaign.

What this package asks of the staging (WP2's file, the same implementer):
`stage_harness` takes `engine_skills`, skill directories copied beside the
harness's into the session's skills directory on either host; the
no-harness path stages them too and writes the record (today it returns
before writing anything); they are in `writes()` and survive the
module-skills cleanup; the record's `skills` names them; the guidance
builder lists them with the harness's skills, each with the host's
opening syntax. The engine's `protect-harness` hook rides along only with
a harness, as today.

## Ownership

Edits: `src/kapso/deployment/` (rewritten: `__init__.py`, `targets.py`,
`record.py`, `handle.py` (`Software`), `worker.py`, `session.py`,
`deployment_prompt.md`, `targets/<name>/`), `src/kapso/cli/deploy.py`,
`src/kapso/cli/__init__.py` (the top-level help's deploy line),
`src/kapso/cli/errors.py` (`DeployError` in the list), the `deploy()`
method, imports, docstring and `__all__` of `src/kapso/kapso.py`,
`src/kapso/__init__.py` (the exports and the docstring),
`src/kapso/config.yaml` (the `deployment` block), `src/kapso/core/roles.py`
(`check_deployment`, `validate_config`), `src/kapso/core/preflight.py`
(`deploy_tools`, `deploy_requirements`, `_specs_for`), `src/kapso/harness/
staging.py` (`engine_skills`), `pyproject.toml` (the package data, the
`[deploy]` extra), `MANIFEST.in`, `.github/workflows/tests.yml` (the
`--ignore` of the deleted directory), `scripts/check_docs_geo.py` (the
alias `deployment strategy` → `deployment target`), `examples/harnesses/
trading/skills/paper-trading/` (the scripts and the body), the tests named
below, `docs/deploy/`, `docs.json`, the deploy sections of
`docs/reference/{cli,kapso-api,configuration,harness}.mdx`, the mentions in
`docs/{installation,first-build,coding-agent-skills}.mdx`,
`docs/build/review.mdx`, `docs/evolve/{overview,architecture}.mdx`,
`docs/harnesses/{index,use}.mdx`, `docs/README.md`, `README.md`,
`skills/*/kapso/SKILL.md`, `docs/plans/kapso-plugin-mental-model.md` (§3.4
and the module table's row, which WP7 builds from), the superseded notes in
`docs/research/{harness-user-flow,harness-design,kapso-interfaces}.md`,
`tests/test_no_retired_names.py`.

Deletes: `src/kapso/deployment/{base,factory,software}.py`, `adapter/`,
`selector/`, `strategies/` (the enum, the factory, the registry, the five
runners, the validator, the instruction files, the three compatibility
aliases), `tests/test_deployment_{adapter,registry,runners}.py`,
`tests/test_local_runner_isolation.py` (its isolation contract moves to
the worker's tests), `tests/deployment_examples/`, `docs/deployment/` (five
pages, redirected to the Deploy group).

Reads, does not edit: `kapso.harness.manifest` (`MODULES`, the deployment
module's attachments), `kapso.harness.check` (`read_front_matter`, the
`front_matter` rule), `kapso.core.config` (the resolver), the adapters,
`kapso.handles`.

## Changes

Primitives first, as new modules nothing imports yet; then one cutover.
Each commit green on its own.

1. **The target skills, their registry and their packaging.** `targets.py`
   (import-light: directories and front matter only, so the preflight
   imports it at the top): `TargetSkill` (name, path, description,
   requires), `bundled_targets()`, `harness_targets(harness)` (the
   deployment module's listed skills holding `scripts/deploy.sh`),
   `resolve_target(requested, config, harness) -> (name | "auto", offered)`
   with the refusals (unknown, a harness name shadowing a bundled one or
   `auto`), and `readiness(target)` (`present`, `missing: <install>`,
   `unverified`; docker's daemon). The five skills with their scripts,
   from today's instruction files and runners. `pyproject.toml`'s
   `"kapso.deployment" = ["targets/**/*"]` and `MANIFEST.in`'s
   `recursive-include src/kapso/deployment/targets *`. Test:
   `tests/test_target_skills.py` (each bundled skill passes `check`'s
   `front_matter` rule with a `Use when` description; its scripts are
   the contract's; `requires` read; the packaging globs name the
   directory; resolution: the call over the config, `auto`, the trading
   example's `paper-trading` and not its `market-data`, the refusals
   naming both lists, a shadowing harness target).
2. **The record and the identity.** `record.py`: the atomic number, the
   name and the free port, the record written at start and completed at
   the end, read with its paths resolved, `latest`, the state writes.
   Test: `tests/test_deployment_record.py` (numbers minted under a thread
   barrier are distinct; the name and port carry the number and two
   campaigns differ; a taken port is skipped; the record round-trips with
   relative paths after a move; the states).
3. **The worker and the handle.** `worker.py` (the JSON-line loop over
   `<module>.<callable>`, `.env` loaded first, a ping) and `handle.py`
   (`Software`: the three run kinds, the lifecycle through the scripts
   with the environment and the stdout update lines, the absent-script
   answers, the state writes, `open`, the context manager, `run_batch`,
   `__repr__`, `proof`). Tests: `tests/test_software.py` (a workspace
   with `main.py`: `function` imports once in its worker, the `.env`
   values visible to it, two deployments keep their own helper modules
   (the contract `test_local_runner_isolation.py` pinned), a raising
   function ends the worker and the next call starts one, `stop`/`start`/
   `is_healthy` on the worker; `http` against a local test server, a
   non-2xx as the error; `script` with stdin and stdout, a non-zero exit
   as the error, a hung script killed at the timeout; a target without
   `run.py`; the lifecycle scripts with every `KAPSO_*` variable set, a
   `start.sh` printing `KAPSO_ENDPOINT=` updating the record, `stop()` on
   a failing script recording the stderr; `is_healthy()` false after a
   stop from another handle; `open` of the highest and a numbered record,
   the refusals).
4. **The staging's engine skills.** `engine_skills` on `stage_harness`,
   staged with and without a harness, in `writes()` and the cleanup, in
   the record, in the guidance. Test: `tests/test_staging_engine_skills.py`
   (both hosts; no harness: the skills land and the record is written; a
   harness: the engine skills beside the module's, surviving the cleanup;
   the guidance lists them with the host's syntax; a tracked collision
   refused by name).
5. **The deployment session.** `session.py`: the workspace copy (the
   dirty refusal, the ignore list, the repository), the env file and the
   options, the staging, the prompt from `deployment_prompt.md` with the
   offered targets and their readiness, the session under the deadline,
   the acceptance in order, the one resume, the record's completion.
   Test: `tests/test_deployment_session.py` with a fake agent that writes
   what the contract expects (the prompt carries the objective in full,
   the result path, the variables, the env names, the options, the target
   or the offered list with readiness on both hosts; the workspace is a
   repository without the excluded names and with the data; the record
   written before the session with `deploying`; a malformed result is a
   refusal naming the field; a wrong target, a missing artifact and a
   failing proof call resume once with the finding then fail; a session
   killed at the deadline is `failed` without a resume; the env file's
   merge and 0600 (the contract `test_deployment_adapter.py` pinned);
   `reasoning` required under `auto`).
6. **The cutover.** `Kapso.deploy()` on the new surface (the refusals as
   `DeployError`, the target resolved, the preflight with the target, the
   session, `Software`), `kapso deploy` (`--target`, `--env`, `--option`,
   the summary, `--status`, `--stop`, `--start`, `--logs`, `--number`),
   the config block in the spec shape with `check_deployment`, the
   preflight's deploy rows and `_specs_for`, `kapso.__init__`'s and
   `kapso.kapso`'s exports (`Software`, `DeployError`), `DeployError` in
   `ENGINE_ERRORS`, the top-level help; the enum, the factory, the
   registry, the runners, the selector, the validator, the instruction
   files, the three old test files, the isolation test and
   `tests/deployment_examples/` deleted; the workflow's `--ignore`; the
   retired names (`DeployStrategy`, `DeployConfig`, `DeployedSoftware`,
   `DeploymentFactory`, `StrategyRegistry`, `DeployStrategyConfig`,
   `DeploymentSetting`, `AdaptationResult`, `DeploymentInfo`,
   `SelectorAgent`, `AdapterAgent`, `AdaptationValidator`, the five
   runner classes and their three aliases, `selector_instruction`,
   `adapter_instruction`, `run_interface`, `required_files`,
   `_adapted_`, `deployment.coding_agent`, `kapso deploy … --strategy`,
   `--interactive`). Tests: `tests/test_cli_deploy.py` (new: `--target`
   to the call, `--env` and `--option` parsed and a bare key refused, the
   summary's lines, `--status`/`--stop`/`--logs` through `open`, an
   unknown target as one line), `tests/test_session_roles.py` (the block
   over the hosts with the host's model, the null `cli` following the
   build's host, the refusals by key, `coding_agent:` refused by the
   walk), `tests/test_harness_deploy_learn.py` (the deployment session
   carries the module and the target skill; without a harness it carries
   the target skill and no guidance), `tests/test_cli_doctor.py` and
   `tests/test_preflight.py` (the deploy rows, the configured target
   required), `tests/test_cli_agent_choices.py`, `tests/test_no_retired_
   names.py`.
7. **The trading example's target.** `paper-trading/scripts/{deploy.sh,
   start.sh,stop.sh,health.sh,logs.sh,run.py}` (the scheduled runner
   started under `nohup` with a pid file in the workspace, stopped by it,
   healthy while it runs, its log as the endpoint, `run.py` one cycle on
   demand) and the body naming the result file, the `script` kind, the
   `schedule` and `cash` options and the account state kept across
   cycles; `kapso harness check` passes; the authoring guide's deployment
   section says the scripts. Test: in `tests/test_harness_deploy_learn.py`,
   a deploy on the trading harness with `target="paper-trading"` stages
   the skill, and its `run.py` runs one cycle against the example's
   servers in a workspace with pinned bars.
8. **The pages.** `docs/deploy/targets.mdx` (what `deploy()` does, the
   `--target` line and the config default, the five targets' table, `env`
   and `options`, `Software` and `Software.open`, the record on disk and
   what a campaign grows by, the lifecycle lines, a harness build's
   targets, what the doctor checks, the refusals), `docs/deploy/
   write-a-target-skill.mdx` (the skill contract, the scripts contract
   with their variables and update lines, the result file, where a target
   lives, testing one with `kapso harness check` and a deploy), `docs.json`
   (the Deploy group, redirects from the five old pages), the reference
   pages' deploy sections, the mentions, the README, the engine skill's
   deploy section, the mental model's deploy row, the superseded notes,
   the geo alias. The docs coverage and snippet checks green.
9. **The proof run** on the fresh machine, recorded below with the
   findings and the Built table.

## Tests

- Syntactic: the files named in the changes. The provider boundary is
  the only fake in the engine's tests: the session's agent. The bundled
  targets' scripts run for real against fake executables on PATH
  (`docker`, `modal`, `bentoml`, `langgraph` as recording shims that answer
  what the scripts read), in `tests/test_target_scripts.py`: the docker
  scripts build and run with the env file, the port and the GPU value,
  save the logs before removal and recreate the same container on start;
  the modal scripts stop with `--yes` and deploy again; the bentoml start
  prints the new endpoint; the langgraph `run.py` keeps its thread and the
  stop deletes it. The staging, the record, the worker, the scripts and
  the resolver run for real.
- Proof run: a fresh `e2-standard-4` with the wheel of the branch's head,
  the steps archived under `scripts/redesign/runs/wp5/` and mapped to the
  acceptance lines below. (a) The installed package lists
  `targets/*/scripts/*`; `kapso doctor deploy` from a directory outside
  any checkout (the host row; docker missing before its install). (b) The
  churn example built for twenty-five minutes (WP4's eighteen-minute run
  delivered 0.8447; twelve minutes did not) to a delivered candidate,
  `solution.commit` checked before any deploy. (c) `kapso deploy campaign
  --target local`: the record, the summary, `Software.open(campaign, 1)`
  from another process, parity on five held-out rows (the deployed `run()`
  against the delivered branch's `predict.py`), `--status`, `--stop`,
  `--start`, `is_healthy()`, `--logs`. (d) Docker installed; `kapso.deploy
  (solution, target="docker")` from Python: the container named and
  ported from the record, parity on the same rows, `stop()` removes it and
  saves its logs, `start()` recreates it with the env file, `is_healthy()`;
  then a second `--target docker` deploy: number 3 beside number 2, both
  healthy, `open(campaign, 2).stop()` leaving 3 running. (e) `--target
  auto` under an override file: the choice, its reasoning and the offered
  list with readiness in the record. (f) A deploy with no `--target` under
  an override file setting `target: local`. (g) WP4's archived trading
  build restored on the machine (the campaign subtree unpacked, the
  delivered branch checked out, `--harness examples/harnesses/trading`
  passed since the record names the old machine's path, both hashes
  recorded): `--target paper-trading --option schedule="*/2 * * * *"`,
  the runner's cycles in `--logs`, `run({})` one cycle on demand, `--stop`
  and `--start` from another process. (h) The refusals as one line: an
  unknown target naming both lists, a harness target on the churn build,
  a dirty campaign, `--target docker` before docker was installed, `--env
  FOO`. (i) On the development box: one `--target local` deploy with
  `--coding-agent codex`, and one Claude Code session following the
  engine skill's deploy section end to end on the churn build (deploy,
  reopen by number, call, stop). What cannot be proven there and is said:
  the cloud targets live, the GPU value's effect, a BentoCloud endpoint
  change across a stop and a start, the result-file refusals beyond the
  fakes, a host call cut mid-session.
- Semantic hooks: none of S1 to S6 runs here; S2's deploy step and its
  parity check are WP9's over WP7's plugin. The numbers this run records
  for them: wall time and the session's cost per target, turns, and the
  parity figure (rows equal out of five, local and docker).

## Acceptance

Each line names the proof step that establishes it.

- `kapso deploy campaign --target local` (c) and `kapso.deploy(solution,
  target="docker")` (d) deploy the churn build on the fresh machine; the
  records at `.kapso/deployments/<n>/deployment.json` name the target, the
  state, the identity, the endpoint and the session; `Software.open
  (campaign, n).run(row)` from another process answers as the delivered
  branch does on the proof's five rows, on both targets.
- A second deployment leaves the first running under its own name and
  port, and stopping one leaves the other healthy (d).
- `deploy()` with no target follows `deployment.target` (f); `auto`
  writes the reasoning and the offered targets with their readiness into
  the record (e); `deploy(target="k8s")`, a harness target on a build
  without one, a dirty campaign and `--env FOO` are one line each (h).
- `src/kapso/deployment/targets/` holds five skill directories, each with
  a `SKILL.md` that passes `check`'s front-matter rule and the scripts the
  contract names; the installed wheel carries them (a); the engine imports
  no target-specific module; `strategies/`, `selector/`, `adapter/`,
  `factory.py`, `base.py` and the enum are gone, and the retired-name check
  refuses their names.
- The trading example's `paper-trading` skill deploys WP4's trading build
  on the fresh machine with its scripts and an option; `run()` runs one
  cycle; `--stop` and `--start` work from another process (g); `kapso
  harness check examples/harnesses/trading` passes.
- `deployment:` is a session spec over the hosts table with the target,
  the three deadlines and the ports; `kapso doctor deploy` shows its host
  row, the configured target's tool as required and the others as
  advisory (a); `coding_agent` under it is refused by the walk.
- The engine skill's deploy section is the one specified, and a Claude
  Code session following it deploys, reopens, calls and stops the churn
  build (i).
- The two Deploy pages exist and `docs.json` reaches them; the five old
  pages redirect; the docs coverage and snippet checks pass; the gate is
  green; the proof run is archived and recorded here.

## Risks

- **The `function` kind's worker** adds a process per handle and a pipe
  per call; a model loads once per worker, as it loaded once per process
  today. A raising function restarts the worker on the next call, which
  reloads the model: said on the page.
- **Docker on the fresh machine**: the install and the group membership
  take minutes; the proof script does it before step (d) and records the
  time. The daemon's absence is a readiness line under `auto` and a
  required row for a named target.
- **The cloud targets are unproven live** in this package. Their scripts
  are what today's runners did, exercised against fake executables; a
  wrong flag surfaces at the release gate or in the owner's own run, and
  the session's record shows which script failed.
- **`auto` choosing a target the machine cannot serve.** The prompt marks
  each target's readiness, the daemon included; a session that still
  chooses a missing one fails at its `deploy.sh` with the tool's name in
  the record, and the deployment is `failed` with the finding.
- **A long session.** The spec's `timeout` (thirty minutes as packaged)
  cuts it; the record is `failed` with the deadline, what `deploy.sh`
  started is reachable through `--stop`, and a re-deploy takes a new
  number.
- **The workspace under `.kapso/`** surprises a person looking for the
  adapted copy beside the campaign, where today's `_adapted_<strategy>`
  was. The summary and the record print the path; the page says where it
  is and what a campaign grows by.
- **The ports.** A span of a thousand ports from 8000 is the packaged
  default; a machine that uses them for something else sets
  `deployment.port_base` and `port_span`.

## Review

The cross-model review of the first plan (`scripts/redesign/review.sh`,
Codex `gpt-6-astra` at xhigh and Claude Code `claude-opus-5`, read-only,
2026-10-26; the outputs under `scripts/redesign/runs/wp5-plan-review/`).
Both would build on the two central moves (one session, the targets as
skills) and neither would build the first plan as written: the
deployment's identity collided across re-deployments, the record could
not reopen a deployment on its own, a bad result left a live runtime
nobody could reach, the scripts had no execution contract or packaging,
the example harness's options had no channel, and a reference skill
passed as a target. Every finding and what the plan now says:

### Codex

| # | Finding | Answer |
|---|---|---|
| 1 | P1: a re-deploy makes an old handle control the new deployment; the hash alone does not keep ports apart | the identity carries the number (`<slug>-<hash6>-<n>`, a port bound free at allocation and recorded); each record keeps its own; a script acts only on the identity in its environment; tested with two deployments and two campaigns |
| 2 | P1: the record cannot reopen a deployment on its own | the record carries the commit and branch, both harness identities and the harness root, the interpreter, the name and port, the values, the target directory copied beside it, paths relative to its directory |
| 3 | P1: failure and cross-process lifecycle semantics missing | the record is written at the start (`deploying`) under an atomic number; `failed` keeps the record and the error; `stop()`/`start()` write the state from any process; `latest` is the highest number and `run()` refuses by state |
| 4 | P1: the scripts have no durable, host-independent location | `deployments/<n>/target/` is the copy every later call runs, `bash`/`sys.executable`, cwd the workspace, the variables listed, stdout/stderr/exit and the timeouts said; `KAPSO_HARNESS_ROOT` recorded and passed; the no-harness staging path grows the engine skills |
| 5 | P1: in-process `function` has no isolation and cannot reopen | a worker process per handle (`kapso.deployment.worker`), the model loaded once, `.env` in the worker, isolation by process; the eviction code goes |
| 6 | P1: the run kinds cannot express the runners' behaviours | `values` in the result and `KAPSO_VALUE_*` on every script; the stdout update lines (`KAPSO_ENDPOINT=`); docker saves its logs before removal and recreates with the env file and the GPU value; modal stops with `--yes`; bentoml is a `script` target with the SDK's own credentials; langgraph keeps its thread in the workspace and deletes it on stop |
| 7 | P1: supporting skills advertised as targets | a harness target is a deployment skill holding `scripts/deploy.sh`; `market-data` is not one; a name shadowing a bundled target or `auto` is refused; the trading manifest is the test |
| 8 | P1: the trading target lacks the scripts the contract requires; the options have no channel | the six scripts specified (change 7); `options` on the call, `--option` on the verb, `KAPSO_OPTION_*` on the scripts; `run()` is one cycle on demand (`script` kind), which is the flow's "the engineer tries one cycle" |
| 9 | P1: the shell scripts are not packaged | `pyproject.toml`'s package data and `MANIFEST.in` in Ownership and change 1, the globs tested, the installed files listed in the proof |
| 10 | P1: the commits cannot individually stay green | primitives first as new modules nothing imports (`targets`, `record`, `handle`, `worker`, `session`), then one cutover commit |
| 11 | P1: a well-formed result is not evidence of a deployment | the engine's acceptance: the session completed, the file's shape, the target requested or offered, the artifacts exist, `health.sh`, the proof call re-run; only then `running`; a killed session is `failed`, never resumed as a missing file |
| 12 | P1: the proof's build delivered nothing | a twenty-five-minute build with the delivered-commit check (b) |
| 13 | P2: the copy policy | dirty tracked files refused; the working tree at the commit copied with the ignore list and the data; the statement and `prepared/` mounted by the staging and kept |
| 14 | P2: git discovery from the nested workspace | the workspace is its own repository with one commit; the collision check and the session's git commands stop there |
| 15 | P2: `metadata.requires` contradicts the harness contract | read from the engine's bundled targets only; a harness target's tools are `environment.commands`; `check` ignores `metadata` |
| 16 | P2: strengthen `auto` beyond binary presence | readiness per target (`present`, `missing: <install>`, `unverified`, the daemon for docker) in the prompt and the record's `offered`; the descriptions keep the choosing criteria; the choice first, then the adaptation |
| 17 | P2: the doctor does not reflect the effective configuration | one resolved spec for the call, the static rows and the live tier (`_specs_for`); a configured named target required, the others advisory; `model` stays nullable (the sentence was wrong) |
| 18 | P2: errors and deadlines versus the rules | per-kind error envelopes from exit and status codes, no catches; the resume under the same deadline; a killed or failed session is failed; the three deadlines and the ports in the block; WP1's refusals as `DeployError` with their wording |
| 19 | P2: the environment contract | names and values validated, the merge and 0600 kept and tested, `.dockerignore` keeps `.env` out of images, the file read again on reopen, `KAPSO_*` as transport of resolved values, the SDKs read their own credentials |
| 20 | P2: the receipt leaves the person without a next step | the summary with the number, state, kind, proof call, health, growth and the next actions pinned to the number; `--status`, `--stop`, `--start`, `--logs` on the verb; `--interactive` gone |
| 21 | P2: the coding-agent flow unspecified and unproven | the engine skill's deploy section specified; proof step (i) runs a Claude Code session through it |
| 22 | P2: the deletion inventory incomplete; `--strategy` too broad a ban | the files and names listed in Ownership and change 6; the check scoped to `kapso deploy … --strategy` |
| 23 | P2: the test list does not cover the scripts | `tests/test_target_scripts.py` against fake executables; the regressions named; "without a harness the session is unchanged" restated |
| 24 | P2: the proof does not establish every acceptance line | each line names its step; docker parity, the Python call, the config default, the re-deploy, the cross-process lifecycle, the coding-agent flow added; the trading restore recipe said; what cannot be proven said |

### Claude Code

| # | Finding | Answer |
|---|---|---|
| F1 | P1: a refusal after `deploy.sh` leaves a runtime nobody can reach | the record at the start; `failed` keeps it; the CLI prints the `--stop` line |
| F2 | P2: nothing says what `run()` takes | `proof` in the result and the record, printed in the summary and inlined in the Python line |
| F3 | P2: the CLI cannot stop or inspect; `--interactive` is dead weight | `--status`, `--stop`, `--start`, `--logs`, `--number`; `--interactive` deleted |
| F4 | P2: the coding-agent flow backgrounds a long verb | the engine skill's section specified (foreground, the duration, the record at start, reopen by number, the stop line); proof (i) |
| F5 | P2: `open` cannot recover the env values | `.env` is the values' one home; the worker loads it, every script gets `KAPSO_ENV_FILE` |
| F6 | P3: health and kind in the summary, the doctor's wording, argparse choices, `--env FOO` | all four as said in the verb's paragraph and the preflight's |
| F7 | P2: the record cannot support the `auto` choice it stores | `offered` with readiness, as the prompt stated it; the session pointer |
| F8 | P2: the description is the whole evidence under `auto` | the choosing criteria in the `Use when` form, pinned on every bundled target |
| F9 | P1: the targets will not ship in the wheel | as Codex 9 |
| F10 | P1: where the scripts live at `open` time | the target directory copied into the record |
| F11 | P1: no channel for the per-deployment values on `start()` | `values` and `KAPSO_VALUE_*`, the docker skill's keys |
| F12 | P2: `metadata.requires` is engine-facing | as Codex 15 |
| F13 | P2: the interpreter and the executable bit | `bash` and `sys.executable`, no bit, the test dropped |
| F14 | P2: the prompt must speak the host's skill syntax | the staging's guidance builder renders the offered list per host |
| F15 | P3: `run.py`'s error channel and deadline | stderr, one JSON document, `call_timeout` |
| F16 | P2: BentoCloud's endpoint changes across a restart | a `script` target; `start.sh` prints `KAPSO_ENDPOINT=` and the record takes it; the general update-line rule |
| F17 | P2: `run()`'s error status versus Rule 2 | per kind from exit and status codes; a raising function ends its worker, the traceback is the error, no catch |
| F18 | P2: the `function` kind's engine-side lifecycle | the worker's state machine; the absent-script answers per method |
| F19 | P3: LangGraph's thread is lost | kept in the workspace, deleted on stop |
| F20 | P3: module resolution narrows silently | `<workspace>/<module>.py`, a module-level callable, said in the contract and the skill |
| F21 | P1: the name and port collide across deployments | as Codex 1 |
| F22 | P2: the numbering has no lock | an atomic `mkdir`, tested under a barrier |
| F23 | P2: no state in the record | `state` and `state_at`, written by the lifecycle from any process |
| F24 | P2: the copy's exclusion list is too little | the list said; the staged mounts kept for the deployed code; `.dockerignore` |
| F25 | P3: say what the campaign grows by | the summary and the page say it, and which directories may be deleted |
| F26 | P2: `timeout` changes meaning and nothing bounds a call | `timeout`, `call_timeout`, `script_timeout` |
| F27 | P3: `deployment.cli` a second home for the host | null follows `search_strategy.params.host`; said in the block and on the page |
| F28 | P3: `check_deployment` must pass `cli` inside the spec | `origin="deployment"`, the deploy hosts named |
| F29 | P3: the live tier probes nothing for a deploy; the function-local import | `_specs_for` gets the spec; `targets.py` import-light at the top |
| F30 | P2: the retired names and the files outside Ownership | listed in Ownership and change 6; the geo alias |
| F31 | P2: the staging ask is one sentence | written out in Consumed and change 4; the hook only with a harness |
| F32 | P2: change 5 is five commits in one | primitives then one cutover (Codex 10 asked for the one cutover; the split is the primitives) |
| F33 | P2: the env test lost, the naming test, the no-harness test contradicted | carried into change 5 and 2; restated |
| F34 | P3: contracts without a test, a test that does not earn its place | `reasoning` under `auto` and the second number tested; the exec-bit assertion dropped; `front_matter` named |
| F35 | P2: the config default and a re-deploy unproven | steps (d) and (f) |
| F36 | P2: nothing proves the wheel carries the targets | step (a) |
| F37 | P3: the trading restore hits the harness-identity refusal first | `--harness examples/harnesses/trading` passed, the branch checked out, both hashes recorded (g) |
| F38 | P3: say what cannot be proven | said at the end of the proof |
| F39 | P1: no options channel for the example harness's `schedule` and `cash` | `options` on the call and the verb, `KAPSO_OPTION_*` on the scripts |
| F40 | P2: Rules 1 and 2 for the rewrite | the deadlines and the ports in the block; no catches; the fallback pair goes with the single session |
| F41 | P3: supersede the research documents' deploy lines | the superseded notes, change 8 |
| F42 | P3: Rule 6 on the prompt | the objective in full |

Built on these answers; the owner checks the decisions.
