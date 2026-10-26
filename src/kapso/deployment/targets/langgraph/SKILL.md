---
name: langgraph
description: "Deploys the solution as a stateful agent on LangGraph Platform, with threads that keep a conversation across calls, streaming and human-in-the-loop. Use when the solution is a LangGraph or LangChain agent and a LangSmith account is at hand (`LANGSMITH_API_KEY`); not for plain inference (local, docker, modal, bentoml) or batch work."
metadata:
  requires:
    binary: langgraph
    install: "pip install \"leeroo-kapso[langgraph]\" and set LANGSMITH_API_KEY"
  run_kinds: [script]
---
# LangGraph

The solution runs as a graph on LangGraph Platform; the engine calls it
through the platform's SDK (the target's `scripts/run.py`) on one thread
it keeps in the workspace, so a conversation persists across calls. A
stop ends that thread and leaves the platform deployment (serverless, it
scales to zero); the stop's output says how to delete it.

## Steps

1. Export the compiled graph from `agent.py` as `graph`, and keep `main.py`
   with `predict(inputs: dict) -> dict` for a local check (`inputs` with
   `messages`, or `text` for one user message).
2. Write `langgraph.json`:

   ```json
   {"dependencies": ["."], "graphs": {"agent": "./agent.py:graph"}, "env": ".env"}
   ```

   `"env": ".env"` points the deployment at the caller's variables when
   the file exists; never paste a value into the code. Keep
   `requirements.txt` complete (`langgraph`, `langgraph-sdk`, the model
   provider's package).
3. Run the deploy script, `bash "$KAPSO_TARGET_DIR/scripts/deploy.sh"`:
   it runs `langgraph deploy --name "kapso-$KAPSO_DEPLOYMENT_NAME"` (the
   platform deployment of this name, found or created), which prints the
   deployment's URL. Then export the values and check the deployment:

   ```bash
   export KAPSO_VALUE_DEPLOYMENT_URL="https://..."   # as printed
   export KAPSO_VALUE_ASSISTANT=agent
   bash "$KAPSO_TARGET_DIR/scripts/health.sh"
   ```

4. Prove one call with real inputs through the SDK:

   ```bash
   echo '{"text": "..."}' | "$KAPSO_INTERPRETER" "$KAPSO_TARGET_DIR/scripts/run.py"
   ```

5. Write the result file: `endpoint` the deployment's URL, `run` as
   `{"kind": "script"}`, `values` with `deployment_url` and `assistant`
   exactly as exported, the artifacts (`agent.py`, `langgraph.json`,
   `requirements.txt`), and the proof call's inputs and output.
