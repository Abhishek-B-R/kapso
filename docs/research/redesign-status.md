# Kapso redesign: what is settled, what is still a decision, what is unbuilt

2026-10-24. The checklist for the integration. The documents it points at:
`kapso-redesign.md` (positioning), `kapso-interfaces.md` (verbs, draft 1),
`harness-design.md`, `harness-authoring-guide.md`, `harness-user-flow.md`,
`onboarding.md`, `harness-ports.md`, and the plugin documents under
`docs/plans/`.

## 1. Settled

- Positioning: the one-liner, TL;DR draft 2, the tags, the word rules.
- Three nouns (engine, harness, experience), three verbs (`build`, `deploy`,
  `learn`), two loaders (`load_harness`, `load_experience`); the Python
  three-step: construct with engine knobs, load, call the verbs.
- The entrance proposes and never gates; the brief carries the goal, the
  evaluation protocol, the rules, the budget, and now the harness and the
  experience lines.
- The harness interface: a directory per domain with `harness.yaml` (four
  lists per module), pages by filename with `guardrails.md`, skills,
  delegates, servers, hooks defined once and listed where they apply; no
  engine-facing fields; the harness and the engine config never share a
  key. The authoring guide, the user flow, the onboarding grammar, the
  trading example (tested), the port plan for the four benchmarks.
- The experience reference grammar: `mine`, `leeroopedia`, a bank path, a
  bank git reference, an ingested index name; loading never ingests; no
  `team` source.
- Hooks in the host's format, routing between modules by the engine,
  inside a session by the model; no runtime router.
- The plugin's packaging and commands (2026-10-12), `--detach`, the inbox.

## 2. Decided 2026-10-24

| Decision | Choice |
|---|---|
| scope of a bank loaded by reference | scope applies to `mine` only; a bank loaded by reference serves what it holds; `scope="all"` lifts it on `mine` |
| `Brief` as an API object or a CLI-only file | a `Brief` dataclass with the brief's fields and a read and write method, accepted by `build()` beside a plain string; `kapso-brief.md` is its serialisation |
| the config without modes | one override file per project (`kapso-config.yaml`), layered over the packaged defaults; named modes retire; MINIMAL is a config that turns knowledge and the ensemble off; benchmark configs become override files; `kapso doctor` prints the effective config |
| bundled deploy targets as skills | yes: the five bundled targets are rewritten as skills shipped with the package, deterministic parts kept as scripts inside them, after the deploy argument lands |
| where shipped harnesses live | bundled harnesses under `src/kapso/harnesses/<name>/` so they ship in the wheel; `examples/harnesses/` keeps samples that exist to be read |
| what `kapso trace` renders | text first: the tree with each attempt's verdict and evidence, the evaluation version, what was consulted, hook decisions, delegate reports, spend; then `--json`; a static page belongs to the live-UI layer |
| the final TL;DR, README section, PyPI summary | one more pass once `build` and `load_harness` exist; the one-liner and the tags are usable now |
| `kapso-interfaces.md` | rewritten against the code after build steps 1 to 3, as the record of what shipped |

## 3. To build, in order

1. **`build`**: `Brief`, `Budget`, `Solution` with `open()`; `evolve` renamed
   in the facade, the CLI, the skill and the docs.
2. **The harness package**: reference resolution and the store under
   `~/.kapso/harnesses/`; `check`; the content hash in the launch record,
   the status file and the checkpoint (a resume refuses a changed hash by
   name); staging per module: pages appended under "Domain guidance",
   skills into the workspace, servers mounted beside the gates, delegates
   as sub-agents or own sessions, hooks merged in manifest order with
   `${PLUGIN_ROOT}` expanded; prepared resources under `prepared/<name>`;
   prerequisite refusal with names; `kapso harness new | check | list | add
   | update | remove | export`; `--harness` on `build`, `deploy`, `learn`.
3. **Experience**: `load_experience` by the grammar; `add_experience` for
   the ingesting forms; `kapso experience add | list | share` replacing
   `kapso bank create | connect`, `learn init-bank`, `learn_knowledge`,
   `research`, `index_kg`; the managed homes `~/.kapso/experience/banks/`
   and `indexes/`; the provenance intro; the scope rule; `serving.enabled`
   removed; the run record extended with sources and pinned heads.
4. **The config**: modes retired; `design_axes` deleted, the planner reads
   the ideation page and the goal; `additional_context` and the handlers'
   prose replaced by pages; `implementation_web` a hook; benchmark configs
   become override files.
5. **Deploy**: the `target` argument with the config's `deployment` default;
   the bundled strategies in the skill shape if decided.
6. **Observability**: `kapso trace`; `doctor --json`; the watch registry's
   liveness filter; the harness in the status header; hook decisions,
   delegate reports and verification evidence in the record.
7. **The plugin** (the layer specified in `docs/plans/kapso-plugin-user-flow.md`
   and the mental model's seams): the `plugin/` tree with the three
   manifests, `.mcp.json` and the self-bootstrapping `kapso-mcp` launcher,
   the four skills of `docs/plans/kapso-plugin-skills.md` (`kapso-setup`,
   `kapso-brief`, `kapso-harness`, `kapso`) with their Codex sidecars, the
   repository-as-marketplace files for Claude Code and Codex; the commands `setup`, `build`, `watch`,
   `inbox`, `resume`, `learn`, `deploy`, `doctor`, plus `harness`,
   `experience` and `--harness` on `build` (`/kapso:build` reads the
   harness's setup page when it writes the brief and writes the harness
   and experience lines into it); the open seams: session-start brief
   (S5), delegation tools (S6), learning from host sessions (S7), the skill
   lab re-run; last, the authoring plugin `/kapso:harness new`, which needs
   `check`. Waits for step 1 (the verb names), steps 2 and 3 (the CLI
   families it wraps) and step 6 (`doctor --json`, the liveness filter).
   The tree and the launcher depend on nothing, but are built with the
   commands after step 1 so no command is written twice.
8. **The ports and the banks** (parked): the four benchmarks into
   `predictive-modelling` and `competitive-programming`, RelBench first;
   their knowledge onboarded per `harness-ports.md`.
9. **Later**: the harness editor loop as a learning-module job; the public
   docs pages when the interface ships.

Dependencies: 1 before everything, since every record is a `Solution`; 2
before 3, since experience scope follows the loaded harness; 4 with 2 and
3, since the knobs leave the config as the pages and loaders arrive.
