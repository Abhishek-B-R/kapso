# WP2: the harness package

2026-10-24. Branch `wp2-harness`, off `redesign` once WP1 is merged (it is
written against `wp1-build` at `b49d3827` and rebases). Size L: the long
pole of the redesign. Depends on WP1 (`Brief.harness`, `Solution.harness`,
`HarnessRef`, the launch record, `kapso build`).

The design is `docs/research/harness-design.md`; the flow is
`harness-user-flow.md` (section 7 lists the seams in the order they land);
the reference grammar and the store are `onboarding.md` section 1; the
pages, skills, delegates, servers and hooks an author writes are
`harness-authoring-guide.md`. This plan turns those into code, in the
engine as it is at `b49d3827` (the seam map below is of that commit).

## Scope

The harness as a thing the engine loads, checks, records and stages: the
reference grammar (a bundled name, a path, a git reference) and the store
under the config's `harness.store`; the manifest schema and `check`; the
content hash and the triple `{name, version, hash}` in the launch record,
the status header, the checkpoint (a resume refuses a changed hash by
name), the solution record and the trajectory manifest; staging per
module into every session the engine runs (pages under "Domain guidance",
skills where the CLI discovers them, servers beside the gates, delegates
as the host's sub-agents, hooks merged in manifest order); the two module
sessions the engine does not have yet and a harness needs, setup (the task
statement and prepared resources) and verification (a verdict per attempt
that can void it); prerequisite refusal with names; `load_harness` on the
facade; `--harness` on `kapso build` and `kapso deploy`; `kapso harness
new | check | list | add | update | remove | export`; the `trading`
example as a task on the trading harness, with its probe run; the
Harnesses documentation section.

**Not in scope.** Experience (WP3: `load_experience`, the brief's
`Experience` line, scope by harness; WP2 only records the triple a lesson
will be scoped by). `--target` on deploy and the bundled targets as skills
(WP5; WP2 stages the deployment page and attachments into the sessions
deploy already runs). The retirements (WP4: `design_axes`,
`implementation_web`, `additional_context`, the handlers' prose; a harness
and `additional_context` coexist until then, the harness block after the
handler's context). The trace of hook decisions, delegate reports and
verification evidence in `kapso trace` and `watch --tree` (WP6; WP2 writes
the files WP6 renders: the per-session staging record, the verdict files,
the stream artifacts). The `kapso learn <campaign>` command and its
`--harness` flag (WP3 rewrites `cli/learn.py`; the Python `learn()` takes
the harness from the object or the record here). Bundled harnesses (WP8
ports; WP2 creates the directory they resolve from and `list` says none
ship yet). The authoring plugin `/kapso:harness new` (WP7). `export
--format cursor` (no verified layout; dropped until asked for). The
Harness² editor loop.

## Interface

### The reference grammar

Three forms, tried in this order; a string that matches none raises an
error that lists the forms and says `kapso harness list`:

```
trading                                   a bundled name: [a-z0-9][a-z0-9-]*, a directory under src/kapso/harnesses/
./harness/trading  ~/h/trading  /abs      a path: a directory that exists; used in place, never copied
git+https://github.com/acme/harnesses@v3#trading     a git reference: url, optional @rev, optional #subdirectory
acme/harnesses@v3#trading                 GitHub shorthand for the same (exactly owner/repo, no scheme)
```

A git reference is cloned once into `<store>/<slug>@<rev>/` (`slug` =
`owner-repo`; `rev` = the tag, branch or sha as written, `HEAD` when
absent) and the harness is `<clone>/<subdirectory>`. `kapso harness update`
re-fetches a branch or `HEAD` reference; a tag or a sha is never
re-fetched. The store is `harness.store` in the config (`~/.kapso/harnesses`
in the shipped file; CLAUDE.md rule 1). A path in a brief's `Harness` line
resolves against the working directory at build time, as every other path
the CLI takes.

### The manifest

`harness.yaml`, exactly the design's section 2. `schema_version: 1`;
`name` (the bundled-name grammar), `version`, `description` required;
`environment: {python: <requirements file>, commands: [..], gpu: bool}`
optional; `modules.<setup|ideation|implementation|verification|feedback|learning|deployment>`
each with the four lists `skills`, `mcp_servers`, `agents`, `hooks`, every
list optional and empty by default. Any other key, module or field fails
`check`. Pages are `instructions/guardrails.md` (every module) and
`instructions/<module>.md`; a module with no entry still gets its pages.

### `check`

```python
from kapso.harness import check
report = check(path)             # CheckReport(failures, warnings, lacking)
```

Failures (the run does not start): an unsupported `schema_version`; an
unknown key, module or field; a reference that resolves to nothing (a
skill name with no `skills/<name>/SKILL.md`, an agent with no
`agents/<name>.md`, a server with no key in `mcp.json`, a hook with no
`hooks/<name>/hook.json`); a skill or agent without `name` and
`description` front matter, or a skill whose `name` is not its directory;
a malformed `mcp.json` (not the `mcpServers` schema: stdio `command`,
`args`, `env`, `cwd`, or `streamable-http` `url`, `headers`) or
`hook.json` (not `{"hooks": {<event>: [{matcher?, hooks: [{type:
command, command}]}]}}`); a hook with an event outside the hosts' set
(`SessionStart`, `SessionEnd`, `UserPromptSubmit`, `PreToolUse`,
`PostToolUse`, `PermissionRequest`, `Stop`, `SubagentStart`,
`SubagentStop`, `PreCompact`, `PostCompact`); a hook command naming a
`${PLUGIN_ROOT}/...` script that does not exist; an `env` value in
`mcp.json` that is a literal where a reference is expected (anything that
is not `${NAME}` for an env name containing `KEY`, `TOKEN`, `SECRET`,
`PASSWORD`, or any value that looks like a credential: twenty-four or more
characters of `[A-Za-z0-9_-]`, or a known prefix `sk-`, `kpsk_`, `ghp_`,
`xoxb-`); a named requirements file that does not exist. Every failure
carries the file and, where there is one, the line.

Warnings: a skill, agent or hook directory no module lists; a skill a
module lists that its page (`instructions/<module>.md`, else
`guardrails.md`) never names; an always-on page longer than
`harness.page_max_lines` (40 in the shipped config). Lacking (reported,
never a failure of the harness): a command not on PATH; an env variable a
server references that is set neither in the environment nor in `.env`;
a python distribution from the requirements file that is not installed; a
GPU when `gpu: true` and `nvidia-smi` is absent or fails.

### The handle

```python
kapso = Kapso(config="kapso-config.yaml")
harness = kapso.load_harness("./harness/trading")

harness.name, harness.version, harness.description
harness.hash                 # sha256 over every file under the directory (sorted relative paths and bytes;
                             # .git, __pycache__, *.pyc excluded), full hex; prints use the first twelve
harness.source               # the reference as given, with a path made absolute
harness.path                 # the directory the run reads
harness.modules["implementation"]   # ModuleAttachments(skills, mcp_servers, agents, hooks): four tuples of names
harness.environment          # Environment(python: Path | None, commands: tuple[str, ...], gpu: bool)
harness.missing              # [Prerequisite(kind, name, read_from, fix)], [] when the machine has everything
harness.ref()                # HarnessRef(name, version, hash, source) — what the records carry
```

`load_harness` resolves, runs `check`, raises `HarnessError` with the
report's failures when there are any (warnings are printed), computes the
hash, reads the prerequisites into `missing` without raising, sets the
object's harness and returns the handle. A second call replaces the first.
`Kapso.harness` is the loaded handle or `None`.

### What the verbs do with it

- `build()`: the harness is the object's when one is loaded, else the
  brief's `Harness` line resolved the same way, else none (today's generic
  behaviour, unchanged: no setup or verification session, nothing staged,
  `solution.harness` `None`). A loaded harness wins over the brief's line
  (the rule call arguments already follow for budgets), and the launch
  print names the one used. With a harness: refuse while `missing` is not
  empty, naming each item, where it is read from and the line that fixes
  it (`pip install -r <path>` for python distributions); write the launch
  record with `harness: {name, version, hash, source}`; the status header
  with `harness: "<name> <version> (<hash12>)"`; the checkpoint with the
  triple (schema 4); write the task statement; run setup if the harness
  has a setup page or attachments; stage every session from the manifest;
  run verification per attempt if the harness has a verification page or
  attachments; return a `Solution` whose `harness` is the ref. Nothing is
  installed by the engine: a git-fetched directory could ask for anything
  (DECISIONS).
- resume: the checkpoint's triple is compared with the harness resolved
  for the resume (the loaded one, else the launch record's `source`
  resolved again); a different hash is refused by name, printing both
  versions and hashes and the two ways out (resume with the recorded
  harness, or start a new campaign). A different source with the same
  hash is allowed and the launch record keeps the original.
- `deploy(solution)`, `learn(solution)`: the object's harness when loaded,
  else the record's `source` resolved again; a loaded harness whose `name`
  differs from the record is refused; another version of the same name is
  allowed and recorded. `learn()` writes the triple into
  `trajectory.yaml` (`harness: {name, version, hash}`), which is what WP3
  scopes lessons by. `deploy()` stages the deployment module into the
  selector and the adapter sessions.

### Staging, per session

One function, called by every place the engine constructs a coding-agent
session, in `src/kapso/harness/staging.py`:

```python
staged = stage_session(harness, module, cwd, host)      # host: "claude_code" | "codex"
staged.guidance            # the "Domain guidance" block, appended to the module's prompt(s); "" without a harness
staged.agent_specific      # keys merged into the session's CodingAgentConfig.agent_specific (below)
staged.record              # written to <campaign>/.kapso/sessions/<session>/harness.json by the caller
```

What it does, deterministically, from `modules.<module>`:

| Attachment | Staged as | Claude Code | Codex |
|---|---|---|---|
| pages | `## Domain guidance (harness <name> <version>)`: `guardrails.md` whole, then `<module>.md` whole, then the attachment lists (a skill per line with its description and how to open it; a delegate per line with its description and how to ask it; the servers by name with the `mcp__<server>__` prefix), then the paths: the task statement, `KAPSO_HARNESS_ROOT`, `prepared/<name>` for each prepared resource | a `{{domain_guidance}}` variable in each module template, placed before the template's closing section (`test_inbox_prompt.py` pins that the implementation prompt ends with the closing line) | same |
| skills | the directories copied whole into the session cwd | `.claude/skills/<name>/` | `.agents/skills/<name>/` |
| mcp_servers | the named entries of `mcp.json`, `${PLUGIN_ROOT}` expanded to the harness path in `command`, `args`, `cwd` and `env`; `cwd` the session cwd unless the entry names one; `env` gains `KAPSO_HARNESS_ROOT`; merged into the `mcp_servers` dict beside the gates | the adapter writes them into `.claude_mcp/mcp_config.json` as today | `-c mcp_servers.<name>.*` as today, plus `default_tools_approval_mode="approve"` (verified: `auto` leaves the call refused under a read-only or workspace-write sandbox) |
| agents | each `agents/<name>.md` (front matter `name`, `description`; body the prompt) as a host sub-agent the session invokes by name | `--agents <cwd>/.claude/harness-agents.json` (`{"<name>": {"description", "prompt"}}`; verified: the model invokes it through `Agent` with `subagent_type` = the name and gets the reply as the tool result) | Codex's `multi_agent` is stable and the model has `collaboration.spawn_agent`; the staging passes each agent as an `agents.<name>` role override (`description`, a config file with the prompt as developer instructions) — the one form the probe did not verify; the build phase probes it first, and if roles cannot be defined per invocation the guidance block tells the session to spawn an agent whose first message is the agent file's text followed by the request |
| hooks | the listed `hooks/<name>/hook.json` files, in manifest order, their event lists concatenated into one `{"hooks": {...}}`, `${PLUGIN_ROOT}` expanded in every command | `--settings <cwd>/.claude/harness-hooks.json` (verified: hooks fire in `-p`) | `<cwd>/.codex/hooks.json` and `--dangerously-bypass-hook-trust` on the command (verified) |
| env | `KAPSO_HARNESS_ROOT=<harness.path>` in the session's and every server's environment | `env_overrides` | `env_overrides` |
| prepared resources | `<campaign>/prepared/` symlinked into the session cwd when the cwd is not the campaign root | | |
| task statement | `<campaign>/kapso_task.md` copied into the session cwd when the cwd is not the campaign root | | |

The staged files are ignored by the workspace's `.gitignore` (`.claude/`,
`.agents/`, `.codex/`, `prepared/`, `kapso_task.md` join the lines
`_ensure_workspace_gitignore` commits) so a session's closing `git add .`
never commits them into a candidate. Env references in a server's `env`
(`"${BROKER_API_KEY}"`) are never resolved by the engine (CLAUDE.md rule
3): the host or the server process reads them from the session
environment, which the engine has loaded `.env` into as it does for the
gates; the mechanism per host (inheritance, or an explicit forward list)
is settled by a probe in the build phase and written into the
authoring guide. Hook matchers are written in Claude Code's tool names
and work as written on Codex (verified: `Bash`, `apply_patch`,
`mcp__<server>__<tool>` and `Edit|Write|MultiEdit`, which Codex aliases
onto `apply_patch`, all matched); a hook that needs the written file's
path must read `tool_input.file_path` on Claude Code and parse the
`apply_patch` header lines on Codex, and the guide says so.

