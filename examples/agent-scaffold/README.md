# Agentic scaffold: chart images to CSV

An hour-long build that improves the vision-language extractor in
`repo/optimize.py`, which turns a chart image into the CSV table it shows,
from the shipped extractor's accuracy of about 0.30 to 0.35 (measured by
the repository's own `evaluate.py`, which you run first) toward the
brief's 0.50, with that `evaluate.py` as the judge: 20 percent header
match, 80 percent SMAPE similarity of the numbers, over 100 line charts.

Recorded result: not recorded yet.

## What you get

- `repo/optimize.py`, whose `VLMExtractor.image_to_csv()` is rewritten on a
  branch of its own inside `campaign/`: the prompt, the parsing, a multi-step
  extraction, validation.
- A score from `repo/evaluate.py --max-samples 100 --num-workers 50`.
- `campaign/.kapso/solution.json`, the record, read back by `Solution.open("campaign")`.

## Run it

```bash
pip install openai huggingface_hub
echo 'OPENAI_API_KEY=sk-...' >> .env     # the extractor and the evaluator call the model
python repo/prepare_data.py              # downloads subset_line_100/: index.csv, images/, tables/
kapso doctor build
kapso build --brief kapso-brief.md --repo repo --output campaign --detach
kapso watch campaign --follow
```

`python run.py` is the same build from Python, into the same `campaign/`
directory: run one or the other.

## What to look at

- `kapso-brief.md`: valid CSV with a header, a vision-capable OpenAI model
  and a reasonable cost per query are rules the judge enforces.
- `solution.diff()`: the extractor that won.
- `cd campaign && python evaluate.py --max-samples 10 --num-workers 4`: a quick
  re-measurement by hand.
- `kapso trace campaign`: every attempt with its sessions and runs, its
  score and the judge's words, what was rejected and why, what it cost.

## Change it

- The target: `Target` in the brief.
- The budget: the brief's `Budget minutes=60 experiments=6`, or the command's
  `--budget-minutes` and `--budget-experiments`, which win over it.
- Protect the evaluator and the data from the start by moving `evaluate.py`
  into a directory of its own and passing it with `--evaluation`, and
  `subset_line_100/` with `--data`.
