# WP3: experience

2026-10-25. Branch `wp3-experience` off `redesign` at `2e38996b` (WP2
merged). Size M as the master estimates; thirteen changes below.

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
`Kapso.index_kg()`, `Kapso(kg_index=)`, `--kg-index`, and `kapso-mcp`'s
`--gates`, `--kg-index` and `--family`.

**Not in scope.** The config without modes (WP4; until then the campaign's
coordinate is the harness, not the mode). `build(context=)` and
`additional_context` (WP4). A paper as a source: the onboarding grammar
lists `--paper`, and no ingestor reads one; it is a later addition to
`add`, said in the docs as such. The plugin's `/kapso:experience` (WP7).
`kapso trace` (WP6). The semantic test S6, "experience pays" (WP9), which
this package makes runnable and does not run.

## Interface

### The reference

`load_experience` takes one string, resolved by its form, as a harness
reference is:

| Form | Example | Resolves to | kind |
|---|---|---|---|
| reserved name | `mine` | your own bank, the one `learn()` writes: `learning.bank.local_path`, `~/.kapso/bank.git` by default, created by `kapso experience add mine` or a first `learn()` | `bank` |
| reserved name | `leeroopedia` | the hosted gate at `gates.leeroopedia.url`, its key from the environment or `.env` | `hosted` |
| path | `./bank.git`, `~/team/bank.git` | a bank home in the bank's own format, used in place | `bank` |
| git reference | `acme/kapso-bank`, `acme/kapso-bank@main`, `git+https://…@v2` | a bank you read and never write, cloned under `experience.banks` (`~/.kapso/experience/banks/<slug>@<rev>/`) with its fetch record beside the clone, as the harness store does | `bank` |
| index name | `org-x` | a corpus ingested under that name: `experience.indexes/<name>/` (`~/.kapso/experience/indexes/`) | `index` |

Resolution order: the two reserved names, then a path that exists, then a
string with a scheme, `git+`, `@` or `#`, or an `owner/repo` shorthand, as
a git reference, then an index name that exists. A string that matches
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
    scope: str              # "harness" or "all"; a bank you read is always "all" (decided 2026-10-24)
    def ref(self) -> ExperienceRef    # the record's shape (WP1's handle, unchanged)
```

```python
kapso.load_experience(ref: str, *, scope: str = "harness") -> ExperienceSource
kapso.experience -> list[ExperienceSource]      # in load order; loading a reference again replaces its entry
kapso.add_experience(*, repo: str | None = None, research: str | None = None, name: str) -> str   # the index name
kapso.share_experience(url: str) -> None         # attaches the remote to your bank and pushes it
```

`load_experience` resolves, confirms the source is reachable and readable
(a bank's format, a key's presence, an index's record), pins it (a bank at
its head after `mine` pulled from its remote; an index at its id), prints
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
kapso build --experience mine,leeroopedia ...                  # wins over the brief's Experience line
kapso-mcp --experience mine,org-x                              # a host session, served the same way
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
  mounts the `idea` and `code` search gates over that index. Nothing
  loaded, nothing served: the gate lists in the strategy's parameters
  lose `leeroopedia`, and the preflight's advisory for its key goes with
  it (a key is checked when the source is loaded).
- **One bank gate over every loaded bank.** The campaign's serving
  directory (`.kapso/serving/`) holds one pinned clone per bank; the gate
  reads `KAPSO_BANKS`, a JSON list of `{dir, head, reference, provenance}`,
  in place of `KAPSO_BANK_DIR` and `KAPSO_BANK_HEAD`; `bank_index` lists
  every bank's servable cards grouped by source with the provenance line,
  `bank_get_card(name, source=None)` reads from the named source (the
  first that holds the name when none is named), the pull log records the
  source. One bank is the common case and reads as today.
- **The coordinate is the harness.** `KAPSO_TASK_HARNESS` carries the
  loaded harness's name, or `none`; `KAPSO_TASK_FAMILY` goes. A card's
  scope is `domain` or a list of `harness:<name>` coordinates
  (`harness:none` for lessons learned without one). `mine` serves the
  cards whose scope covers the coordinate; `scope="all"` serves every
  servable card of `mine` and the intro says so; a bank you read serves
  what it holds. The card-writer writes `[harness:<name>]` from the
  trajectory's recorded harness; `family:` coordinates are no longer
  written or read (a pre-release bank is re-learned or edited by hand;
  there is nothing to migrate).
- **The intro** is compiled from the sources and rides where today's bank
  intro rides (after the static context notes): "You are served: 142
  cards measured by you under the trading harness (your bank, head
  `lr_2026-10-25_3`); 37 cards from `acme/kapso-bank`, measured by
  others, every scope; Leeroopedia's pages, reported by others; the
  `org-x` corpus (1,204 pages), reported by others." Then the fixed text
  on how to read a card and what a citation is, as today.
- **Pinned for the campaign.** `mine` pulls from its remote when it has
  one (a conflict is an error with git's words) and is pinned at its head;
  a bank you read is pinned at its clone's head; an index at its id. A
  resume loads the recorded references and re-pins each bank at the
  recorded head (a checkout of that commit in the serving directory), so a
  resumed campaign is served what its first half was; a source that is
  gone is refused by name with `kapso experience list`.
- **The record.** `experience`, a list of `{reference, kind, resolved,
  head, provenance}` in load order, in `launch.json`, `status.json`, the
  checkpoint (schema 5), `solution.json` (schema 4; `knowledge_index` and
  `experience_head` go) and the trajectory manifest. `Solution.experience`
  is the list; `explain()` prints one `Experience:` row per source.

### The host session

`kapso-mcp --experience mine,org-x` stages the same serving into the
session's directory under `learning.serving.session_root` and serves the
bank gate and the search gates beside `research`, `repo_memory` and
`experiment_history`, which ride as today by what the directory holds.
`--gates`, `--kg-index` and `--family` go.

### The learning side

`learn()` writes `mine`, as today; the mining and update crews take the
coordinate from the trajectory manifest's `harness` (name, or `none`), and
their lead sessions are staged with the harness's learning module in
full (skills, servers, hooks beside the pages), closing WP2's finding.
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
gates:
  leeroopedia:                           # the hosted source's address and timeout, unchanged
```

