"""Deployment (docs/plans/redesign/wp5-deploy.md): `Kapso.deploy()` runs
one deployment session on a copy of the solution, staged with the
target's skill (bundled under `targets/`, or a harness's), records the
deployment under the campaign (`.kapso/deployments/<n>/`) and hands back
a `Software` that runs, stops, starts and reads it through the record and
the target's scripts; `Software.open(campaign, number)` is the same
handle from any later process.

    from kapso import Kapso, Software, Solution

    software = Kapso().deploy(Solution.open("../churn-build"), target="docker")
    software.run({"tenure_months": 3, "plan": "basic"})
    software.stop()
    Software.open("../churn-build", software.number).start()
"""

from kapso.deployment.errors import DeployError
from kapso.deployment.handle import Software

__all__ = ["DeployError", "Software"]
