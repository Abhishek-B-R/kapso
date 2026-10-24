"""Your first build: the churn model, scored by the evaluator Kapso protects."""
from kapso import Kapso, Brief

solution = Kapso().build(
    Brief.read("kapso-brief.md"),
    evaluation="evaluation", data="data", repo="repo", output="build",
)
print(solution.explain())
