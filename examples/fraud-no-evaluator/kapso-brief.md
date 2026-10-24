Objective    Raise the fraud scorer's precision-recall AUC on held-out
             transactions, keeping the contract: score.py takes --data and
             --out and writes id,fraud_probability for every row.
Measured by  No evaluator exists. Build one in kapso_evaluation/ that
             follows this protocol: split kapso_datasets/transactions.csv
             once, stratified on fraud, 80/20 with seed 7; fit only on the
             80; report precision-recall AUC (average precision) on the
             20 as the last line, "pr_auc: <value>"; keep the split fixed
             for the whole campaign.
Baseline     unknown: the shipped rules have never been measured
Target       pr_auc above 0.50, proposed; raise it if the first measurement
             shows more room
Rules
  - the held-out 20 percent is never fitted on and never inspected by hand
  - every transaction gets a score; none is dropped
  - the evaluator, once built, is not modified
Budget       minutes=45 experiments=3
