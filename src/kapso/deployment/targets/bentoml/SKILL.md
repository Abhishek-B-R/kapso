---
name: bentoml
description: "Deploys the solution as a BentoML service on BentoCloud: a managed, monitored ML endpoint with request batching and versioning. Use when the solution is a model to serve in production under a BentoCloud account (`BENTO_CLOUD_API_KEY`); not for development (local), a service on this machine (docker) or a conversational agent (langgraph)."
metadata:
  requires:
    binary: bentoml
    install: "pip install \"leeroo-kapso[bentoml]\" and log in with `bentoml cloud login`"
  run_kinds: [script]
---
# BentoML

The solution runs as the BentoCloud deployment `kapso-$KAPSO_DEPLOYMENT_NAME`;
the engine calls it through the BentoML SDK by that name (the target's
`scripts/run.py`), which asks BentoCloud for the endpoint each time, so a
redeploy that changes the URL changes nothing for the caller.

## Steps

1. Give the solution a module-level entry point, `main.py` with
   `predict(inputs: dict) -> dict`; keep `requirements.txt` complete.
2. Write `service.py`:

   ```python
   from typing import Any, Dict

   import bentoml


   @bentoml.service(resources={"cpu": "2", "memory": "4Gi"}, traffic={"timeout": 300})
   class SolutionService:
       def __init__(self) -> None:
           from main import predict as _predict
           self._predict = _predict

       @bentoml.api
       def predict(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
           return self._predict(inputs)

       @bentoml.api
       def health(self) -> Dict[str, str]:
           return {"status": "healthy"}
   ```

   and `bentofile.yaml` (`service: "service:SolutionService"`, the
   includes, `python.requirements_txt`, the Python version). Request a
   GPU in `resources` only when the model needs one.
3. Write `deploy.py`, which runs `bentoml deploy . --name
   "$KAPSO_VALUE_DEPLOYMENT"` (with `--env NAME=VALUE` for each variable
   named in the env file, read from the file, never pasted into code) and
   waits until the deployment is running.
4. Export the value and run the deploy script:

   ```bash
   export KAPSO_VALUE_DEPLOYMENT="kapso-$KAPSO_DEPLOYMENT_NAME"
   bash "$KAPSO_TARGET_DIR/scripts/deploy.sh"
   ```

   It runs `deploy.py` and prints the deployment as BentoCloud describes
   it; fix what fails and run it again.
5. Prove one call with real inputs through the SDK:

   ```bash
   echo '{...}' | "$KAPSO_INTERPRETER" "$KAPSO_TARGET_DIR/scripts/run.py"
   ```

6. Write the result file: `endpoint` the deployment's URL as BentoCloud
   printed it, `run` as `{"kind": "script"}`, `values` with `deployment`
   exactly as exported, the artifacts (`service.py`, `bentofile.yaml`,
   `deploy.py`, `requirements.txt`), and the proof call's inputs and
   output.
