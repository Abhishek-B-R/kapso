# Fraud scorer

`score.py` assigns every transaction a fraud probability from three
hand-written rules. There is no evaluator in this repository and no
train/test split: `transactions.csv` holds every labelled row.

Contract, which any replacement keeps:

```
python score.py --data <directory holding transactions.csv> --out scores.csv
```

writes `id,fraud_probability` for every transaction, in input order.
