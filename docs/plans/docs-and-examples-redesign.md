# Redesigning the examples and the documentation

2026-10-24. Companion to `docs/research/redesign-status.md` (the build
order) and `docs/research/kapso-redesign.md` (the positioning and the
rules for public sentences). The documentation is Mintlify, built from
`main`, navigation in `/docs.json`; internal notes under `docs/plans/` and
`docs/research/*.md` stay out of the site.

## 1. What is wrong today, in one paragraph

The site is organised by the engine's internals: an "Evolve system" section
with seventeen pages on orchestrator, strategies, gates, feedback generator
and lifecycle, beside knowledge, learning and deployment sections named
after modules. An engineer who wants to build something has to learn the
machine before finding the three lines they need. The examples are five
use-case directories whose drivers run to about eighty lines each, which
is the old interface showing; their READMEs have four sections that differ
from one to the next; none of them is executed by a test, so they drift.

## 2. Principles

1. **Organised by what the reader is doing.** Two readers: the engineer
   who builds with Kapso and the author who writes a harness. A third, the
   contributor, gets the internals in one section at the end.
2. **Copy-paste first.** Every page opens with the outcome and the exact
   lines, Python and CLI; the concept comes after, short.
3. **Every snippet is an example that runs.** Snippets come from files
   under `examples/`, a drift check keeps page and file identical, and the
   semantic test S1 executes the examples on a fresh machine. The examples
   are the fixtures of the semantic tests: one source, not two.
4. **Claim-safe.** Every number travels with who ran it, on what evaluator,
   and when; the words-out list of `kapso-redesign.md` is a lint on public
   pages.
5. **Shipped behaviour only.** A section lands with the release that ships
   its verbs; until then the current pages stay.
6. **Readable by agents too.** The docs MCP server serves these pages to
   coding agents and the plugin's skills link to them, so headings name
   the job, commands sit in fenced blocks, and no marketing sits between
   steps.
7. **One job per page, and the sidebar reads as the flow.**

## 3. The new navigation

Tab **Documentation**:

| Group | Pages |
|---|---|
| Start | Overview (the one-liner, the TL;DR, the twelve lines); Install; Your first build (ten minutes, the churn example); Kapso in your coding agent (the install line per host, the six skills in one table, what the agent will ask you) |
| Build | The objective and the brief; Evaluation (the contract; provided, proposed, versioned); Run and watch; The inbox; Review the result; Resume and budgets |
| Harnesses | What a harness is; Use a harness (list, add, load, the brief line); Bundled harnesses (one page each as they ship); Write a harness (the authoring guide, public edition); Harness reference (`harness.yaml`, pages, skills, delegates, `mcp.json`, hooks, `check`, `export`); Example: trading |
| Experience | What experience is; Your bank (learn, share, scope); Leeroopedia; Ingest a repository or a paper; Provenance |
| Deploy | Targets; Write a target skill |
| Learn | What learn produces (cards with receipts); Development mode (the graders, the pipeline, the bank's internals, condensed from today's six pages) |
| How it works | The engine's modules; Evaluation integrity; The record and the trace; The search (strategies, parent selection, cost-aware selection, model routing and retries, condensed from today's Evolve pages) |
| Benchmarks | RelBench, MLE-bench, ALE-bench, IOAI: results with provenance and how to reproduce through the harness |

Tab **API Reference**: Python API (`Kapso`, `Brief`, `Budget`, `Solution`,
`Software`, `Experience`); CLI; Config; Brief format; Harness formats;
Plugin commands.

Where today's pages go:

| Today | New home |
|---|---|
| index, installation, quickstart | Start: Overview, Install, Your first build |
| agent-access, coding-agent-skills | Start: Kapso in your coding agent |
| evolve/overview, architecture, execution-flow, orchestrator, experiment-lifecycle | How it works: The engine's modules |
| evolve/external-evaluation, evaluation-integrity | Build: Evaluation, and How it works: Evaluation integrity |
| evolve/inbox, resuming-runs | Build: The inbox; Resume and budgets |
| evolve/search-strategies, parent-selection, cost-aware-selection, model-routing-retries, coding-agents, feedback-generator | How it works: The search |
| evolve/mcp-gates, repo-memory | Experience: What experience is; How it works: The engine's modules |
| knowledge/* | Experience: Ingest; Leeroopedia |
| learning/* | Learn; Experience: Your bank |
| deployment/* | Deploy |
| benchmarks/* | Benchmarks, restated per harness |
| reference/* | API Reference, extended |

## 4. The examples

An example is a task on a harness, and its driver is the twelve-line flow.
The shape, identical for every example:

```
examples/<name>/
├── README.md          four sections, always the same: What you get · Run it · What to look at · Change it
├── repo/              the starting code
├── evaluation/        the evaluator Kapso protects (evaluate.py, its fast mode)
├── data/ or fetch.py  the data, or how to get it
├── kapso-brief.md     the brief, with the Harness and Experience lines
└── run.py             load_harness, build, print the result; deploy and learn where the example says so
```

Rules: `run.py` is at most twelve lines of code; the README is under eighty
lines and opens with the outcome and the one command; the recorded result
in the README names who ran it, on which evaluator, when; every example
runs under the semantic tests on a fresh machine; an example's harness is
bundled (by name) or sits under `examples/harnesses/` to be read.

The set:

| Example | Harness | What it shows |
|---|---|---|
| `churn-first-build` | `predictive-modelling` (bundled) | the ten-minute first build with an evaluator present; the record |
| `fraud-no-evaluator` | `predictive-modelling` | the proposed evaluation, approved and protected |
| `full-loop` | `predictive-modelling` | build, review, learn, build again with experience, deploy (today's `ml_model_development` role) |
| `gpu-kernels` | `gpu-kernels` | today's CUDA example as a task on its harness |
| `torch-performance` | `torch-performance` | today's PyTorch example |
| `prompt-harness` | `prompt-harness` | today's prompt-engineering example |
| `agent-scaffold` | `agent-scaffold` | today's agentic-scaffold example |
| `trading` | `examples/harnesses/trading` | the author's example: a harness, a task, the probe run, one improve round |

`examples/README.md` is the table above with minutes and the one command
per row. Today's five drivers are retired with their examples' conversion;
the drop from eighty lines to twelve is the interface's proof, and the
README says so once.

## 5. Checks

- `mint validate` and `mint broken-links`, as today.
- A snippet-drift check in `scripts/`: every fenced block on a public page
  that names its source file (`examples/churn-first-build/run.py`) equals
  that file; CI fails on a difference.
- Semantic test S1 runs every example's `run.py` and CLI line on a fresh
  GCP machine from the released package or a wheel built from the branch;
  nothing from the development checkout.
- Two lints on public pages: the words-out list, and a number near a
  metric word with no provenance beside it.

## 6. Migration, tied to the build order

| With build step | Documentation | Examples |
|---|---|---|
| 1, `build` | Start and Build sections; the TL;DR pass; the Evolve pages retired into How it works | `run.py` and `kapso-brief.md` for every example; `churn-first-build` and `fraud-no-evaluator` created |
| 2, the harness package | Harnesses section; Harness reference | every example re-based on its harness; `trading` example with its probe run |
| 3, experience | Experience section; knowledge and learning pages merged | `full-loop` |
| 5 and 6, deploy and observability | Deploy; The record and the trace | deploy lines in `full-loop` |
| 7, the plugin | Kapso in your coding agent | the plugin flow in `churn-first-build`'s README |
| 8, the ports | one Bundled-harness page per port; Benchmarks restated | |

The site builds from `main`, so each section ships in the release that
ships its verbs, and the old pages stay live until then.
