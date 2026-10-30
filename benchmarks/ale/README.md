# ALE-Bench Integration

Rendered guide: [docs.leeroo.com/docs/benchmarks/ale-bench](https://docs.leeroo.com/docs/benchmarks/ale-bench) · Kapso by Leeroo: [github.com/Leeroo-AI/kapso](https://github.com/Leeroo-AI/kapso) · `pip install leeroo-kapso`

This module provides integration with [ALE-Bench](https://github.com/SakanaAI/ALE-Bench), a benchmark for evaluating AI agents on AtCoder Heuristic Contests (algorithmic optimization problems).

Kapso achieved **#1 on ALE-Bench**: a final rating of **1909 Elo** against ALE Agent's 1879
(+30 Elo), under the same time budget per problem and the official scorer.

![ALE-Bench: Kapso's final rating of 1909 Elo against ALE Agent's 1879, above a per-problem breakdown of ten AtCoder Heuristic Contest problems; every row is drawn from its own truncated Elo origin, and the per-problem bar gaps share one scale](../../docs/images/ale-bench.png)

| Problem | ALE Agent | Kapso | Δ Elo |
|---|---|---|---|
| **Final result** | 1879 | **1909** | **+30** |
| ahc008 | 1189 | 1221 | +32 |
| ahc011 | 1652 | 1607 | −45 |
| ahc015 | 2446 | 2528 | +82 |
| ahc016 | 1457 | 2022 | +565 |
| ahc024 | 1980 | 1980 | 0 |
| ahc025 | 1331 | 1353 | +22 |
| ahc026 | 1965 | 2040 | +75 |
| ahc027 | 1740 | 1839 | +99 |
| ahc046 | 2153 | 2194 | +41 |
| ahc039 | 2880 | 2310 | −570 |

Every row of the chart is drawn from its own truncated axis, because Elo differences live far
from zero: on an absolute 1000–3000 scale the final ratings are 1.5% apart and render as the
same bar. The per-problem rows share one Elo-per-pixel scale, so gap sizes stay comparable
across problems — a +22 never renders like a +565; the Final result row uses a magnified
scale of its own. Bar lengths therefore carry only the within-row and across-row gaps; the
table above is the absolute reading.

## How it runs

The runner launches `build()` with the bundled `competitive-programming` harness. The Brief
carries the problem's facts (the statement, the constraints, the example, the contest's
tools, the scorer's invocation, the all-or-nothing rule, the contest's units); the harness
carries the discipline (the heuristic patterns, performance under a time limit, the scorer
procedure and its finish hook, the score auditor). The provided grader
(`data/generic_eval/grader.py`), registered by the evaluation maintainer, judges every
candidate's `main.cpp` through the benchmark's own Docker judge on the public cases, the
total averaged over the configured runs: the score of record, oriented so that higher is
better, with the floor for a submission that fails a case. The candidates run the same
grader as their scorer (`--scores results/scores.json`). After the campaign the runner
judges the delivered candidate once on the private cases and estimates the final rank and
the performance, written to `final_report.json` under the problem's archive root
(`tmp/ale/<problem>/`, the `benchmark.work_root` key of `config.yaml`).

## Prerequisites

1. **Core Kapso installed** (from the repository root): `pip install -e .`
2. **System dependencies**: `sudo apt-get install -y libcairo2-dev`
3. **Docker** (the judge): `sudo apt-get install -y docker.io && sudo usermod -aG docker $USER`
4. **ALE-Bench and its judge image**:
   ```bash
   git clone https://github.com/SakanaAI/ALE-Bench.git
   cd ALE-Bench && pip install . && pip install ".[eval]"
   bash ./scripts/docker_build_202301.sh $(id -u) $(id -g)
   cd ..
   ```
5. **The hosts' credentials** in `.env`: the codex CLI's own login and `CLAUDE_CODE_OAUTH_TOKEN`
   for the Claude sessions.

## Usage

```bash
# List available problems
PYTHONPATH=. python -m benchmarks.ale.runner --list          # every problem
PYTHONPATH=. python -m benchmarks.ale.runner --lite          # the lite roster

# Solve a problem
PYTHONPATH=. python -m benchmarks.ale.runner -p ahc039 -i 30 --workspace tmp/ale_campaign

# The final report again on a finished campaign (no campaign runs)
PYTHONPATH=. python -m benchmarks.ale.runner -p ahc039 --workspace tmp/ale_campaign --final-eval-only
```

## CLI options

| Option | Description | Default |
|--------|-------------|---------|
| `-p, --problem` | Problem ID (e.g. `ahc039`) | Required |
| `-i, --iterations` | `Budget.experiments` | the config's `budget.experiments` |
| `--time-budget-hours` | `Budget.minutes`, in hours | the config's `budget.minutes` (unbounded) |
| `-d, --coding-agent` | The host every role without a `cli` of its own runs on | `codex`, the override file's `host` |
| `--harness` | A harness reference | the bundled `competitive-programming` |
| `--experience` | Comma-separated experience sources to serve | none |
| `--workspace` / `--resume` | The campaign directory / continue the campaign in it | a fresh directory |
| `--final-eval-only` | No campaign: the final report (the private cases, the rank, the performance) on the solution the `--workspace` campaign already holds; refused without `--workspace` | - |
| `--list` / `--lite` | List problems | - |

## Layout

| path | role |
|---|---|
| `runner.py` | the single-problem CLI on `build()`: writes the task root, stages the evaluation, writes the Brief, judges the delivery once on the private cases |
| `context.py` | the Brief from the problem's statement |
| `problems.py` | the lite roster, as data |
| `config.yaml` | the override file over the packaged config; the `benchmark:` block holds the runner's own keys (the archive root, the runs, the judge's workers, the floor scores) |
| `data/generic_eval/` | the provided grader and its README for the maintainer |
