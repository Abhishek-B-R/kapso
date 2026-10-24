"""A build with no evaluator: the campaign builds one from the brief's protocol."""
from kapso import Kapso, Brief

solution = Kapso().build(
    Brief.read("kapso-brief.md"), data="data", repo="repo", output="build",
)
print(solution.explain())
print(solution.evaluation)   # the evaluator the campaign built and registered
