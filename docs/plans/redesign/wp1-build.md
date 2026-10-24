# WP1: `build`

2026-10-24, revised after review. Branch `wp1-build`. Size M, four
to six days after WP0. Depends on WP0 (done: the CLI package, the fixture,
the fresh machine).

## Scope

The verb and its handles: `Brief`, `Budget`, `Solution` and its record on
disk, in one module; `Kapso.build()` with today's `evolve()` body behind the
new signature; `kapso build` with `--brief`, `--detach` and `--resume`;
`Solution.open(path)` reading the record a build writes; `explain()` and
`diff()`; the constructor's `config=` keyword; the rename of `evolve` in
code, tests, examples and the shipped skill, including the status file's
operation name and the doctor's verb. The record gains the brief and the
delivered candidate's identity.

**Not in scope.** Loading a harness (WP2: `Solution.harness` is `None`
until then). Experience (WP3: `Solution.experience` is an empty list;
`LessonResult` becomes `Experience` there, with `learn()`'s own changes).
Deploy's flags and targets (WP5; WP1 only makes `kapso deploy` take a
`Solution`). The documentation pages (WP10's Start and Build slice, landed
right after this package). The entrance's proposed evaluation is the
engine's existing behaviour and does not change here. Engine knobs that
`evolve()` takes today (`mode`, `coding_agent`, `context`,
`additional_context`, `serving_scope`, `iteration_evaluator`) stay as
keyword arguments of `build()` unchanged; WP2, WP3 and WP4 retire them.

## Interface

The names below are the ones that shipped, after the naming review (see
Review, "Naming review"): `experiments` and `usd` in the budget,
`campaign` for the directory, `goal_achieved`, `evaluator`,
`rejected_candidates`, `callback_metrics`, `knowledge_index`,
`experience_head`, `save()`, `build(brief=...)`, the `--budget-*` flag
family, and `kapso deploy <campaign>`.

```python
@dataclass
class Budget:
    minutes: float | None = None
    experiments: int | None = None
    usd: float | None = None                  # model spend
    reserve_minutes: float | None = None      # finalization reserve
    # __post_init__: every set value finite and positive, experiments an int,
    # reserve_minutes < minutes when both are set; None means "the config's".

@dataclass
class Brief:
    objective: str                            # required, may span lines, never clipped
    measured_by: str | None = None
    baseline: str | None = None
    target: str | None = None
    rules: list[str] = field(default_factory=list)
    budget: Budget | None = None
    harness: str | None = None                # a harness reference, stored verbatim; WP2 resolves
    experience: list[str] = field(default_factory=list)   # experience references, verbatim; WP3 resolves

    @classmethod
    def read(cls, path) -> "Brief": ...       # the grammar below; an unknown or repeated field raises
    def write(self, path) -> None: ...
    def render(self) -> str: ...              # the whole brief as the text the engine receives

@dataclass
class EvaluatorRef:                           # the registry head at delivery
    version: int
    evaluator_id: str
    provenance: str                           # provided | maintainer_built | derived_fast

@dataclass
class HarnessRef:   name: str; version: str; hash: str; source: str     # WP2 fills
@dataclass
class ExperienceRef: reference: str; kind: str; resolved: str; head: str | None; provenance: str   # WP3 fills

@dataclass
class Solution:
    brief: Brief
    campaign: Path              # the campaign directory: the workspace, checked out at the delivered branch, and the record under .kapso/
    branch: str | None          # the delivered candidate's branch; None when no candidate succeeded
    commit: str | None          # its commit at delivery; None with branch
    base_commit: str            # the workspace's seed commit, diff()'s base
    score: float | None         # the delivered candidate's authoritative measurement
    goal_achieved: bool         # the judge's verdict that the objective was met
    stopped_reason: str         # goal_achieved | max_iterations | budget_exhausted | waiting_for_user | ...
    stop_detail: str | None
    experiments: int            # this run
    experiments_total: int      # across every resume
    cost_usd: float
    requests: list[dict]        # open inbox requests when stopped_reason is waiting_for_user
    feedback: str | None        # the judge's last verdict, in full
    evaluator: EvaluatorRef | None   # None when no evaluator was registered (the agent built its own)
    harness: HarnessRef | None
    experience: list[ExperienceRef]
    rejected_candidates: int    # candidates rejected for touching the evaluator
    callback_metrics: dict[str, float]      # the caller's iteration_evaluator, delivered candidate
    callback_primary_metric: str | None
    knowledge_index: str | None             # until WP3 folds these two into experience
    experience_head: str | None

    record_path: Path                         # <campaign>/.kapso/solution.json
    def save(self) -> Path: ...               # build() writes it at return, every time it returns
    @classmethod
    def open(cls, path) -> "Solution": ...    # reads the record; raises when absent ("not finished; watch it")
    def explain(self) -> str: ...             # the summary block, from the fields
    def diff(self) -> str: ...                # git diff base_commit..commit in the campaign; "" when no candidate

class Software: today's `kapso.deployment.software.Software`, unchanged in WP1.

def build(self, brief: str | Brief | None = None, *, evaluation=None, data=None, repo=None,
          output=None, budget: Budget | None = None, resume=False, on_status=None,
          mode=None, coding_agent=None, context=None, additional_context="",
          serving_scope=None, iteration_evaluator=None,
          iteration_evaluator_failure_policy="record") -> Solution
```