### The task statement and prepared resources

With a harness, `build()` writes `<campaign>/kapso_task.md` before any
session: the brief rendered whole (the objective, measured-by, baseline,
target, rules), the evaluation reference (`kapso_evaluation/` provided, or
"to be built from the brief's protocol"), the data reference
(`kapso_datasets/`), the harness name and version, and a "## Prepared
resources" section (empty until setup). The file is untracked and ignored;
staging copies it into every session directory; every module's guidance
names its path. Untracked, so it never lands in a candidate branch.

Setup runs once per fresh campaign, at the campaign root, after
`_setup_kapso_directories` and before the evaluation maintainer's setup,
when the harness has `instructions/setup.md` or any setup attachment: one
coding-agent session (the `coding_agent` block, full sandbox, the setup
module staged, no engine gates) with the engine's new `setup.md` template:
the task statement, the paths, and the convention "to return a prepared
resource, create `prepared/<name>/` in this directory; everything under
`prepared/` is mounted for every later session at the same relative path
and listed in the task statement; you may rewrite the task statement's
domain section". After the session the engine lists `prepared/*` into the
statement and the status file's `setup` phase records the names. A setup
session that leaves nothing under `prepared/` is not an error.

### Verification

Runs per attempt, after the implementation session has closed and the
registered evaluation has run, before the judge, when the harness has
`instructions/verification.md` or any verification attachment. The engine
writes `<campaign>/.kapso/verification/<branch>/diff.patch` (`git diff
main...<branch>`) and `evaluation_output.txt`, materialises the branch in
a detached worktree (`materialize_ref`, as ideation does), and runs one
session there (the `feedback_generator` block's CLI and model, the
verification module staged, Codex with `--add-dir` on the verification
directory) with the engine's new `verification.md` template: the two
paths, the task statement, and the verdict contract. The session writes
`<campaign>/.kapso/verification/<branch>/verdict.json`:

