---
name: modal
description: "Deploys the solution as a serverless function on Modal.com, with a GPU when the model needs one and scaling to zero: pay per call, no server to keep. Use when the solution needs a GPU this machine lacks or should scale with demand and a Modal account is at hand (`modal token new`); not for a quick local call (local) or a persistent service on this machine (docker)."
metadata:
  requires:
    binary: modal
    install: "pip install \"leeroo-kapso[modal]\" and authenticate with `modal token new`"
  run_kinds: [script]
---
# Modal

The solution runs as the Modal app `kapso-$KAPSO_DEPLOYMENT_NAME` with a
function `predict`; the engine calls it through the Modal SDK by the app's
name (the target's `scripts/run.py`).

## Steps

1. Give the solution a module-level entry point, `main.py` with
   `predict(inputs: dict) -> dict`; keep `requirements.txt` complete.
2. Write `modal_app.py`:

   ```python
   import os
   import sys

   import modal

   app = modal.App(os.environ["KAPSO_VALUE_APP"])
   image = (
       modal.Image.debian_slim(python_version="3.11")
       .pip_install_from_requirements("requirements.txt")
       .add_local_dir(".", remote_path="/root/solution", ignore=[".env", ".git", ".claude", ".agents", ".codex", "__pycache__", "kapso_evaluation", "prepared"])
       .workdir("/root/solution")   # the solution's relative paths (model/..., data/...) resolve as they did here
   )
   secrets = [modal.Secret.from_dotenv()] if os.path.exists(".env") else []


   @app.function(image=image, secrets=secrets, timeout=300)   # gpu="T4", memory=16384 when the model needs them
   def predict(inputs: dict) -> dict:
       sys.path.insert(0, "/root/solution")
       from main import predict as _predict
       return _predict(inputs)
   ```

   Name the app from `$KAPSO_VALUE_APP` as shown, never by hand: the
   engine looks the function up under that name. Request `gpu=` and
   `memory=` on the function only when the code needs them.
3. Export the value and run the deploy script:

   ```bash
   export KAPSO_VALUE_APP="kapso-$KAPSO_DEPLOYMENT_NAME"
   bash "$KAPSO_TARGET_DIR/scripts/deploy.sh"
   ```

   It runs `modal deploy modal_app.py` and then looks the function up by
   name; fix what fails and run it again.
4. Prove one call with real inputs through the SDK:

   ```bash
   echo '{...}' | "$KAPSO_INTERPRETER" "$KAPSO_TARGET_DIR/scripts/run.py"
   ```

5. Write the result file: no `endpoint` (the SDK call needs none), `run`
   as `{"kind": "script"}`, `values` with `app` exactly as exported, the
   artifacts (`modal_app.py`, `requirements.txt`), and the proof call's
   inputs and output.

## Never

Do not paste the caller's variables into `modal_app.py`: the `.env` file
rides as a Modal secret (Modal's dotenv loader unquotes a quoted value and
expands `${NAME}`, where the engine and docker take values verbatim: keep
the values plain). Do not deploy under another app name.