Precedence, highest first: a `budget=` argument's set fields; the brief's
`Budget`; on a resume, the launch record; the config's defaults. `brief`
may be left out only on a resume, which takes it from the checkpoint, as
today; `reply()` resumes the same way. A `str` becomes a `Brief` with only
`objective`; a `Brief` is rendered whole into the engine's problem
description, so nothing the engineer wrote is lost on the way to the model.
`evaluation`, `data` and `repo` are call arguments, never brief fields.
Every path `build()` takes reaches the engine absolute (a URL for `repo`
goes to the cloner as it is).

`Kapso(config=...)` replaces `Kapso(config_path=...)`; the attribute stays
`config_path` internally. `kg_index` and `bank` stay until WP3.
`Budget.usd` is the model-spend budget (today's `cost_budget`); the
platform-credit budget stays a config value. The experiment default's
literal moves into the config in WP4, with the budget block it belongs to.

**The brief file**, `kapso-brief.md`:

```
Objective    Raise the churn model's out-of-sample AUC above 0.85
             without changing the prediction contract.
Measured by  kapso_evaluation/evaluate.py, ROC AUC on the held-out rows
Baseline     0.797 (logistic regression, 2026-10-24)
Target       0.85
Rules
  - the evaluator is never modified
  - no fitting on the held-out rows
Budget       minutes=480 experiments=10
Harness      predictive-modelling
Experience   mine, leeroopedia
```

- A field starts a line with its name (case-insensitive, one of the eight,
  matched as a whole word, so `Measured by` needs no special separator)
  followed by whitespace and the value; an indented line continues the
  field above, newline preserved; `Rules` and `Experience` take `- ` items on
  indented lines, and `Experience` also accepts one comma-separated line;
  `Budget` takes `name=value` tokens from `minutes`, `experiments`,
  `usd`, `reserve_minutes`; blank lines are ignored; nothing else is.
- Raises, with the line number: an unknown field name; a repeated field; a
  missing or blank `Objective`; an indented line before any field; a `- `
  item under a scalar field; a `Budget` token outside the four names or
  not a number; text that belongs to no field. Reference strings are kept
  verbatim (`acme/harnesses@v3#trading` has `@` and `#`).
- The whole file is read and rendered; no field has a length limit.
  `render()` is deterministic (the checkpoint fingerprints the goal, so a
  resume must render the same bytes), and `write()` emits exactly the
  grammar, so a brief round-trips.

**The record.** `build()` writes `.kapso/solution.json` (the `Solution`
as a dictionary, the brief inside) every time it returns, so a finished,
a paused and a budget-stopped campaign all have one; the launch record
gains the brief; the checkpoint keeps its shape. `open()` reads only that
file: a campaign that has not returned has no solution yet, and `open()`
says so and names `kapso watch`.

## Ownership

Edits: `src/kapso/handles.py` (new); `src/kapso/kapso.py` (the constructor
keyword, `evolve` to `build`, `reply`, `deploy`'s and `learn`'s parameter
types, the summary prints); `src/kapso/execution/solution.py` (deleted);
`src/kapso/cli/build.py` (from `evolve.py`), `cli/__init__.py` (the verb
tuple), `cli/common.py` (the summary), `cli/inbox.py` (texts), `cli/deploy.py`
(`Solution.open`), `cli/doctor.py` (the verb); `src/kapso/execution/observability.py`
(`BuildStatus`, operation `build`); `src/kapso/core/preflight.py` (the verb
and its requirements function); `src/kapso/deployment/base.py`,
`selector/agent.py`, `adapter/agent.py` (the type and `trace` in place of
`code_path`); `src/kapso/__init__.py`, `src/kapso/execution/__init__.py`
(exports); `src/kapso/knowledge_base/types.py`; `src/kapso/learning/harvest.py`,
`trajectory_store.py`, `lesson_result.py` (names in prose and the status
operation); `moltbook_bot/server.py`; `skills/*/kapso/SKILL.md` and
`skills/codex/kapso/agents/openai.yaml`; `examples/**/*.py` that call
`evolve` (nine files; the twelve-line rewrite is WP10's, here only the
call changes); the tests named below. The external skill lab at
`~/kapso-skill-lab` names `evolve` in fixtures, prompts and rubrics: WP7's
re-run updates it. Reads only: the orchestrator and the strategies, whose
`solve` entry points do not change.

## Changes

1. `handles.py`: `Budget`, `Brief` with `read`, `write`, `render`,
   `Evaluation`, `HarnessRef`, `ExperienceRef`, `Solution` with `write`,
   `open`, `explain`, `diff`. Test `tests/test_handles.py`.
2. `Kapso.__init__(config=...)`; `Kapso.build()` wrapping today's body:
   argument mapping, the brief rendered into the problem description,
   `Budget` to the budget arguments, the precedence above, the launch
   record with the brief, the `Solution` built from the solve result, the
   registry head, the workspace's head commit and seed commit, written to
   the record; `evolve()` deleted. Test `tests/test_build_facade.py`
   (provider mocked): the record a build writes has the pinned key list,
   and the values the fake orchestrator supplied land in it; the problem
   description contains the whole objective of a 50-kilobyte brief; a
   resume takes the brief from the checkpoint and the budgets from the
   record unless given, and keeps the brief's budget with the inbox off.
3. `Solution` replacing `SolutionResult` in every consumer listed under
   Ownership, `SolutionResult` deleted; `reply()` returns `Solution | None`.
   Tests: the deployment, inbox and return-result tests re-pointed.
4. `Solution.open`, `explain`, `diff` on three records that `build()`
   itself writes in the test (the orchestrator stubbed to return a
   completed, a waiting-for-the-person and a no-successful-candidate
   result), never hand-authored JSON. Test `tests/test_solution_open.py`,
   which also pins that `open()` on a directory without the record raises
   naming `kapso watch`.
5. `kapso build` in `cli/build.py`: `--goal/-g`, `--goal-file/-f` (plain
   text), `--brief` (the brief file), `--evaluation`, `--data`, `--repo`,
   `--output/-o`, `--budget-minutes`, `--budget-experiments`, `--budget-usd`,
   `--budget-reserve-minutes`, `--resume`, `--detach`, `--log`, `--config`,
   `--mode/-m`, `--coding-agent/-a`, `--kg-index`; `kapso evolve` gone.
   Test `tests/test_cli_build.py`: the test enumerates the parser's own
   actions, so a flag that stops reaching the facade fails it, not only
   the flags the test author remembered; `--brief` reaches `build()` as a
   `Brief`; a `--resume` without a goal reaches `build(goal=None,
   resume=True)`; `--detach` re-invokes with the child argv (the WP0 test,
   renamed).
6. `kapso deploy <campaign>` opens the record with `Solution.open` (the
   directory is positional, as `kapso watch` and `kapso inbox` take it);
   `--goal` removed (the brief is in the record).
7. The status file: `BuildStatus`, `OPERATION = "build"`; `watch` and the
   harvest read the new name. Test: the observability tests' fixtures.
8. Preflight: `VERBS` with `build`; `build_requirements`; `kapso doctor
   build`. Test: `tests/test_cli_doctor.py` and the preflight tests.
9. Prints and texts: `BUILDING:`, `Build complete`, the inbox's "resume
   with kapso build --output ... --resume", the detach label.
10. The skill: every `evolve` line in the three `SKILL.md` files and the
    Codex sidecar's default prompt become the `build` lines with the brief
    (no parity test exists; the grep test below is what covers `skills/`).
    The nine example scripts call `build`; the mining prompts' "evolve
    version" wording and the config's comments say `build`.
11. A grep test, `tests/test_no_evolve_left.py`: the word `evolve` in any
    case, `SolutionResult` and `config_path=` are absent under `src/`,
    `tests/`, `skills/`, `examples/`, `moltbook_bot/` and in
    `pyproject.toml`, except the two design-document filenames
    (`evolve-hub-design.md`, `evolve-observability-design.md`) that code
    comments cite, which WP10 renames with the documents. The
    documentation itself (`README.md`, `docs/`: 34 `.mdx` files, 254
    occurrences at `379b4e70`) is WP10's.

## Tests

- Syntactic: the files above. Negative cases for the brief grammar, one
  test per rule in the Interface; the 50-kilobyte objective asserted in
  the handler's problem description, not only in the parsed object; a
  `Budget` with a negative, non-finite or non-integer value raises; the
  record's key list pinned, with the delivered commit and the seed in it;
  a parametrized round trip from Python-built briefs (indented
  continuations, bullets, a tiny budget); three `open()` cases written by
  `build()`; every CLI flag mapped from the parser's own actions; the
  detach child argv; abbreviated flags refused; a log inside the output
  refused; a missing directory refused; the verb list in `--help`; the
  status operation; the doctor verb; the grep test.
- Proof run, on the fresh machine from the branch wheel, archived under
  `scripts/redesign/runs/wp1/` and cited here: the churn fixture staged
  (`generate.py`, then the fixture's `kapso-brief.md`), then

  ```
  kapso build --brief kapso-brief.md --evaluation evaluation --data data --repo repo \
              --output ../churn-build --budget-minutes 15 --budget-experiments 2
  ```

  producing `../churn-build/.kapso/solution.json`, then in a second process

  ```python
  from kapso import Kapso, Solution
  solution = Solution.open("../churn-build")
  print(solution.score, solution.branch, solution.stopped_reason)
  print(solution.diff()[:2000])
  ```

  and the twelve-line Python flow from `harness-design.md` section 8 with
  `load_harness` and `load_experience` left out, run end to end with
  `budget=Budget(minutes=15, experiments=2)`.
- Semantic hooks: the naming review, run with `scripts/redesign/review.sh`
  (Codex astra at xhigh and Claude Code opus-5) over `handles.py` and the
  `build()` signature, each reviewer asked, per public name and
  parameter, whether a cold engineer guesses its meaning from the name
  alone, yes or no with a proposed rename; every "no" is renamed or
  answered in this file. S1's baseline on today's `main` and S1 proper
  need WP9's driver and WP10's pages and run there.

## Acceptance

- Gate green with the new tests in it; `tests/test_no_evolve_left.py`
  passes.
- The proof run's two commands and the Python flow ran on the fresh
  machine from the wheel whose sha256 is recorded here, produced a
  `Solution`, and `open()` read it back in another process; the archive
  path is recorded here.
- `docs/research/kapso-interfaces.md` section 5 rewritten against the code
  for `build` and the handles (`redesign-status.md`, decided choice 8:
  the interfaces document is rewritten against the code, verb by verb).
- Both reviewers' findings answered below; the decisions log carries
  `--brief`, `trace`, the record file, `config=`, and deploy taking a
  `Solution`.

## Built

2026-10-24, branch `wp1-build`. What differs from the plan above, and why:

- `Solution` has no `resumed`, `status_path` or `experiment_logs`
  (decisions log); `explain()` is built from the fields alone.
- `learn()` writes flat keys into `final_report.json` in place of the old
  `metadata` dictionary (decisions log).
- A plain string goal is rendered as a brief too, so the checkpoint always
  holds the brief grammar and `kapso inbox` shows the objective's first
  line by parsing it (decisions log).
- The brief grammar keeps paragraph breaks and relative indentation inside
  a field (decisions log); the sample in the Interface parses and renders
  byte for byte.
- `tests/handles_support.py` holds the fake orchestrator, the git
  workspace and the facade stub the new tests share; the three `open()`
  cases are records `build()` writes with that fake, as planned.
- The grep test's word rule: `evolve` not preceded by a letter and not
  followed by a letter or a hyphen (so `evolved`, `evolves` and the two
  design-document filenames pass), with `docs/evolve/` as the one listed
  exemption; it also forbids `SolutionResult` and `Kapso(config_path`.
- The branch is `wp1-build`: git cannot hold `redesign/wp1-build` beside
  the `redesign` ref.
- The churn fixture moved to `examples/churn-first-build/` (the examples
  are the semantic suite's fixtures, one source) with its brief, a
  twelve-line `run.py` and the four-section README; `examples/fraud-no-evaluator/`
  is new (a protocol in `Measured by`, no evaluator; rules 0.09 PR-AUC,
  boosting 0.55 under the protocol). The five older examples got a
  `kapso-brief.md`, a `run.py` and the four-section README, and their
  `initial_repo/` became `repo/`; their evaluators stay inside the repo
  until WP2 re-bases them on harnesses.
- The docs slice (WP10, row 1): `docs/first-build.mdx` replaces the
  quickstart; the Build group (`docs/build/`: the brief, evaluation, run
  and watch, the inbox, review, resume and budgets); the brief format
  reference; the CLI and Python references rewritten for `build`; the
  Overview with the twelve lines; the old Evolve group regrouped as "How
  it works" in place, with its snippets on the new arguments (the
  condensation of those pages waits for the packages that change them);
  `scripts/check_snippets.py` keeps a quoted file and its page identical
  and runs in the docs workflow. "Kapso in your coding agent" is WP7's.

## Findings for later packages

- **Ideation dominates a small build.** On the shipped `GENERIC` config
  the ideation session runs twelve to fourteen minutes before the first
  candidate is implemented (second proof run, 2026-10-24: setup done in
  four seconds, the implementation folder created twelve minutes in, the
  Python-flow campaign still in `ideation` at fourteen minutes). A
  fifteen-minute campaign therefore delivers nothing, and "a first build
  in ten minutes" is not true today. WP4 (the config package) should give
  small briefs a faster path: a lighter ideation effort or fewer lanes
  for a one-file task, or a quick profile; the semantic suite's S1 should
  measure time-to-first-candidate.
- **The evaluation registry is empty without the maintainer.** `GENERIC`
  and `MINIMAL` have no `evaluation_maintainer` block, so `solution.evaluator`
  is `None` and a proposed evaluator is judged but not registered or
  protected file by file. WP4 decides whether the maintainer is on by
  default; until then the pages say what the shipped config does.
- **`done` precedes the record.** The orchestrator publishes the status
  file's terminal state inside `solve()`; the facade then checks out the
  deliverable and writes `.kapso/solution.json`. `kapso watch --follow`
  can return before `Solution.open` succeeds, by the seconds the checkout
  takes. WP6 (the record and the trace) should publish `done` after the
  record is written, and should save a record before the delivery steps
  that can raise.
- **A fresh machine needs the task's libraries.** `kapso doctor build`
  checks the engine's needs, not the task's; the churn example needs
  numpy, pandas and scikit-learn, which its README now installs. The
  harness package (WP2) carries an `environment` block for exactly this,
  and the doctor could report a harness's requirements.

## Risks

- `SolutionResult` has more consumers than the facade; the Ownership list
  is the inventory, and the grep test is the net.
- The brief parser must never clip (rule 6): the prompt-level test reads a
  large file through to the problem description.
- The status operation rename reaches the harvest and the trajectory
  store, which key on it; their tests run in the gate.
- A `Solution` is only as durable as its record; `save()` runs on every
  return path of `build()`, including the paused one.

## Review

Codex (astra, xhigh) read the first draft; its findings and what changed:

| Finding | Answer |
|---|---|
| `Solution` omitted the goal, stop reason, requests and cost that deployment, learning and the CLI use; `branch: str` cannot say "no candidate"; a branch alone does not identify measured code | the Interface now carries `brief`, `stopped_reason`, `stop_detail`, `requests`, `cost_usd`, `feedback`; `branch` and `commit` are `None` when nothing succeeded; `commit` and `base_commit` identify the code |
| `open()` had no reconstruction contract and no durable evaluation log; the result exists only after `solve()` returns | `build()` writes `.kapso/solution.json` on every return; `open()` reads that file only and raises before it exists; `score` is the delivered candidate's, as the facade computes it; `succeeded` stays the feedback's stop vote; `evaluation` is the registry head |
| a required `goal` breaks `--resume` and `reply()`; precedence among budgets undefined; `Kapso(config=...)` unowned | `goal` optional on a resume; precedence written; the constructor keyword is this package's |
| the brief grammar contradicted its examples | the grammar is written out with continuations, list items, the budget tokens, and every rejection; references are kept verbatim; the whole brief is rendered into the prompt |
| consumers not inventoried; `reply()` the likeliest miss; no benchmark constructors exist | the Ownership list names every consumer found, `reply()` included; the benchmark claim is dropped |
| `Software` and `Experience` were placeholders; `ExperienceRef` undefined | `Software` is today's class; `Experience` moves to WP3 with `LessonResult`; `ExperienceRef` has its fields |
| the rename grep misses preflight, the status operation, prints, the sidecar, the skill lab, the detach label | all listed as changes 7 to 10; the lab is WP7's |
| round-trip and mocked tests can pass while broken | the prompt-level test, the resume test, the three `open()` fixtures and the record golden modulo new keys |
| acceptance not reproducible | the commands, the fixture, the archive path and the baseline commit are named |

Claude Code (opus-5) read the same draft; where a finding repeats one of
Codex's the answer above stands, and the rest:

| Finding | Answer |
|---|---|
| `succeeded: bool` collapses achieved, budget-stopped and waiting-for-the-person; the summary printer and the inbox branch on the stop reason and the requests | `stopped_reason` and `requests` are fields; `succeeded` keeps today's meaning (the feedback's stop vote) |
| `branch` and `evaluation` typed as always present; the registry is legitimately empty | both `None`-able, with the meaning written beside them |
| the launch record is written only with the inbox on, so a brief kept there is not durable; `best_branch` and the delivered score exist only in memory; `status.json`'s best score is a projection, not the deliverable | the record file carries the brief and the delivered candidate; `open()` never re-derives selection |
| the goal is fingerprinted by the checkpoint, so the renderer must be byte-stable; `write()` must not destroy text outside the grammar | `render()` is deterministic; the grammar admits no text outside fields, so there is nothing to lose, and a parse-render-parse round trip is a test |
| `Measured by` holds a space, so one space cannot delimit | field names are matched as whole words from the known eight |
| the `final_report.json` shape is an on-disk consumer (the trajectory store, the RelBench handler) | kept, fed from the `Solution`'s fields; its keys do not change in WP1 |
| the grep test cannot see the status operation, the doctor verb, the banners, the mining prompts, the config comments, the layout test's verb list, nor `skills/`, `examples/`, the README | changes 7 to 11 name each; the grep test covers `skills/`, `examples/` and `moltbook_bot/`; the README and `docs/` are WP10's |
| a strict "no `evolve` under `src/`" is unreachable while comments cite `evolve-hub-design.md` | the two design-document filenames are the grep test's only exceptions |
| the CLI test cannot catch dropped flags; the parity test does not exist; a hand-authored `open()` fixture proves little | the CLI test enumerates the parser's actions; the parity claim is withdrawn; the three `open()` cases are records `build()` writes |
| "twelve-line flow", "decision 8", the judge review and the 71 documentation files are not checkable | the flow and the commands are written in Tests; the decision is named by its document; the naming review names its reviewers and criterion; the count is corrected (254 occurrences in 34 files) |
| `Software` exists already; `Experience` collides with the experience-source handle; `Evaluation`, `HarnessRef`, `ExperienceRef` undefined; the package's lazy exports not owned | `Software` is that class; the collision is logged for WP3; the three types are defined; `src/kapso/__init__.py` is in Ownership |
| four homes for the budget without precedence; the iteration default is a literal; `dollars` could mean platform credits; brief-versus-`load_harness` precedence unstated | precedence written; the literal moves with WP4's budget block; `dollars` is model spend; harness precedence is WP2's, logged |
| WP1 answers the interfaces document's open question (is `Brief` the API object or a CLI-only file?) without logging it | logged in the decisions file: it is both, one grammar |

### Naming review

After the build, both reviewers read `handles.py`, the facade, the CLI,
the churn example and the Build pages and judged every public name (brief
`scripts/redesign/review.sh`, 2026-10-24). Taken, because both said so or
one said so and the argument held:

| Was | Is | Why |
|---|---|---|
| `Budget.iterations`, `Solution.iterations`, `cumulative_iterations`, `--iterations`, brief token `iterations=` | `experiments`, `experiments_total`, `--budget-experiments`, `experiments=` | every string a person reads said experiments; the code alone said iterations |
| `Budget.dollars`, `--budget-dollars`, token `dollars=` | `usd`, `--budget-usd`, `usd=` | matches `cost_usd`; one word for money |
| `--reserve-minutes` | `--budget-reserve-minutes` | the four budget flags are one family a person can tab through |
| `Solution.trace` | `Solution.campaign` | "trace" promised a log; it is the directory you `cd` into, the one `watch`, `inbox` and `deploy` take |
| `succeeded` | `goal_achieved` | read as "ran without error"; it is the judge's verdict, and matches the stop reason's value and `explain()`'s label |
| `Evaluation`, `Solution.evaluation` | `EvaluatorRef`, `Solution.evaluator` | "evaluation" was spent on the directory, the stamp and the score; the stamp is the evaluator's identity |
| `invalid_evaluations` | `rejected_candidates` | it counts candidates |
| `external_metrics`, `external_primary_metric` | `callback_metrics`, `callback_primary_metric` | "external" was the engine's point of view; they come from the caller's `iteration_evaluator` |
| `kg_index`, `bank_head_served` | `knowledge_index`, `experience_head` | an unexpanded abbreviation and three internal words, on the public record |
| `Solution.write()` | `save()` | `Brief.write(path)` takes a destination and this one refused one |
| `build(goal=...)` | `build(brief=...)` | the first thing every page passes is a `Brief`; a string stays accepted |
| `HarnessRef.ref` | `HarnessRef.source` | the class suffix repeated with another meaning |
| `kapso deploy --solution-path DIR` | `kapso deploy DIR` | the same directory `watch` and `inbox` take positionally |
| `--output build` in the examples | `--output campaign` | the word `build` was the verb, a doctor argument, a directory and a watch target in four consecutive lines |

Kept, with the reason: `Harness` and `Experience` (the owner's words for
the two layers; `Domain` and `Lessons` were proposed); `Solution` (the
design's noun; `BuildResult` was proposed); `stopped_reason` (the status
file and the checkpoint say it, and `kapso watch --json` is public too;
WP6 may rename both together); `requests` (the inbox's vocabulary
throughout); `feedback` (the engine's word for the judge's text);
`explain()` and `open()` (consistent with `memory.explain()` and
`LessonResult.explain()`); `Kapso(config=)` (its siblings `kg_index=` and
`bank=` are paths without a suffix); `--goal-file` beside `--brief` (a
plain prose file would need every line indented to pass as a brief);
`reserve_minutes` as the field name; `ExperienceRef`'s fields (WP3's).

