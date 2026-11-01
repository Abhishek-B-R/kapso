"""One paper-trading cycle on demand: `deploy/run_paper.py --once` in the
engine's interpreter, its JSON document on stdout. The inputs on stdin
are the call's; `{"at": "<timestamp>"}` runs the cycle as of that bar
(`--at`), `{}` as of the latest closed bar."""

import json
import os
import subprocess
import sys

inputs = json.load(sys.stdin)
command = [os.environ["KAPSO_INTERPRETER"], "deploy/run_paper.py", "--once"]
if isinstance(inputs, dict) and inputs.get("at"):
    command.extend(["--at", str(inputs["at"])])
completed = subprocess.run(command, capture_output=True, text=True)
if completed.returncode != 0:
    sys.stderr.write(completed.stderr)
    sys.exit(completed.returncode)
print(completed.stdout.strip().splitlines()[-1])
