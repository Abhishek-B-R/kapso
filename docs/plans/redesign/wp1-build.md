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

```python
@dataclass
class Budget:
    minutes: float | None = None
    iterations: int | None = None
    dollars: float | None = None
    reserve_minutes: float | None = None      # finalization reserve
    # __post_init__: every set value finite and positive, iterations an int,
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
class Evaluation:                             # the registry head at delivery
    version: int
    evaluator_id: str
    provenance: str                           # provided | maintainer_built | derived_fast

@dataclass
class HarnessRef:   name: str; version: str; hash: str; ref: str        # WP2 fills
@dataclass
class ExperienceRef: reference: str; kind: str; resolved: str; head: str | None; provenance: str   # WP3 fills

@dataclass
class Solution:
    brief: Brief
    trace: Path                 # the campaign directory: the workspace, checked out at the delivered branch, and the record under .kapso/
    branch: str | None          # the delivered candidate's branch; None when no candidate succeeded
    commit: str | None          # its commit at delivery; None with branch
    base_commit: str            # the workspace's seed commit, diff()'s base
    score: float | None         # the delivered candidate's authoritative measurement
    succeeded: bool             # the feedback's stop vote: the goal was met
    stopped_reason: str         # goal_achieved | max_iterations | budget_exhausted | waiting_for_user | ...
    stop_detail: str | None
    iterations: int
    cumulative_iterations: int
    cost_usd: float
    requests: list[dict]        # open inbox requests when stopped_reason is waiting_for_user
    feedback: str | None        # the last feedback's text
    evaluation: Evaluation | None   # None when no evaluator was registered (the agent built its own)
    harness: HarnessRef | None
    experience: list[ExperienceRef]
    resumed: bool
    invalid_evaluations: int
    external_metrics: dict[str, float]
    external_primary_metric: str | None
    kg_index: str | None        # until WP3 folds these two into experience
    bank_head_served: str | None

    RECORD = ".kapso/solution.json"
    def write(self) -> Path: ...              # build() writes it at return, every time it returns
    @classmethod
    def open(cls, path) -> "Solution": ...    # reads the record; raises when absent ("not finished; watch it")
    def explain(self) -> str: ...             # the summary block, from the fields and the experiment history
    def diff(self) -> str: ...                # git diff base_commit..commit in trace; "" when no candidate

class Software: today's `kapso.deployment.software.Software`, unchanged in WP1.

def build(self, goal: str | Brief | None = None, *, evaluation=None, data=None, repo=None,
          output=None, budget: Budget | None = None, resume=False, on_status=None,
          mode=None, coding_agent=None, context=None, additional_context="",
          serving_scope=None, iteration_evaluator=None,
          iteration_evaluator_failure_policy="record") -> Solution
```

Precedence, highest first: a `budget=` argument's set fields; the brief's
`Budget`; on a resume, the launch record; the config's defaults. `goal` may
be left out only on a resume, which takes it from the checkpoint, as today;
`reply()` resumes the same way. A `str` goal becomes a `Brief` with only
`objective`; a `Brief` is rendered whole into the engine's problem
description, so nothing the engineer wrote is lost on the way to the model.
`evaluation`, `data` and `repo` are call arguments, never brief fields.

`Kapso(config=...)` replaces `Kapso(config_path=...)`; the attribute stays
`config_path` internally. `kg_index` and `bank` stay until WP3.
`Budget.dollars` is the model-spend budget (today's `cost_budget`); the
platform-credit budget stays a config value. The iteration default's
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
Budget       minutes=480 iterations=10
Harness      predictive-modelling
Experience   mine, leeroopedia
```

- A field starts a line with its name (case-insensitive, one of the eight,
  matched as a whole word, so `Measured by` needs no special separator)
  followed by whitespace and the value; an indented line continues the
  field above, newline preserved; `Rules` and `Experience` take `- ` items on
  indented lines, and `Experience` also accepts one comma-separated line;
  `Budget` takes `name=value` tokens from `minutes`, `iterations`,
  `dollars`, `reserve_minutes`; blank lines are ignored; nothing else is.
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
   (provider mocked): the record a build writes equals the golden record
   `evolve` wrote for the same fixture apart from the new keys; the
   problem description contains the whole objective of a 50-kilobyte
   brief; a resume takes the goal from the checkpoint and the budgets from
   the record unless given.
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
   `--output/-o`, `--budget-minutes`, `--budget-dollars`, `--reserve-minutes`,
   `--iterations/-i`, `--resume`, `--detach`, `--log`, `--config`,
   `--mode/-m`, `--coding-agent/-a`, `--kg-index`; `kapso evolve` gone.
   Test `tests/test_cli_build.py`: the test enumerates the parser's own
   actions, so a flag that stops reaching the facade fails it, not only
   the flags the test author remembered; `--brief` reaches `build()` as a
   `Brief`; a `--resume` without a goal reaches `build(goal=None,
   resume=True)`; `--detach` re-invokes with the child argv (the WP0 test,
   renamed).
6. `kapso deploy --solution-path` opens the record with `Solution.open`;
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
  record golden compared modulo the new keys; three `open()` fixtures;
  every CLI flag mapped; the detach child argv; the verb list in `--help`;
  the status operation; the doctor verb; the grep test.
- Proof run, on the fresh machine from the branch wheel, archived under
  `scripts/redesign/runs/wp1/` and cited here: the churn fixture staged
  (`generate.py`, then the fixture's `kapso-brief.md`), then

  ```
  kapso build --brief kapso-brief.md --evaluation evaluation --data data --repo repo \
              --output ../churn-build --budget-minutes 5 --iterations 2
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
  `budget=Budget(minutes=5, iterations=2)`.
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
- `tests/semantic/fixtures/churn-with-evaluator/kapso-brief.md` is the
  fixture's brief (five minutes, two iterations); the fixture README shows
  the build line.

## Risks

- `SolutionResult` has more consumers than the facade; the Ownership list
  is the inventory, and the grep test is the net.
- The brief parser must never clip (rule 6): the prompt-level test reads a
  large file through to the problem description.
- The status operation rename reaches the harvest and the trajectory
  store, which key on it; their tests run in the gate.
- A `Solution` is only as durable as its record; `write()` runs on every
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
