---
name: local
description: "Runs the solution in a Python process on this machine, called as a function: no infrastructure, the fastest path, no isolation. Use when the person wants to call the solution from Python here (development, testing, a CPU model), not for a shared service, a GPU workload or a scaled API."
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
   worker before the import, so do not load `.env` yourself.
2. Keep `requirements.txt` complete: the worker runs in the engine's own
   interpreter (`$KAPSO_INTERPRETER`), so install what `main.py` imports
   with `"$KAPSO_INTERPRETER" -m pip install -r requirements.txt`.
3. Run `bash "$KAPSO_TARGET_DIR/scripts/deploy.sh"`: it imports `main` in
   that interpreter with the caller's variables and fails naming the
   error if the import does not succeed. Fix and run it again.
4. Prove one call with real inputs, the shape the solution expects (a
   feature row, a text), in the same interpreter:

   ```bash
   "$KAPSO_INTERPRETER" -c 'from main import predict; print(predict({...}))'
   ```

5. Write the result file with `run` as `{"kind": "function", "module":
   "main", "callable": "predict"}`, no `endpoint`, no `values`, and the
   proof call's inputs and output.

## Never

Do not start a server or a background process: the engine's worker is the
runtime. Do not write the caller's variables into the code.
