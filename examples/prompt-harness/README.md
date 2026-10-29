# Prompt engineering: a better AIME prompt

An hour-long build that rewrites the prompt template in `repo/optimize.py`
until accuracy on a subset of AIME 2024 problems climbs from the shipped
0.10 to 0.20 toward the brief's 0.30 to 0.50, with the repository's own
`evaluate.py` as the judge.

Recorded result: not recorded yet.

## What you get

- `repo/optimize.py`, whose `PROMPT_TEMPLATE` and `solve()` are rewritten on
  a branch of its own inside `campaign/`, one branch per experiment.
- A score from `repo/evaluate.py`: accuracy, with answers in `\boxed{XXX}`
  form, calling the OpenAI model it names.
- `campaign/.kapso/solution.json`, the record, read back by `Solution.open("campaign")`.

## Run it

```bash
pip install openai datasets          # what repo/evaluate.py needs
echo 'OPENAI_API_KEY=sk-...' >> .env   # the evaluator calls the model
kapso doctor build
kapso build --brief kapso-brief.md --repo repo --output campaign --detach
kapso watch campaign --follow
```

`python run.py` is the same build from Python, into the same `campaign/`
directory: run one or the other.

## What to look at

- `kapso-brief.md`: the objective, the measurement, the baseline, the
  target and the rules. The rule that `evaluate.py` is never modified is
  what the judge enforces for the whole campaign.
- `solution.diff()`: the prompt that won, against the shipped one.
- `cd campaign && python evaluate.py`: the score, re-measured by hand.
- `kapso trace campaign`: every attempt with its sessions and runs, its
  score and the judge's words, what was rejected and why, what it cost.

## Change it

- The target: `Target` in the brief; the model: the one `evaluate.py` names.
- The budget: the brief's `Budget minutes=60 experiments=8`, or the command's
  `--budget-minutes` and `--budget-experiments`, which win over it.
- Protect the evaluator from the start by moving `evaluate.py` into a
  directory of its own and passing it with `--evaluation`; `Measured by`
  then names `kapso_evaluation/evaluate.py`.
