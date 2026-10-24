"""Your first build: the churn model, scored by the evaluator Kapso protects.

Run from this directory, after `python generate.py`; the campaign lands in campaign/."""
from kapso import Kapso, Brief

solution = Kapso().build(
    Brief.read("kapso-brief.md"),
    evaluation="evaluation", data="data", repo="repo", output="campaign",
)
print(solution.explain())
