# A strategy on daily bars

`strategy.py` holds one function, `signal(bars) -> pd.Series`: the position
to hold per bar, in [-1, 1], computed from that bar and the ones before it.
The evaluation (`kapso_evaluation/evaluate.py`) shifts the signal by one
bar, charges 5 basis points per unit of turnover, and scores the
out-of-sample year as an equal-weight portfolio over the instruments under
`kapso_datasets/bars/`. Develop on the bars you have; the out-of-sample
bars are read by the evaluation alone.