`load_experience_defaults(config_path)` reads the `experience` block and
the two learning keys, as `load_harness_defaults` does its own. Nothing
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
`observability.py`, `orchestrator.py` and `search_strategies/generic/*`
where the gate lists and the intro are threaded; `src/kapso/config.yaml`,
`core/config.py`; the docs; the tests.

Read, not edited: `src/kapso/harness/` (the coordinate comes from
`Harness.name`); `src/kapso/knowledge_base/` and `src/kapso/researcher/`
(reached, not reshaped: WP4 and later decide their fate).

## Changes

1. The reference grammar, the homes and the handle: `experience/reference.py`
   (`parse_experience_reference(text, *, cwd, bank_home, banks_root,
   indexes_root)` by the order above, `ExperienceReferenceError` with the
   forms), `experience/store.py` (bank clones with a record beside, the
   index home and its `index.json`), `experience/sources.py`
   (`ExperienceSource`, `resolve_source`, the bank-format check, the key
   check for the hosted gate, `pin`). Test `tests/test_experience_reference.py`:
   each form and the order; an empty, odd or unknown string lists the
   forms; a missing bank or index names the `add` line; a key missing
   names the variable and `.env`.
2. `Kapso.load_experience`, `Kapso.experience`, `load_experience_defaults`,
   the config block, `scope`, the printed line, re-loading a reference
   replacing its entry. Test `tests/test_experience_load.py`.
3. The serving plan from sources: `serving_launch.plan_serving(sources,
   task_coords, serve_dir)` clones each bank at its head, compiles the
   intro from every source, writes the serving record with the sources,
   returns the gate environment (`KAPSO_BANKS`, `KAPSO_TASK_HARNESS`, the
   pull log) and the index references; `serving.enabled` deleted from the
   config and the code. Tests: `tests/test_serving_wiring.py` rewritten
   on sources (one bank reads as today; two banks are two clones and one
   intro; no source means no plan).
4. The bank gate over several banks: `KAPSO_BANKS`, `bank_index` grouped
   by source with provenance, `bank_get_card(name, source)`, the pull log
   with the source. Tests: the gate's tests extended with two banks and a
   name held by both.
5. The scope coordinate: `Card.eligible_for({"harness": ...})`,
   `harness:<name>` and `harness:none`, the card-writer's page, the
   update frame and the mining frame taking the coordinate from the
   manifest's `harness`; `scope="all"`. Tests: `tests/test_bank_retriever.py`,
   `tests/test_update_frame.py`, `tests/test_mining_frame.py` on the
   coordinate.
6. `build()`: the sources from the object, else the brief's `Experience`
   line; the intro into the knowledge slot; the gates per source in
   ideation and implementation; the records in `launch.json`,
   `status.json`, the checkpoint (schema 5) and `solution.json` (schema 4,
   the two fields deleted), the trajectory manifest; a resume re-pinning
   at the recorded heads and refusing a gone source; `Solution.experience`,
   `explain()`. Test `tests/test_experience_records.py` (the real writers,
   the sessions stubbed).
7. `add_experience(repo=, research=, name=)`: the index home, the
   knowledge pipeline reached through it, `index.json` as the index's
   record; `learn_knowledge`, `research`, `index_kg` and `Kapso(kg_index=)`
   deleted; the knowledge search constructed when an index is loaded, not
   at construction (so a build with no index needs no embedding key: the
   WP2 finding). Test `tests/test_experience_add.py` with the pipeline
   stubbed at its boundary, and the construction test extended.
