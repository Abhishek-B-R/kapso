---
name: kapso
description: Operate Kapso (PyPI leeroo-kapso), the long-running agents that optimize AI and Data systems, from a coding session — verify the install with kapso doctor, launch and follow a build campaign toward a scored goal, answer a campaign that is WAITING ON YOU, resume an interrupted run, learn from a finished campaign into the lesson bank, serve a build the experience it should start from (your bank, Leeroopedia, a team's bank, an ingested corpus), and deploy the winner. Use when the user mentions Kapso or kapso build, learn, experience, deploy, doctor, watch, inbox, or asks to build and verify something against a measurable metric (accuracy, latency, score) in a project where kapso is installed. Do not use for ordinary code edits, or for hand-tuning a metric when Kapso is neither installed nor asked for.
---

# Kapso

Kapso runs experiment campaigns: propose a candidate, implement it on its own git
branch, score it with the judge, keep the best, repeat. Everything below is 0.8.x.
Prefer the facts here and the docs links at the end over reading the package source;
the source is large and a session that greps it runs out of turns before answering.

## Facts that prevent the common mistakes

- Install with `pip install leeroo-kapso`. The PyPI package named `kapso` is an
  unrelated WhatsApp tool that shadows the `kapso` command. Python 3.10+.
- Every model call runs through a coding-agent CLI that must be logged in:
  `claude` (ideation, implementation, judging) and `codex` (research, utilities).
  There is no API-key fallback. `OPENAI_API_KEY` is optional and only ever
  embeds text: a corpus ingested with `kapso experience add`, and semantic search
  over past experiments once `models.embedding` is set in the config (off in the
  shipped config).
- `LEEROOPEDIA_API_KEY` in `.env` is the hosted knowledge base of ML and AI
  frameworks (nothing to install; a new account at
  https://app.leeroopedia.com/dashboard has $20 of free credit). A build reads it
  when it loads it: `--experience leeroopedia`. Without the key `doctor` shows the
  row as `[-- ]` and `kapso experience add leeroopedia` says where the key goes.
- Secrets come from `.env` in the directory you run from (`find_dotenv(usecwd=True)`);
  a shell export works only if it is actually exported. Config never holds secrets.
- All knobs live in one YAML. To change anything, copy the packaged file, edit, and
  pass it with `--config` / `Kapso(config=...)`. Never set Kapso behaviour through
  environment variables.
- Run `kapso doctor build` (or `kapso doctor learn|deploy|experience`) before any
  run. Every required row must read `[OK ]`; `[-- ]` rows are optional. Add
  `--models` to live-probe every configured model with one token each; a model
  the login cannot serve fails here in seconds instead of hours in. A usage cap on
  a model it can serve is not visible to the probe.
- A campaign takes tens of minutes to hours. Launch it with `--detach`: the
  command returns at once with the pid, the log, the status path and the
  `watch` line, and the run outlives your tool call on every host. Hand off in
  your reply right away: the brief you passed, the metric and target you assumed
  and that the user's own can replace them, the `kapso watch <campaign> --follow`
  command, and that `WAITING ON YOU` is a pause answered through `kapso inbox`.
  The status file appears within seconds (phase `setup` while the workspace is
  seeded and repo memory bootstrapped, which takes minutes), so do not poll the
  log or arm monitors unless asked. Never run `kapso build` without `--detach`
  from a tool call.
- A run that ends with `WAITING ON YOU` has paused, not failed (exit code 0).
  Do not restart it; reply through the inbox (below).
- A build is served exactly the experience it loads (`--experience`, the brief's
  `Experience` line, `load_experience()`), and nothing when it loads nothing.
  There is no serving switch in the config.

## Build: run a campaign

### The brief

The judge stops the campaign only when the objective reads as fully achieved, and
it scores every experiment from what the evaluation prints. So the brief has to
name a success metric and a number, and it helps to name the judge. Write it as a
file, `kapso-brief.md`, one field per line, indented lines continuing the field
above:

```
Objective    Raise the churn model's out-of-sample AUC above 0.85
             without changing the prediction contract.
Measured by  evaluation/evaluate.py, ROC AUC on the held-out rows
Baseline     0.797 (logistic regression)
Target       0.85
Rules
  - the evaluator is never modified
  - no fitting on the held-out rows
Budget       minutes=60 experiments=10
Experience   mine, leeroopedia
```

Only `Objective` is required; whatever the user gives goes in verbatim, and the
whole brief reaches the judge. `--goal "..."` is the one-line form of the same
thing. `Harness` names the domain layer the build runs with (a bundled name, a
directory, a git reference); `Experience` names what it is served.

First look for an evaluation the repo already has: a scoring script, a test
suite, a benchmark command. Then:

- The repo has one but the request names no metric or target: run it once for
  the baseline, write the brief with that metric and a target you propose, and
  tell the user in one line what you assumed and that their own success metric
  goes straight into the brief. Leave headroom below any ceiling you can see; a
  target the data cannot reach ends in the inbox, not in a result.
- The repo has none and the request names none: your whole reply is one
  question, one line, asking whether they have a script or command that
  scores this and what "good" means; nothing is launched, measured or
  written before the answer. A script they have goes in with `--evaluation`,
  protected. If they answer that they have none or do not know, launch with
  the best metric you can state in the brief and no `--evaluation`: the campaign
  builds its own evaluation in `kapso_evaluation/` from the brief, and the
  judge checks that it is fair. Never write an evaluator on the user's behalf,
  and never ask twice.
- Put rules in the brief, not methods. The judge enforces data rules and
  prohibitions ("do not modify evaluation/evaluate.py", "do not fit on
  data/test.csv") as invariants for the whole campaign, and would freeze a
  method preference the same way.

### Launch

```bash
kapso doctor build
kapso build \
  --brief kapso-brief.md \
  --repo . \
  --evaluation evaluation \
  --data data \
  --output ../churn-campaign \
  --budget-minutes 60 --budget-experiments 10 \
  --experience mine \
  --detach
kapso watch ../churn-campaign --follow
```

- `--detach` starts the campaign in a session of its own and prints its pid,
  the log (`../churn-campaign.log`) and the `watch` line; no `nohup`, `setsid`
  or `&` is needed, on any host. The launch is a tool call of its own: nothing
  chained in front of it.
- `--repo <path|github url>` seeds the campaign; a non-git directory is
  copied and committed as the baseline. The original is never modified. Every
  experiment lands on branch `generic_exp_N` inside `--output`, an empty
  directory outside the repo being seeded (a sibling), so the seed copy never
  contains the campaign.
- `--evaluation` is copied to `kapso_evaluation/` and integrity-protected: any
  candidate that edits it is rejected and unscored. Use it whenever the user has a
  judge. `--data` is copied to `kapso_datasets/`. The seed copy includes
  everything in the directory, `.env` included.
- Bound the run: `--budget-experiments` (default 10), `--budget-minutes` (durable
  across resumes), `--budget-usd` (best effort; codex sessions report no cost).
  A flag wins over the brief's `Budget` line.
- `--experience mine,leeroopedia` names what the build is served (below); it
  wins over the brief's `Experience` line, and each source is loaded before the
  fork, so a source that does not exist refuses here, not in the child's log.
  `--harness <ref>` names the domain layer the same way.
- `-a` picks the host every role without a `cli` of its own runs on
  (`claude_code` as packaged, `codex`, `gemini`, `openhands`, `oss_claude_code`);
  `--config <file>` layers an override file over the packaged config.
- The summary block ends `COMPLETED` with score and stop reason, or `WAITING ON YOU`.

Python, same thing:

```python
from kapso import Kapso, Brief, Budget, Solution
k = Kapso()
k.load_experience("mine")
solution = k.build(
    Brief.read("kapso-brief.md"), repo=".", evaluation="evaluation", data="data",
    output="./campaign", budget=Budget(minutes=60),
)
print(solution.explain())   # .score .goal_achieved .branch .campaign .experience .diff()
Solution.open("./campaign") # the same solution from any process, once the build returned
```

`build()` blocks for the whole campaign: from a tool call prefer the CLI with
`--detach`, or start the script in a session of its own.

## Inbox: the campaign is waiting on you

A session that needs something only a person can provide (a credential, access, a
file) records a request and the campaign pauses.

```bash
kapso inbox ./campaign                 # the open requests: key, hit, tried, fix, next
kapso inbox reply ./campaign 1 "added the key to .env" --detach
```

- The id may be omitted when one request is open; an empty note means done.
- The reply resumes the very session that asked. With `--detach` the note is
  checked here and the campaign resumes in a session of its own, so hand off
  with the `watch` line it prints; without it, the resume runs in the
  foreground of that command. Either form works from any directory.
- A credential-shaped reply is refused: put the value where `fix` says (usually
  `.env`) and reply with a note.

## Resume an interrupted campaign

```bash
kapso watch ../churn-campaign                  # DEAD (pid gone) or STALLED means it died
kapso build --output ../churn-campaign --resume --detach
```

A resume is a launch: `--detach` it the same way and hand off with the
`kapso watch … --follow` line it prints. Do it in the same turn you diagnose
the death in; a reply that only announces a resume leaves the campaign dead. Other `kapso build` processes on the machine belong
to other campaigns; never kill one. The checkpoint in `.kapso/run_state.json` carries
the brief and the search state; the launch record `.kapso/launch.json` carries
every flag of the launch, and a resume reads both, so pass only what you mean
to change (a bigger `--budget-minutes`, say). A bare resume is served the sources
the launch pinned, at the same heads. A resume that changes the host, the
evaluation, config, harness or experience is refused by name; start a new campaign in
a new output path instead. A campaign paused by the inbox resumes through
`kapso inbox reply`, not `--resume`.

## Learn: bank what a campaign taught

`learn()` mines one finished campaign into your bank, a local git repo of
evidence-priced cards. It runs crews for an hour or more and needs both CLIs.

```bash
kapso learn ./campaign                          # or a trajectory id
kapso learn ./campaign --harness ./harness      # when the campaign's record names none
```

```python
from kapso import Kapso
k = Kapso()
lesson = k.learn("./campaign")      # or learn(solution); a trajectory id also works
print(lesson.explain())             # cards created/updated, admitted, report paths
print(k.memory.explain())           # bank head, active cards
```

- The bank is created on first use at `learning.bank.local_path`
  (`~/.kapso/bank.git`), or by `kapso experience add mine`. Share it with
  `kapso experience share <git-url>` (create the repository yourself first,
  `gh repo create org/kapso-bank --private`); after that every `learn()` pushes
  and `kapso experience update` pulls the team's lessons.
- A build is served the bank when it loads it: `--experience mine`. Without that,
  banked cards have no effect on `build()`.
- Follow a learn with `kapso watch learning/status`.
- `kapso learn dev <import|mine|grade|update|develop|codify|ingest|gauntlet|behave>`
  are the learning system's own tools, for people working on the learning system,
  not the everyday path.

## Experience: what a build is served

A build is served exactly what it loads. `kapso experience` makes the sources
that must exist first, lists them, and shares your bank.

```bash
kapso experience add mine                                          # your bank, empty; learn() fills it
kapso experience add leeroopedia                                   # checks the key in .env
kapso experience add --repo https://github.com/org/repo --name org-repo   # a repository into an index (hours)
kapso experience add --research "gradient boosting for churn" --name churn-gbm   # the web researched, then ingested
kapso experience list                                              # mine, the hosted gate, banks you read, indexes
kapso experience share https://github.com/org/kapso-bank.git
kapso experience update                                            # pulls mine, re-fetches banks you read
kapso experience remove org-repo                                   # an index, or a bank you read
kapso build --experience mine,leeroopedia,org-repo --brief kapso-brief.md ...
```

- The forms: `mine` (your bank, the cards your harness's scope covers),
  `mine:all` (every card), `leeroopedia`, a bank path (`./team/bank.git`) or git
  reference (`acme/kapso-bank@v2`), an index name. A source that does not exist
  is refused with the `add` line that makes it; loading never ingests.
- Ingesting a repository or a question needs `kapso doctor experience` green:
  Weaviate on 8080 and Neo4j on 7687 (from a source checkout: `bash
  scripts/start_infra.sh`), `OPENAI_API_KEY` for the embeddings, both CLIs. It is
  a foreground command that can run for hours; the time scales with the material.
  Follow it with `kapso watch learning/status`. One index per build.
- The same sources reach the session you are in through `kapso-mcp`:
  `claude mcp add kapso -- kapso-mcp --experience mine` (`--harness <ref>` gives
  it the harness's scope).
- Python: `k.add_experience(repo=url, name="org-repo")`, `k.load_experience("mine")`,
  `k.share_experience(url)`, `k.update_experience()`, `k.remove_experience(name)`;
  `k.experience` lists what is loaded and `solution.experience` what a campaign
  was served, each source at its pinned head.

## Deploy

Deploy runs one session that adapts a copy of the solution to a target,
deploys it with the target's scripts, proves one call, and returns when the
engine has checked the result. It takes minutes (up to thirty, the
session's deadline). Run it in the foreground when your tool's timeout
allows; when it does not (Claude Code's Bash tool stops at ten minutes),
run it once in the background writing to a log and wait for the summary
to appear there, never a second time. The record is written when the
deploy starts, so `kapso deploy <campaign> --status` says what is
deploying even while the call runs or after a host call is cut.

```bash
kapso doctor deploy
kapso deploy ../churn-campaign --target local    # auto|local|docker|modal|bentoml|langgraph, or a harness target
kapso deploy ../churn-campaign --status           # every deployment of the campaign, with its state
kapso deploy ../churn-campaign --logs --number 1
kapso deploy ../churn-campaign --stop --number 1
```

The summary names the deployment's number, how `run()` calls it, the call
the session proved (the example of what it takes) and the next actions
pinned to that number. To call what was deployed, reopen that number from
Python:

```python
from kapso import Software
software = Software.open("../churn-campaign", 1)
print(software.proof["inputs"])                     # what run() takes
print(software.run({"tenure_months": 3, "monthly_spend": 92.0, "support_tickets": 4, "logins_per_week": 1.0, "plan": "basic"}))
software.stop()
```

A scheduled target (the trading example's `paper-trading`) runs on its own;
read `--logs`, and `run()` runs one cycle on demand. The original solution
is untouched: the deployment lives under `<campaign>/.kapso/deployments/<n>/`.
`--target auto` lets the session choose among the targets this machine can
serve and records why.

## Models and config

```bash
python -c "from kapso.kapso import DEFAULT_CONFIG_PATH; print(DEFAULT_CONFIG_PATH)"
cp "$(python -c 'from kapso.kapso import DEFAULT_CONFIG_PATH; print(DEFAULT_CONFIG_PATH)')" kapso-config.yaml
# edit, then:
kapso doctor learn --models --config kapso-config.yaml
```

Shipped models: campaigns on `claude-opus-5`, learning crews on `claude-fable-5`,
codex roles on `gpt-5.6-sol`. Swap a model by editing every occurrence in the block
you care about (`learning.*` for the crews, `modes.<MODE>.*` for campaigns). The
`timeout_minutes` caps were calibrated on the shipped models; tell the user a slower
model may need them raised, but change only what was asked.
`Kapso(config="kapso-config.yaml")` and `--config` on every CLI verb select
your file.

## When Kapso is the wrong tool

A one-file change with an obvious fix is faster by hand. Reach for a campaign when
there is a judge to beat, many candidates worth trying, and the user accepts an
unattended run of an hour or more on their coding-agent subscription. Say which you
are doing and why; never launch a campaign the user did not ask for.

## Docs, served as Markdown

- CLI reference: https://docs.leeroo.com/docs/reference/cli.md
- Python API: https://docs.leeroo.com/docs/reference/kapso-api.md
- Configuration: https://docs.leeroo.com/docs/reference/configuration.md
- Inbox: https://docs.leeroo.com/docs/build/inbox.md
- Resuming runs: https://docs.leeroo.com/docs/build/resume-and-budgets.md
- Evaluation integrity: https://docs.leeroo.com/docs/evolve/evaluation-integrity.md
- Trajectory learning: https://docs.leeroo.com/docs/learning/overview.md
- Experience: https://docs.leeroo.com/docs/experience.md
- Harnesses: https://docs.leeroo.com/docs/harnesses.md
- Deploy: https://docs.leeroo.com/docs/deploy/targets.md
- Index of every page: https://docs.leeroo.com/llms.txt

The whole site is also an MCP server:
`claude mcp add --transport http kapso-docs https://docs.leeroo.com/mcp`.
