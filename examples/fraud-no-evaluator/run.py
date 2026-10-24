"""A build with no evaluator: the campaign builds one from the brief's protocol."""
from kapso import Kapso, Brief

solution = Kapso().build(
    Brief.read("kapso-brief.md"), data="data", repo="repo", output="campaign",
)
print(solution.explain())
print(solution.feedback)     # the judge's last verdict, including on the evaluation the campaign built