8. `share_experience(url)` and `kapso experience share`; `create_bank_repo`
   deleted (the repository is the person's to create with `gh`).
9. `kapso experience add | list | share`; `kapso bank`, `kapso research`,
   `kapso index_kg` and `kapso learn init-bank` deleted with their
   modules; the verb tuple; the docs coverage check. Test
   `tests/test_cli_experience.py` (every subcommand's flags, `add mine`
   creates the home, `list` has an empty state and the rows, `share`
   attaches a remote to a bare bank).
10. `--experience` on `kapso build` (validated before `--detach` forks, as
    `--harness`), the brief's line, `kapso-mcp --experience`. Tests in
    `tests/test_cli_build.py`, `tests/test_cli_detach.py`,
    `tests/test_host_session_server.py`.
11. The harness's learning module staged into the crews' lead sessions.
    Test in `tests/test_harness_deploy_learn.py`.
12. Docs: `docs/experience/{index,use,add,share}.mdx`,
    `docs/reference/experience.mdx`, the `Experience` entries in the CLI,
    API, brief and configuration references, `docs/learning/bank.mdx` and
    `serving.mdx` rewritten on sources, `docs/knowledge/*` and
    `docs/research/overview.mdx` folded into the experience pages with
    redirects in `docs.json`, the churn example's README on `learn()` then
    `--experience mine`; `scripts/check_docs_coverage.py` covering the
    verb; `mint validate` and `mint broken-links`.
13. The record of this package: the proof runs, the review, the decisions,
    the findings; the master's status.

## Tests

- Syntactic: the files above, in the curated gate. Negative cases: every
  form that resolves to nothing; a bank in the wrong format; a key
  missing; a gone source on resume; two banks holding one card name; a
  card with a `family:` coordinate (ignored, never served, so a stale bank
  is visible in `list` as such). Goldens: the intro for one, two and three
  sources; the serving record; the gate environment. Contract: the record
  fields; the checkpoint and solution schemas; `Solution.open` reading the
  sources back.
- Proof run, on a fresh machine from the wheel: the churn example built
  (forty-five minutes, two experiments), `kapso.learn(solution)` on the
  box (the crews on the shared token), then a second build of the same
  example with `--experience mine` at a smaller budget: the archived
  second campaign must show the intro with the card count and "measured
  by you under no harness" (the churn example has no harness), `bank_index`
  calls in the ideation stream, `experience` in all four records with the
  head the learn produced, `kapso experience list` printing `mine` with
  that head, and `Solution.open` reading `experience` in a second process.
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
  zero cards; after a `learn()` the head moved and the count is the
  cards' count.
- A build with `--experience mine` after a learn serves the intro and the
  bank gate; the campaign's `launch.json`, `status.json`, `run_state.json`
  and `solution.json` carry the same `experience` list with the pinned
  head; a resume after the bank moved re-pins at the recorded head.
- A build with nothing loaded serves nothing and records `experience: []`;
  no key is needed for it (no embedder at construction).
- `load_experience("acme/kapso-bank")` fetches the clone under
  `experience.banks` with the record beside it and serves every card it
  holds; `load_experience("mine")` under the trading harness serves only
  the cards scoped `domain` or `harness:trading`, and `scope="all"` lifts
  that.
- `kapso bank`, `kapso research`, `kapso index_kg`, `kapso learn
  init-bank`, `--kg-index`, `kapso-mcp --gates` are gone from the CLI, the
  docs and the tests; the docs coverage check covers `kapso experience`.
- Both reviewers' findings on this plan and on the pull request are
  answered below; the gate is green; the docs checks are green.

## Risks

| Risk | What is done |
|---|---|
| the bank gate's single-bank assumptions run deep (card names, the pull log, the exposure ladder) | change 4 keeps one bank the common case: `KAPSO_BANKS` with one entry reads as today; the index's grouping and `source` are additive |
| the scope coordinate change strands existing banks | there is nothing to migrate pre-release; `list` shows a bank whose cards carry `family:` coordinates as "scoped by a retired coordinate"; the owner's RelBench bank is re-learned when WP8 ports that harness |
| the knowledge pipeline's containers (Weaviate, Neo4j) are absent on the fresh machine | `add --repo` says which container and the line that starts it; the proof run covers `mine`, not an index; the index path is tested with the pipeline stubbed at its boundary |
| the Leeroopedia key on the fresh machine | not stored as a secret; loaded once on the development box; `add leeroopedia` on the machine must refuse with the variable name |
| the learn in the proof run costs the shared token an hour of crews | the token gate before it; the learn runs once; the second build is small |
| `--experience` on `learn` and `deploy` expected by the master | not added, with the reason in the Interface and a decision entry; the master's line corrected in this package's status row |

## Review

The sub-plan's review by Codex (`gpt-6-astra`, xhigh) and Claude Code
(`claude-opus-5`) is recorded here with each finding's answer before the
first change lands; the pull-request review follows the build.
