---
name: docker
description: "Builds the solution into an image and runs it as a container serving HTTP on a port of this machine: isolated, reproducible, system packages welcome. Use when the solution needs its own environment or system dependencies, or a service other processes call over HTTP; not for a GPU workload the machine lacks, nor for a quick call from Python (local)."
metadata:
  requires:
    binary: docker
    install: "install Docker: https://docs.docker.com/get-docker/ (and start its daemon)"
    probe:
      command: docker info
      timeout: 30
      fix: "start Docker Desktop, or: sudo systemctl start docker"
  run_kinds: [http]
---
# Docker

The solution runs as a container `kapso-$KAPSO_DEPLOYMENT_NAME` built from
the image of the same name, listening inside on a port you choose
(8000 unless the app needs another) and published on this machine's
`$KAPSO_PORT`. The engine calls `POST http://localhost:$KAPSO_PORT/predict`
and reads `GET /health`.

## Steps

1. Give the solution a module-level entry point, `main.py` with
   `predict(inputs: dict) -> dict`, importing heavy modules at the top.
2. Write `app.py`, a FastAPI application:

   ```python
   from typing import Any, Dict

   from fastapi import FastAPI

   from main import predict as _predict

   app = FastAPI()


   @app.get("/health")
   def health() -> Dict[str, str]:
       return {"status": "healthy"}


   @app.post("/predict")
   def predict(inputs: Dict[str, Any]) -> Dict[str, Any]:
       """The inputs as the raw JSON body, never wrapped."""
       return _predict(inputs)
   ```

   Add `fastapi` and `uvicorn` to `requirements.txt`, with every
   dependency `main.py` needs, pinned.
3. Write the `Dockerfile`:

   ```dockerfile
   FROM python:3.11-slim
   WORKDIR /app
   COPY requirements.txt .
   RUN pip install --no-cache-dir -r requirements.txt
   COPY . .
   RUN useradd --create-home --uid 1000 app && chown -R app:app /app
   USER app
   EXPOSE 8000
   CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
   ```

   The caller's variables reach the container through `--env-file` at
   run time (each value verbatim, as `.env` holds it); never `COPY .env`
   or bake a value into an `ENV` line. The deploy script adds `.env`,
   `.git`, the engine's and the hosts' directories, `kapso_evaluation`
   and `prepared` to `.dockerignore`; keep them there, add the data the
   service does not read (`kapso_datasets`, say), and copy into the
   workspace what it does read from `prepared/` (a link the image cannot
   follow).
4. Export the values the scripts need, then run the deploy script:

   ```bash
   export KAPSO_VALUE_CONTAINER_PORT=8000   # what the app listens on inside
   export KAPSO_VALUE_GPU=none              # or `all` when the image needs the machine's GPUs
   bash "$KAPSO_TARGET_DIR/scripts/deploy.sh"
   ```

   It removes a previous container of this deployment, builds the image,
   runs the container with the env file, the port and the GPU request,
   and waits for `/health`. On a failure read its message and the
   container's logs (`docker logs kapso-$KAPSO_DEPLOYMENT_NAME`), fix,
   and run it again.
5. Prove one call with real inputs:

   ```bash
   curl -sS -X POST "http://localhost:$KAPSO_PORT/predict" -H 'Content-Type: application/json' -d '{...}'
   ```

6. Write the result file: `endpoint` `http://localhost:$KAPSO_PORT`,
   `run` as `{"kind": "http", "url": "http://localhost:$KAPSO_PORT",
   "path": "/predict"}`, `values` with `container_port` and `gpu` exactly
   as exported (the engine recreates the container from them after a
   stop), the artifacts (`Dockerfile`, `app.py`, `requirements.txt`,
   `.dockerignore`), and the proof call's inputs and output.
