# Examples

Every example is a task: a brief (`kapso-brief.md`), a starting repository
(`repo/`), the data or how to get it, and `run.py`, the same build the one
command runs. The three newest also carry a seeded data generator and a
protected evaluator (`evaluation/`); the five older ones keep their
evaluator inside the repository, where the judge protects it by rule, until
the harness work moves them. `harnesses/` holds the harness the trading
example builds on. Install Kapso and log the coding-agent CLIs in first
(`kapso doctor build` must pass), then run from the example's directory.

| Example | Minutes | What it shows | The one command |
|---|---|---|---|
| [churn-first-build](churn-first-build/README.md) | 45 | your first build: an evaluator present, a baseline, a target, the record | `kapso build --brief kapso-brief.md --evaluation evaluation --data data --repo repo --output campaign --detach` |
| [fraud-no-evaluator](fraud-no-evaluator/README.md) | 45 | no evaluator: the campaign builds one from the brief's protocol, then protects it | `kapso build --brief kapso-brief.md --data data --repo repo --output campaign --detach` |
| [pipeline-dbt](pipeline-dbt/README.md) | 30 | a dbt pipeline on DuckDB whose exports carry defects: the data contract made to hold at the staging layer; the third domain a harness author writes for | `kapso build --brief kapso-brief.md --evaluation evaluation --data data --repo repo --output campaign --detach` |
| [trading](trading/README.md) | 75 | a harness on the build: a setup session, pages and hooks in every session, verification per attempt | `kapso build --brief kapso-brief.md --evaluation evaluation --data data --repo repo --output campaign --detach` |
| [ml_model_development](ml_model_development/README.md) | 45 | a Kaggle tabular model, and the full loop (research, learn, build again) | `kapso build --brief kapso-brief.md --repo repo --output campaign --detach` |
| [prompt_engineering](prompt_engineering/README.md) | 60 | the prompt as the thing under test, scored on AIME problems | `kapso build --brief kapso-brief.md --repo repo --output campaign --detach` |
| [agentic_scaffold](agentic_scaffold/README.md) | 60 | a vision-language extractor, scored against ground-truth tables | `kapso build --brief kapso-brief.md --repo repo --output campaign --detach` |
| [pytorch_optimization](pytorch_optimization/README.md) | 60, CUDA | a faster module under a numerical tolerance | `kapso build --brief kapso-brief.md --repo repo --output campaign --detach` |
| [cuda_optimization](cuda_optimization/README.md) | 90, CUDA | multi-head attention, flash attention or Triton | `kapso build --brief kapso-brief.md --repo repo --output campaign --detach` |

Each `run.py` is under twelve lines: read the brief, build, print the
result. The five older drivers ran to eighty lines each; the difference is
the interface, not the examples.

The examples are also the fixtures of the semantic production tests
(`tests/semantic/README.md`): the same directories run on a fresh machine
from the released package, so a page that quotes one quotes something that
ran.
