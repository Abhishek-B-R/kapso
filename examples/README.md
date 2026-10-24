# Examples

Every example is a task: a brief (`kapso-brief.md`), a starting repository
(`repo/`), the data or how to get it, and `run.py`, the same build the one
command runs. The two newest also carry a seeded data generator and a
protected evaluator (`evaluation/`); the five older ones keep their
evaluator inside the repository, where the judge protects it by rule, until
the harness work moves them. Install Kapso and log the coding-agent CLIs in
first (`kapso doctor build` must pass), then run from the example's directory.

| Example | Minutes | What it shows | The one command |
|---|---|---|---|
| [churn-first-build](churn-first-build/README.md) | 10 | your first build: an evaluator present, a baseline, a target, the record | `kapso build --brief kapso-brief.md --evaluation evaluation --data data --repo repo --output build --detach` |
| [fraud-no-evaluator](fraud-no-evaluator/README.md) | 15 | no evaluator: the campaign builds one from the brief's protocol, then protects it | `kapso build --brief kapso-brief.md --data data --repo repo --output build --detach` |
| [ml_model_development](ml_model_development/README.md) | 45 | a Kaggle tabular model, and the full loop (research, learn, build again) | `kapso build --brief kapso-brief.md --repo repo --output build --detach` |
| [prompt_engineering](prompt_engineering/README.md) | 60 | the prompt as the thing under test, scored on AIME problems | `kapso build --brief kapso-brief.md --repo repo --output build --detach` |
| [agentic_scaffold](agentic_scaffold/README.md) | 60 | a vision-language extractor, scored against ground-truth tables | `kapso build --brief kapso-brief.md --repo repo --output build --detach` |
| [pytorch_optimization](pytorch_optimization/README.md) | 60, CUDA | a faster module under a numerical tolerance | `kapso build --brief kapso-brief.md --repo repo --output build --detach` |
| [cuda_optimization](cuda_optimization/README.md) | 90, CUDA | multi-head attention, flash attention or Triton | `kapso build --brief kapso-brief.md --repo repo --output build --detach` |

Each `run.py` is under twelve lines: read the brief, build, print the
result. The five older drivers ran to eighty lines each; the difference is
the interface, not the examples.

The examples are also the fixtures of the semantic production tests
(`tests/semantic/README.md`): the same directories run on a fresh machine
from the released package, so a page that quotes one quotes something that
ran.