```json
{"verdict": "valid" | "void", "summary": "...", "findings": [{"rule": "...", "evidence": "strategy/signal.py:4 ..."}]}
```

`void` sends the attempt down the path an integrity rejection takes
today: its score is cleared, it is never a parent and never delivered, it
counts in `solution.rejected_candidates`, and the judge is told the
verdict and the findings. `valid` passes the attempt to the judge with
the summary. A malformed verdict raises (rule 2). A session that ends
without writing one is recorded as `verdict: "none"` and the attempt
stays valid, with the judge told that verification produced no verdict
(DECISIONS: a forgotten file must not kill a campaign, and the judge
still sees that the check did not happen).

### The CLI

```
kapso harness new <name> [--dir <parent>]          # harness.yaml + instructions/guardrails.md, from the guide's template
kapso harness check <ref>                          # failures, then warnings, then what this machine lacks; exit 1 on a failure
kapso harness list                                 # bundled (none ship yet), fetched (store), local (recently loaded paths)
kapso harness add <ref>                            # fetch (git) or register (path) + check + prerequisites, never failing on them
kapso harness update <ref|name>                    # re-fetch a branch reference, re-check, print the version change
kapso harness remove <ref|name>                    # delete the fetched copy, or forget a local path
kapso harness export <ref> --format claude|codex --out <dir>
kapso build ... --harness <ref>                    # wins over the brief's Harness line
kapso deploy <campaign> --harness <ref>            # must name the record's harness; another version is allowed
```

