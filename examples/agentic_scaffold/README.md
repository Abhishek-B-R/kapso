# Agentic scaffold: chart images to CSV

An hour-long build that improves the vision-language extractor in
`repo/optimize.py`, which turns a chart image into the CSV table it shows,
from about 0.30 to 0.35 accuracy toward the brief's 0.50, with the
repository's own `evaluate.py` as the judge: 20 percent header match, 80
percent SMAPE similarity of the numbers, over 100 line charts.

Recorded result: not recorded yet.

## What you get

- `repo/optimize.py`, whose `VLMExtractor.image_to_csv()` is rewritten on a
  branch of its own inside `build/`: the prompt, the parsing, a multi-step
  extraction, validation.
- A score from `repo/evaluate.py --max-samples 100 --num-workers 50`.
- `build/.kapso/solution.json`, the record, read back by `Solution.open("build")`.

## Run it

```bash
pip install openai huggingface_hub
echo 'OPENAI_API_KEY=sk-...' >> .env     # the extractor and the evaluator call the model
python repo/prepare_data.py              # downloads subset_line_100/: index.csv, images/, tables/
kapso doctor build
kapso build --brief kapso-brief.md --repo repo --output build --detach
kapso watch build --follow
```

`python run.py` is the same build from Python.

## What to look at

- `kapso-brief.md`: valid CSV with a header, a vision-capable OpenAI model
  and a reasonable cost per query are rules the judge enforces.
- `solution.diff()`: the extractor that won.
- `cd build && python evaluate.py --max-samples 10 --num-workers 4`: a quick
  re-measurement by hand.

## Change it

- The target: `Target` in the brief.
- The budget: the brief's `Budget minutes=60 iterations=6`, or the command's
  `--budget-minutes` and `--iterations`, which win over it.
- Protect the evaluator and the data from the start by moving `evaluate.py`
  into a directory of its own and passing it with `--evaluation`, and
  `subset_line_100/` with `--data`.
