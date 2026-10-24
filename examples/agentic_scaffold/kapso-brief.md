Objective    Optimize the VLM chart data extraction in optimize.py to
             improve accuracy: VLMExtractor.image_to_csv() turns a chart
             image into the CSV table it shows.
Measured by  python evaluate.py --max-samples 100 --num-workers 50, in the
             repository: for each chart image in subset_line_100/, the
             extracted CSV against the ground-truth table; accuracy is 20
             percent header match and 80 percent SMAPE similarity of the
             numeric values
Baseline     about 0.30 to 0.35
Target       0.50 or above
Rules
  - the output is valid CSV with a header row
  - the extractor works with OpenAI vision-capable models
  - the average cost per query stays reasonable
  - evaluate.py and subset_line_100/ are never modified
Budget       minutes=60 experiments=6
