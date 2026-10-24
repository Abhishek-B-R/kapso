# WP1: `build`

2026-10-24. Branch `redesign/wp1-build`. Size M, four to five days after
WP0. Depends on WP0 (the CLI split and the handles module location).

## Scope

The verb and its handles: `Brief`, `Budget`, `Solution`, `Software`,
`Experience` in one module; `Kapso.build()` with today's `evolve()` body
behind the new signature; `kapso build` with `--goal-file`, `--detach` and
`--resume` as they are; `Solution.open(path)` on a campaign directory;
`explain()` and `diff()`; the rename of `evolve` in code, tests and the
shipped skill. The record (launch record, status file, checkpoint) carries
the brief and leaves room for the harness triple and the experience
sources.

**Not in scope.** Loading a harness (WP2: `Solution.harness` is `None`
until then). Experience (WP3: `Solution.experience` is an empty list).
The documentation pages (WP10's Start and Build slice, landed right after
this package). The entrance's proposed evaluation is the engine's existing
behaviour and does not change here.

## Interface

```python
@dataclass
class Brief:
    objective: str
    measured_by: str | None = None
    baseline: str | None = None
    target: str | None = None
    rules: list[str] = field(default_factory=list)
    budget: "Budget | None" = None
    harness: str | None = None          # a harness reference, resolved by WP2
    experience: list[str] = field(default_factory=list)   # experience references, resolved by WP3

    @classmethod
    def read(cls, path) -> "Brief": ...        # kapso-brief.md; the whole file, never clipped; an unknown field raises
    def write(self, path) -> None: ...

@dataclass
class Budget:
    minutes: int | None = None
    iterations: int | None = None
    dollars: float | None = None
    finalization_reserve_minutes: int | None = None   # defaults come from the config, never duplicated here

class Solution:
    branch: str; score: float | None; succeeded: bool
    evaluation: Evaluation          # version, provenance, log_path
    trace: Path                     # the campaign directory
    harness: HarnessRef | None      # name, version, hash, ref
    experience: list[ExperienceRef]
    @classmethod
    def open(cls, path) -> "Solution": ...   # from a campaign directory; a missing record raises
    def explain(self) -> str: ...
    def diff(self) -> str: ...

class Software: ...      # endpoint, artifacts, summary, target  (deploy's return; WP5 extends)
class Experience: ...    # bank head, cards created and updated, report paths, explain()  (learn's return)

def build(self, goal: str | Brief, *, evaluation=None, data=None, repo=None,
          output=None, budget: Budget | None = None, resume=False, on_status=None) -> Solution
```

The brief file format: one field per line, `Field    value`, in the order
of the dataclass, lists as indented dashes; the format the entrance design
already writes. Read in full (CLAUDE.md rule 6).

Consumed: WP0's `src/kapso/cli/` layout and the handles module path.

## Ownership

Edits: `src/kapso/handles.py` (new), the build section of
`src/kapso/kapso.py`, `src/kapso/cli/build.py`, `skills/*/kapso/SKILL.md`,
the tests below. Reads only: the orchestrator and the strategy (their
`solve` entry points are unchanged), `core/config.py` (budget defaults).

## Changes

1. `handles.py` with the five classes and the brief reader and writer;
   `tests/test_handles.py`.
2. `Kapso.build()` wrapping today's `evolve()` body: argument mapping,
   `Budget` to the budget config, `Brief` fields into the goal file the
   engine already consumes; `evolve()` deleted; `tests/test_build_facade.py`
   with the provider mocked, asserting the record a build writes equals
   the golden record `evolve` wrote for the same fixture.
3. `Solution` replacing `SolutionResult` everywhere it is returned or
   consumed (`deploy`, `learn`, the benchmark runners that construct it);
   `SolutionResult` deleted.
4. `Solution.open`, `explain`, `diff` over a recorded campaign fixture
   under `tests/fixtures/`; `tests/test_solution_open.py`.
5. `kapso build` in `src/kapso/cli/build.py`: `--goal`, `--goal-file`,
   `--evaluation`, `--data`, `--repo`, `--output`, `--budget-minutes`,
   `--iterations`, `--detach`, `--resume`, `--config`; `kapso evolve`
   deleted; `tests/test_cli_build.py` on the argument-to-facade mapping.
6. The record: launch record and status gain the brief; the checkpoint
   keeps its shape with two null fields for the harness triple and the
   sources; `tests/test_build_record.py`.
7. The skill: every `evolve` line in `skills/*/kapso/SKILL.md` becomes the
   `build` line with the brief; the one-skill-three-hosts parity test
   extended.
8. A grep test: no `evolve(` or `SolutionResult` left under `src/` and
   `tests/`; the 71 documentation mentions are WP10's and are listed in
   this file so none is forgotten.

## Tests

- Syntactic: the five files above. The brief round-trips, an unknown field
  raises, a 50-kilobyte objective is read whole; a `Budget` with a negative
  value raises; `Solution.open` on a directory without a record raises;
  the golden record matches; every CLI flag reaches the facade argument it
  names.
- Proof run: the churn fixture, five minutes, on the fresh machine, from
  Python in twelve lines and from the CLI in one, producing a `Solution`
  that `open()` reads back in a second process.
- Semantic hooks: S1 against today's `main` before this package starts
  (the baseline); the naming review by the judge model over the handle
  signatures and docstrings ("does the name say what it does"); S1 proper
  after WP10's Start and Build pages.

## Acceptance

- Gate green with the new tests in it; no `evolve` or `SolutionResult`
  under `src/` and `tests/`.
- The twelve-line Python flow and the one CLI line run on the fresh
  machine and produce a `Solution` the proof run archives.
- `Solution.open` works in a separate process on that campaign.
- The interface section of `docs/research/kapso-interfaces.md` rewritten
  against the code for `build` and the handles (decision 8, first part).
- Reviewed; the owner's go recorded below.

## Risks

- `SolutionResult` is consumed by `deploy`, `learn` and the benchmark
  runners: change 3 lists every consumer before touching the first.
- The brief parser must never clip (rule 6): the test reads a large file.
- The entrance's three cases rely on `--goal-file` and a campaign without
  `--eval-dir` building its evaluator: unchanged here, pinned by an
  existing test, and named so WP10's Build page says the right thing.

## Review

Pending.
