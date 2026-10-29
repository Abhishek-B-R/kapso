# IOAI 2026 Integration

Rendered guide: [docs.leeroo.com/docs/benchmarks/ioai-2026](https://docs.leeroo.com/docs/benchmarks/ioai-2026) · Kapso by Leeroo: [github.com/Leeroo-AI/kapso](https://github.com/Leeroo-AI/kapso) · `pip install leeroo-kapso`

Every summer the sharpest young AI minds on the planet sit the same exam. The
[International Olympiad in Artificial Intelligence](https://ioai-official.org) is the IMO of
the AI era: at IOAI 2026 in Astana, 471 contestants from 108 countries and territories
competed on expert designed problems spanning the whole craft of machine learning, from
computer vision and language to optimization under a single GPU budget.

In 2026 the olympiad opened a second arena. [IOAI², the AI Model Track](https://ioai-official.org/ai-model-track/),
puts AI systems in the same exam hall: the same
[six contest tasks](https://github.com/IOAI-official/IOAI-2026), two fully autonomous 6 hour
sessions with three tasks each, up to 50 submission attempts per task, every solution scored
on standardized single GPU hardware. Once a session starts, no human may solve, correct, or
improve anything. Fourteen AI labs entered as Founding AI Participants; Kapso was one of them.
The olympiad's own account of the inaugural track:
[What happens when autonomous AI takes on the same tasks as the world's top young AI talents?](https://ioai-official.org/what-happens-when-autonomous-ai-takes-on-the-same-tasks-as-the-worlds-top-young-ai-talents/)

## Results

🎓 **Surpassed the best human performance**: the total of 536.07 topped every one of the
471 contestants from 108 countries

🥇 **Top 3 of all AI system participants**: the 14 Founding AI Participants spanned major
AI labs and several startups

🏆 **IOAI² Grand Master Trophy**

Per task:

| # | Task | Score |
|---|---|---|
| 1 | Speech understanding: reconstruct the chronological order of a shuffled spoken conversation from raw audio | 75.97 |
| 2 | Sequential decision making: train a control policy from scratch to steer an agent through a dynamic grid world | 98.83 |
| 3 | Interactive language reasoning: play 120 live word association games against an adaptive judge using semantic embeddings | 92.03 |
| 4 | Text forensics: pinpoint the exact character where a document switches authors, armed with only a text encoder | 98.84 |
| 5 | Adversarial machine learning: craft imperceptible image perturbations that steer two different vision architectures at once | 97.17 |
| 6 | Extreme model compression: fit a hidden field with a network under 20k parameters that must generalize and quantify its own uncertainty | 73.23 |
|   | **Total** | **536.07** |

## How it works

1. **Preflight**: one agent session ingests the official task brief, downloads the data, and
   writes the task statement with the metric's direction. The campaign clock starts at brief-in.
2. **Campaign**: the runner launches `build()` with the bundled `competitive-programming`
   harness. The Brief carries the statement, the competition, the deadline, the submission
   procedure and the ledger, the session pool and the organizers' rules; the harness carries
   the discipline (the contest economics, the Kaggle flow, the olympiad playbook, the
   auditors, the hooks that ask for the insurance submission and refuse a raw submit). Every
   submission goes through the task root's procedure, which records it in the ledger; the
   provided evaluation reports each candidate's own recorded submission by its public score.
3. **Shared learning**: lanes learn from every sibling submission on the board, and a bank of
   past olympiad solutions is served as experience (`--experience`), never staged.

## Quickstart

```bash
# from the repository root
pip install -e .

# ingest a task (URL or organizer brief) into a run root
PYTHONPATH=src:. python -m benchmarks.ioai2026.preflight \
    --task <task url or brief> --root tmp/ioai/task1

# run the campaign for one 6 hour session
PYTHONPATH=src:. python -m benchmarks.ioai2026.runner --root tmp/ioai/task1 --hours 6
```

## Layout

| path | role |
|---|---|
| `runner.py` / `preflight.py` | the campaign on `build()` with the contest root staged / task ingestion |
| `context.py` | the Brief from the preflight's statement and the campaign's facts |
| `submit.py` | the task root's submission procedure: submits and records the ledger entry |
| `data/generic_eval/` | the provided evaluation: the candidate's own recorded submission |
| `kernel_slots.py` | ticket office over the submission platform's per account session limits |
| `config.yaml` | the override file over the packaged config (the roles, the lanes, the budget); the runner's own settings (the harvest, the session budget) under `benchmark:` |
| `RULES.md` | organizer rules, pinned into every campaign's contest root |
