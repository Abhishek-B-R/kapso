# MLE-Bench Integration

Rendered guide: [docs.leeroo.com/docs/benchmarks/mle-bench](https://docs.leeroo.com/docs/benchmarks/mle-bench) · Kapso by Leeroo: [github.com/Leeroo-AI/kapso](https://github.com/Leeroo-AI/kapso) · `pip install leeroo-kapso`

This module provides integration with [MLE-Bench](https://github.com/openai/mle-bench), OpenAI's benchmark for evaluating ML agents on Kaggle competitions.

Kapso achieved **#1 among open-source systems** on this benchmark. These results were submitted as an [official submission to MLE-Bench](https://github.com/openai/mle-bench/pull/107).

![MLE-Bench Results](../../docs/images/mle-bench.png)

## How it runs

The runner launches `build()` with the bundled `predictive-modelling` harness. The Brief
carries the competition's facts (its published description, the prepared data's layout,
the submission contract, the held-out protocol, the caps, the packages the environment
refuses); the harness carries the discipline (the task-type playbooks, the validation
protocol, the EDA discipline, the hub fetch, ensembling); the provided grader
(`data/generic_eval/grader.py`), registered by the evaluation maintainer, runs every
candidate's `main.py` (debug mode as the gate, then full mode), validates its
`final_submission.csv` with the competition's own validator and reads the held-out score
the program reports in `<score>` tags: the score of record, oriented so that higher is
better. The official grade on the private answers is computed once, after the campaign,
on the delivered candidate, and written to `final_report.json` under the competition's
archive root (`tmp/mle/<competition>/`, the `benchmark.work_root` key of `config.yaml`).

## Prerequisites

1. **Core Kapso installed** (from the repository root): `pip install -e .`
2. **MLE-Bench** (needs git LFS):
   ```bash
   git clone https://github.com/openai/mle-bench.git
   cd mle-bench && git lfs install && git lfs fetch --all && git lfs pull && pip install -e . && cd ..
   ```
3. **The hosts' credentials** in `.env`: the codex CLI's own login and `CLAUDE_CODE_OAUTH_TOKEN`
   for the Claude sessions.

## Usage

```bash
# List available competitions
PYTHONPATH=. python -m benchmarks.mle.runner --list          # every competition
PYTHONPATH=. python -m benchmarks.mle.runner --lite          # the lite roster

# Solve a competition
PYTHONPATH=. python -m benchmarks.mle.runner -c spooky-author-identification -i 20 --workspace tmp/mle_campaign
```

## CLI options

| Option | Description | Default |
|--------|-------------|---------|
| `-c, --competition` | Competition ID | Required |
| `-i, --iterations` | `Budget.experiments` | the config's `budget.experiments` |
| `--time-budget-hours` | `Budget.minutes`, in hours | the config's `budget.minutes` (unbounded) |
| `-d, --coding-agent` | The host every role without a `cli` of its own runs on | `codex`, the override file's `host` |
| `--harness` | A harness reference | the bundled `predictive-modelling` |
| `--experience` | Comma-separated experience sources to serve | none |
| `--workspace` / `--resume` | The campaign directory / continue the campaign in it | a fresh directory |
| `--list` / `--lite` | List competitions | - |

## Layout

| path | role |
|---|---|
| `runner.py` | the single-competition CLI on `build()`: prepares the data, stages the evaluation, writes the Brief, grades the delivery once |
| `context.py` | the Brief from the competition's description and files |
| `config.yaml` | the override file over the packaged config; the `benchmark:` block holds the runner's own keys (the archive root, the caps, the floor scores, the forbidden packages) |
| `data/generic_eval/` | the provided grader and its README for the maintainer |
| `data/generic_baseline/` | the seeded candidate: the sample submission and the floor score |
