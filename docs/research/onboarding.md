# Onboarding a harness or an experience source

2026-10-24. Companion to `harness-design.md`, `harness-user-flow.md` and
`kapso-interfaces.md` §4. Onboarding is everything between "this exists
somewhere" and "this run uses it": fetching, checking, keeping a local copy,
loading it for a run, and recording what was loaded. The two nouns get the
same treatment, on purpose, so an engineer who has onboarded one knows how
to onboard the other.

## 0. The shape, shared by both

| | Harness | Experience |
|---|---|---|
| the unit | one directory per domain | one source: a bank, a hosted gate, an ingested corpus |
| bundled with the package | `predictive-modelling`, `relational-prediction`, `trading`, ... by name | nothing; experience is always yours or someone's |
| comes from | a bundled name, a local path, a git URL | `mine`, a team bank's git URL, `leeroopedia`, a repository, a paper, a research question |
| local home | `~/.kapso/harnesses/<slug>@<rev>/` for fetched ones; a path is used in place | `~/.kapso/bank.git` (the bank), `~/.kapso/experience/` (ingested indexes), `~/.kapso/trajectories/` (the raw material) |
| once per machine | `kapso harness add <ref>` | `kapso experience add <source>` |
| see what is there | `kapso harness list` | `kapso experience list` |
| per run | `load_harness(ref)` / `--harness` | `load_experience(source)` / `--experience` |
| what load checks | schema, references, front matter, prerequisites | reachable, readable, provenance known |
| what the run records | name, version, content hash | source, provenance, bank head or index id |
| sharing | commit the directory, or push its repository | `kapso experience share <git-url>` for the bank; hosted and imported sources are shared by their nature |
| scope | serves every task in its domain | a lesson serves the harness it was learned under, unless shared on purpose |

Neither is named in the Kapso config file. The config holds engine knobs;
what a run loads is said at the call, on the command line, or in the brief.

## 1. Harness

### References

Three forms, resolved in this order:

```
trading                                    a bundled harness, by name
./harness/trading                          a directory, used in place
git+https://github.com/acme/harnesses@v3#trading    a git repository, a revision, a subdirectory
acme/harnesses@v3#trading                  the same, GitHub shorthand
```

A git reference is fetched once into `~/.kapso/harnesses/<slug>@<rev>/` and
used from there; `rev` may be a tag, a branch or a sha, and a branch is
re-fetched by `kapso harness update`. A path is never copied: the engineer
edits it and the next run sees the edit, which is what an author wants and
what a content hash makes safe.

### Once per machine

```
kapso harness add acme/harnesses@v3#trading
  fetched  ~/.kapso/harnesses/acme-harnesses@v3/trading
  check    ok (7 skills, 2 agents, 2 servers, 6 hooks)
  needs    BROKER_API_KEY (env, for the broker server)       not set
  name     trading 0.3.0  sha256 9c1e…
```

`add` fetches, runs `check`, and reports prerequisites against this machine
without failing on them: a missing env variable is a fact the engineer will
fix in `.env`, not an error in the harness. `list` shows every bundled,
fetched and recently used local harness with its version and whether its
prerequisites are met now. `update` re-fetches a branch reference, re-runs
`check`, and prints the version change. `remove` deletes the fetched copy.
Bundled harnesses need no `add`: they are already there, under the package.

```
kapso harness list
  bundled    predictive-modelling 1.0.0   relational-prediction 1.0.0   trading 0.1.0
  fetched    trading 0.3.0   acme/harnesses@v3#trading   needs BROKER_API_KEY
  local      ./harness/trading 0.4.0-dev   (used 2026-10-24)
```

### Per run

```python
kapso.load_harness("acme/harnesses@v3#trading")
```

```
kapso build --harness acme/harnesses@v3#trading ...
```

Loading resolves the reference, runs `check` (a failing harness never starts
a run), verifies prerequisites and refuses to start with the missing names,
computes the content hash, and records `{name, version, hash, ref}` in the
launch record, the status file and the checkpoint. A resume compares the
hash and refuses a changed harness by name: the record of a run is the
record of one harness. Every lesson learned from the run carries the same
triple.

The brief carries the harness too, so a campaign launched from a brief
needs no flag:

```
Objective    ...
Harness      acme/harnesses@v3#trading
Experience   mine, leeroopedia
Measured by  ...
```

A flag on the command line wins over the brief. In the plugin, `/kapso:build`
writes the line from `kapso harness list` and the engineer's answer.

### What the engineer sees when something is wrong

- a reference that does not resolve: the forms above, and `kapso harness list`
- a harness that fails `check`: the failures, file by file; the run does not start
- a prerequisite missing: the names, where each is read from (`.env`, PATH, a GPU), and the harness's own words from its server skill when it has them
- a resume with a changed harness: both hashes and versions, and the two ways out (resume with the recorded one, or start a new run)

## 2. Experience

