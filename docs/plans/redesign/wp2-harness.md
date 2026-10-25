# WP2: the harness package

2026-10-24, revised after the cross-model review (see Review). Branch
`wp2-harness`, off `redesign` once WP1 is merged (written against
`wp1-build` at `b49d3827`; it rebases). Size XL as a whole; the first
shippable slice (changes 1 to 11, a complete build path) is L. Depends on
WP1 (`Brief.harness`, `Solution.harness`, `HarnessRef`, the launch record,
`kapso build`).

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
content hash and the identity `{name, version, hash, source}` in the launch
record, the status file, the checkpoint (a resume refuses a changed hash
by name; a change mid-campaign fails loud), the solution record and the
trajectory manifest; staging into every session the engine runs (pages
under "Domain guidance", skills where the CLI discovers them, servers
beside the gates, delegates as the host's sub-agents carrying the pages,
hooks merged in manifest order); the two module sessions the engine does
not have yet and a harness needs: setup (a domain statement and prepared
resources) and verification (a verdict per attempt, inside the attempt
pipeline, that can void it); prerequisite refusal scoped to the modules a
verb runs; `load_harness` on the facade; `--harness` on `kapso build` and
`kapso deploy`; `kapso harness new | check | list | add | update |
remove`; the `trading` example as a task on the trading harness, with its
probe run on both CLIs; the Harnesses documentation section.

**Not in scope.** Experience (WP3: `load_experience`, the brief's
`Experience` line, scope by harness; WP2 records the identity a lesson is
scoped by). `--target` on deploy and the bundled targets as skills (WP5;
WP2 stages the deployment module into the sessions deploy runs, through
the interface asked for below). The retirements (WP4: `design_axes`,
`implementation_web`, `additional_context`, the handlers' prose; a harness
and `additional_context` coexist until then, the guidance never injected
through `additional_context`). The rendering of hook decisions, delegate
reports and verdicts in `kapso trace` and `watch --tree` (WP6; WP2 writes
what WP6 renders: a stream artifact and a staging record per session, the
verdict files, the structured identity in the status file). `kapso learn
<campaign>` and its `--harness` flag (WP3 rewrites `cli/learn.py`; the
Python `learn()` takes the harness from the object or the record here).
Bundled harnesses (WP8; WP2 creates the directory they resolve from and
`list` says none ship yet). The authoring plugin (WP7). **`kapso harness
export`** (moved to WP7, which owns the host plugin layouts: an export
has to carry `servers/`, the requirements, the hook scripts and the
delegates with their references rewritten, and prove the result loads on
each host; none of that is needed for a build). The Harness² editor loop.

## Interface

### The reference grammar

Three forms, tried in this order; a string that matches none raises
`HarnessReferenceError` listing the forms:

```
trading                                   a bundled name: [a-z0-9][a-z0-9-]*, a directory under src/kapso/harness/bundled/
./harness/trading  ~/h/trading  /abs      a path: a directory that exists; used in place, never copied
git+https://github.com/acme/harnesses@v3#trading     a git reference: url, optional @rev, optional #subdirectory
acme/harnesses@v3#trading                 GitHub shorthand: owner/repo with @rev or #subdirectory present
```

A string with one slash and neither `@` nor `#` is a path, and a path that
does not exist is reported as one (`no directory /abs/harness/trading and
no bundled harness named "harness/trading"; the forms are ...`), never
tried as a repository. A git reference is cloned once into
`<store>/<host>-<owner>-<repo>@<rev>/` (`rev` as written, `/` replaced by
`-`, `HEAD` when absent), with `source.json` in the clone recording the
remote, the rev as written and the resolved commit; the harness is
`<clone>/<subdirectory>`. `kapso harness update` re-fetches a branch or
`HEAD` reference; a tag or a sha is never re-fetched. `remove` deletes one
fetched clone, every harness it holds, and says so. The store is
`harness.store` in the config. A path in a brief's `Harness` line
resolves against the working directory at build time, as every other path
the CLI takes.

### The manifest

`harness.yaml`, the design's section 2 with one amendment: `version` is
required (the identity every record carries is name, version and hash;
`kapso harness new` writes `0.1.0`, and the design's section 1 sentence
gains the word). `schema_version: 1`; `name` (the bundled-name grammar),
`version`, `description`; `environment: {python: <requirements file>,
commands: [..], gpu: bool}` optional; `modules.<setup|ideation|implementation|verification|feedback|learning|deployment>`
each with the four lists `skills`, `mcp_servers`, `agents`, `hooks`,
every list optional and empty by default. Any other key, module or field
fails `check`. Pages are `instructions/guardrails.md` (every module) and
`instructions/<module>.md`; a module with no entry still gets its pages.

### `check`

```python
from kapso.harness import check_harness
report = check_harness(path, page_warning_lines=...)   # CheckReport(failures, warnings, missing)
```

A file that does not parse (YAML, JSON, front matter) raises with the
parser's own file and line (CLAUDE.md rule 2); `check` reports structural
problems of files it could parse. Failures (the run does not start): an
unsupported `schema_version`; an unknown key, module or field; a reference
that resolves to nothing (a skill name with no `skills/<name>/SKILL.md`,
an agent with no `agents/<name>.md`, a server with no key in `mcp.json`,
a hook with no `hooks/<name>/hook.json`); a skill or agent without `name`
and `description` front matter, or a skill whose `name` is not its
directory; an `mcp.json` outside the `mcpServers` schema (stdio
`command`, `args`, `env`, `cwd`; `streamable-http` `url`, `headers`); a
server name outside `[A-Za-z0-9_-]+` or equal to the engine's
`gated-knowledge`; a `hook.json` outside `{"hooks": {<event>:
[{matcher?, hooks: [{type: command, command}]}]}}` (the one hook shape
both hosts run from a file); a hook event outside the hosts' set
(`SessionStart`, `SessionEnd`, `UserPromptSubmit`, `PreToolUse`,
`PostToolUse`, `PermissionRequest`, `Stop`, `SubagentStart`,
`SubagentStop`, `PreCompact`, `PostCompact`); a hook command naming a
`${PLUGIN_ROOT}/...` file that does not exist; an `env` value in
`mcp.json` that is a literal for a name containing `KEY`, `TOKEN`,
`SECRET` or `PASSWORD`, or any value with a known credential prefix
(`sk-`, `kpsk_`, `ghp_`, `xoxb-`); a named requirements file that does not
exist. Every failure carries the file and, where there is one, the line.

Warnings: a skill, agent or hook directory no module lists; a skill a
module lists that its page (`instructions/<module>.md`, else
`guardrails.md`) never names; an always-on page longer than
`page_warning_lines` (the config's `harness.page_warning_lines`, 40 in
the shipped file, threaded by every caller); an `env` value of
twenty-four or more opaque characters that is not a reference.

Missing (what this machine lacks; reported, never a failure of the
harness), as `core.preflight.Requirement` rows (`label`, `ok`, `fix`,
`origin`), each tagged with the modules that need it: a command in
`environment.commands` not on PATH; the first word of a hook or server
command not on PATH (`python` is absent on a stock Ubuntu; the fix line
says `python3`); an env variable a server references that is set
neither in the process environment nor in `.env` (a presence probe, the
precedent is `core/preflight.py:389-397`; no value is read into the
engine); a python distribution from the requirements file not importable
by the interpreter the engine runs (`importlib.metadata`, name only;
version markers are checked when the file pins them); a GPU when `gpu:
true` and `nvidia-smi` is absent or fails.

The CLI prints the onboarding document's summary: `check ok (7 skills, 2
agents, 2 servers, 6 hooks)`, then warnings, then `needs ...` rows with
where each is read from; exit 1 on a failure.

### The handle

```python
kapso = Kapso(config="kapso-config.yaml")
harness = kapso.load_harness("./harness/trading")

harness.name, harness.version, harness.description
harness.hash                 # sha256 over every regular file under the directory (sorted relative paths and
                             # bytes; .git, __pycache__, *.pyc excluded; a symlink hashes as its target path
                             # string); full hex; prints show the first twelve
