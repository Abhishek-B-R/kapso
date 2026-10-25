"""The trading example on its harness.

Run from this directory, after `python generate.py`; the campaign lands in campaign/."""
from kapso import Kapso, Brief

kapso = Kapso()
kapso.load_harness("../harnesses/trading")
solution = kapso.build(
    Brief.read("kapso-brief.md"),
    evaluation="evaluation", data="data", repo="repo", output="campaign",
)
print(solution.explain())
