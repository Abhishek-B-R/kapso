# WP3: experience

2026-10-25. Branch `wp3-experience` off `redesign` at `2e38996b` (WP2
merged). Size M as the master estimates; sixteen changes below, three of
them added after the review.

## Scope

Experience is what a campaign is served that was measured before: the
lessons in a bank (yours, or one you read), Leeroopedia's hosted pages, a
corpus ingested earlier. This package gives it one reference grammar, one
loader (`load_experience`, `--experience`, the brief's `Experience` line),
one `add` for what must exist before it can be loaded, a serving layer
driven by what is loaded and nothing else (`serving.enabled` goes), the
scope rule tied to the harness, a provenance intro the sessions read, and
the sources with their pinned heads in every record. The verbs and knobs
it replaces go: `kapso bank`, `kapso learn init-bank`, `kapso research`,
`kapso index_kg`, `Kapso.research()`, `Kapso.learn_knowledge()`,
`Kapso.index_kg()`, `Kapso(kg_index=)`, `--kg-index`, `build(serving_scope=)`
with the `dataset` coordinate, and `kapso-mcp`'s `--gates`, `--kg-index`
and `--family`. It adds what the review showed missing: `kapso experience
update | remove`, `kapso learn <campaign>` with `--harness`, `kapso-mcp
--harness`, and the intro's own prompt slot.

**Not in scope.** The config without modes (WP4; until then the campaign's
coordinate is the harness, not the mode). `build(context=)` and
`additional_context` (WP4). A paper as a source: the onboarding grammar
lists `--paper`, and no ingestor reads one; it is a later addition to
`add`, said in the docs as such, owner: this package's second iteration.
Joining a team bank that already has history and recovering from a
diverged remote (`share` stays push-only, refusing in git's words). The plugin's `/kapso:experience` (WP7).
`kapso trace` (WP6). The semantic test S6, "experience pays" (WP9), which
this package makes runnable and does not run.

## Interface

### The reference

`load_experience` takes one string, resolved by its form, as a harness
reference is:

| Form | Example | Resolves to | kind |
|---|---|---|---|
| reserved name | `mine`, `mine:all` | your own bank, the one `learn()` writes: `learning.bank.local_path`, `~/.kapso/bank.git` by default, created by `kapso experience add mine` or a first `learn()`; `:all` lifts the scope rule | `bank` |
| reserved name | `leeroopedia` | the hosted gate at `gates.leeroopedia.url`; loading probes that `LEEROOPEDIA_API_KEY` is present in the environment or `.env` (the session's own connection reads it; it is never configuration) | `hosted` |
| path | `./bank.git`, `~/team/bank.git`, `/srv/bank.git` | a bank home in the bank's own format, used in place; a string written as a path (`./`, `../`, `/`, `~`) is a path and must exist | `bank` |
| git reference | `acme/kapso-bank`, `acme/kapso-bank@main`, `git+https://…@v2` | a bank you read and never write, cloned under `experience.banks` (`~/.kapso/experience/banks/<slug>@<rev>/`) with its fetch record beside the clone, as the harness store does | `bank` |
| index name | `org-x` | a corpus ingested under that name: `experience.indexes/<name>/` (`~/.kapso/experience/indexes/`) | `index` |

Resolution order: the two reserved names (`mine` with or without `:all`),
then a string written as a path, which must exist, then a string with a
scheme, `git+`, `@` or `#`, or an `owner/repo` shorthand, as a git
reference, then an index name that exists. A `:all` suffix on anything but
`mine` is refused by name. A string that matches
none raises `ExperienceReferenceError` listing the forms and
`kapso experience list`. Loading never ingests and never creates: a bank
or an index that does not exist is refused with the `add` line that makes
it.

### The handle

```python
@dataclass
class ExperienceSource:
    reference: str          # as given
    kind: str               # "bank" | "hosted" | "index"
    resolved: str           # the bank home or clone, the gate's URL without its key, the index directory
    head: Optional[str]     # a bank's pinned commit; an index's id; None for the hosted gate
    provenance: str         # "measured by you" (mine), "measured by others" (a bank you read), "reported by others" (leeroopedia, an index)
    scope: str              # "harness" or "all"; `mine:all` is "all"; a bank you read is always "all" (decided 2026-10-24)
    def ref(self) -> ExperienceRef    # the record's shape: WP1's handle plus `scope` (the review)
```

```python
kapso.load_experience(ref: str) -> ExperienceSource   # `mine:all` lifts the scope; no other knob
kapso.experience -> list[ExperienceSource]      # in load order; loading a reference again replaces its entry
kapso.add_experience(ref: str | None = None, *, repo: str | None = None, research: str | None = None, name: str | None = None) -> str   # `mine` creates the bank; a repo or a question ingests into the index `name`
kapso.update_experience(ref: str | None = None) -> None   # pulls mine, re-fetches a bank you read at a moving reference; every source when None
kapso.remove_experience(ref: str) -> None       # deletes a clone or an index with its record
kapso.share_experience(url: str) -> None         # attaches the remote to your bank and pushes it
```

`load_experience` resolves, confirms the source is reachable and readable
(a bank's format, a key's presence, an index's record), pins it (a bank at
its head as it is on disk — loading never pulls, `update` does; an index
at its id), prints
one line (`Experience: mine at lr_2026-10-25_3, 142 cards, measured by
you`) and appends it to the object's sources. `add_experience` ingests a
repository or a research question into an index under the name and
returns the name; it needs the graph containers, which it says when they
are absent. `share_experience` is today's `connect_bank`, by its new name.

### The CLI

```
kapso experience add mine                                      # creates the empty bank home (today: learn init-bank)
kapso experience add leeroopedia                               # checks the key, probes the gate once
kapso experience add --repo https://github.com/org/x --name org-x        # ingests into an index (today: learn_knowledge + index_kg)
kapso experience add --research "QLoRA memory optimizations" --name qlora  # research, ingested (today: research + learn_knowledge)
kapso experience list                                          # mine, leeroopedia, every bank clone, every index, each with its state
kapso experience share https://github.com/acme/kapso-bank.git  # today: kapso bank connect
kapso experience update                                        # pulls mine from its remote; re-fetches every bank you read at a moving reference
kapso experience update acme/kapso-bank                        # one source
kapso experience remove acme/kapso-bank                        # deletes a clone or an index with its record
kapso learn ./campaign --harness ./harness                     # learns from a campaign directory (today: Python only)
kapso build --experience mine,leeroopedia ...                  # wins over the brief's Experience line
kapso build --experience mine:all ...                          # every card you measured, whatever the harness
kapso-mcp --harness ./harness --experience mine,org-x          # a host session, served the same way, with its coordinate
```

`--experience` is on `build` and on `kapso-mcp`. It is not on `deploy`,
which serves nothing, nor on `learn`, which writes `mine` whatever is
loaded (`Kapso(bank=)` stays the way to point `mine` elsewhere); the master
plan's "on the three verbs" is corrected here (a decision below). The
brief's `Experience` line takes the same references, one comma-separated
line or `- ` items; the loaded sources win over it.

### What a build does with the sources

- **Served where the engine serves**: ideation and implementation sessions,
  never the judge, never setup or verification. A bank source mounts the
  bank gate; the hosted source mounts the `leeroopedia` server; an index
  mounts the `idea` and `code` search gates over that index (one index
  per campaign; two loaded are refused by name). Nothing
  loaded, nothing served: the gate lists in the strategy's parameters
  lose `leeroopedia`, and the preflight's advisory for its key goes with
  it (a key is checked when the source is loaded).
- **One bank gate over every loaded bank.** The campaign's serving
  directory (`.kapso/serving/`) holds one pinned clone per bank; the gate
  reads `KAPSO_BANKS`, a JSON list of `{reference, head, dir, provenance, scope}`,
  in place of `KAPSO_BANK_DIR` and `KAPSO_BANK_HEAD`; `bank_index` lists
  every bank's servable cards grouped by source with the provenance line,
  `bank_get_card(name, source=None)` reads from the named source (the
  first that holds the name when none is named), the pull log records the
  source. One bank is the common case and reads as today.
- **The coordinate is the harness.** `KAPSO_TASK_HARNESS` carries the
  loaded harness's name, or `none`; `KAPSO_TASK_FAMILY` goes. A card's
  scope is `domain` or a list of `harness:<name>` coordinates
  (`harness:none` for lessons learned without one; `none` is a reserved
  harness name). Scope is a filter: `mine` lists in `bank_index` and opens
  in both reads only the cards whose scope covers the coordinate;
  `mine:all` lifts that and the intro says so; a bank you read serves
  everything it holds; quarantine is law under every scope. The
  card-writer writes `[harness:<name>]` from the trajectory's recorded
  harness; `family:` coordinates are no longer written or read anywhere
  (a pre-release bank is re-learned; there is nothing to migrate).
- **The intro** is compiled from the sources and rides where today's bank
  intro rides (after the static context notes): "You are served: 142
  cards measured by you under the trading harness (your bank, head
  `lr_2026-10-25_3`); 37 cards from `acme/kapso-bank`, measured by
  others, every scope; Leeroopedia's pages, reported by others; the
  `org-x` corpus (1,204 pages), reported by others." Then the fixed text
  on how to read a card and what a citation is, as today. It reaches the
  sessions through its own prompt slot, `{{experience_intro}}`, threaded
  into the ideation and implementation prompts and nowhere else (the
  judge, setup, verification and maintainer sessions never see it);
  `handler.additional_context` is frozen at construction and was never a
  seam (change 14). When `mine` has a remote the line says "measured by
  you and your team".
- **Pinned for the campaign.** Loading never pulls: `mine` is pinned at
  its home's head and a bank you read at its clone's head, as they are on
  disk (`kapso experience update` is the network step); an index at its
  id. A
  resume loads the recorded references and re-pins each bank at the
  recorded head (a checkout of that commit in the serving directory), so a
  resumed campaign is served what its first half was; a source that is
  gone is refused by name with `kapso experience list`.
- **The record.** `experience`, a list of `{reference, kind, resolved,
  head, provenance, scope}` in load order, in `launch.json`, `status.json`, the
  checkpoint (schema 5), `solution.json` (schema 4; `knowledge_index` and
  `experience_head` go) and the trajectory manifest. `Solution.experience`
  is the list; `explain()` prints one `Experience:` row per source. The
  list enters the checkpoint's fingerprint: a resume that names a
  different list is refused by name, as a changed harness is. The judge's
  `cards_load_bearing` stays on the node and in the reconstructed
  feedback, so the trajectory carries the attribution.

### The host session

`kapso-mcp --harness ./harness --experience mine,org-x` stages the same
serving into the session's directory under `learning.serving.session_root`
and serves the bank gate and the search gates beside `research`,
`repo_memory` and `experiment_history`, which ride as today by what the
directory holds. `--harness` gives the session its coordinate (`none`
without it); the intro rides as the MCP server's `instructions`, so the
session names its sources on connect; `leeroopedia` loaded here prints the
reminder to add it as the host's own HTTP server (the bundled server
serves bundled gates only); a source that cannot be loaded stops the
server with the fixing line on stderr; the session's directory is removed
when the server exits. `--gates`, `--kg-index` and `--family` go, and
`--gates` does not come back: the directory-driven gates turn themselves
off with a reason, and `kg` never rode on a host.

### The learning side

`learn()` writes `mine`, as today, and `Kapso(bank=)` is threaded through
every crew it runs; the mining and update crews, the graders' hindcast and
gauntlet, the behaviour scenarios and the bank invariants take the
coordinate from the trajectory manifest's `harness` (name, or `none`);
exposure comes from the archived pull log, which names the source of
every served row, so a cited name is credited to the source it was read
from and a name read from two sources is reported as an ambiguity; the
hindcast's own serving record is availability only. The crews' lead
sessions and their workers are staged with the harness's learning module
in full (skills, servers, hooks beside the pages), closing WP2's finding.
`learn_knowledge`, `research` and `index_kg` leave the facade; their
pipelines stay where they are (`kapso.knowledge_base`, `kapso.researcher`)
and are reached through `add_experience`.

### Config

```yaml
experience:
  banks: ~/.kapso/experience/banks       # banks you read, one clone per <slug>@<rev>, with a record beside
  indexes: ~/.kapso/experience/indexes   # corpora you ingested, one directory per name
learning:
  bank:
    local_path: ~/.kapso/bank.git        # mine
  serving:
    session_root: ~/.kapso/serving       # a host session's staging; `enabled` is gone
  retriever:
    probe_budget: 1                      # probe offers riding card reads, from `mine` alone
gates:
  leeroopedia:                           # the hosted source's address and timeout, unchanged
```

`load_experience_defaults(config_path)` reads the `experience` block, the
three learning keys and the hosted gate's block, as `load_harness_defaults`
does its own. Nothing
names a source in the config: loading is at the call, the flag or the
brief.

## Ownership

Edits: `src/kapso/experience/` (new: `reference.py`, `store.py`,
`sources.py`, `serving.py`), `src/kapso/cli/experience.py` (new),
`src/kapso/cli/build.py`, `src/kapso/cli/__init__.py`, `src/kapso/cli/learn.py`;
deletions `src/kapso/cli/bank.py`, `src/kapso/cli/research.py`,
`src/kapso/cli/index_kg.py`; `src/kapso/kapso.py`; `src/kapso/handles.py`
(`Solution.experience` filled, two fields deleted); `src/kapso/learning/serving_launch.py`,
`retriever.py` (the intro), `bank.py` (`eligible_for` on the harness
coordinate), `trajectory_store.py`, `update_frame.py`, `mining.py`, the
crews' role pages; `src/kapso/gated_mcp/gates/bank_gate.py`, `presets.py`,
`host_session.py`; `src/kapso/execution/run_checkpoint.py` (schema 5),
`observability.py`, `inbox.py`, `orchestrator.py`, `feedback_flow.py` and
`search_strategies/generic/*` where the gate lists and the intro are
threaded, `search_strategies/strategies.yaml`; `src/kapso/learning/harvest.py`,
`lesson_result.py`, `bank_invariants.py`, `behavior.py`, `graders/frame.py`,
`graders/gauntlet.py`, the grading prompts; `src/kapso/core/preflight.py`
and `cli/doctor.py` (the verbs), `cli/watch.py` (the operation names);
`src/kapso/harness/check.py` (the reserved name); `benchmarks/relbench/runner.py`
and `campaign.py`; `moltbook_bot/server.py`; `examples/ml_model_development/`;
`knowledge_base/learners/__main__.py`; `skills/*/kapso/SKILL.md`; the
README; `src/kapso/config.yaml`, `core/config.py`; the docs; the tests.

Read, not edited: `src/kapso/knowledge_base/search` and
`src/kapso/researcher/` (reached, not reshaped, beyond the namespace an
index needs: WP4 and later decide their fate).

## Changes

1. The reference grammar, the homes and the handle: `experience/reference.py`
   (`parse_experience_reference(text, *, cwd, bank_home, banks_root,
   indexes_root)` by the order above, `ExperienceReferenceError` with the
   forms), `experience/store.py` (bank clones with a record beside, the
   index home and its `index.json`), `experience/sources.py`
   (`ExperienceSource`, `resolve_source`, the bank-format check, the key
   check for the hosted gate, `pin`). After the review: a string written
   as a path is a path and must exist; `mine:all`. Test `tests/test_experience_reference.py`:
   each form and the order; an empty, odd or unknown string lists the
   forms; a missing path names the path; a missing bank or index names
   the `add` line; a key missing names the variable and `.env`; `:all`
   on anything but `mine` refused by name.
2. `Kapso.load_experience`, `Kapso.experience`, `load_experience_defaults`,
   the config block, `scope`, the printed line, re-loading a reference
   replacing its entry. Test `tests/test_experience_load.py`.
3. The serving plan from sources: `serving_launch.plan_serving(sources,
   task_coords, serve_dir)` clones each bank at its head, compiles the
   intro from every source, writes the serving record with the sources,
   returns the gate environment (`KAPSO_BANKS`, `KAPSO_TASK_HARNESS`, the
   pull log) and the index references; `serving.enabled` deleted from the
   config and the code; `build(serving_scope=)` and the `dataset`
   coordinate with it; the RelBench runner takes `--experience` and its
   harvest reads the record's sources. Built at `c670e1ed`. Tests:
   `tests/test_serving_wiring.py` rewritten on sources (one bank reads as
   today; two banks are two clones and one intro; no source means no
   plan; the hosted gate and an index without a bank; two indexes
   refused).
4. The bank gate over several banks: `KAPSO_BANKS`, `bank_index` grouped
   by source with provenance, `bank_get_card(cards, source=)` and the
   evidence read likewise, the pull log with the source. Built at
   `c670e1ed`. Tests: the gate's tests extended with two banks and a name
   held by both.
5. The scope coordinate: `Card.eligible_for({"harness": ...})`,
   `harness:<name>` and `harness:none` (`none` reserved in the harness
   `check`); scope as a filter in `render_index` and both reads for
   `mine` at the default scope, lifted by `mine:all`; probe offers from
   `mine` alone; the card-writer's page; the update frame, the mining
   frame, the graders' hindcast and gauntlet, the behaviour scenarios and
   the bank invariants taking the coordinate from the manifest's
   `harness`; exposure and attribution from the pull log by (source,
   name), a two-source name an ambiguity finding; "measured by you and
   your team" when `mine` has a remote. Tests: `tests/test_bank_retriever.py`,
   `tests/test_bank_pull.py`, `tests/test_update_frame.py`,
   `tests/test_mining_frame.py`, `tests/test_grading_frame.py`,
   `tests/test_bank_invariants.py` on the coordinate and on a duplicate
   name across two sources. Built at `ccd529d4`.
6. `build()`: the sources from the object, else the brief's `Experience`
   line; the gates per source in ideation and implementation; the records
   in `launch.json`, `status.json`, the checkpoint (schema 5) and
   `solution.json` (schema 4, the two fields deleted), the trajectory
   manifest, each entry with its `scope`; the fingerprint and the inbox's
   resume keys trading `kg_index` and `serving_scope` for `experience`; a
   resume re-pinning at the recorded heads and scopes, refusing a gone
   source and a changed list by name; `Solution.experience`, `explain()`;
   the judge's `cards_load_bearing` kept on the node and in the
   reconstructed feedback; `Kapso(bank=)` threaded through every crew
   `learn()` runs. Tests `tests/test_experience_records.py` (the real
   writers, the sessions stubbed; a served build seeded from a
   repository; the attribution round trip) and the learn test with two
   distinct banks. Built at `993fdb60`.
7. `add_experience(ref=, repo=, research=, name=)`: `mine` creates the
   bank; a repository or a question ingests into the index home under
   `name`, each index in its own backend namespace named in `index.json`
   (`backend_refs`), an existing name refused, the record's keys the
   ones the search gates read; the merger receives the index builder as
   an experience-package function; `learn_knowledge`, `research`,
   `index_kg` and `Kapso(kg_index=)` deleted, `Kapso.reply()` and the
   resume constructing from the record's `experience`; the knowledge
   search constructed when an index is loaded, and the orchestrator's
   `_create_knowledge_search` building no backend without one (the WP2
   no-key crash, which is there, not in the facade). Tests
   `tests/test_experience_add.py` with the provider calls stubbed and the
   real pipeline glue exercised, an orchestrator constructed with no
   source and no embedding key, a reply from another directory. Built at
   `e0b8acff`.
8. `share_experience(url)` and `kapso experience share`; `create_bank_repo`
   deleted (the repository is the person's to create with `gh`).
9. `kapso experience add | list | share`, `add` with `ref` optional and
   exactly one of `ref`, `--repo`, `--research` required in one message,
   reserved names refused for `--name`; `kapso learn <campaign>
   [--harness ref]` (WP2's hand-over); `kapso bank`, `kapso research`,
   `kapso index_kg` and `kapso learn init-bank` deleted with their
   modules; the verb tuple; the docs coverage check. Tests
   `tests/test_cli_experience.py` (every subcommand's flags, `add mine`
   creates the home, `list` has an empty state and the rows, `share`
   attaches a remote to a bare bank) and `tests/test_cli_learn.py` (the
   campaign form). Built at `a7e8101c`; the learning system's tools moved
   under `kapso learn dev` (the decision is in DECISIONS.md).
10. `--experience` on `kapso build` (validated before `--detach` forks, as
    `--harness`), the brief's line, `kapso-mcp --experience` (built at
    `c670e1ed`) with `--harness` for the coordinate, the intro as the
    server's `instructions`, the session directory removed at exit, the
    loaded hosted settings threaded into the gate config. Tests in
    `tests/test_cli_build.py`, `tests/test_cli_detach.py`,
    `tests/test_host_session_server.py` (an MCP initialisation reading
    the instructions). Built at `6d71ac58` (the host session) and
    `65e6f300` (`--experience` on the build and the brief's line in
    `build()`).
11. The harness's learning module staged into the crews' lead sessions
    and their `codex exec` workers, with mining's `.claude` handling
    leaving the harvested inventory intact. Test in
    `tests/test_harness_deploy_learn.py` and the worker invocation's
    configuration. Built at `ed7f8261`: a harvest leaves the hosts'
    staging directories out of a bundle, a mining run has its own
    directory under `learning.mining.run_root`, and the guidance names
    the task statement only when the campaign has one (the decisions
    are in DECISIONS.md).
12. Docs: `docs/experience/{index,use,add,share}.mdx`,
    `docs/reference/experience.mdx`, the `Experience` entries in the CLI,
    API, brief and configuration references, `docs/learning/bank.mdx` and
    `serving.mdx` rewritten on sources, `docs/knowledge/*` and
    `docs/research/overview.mdx` folded into the experience pages with
    redirects in `docs.json`, the churn example's README on `learn()` then
    `--experience mine`; `scripts/check_docs_coverage.py` covering the
    verb; `mint validate` and `mint broken-links`. The deletion
    inventory beyond the docs: the three skills' pages, the README,
    `docs/installation.mdx`, `docs/coding-agent-skills.mdx`, the learning
    and evolve pages, preflight's `research`/`learn_knowledge` verbs and
    its `kapso bank` fix lines, `kapso doctor`'s verbs, `kapso watch`'s
    operation names, `moltbook_bot/server.py` (`kg_index`, `/research`),
    `knowledge_base/learners/__main__.py`, the ML full-loop example, the
    manual tests.
13. The record of this package: the proof runs, the review, the decisions,
    the findings; the master's status.
14. The intro's seam: `{{experience_intro}}` threaded into the ideation
    and implementation prompts as WP2 threads the harness guidance, and
    into no other session. Tests render the two prompts with the intro
    and assert its absence from the judge, setup, verification and
    maintainer prompts; the mounted-gate assertion extended to two banks
    and to an index; the judge's gate list never holds `bank`. Built at
    `e4eb0712`.
15. `kapso experience update [ref]` and `remove <ref>`, with
    `Kapso.update_experience` and `remove_experience`: `update` pulls
    `mine` fast-forward from its origin and re-fetches a bank you read at
    a moving reference (a pinned commit never moves; a campaign keeps its
    pin); `remove` deletes a clone or an index with its record and
    namespace. Tests in `tests/test_cli_experience.py` with local git
    remotes. Built at `e86110c7`.
16. The drift test: `tests/test_no_retired_names.py` over `src`, `tests`,
    `skills`, `examples`, `benchmarks`, `moltbook_bot` and `docs` for the
    retired names (`serving.enabled`, `kapso bank`, `learn init-bank`,
    `research(`, `learn_knowledge`, `index_kg`, `kg_index=`, `--kg-index`,
    `KAPSO_BANK_DIR`, `KAPSO_TASK_FAMILY`, `serving_scope`, `family:`),
    the precedent being `tests/test_no_evolve_left.py`.

## Tests

- Syntactic: the files above, in the curated gate. Negative cases: every
  form that resolves to nothing; a bank in the wrong format; a key
  missing; a gone source on resume; a changed list on resume; two banks
  holding one card name, through the gate, the pull log and the evidence
  check; a card with a `family:` coordinate (not eligible at the default
  scope, served under `mine:all`); `:all` on a bank you read. Goldens: the
  intro for one, two and three sources; the serving record; the gate
  environment; the rendered ideation and implementation prompts with the
  intro, and the judge's without. Contract: the record fields with
  `scope`; the checkpoint and solution schemas; `Solution.open` reading
  the sources back; the judge's gate list never holding `bank`.
- Proof run, on a fresh machine from the wheel: WP2's trading campaign
  (the harness example) learned on the box with `kapso learn <campaign>
  --harness examples/harnesses/trading` (the crews on the shared token),
  until the bank holds an admitted, servable card scoped `harness:trading`
  or `domain`; then a build of the trading example on the machine with
  `--harness` and `--experience mine` at a small budget (two experiments):
  the archived campaign must show the intro in the ideation prompt with
  the card count and "measured by you, under the trading harness", a
  `bank_get_card` read in the pull log with its source and head,
  `experience` in all four records with the head the learn produced,
  `kapso experience list` printing `mine` with that head, and
  `Solution.open` reading `experience` in a second process. A second
  build under no harness must list zero of the harness-scoped cards and
  all of them under `mine:all` (the index, not only the count).
  `leeroopedia` is loaded on the development box with the key, once, and
  its session record shows the server mounted; the fresh machine has no
  key, which `add leeroopedia` must say.
- Semantic hook: S6 ("experience pays") becomes runnable: the same task
  built twice, the second served `mine`; the numbers to record are the
  two scores and the cards the second campaign cited (the judge's
  `cards_load_bearing`).

## Acceptance

- `kapso experience list` on a fresh machine prints the empty state with
  the two `add` lines; after `add mine` it prints `mine` with its head and
  zero cards; after a `learn()` that admitted a card the head moved and
  the count is the cards' count (a learn that admits nothing moves
  nothing, and says so).
- A build with `--experience mine` after a learn serves the intro in the
  ideation and implementation prompts and the bank gate; the campaign's
  `launch.json`, `status.json`, `run_state.json` and `solution.json` carry
  the same `experience` list with the pinned head and scope; a resume
  after the bank moved re-pins at the recorded head; a resume that names
  a different list is refused by name.
- A build with nothing loaded serves nothing and records `experience: []`;
  no key is needed for it (no embedder at construction).
- `load_experience("acme/kapso-bank")` fetches the clone under
  `experience.banks` with the record beside it and serves every card it
  holds; `load_experience("mine")` under the trading harness lists and
  opens only the cards scoped `domain` or `harness:trading`, and
  `mine:all` lifts that.
- `kapso bank`, `kapso research`, `kapso index_kg`, `kapso learn
  init-bank`, `--kg-index`, `kapso-mcp --gates`, `serving.enabled` and
  `serving_scope` are gone from the CLI, the docs, the skills, the
  examples and the tests, which the drift test checks; `kapso experience
  update | remove` and `kapso learn <campaign>` exist; the docs coverage
  check covers `kapso experience`.
- Both reviewers' findings on this plan and on the pull request are
  answered below; the gate is green; the docs checks are green.

## Risks

| Risk | What is done |
|---|---|
| the bank gate's single-bank assumptions run deep (card names, the pull log, the exposure ladder) | change 4 keeps one bank the common case: `KAPSO_BANKS` with one entry reads as today; the index's grouping and `source` are additive |
| the scope coordinate change strands existing banks | there is nothing to migrate pre-release and no `family:` knowledge stays in code: such a card is not eligible at the default scope and reads under `mine:all`; the owner's RelBench bank is re-learned when WP8 ports that harness |
| the knowledge pipeline's containers (Weaviate, Neo4j) are absent on the fresh machine | `add --repo` says which container and the line that starts it; the proof run covers `mine`, not an index; the index path is tested with the pipeline stubbed at its boundary |
| the Leeroopedia key on the fresh machine | not stored as a secret; loaded once on the development box; `add leeroopedia` on the machine must refuse with the variable name |
| the learn in the proof run costs the shared token an hour of crews | the token gate before it; the learn runs once; the second build is small |
| `--experience` on `learn` and `deploy` expected by the master | not added, with the reason in the Interface and a decision entry; the master's line corrected in this package's status row |

## Review

The sub-plan was reviewed at `276e796b` by Codex (`gpt-6-astra`, xhigh)
and Claude Code (`claude-opus-5`) while changes 1, 2, 8 and half of 9 were
landing; the reviews are kept locally in `scripts/redesign/runs/wp3-plan-review/`
(gitignored, like the other run records). Each finding's answer is below; "amended" means the plan's text above was
changed accordingly and the decision is in `DECISIONS.md` (2026-10-25,
WP3). The pull-request review follows the build.

### Codex

| # | Finding | Answer |
|---|---|---|
| P1-1 | `plan_serving` as written clones and writes before a seeded workspace exists | The plan/stage split is kept: `plan_serving` is pure, `stage_serving` runs after orchestrator construction (change 3, built). A served build seeded from a repository is a change 6 test. |
| P1-2 | The intro rides a dead seam: `handler.additional_context` is frozen at construction | Accepted; the plan prescribed the benchmark's slot. Change 14 threads `{{experience_intro}}` into the ideation and implementation prompts only, with rendered-prompt tests and an absence test for the judge, setup, verification and maintainer sessions. |
| P1-3 | `scope` is lost between the handle, the gate and the records | Amended: `scope` is on `ExperienceRef`, in every record and in the fingerprint; `KAPSO_BANKS` carries it (built); a resume re-loads at the recorded scope (change 6). |
| P1-4 | `eligible_for` does not filter; the retriever lists every servable card | Amended, with a decision: scope is a filter again on the harness coordinate — `mine` at the default scope lists and reads only the cards its scope covers, `mine:all` lifts, a bank you read serves everything, quarantine always (change 5). The Tests section's `family:` sentence is corrected: such a card is not eligible under the default scope and is served under `mine:all`. |
| P1-5 | Multi-bank identity is more than a `source` field: citations, the evidence tool, attribution | Amended, with a decision: identity is (source, name) through the pull log; both read tools take `source=` (built); the learning side credits a cited name to the source it was read from and reports a two-source name as an ambiguity (change 5); the citation grammar stays `[card:name]`. Tests follow the whole path with a duplicate name. |
| P1-6 | An index is neither isolated nor pinned: backends share namespaces | Accepted for change 7: each index gets its own backend namespace named in its record's `backend_refs`; `add` with an existing name refuses; `remove` deletes the namespace; "pinned at its id" means the namespace is never written again. Verified against both backends when built. |
| P1-7 | The graders' hindcast and the evidence check still speak `family`/`dataset` and expect a `served` list | Accepted: change 5 lists `graders/frame.py`, `gauntlet.py`, `behavior.py`, `bank_invariants.py` and the grading prompts; exposure comes from the archived pull log with source identity, the hindcast record is availability only. |
| P1-8 | `Kapso(bank=)` is not threaded to the update crew | Accepted: change 6 threads the resolved bank home through every crew `learn()` runs; test with two distinct banks. |
| P1-9 | The host cannot mount the hosted source through the bundled server | Decided: `kapso-mcp` serves the bundled gates only; loading `leeroopedia` on the host prints the reminder to add it as the host's HTTP server (built, documented). |
| P2-1 | Several indexes have no routing contract | Decided: one index per campaign, refused by name at planning (built). |
| P2-2 | Deleting `index_kg` orphans the merger's builder; `.index` vs `index.json` | Change 7 names the builder the merger receives (an experience-package function) and pins the record's keys to what the gates read. |
| P2-3 | The no-key crash is in the orchestrator's search construction, not the facade | Accepted: change 7 fixes `_create_knowledge_search` (no backend without a loaded index) with an orchestrator construction test under no key. |
| P2-4 | `Kapso.reply()` still constructs with `kg_index=` | Accepted: change 7 constructs from the record's `experience`; a reply/resume test from another directory. |
| P2-5 | `kapso learn <campaign>` and `--harness` on learn, assigned by WP2, are missing | Accepted: change 9 adds them with a CLI test. |
| P2-6 | The crews' workers (`codex exec`) and mining's `.claude` handling are outside the lead's staging | Accepted: change 11 stages the learning module for the workers too and keeps the harvested inventory intact. |
| P2-7 | Team-bank joining and synchronisation are unspecified | Decided: `share` stays push-only in this package, refusing a rejected push in git's words; joining and divergence recovery are a later package; the intro says "measured by you and your team" when `mine` has a remote (change 5). |
| P2-8 | A bank you read is never refreshed | Amended: change 15 adds `kapso experience update [ref]` and `remove <ref>`; loading never pulls (decision). |
| P2-9 | The host session has no coordinate and drops the intro | Amended: `kapso-mcp --harness <ref>` is the coordinate; the intro rides as the server's `instructions` (change 10). |
| P2-10 | RelBench's runner and harvest break | Done in change 3: the runner takes `--experience`, the harvest reads the record's sources. |
| P2-11 | `moltbook_bot`, `knowledge_base/learners/__main__`, the ML examples call deleted APIs | Accepted: change 12 migrates or retires each; change 16's drift test catches a retired name anywhere. |
| P2-12 | Skills, preflight, doctor, `MemoryStatus` still prescribe the removed interface | Accepted: change 12 covers the three skills, preflight's verbs and fix lines, `kapso doctor`'s verbs; `MemoryStatus.serving_enabled` is gone (built). |
| P2-13 | `probe_budget` and the hosted settings have no route | `probe_budget` rides `load_experience_defaults` (built, listed in Config); change 10 threads the loaded source's hosted settings into the gate config. |
| P2-14 | A missing explicit path can resolve as a git reference; `harness:none` collides with a harness named `none`; `--name mine` | Amended: a string written as a path is a path and must exist (change 1); `none` is a reserved harness name (change 5); reserved names are refused for `--name` (change 9). |
| P2-15 | The proof shows no card read; "the head moved" is false when nothing is admitted | Amended: the proof learns from the trading campaign, requires an admitted servable card, and asserts a `bank_get_card` read with source and head in the pull log; the acceptance line says "after a learn that admitted a card". |
| P2-16 | The judge's `cards_load_bearing` is discarded before archival | Accepted: change 6 keeps it on the node and in the reconstructed feedback, with a round-trip test. |
| P3-1 | Deviations recorded against the wrong decisions; papers have no owner | Amended: the decisions are in `DECISIONS.md`; papers' owner is the package's second iteration; the master's line was the harness interface's. |

### Claude Code

| # | Finding | Answer |
|---|---|---|
| P1-1 | The intro has no live seam | As Codex P1-2: change 14. |
| P1-2 | Scope is not a filter anywhere | As Codex P1-4: a decision reversing the 2026-08 amendment, change 5. |
| P1-3 | `harness:none` buckets every harness-less campaign; `scope="all"` has no CLI syntax; `dataset:` lingers | Amended: `mine:all` is the lift's syntax in the CLI, the brief and Python; `none` reserved; the `dataset` coordinate and `serving_scope` retired (built). The single coordinate is justified in the decision: the harness is the domain; a lesson learned outside any harness is `domain` or `none` by the writer's call. |
| P1-4 | RelBench's serving breaks and nobody owns it | As Codex P2-10: done in change 3; the two files are in Ownership. |
| P1-5 | The hindcast, gauntlet, behaviour scenarios and invariants still build `family`/`dataset` | As Codex P1-7: change 5. |
| P1-6 | `kapso learn <campaign>` and `--harness` on learn are missing | As Codex P2-5: change 9. |
| P1-7 | The host session loses gate control and its coordinate, fetches at every start, and an error kills it | Decided: no `--gates` (the directory-driven gates turn themselves off with a reason; `kg` never rode on a host); `--harness` gives the coordinate; loading never pulls, so a start touches the network only to fetch a bank for the first time; a source that cannot be loaded stops the server with the fixing line (rule 2, no partial serving); the session directory is removed at exit; the intro rides as the server's instructions (change 10). |
| P1-8 | A bank you read can never be refreshed; no `update`/`remove` | As Codex P2-8: change 15. |
| P2-1 | The no-key finding is mislocated | As Codex P2-3: change 7. |
| P2-2 | A resume loses `scope`; the fingerprint keys and the inbox's resume keys must trade `kg_index`/`serving_scope` for `experience` | As Codex P1-3; `execution/inbox.py` is in Ownership; the decision says the loaded experience is campaign identity (fingerprinted, a changed list refused by name). |
| P2-3 | `build(serving_scope=)` was never retired by name | Done in change 3, listed in Scope. |
| P2-4 | Unlisted consumers: preflight verbs and fix lines, doctor, watch/observability operation names, `strategies.yaml`, the strategy's literal gate lists, skills, `moltbook_bot`, the ML examples, docs, tests, manual tests; make the acceptance machine-checkable | Accepted: each is named in change 12's inventory; change 16 adds the drift test over `src, tests, skills, examples, benchmarks, moltbook_bot, docs`. `strategies.yaml` and the mode lists lost `leeroopedia` in change 3; the strategy's literal defaults are the engine's own duplication, which WP4 collapses with the modes. |
| P2-5 | The serving record's and the manifest's `bank_head` are read in unlisted places | Done in change 3 (`learn()` reads the record's `sources`; the manifest carries `experience`); the graders' readers are change 5. |
| P2-6 | `kapso experience list` cannot detect `family:` cheaply or safely | Decided: no `family:` knowledge anywhere; `list` is silent; the Risks row is corrected. |
| P2-7 | The deviation list is incomplete | Amended: every deviation has a decision entry (deploy, learn, papers, `update`/`remove`, `mine:all`, the host coordinate and intro). |
| P2-8 | Probe offers ride every loaded bank | Decided: offers come from `mine` alone (change 5, with the gate). |
| P3-1 | Names: `ExperienceSource` vs `Experience`/`ExperienceRef`; `experience.banks` names a home; `KAPSO_BANKS` is a document; `add_experience` cannot create `mine` | `ExperienceSource` stays: the plan's noun for a loaded thing is "source" throughout and `ExperienceRef` is its record, as `HarnessRef` is a harness's. The config keys name homes and say so in their comments. `KAPSO_BANKS` stays a document: the gate reads one variable. `add_experience("mine")` creates the bank (change 7), so Python and the CLI create the same three things. |
| P3-2 | `kapso experience add`'s two shapes are unspecified; `--name mine` | Amended: `ref` is optional and exactly one of `ref`, `--repo`, `--research` is required, said in one message; reserved names refused (change 9). |
| P3-3 | A non-`mine` source silently reinterprets `scope=` | Amended: `scope=` goes with `mine:all`; a suffix on any other reference is refused by name. |
| P3-4 | Config-like values: `probe_budget`, the strategy's gate-list literals, the hosted key's wording | `probe_budget` is listed in Config and rides `load_experience_defaults`; the gate-list literals are WP4's (above); the Interface says the key is a presence probe plus a provider-read credential, never configuration. |
| P3-5 | The index record's keys must match what the gate reads | Change 7 pins them (as Codex P2-2). |
| P3-6 | Tests: the intro reaching a prompt, the judge never getting the bank gate, the resume re-pin, the mounted-gate assertion for two banks and an index; the proof on the churn example proves nothing about harness scoping | Amended: the Tests section names each; the proof runs on the trading fixture. S6 is measurable once change 14 is in. |
| Q1 | Does `mine` pull on a resume? | No: loading never pulls; a resume re-pins at the recorded head from the local home. |
| Q2 | Which card does a lesson's evidence credit when two banks hold the name? | The source the pull log shows it was read from; a name read from both is an ambiguity finding. |
| Q3 | Is `experience` campaign identity or a dial? | Identity: fingerprinted; a resume that names a different list is refused by name. |
