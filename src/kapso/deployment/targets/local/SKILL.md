---
name: local
description: "Runs the solution in a Python process on this machine, called as a function: no infrastructure, the fastest path, no isolation. Use when the person wants to call the solution from Python here (development, testing, a CPU model), not for a shared service, a GPU workload or a scaled API."
metadata:
  run_kinds: [function]
---
# Local

The solution runs in a worker process the engine starts in this
workspace; every call imports `main.predict` once and calls it. Nothing to
install, nothing to stop but the worker.

## Steps

1. Give the solution a module-level entry point, `main.py` at the
   workspace root:

   ```python
   def predict(inputs: dict) -> dict:
       """One call: the inputs as a dict, the result as a dict."""
       ...
   ```

   Import heavy modules and load models at the top of `main.py` once (the
   worker keeps the module loaded between calls), never inside `predict`.
   A class is not looked for: `predict` is a module-level function. Read
   the caller's variables with `os.environ.get(...)`; they are set in the
   worker before the import (each value verbatim from `.env`), so do not
   load `.env` yourself.
2. Keep `requirements.txt` complete: the worker runs in the engine's own
   interpreter (`$KAPSO_INTERPRETER`), so install what `main.py` imports
   into it: `"$KAPSO_INTERPRETER" -m pip install -r requirements.txt`, or,
   when that interpreter has no pip (a `uv tool` install), `uv pip install
   --python "$KAPSO_INTERPRETER" -r requirements.txt`.
3. Run `bash "$KAPSO_TARGET_DIR/scripts/deploy.sh"`: it imports `main` in
   the engine's worker (the process every call runs in), the caller's
   variables loaded as the worker loads them, and fails with the
   traceback if the import does not succeed. Fix and run it again.
4. Prove one call with real inputs, the shape the solution expects (a
   feature row, a text), through the same worker:

   ```bash
   echo '{"inputs": {...}}' | "$KAPSO_INTERPRETER" -m kapso.deployment.worker "$KAPSO_WORKSPACE" main predict ${KAPSO_ENV_FILE:+"$KAPSO_ENV_FILE"}
   ```

   It answers one line, `{"output": ...}`: the proof's output.

5. Write the result file with `run` as `{"kind": "function", "module":
   "main", "callable": "predict"}`, no `endpoint`, no `values`, and the
   proof call's inputs and output.

## Never

Do not start a server or a background process: the engine's worker is the
runtime. Do not write the caller's variables into the code.