`export --format claude` writes `.claude-plugin/plugin.json`, `skills/`,
`agents/`, `.mcp.json` and `hooks/hooks.json` (every hook merged) with a
`README.md` made of the pages and a note that module routing is not
reproduced; `--format codex` writes `.agents/skills/`, `.codex/hooks.json`,
a `config.toml` fragment for the servers and the same README. "Recently
loaded paths" are kept in `<store>/recent.json`, written by `load_harness`
for the path form (the onboarding document's `local` row).

### Records

| Record | Field | Written by |
|---|---|---|
| `<campaign>/.kapso/launch.json` | `harness: {name, version, hash, source} \| null` | `build()` |
| `<campaign>/.kapso/status.json` header | `harness: "<name> <version> (<hash12>)" \| null`; phases gain `verification` | `BuildStatus` |
| `<campaign>/.kapso/run_state.json` | `harness` (the four fields), schema 4 | the checkpoint store |
| `<campaign>/.kapso/solution.json` | `harness` (already in schema 2, filled) | `Solution.save` |
| `<campaign>/.kapso/sessions/<session>/harness.json` | `{module, host, pages, skills, mcp_servers, agents, hooks}` as staged | every staging call |
| `<campaign>/.kapso/verification/<branch>/` | `diff.patch`, `evaluation_output.txt`, `verdict.json` | the verification step |
| `<campaign>/kapso_task.md`, `<campaign>/prepared/` | the statement and the resources | `build()`, the setup session |
| `~/.kapso/trajectories/<id>/trajectory.yaml` | `harness: {name, version, hash}` | `learn()` |

### Config

```yaml
harness:
  store: ~/.kapso/harnesses     # fetched git references live here, one directory per <slug>@<rev>
  page_max_lines: 40            # `check` warns on an always-on page longer than this
```

No other key: the harness and the engine config never share one.

## Ownership

Edits: `src/kapso/harness/` (new: `__init__.py`, `manifest.py`,
`reference.py`, `store.py`, `check.py`, `hash.py`, `staging.py`,
`hooks.py`, `export.py`, `templates/` for `new`); `src/kapso/harnesses/`
(new, a README; the bundled-name root); `src/kapso/cli/harness.py` (new),
`cli/__init__.py` (one tuple entry), `cli/build.py` and `cli/deploy.py`
(`--harness`); `src/kapso/kapso.py` (`load_harness`, the harness lines of
`build`, `reply`, `deploy`, `learn`); `src/kapso/config.yaml` (the
`harness` block); `src/kapso/handles.py` (nothing: `HarnessRef` stays as
WP1 left it); the staging seams: `execution/coding_agents/adapters/claude_code_agent.py`
(`settings_path` → `--settings`, `agents_path` → `--agents`),
`codex_agent.py` (`hooks_trust_bypass` → `--dangerously-bypass-hook-trust`,
`add_dirs` → `--add-dir`, `approve` for harness servers, agent roles),
`search_strategies/generic/codex_ideation.py` (servers and hooks for a
Codex member), `execution/experiment_workspace/experiment_workspace.py`
(the ignore lines, `materialize_ref` staging), `experiment_session.py`
(the prepared symlink and the statement copy), `search_strategies/generic/{strategy,ideation,implementation,lens_planning,feedback_flow}.py`,
`feedback_generator/feedback_generator.py`, `evaluation_maintainer/maintainer.py`
(setup staging only), the prompt templates under
`search_strategies/generic/prompts/` (a `{{domain_guidance}}` variable
each; two new templates `setup.md`, `verification.md`),
`execution/orchestrator.py` (the setup step, the verification step, the
checkpoint fields), `execution/run_checkpoint.py` (schema 4, the
refusal), `execution/observability.py` (the header field, the phase),
`execution/inbox.py` (the launch key), `core/preflight.py` (the
environment block, read by `doctor build` when a harness is given),
`deployment/base.py`, `deployment/selector/agent.py`,
`deployment/adapter/agent.py` (staging), `learning/mining.py`,
`learning/update_frame.py`, `learning/trajectory_store.py` (the learning
page, the manifest field); `examples/trading/` (new), `examples/README.md`,
`examples/harnesses/trading/hooks/*/` (the two file hooks read both
tool-input shapes), `examples/harnesses/README.md`; docs:
`docs/harnesses/*.mdx` (new), `docs/reference/{kapso-api,cli,brief-format}.mdx`,
`docs/reference/harness.mdx` (new), `docs.json`; the tests named below.

Reads, does not edit: `src/kapso/gated_mcp/` (the gates' server stays as
it is; harness servers are mounted beside it by merging dicts),
`src/kapso/environment/handlers/` (WP4 retires them), `benchmarks/`
(WP4 and WP8), `cli/learn.py` (WP3), `docs/build/*` (WP1's, except one
sentence on the brief page pointing at the Harness line's reference
page).

## The seam map (commit `b49d3827`)

What the code does today at each place WP2 cuts, so the change list below
is checkable. Short paths are under `src/kapso/`.

- **Sessions.** Every build session constructs its own
  `CodingAgentConfig` and adapter: single ideation and ensemble members
  (`search_strategies/generic/ideation.py:316-350, 545-580`, Codex members
  through `codex_ideation.py:46-158` with no MCP and a read-only sandbox),
  the selector (`ideation.py:788-844`), the lens planner
  (`lens_planning.py:185-248`), implementation (`implementation.py:208-317`,
  Claude direct, Codex through the factory), the judge
  (`feedback_generator.py:82-112, 154-182`), the maintainer
  (`evaluation_maintainer/maintainer.py:274-278, 445-455`), deploy
  (`deployment/selector/agent.py:157-168`, `deployment/adapter/agent.py:263-286`),
  the learning crews (`learning/mining.py:379-395`,
  `learning/update_frame.py:427-442`). Eight construction sites, one
  staging call each.
- **Working directories.** Implementation: a clone per node at
  `<campaign>/sessions/<branch>` (`experiment_session.py:49-180`); its
  close runs `git add .` and pushes the branch (`346-439`). Ideation, the
  lens planner and the selector share one detached worktree from
  `materialize_ref` (`experiment_workspace.py:205-231`). The judge, the
  maintainer and the difficulties fallback run at the campaign root.
  Untracked data reaches a clone through `_bring_dropped_data`
  (`experiment_session.py:182-196`), the precedent for the statement copy.
- **MCP.** `get_mcp_config` (`gated_mcp/presets.py:479-623`) returns the
  `mcp_servers` dict both adapters take verbatim: Claude writes it to
  `.claude_mcp/mcp_config.json` and passes `--mcp-config`
  (`claude_code_agent.py:405-447, 1221-1224`); Codex turns it into `-c
  mcp_servers.<name>.*` (`codex_agent.py:48-83`). Harness servers merge
  into that dict. Tool names are `mcp__<server>__<tool>` on both hosts.
- **Command lines.** Claude: `claude -p --dangerously-skip-permissions
  --output-format stream-json ... [--mcp-config] [--append-system-prompt]`
  (`claude_code_agent.py:1168-1230`); nothing writes `.claude/`, settings
  or hooks today. Codex: `codex exec --sandbox danger-full-access
  --skip-git-repo-check ... --json` (`codex_agent.py:232-256`); nothing
  writes `.codex/`.
- **Prompts.** The handler's problem context (`environment/handlers/generic.py:73-144`)
  reaches `{{problem}}` in `ideation_claude_code.md`, `ideation_selector.md`,
  `ideation_lens_planner.md` and `implementation_claude_code.md`
  (`ideation.py:903-930`, `implementation.py:492-538`,
  `lens_planning.py:316-327`); the judge gets only `goal`
  (`feedback_generator.py:212-244`); the deploy prompts get
  `solution.brief.objective`; the learning crews get no task text. Each
  renderer substitutes differently (`{{var}}` replace, `str.format`,
  `.replace`), so the guidance is a template variable rendered with the
  rest, never text appended before rendering.
- **Records.** Launch record `execution/inbox.py:394-455` (schema 1, the
  fingerprinted keys at 427); status header `execution/observability.py:164-177`,
  phases `311-325`; checkpoint `execution/run_checkpoint.py:53-126`
  (schema 3), refusals `279-315`; trajectory manifest
  `learning/trajectory_store.py:382-436`; solution record `handles.py:547-604`,
  `build()` sets `harness=None` at `kapso.py:1576`.
- **Setup today.** `_setup_kapso_directories` (`search_strategies/base.py:618-677`)
  copies and commits `kapso_evaluation/` and `kapso_datasets/`; the only
  pre-iteration agent session is the maintainer's
  (`orchestrator.py:689-720`). No task statement is written anywhere; no
  `prepared/` exists.
- **Verification today.** Integrity enforcement (`base.py:784`), the
  registered-evaluation frame (`registered_evaluation.py:285-404`), the
  judge's `<evaluation_valid>` tag, the maintainer's change requests
  (`orchestrator.py:898-945`). No per-attempt session.
- **Delegates today.** The mining and update frames stage
  `.claude/agents/*.md` into their bundle directories
  (`learning/mining.py:334-377`, `learning/update_frame.py:372-415`), the
  precedent for staging; `--agents` makes the file unnecessary.
- **Preflight.** `Requirement(label, ok, fix, origin, required, detail)`
  (`core/preflight.py:101-116`); builders per verb (`907-913`); shape
  precedents for a binary on PATH (`345-351`), an env variable (`389-397`),
  a file (`58-68`).

Pre-existing behaviours the map found that are not WP2's to fix, recorded
for the packages that own them: `handler.additional_context` appended
after construction never reaches a prompt (`kapso.py:1484-1486`), so the
serving intro is not served today (WP3); `implementation_web: false` only
trims the Claude allow-list, which does not restrict under
`--dangerously-skip-permissions`, so the knob binds on Codex only (WP4
replaces it with a hook); build sessions bypass `agents.yaml` defaults
(`factory.build_config`), which deploy and learn do not (WP6 or WP4);
`strict_mcp_config` is never set for build sessions, so a user's own
Claude servers are mounted in campaigns (WP6); the Codex adapter sets
`default_tools_approval_mode="auto"` for hosted gates, which the probe
shows does not pre-approve under a read-only sandbox (verified with a
stdio server; a hosted server is checked when a Codex inference session
mounts one, WP4).

## Host facts, verified 2026-10-24 on the development box

Claude Code 2.1.304 and codex-cli 0.153.4; the probe scripts and event
dumps are archived with the proof run. These are the facts the master plan
listed as unverified, plus the ones the staging design needed:

| Fact | Claude Code | Codex |
|---|---|---|
| hooks file the engine stages | `--settings <file>`; fires in `-p` | `<cwd>/.codex/hooks.json` with `--dangerously-bypass-hook-trust` |
| hook working directory | the session cwd | the session cwd |
| shell tool name in events and matchers | `Bash` | `Bash` |
| file tool name | `Write`, `Edit`, `MultiEdit`; `tool_input.file_path` | `apply_patch`; a matcher `Edit\|Write\|MultiEdit` also fires on it; `tool_input.command` is the patch text with `*** Add File:` / `*** Update File:` lines |
| MCP tool name | `mcp__<server>__<tool>`; the event also carries `mcp_server` | `mcp__<server>__<tool>` |
| `Stop` and `stop_hook_active` | `False`, then `True` after a `{"decision": "block"}` | same |
| PreToolUse deny with a reason | followed by the model | followed (three denials in one session, each reason obeyed) |
| `SubagentStart` / `SubagentStop` | fire with `agent_type` = the agent's name | fire |
| sub-agents | `--agents '{"name": {"description", "prompt"}}'`; invoked through `Agent`, `subagent_type` = the name | `multi_agent` stable: `collaboration.spawn_agent` / `wait_agent` exist; named roles per invocation not yet verified |
| stdio MCP server under the sandbox | `--mcp-config` + `--strict-mcp-config` | `danger-full-access`: runs; `workspace-write` and `read-only`: "MCP tool call requires approval, but approval policy is never" unless `default_tools_approval_mode="approve"` (accepted values `auto`, `prompt`, `writes`, `approve`) |
| `--strict-config` | | fails on this box's user config (`preferred_auth_method`); usable with `--ignore-user-config` |

## Changes

Each one a commit with its test; the order is the order of landing.

1. `harness/manifest.py`, `harness/hash.py`: the schema as dataclasses
   (`Manifest`, `ModuleAttachments`, `Environment`), `read_manifest(path)`
   with line-numbered errors, the content hash. Test `tests/test_harness_manifest.py`:
   the trading example parses to the expected attachments per module; an
   unknown module, field, key or schema version raises naming the line;
   the hash is stable across runs and changes with one byte of one page,
   not with a `__pycache__` file.
2. `harness/check.py`: `check(path) -> CheckReport`, every failure,
   warning and lacking item of the Interface. Test `tests/test_harness_check.py`:
   one negative case per failure rule (a fixture harness mutated one rule
   at a time), one per warning, the lacking list from a fake PATH and
   `.env`; and `examples/harnesses/trading` has zero failures and zero
   warnings (the example stays valid, or the test says which rule it
   broke).
3. `harness/reference.py`, `harness/store.py`: the grammar, `resolve`,
   the store with `add`, `update`, `remove`, `list`, `recent`. Test
   `tests/test_harness_store.py`: the three forms and the GitHub shorthand
   parse as pinned; a local bare repository stands in for the remote and
   `add` lands under `<store>/<slug>@<rev>/<subdir>`; `update` moves a
   branch reference and leaves a tag alone; a string matching no form
   raises listing the forms.
4. `harness/__init__.py`: `Harness`, `load(ref, config)` (resolve, check,
   raise on failures, hash, prerequisites), `Prerequisite`,
   `HarnessError`; `Kapso.load_harness`, `Kapso.harness`; the config block.
   Test `tests/test_harness_load.py`: a failing harness never loads; a
   missing command lands in `missing` with its fix line; `ref()` matches
   `HarnessRef`.
5. The records: the launch key, the status header and phase, the
   checkpoint schema 4 with the refusal, `trajectory.yaml`, `build()`
   filling `solution.harness`. Test `tests/test_harness_records.py`
   (provider mocked, the fake orchestrator from `tests/handles_support.py`):
   a build with a loaded harness writes the triple into all four campaign
   records with the same hash; a resume after one byte of a page changed
   is refused naming both versions and hashes; a resume with the same
   content from another path proceeds.
6. The prerequisite refusal in `build()` and the environment block in
   `preflight` (`doctor build --harness <ref>` prints what the machine
   lacks in the doctor's own table). Test: `tests/test_harness_prereqs.py`
   and two rows in `tests/test_cli_doctor.py`.
7. `harness/staging.py`, `harness/hooks.py`: `stage_session`, the
   guidance block, the skills copy, the server merge, the agents file, the
   hooks merge, the record; the two adapters' new keys; the ignore lines.
   Test `tests/test_harness_staging.py`: goldens of the staged tree for
   the trading harness's implementation and ideation modules on both
   hosts (`tests/golden/harness_staging/`), the merged hooks file in
   manifest order with `${PLUGIN_ROOT}` expanded and no `${` left, the
   servers' `cwd` and `env`, and the adapters' command lines carrying
   `--settings`, `--agents`, `--dangerously-bypass-hook-trust` and
   `approve`.
8. The task statement and prepared resources: `kapso_task.md`, the
   `prepared/` symlink and the statement copy in `experiment_session.py`
   and `materialize_ref`. Test `tests/test_harness_task_statement.py`:
   the statement holds the whole brief (a 50-kilobyte objective, as WP1
   tests the prompt) and the evaluation and data references; a clone sees
   the statement and `prepared/market-data/MANIFEST.json` through the
   link; the session close commits neither.
9. The guidance in every module's prompt: the `{{domain_guidance}}`
   variable in the ideation, ensemble, selector, lens planner and
   replanner, implementation, judge, maintainer setup, deploy selector
   and adapter templates and the two crews' lead prompts; the eight
   staging calls. Test `tests/test_harness_guidance.py`: for each module
   the rendered prompt contains `guardrails.md` and the module page whole
   and names the skills and delegates the manifest lists; a module with
   no harness renders with no "Domain guidance" heading and the
   implementation prompt still ends with the closing line; the existing
   prompt tests stay green.
10. The setup session: the `setup.md` template, the orchestrator step,
    the `prepared/*` listing, the status phase. Test
    `tests/test_harness_setup.py` (the agent stubbed to create
    `prepared/market-data/MANIFEST.json`): the statement gains the
    resource and the status file's `setup` phase names it; with no setup
    page and no setup attachment no session runs.
11. The verification session: the `verification.md` template, the files,
    the worktree, the verdict contract, the void path, the judge's view.
    Test `tests/test_harness_verification.py` (the agent stubbed to write
    each verdict): `void` clears the score, excludes the node from parent
    selection and delivery and increments `rejected_candidates`; `valid`
    passes the summary to the judge; a malformed verdict raises; no
    verdict is recorded as `none` and the judge is told.
12. Deploy and learn: `deploy()` and `learn()` resolve the harness from
    the object or the record, refuse a different name, stage the
    deployment and learning modules; `kapso deploy --harness`. Test:
    `tests/test_solution_open.py` (two refusal cases), `tests/test_deployment_adapter.py`
    (the adapter prompt carries the deployment page), `tests/test_mining_frame.py`
    (the lead prompt carries the learning page), `tests/test_trajectory_store.py`.
13. `cli/harness.py`: the seven subcommands; `--harness` on `kapso
    build`. Test `tests/test_cli_harness.py` (the parser's own actions
    enumerated, as `test_cli_build.py` does; `new` writes the two files
    and they pass `check`; `check` exits 1 on a failure and 0 with
    warnings; `list` prints the three rows; `export` writes the two
    layouts and `--format cursor` is refused) and one row in
    `tests/test_cli_build.py`.
14. The trading example: `examples/trading/` (`generate.py` for synthetic
    bars with a weak momentum effect and a cost model, `evaluation/evaluate.py`
    printing the risk line then `sharpe: <value>` and writing
    `kapso_evaluation/result.json`, with `--fast`; `repo/strategy.py`, a
    baseline the evaluator measures; `kapso-brief.md` with `Harness
    ../harnesses/trading`; `run.py` under twelve lines; the four-section
    README with the recorded result and its provenance), the two file
    hooks of the harness reading both tool-input shapes, the examples
    table. Test `tests/test_examples_trading.py`: the evaluator on the
    baseline prints the contract's last line and the fast mode is marked;
    the example's brief parses with the harness line.
15. Docs: `docs/harnesses/{index,use,write,example-trading}.mdx`,
    `docs/reference/harness.mdx` (manifest, pages, skills, delegates,
    `mcp.json`, hooks with the host table above, `check`, `export`), the
    `load_harness`, `kapso harness` and `--harness` entries in the API,
    CLI and brief-format references, `docs.json` with the Harnesses group;
    `scripts/check_snippets.py` covers the new pages; `mint validate` and
    `mint broken-links` green.
16. The grep test `tests/test_no_evolve_left.py` gains nothing; a new
    `tests/test_harness_layout.py` pins that no file under `src/kapso/`
    outside `harness/`, the adapters and the eight staging calls imports
    `kapso.harness` (the harness stays one package with one seam per
    session).

## Tests

- Syntactic: the files above, in the curated gate, with the CI invocation
  unchanged. Negative cases: every `check` rule; the resume refusal; the
  malformed verdict; the secret literal; a hook with an unknown event; a
  reference of no form. Goldens: the staged trees and the merged hooks
  file for the trading harness per host. Contract: the verdict schema,
  the record fields, the guidance block's shape (pages whole, never
  clipped: a 20-kilobyte page reaches the prompt in full).
- Proof run, on the fresh machine, from the wheel: the trading example on
  both CLIs, two machines in parallel (`kapso-fresh-wp2-claude`,
  `kapso-fresh-wp2-codex`), `--budget-minutes 75 --budget-experiments 2`
  (ideation alone takes twelve to fourteen minutes on the shipped config,
  WP1's finding; setup and verification add two sessions). The archived
  campaign must show: the triple in `launch.json`, `status.json`,
  `run_state.json` and `solution.json` with one hash; `kapso_task.md`
  listing `market-data` under prepared resources and
  `prepared/market-data/MANIFEST.json` present; a `harness.json` per
  session with the staged lists matching the manifest; in the stream
  artifacts, the `session-brief` context line and at least one
  `scan-writes` or `require-results` hook decision; a
  `verification/<branch>/verdict.json` per attempt; a delegate invocation
  in at least one verification or feedback session; `Solution.open` in a
  second process reading the record with `solution.harness` filled; and
  `kapso harness check` quiet on the machine before the build. Both CLIs
  must reach the same end state; a difference is a finding.
- Semantic hook: S3's guideline-completeness test becomes runnable: a
  model author (Codex gpt-6-astra at xhigh, and Claude opus-5) with only
  the authoring guide, the design and the trading example writes a
  `pipeline-dbt` harness in a scratch directory; every guess it logs is
  a sentence missing from the guide; the result must pass `check`. Record
  the two guess counts and the check output in this plan.

## Acceptance

- `kapso harness new x && kapso harness check x` is quiet, and `check
  examples/harnesses/trading` reports zero failures and zero warnings.
- `kapso build --brief examples/trading/kapso-brief.md --evaluation
  evaluation --data data --repo repo --output campaign` on the fresh
  machine stages every module of the trading harness on both CLIs, and
  the archived campaign shows each item of the proof-run list.
- A resume after editing one page is refused by name with both hashes; a
  build with `BROKER_API_KEY` unset is refused before any session, naming
  the variable and `.env`.
- `solution.harness`, the launch record, the status header, the
  checkpoint and `trajectory.yaml` carry one and the same triple.
- A build with no harness behaves as at `b49d3827`: no new session, no
  staged file, no "Domain guidance" heading, `solution.harness` `None`;
  the gate's count grows and nothing that passed stops passing.
- The host-fact table above is confirmed by the proof run on the fresh
  machine, including the one row it left open (Codex named roles).
- Both reviewers' findings on this plan and on the pull request are
  answered below; the gate is green; the docs checks are green.

## Risks

| Risk | What is done |
|---|---|
| Codex cannot take named agent roles per invocation | the build phase probes `agents.<name>` first; the fallback is in the Interface (spawn with the agent file's text), and the proof run shows which one shipped |
| env references for harness servers: the host does not forward `${VAR}` | a probe in the build phase settles inheritance per host; if neither host forwards, the engine passes the names in an explicit list the host supports, never the values |
| the per-session staging misses a construction site | `tests/test_harness_layout.py` enumerates the sites that import the staging call; the guidance test renders every module |
| a staged file reaches a candidate branch | the ignore lines are committed before the first clone, and the task-statement test asserts the close commits nothing staged |
| ideation on the shipped config leaves no time for setup and verification in the proof | 75 minutes and two experiments; the finding on ideation's duration is WP4's |
| the verification session voids good attempts | a `void` needs findings with evidence (the page and the verdict contract say so); the record keeps every verdict for the author's loop; the judge sees the findings |
| the Claude weekly token window | the gate before the proof, as for WP1; the Codex machine runs on the API key |
| scope: sixteen changes | the order lands a usable loader and records first (1 to 6), so a smaller package can ship if the proof finds a wall at staging |

## Review

To be filled: the cross-model review of this plan (Codex gpt-6-astra at
xhigh and Claude Code opus-5 through `scripts/redesign/review.sh`), each
finding and how it was answered; then the pull-request review.
