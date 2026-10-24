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
| the unit | one directory per domain | one source: a bank, a hosted gate, an ingested index |
| bundled with the package | `predictive-modelling`, `relational-prediction`, `trading`, ... by name | nothing; experience is always yours or someone's |
| the reference | a bundled name, a local path, a git reference | a reserved name (`mine`, `leeroopedia`), a path or git reference to a bank, the name of an ingested index |
| local home | `~/.kapso/harnesses/<slug>@<rev>/` for fetched ones; a path is used in place | `~/.kapso/bank.git` (your bank), `~/.kapso/experience/banks/` (others' banks), `~/.kapso/experience/indexes/` (ingested indexes), `~/.kapso/trajectories/` (the raw material) |
| once per machine | `kapso harness add <ref>` | `kapso experience add ...` for what must be created: a bank early, a remote, an index |
| see what is there | `kapso harness list` | `kapso experience list` |
| per run | `load_harness(ref)` / `--harness` | `load_experience(ref)` / `--experience` |
| what load checks | schema, references, front matter, prerequisites | exists, reachable, readable; provenance known |
| what the run records | name, version, content hash | the reference, what it resolved to, its provenance, the pinned head or index id |
| sharing | commit the directory, or push its repository | `kapso experience share <git-url>` attaches a remote to your bank |
| scope | serves every task in its domain | a lesson serves the harness it was learned under, unless `scope="all"` |

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
a run), reads the prerequisites against this machine into the handle's
`missing` list, computes the content hash, and sets the object's harness.
`build` refuses to start while `missing` is not empty and names what is
missing and where each is read from. The run records `{name, version,
hash, ref}` in the launch record, the status file and the checkpoint. A
resume compares the hash and refuses a changed harness by name: the record
of a run is the record of one harness. Every lesson learned from the run
carries the same triple.

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

### The reference

`load_experience` takes one string, resolved by its form, exactly as a
harness reference is:

| Form | Example | What it is | Resolves to |
|---|---|---|---|
| reserved name | `mine` | your own bank, the one `learn()` writes | the path in the config's `learning.bank.local_path`, default `~/.kapso/bank.git` |
| reserved name | `leeroopedia` | the hosted gate | its URL, with the key read from `.env` |
| path | `./bank.git`, `~/team/bank.git` | a bank directory in the bank's git format | used in place |
| git reference | `acme/kapso-bank`, `git+https://…@main` | a bank repository you read but do not write | cloned under `~/.kapso/experience/banks/<slug>@<rev>` |
| index name | `org-x` | a corpus ingested earlier under that name | `~/.kapso/experience/indexes/org-x` |

Resolution order: the two reserved names, then a path that exists, then
anything with a slash or a scheme as a git reference, then an index name. A
string that matches none of these is an error that lists the forms.

There is no `team` source. A team bank is your bank with a remote attached
by `share`; `mine` pulls before it pins, and the intro says "measured by you
and your team". A bank you only read, someone else's, is the git-reference
form.

Loading never ingests. A repository, a paper or a research question becomes
an index first, by an action with a name, and the loader uses it by that
name afterwards. The loader only loads things that exist, so it never
surprises anyone with an hour of ingestion.

### Once per machine

```
kapso experience add mine                                        # creates the empty bank early (today: learn init-bank); not needed after a first learn()
kapso experience share https://github.com/acme/kapso-bank.git    # attaches the remote to your bank (today: kapso bank create | connect)
kapso experience add leeroopedia                                 # checks the key in .env, probes the gate once
kapso experience add --repo https://github.com/org/x --name org-x      # ingests into an index (today: learn_knowledge); needs the graph containers
kapso experience add --paper ./paper.pdf --name paper-x
kapso experience add --research "QLoRA memory optimizations" --name qlora-notes
kapso experience list
  mine         ~/.kapso/bank.git     head lr_2026-10-22_7   142 cards   remote acme/kapso-bank (in sync)
  leeroopedia  hosted                key present, reachable
  org-x        index                 ingested 2026-10-20, id 3f9a…
```

`add` makes a source exist and says what it needed: a key, running
containers, a name. It never serves anything by itself. In Python the
ingesting forms are `kapso.add_experience(repo=..., name=...)`,
`add_experience(paper=..., name=...)`, `add_experience(research=..., name=...)`,
each returning the index name.

### Per run

```python
kapso.load_experience("mine")                     # ~/.kapso/bank.git, pinned at its head, scoped to the loaded harness
kapso.load_experience("leeroopedia")              # the hosted gate
kapso.load_experience("acme/kapso-bank")          # a colleague's bank, read-only clone
kapso.load_experience("org-x")                    # the index ingested last week
kapso.load_experience("mine", scope="all")        # every card, not only this harness's
```

```
kapso build --experience mine,leeroopedia ...
```

Loading is the switch; there is no `serving.enabled`. A load resolves the
reference, confirms the source is reachable, pins it for the whole run (a
bank at its head, an index at its id), and appends it to the object's
sources in order. The handle says what happened:

```python
source = kapso.load_experience("mine")
source.kind        # "bank" | "hosted" | "index"
source.resolved    # "/home/me/.kapso/bank.git"
source.head        # "lr_2026-10-22_7"
source.provenance  # "measured by you"
```

Inside a run the sources are served through their tools in the modules the
engine serves (ideation and implementation; never the feedback judge), with
one intro the sessions read: "you are served 142 cards measured by you
under the trading harness, and Leeroopedia's pages reported by others". The
run records each source with its reference, what it resolved to, its
provenance and its pinned head or id, beside the harness triple.

Scope follows the harness: with `trading` loaded, `mine` serves the cards
learned under `trading`. `scope="all"` serves everything, and the intro says
so. A harness that must not be served, a benchmark under protocol, is run
without a load.

### What the engineer sees when something is wrong

- a reference that matches no form: the five forms above and `kapso experience list`
- a key missing: the variable name and that it belongs in `.env`
- containers down for an ingestion: which, and the line that starts them
- a bank behind its remote: the pull happens at load; a conflict is reported with the bank's own words

## 3. The plugin

| Command | Does |
|---|---|
| `/kapso:setup` | after the install, lists the bundled harnesses and offers `experience add mine`; offers Leeroopedia's plugin line when no key is present |
| `/kapso:harness add\|list\|update\|remove\|new\|check\|export` | section 1, plus the author's verbs |
| `/kapso:experience add\|list\|share` | section 2 |
| `/kapso:build` | asks which harness once when the project has no brief, lists what `experience list` shows, writes both lines into the brief, launches |

The host session itself, through `kapso-mcp`, serves the bank and the
indexes the same way a campaign does: the session names its sources on
connect, with the same provenance intro.

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
   `experience add` with a `--name`.
3. `load_harness` and `load_experience` on the facade with the reference
   grammars; `add_experience` for the ingesting forms; `--harness` and
   `--experience` on `build`, `deploy` and `learn`; the two brief lines.
4. The managed homes `~/.kapso/experience/banks/` and
   `~/.kapso/experience/indexes/` in place of `.index` files passed by path.
5. The provenance intro and the scope rule in the serving layer; the
   `serving.enabled` key removed.
6. The run record extended with the harness triple and the experience
   sources with their pinned heads.