The first-build stumbles both reviewers found were fixed: the example's
output directory is `campaign/`; the README and the page say `run.py` and
the CLI line build into the same directory, so run one or the other; the
`--evaluation evaluation` to `kapso_evaluation/` naming is explained where
the command is; `run.py` says it runs from the example directory after
`generate.py`; the deploy-and-learn snippet binds `kapso` and imports what
it uses.

### Pull-request review

Both reviewers read the branch against this plan (brief
`scripts/redesign/review.sh`, 2026-10-24; Claude Code read it at
`5e770f96`, Codex at `da3a6bb2`). Findings and what was done:

| Finding | Answer |
|---|---|
| five of the six Build pages were untracked: a bare `build/` rule in `.gitignore` matched `docs/build/`, and `docs.json` listed pages that were not in the repository (Claude, highest) | the rule is `/build/`; the pages are committed; `mint validate` and `broken-links` rerun |
| a Python-built brief whose continuation lines are indented, or holds a bullet, or a budget that renders as `1e-05`, does not survive `parse(render())`, so a bare resume dies on the goal fingerprint (both, highest) | `Brief` normalizes on construction (first line stripped, the rest dedented together); a bullet under a text field is text; numbers render in plain digits; a parametrized round-trip test from Python-built briefs pins it |
| a resume with the inbox off lost the brief's budget: budgets merged before the checkpoint's brief was read, and the launch record existed only with the inbox on (Codex, highest) | the checkpoint's brief is read before the merge; the launch record is written on every fresh campaign and carries the brief; registration alone stays conditional on the inbox |
| `kapso inbox` tracebacked on a campaign whose checkpoint goal is not brief grammar, a benchmark runner's (Claude) | the goal line is the first line, with an `Objective` name stripped when present; no parsing |
| the evaluation pages and the fraud example promised a registry and protection the shipped config never produces: the maintainer runs only with an `evaluation_maintainer` block (both) | the pages say what the shipped config does and when the registry exists; `solution.evaluator` documented as `None` without the maintainer; the fraud example's claims rewritten |
| a missing `data` directory was swallowed by the handler, launching a dataless campaign (Claude) | `build()` refuses a missing evaluation, data or local repo directory, by name |
| the temporary workspace with serving on was still relative (Claude) | resolved |
| deployment copied the current tree without checking the recorded commit (Codex) | `deploy()` refuses a solution with no candidate and a workspace not checked out at the delivered commit, naming the checkout command |
| `--det` relaunched the detached child forever; a `--log` inside `--output` made the fresh directory non-empty (Codex) | `allow_abbrev=False` on build, inbox and deploy; a log inside the output is refused before the child starts |
| three summary renderings disagreed (Codex); `COMPLETED` hid "no candidate" and the stop detail | the facade's completion block and the CLI summary print `solution.explain()`; the labels align at one column |
| `_validate_resume_workspace`, `_clone_github_repo`, `_search_workflow_repo` kept local imports and exception handling; a failed clone started an empty campaign (both) | imports at the top; a failed clone or workflow search propagates |
| `.kapso/solution.json` was not in the workspace's ignore list (Claude) | added |
| `schema_version` stayed 1 across the key rename; `request.get("key", "")` substituted for a required field; the record's `campaign` key was unused and untrustworthy after a move (Claude) | schema 2; `request["key"]`; the key dropped |
| `EvaluatorRef`, `HarnessRef`, `ExperienceRef`, `BriefError` were not exported (Claude) | exported |
| `kapso deploy` had no `--config` (Claude) | added |
| the examples' "Run it" blocks omitted numpy, pandas and scikit-learn; the churn README cited a recorded result that did not exist; the detached flow's summary block goes to the log, not to `watch` (both) | the install line is in the block; the recorded-result paragraph says "not recorded yet"; the README says where the block goes |
| `tests/test_solve_result.py` proved nothing (Claude) | deleted |
| grammar errors without a line number (Codex) | every `BriefError` carries the line of the field or token it is about |
| the plan's Tests bullet and Change 2 still promised a golden-record comparison; the Interface's `RECORD` constant did not exist (both) | both corrected below and in the Interface |
| "done" in the status file precedes the record by the checkout and the write (Codex); a failed final checkout leaves no record (Claude) | `open()`'s message covers a build that just ended and one that stopped before delivering; publishing `done` after the record is WP6's, with the record's lifecycle |
| the lazy export map in `kapso/__init__.py` is a function-local import (Codex) | kept: it is the documented cold-start fix for the MCP server (8 seconds otherwise); the handles join the same map |
| `DEFAULT_MAX_ITERATIONS` is a literal (Claude) | WP4's, as the plan says; renamed with the budget block then |
