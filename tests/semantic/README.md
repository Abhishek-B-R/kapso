# Semantic production tests

What this directory will hold, and the contracts its parts meet. The design
is `docs/plans/semantic-production-tests.md`; the build order is in
`docs/plans/redesign/MASTER.md` (WP9). Nothing here is collected by the
ordinary gate (`conftest.py` ignores every file), and nothing here runs on
the development machine: `scripts/redesign/fresh_machine.sh` provisions a
GCP machine, installs the package, runs, and deletes it.

```
tests/semantic/
├── README.md            this contract
├── conftest.py          keeps pytest out
├── personas/            one card per simulated user (below)
├── report.py            renders one run's record as the markdown report
└── reports/             the reports, one per run (gitignored except the ones cited in a sub-plan)
```

## Fixtures

The fixtures are the examples under `examples/`: one source, so a page
that quotes an example quotes something the suite ran. A fixture is a small
task an engineer could plausibly bring. Each directory has: a `README.md`
with the task (What you get, Run it, What to look at, Change it) and the
recorded result; `kapso-brief.md`; a deterministic generator for any data
(seeded, byte-identical, hashes in `MANIFEST.json`); `repo/`, the starting
repository; `evaluation/` when the fixture has an evaluator; `baseline.json`,
the shipped model's score with a noise figure, when one was measured.
Generated data is never committed.

| Fixture | Shows | State |
|---|---|---|
| `examples/churn-first-build` | tabular, evaluator present, baseline 0.797 AUC (SE 0.010) with 0.832 reachable by boosting alone | built (WP0, moved under the examples in WP1) |
| `examples/fraud-no-evaluator` | labelled data and a protocol, no evaluator | built (WP1), not yet run |
| `empty-wish` | a README and nothing else | WP9 |
| `trading-strategy` | the author's fixture | WP9 |
| `pipeline-dbt` | the third domain for the guide's test | WP9 |

The evaluator contract every fixture meets: one command from the workspace
root; the metric on its own line as the last line, `name: value`; a
`result.json` in the engine's shape; non-zero exit with a printed reason on
a malformed submission; deterministic given the submission; a `--fast` mode
whose number is marked not comparable; one cycle well under a minute.

## Personas

A persona card is YAML with: `name`, `role`, `expertise`, `knows` (what they
know about their repository and goal), `wants`, `patience` (questions before
answers turn terse), `answers` (how they reply), `pushes_back_when`. The
simulated user is a model from the other vendor than the host's, prompted
with the card and the fixture's README, driving the host CLI turn by turn.

## Runs and reports

A run record is JSON: `test` (S1 to S6), `host`, `machine`, `package`
(version and wheel sha256), `started`, `finished`, `steps` (each with
`name`, `messages`, `questions`, `minutes`, `longest_message_lines`,
`completed`, `artifacts`), `judge` (dimension to score), `transcripts`
(paths). `report.py` renders it against the budgets in
`docs/plans/kapso-plugin-skills.md` and writes pass or fail per step.
