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
   past olympiad solutions — the IOAI book converted by `book_to_bank.py` (below) — is served
   as experience (`--experience`), never staged.

## Quickstart

```bash
# from the repository root
pip install -e .

# ingest a task (URL or organizer brief) into a run root, with the task's binding rules
PYTHONPATH=src:. python -m benchmarks.ioai2026.preflight \
    --task <task url or brief> --root tmp/ioai/task1 \
    --rules benchmarks/ioai2026/RULES.md

# run the campaign for one 6 hour session
PYTHONPATH=src:. python -m benchmarks.ioai2026.runner --root tmp/ioai/task1 --hours 6
```

`--rules` pins the task's binding rules under the task (the default is the IOAI AI Models Track
rules beside the script); another competition's rules file turns the preflight and the runner to
that competition, whose quota and report requirements the statement then carries. The preflight
refuses to run without a rules file at the path given.

## The book as a bank

The bank served as experience is the IOAI book — one directory per past olympiad task
(`problem.md`, `idea.md`, `solution/`) — converted by `book_to_bank.py`: one procedure card per
entry at `procedures/<uid>/card.md` with the solution files under `code/`, the card's one
evidence entry `reported` (the score at its source, who reported it, under what licence, by
what protocol), the card born `candidate`. A reported score is not a kapso measurement: the
serving layer says so on every read, the reliability block carries no numbers, and only a
campaign that runs the card promotes it. The licence pass over the book (`PROVENANCE.md`: one
row per entry with the licence read at every cited source, the use and publish verdicts, the
open questions left to a human) decides membership: the shareable bank takes the verdicts
`shippable-with-attribution` and `ours (shippable)`, the local-only bank the rest; `--exclude`
drops an entry by uid, so a campaign on one of the book's tasks is served the bank without its
own entry.

```bash
PYTHONPATH=src:. python benchmarks/ioai2026/book_to_bank.py \
    --book <the book> --provenance <provenance.json> --out ~/banks/ioai-shareable \
    --verdicts shippable-with-attribution "ours (shippable)" [--exclude <uid>] [--table PROVENANCE.md]
PYTHONPATH=src:. python -m benchmarks.ioai2026.runner --root tmp/ioai/task1 --hours 6 \
    --experience ~/banks/ioai-shareable
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
| `book_to_bank.py` | the IOAI book as a bank: one procedure card per entry, its evidence `reported`, membership by the licence pass |
| `PROVENANCE.md` | the licence pass over the book: every entry's sources, licences, use and publish verdicts, the open questions |