harness.source               # the reference as given, with a path made absolute
harness.path                 # the directory the run reads
harness.modules["implementation"]   # ModuleAttachments(skills, mcp_servers, agents, hooks): four tuples of names
harness.environment          # HarnessEnvironment(python: Path | None, commands: tuple[str, ...], gpu: bool)
harness.missing              # [Requirement] unmet on this machine, each naming the modules that need it
harness.ref()                # HarnessRef(name, version, hash, source) — what the records carry
```

`load_harness` resolves (fetching a git reference into the store when
absent, and printing `fetched <path>` when it did), runs `check`, raises
`HarnessError` with the report's failures when there are any (warnings
are printed), computes the hash, reads the prerequisites into `missing`,
sets the object's harness and returns the handle. A second call replaces
the first. `Kapso.harness` is the loaded handle or `None`. The design's
section 8 shows `modules[...]` as a mapping; the dataclass is the
amendment, recorded in DECISIONS.

### What the verbs do with it

- `build()`: the harness is the object's when one is loaded, else the
  brief's `Harness` line resolved the same way, else none (today's generic
  behaviour, unchanged: no setup or verification session, nothing staged,
  `solution.harness` `None`). A loaded harness wins over the brief's line
  (the rule call arguments follow for budgets) and the launch print names
  the one used and the sessions it adds (`harness setup; verification per
  attempt`). With a harness: the prerequisites are checked again at the
  call (never from the load's cache) and the build refuses while any
  requirement of the modules a build runs (setup, ideation,
  implementation, verification, feedback) is unmet, naming each, where it
  is read from and the line that fixes it; deployment-only and
  learning-only requirements are printed as advisory. `kapso build
  --detach` does this before it forks, so the handoff never claims a
  launch that died on a prerequisite. Then: the launch record with
  `harness: {name, version, hash, source}`; the status file's structured
  `harness` key; the checkpoint with the identity (schema 4); the task
  statement; setup when the harness has a setup page or attachment; every
  session staged from the manifest, the harness re-hashed at each staging
  call and a changed hash failing loud (`the harness changed since launch:
  <hash12> at launch, <hash12> now; restore it or start a new campaign`);
  verification per attempt when the harness has a verification page or
  attachment; a `Solution` whose `harness` is the ref. Nothing is
  installed by the engine (DECISIONS).
- resume: the checkpoint's identity is compared with the harness resolved
  for the resume (the loaded one, else the launch record's `source`
  resolved again); a different hash is refused by name, printing both
  versions and hashes and the way out for the form: a path (`restore the
  recorded content, for instance git checkout in <path>, or start a new
  campaign with a new --output`), a fetched reference (`the store still
  holds <path>; pass it with --harness, or start a new campaign`). A
  different source with the same hash proceeds and the launch record
  keeps the original. The harness is not part of the checkpoint's config
  fingerprint: the hash comparison is its check, with its own message.
- `deploy(solution)`, `learn(solution)`: the object's harness when loaded,
  else the record's `source` resolved again; a source that no longer
  resolves (another machine, a deleted branch) is refused naming the
  recorded identity and `pass --harness <ref> pointing at a copy of <name>
  <version>`; a solution with `harness: null` deploys and learns as today
  (a harness cannot be attached to a generic campaign after the fact);
  a loaded harness whose `name` differs from the record is refused;
  another version of the same name is allowed and printed beside the
  build's. `learn()` writes the build's identity into `trajectory.yaml` as
  `harness` and, when a different version did the learning,
  `learning_harness`; WP3 scopes lessons by the former. `deploy()` stages
  the deployment module into the selector and adapter sessions and prints
  both identities when they differ; a deployment record is WP5's.

### Threading

`harness` is a constructor argument of `OrchestratorAgent`, a field of
`SearchStrategyConfig`, and an explicit parameter of every phase function
that constructs a session (the sites are enumerated under Changes, 9). It
is excluded from `config_fingerprint` (above). Nothing reaches a session
through `additional_context` or the handler.

### Staging, per session

One function in `src/kapso/harness/staging.py`, called at every site that
constructs a coding-agent session, after the session's directory exists
and before the executing agent's `initialize`:

```python
staged = stage_harness(harness, module, session_dir=..., campaign_dir=..., session_id=..., host=...)
staged.guidance          # the "Domain guidance" block for the module's prompt(s); "" without a harness
staged.agent_specific    # keys merged into the session's CodingAgentConfig.agent_specific (below)
staged.allowed_tools     # the harness servers' tools, added to the session's allow-list and prompt tool list
staged.record            # written to <campaign>/.kapso/sessions/<session_id>/harness.json
```

Idempotent (a second call on the same directory and host replaces what it
wrote), safe under concurrency (the ensemble's members and the lanes share
directories: each host's files have fixed names and are written whole
with an atomic replace), and refused before anything is written when the
session directory already tracks a path it would write (a seed repository
with a skill of the same name under `.claude/skills/`, or its own
`.codex/hooks.json`): the message names the path and the harness file.

| Attachment | Staged as | Claude Code | Codex |
|---|---|---|---|
| pages | `## Domain guidance (harness <name> <version>)`: `guardrails.md` whole, then `<module>.md` whole, then the attachment lists (a skill per line with its description and how to open it; a delegate per line with its description and how to ask it; the servers by name with the `mcp__<server>__` prefix), then the paths: the task statement, `KAPSO_HARNESS_ROOT`, `prepared/<name>` for each prepared resource | a `{{domain_guidance}}` variable in each module template, placed before the template's closing section (`test_inbox_prompt.py` pins that the implementation prompt ends with the closing line); the maintainer, deploy and learning prompts, which render differently, get the block as a variable of their own renderer, never as text appended before rendering | same |
| skills | the directories copied whole into the session directory | `.claude/skills/<name>/` | `.agents/skills/<name>/` |
| mcp_servers | the named entries of `mcp.json`, `${PLUGIN_ROOT}` expanded to the harness path in `command`, `args`, `cwd` and `env`; `cwd` the session directory unless the entry names one; `env` gains `KAPSO_HARNESS_ROOT`; `${VAR}` references kept as references; merged into the `mcp_servers` dict beside the gates; `mcp__<server>` added to the allow-list and the prompt's tool list | written verbatim into `.claude_mcp/mcp_config.json`; the host expands `${VAR}` from the session environment (verified; an unset variable is left literal, which is why the prerequisite check confirms each one); `streamable-http` entries with `headers` verbatim | `-c mcp_servers.<name>.*` as today, plus `default_tools_approval_mode="approve"` (verified: `auto` leaves the call refused under a read-only or workspace-write sandbox) and `env_vars=[...]` for every `${VAR}` reference (verified: a stdio server does not inherit the parent environment, and `env_vars` forwards by name); `streamable-http` entries with `tool_timeout_sec` from `harness.server_tool_timeout_seconds` and headers through the key `--strict-config` accepts in the build phase, else refused by `check` for this host with a message |
| agents | each `agents/<name>.md` as a host sub-agent the session asks by name; the delegate's prompt is the guidance block (the pages, the task statement path, the attachment lists) followed by the agent file's body, so a delegate reads what its module reads | `--agents` with the JSON string the adapter serializes (verified inline: the model asks it through `Agent` with `subagent_type` = the name and gets the reply as the tool result; the host writes the agent transcript and names it in `SubagentStop`) | `-c agents.<name>.description=...` and `-c agents.<name>.config_file=<staged toml>` whose `developer_instructions` is the prompt (verified: the model spawned the role by name, the role followed its instructions, `SubagentStart`/`SubagentStop` carried `agent_type` = the name) |
| hooks | the listed `hooks/<name>/hook.json` files, in manifest order, their event lists concatenated into one `{"hooks": {...}}`, `${PLUGIN_ROOT}` expanded in every command | `--settings <session>/.claude/harness-hooks.json` (verified: hooks fire in `-p`) | `<session>/.codex/hooks.json` and `--dangerously-bypass-hook-trust` on the command (verified with the user config present; see Host facts for the open point the proof settles) |
| env | `KAPSO_HARNESS_ROOT=<harness.path>` in the session's and every server's environment | `env_overrides` | `env_overrides` |
| prepared resources | `<campaign>/prepared/` symlinked into the session directory when it is not the campaign root | | |
| task statement | `<campaign>/kapso_task.md` copied into the session directory when it is not the campaign root | | |
| evidence | `stream_artifact_path` set for every staged session, `<campaign>/.kapso/sessions/<session_id>/stream.jsonl`, so hook decisions, delegate calls and tool use are on disk for WP6 (and for `grep` until then) | | |

The staged files are ignored by the workspace's `.gitignore` (`.claude/`,
`.agents/`, `.codex/`, `prepared`, `kapso_task.md`, the last two without
a trailing slash so a symlink and a file match; committed before the
first clone) so a session's closing `git add .` never commits them into a
candidate. Hook matchers are written in Claude Code's tool names and work
as written on Codex (verified: `Bash`, `apply_patch`,
`mcp__<server>__<tool>` and `Edit|Write|MultiEdit`, which Codex aliases
onto `apply_patch`, all matched); a hook that needs the written file's
path reads `tool_input.file_path` on Claude Code and parses the
`apply_patch` header lines on Codex, the two file hooks of the trading
example do both, and the guide says so. Hook and server commands say
`python3`.

### The task statement, setup and prepared resources

