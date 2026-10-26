"""The `function` run kind's worker (docs/plans/redesign/wp5-deploy.md):
one process per `Software` handle, started by it as

    <interpreter> -m kapso.deployment.worker <workspace> <module> <callable> [<env-file>]

in the workspace, the env file's values set before the import. It
imports `<workspace>/<module>.py` once and answers one JSON line per
request line: `{"ping": true}` with `{"pong": true}`, `{"inputs": …}`
with `{"output": <callable>(inputs)}`. The solution's own prints go to
stderr, so the reply channel stays clean. A call whose function raises
ends the worker with the traceback on stderr: the handle reports it as
the call's error and starts a worker again for the next call.

The env file is read as the docker target's `--env-file` reads it: one
`NAME=VALUE` per line, the value verbatim to the end of the line (no
quotes removed, nothing expanded), blank lines and `#` lines skipped. The
local target's `deploy.sh` proves the entry point through this same
module, so what it proved is what every call runs."""

import importlib
import json
import os
import sys
from pathlib import Path


def load_env_file(path: str) -> None:
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.lstrip().startswith("#") or "=" not in line:
            continue
        name, value = line.split("=", 1)
        os.environ[name.strip()] = value


def main(argv) -> None:
    workspace, module_name, callable_name = argv[1:4]
    if len(argv) > 4:
        load_env_file(argv[4])
    os.chdir(workspace)
    sys.path.insert(0, str(Path(workspace).resolve()))
    # The reply channel is the original stdout on a descriptor of its own;
    # descriptor 1 then goes to stderr, so the solution's prints and the
    # output of any process it starts never reach the channel.
    channel = os.fdopen(os.dup(sys.stdout.fileno()), "w", encoding="utf-8")
    os.dup2(sys.stderr.fileno(), sys.stdout.fileno())
    sys.stdout = sys.stderr
    function = getattr(importlib.import_module(module_name), callable_name, None)
    if not callable(function):
        sys.exit(f"{module_name}.py has no module-level callable {callable_name}")
    for line in sys.stdin:
        request = json.loads(line)
        reply = {"pong": True} if request.get("ping") else {"output": function(request["inputs"])}
        channel.write(json.dumps(reply) + "\n")
        channel.flush()


if __name__ == "__main__":
    main(sys.argv)