### Sources

| Source | `load_experience(...)` | What it is | Provenance shown to sessions |
|---|---|---|---|
| my own runs | `"mine"` | the local bank, `~/.kapso/bank.git`, fed by `learn()` | measured by you |
| a team's runs | `"team"` once attached, or a git URL | the same bank with a remote; `learn()` pushes, a load pulls | measured by your team |
| Leeroopedia | `"leeroopedia"` | the hosted gate; needs its key in `.env` | reported by others, curated |
| a repository or a paper | `repo="..."`, `paper="..."` | ingested into the knowledge graph under `~/.kapso/experience/` | reported by others, imported |
| a research question | `research="..."` | fresh findings, ingestible | reported by others, fresh |

### Once per machine

```
kapso experience add mine                     # creates ~/.kapso/bank.git if absent (today: learn init-bank)
kapso experience add https://github.com/acme/kapso-bank.git     # attaches the team remote (today: kapso bank connect)
kapso experience add leeroopedia              # checks the key in .env, probes the gate once
kapso experience add --repo https://github.com/org/x            # ingests; needs the graph containers (today: learn_knowledge)
kapso experience add --paper ./paper.pdf
kapso experience list
  mine         ~/.kapso/bank.git   head lr_2026-10-22_7   142 cards   remote acme/kapso-bank (in sync)
  leeroopedia  hosted              key present, reachable
  repo         org/x               ingested 2026-10-20, index 3f9a…
kapso experience share acme/kapso-bank        # creates the remote and attaches it (today: kapso bank create)
```

`add` makes a source usable and says what it needed: a key, running
containers, a remote. It never serves anything by itself. `mine` exists
after the first `learn()` whether or not it was added; `add mine` only
creates the empty bank early so a first run can declare it.

### Per run

```python
kapso.load_experience("mine")
kapso.load_experience("leeroopedia")
```

```
kapso build --experience mine,leeroopedia ...
```

Loading is the switch; there is no `serving.enabled`. A load pins the source
for the whole run (the bank at its head, an index at its id), writes the
provenance intro the sessions read ("you are served 142 cards measured by
you under the trading harness, and Leeroopedia's pages reported by others"),
and mounts the source's tools in the modules the engine serves (ideation and
implementation; never the feedback judge). The run records the source, its
provenance and its pinned head or id beside the harness triple.

Scope follows the harness: with `trading` loaded, `mine` serves the cards
learned under `trading`. `load_experience("mine", scope="all")` serves
everything, and the intro says so. A harness that must not be served, a
benchmark under protocol, is run without a load.

### What the engineer sees when something is wrong

- a source not added: the `add` line for it
- a key missing: the variable name and that it belongs in `.env`
- containers down for an ingestion: which, and the line that starts them
- a team bank behind its remote: the pull happens at load; a conflict is reported with the bank's own words

## 3. The plugin

| Command | Does |
|---|---|
| `/kapso:setup` | after the install, lists the bundled harnesses and offers `experience add mine`; offers Leeroopedia's plugin line when no key is present |
| `/kapso:harness add\|list\|update\|remove\|new\|check\|export` | section 1, plus the author's verbs |
| `/kapso:experience add\|list\|share` | section 2 |
| `/kapso:build` | asks which harness once when the project has no brief, lists what `experience list` shows, writes both lines into the brief, launches |

The host session itself, through `kapso-mcp`, serves the bank and the
knowledge graph the same way a campaign does: a load in `kapso-config.yaml`
is not the mechanism; the session names its sources on connect, with the
same provenance intro.

## 4. First runs, by what the engineer has

- **Nothing but the package.** Bundled harnesses by name, no experience.
  `kapso build --harness predictive-modelling ...` works on a fresh install
  once `doctor` is green.
- **One finished run.** `learn()` created `mine`. The next build in the same
  harness with `--experience mine` starts from what the first one taught.
- **A team.** `experience share` once; every teammate's `learn()` pushes
  and every load pulls.
- **A domain of their own.** The author's loop in `harness-user-flow.md`
  section 1, then `harness add` by path for themselves and by git URL for
  everyone else.

## 5. What this asks of the core

1. A harness store under `~/.kapso/harnesses/` with fetch, update and remove,
   and the reference grammar above.
2. `kapso harness add | list | update | remove` beside `new | check | export`;
   `kapso experience add | list | share` replacing `kapso bank create | connect`
   and `kapso learn init-bank`; `learn_knowledge` and `research` folded into
   `experience add` as the interfaces draft says.
3. `load_harness` and `load_experience` on the facade; `--harness` and
   `--experience` on `build`, `deploy` and `learn`; the two brief lines.
4. The managed index home `~/.kapso/experience/` in place of `.index` files
   passed by path.
5. The provenance intro and the scope rule in the serving layer; the
   `serving.enabled` key removed.
6. The run record extended with the harness triple and the experience
   sources with their pinned heads.