With a harness, `build()` writes `<campaign>/kapso_task.md` before any
session: the brief rendered whole, the effective budget, the evaluation
reference (`kapso_evaluation/` provided, or "to be built from the brief's
protocol"), the data reference (`kapso_datasets/`), the harness name and
version, a `## Domain statement` section (empty until setup) and a `##
Prepared resources` section (empty until setup). The engine owns the
file and renders it; no session edits it. It is untracked and ignored;
staging copies it into every session directory; every module's guidance
names its path.

Setup runs once per fresh campaign, at the campaign root, after
`_setup_kapso_directories` and before the evaluation maintainer's setup,
when the harness has `instructions/setup.md` or any setup attachment: one
coding-agent session (the `coding_agent` block, full sandbox, the setup
module staged, the inbox gate mounted so a missing input pauses the
campaign with `WAITING ON YOU` as the flow's B5 describes, timeout
`harness.setup_minutes` clamped by the budget like every session) with
the engine's new `setup.md` template: the task statement, the paths, and
the contract "write your domain statement to `.kapso/harness_setup/statement.md`;
to return a prepared resource, create `prepared/<name>/` here; everything
under `prepared/` is mounted for every later session at the same relative
path and listed in the task statement". After the session the engine
re-renders `kapso_task.md` with the statement and the `prepared/*` names,
verifies the evaluation and data manifests it pinned at construction and
fails loud naming the harness if the session touched them, records
`harness_setup: done` with the resource names in the checkpoint (a crash
afterwards does not repeat the session) and in the status payload. A
setup session that leaves nothing under `prepared/` is not an error.

### Verification

Inside the attempt pipeline (`strategy._finalize_nodes`), after the
integrity check and the evaluation and before the judge, when the harness
has `instructions/verification.md` or any verification attachment. The
engine writes `<campaign>/.kapso/verification/<branch>/diff.patch` (`git
diff main...<branch>`) and `evaluation_output.txt`, materialises the branch
in a detached worktree (`materialize_ref`, as ideation does), and runs one
session there (the `feedback_generator` block's CLI and model, the
verification module staged, timeout `harness.verification_minutes`
clamped by the budget, Codex with `--add-dir` on the verification
directory) with the engine's new `verification.md` template: the two
paths, the task statement, and the verdict contract. The session writes
`<campaign>/.kapso/verification/<branch>/verdict.json`:

```json
{"verdict": "valid" | "void", "summary": "...", "findings": [{"rule": "...", "evidence": "strategy/signal.py:4 ..."}]}
```

The result is its own state on the node, `SearchNode.verification`
(`{"verdict", "summary", "findings"}`, serialized with the node), never a
rewrite of `evaluation_valid`: the judge receives it (a new keyword of
`generate_feedback`) and ANDs a `void` into the node's validity after its
own verdict, so the judge's default cannot resurrect a void; parent
selection and delivery read it. `void` sends the attempt down the path an
integrity rejection takes: its score is cleared, it is never a parent and
never delivered, it counts in `solution.rejected_candidates` (whose
meaning becomes "rejected by the integrity check or voided by
verification"; the per-node reason is in the experiment history), and
the judge is told the verdict and the findings. `valid` passes the attempt
to the judge with the summary. A malformed verdict raises (rule 2). A
session that ends without writing one is run once more with the same
inputs; still nothing, and the node is `unverified`: its score stands, it
stays eligible as a parent, it is never delivered while the harness has
verification, and the judge is told that verification produced no
verdict. The delivered candidate's verification is in the solution record
(`verification: {"verdict", "summary"} | null`, schema 3) and `explain()`
prints it as `Verified:      valid — <summary>`.

### The CLI

```
kapso harness new <name> [--dir <parent>]     # harness.yaml (version 0.1.0) + instructions/guardrails.md; prints the path and `kapso harness check <path>`
kapso harness check <ref>                     # `check ok (…)`, warnings, `needs …`; exit 1 on a failure; prints `fetched <path>` when it fetched
kapso harness list                            # bundled (none ship yet) and fetched, each with version and `needs …`; one line when the store is empty
kapso harness add <ref>                       # fetch (git) + check + needs, never failing on them; a path is checked in place
kapso harness update <ref>                    # re-fetch a branch reference, print the movement, then check it
kapso harness remove <ref>                    # delete one fetched clone (every harness in it); a path is refused: nothing was fetched
kapso build ... --harness <ref>               # wins over the brief's Harness line; validated before --detach forks
kapso deploy <campaign> --harness <ref>       # must name the record's harness; another version is allowed and printed
```

The `kapso harness` verb is one module and one tuple entry, plus its line
in `cli/__init__.py`'s epilog.

### Records

| Record | Field | Written by |
|---|---|---|
| `<campaign>/.kapso/launch.json` | `harness: {name, version, hash, source} \| null` | `build()` |
| `<campaign>/.kapso/status.json` | `harness` (the same four fields) in the payload; phases gain `harness_setup` and `verification`; the `harness_setup` payload names the prepared resources | `BuildStatus` (the key; WP6 renders it in `watch`) |
| `<campaign>/.kapso/run_state.json` | `harness` (the four fields), `harness_setup`; schema 4 | the checkpoint store |
| `<campaign>/.kapso/solution.json` | `harness` filled; `verification` added; schema 3; `explain()` prints the hash's first twelve characters | `Solution.save` |
| `<campaign>/.kapso/sessions/<session_id>/` | `harness.json` `{module, host, pages, skills, mcp_servers, agents, hooks, hash}` and `stream.jsonl` | every staging call and the adapters |
| `<campaign>/.kapso/verification/<branch>/` | `diff.patch`, `evaluation_output.txt`, `verdict.json` | the verification step |
| `<campaign>/.kapso/harness_setup/statement.md`, `<campaign>/kapso_task.md`, `<campaign>/prepared/` | the statement, the composed task file, the resources | the setup session, `build()` |
| `~/.kapso/trajectories/<id>/trajectory.yaml` | `harness` (the build's), `learning_harness` when different | `learn()` |

Session ids: implementation keeps the branch name; ideation members use
`ideation/iter<N>/<cli>_<model>` (their artifact names today); the selector
and the lens planner their artifact names; the judge `feedback/<branch>`;
verification `verification/<branch>`; setup `harness_setup`; deploy and
learning sessions their own directories.

### Config

```yaml
harness:
  store: ~/.kapso/harnesses          # fetched git references, one directory per <slug>@<rev>
  page_warning_lines: 40             # `check` warns on an always-on page longer than this
  setup_minutes: 20                  # the harness setup session's timeout, clamped by the budget
  verification_minutes: 10           # each verification session's timeout, clamped by the budget
  server_tool_timeout_seconds: 600   # a harness server's per-call timeout where the host takes one (Codex)
```

Read by a `load_harness_defaults()` beside `load_deployment_defaults`
(`core/config.py:52-62`), from the packaged file with a user file's
`harness:` keys over it, because `load_mode_config` merges only
`defaults:` and `modes.*` and a user's `--config` copy has no `harness:`
block. No other key: the harness and the engine config never share one.

## Ownership

Edits: `src/kapso/harness/` (new: `__init__.py`, `manifest.py`,
`reference.py`, `store.py`, `check.py`, `hash.py`, `staging.py`,
`hooks.py`, `templates/` for `new`, `bundled/` with a README as the
bundled-name root, and the package-data glob in `pyproject.toml` that
ships it); `src/kapso/cli/harness.py` (new), `cli/__init__.py` (the tuple
entry and the epilog line), `cli/build.py` and `cli/deploy.py`
(`--harness`, the pre-detach validation); `src/kapso/kapso.py`
(`load_harness`, the harness lines of `build`, `reply`, `deploy`, `learn`);
`src/kapso/core/config.py` (`load_harness_defaults`) and `config.yaml`
(the block); `src/kapso/handles.py` (`verification`, schema 3, the
twelve-character hash in `explain`); the adapters
`execution/coding_agents/adapters/claude_code_agent.py` (`settings_path`,
`agents` → `--settings`, `--agents`), `codex_agent.py` (`hooks_trust_bypass`,
`add_dirs`, `agents`, `approve` and `env_vars` for harness servers),
`search_strategies/generic/codex_ideation.py` (servers and hooks for a
Codex member); `execution/experiment_workspace/experiment_workspace.py`
(the ignore lines, `materialize_ref` staging), `experiment_session.py`
(the prepared symlink, the statement copy, staging after checkout);
`execution/search_strategies/base.py` (`SearchStrategyConfig.harness`,
`SearchNode.verification`, parent selection and delivery reading it),
`search_strategies/generic/{strategy,ideation,implementation,lens_planning,feedback_flow}.py`,
`feedback_generator/feedback_generator.py`, `evaluation_maintainer/maintainer.py`
(setup and change-request staging); the prompt templates under
`search_strategies/generic/prompts/` (`{{domain_guidance}}`; two new
templates `setup.md`, `verification.md`); `execution/orchestrator.py`
(the constructor argument, the setup step, the checkpoint fields),
`execution/run_checkpoint.py` (schema 4, the refusal),
`execution/observability.py` (the payload key, the two phases),
`execution/inbox.py` (the launch key, `RESUME_FROM_RECORD`); `examples/trading/`
(new), `examples/README.md`, `examples/harnesses/trading/` (the two file
hooks read both tool-input shapes; `python3` in commands),
`examples/harnesses/README.md`; `docs/research/harness-design.md`
(section 1's `version`, section 8's `modules` shape, section 8's export
line pointing at WP7); docs: `docs/harnesses/*.mdx` (new),
`docs/reference/{kapso-api,cli,brief-format}.mdx`, `docs/reference/harness.mdx`
(new), `docs.json`; the tests named below.

Interfaces asked of other owners (one call or one key each; the owner
keeps the file): **WP5** (`src/kapso/deployment/`): a `harness` field on
`DeployConfig` and one `stage_harness` call before the selector's and the
adapter's sessions (both agents of the adapter's fallback pair);
**WP6** (`observability.py`, `cli/watch.py`): the `harness` payload key
and the two phases are written by WP2, rendered by WP6; `doctor` gains no
harness flag here (`kapso harness check` reports what a machine lacks);
**WP3** (`learning/mining.py`, `update_frame.py`, `trajectory_store.py`):
the learning page into the two leads' prompts and the two `trajectory.yaml`
keys; **WP4** (`core/config.py`): `load_harness_defaults` lands here and
folds into WP4's one-override-file resolver when modes go.

Reads, does not edit: `src/kapso/gated_mcp/` (harness servers are mounted
beside the gates by merging dicts; the gate server's name is reserved),
`src/kapso/environment/handlers/` (WP4), `benchmarks/` (WP4 and WP8),
`cli/learn.py` (WP3), `docs/build/*` (WP1's, except one sentence on the
brief page pointing at the Harness line's reference page).

## The seam map (commit `b49d3827`)

What the code does today at each place WP2 cuts, so the change list below
is checkable. Short paths are under `src/kapso/`.

- **Session construction sites** (`CodingAgentConfig(` and
  `build_config(`): single ideation `ideation.py:316-350`; ensemble
  members `ideation.py:545-580` (Claude and OSS) and the Codex member
  through `codex_ideation.py:46-158` (no MCP, read-only sandbox, its own
  runner); the selector `ideation.py:788-844`; the lens planner
  `lens_planning.py:185-248`; implementation `implementation.py:208-317`
  (two constructions, `:210` and `:234`, Claude direct and Codex through
  the factory, plus the continuation at `:270-279`), after
  `ExperimentSession.__init__` has already constructed a workspace agent
  (`experiment_session.py:157-171`) the generic run uses only for
  `_initialize_workspace`; the difficulties fallback
  `difficulties_generator.py:59-76`; the judge
  `feedback_generator.py:82-112, 154-182`; the maintainer
  `maintainer.py:274-278, 445-455`; deploy `deployment/selector/agent.py:157-168`
  and `deployment/adapter/agent.py:263-286` (called twice on fallback,
  possibly with another host); learning `mining.py:379-395`,
  `update_frame.py:427-442` (and its `run-role.sh` Codex worker at
  `:388`), `graders/frame.py:68-84`, `codify_run.py:246-300`,
  `behavior.py:113-127`. Which of these are staged, and which are not and
  why, is Changes 9.
- **Working directories.** Implementation: a clone per node at
  `<campaign>/sessions/<branch>` (`experiment_session.py:49-180`); its
  close runs `git add .` and pushes the branch (`346-439`). Ideation, the
  lens planner and the selector share one detached worktree from
  `materialize_ref` (`experiment_workspace.py:205-231`), the ensemble's
  members in a thread pool (`ideation.py:609`) and K lanes in parallel
  (`strategy.py:815`). The judge, the maintainer and the difficulties
  fallback run at the campaign root. Untracked data reaches a clone
  through `_bring_dropped_data` (`experiment_session.py:182-196`).
- **The attempt pipeline.** `strategy._finalize_nodes` (`strategy.py:861-864`):
  integrity → `_evaluate_admitted_candidate` → `_generate_feedback`;
  `feedback_flow.py:94` sets `node.evaluation_valid = feedback_result.evaluation_valid
  and execution_valid` after the judge, whose default is `True`
  (`feedback_generator.py:302`); parent selection and delivery read
  `evaluation_valid` and the score (`strategy.py:1346, 1508, 1561, 1649`).
- **MCP.** `get_mcp_config` (`gated_mcp/presets.py:479-623`) returns the
  `mcp_servers` dict and the allowed-tool list; the callers build the
  allow-list and the prompt's tool list from the second value
  (`implementation.py:200-204`, `ideation.py:297-301`); Claude writes the
  dict to `.claude_mcp/mcp_config.json` and passes `--mcp-config`
  (`claude_code_agent.py:405-447, 1221-1224`); Codex turns it into `-c
  mcp_servers.<name>.*` (`codex_agent.py:48-83`, names validated
  `[A-Za-z0-9_-]+`, URL entries requiring `timeout`). The gate server is
  `gated-knowledge` (`presets.py:481`).
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
  `solution.brief.objective` through `str.format` and `.replace`
  renderers; the learning crews get no task text, and the grading
  `_fill` raises on a leftover `{{`.
- **Records.** Launch record `execution/inbox.py:394-455` (schema 1,
  `RESUME_FROM_RECORD` at 419, fingerprinted keys at 427); status header
  `execution/observability.py:164-177`, phases `311-325` (`setup` there
  means the strategy constructor's phase); checkpoint
  `execution/run_checkpoint.py:53-126` (schema 3), fingerprint input
  `orchestrator.py:231-257`, refusals `279-315`, the bootstrap checkpoint
  written after the maintainer's setup (`orchestrator.py:1356`);
  trajectory manifest `learning/trajectory_store.py:382-436`; solution
  record `handles.py:547-604`, `explain` prints the full hash at `:703`;
  `build()` sets `harness=None` at `kapso.py:1576`.
- **Config.** `load_mode_config` (`core/config.py:64-91`) merges
  `defaults:` under `modes.<MODE>`; `load_deployment_defaults`
  (`:52-62`) is the precedent for a top-level block.
- **Setup today.** `_setup_kapso_directories` (`search_strategies/base.py:618-677`)
  copies and commits `kapso_evaluation/` and `kapso_datasets/`;
  `provided_evaluation_manifest` is pinned at construction (`base.py:496-509`);
  the only pre-iteration agent session is the maintainer's
  (`orchestrator.py:689-720`). No task statement; no `prepared/`.
- **Delegates today.** The mining and update frames stage and remove
  `.claude/agents/*.md` whole (`learning/mining.py:334-377`,
  `learning/update_frame.py:372-415`); `--agents` makes the file
  unnecessary and the staging must not collide with theirs.
- **Preflight.** `Requirement(label, ok, fix, origin, required, detail)`
  (`core/preflight.py:101-116`); precedents for a binary on PATH
  (`345-351`), an env variable (`389-397`), a file (`58-68`).
- **Packaging.** `pyproject.toml:136` ships `*.txt/json/yaml/yml/md`
  package data and `packages.find` cannot collect hyphenated directories
  (`hooks/deny-snapshot`), so a bundled root needs its own glob.

Pre-existing behaviours the map found that are not WP2's to fix, recorded
for the packages that own them: `handler.additional_context` appended
after construction never reaches a prompt (`kapso.py:1484-1486`), so the
serving intro is not served today (WP3); `implementation_web: false` only
trims the Claude allow-list, which does not restrict under
`--dangerously-skip-permissions`, so the knob binds on Codex only (WP4
replaces it with a hook); build sessions bypass `agents.yaml` defaults
(`factory.build_config`), which deploy and learn do not (WP4);
`strict_mcp_config` is never set for build sessions, so a user's own
Claude servers are mounted in campaigns (WP6); the Codex adapter sets
`default_tools_approval_mode="auto"` for hosted gates, which does not
pre-approve under a read-only sandbox (verified with a stdio server;
checked for a hosted one when a Codex inference session mounts it, WP4);
ensemble members share one `.claude_mcp/` whose first `cleanup()` removes
the siblings' config (WP6 or WP4).

## Host facts, verified 2026-10-24 on the development box

Claude Code 2.1.304 and codex-cli 0.153.4; the probe scripts and event
dumps are under `scripts/redesign/runs/wp2-hostfacts/` (ignored, like the
proof archives). These are the facts the master plan listed as
unverified, plus the ones the staging design needed:

| Fact | Claude Code | Codex |
|---|---|---|
| hooks file the engine stages | `--settings <file>`; fires in `-p` | `<cwd>/.codex/hooks.json` with `--dangerously-bypass-hook-trust`; it fired with the box's user config present and did NOT fire under `--ignore-user-config` (even with `--enable hooks`); the engine never passes that flag, and the proof run confirms hooks fire under the fresh machine's minimal user config |
| hook working directory | the session cwd | the session cwd |
| shell tool name in events and matchers | `Bash` | `Bash` |
| file tool name | `Write`, `Edit`, `MultiEdit`; `tool_input.file_path` | `apply_patch`; a matcher `Edit\|Write\|MultiEdit` also fires on it; `tool_input.command` is the patch text with `*** Add File:` / `*** Update File:` lines |
| MCP tool name | `mcp__<server>__<tool>`; the event also carries `mcp_server` | `mcp__<server>__<tool>` |
| `Stop` and `stop_hook_active` | `False`, then `True` after a `{"decision": "block"}` | same |
| PreToolUse deny with a reason | followed by the model | followed (three denials in one session, each reason obeyed) |
| `SubagentStart` / `SubagentStop` | fire with `agent_type` = the agent's name, `agent_transcript_path` on stop | fire with `agent_type` = the role's name, `last_assistant_message` on stop |
| sub-agents | `--agents '{"name": {"description", "prompt"}}'` inline; invoked through `Agent`, `subagent_type` = the name | `-c agents.<name>.description=... -c agents.<name>.config_file=<toml>` (`developer_instructions` in the toml); the role was spawned by name and followed its instructions; `--strict-config` accepts the keys |
| stdio MCP server under the sandbox | `--mcp-config` + `--strict-mcp-config` | `danger-full-access`: runs; `workspace-write` and `read-only`: "MCP tool call requires approval, but approval policy is never" unless `default_tools_approval_mode="approve"` (accepted values `auto`, `prompt`, `writes`, `approve`) |
| a stdio server's environment | inherits the CLI's; `${VAR}` in `env` expanded from it, an unset variable left literal | does not inherit; `${VAR}` passed literally; `mcp_servers.<name>.env_vars=[...]` forwards by name (`forward_env`, `inherit_env`, `env_passthrough` are unknown fields) |
| `--strict-config` | | fails on this box's user config (`preferred_auth_method`); usable with `--ignore-user-config` |

## Changes

Each one a commit with its test; the order is the order of landing.
Changes 1 to 11 are the first shippable slice: a harness that a build
loads, records, stages, sets up and verifies with.

1. `harness/manifest.py`, `harness/hash.py`: the schema as dataclasses
   (`Manifest`, `ModuleAttachments`, `HarnessEnvironment`),
   `read_manifest(path)` with line-numbered errors, the content hash.
   Test `tests/test_harness_manifest.py`: the trading example parses to
   the expected attachments per module; an unknown module, field, key or
   schema version raises naming the line; the hash is stable across runs
   and changes with one byte of one page, not with a `__pycache__` file.
2. `harness/check.py`: `check_harness(path, *, page_warning_lines) ->
   CheckReport`, every failure, warning and missing row of the Interface,
   and the CLI's summary line. Test `tests/test_harness_check.py`: one
   negative case per failure rule (a fixture harness mutated one rule at
   a time, including the reserved and the non-TOML server names), one per
   warning, the missing rows from a fake PATH and `.env` with their
   modules; an unparseable `mcp.json` raises with the parser's line; and
   `examples/harnesses/trading` has zero failures and zero warnings.
3. `harness/reference.py`, `harness/store.py`: the grammar, `resolve`,
   the store with `add`, `update`, `remove`, `list`. Test
   `tests/test_harness_store.py`: the forms parse as pinned, including the
   shorthand rule and the missing-path message; a local bare repository
   stands in for the remote and `add` lands under `<store>/<slug>@<rev>/<subdir>`
   with `source.json`; `update` moves a branch reference and leaves a tag
   alone; `remove` refuses a path.
4. `harness/__init__.py`: `Harness`, `load_harness(ref, *, config)`
   (resolve, check, raise on failures, hash, prerequisites),
   `HarnessError`, `HarnessReferenceError`; `Kapso.load_harness`,
   `Kapso.harness`; `load_harness_defaults` and the config block. Test
   `tests/test_harness_load.py`: a failing harness never loads; a missing
   command lands in `missing` with its fix line and its modules; `ref()`
   matches `HarnessRef`; the config block reaches `check` from a user
   file with no `harness:` key.
5. The threading and the records: `OrchestratorAgent(harness=...)`,
   `SearchStrategyConfig.harness`, the fingerprint exclusion, the launch
   key and `RESUME_FROM_RECORD`, the status payload key and phases, the
   checkpoint schema 4 with the refusal messages per form, the re-hash
   at staging, `build()` filling `solution.harness`. Test
   `tests/test_harness_records.py` with the real orchestrator, checkpoint
   store and status writer and only the sessions stubbed (the pattern of
   `tests/test_run_checkpoint.py`): a build with a loaded harness writes
   the identity into all four campaign records with one hash; a resume
   after one byte of a page changed is refused naming both versions and
   hashes and the form's way out; a resume with the same content from
   another path proceeds; a change between two sessions fails loud.
6. The prerequisite refusal in `build()`, `deploy()` and `learn()`,
   scoped by module, re-checked at the call; `kapso build --detach`
   validating before it forks. Test `tests/test_harness_prereqs.py`: a
   deployment-only variable does not refuse a build and is printed as
   advisory; a missing implementation command refuses with the fix line;
   fixing `.env` after `load_harness` is enough; the detach parent
   refuses before any child exists (`tests/test_cli_detach.py` gains a
   case).
7. `harness/staging.py`, `harness/hooks.py`: `stage_harness` and
   `StagedHarness`, the guidance block, the skills copy, the server merge
   with the allow-list and the per-host translation, the agents with the
   pages prepended, the hooks merge, the env, the record, the stream
   artifact path, the ignore lines, the tracked-path refusal, idempotency;
   the two adapters' new keys. Test `tests/test_harness_staging.py`:
   goldens of the staged tree for the trading harness's implementation
   and ideation modules on both hosts (`tests/golden/harness_staging/`),
   the merged hooks file in manifest order with `${PLUGIN_ROOT}` expanded
   and no `${` left, the servers' `cwd`, `env`, `env_vars` and `approve`,
   the delegate prompt beginning with the module's pages, the adapters'
   command lines carrying `--settings`, `--agents`,
   `--dangerously-bypass-hook-trust` and `--add-dir`; two hosts staging
   the same directory concurrently; a seed repository tracking
   `.claude/skills/backtesting` refused by name; the guidance block's
   byte count per module recorded by the test's output for the plan.
8. The task statement and prepared resources: `kapso_task.md` rendered
   by the engine, the `prepared` symlink and the statement copy in
   `experiment_session.py` (after checkout, before the executing agent)
   and `materialize_ref`; the trading example's `protect-prepared` hook
   resolving both paths. Test `tests/test_harness_task_statement.py`:
   the statement holds the whole brief (a 50-kilobyte objective, as WP1
   tests the prompt), the effective budget and the references; a clone
   sees the statement and `prepared/market-data/MANIFEST.json` through
   the link; the session close commits neither the link nor the file;
   the hook denies a write through the real symlink on both event shapes.
9. The guidance in every module's prompt and the staging call at every
   site. Staged: single ideation, the ensemble members (Claude, OSS and
   the Codex runner), the selector, the lens planner and replanner
   (ideation); implementation, both constructions and the continuation
   (implementation); the judge (feedback); the maintainer's setup session
   (setup) and its change-request sessions (verification); deploy's
   selector and adapter, both agents of the fallback pair (deployment,
   through WP5's interface); the mining and update leads (learning,
   through WP3's). Not staged, and the plan says why: the difficulties
   fallback (an engine utility that reads a stream, not a domain
   session), the grading sessions (the engine judging lessons under its
   own rubric), `codify_run` and `behavior` (development tools), the
   repo-memory and CLI-inference utility roles, `ExperimentSession`'s
   workspace agent (unused by the generic run). Test
   `tests/test_harness_guidance.py`: for each staged module the rendered
   prompt contains `guardrails.md` and the module page whole and names
   the skills, delegates and servers the manifest lists; a 20-kilobyte
   page reaches the prompt in full; a module with no harness renders with
   no "Domain guidance" heading and the implementation prompt still ends
   with the closing line; the existing prompt tests stay green.
10. The setup session: the `setup.md` template, the orchestrator step with
    the inbox gate, the statement composition, the manifest verification,
    the checkpoint and status entries. Test `tests/test_harness_setup.py`
    (the agent stubbed to write the statement and create
    `prepared/market-data/MANIFEST.json`): the task file gains both and
    keeps the brief's rules byte for byte; the status payload names the
    resource; a stub that edits `kapso_evaluation/` makes the build fail
    naming the harness; with no setup page and no setup attachment no
    session runs; a resume after setup does not run it again.
11. The verification step: the `verification.md` template, the files, the
    worktree, `SearchNode.verification`, the judge keyword, the retry,
    the void and unverified paths, parent selection and delivery, the
    counter, the solution field and `explain()`. Test
    `tests/test_harness_verification.py` (the agent stubbed to write each
    verdict): `void` clears the score, excludes the node from parent
    selection and delivery, increments `rejected_candidates` and reaches
    the judge; a judge saying valid does not resurrect a void; `valid`
    passes the summary to the judge and lands in the solution record; a
    malformed verdict raises; no verdict is retried once, then recorded
    `unverified`, kept as a parent and never delivered.
12. Deploy and learn: `deploy()` and `learn()` resolve the harness from
    the object or the record with the refusals above, print both
    identities when they differ, stage the deployment and learning
    modules; `kapso deploy --harness`; the two `trajectory.yaml` keys.
    Test: `tests/test_solution_open.py` (the refusal cases),
    `tests/test_deployment_adapter.py` (the adapter prompt carries the
    deployment page on both agents of the pair), `tests/test_mining_frame.py`
    (the lead prompt carries the learning page; the frame's own
    `.claude/agents` staging survives), `tests/test_trajectory_store.py`.
13. `cli/harness.py`: the six subcommands and the epilog line;
    `--harness` on `kapso build`. Test `tests/test_cli_harness.py` (the
    parser's own actions enumerated, as `test_cli_build.py` does; `new`
    writes the two files, prints the check line, and the result passes
    `check`; `check` exits 1 on a failure and 0 with warnings and prints
    the summary line; `list` prints the empty-store line and the two
    sections; `remove` refuses a path) and one row in
    `tests/test_cli_build.py`.
14. The trading example: `examples/trading/` (`generate.py` for synthetic
    bars with a weak momentum effect and a cost model; `evaluation/evaluate.py`
    printing the risk line then `sharpe: <value>`, writing
    `kapso_evaluation/result.json`, `results/equity_curve.csv` and
    `results/trades.csv` as the backtesting skill and the `require-results`
    hook expect, with `--fast`; `repo/strategy.py`, a baseline the
    evaluator measures with headroom the generator is tuned for;
    `kapso-brief.md` with `Harness ../harnesses/trading`; `run.py` under
    twelve lines; the four-section README whose "Run it" begins with `cd
    examples/trading` and whose recorded result carries its provenance),
    the trading harness's two file hooks reading both tool-input shapes,
    `python3` in its commands, the examples table. Test
    `tests/test_examples_trading.py`: the evaluator on the baseline prints
    the contract's last line and writes the three files; the fast mode is
    marked; the brief parses with the harness line.
15. Docs: `docs/harnesses/{index,use,write,example-trading}.mdx`,
    `docs/reference/harness.mdx` (manifest, pages, skills, delegates,
    `mcp.json`, hooks with the host table above, `check`), the
    `load_harness`, `kapso harness` and `--harness` entries in the API,
    CLI and brief-format references, `docs.json` with the Harnesses
    group, the three sentences of the design document; `scripts/check_snippets.py`
    covers the new pages; `mint validate` and `mint broken-links` green.

## Tests

- Syntactic: the files above, in the curated gate, with the CI invocation
  unchanged. Negative cases: every `check` rule; the resume refusal per
  form; the mid-campaign change; the malformed verdict; the secret
  literal; a hook with an unknown event; a reference of no form; the
  tracked-path collision. Goldens: the staged trees and the merged hooks
  file for the trading harness per host. Contract: the verdict schema,
  the record fields, the task statement's composition, the guidance
  block's shape (pages whole, never clipped). The records test runs the
  real writers; only sessions are stubbed.
- Proof run, on the fresh machine, from the wheel: the trading example on
  two machines in parallel (`kapso-fresh-wp2-claude`, `kapso-fresh-wp2-codex`),
  `cd examples/trading && kapso build --brief kapso-brief.md --evaluation
  evaluation --data data --repo repo --output campaign --budget-minutes 75
  --budget-experiments 2`, the second machine with `--coding-agent codex`.
  The exercised sessions per machine: setup, ideation, the lens planner
  and the judge on Claude Code on both (the engine constructs them so);
  implementation and verification on Claude Code on the first and on
  Codex on the second. The archived campaign must show: the identity in
  `launch.json`, `status.json`, `run_state.json` and `solution.json` with
  one hash; `kapso_task.md` with the domain statement and `market-data`
  under prepared resources, `prepared/market-data/MANIFEST.json` present;
  a `harness.json` and a `stream.jsonl` per staged session with the staged
  lists matching the manifest; in the streams, the `session-brief` context
  line and at least one `scan-writes` or `require-results` decision (the
  canary that hooks fired under the fresh machine's Codex user config); a
  `verdict.json` per attempt with at least one `valid` or `void`, not
  `unverified`; a delegate invocation in at least one verification or
  feedback session; `Solution.open` in a second process reading the record
  with `solution.harness` and `solution.verification` filled; `kapso
  harness check ../harnesses/trading` quiet on the machine before the
  build; the guidance block's bytes per module beside the run. The two
  machines must satisfy the same invariants; a difference in them is a
  finding.
- Semantic hook: S3's guideline-completeness test becomes runnable: a
  model author (Codex gpt-6-astra at xhigh, and Claude opus-5) with only
  the authoring guide, the design and the trading example writes a
  `pipeline-dbt` harness in a scratch directory; every guess it logs is a
  sentence missing from the guide; the result must pass `check`. Record
  the two guess counts and the check output in this plan.

## Acceptance

- `kapso harness new x` prints the path, and `kapso harness check ./x`
  prints `check ok (0 skills, 0 agents, 0 servers, 0 hooks)`; `check
  examples/harnesses/trading` reports zero failures and zero warnings.
- The proof-run command on both fresh machines stages every module of the
  trading harness, and each archived campaign shows every item of the
  proof-run list.
- A resume after editing one page is refused by name with both hashes and
  the form's way out; a build whose harness names an unset variable in a
  server mounted on implementation is refused before any session, naming
  the variable and `.env` (a test fixture; the trading broker is
  paper-only and names no credential).
- `solution.harness`, the launch record, the status payload, the
  checkpoint and `trajectory.yaml` carry one and the same identity.
- A build with no harness behaves as at `b49d3827`: no new session, no
  staged file, no "Domain guidance" heading, `solution.harness` `None`;
  the gate's count grows and nothing that passed stops passing.
- The host-fact table above is confirmed by the proof run on the fresh
  machine, including the one row it left open (Codex hooks under a
  minimal user config).
- Both reviewers' findings on this plan and on the pull request are
  answered below; the gate is green; the docs checks are green.

## Built

Branch `wp2-harness` off `redesign` at `aa62fdfe`, fourteen commits, each
with its tests and the gate green at every one; at `42729205` the gate is
1,469 passed, 27 skipped, 2 deselected, the docs coverage check covers 38
commands and methods, the snippet check 6 quoted files, `mint validate`
and `mint broken-links` pass.

| Commit | What landed |
|---|---|
| `a1ee342c` | the manifest, read with its line numbers, and the content hash |
| `b2b30df6` | `check`, with every rule, warning and prerequisite row |
| `98bfdb1b` | the reference grammar and the store |
| `a775d5e4` | the handle, `load_harness`, and the config block |
| `bc75db09` | one identity in every record; prerequisites scoped per verb |
| `0110f920` | staging a module into a session, per host |
| `eb1cf618` | the task statement, and the guidance staged into every session |
| `4e5c8c63` | the harness setup session |
| `348f2bf6` | verification per attempt, and the verbs on a finished build (changes 11 and 12) |
| `2fce1275` | a staging without a session directory is refused (a test had staged into the runner's cwd) |
| `27c7e70a` | `kapso harness new`, `check`, `add`, `update`, `remove` and `list` |
| `4e96c263` | the trading example, a task on the trading harness; `python3` in the harness's commands |
| `4a931ea9` | the Harnesses pages and the harness reference |
| `42729205` | requirements are checked against `python3` on PATH (DECISIONS, 2026-10-25) |

The guidance block per module for the trading harness, measured by
staging each module on Claude Code (`guardrails.md`, the module's page,
the paths):

| Module | Guidance | Skills | Servers | Delegates | Hooks |
|---|---|---|---|---|---|
| setup | 2,322 B | 1 | 1 | 0 | 3 |
| ideation | 2,799 B | 2 | 0 | 0 | 3 |
| implementation | 3,854 B | 4 | 1 | 1 | 6 |
| verification | 3,444 B | 2 | 0 | 1 | 3 |
| feedback | 2,642 B | 1 | 0 | 1 | 3 |
| learning | 1,619 B | 0 | 0 | 0 | 0 |
| deployment | 2,638 B | 2 | 2 | 0 | 4 |

Under four kilobytes on the heaviest module: two whole pages cost less
than one tool result, and the size rule in the guide holds for the example.

Two decisions taken while building are in `DECISIONS.md` under
2026-10-25: the requirements check moved from the engine's interpreter to
`python3` on PATH (a `uv tool` install has no `pip` in the engine's venv,
and the harness's servers and hooks never run there), and a staging that
names no directory raises instead of writing into the working directory.

Two more fixes came out of the first proof launches, before any
session ran to the end: Claude Code's `--session-id` must be a UUID, and
the setup session had passed its name (`harness_setup`) as the inbox id
that doubles as it, so both machines' first builds died in the setup
session with `Invalid session ID. Must be a valid UUID.`; the id is now
minted as a UUID and the setup session's requests are found by their node
id. And `--detach` printed Python's `ResourceWarning: subprocess N is
still running` after a successful launch, the `Popen` object being let go
while its child runs; the launch now drops it under a warnings filter.

The trading example's data was tuned to a trend weight of 0.35: the
shipped 20/100 cross scores 0.1384 out of sample (the brief's baseline,
pinned by `tests/test_examples_trading.py` on every machine), a 10/50
cross about 0.92, a 20-day momentum sign about 2.8, a volatility-targeted
momentum about 2.2, buy-and-hold negative; the target of 1.0 is
reachable and the baseline is not already there.

## Proof runs

**Rehearsal on the development box, 2026-10-25 11:12 UTC**, the trading
example with the worktree's code, fifteen minutes and one experiment, on
Claude Code (`claude-opus-5`), the shared token and the inbox on. The
setup session ran four minutes, built `prepared/market-data` through the
server's `snapshot` tool (its first attempt reached the data through the
original directory the statement named, fixed in `346c48f0`) and wrote a
domain statement that even flagged the brief's budget line against the
campaign's; the task statement carried it. The implementer, staged with
the harness, scored a volatility-targeted momentum signal at a Sharpe of
2.2095 with `results/equity_curve.csv` and `results/trades.csv` saved; the
six hooks' `SessionStart` lines are in its stream. Then the budget was
spent: the verification session got the 102-second clamp twice, spawned
the `lookahead-auditor` delegate on Claude Code (the `SubagentStart`
events are in its stream) and was killed before writing a verdict, so the
attempt was `unverified`; the judge got the 60-second floor, was killed
after six tool calls, and its retry answered that no attempt was in
scope and marked the evaluation invalid, so the record delivered nothing
(`Candidate: none succeeded`, one rejected, $4.04). The verifier's diff
had carried the engine's `.kapso/repo_memory.json` and a thousand CSV
lines beside the strategy change, fixed in `f7a80ee1`. Every harness
path ran; what failed was the budget's end, which is WP4's finding
below.

**Two fresh machines, 2026-10-25**, `kapso-fresh-wp2-claude` and
`kapso-fresh-wp2-codex` (`e2-standard-4`, Ubuntu 24.04, the wheel as a
`uv` tool, Claude on the shared token, Codex on the API key), the trading
example copied over with its data generated on the machine, the harness's
and the example's requirements on the system `python3`
(`pip install --break-system-packages`), `kapso harness check
../harnesses/trading` printing `check ok (7 skills, 2 agents, 2 servers, 6
hooks)` and `kapso doctor build` passing on both. The first launches
(wheel from `42729205`) died in the setup session on both machines within
a minute: Claude Code's `--session-id` wants a UUID (the fix in
`d603e892`); `kapso watch` showed the campaign `RUNNING ⚠ DEAD` with the
traceback in the log only (a finding below). Both were relaunched at
11:12 UTC on the wheel from `d603e892`, seventy-five minutes and two
experiments. Archives under `scripts/redesign/runs/<id>/` (gitignored);
`proof_check.py` in the session scratchpad reads them.

| | `wp2-claude` | `wp2-codex`, `--coding-agent codex` |
|---|---|---|
| setup session | 364 s, $1.84, `prepared/market-data` with `MANIFEST.json`, the domain statement in `kapso_task.md` (10.8 KB) | 287 s, $1.39, the same; one hook denial in its stream |
| implementation | 11:24:51 to 11:32:22, scored at 11:27:49 on its first evaluation run | one run, the auditor asked |
| verification | 16 min with the `lookahead-auditor` delegate (122 mentions in the stream); `valid`, two `shift(-1)` findings in a recon script, explained | `valid`, three findings of the same kind, explained |
| result | 11:59, 45.4 min, **1.9336**, `goal_achieved`, one experiment, $13.04 | 11:54, 40.3 min, **1.9944**, `goal_achieved`, one experiment, $12.96 |
| records | one identity in `launch.json`, `status.json`, `run_state.json`, `solution.json`; `status.phases` with `harness_setup` and `verification`; the checkpoint's `harness_setup` done | the same |
| sessions | `harness_setup`, `ideation/iter1/claude_code`, `generic_exp_0`, `verification/generic_exp_0`, `feedback/generic_exp_0`, each with `harness.json` and `stream.jsonl`; the `SessionStart` hook's response in every stream, its context line in the implementation and verification sessions, the `Agent` tool with the harness's delegates in implementation, verification and feedback | the same |
| second process | `Solution.open` read the record with `harness` and `verification` filled | the same |

Every item of the proof-run list holds on both, with one exception that
is a finding: the second machine's sessions all ran on Claude Code.
`--coding-agent codex` does not route the implementation session in the
`GENERIC` mode, which reads `implementation_cli` from the strategy's
parameters (default `claude_code`), so the Codex rows of the host table
were not exercised by that run. A third campaign on the same machine, on
the wheel from `f0a81497` with a config copy that sets
`implementation_cli: codex` (forty-five minutes, one experiment), runs
implementation and, since the review moved it to the attempt's host,
verification on Codex; its outcome is recorded below as it lands.

CODEX_PROOF_RESULT

What the judge noticed on the second machine and the engine did not: the
implementer wrote a new file, `kapso_evaluation/eval_profile.md`, under the
protected directory, and the integrity check, which rejects a modified
evaluator, let a new file pass. A finding below.

## Author test (S3)

Run 2026-10-25 on the development box: two model authors, each with the
authoring guide, the design document and the trading example and nothing
else, asked to write a `pipeline-dbt` harness in a scratch directory and
to log every guess as one line of `GUESSES.md`. Neither ran `kapso`.

| Author | Files | `kapso harness check` | Guesses |
|---|---|---|---|
| Codex `gpt-6-astra`, xhigh | 22 (8 pages, 4 skills, 1 delegate, 1 server, 2 hooks) | `check ok (4 skills, 1 agents, 1 servers, 2 hooks)`, one need (`dbt (command)`), no warning | 66 |
| Claude Code `claude-opus-5` | 39 (8 pages, 7 skills, 2 delegates, 2 servers, 7 hooks) | `check ok (7 skills, 2 agents, 2 servers, 7 hooks)`, seven needs (six `${VAR}` references of its servers, `dbt (command)`), no warning | 65 |

Both pass `check` with no warning on the first try, so the guide's
conventions carry: the front matter, the quoting, the reference
resolution, the manifest's shape, the hooks' shape. The guesses are the
sentences the guide lacks, and the two lists overlap heavily: the seven
module keys and that an omitted module or list means empty; `version`
required and free-form; the page-size threshold (40 lines) and that the
task statement, the diff and the evaluation output reach a session by
paths the engine supplies; that a prepared resource is a directory left
under `prepared/<name>/` with no registration and that `results/` names
are the author's; the hook event list, each event's decision JSON (the
`Stop` shape differs), `stop_hook_active`, the input fields per tool and
that silence is exit 0 with nothing on stdout; a minimal FastMCP server;
`python3` in the guide's own snippets (it still says `python` in places);
that check runs no script and reads no path quoted in a `SKILL.md`; that
a missing command is a need, never a failure; and one contradiction, the
feedback page's example of a margin-based stop rule beside the rule that
a harness holds no stop rule. The guide was revised the same day with
those sentences (the manifest's keys and defaults, the paths the engine
supplies, the prepared-resource and `results/` conventions, the verdict
file, the hook events and each shape's decision JSON, a minimal FastMCP
server, the streamable-http form, `python3`, what `check` does not do, the
feedback example without its stop rule); the published `write` page
carries the sentences a user needs. The two `GUESSES.md` files and both
harnesses are kept with the run records (`scripts/redesign/runs/wp2-s3/`).

## Findings for later packages

- **A build without `OPENAI_API_KEY` crashes at the orchestrator's
  construction** (WP4, WP6). `OrchestratorAgent.__init__` calls
  `_create_knowledge_search`, whose `kg_graph_search` backend builds an
  OpenAI embedder at construction, with the knowledge graph disabled and
  after the preflight passed with one advisory; `kapso doctor build` does
  not list the variable. Seen on the development box when the local smoke
  ran without it; the fresh machines carry the key, so the proof runs did
  not. The embedder belongs behind the knowledge-graph switch, or the
  preflight names the variable. Pre-existing, not a harness path.
- **A crashed detached build leaves `status.json` in its last state**
  (WP6). Both machines' first builds died in the setup session; `kapso
  watch` showed `RUNNING ♥ 25s ago ⚠ DEAD (pid gone)` with the phase
  `harness_setup`, and the error was only in `campaign.log`. The entry
  point should write `state: failed` with the error on an unhandled
  exception, as it does for a failure it catches.
- **The host's session id is minted by the callers** (WP6). The inbox id
  doubles as Claude Code's `--session-id`, which must be a UUID, and is
  minted in two places (`implementation.py` and the orchestrator's setup
  session). The adapter could mint it and hand it to the inbox gate, so a
  new session kind cannot repeat this package's mistake.
- **The traceback as the user's error message** (WP6, WP7). A
  `HarnessError` or `BriefError` prints a full traceback in the terminal
  and the detached log. An excepthook that prints the message alone for
  the engine's own error classes, keeping the traceback in the log, is the
  fix; the harness messages were written to be read on their own.
- **Learning attachments** (WP3). Only the learning module's pages reach
  the crews (`pages_block`); its skills, servers and hooks are not staged,
  because the crews' sessions are WP3's to shape.
- **A spent budget starves the sessions that finish an attempt** (WP4).
  In the rehearsal the setup, ideation and implementation sessions used
  the fifteen minutes, and the verification and judge sessions that
  followed were clamped to the floor and killed: the attempt was
  `unverified`, and the judge's retry after its kill answered with no
  attempt in scope and marked a 2.21 evaluation invalid. Finalisation
  needs reserved time, as `reserve_minutes` reserves it for the final
  checkout, or the campaign must stop before an implementation it cannot
  finish; the judge's retry after a deadline kill should carry the
  original prompt or fail loud rather than answer (WP6).
- **The Codex adapter leaves a file unclosed** (WP6): `codex_agent.py:264`
  prints `ResourceWarning: unclosed file` in the campaign log after an
  ensemble member's session; pre-existing.
- **`--coding-agent` does not route the implementation session** (WP4).
  The `GENERIC` strategy reads `implementation_cli` from its parameters
  and the flag reaches another field; the second proof machine ran every
  session on Claude Code under `--coding-agent codex`. The config without
  modes must make the one knob the flag sets the one the strategy reads,
  and the CLI reference must say what the flag does until then.
- **A new file under `kapso_evaluation/` passes the integrity check**
  (WP6, evaluation governance). The second machine's implementer wrote
  `kapso_evaluation/eval_profile.md`; the check rejects a modified
  evaluator and let the addition through, and only the judge noticed. The
  protected directory should be protected as a tree.
- **`strict_mcp_config` and the `.claude_mcp` cleanup race**, pre-existing,
  noted in change 9 and left alone.

## Risks

| Risk | What is done |
|---|---|
| Codex hooks do not fire under the fresh machine's minimal user config | the proof's canary (a hook decision in the stream); if they do not, the staging writes the one user-level key the probe finds necessary and the plan records it |
| the judge resurrects a void, or an unverified attempt is delivered | closed by design: `verification` is its own node state, ANDed after the judge, read by parent selection and delivery; tested in change 11 |
| the setup session breaks the evaluation boundary | the manifests pinned at construction are verified after the session; a change fails loud naming the harness |
| the staging misses a construction site | Changes 9 enumerates every `CodingAgentConfig(` and `build_config(` site and says staged or not and why; the guidance test renders every staged module |
| a staged file reaches a candidate branch, or overwrites the repository's own | the ignore lines (no trailing slashes) are committed before the first clone; tracked collisions are refused by name; tested in changes 7 and 8 |
| a hook fails open because its interpreter is absent | `check` reports a command word not on PATH as missing; the example and the guide say `python3`; the proof's canary |
| a path harness edited mid-campaign, or `harness update` under a live run | re-hashed at every staging call; a change fails loud with both hashes |
| prompt growth from two whole pages per session | measured per module in change 7's test and recorded beside the proof run; the guide's size rule and `page_warning_lines` |
| a verification session clamped to the floor near the budget's end | `verification_minutes` is clamped like every session; the proof requires one real verdict; the budget finding stays WP4's |
| ideation on the shipped config leaves no time for setup and verification in the proof | 75 minutes and two experiments |
| the Claude weekly token window | the gate before the proof, as for WP1; the second machine runs implementation on the API key |
| scope: XL as a whole | changes 1 to 11 are a complete build path and ship first; 12 and 13's store commands follow; export is WP7's |

## Review

Both reviewers read the plan of commit `9287b8c4` with the design
documents and the code. Every finding and its answer; "folded" means the
plan above now says so.

### Codex (gpt-6-astra, xhigh)

| Finding | Answer |
|---|---|
| Q1.1 a missing verdict should not make an attempt deliverable | folded: `unverified` (retried once) keeps its score and parent eligibility, is never delivered while the harness has verification |
| Q1.2 module isolation: ownership, cleanup and collisions of staged files; ambient servers | folded for the harness's own files (idempotent, per-host names, tracked-path refusal); the user's own Claude servers in campaigns are a pre-existing behaviour listed for WP6 |
| Q1.3 delegate inheritance is assumed | folded: the delegate prompt begins with the module's guidance block |
| Q1.4 setup and verification conditional | kept, with the rule stated (page or attachment) and the engine's integrity check always running; a harness that writes verification rules only in `guardrails.md` is a guide sentence, added in change 15 |
| Q1.5 requirements checked, not prepared; specify the interpreter | kept (DECISIONS); the interpreter and the check are specified under `check` |
| Q1.6 export loses the dependency closure | folded by moving export to WP7 with that reason |
| Q1.7 status stores a string, not the identity | folded: the structured key |
| Q1.8 build and learning provenance conflated | folded: `harness` and `learning_harness` |
| Q1.9 the inbox path for inputs missing at setup | folded: setup mounts the inbox gate |
| Q1.10 `check` narrows the hook format; the credential heuristic | folded: the one shape is published; the length heuristic is a warning |
| Q1.11 `version` required and `modules` as a dataclass | folded: both kept and recorded as amendments to the design's sections 1 and 8 |
| Q1.12 `list` and refusal output underspecified | folded: the onboarding's columns and the summary line; the fix line per missing row |
| Q1.13 surfaces moved to later packages | folded: the master's WP2 row is corrected for `learn --harness` and export; the user flow's steps that wait are named in the docs slice |
| Q2.1 verification at the wrong level | folded: inside `_finalize_nodes` |
| Q2.2 the integrity path cannot carry the verdict; `evaluation_valid` is overwritten | folded: `SearchNode.verification`, ANDed after the judge, read by selection and delivery; `base.py` in Ownership |
| Q2.3 more than eight session seams | folded: Changes 9 enumerates every site, staged or excluded with the reason |
| Q2.4 implementation constructs two agents | folded: staged after checkout, before the executing agent |
| Q2.5 the staging signature lacks context | folded: campaign directory and session id are arguments |
| Q2.6 shared directories race | folded: idempotent, atomic per-host files; the `.claude_mcp` cleanup race is pre-existing and listed |
| Q2.7 HTTP entries are not verbatim on Codex | folded: translated per host with the config's timeout; headers through the key strict-config accepts, else refused by `check` for that host |
| Q2.8 `--agents` with a filename contradicts the probe | folded: the JSON string |
| Q2.9 feedback inspects the campaign root, not the candidate | the judge keeps its inputs (diff and evaluation output are already passed to it); the risk reviewer reads `results/` through the diff and the named evaluation output, which the evaluator now writes; moving the judge into a worktree is WP6's or WP4's |
| Q2.10 the symlink breaks `protect_prepared.py` | folded: the hook resolves both paths; tested through the real link |
| Q2.11 evidence not durably captured | folded: a stream artifact for every staged session; rendering stays WP6's |
| Q2.12 deploy copies the tree; mining removes `.claude/` | folded: `prepared/` is already in deploy's copy (the symlink step is skipped at the root of a copy); the mining frame's own staging is tested to survive |
| Q2.13 no deployment record for "allowed and recorded" | folded: printed; the record is WP5's |
| Q2.14 doctor and config plumbing | folded: the doctor flag is dropped; `load_harness_defaults` |
| Q2.15 the proof's coverage claims | folded: the exercised-session matrix per machine; the refusal moved to a fixture |
| Q3.1 `check x` is the bundled form | folded: `new` prints `check ./x` |
| Q3.2 mixed working directories | folded: `cd examples/trading` first |
| Q3.3 `missing` cached at load | folded: re-checked at every verb call |
| Q3.4 the resume remedy may be impossible | folded: the way out per form |
| Q3.5 detach reports success before validation | folded: validated before the fork |
| Q3.6 setup's editable output | folded: the engine composes the file; setup writes its own statement file |
| Q3.7 the author cannot see what fired | folded as far as WP2 goes: the stream per session and the grep in the docs; rendering is WP6's |
| Q3.8 deploy's null and changed-source cases | folded |
| Q4.1 prerequisite checks read the environment | stated: a presence probe by name, the preflight precedent; no value is read |
| Q4.2 the records test mocks what it claims | folded: the real writers |
| Q4.3 the import-layout test | deleted |
| Q4.4 malformed input and try/except | folded: unparseable files raise; `check` reports structure |
| Q4.5 the Codex role fallback | moot: roles verified; one mechanism |
| Q5.1 L not credible; first slice | folded: XL with the slice 1 to 11 |
| Q5.2 the hash does not freeze a run | folded: re-hash per staging |
| Q5.3 prepared resources writable through the link | the hook plus the manifest's hash in `MANIFEST.json`; read-only mounts are a host feature neither CLI offers for a symlink; recorded as a known limit in the docs |
| Q5.4 store identity and deletion | folded: host in the slug, `source.json`, `remove` names what it deletes |
| Q5.5 crash recovery for the new phases | folded: `harness_setup` in the checkpoint; verification per branch directory |
| Q5.6 the proof lacks contrasts; the evaluator's artifacts | folded: the evaluator writes the results files; the adversarial paths are unit-tested, the proof requires a real verdict and a hook decision |
| Q5.7 tracked paths defeat "never committed" | folded: refused by name |
| Q6 names | `HarnessEnvironment` (the Claude review's word, not `EnvironmentRequirements`), `Requirement` reused and `missing` everywhere, `stage_harness`, `page_warning_lines`, `unverified`, `load_harness` at the package level; `kapso_task.md` kept (the `kapso_` family) |

### Claude Code (opus-5)

| Finding | Answer |
|---|---|
| Q1.1 delegates lose the pages | folded |
| Q1.2 the refusal is harness-wide and replaces the inbox pause | folded: scoped by verb; setup has the inbox |
| Q1.3 `version` required | kept; the design's section 1 gains the word |
| Q1.4 the Codex fallback is weaker than the design's | moot: roles verified |
| Q1.5 `check` and `list` lose the onboarding's rendering | folded |
| Q1.7 `modules` shape | recorded as an amendment |
| Q2.1 no threading path; the fingerprint trap | folded: the Threading section |
| Q2.2 verification placement; the void overwritten | folded |
| Q2.3 eight sites is wrong | folded: enumerated |
| Q2.4 harness tools reach neither the allow-list nor the prompt | folded: `StagedHarness.allowed_tools` |
| Q2.5 server-name collisions and TOML safety | folded: two `check` failures |
| Q2.6 the ignore lines miss the symlink and tracked paths | folded |
| Q2.7 the config block is unreachable | folded: `load_harness_defaults` |
| Q2.8 the `BROKER_API_KEY` acceptance cannot be met by the example | folded: a fixture |
| Q2.9 shared directories and session ids | folded: idempotent staging; ids per site |
| Q2.10 ownership collisions with WP5 and WP6 | folded: interfaces asked, the doctor flag dropped |
| Q2.11 `handles.py` is not nothing | folded |
| Q2.12 the `setup` phase's meaning | folded: `harness_setup`, with a payload |
| Q2.13 resume plumbing and the epilog | folded |
| Q2.14 the bundled root will not ship | folded: `harness/bundled/` and the glob |
| Q2.15 hashed once, read per session | folded: re-hash per staging |
| Q2.16 setup can break the evaluation boundary | folded: the manifest check |
| Q3.1 the author's loop | the stream per session now, the grep in the docs; rendering is WP6's |
| Q3.2 the resume remedy | folded |
| Q3.3 `check`'s silence | folded: the summary line |
| Q3.4 the secret heuristic | folded: a warning |
| Q3.5 `check` on a git reference clones silently | folded: `fetched <path>` printed |
| Q3.6 a mistyped path becomes a clone attempt | folded: the grammar rule |
| Q3.7 `list` has no empty state | folded |
| Q3.8 an unsatisfiable refusal | folded: scoped by verb; no override flag |
| Q3.9 deploy and learn on another machine | folded |
| Q3.10 setup may rewrite the statement wholesale | folded: the engine composes |
| Q3.11 the budget clamp and `none` verdicts | folded: `verification_minutes`, `unverified`, the proof requires a real verdict |
| Q4.1 `check` forces a try/except | folded: unparseable files raise |
| Q4.2 `check` cannot see the config | folded: threaded |
| Q4.3 the layout test | deleted |
| Q4.4 rule 3 stated | stated |
| Q4.5 no guidance through `additional_context` | stated in Not in scope |
| Q5.2 hooks failing open on a missing interpreter | folded |
| Q5.3 prompt growth | folded: measured |
| Q5.4 `update` under a live run | folded: re-hash per staging |
| Q5.5 export unverified | moved to WP7 |
| Q5.6 the estimate | XL, with the slice |
| Q5.7 what to cut | the order of the Changes follows it, except verification, which stays in the first slice because the trading harness's promise is the verdict |
| Q6 names | `HarnessEnvironment`, `missing`, `harness/bundled/`, `stage_harness` and `StagedHarness`, `remove` for fetched clones only (and no `forget`: the recently-used list is dropped), `check_harness`, `HarnessReferenceError`, `harness_setup`; `kapso_task.md`, `prepared/`, `verdict.json` kept |

### The pull request: Codex (gpt-6-astra, xhigh), 2026-10-25

Run on `42729205` with `scripts/redesign/review.sh` (findings in the
session scratchpad, `review_wp2/codex.md`); answered in `6c3e4ffe`
(the P1s), `011e0361` and `f0a81497`.

| Finding | Answer |
|---|---|
| P1 a resume on the same object compared the pre-reload hash | fixed: the loaded handle is reloaded before the checkpoint comparison; test on the same object |
| P1 a void attempt could become the next parent | fixed: the committed-work fallback skips a void; `_select_parent()` tested |
| P1 a void attempt could be delivered when the judge raised or the evaluator bridge restored validity | fixed: the void is applied on the judge's except path and kept by the bridge; `is_deliverable` admits `None` or `valid` only. The except itself is pre-existing engine behaviour (a judge failure keeps the evaluation's score) and stays |
| P1 `Kapso.research()` raised AttributeError | fixed: the constructor's stranded line is back; a test constructs a real `Kapso()` |
| P2 concurrent staging not atomic | fixed: staging is serialised with a lock, temporary names are unique |
| P2 staging accumulates across modules | fixed: a module's staging leaves exactly its skills, hooks and delegates in a shared directory; tested across setup, feedback and learning |
| P2 `.gitignore` substring match | fixed: whole lines; tested with a comment and a `.claude/settings.local.json` seed |
| P2 a tracked `kapso_task.md` overwritten | fixed: refused before the write |
| P2 the maintainer's setup session can change pinned data | fixed: `kapso_datasets/` is pinned across it too |
| P2 setup and verification exceed the budget | fixed: the setup clamp reads a budget view; the verification clamp is taken per attempt and no retry runs under the budget's deadline |
| P2 a setup request does not pause before the maintainer | fixed: the maintainer's setup waits while the question stands |
| P2 a `.env` fix after loading reaches `check` but not the sessions | fixed: `.env` is read again after the prerequisite check passes |
| P2 the `Bearer ${TOKEN}` example fails on Codex, `check` silent | fixed: a reference inside a longer value is a failure; the docs and the guide show a whole-value reference |
| P2 Codex loses env renaming | fixed: an `env` entry must name the variable it forwards, a `check` failure otherwise; documented |
| P2 raw Codex ideation sessions lack `KAPSO_HARNESS_ROOT` | fixed: the runner takes the staged environment |
| P2 null required fields pass `check` | fixed: an empty value is a finding; no manifest without a finding is a failure |
| P2 a malformed server env crashes `check` | fixed and tested |
| P2 markers read in the engine's interpreter | fixed: `python3` reports its own marker environment |
| P2 `source.json` inside the clone changes a root harness's hash | fixed: the record sits beside the clone |
| P2 two revisions share a cached checkout | fixed: a second reference naming the same directory is refused by name |
| P2 later judgments write the first attempt's stream | fixed: the judge's staging is merged onto its own settings at every judgment |
| P2 ideation sessions keep their own stream path | the ideation artifacts stay where the selector reads them; the session record now names the stream it writes (`stream`), and the docs say where an ideation stream lives |
| P2 deploy and learn reject recorded git shorthand | fixed: a git form of any kind counts as reachable; tested |
| P2 a loaded harness attached to a generic campaign | fixed: refused |
| P2 learning attachments never staged | as recorded in Findings: WP3 shapes the crews' sessions; the pages reach them today |
| P2 learning by path loses provenance | fixed: a campaign directory with a record resolves its harness as a Solution does |
| P2 a changed version at the recorded source is silent | fixed: both identities are printed on that branch too |
| P2 a detached resume skips the prerequisite check | fixed: the launch record's harness is loaded and checked before the fork; tested |
| P2 `harness update` skips the check | fixed |
| P2 the adapter swallows staging refusals | fixed: a `HarnessError` propagates; tested |
| P2 the protect hook misses `*** Move to:` | fixed in both file hooks |
| P2 prepared resources documented as read-only | fixed: the docs say the file-tool hook denies a write and a shell is not covered |
| P2 the acceptance evidence missing; `--coding-agent codex` does not put verification on Codex | the proof runs above; verification now runs on the implementation CLI, and the flag's routing is a WP4 finding |
| P3 the task statement's budget shows `the config's` | fixed: the resolved values, `none` where no limit |
| P3 `VERIFICATION_ATTEMPTS` literal | fixed: `harness.verification_attempts` in the config |
| P3 function-local imports in tests | fixed |
| P3 documented exception types | fixed: the reference names the parser's error and `RunCheckpointIncompatibleError` |

### The pull request: Claude Code (opus-5), 2026-10-25

Run on the same brief, reading at `6c3e4ffe` (`review_wp2/claude.md`);
three of its heaviest findings were the Codex P1s already fixed.

| Finding | Answer |
|---|---|
| High `.gitignore` substring match lets staged files into candidate commits | fixed, as above |
| High a failed verification session is indistinguishable from silence; the retry reuses an expired clamp | fixed: the session's error reaches the verdict's summary, the clamp is taken per attempt, and no retry runs when the budget set the deadline; tested |
| Medium-high an empty `name`, `version` or `description` passes `check` | fixed, as above |
| Medium staged skills accumulate across modules | fixed, as above |
| Medium the judge's staging merged once | fixed, as above |
| Medium ideation sessions keep their own stream path | the record names it; the docs say so |
| Medium an unmapped coding agent dies inside the first staging; the adapter's fallback cannot run under a harness | fixed: an explicit `--coding-agent` with no staging is refused at the call; the adapter lets the refusal through instead of trying the fallback |
| Medium Codex ideation sessions lack the environment | fixed, as above |
| Medium a setup request does not pause before the maintainer | fixed, as above |
| Medium-low `update` and `remove` take no name | by design: a fetched harness is named by its reference, which `list` prints; the plan's CLI section now says `<ref>` |
| Medium-low deploy and learn print both identities only when loaded | fixed, as above |
| Low the launch print claims an override that did not happen | fixed: the brief's line is compared as a resolved directory or the reference as written |
| Low `kapso harness list` raises on an unparsable manifest in the store | fixed: a harness with findings lists by its directory, `check` says what is wrong |
| Medium-low the `needs` sample output and the launch print in the docs | fixed to what the code prints |
| Low "read-only" in the docs and the setup prompt | fixed: pinned by the hooks, not read-only |
| Low `rejected_candidates` in the API reference; "forty" files | fixed |
| Low the guidance block's attachment sections undocumented | fixed in the reference and the use page |
| Rule 1 `VERIFICATION_ATTEMPTS` | fixed, in the config |
| Low the hash ignores file mode | kept: a hook or script runs through `python3 <path>`, so the mode changes nothing the engine runs; paths and bytes stay the identity |
| Question: two `default_tools_approval_mode` overrides for a streamable-http server on Codex | fixed: the key is written once, the harness's mode when it has one |
| Tests: the fallback agent under a harness, the unmapped host on a build, a failing verification session, the support stub's copy of `stage_harness_for`, two dead assertions | the first three tested; the stub calls the engine's own method; both assertions rewritten |
